package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math"
	"net/url"
	"strconv"
	"strings"
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

var debug bool

func init() {
	flag.BoolVar(&debug, "debug", false, "Enable debug logging")
}

type Config struct {
	Debug       bool     `toml:"debug"`
	Server      string   `toml:"server"`
	AccessToken string   `toml:"access_token"`
	NatsURLs    []string `toml:"nats_urls"`
}

// Validate implements agent.Configurable interface
func (c *Config) Validate() error {
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
	client *mastodon.Client
	nc     *nats.Conn
	js     nats.JetStreamContext
	acc    *mastodon.Account
	server string // Add server URL from config
}

func newMastodonService(cfg *Config) (*MastodonService, error) {
	if cfg.Debug {
		log.Printf("DEBUG: Connecting to Mastodon server: %s", cfg.Server)
	}

	// Connect to mastodon
	client := mastodon.NewClient(&mastodon.Config{
		Server:      cfg.Server,
		AccessToken: cfg.AccessToken,
	})

	// Connect to NATS
	nc, err := nats.Connect(strings.Join(cfg.NatsURLs, ","))
	if err != nil {
		return nil, err
	}

	// Create JetStream context
	js, err := nc.JetStream()
	if err != nil {
		return nil, err
	}

	// Create stream
	_, err = js.AddStream(&nats.StreamConfig{
		Name:     "MASTODON",
		Subjects: []string{"mastodon.stream.>"},
	})
	if err != nil && err != nats.ErrStreamNameAlreadyInUse {
		return nil, err
	}

	svc := &MastodonService{
		client: client,
		nc:     nc,
		js:     js,
		server: cfg.Server,
	}

	// Get account info
	acc, err := client.GetAccountCurrentUser(context.Background())
	if err != nil {
		return nil, err
	}
	svc.acc = acc

	if cfg.Debug {
		log.Printf("DEBUG: Logged in as %s", acc.Acct)
		log.Printf("DEBUG: Account stats - Following: %d, Followers: %d, Posts: %d",
			acc.FollowingCount, acc.FollowersCount, acc.StatusesCount)
	}

	return svc, nil
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
				if debug {
					log.Printf("DEBUG: Reconnection attempt %d after %v delay", attempt, delay)
				}
				time.Sleep(delay)
				// Update delay with exponential backoff
				delay = time.Duration(math.Min(
					float64(delay)*2,
					float64(maxRetryDelay),
				))
			}

			eventChan, err = s.client.StreamingUser(ctx)
			if err != nil {
				if debug {
					log.Printf("DEBUG: Connection failed: %v", err)
				}
				attempt++
				continue
			}

			if debug {
				log.Printf("DEBUG: Stream connected successfully after %d attempts", attempt)
			}
			return eventChan, nil
		}
	}
}

func (s *MastodonService) streamHomeTimeline(ctx context.Context) {
	if debug {
		log.Printf("DEBUG: Starting home timeline stream")
	}

	for {
		select {
		case <-ctx.Done():
			if debug {
				log.Printf("DEBUG: Stream shutting down")
			}
			return
		default:
			eventChan, err := s.connectWithRetry(ctx)
			if err != nil {
				log.Printf("Error connecting to stream: %v", err)
				return
			}

			// Handle events until connection breaks
			for event := range eventChan {
				if debug {
					log.Printf("DEBUG: Received event type: %T", event)
				}

				switch e := event.(type) {
				case *mastodon.UpdateEvent:
					subject := "mastodon.stream." + s.getDomain() + "." + s.acc.Username + ".timeline.home"
					if debug {
						log.Printf("DEBUG: Publishing status from @%s to %s", e.Status.Account.Username, subject)
					}

					payload, err := json.Marshal(e.Status)
					if err != nil {
						log.Printf("Error marshaling status: %v", err)
						continue
					}

					if _, err := s.js.Publish(subject, payload); err != nil {
						log.Printf("Error publishing: %v", err)
					}
				case *mastodon.ErrorEvent:
					log.Printf("Stream error: %v", e.Error())
				case nil:
					// Connection closed
					if debug {
						log.Printf("DEBUG: Stream connection closed, attempting reconnection")
					}
					goto reconnect
				}
			}

		reconnect:
			if debug {
				log.Printf("DEBUG: Stream disconnected, attempting reconnection")
			}
		}
	}
}

func (s *MastodonService) handlePost(req micro.Request) {
	text := string(req.Data())
	if text == "" {
		req.Error("400", "Post text cannot be empty", []byte("empty post text"))
		return
	}

	if debug {
		log.Printf("DEBUG: Posting status: %s", text)
	}

	status, err := s.client.PostStatus(context.Background(), &mastodon.Toot{
		Status: text,
	})
	if err != nil {
		req.Error("500", "Failed to post status", []byte(err.Error()))
		return
	}

	req.Respond([]byte(status.URL))
}

func main() {
	configFile, err := agent.FindConfigFile("mastodon-agent")
	if err != nil {
		log.Fatal(err)
	}

	cfg, err := agent.LoadConfig[*Config](configFile)
	if err != nil {
		log.Fatal(err)
	}

	debug = cfg.Debug // Set global debug flag

	if debug {
		log.Printf("DEBUG: Debug logging enabled")
		log.Printf("DEBUG: Using config file: %s", configFile)
	}

	svc, err := newMastodonService(cfg)
	if err != nil {
		log.Fatal(err)
	}

	// Create NATS micro service
	srv, err := micro.AddService(svc.nc, micro.Config{
		Name:    "mastodon",
		Version: "1.0.0",
		Metadata: map[string]string{
			"account_id":       string(svc.acc.ID),
			"account_username": svc.acc.Username,
			"instance":         svc.getDomain(),
			"followers_count":  strconv.FormatInt(svc.acc.FollowersCount, 10),
			"following_count":  strconv.FormatInt(svc.acc.FollowingCount, 10),
			"statuses_count":   strconv.FormatInt(svc.acc.StatusesCount, 10),
		},
		Endpoint: &micro.EndpointConfig{
			// Only subscribe to exact instance+username combination
			Subject: fmt.Sprintf("mastodon.post.%s.%s.now", svc.getDomain(), svc.acc.Username),
			Handler: micro.HandlerFunc(svc.handlePost),
		},
	})
	if err != nil {
		log.Fatal(err)
	}
	defer srv.Stop()

	// Start streaming timeline
	go svc.streamHomeTimeline(context.Background())

	// Keep running
	select {}
}
