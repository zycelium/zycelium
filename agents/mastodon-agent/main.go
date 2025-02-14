package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/mattn/go-mastodon"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/micro"
	"github.com/zycelium/zycelium/agent"
)

const (
	initialRetryDelay = 1 * time.Second
	maxRetryDelay     = 5 * time.Minute
)

type Config struct {
	Debug       bool     `toml:"debug"`
	Server      string   `toml:"server"`
	AccessToken string   `toml:"access_token"`
	NatsURLs    []string `toml:"nats_urls"`
}

// Validate implements agent.Configurable interface
func (c Config) Validate() error { // Changed from pointer receiver to value receiver
	if c.Server == "" {
		return fmt.Errorf("server URL is required")
	}
	if c.AccessToken == "" {
		return fmt.Errorf("access token is required")
	}
	if len(c.NatsURLs) == 0 {
		return fmt.Errorf("at least one NATS URL is required")
	}
	return nil
}

type MastodonService struct {
	*agent.BaseService
	client *mastodon.Client
	acc    *mastodon.Account
	logger agent.Logger
	server string
}

func NewMastodonService(cfg Config, opts *agent.Options) (*MastodonService, error) {
	// Create base service
	base, err := agent.NewService("mastodon", cfg.NatsURLs,
		agent.WithVersion("1.0.0"),
	)
	if err != nil {
		return nil, err
	}

	// Initialize Mastodon client
	client := mastodon.NewClient(&mastodon.Config{
		Server:      cfg.Server,
		AccessToken: cfg.AccessToken,
	})

	svc := &MastodonService{
		BaseService: base,
		client:      client,
		logger:      agent.NewLogger(opts.Debug),
		server:      cfg.Server, // Store server URL
	}

	// Get account info
	acc, err := client.GetAccountCurrentUser(context.Background())
	if err != nil {
		return nil, err
	}
	svc.acc = acc

	// Add metadata
	base.SetMetadata(map[string]string{
		"account_id":       string(acc.ID),
		"account_username": acc.Username,
		"instance":         svc.getDomain(),
		"followers_count":  strconv.FormatInt(acc.FollowersCount, 10),
		"following_count":  strconv.FormatInt(acc.FollowingCount, 10),
		"statuses_count":   strconv.FormatInt(acc.StatusesCount, 10),
	})

	// Add handlers with simplified subject
	subject := fmt.Sprintf("mastodon.post.%s.%s", svc.getDomain(), acc.Username)
	svc.logger.Debug("Registering handler for subject: %s", subject)
	base.AddHandler(subject, micro.HandlerFunc(svc.handlePost))

	return svc, nil
}

func (s *MastodonService) handlePost(req micro.Request) {
	text := string(req.Data())
	if text == "" {
		req.Error("400", "Post text cannot be empty", []byte("empty post text"))
		return
	}

	s.logger.Debug("Posting status: %s", text)

	status, err := s.client.PostStatus(context.Background(), &mastodon.Toot{
		Status: text,
	})
	if err != nil {
		req.Error("500", "Failed to post status", []byte(err.Error()))
		return
	}

	req.Respond([]byte(status.URL))
}

func (s *MastodonService) getDomain() string {
	var domain string
	if s.acc != nil && s.acc.Acct != "" {
		if parts := strings.Split(s.acc.Acct, "@"); len(parts) > 1 {
			domain = parts[1]
		}
	}
	if domain == "" {
		u, err := url.Parse(s.server)
		if err != nil {
			return "unknown"
		}
		domain = u.Host
	}
	return strings.ReplaceAll(domain, ".", "_")
}

func (s *MastodonService) connectWithRetry(ctx context.Context) (chan mastodon.Event, error) {
	var (
		eventChan chan mastodon.Event
		err       error
		attempt   = 0
		delay     = initialRetryDelay
	)

	for {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
			if attempt > 0 {
				s.logger.Debug("Reconnection attempt %d after %v delay", attempt, delay)
				time.Sleep(delay)
				// Update delay with exponential backoff
				delay = time.Duration(math.Min(
					float64(delay)*2,
					float64(maxRetryDelay),
				))
			}

			eventChan, err = s.client.StreamingUser(ctx)
			if err != nil {
				s.logger.Debug("Connection failed: %v", err)
				attempt++
				continue
			}

			s.logger.Debug("Stream connected successfully after %d attempts", attempt)
			return eventChan, nil
		}
	}
}

func (s *MastodonService) streamHomeTimeline(ctx context.Context) {
	s.logger.Debug("Starting home timeline stream")

	// Pre-create subject for better performance
	subject := s.MakeSubject("mastodon", "stream", s.getDomain(), s.acc.Username, "timeline", "home")
	// OR alternatively:
	// subject := agent.MakeSubject("mastodon", "stream", s.getDomain(), s.acc.Username, "timeline", "home")

	for {
		select {
		case <-ctx.Done():
			s.logger.Debug("Stream shutting down")
			return
		default:
			eventChan, err := s.connectWithRetry(ctx)
			if err != nil {
				s.logger.Error("Error connecting to stream: %v", err)
				return
			}

			// Handle events until connection breaks
			for event := range eventChan {
				s.logger.Debug("Received event type: %T", event)

				switch e := event.(type) {
				case *mastodon.UpdateEvent:
					s.logger.Debug("Publishing status from @%s to %s", e.Status.Account.Username, subject)

					payload, err := json.Marshal(e.Status)
					if err != nil {
						s.logger.Error("Error marshaling status: %v", err)
						continue
					}

					// Add publish options for better reliability
					_, err = s.JetStream().Publish(subject, payload, nats.Context(ctx))
					if err != nil {
						s.logger.Error("Error publishing: %v", err)
					}
				case *mastodon.ErrorEvent:
					s.logger.Error("Stream error: %v", e.Error())
				case nil:
					// Connection closed
					s.logger.Debug("Stream connection closed, attempting reconnection")
					goto reconnect
				}
			}

		reconnect:
			s.logger.Debug("Stream disconnected, attempting reconnection")
		}
	}
}

func main() {
	// Parse flags and load config
	cfg, opts, err := agent.ParseFlags[Config]("mastodon-agent")
	if err != nil {
		log.Fatal(err)
	}

	// Create service
	svc, err := NewMastodonService(cfg, opts)
	if err != nil {
		log.Fatal(err)
	}

	// Create cancelable context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh
		cancel()
	}()

	// Sync config with NATS KV store
	if err := agent.SyncConfig(svc.BaseService.NATS(), "mastodon", cfg); err != nil {
		log.Printf("WARNING: Failed to sync config: %v", err)
	}

	// Start streaming timeline in background
	go svc.streamHomeTimeline(ctx)

	// Run service until context is canceled
	if err := svc.Run(ctx); err != nil {
		log.Fatal(err)
	}
}
