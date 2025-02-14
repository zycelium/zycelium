package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/nats-io/nats.go/micro"
	"github.com/zycelium/zycelium/agent"
)

type Config struct {
	Debug      bool     `toml:"debug"`
	NatsURLs   []string `toml:"nats_urls"`
	Capitalize bool     `toml:"capitalize"` // Add capitalize option
}

// Validate implements agent.Configurable interface
func (c Config) Validate() error {
	if len(c.NatsURLs) == 0 {
		return fmt.Errorf("at least one NATS URL is required")
	}
	return nil
}

type HelloService struct {
	*agent.BaseService
	logger     agent.Logger
	capitalize bool // Track current setting
}

func NewHelloService(cfg Config, opts *agent.Options) (*HelloService, error) {
	// Create base service
	base, err := agent.NewService("hello", cfg.NatsURLs,
		agent.WithVersion("1.0.0"),
	)
	if err != nil {
		return nil, err
	}

	svc := &HelloService{
		BaseService: base,
		logger:      agent.NewLogger(opts.Debug),
		capitalize:  cfg.Capitalize, // Initialize from config
	}

	// Add handler for hello subject
	subject := agent.MakeSubject("hello")
	svc.logger.Debug("Registering handler for subject: %s", subject)
	if err := base.AddHandler(subject, micro.HandlerFunc(svc.handleHello)); err != nil {
		return nil, fmt.Errorf("failed to add handler: %w", err)
	}

	return svc, nil
}

func (s *HelloService) handleHello(req micro.Request) {
	name := string(req.Data())
	if name == "" {
		name = "World"
	}

	response := fmt.Sprintf("Hello, %s!", name)
	if s.capitalize {
		response = strings.ToUpper(response)
	}

	s.logger.Debug("Received hello request for: %s (capitalize=%v)", name, s.capitalize)
	req.Respond([]byte(response))
}

func main() {
	// Parse flags and load config
	cfg, opts, err := agent.ParseFlags[Config]("hello-agent")
	if err != nil {
		log.Fatal(err)
	}

	// Create service
	svc, err := NewHelloService(cfg, opts)
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

	// Sync config with NATS KV store first
	if err := agent.SyncConfig(svc.BaseService.NATS(), "hello", cfg); err != nil {
		log.Printf("WARNING: Failed to sync config: %v", err)
	}

	// Now setup config watching
	if err := agent.WatchConfigKeys(ctx, svc.BaseService.NATS(), "hello", []string{"capitalize"}, func(e agent.ConfigEvent) {
		if val, ok := e.Value.(bool); ok {
			svc.logger.Debug("Updating capitalize setting to: %v", val)
			svc.capitalize = val
		}
	}); err != nil {
		log.Fatal(err)
	}

	// Run service until context is canceled
	if err := svc.Run(ctx); err != nil {
		log.Fatal(err)
	}
}
