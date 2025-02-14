package agent

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/micro"
)

// Service defines the interface for a Zycelium service
type Service interface {
	Name() string
	Version() string
	Init(context.Context) error
	Start(context.Context) error
	Stop(context.Context) error
}

// BaseService provides common service functionality
type BaseService struct {
	name     string
	version  string
	nc       *nats.Conn
	js       nats.JetStreamContext
	srv      micro.Service
	handlers map[string]micro.Handler
	metadata map[string]string
}

// JetStream returns the JetStream context
func (s *BaseService) JetStream() nats.JetStreamContext {
	return s.js
}

// NATS returns the NATS connection
func (s *BaseService) NATS() *nats.Conn {
	return s.nc
}

// ServiceOption allows configuring BaseService
type ServiceOption func(*BaseService)

// WithVersion sets service version
func WithVersion(version string) ServiceOption {
	return func(s *BaseService) {
		s.version = version
	}
}

// WithMetadata adds metadata to service
func WithMetadata(metadata map[string]string) ServiceOption {
	return func(s *BaseService) {
		s.metadata = metadata
	}
}

// NewService creates a new base service
func NewService(name string, natsURLs []string, opts ...ServiceOption) (*BaseService, error) {
	if err := ValidateName(name); err != nil {
		return nil, err
	}

	nc, err := nats.Connect(strings.Join(natsURLs, ","))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	js, err := nc.JetStream()
	if err != nil {
		return nil, fmt.Errorf("failed to get JetStream context: %w", err)
	}

	svc := &BaseService{
		name:     name,
		version:  "0.0.0",
		nc:       nc,
		js:       js,
		handlers: make(map[string]micro.Handler),
		metadata: make(map[string]string),
	}

	for _, opt := range opts {
		opt(svc)
	}

	return svc, nil
}

// AddHandler adds a NATS micro handler
func (s *BaseService) AddHandler(subject string, handler micro.Handler) error {
	if err := ValidateSubject(subject); err != nil {
		return err
	}
	s.handlers[subject] = handler
	return nil
}

// SetMetadata sets the service metadata
func (s *BaseService) SetMetadata(metadata map[string]string) {
	for k, v := range metadata {
		s.metadata[k] = v
	}
}

// initJetStream creates required streams if they don't exist
func (s *BaseService) initJetStream() error {
	// Create stream for service events
	streamName := MakeKVBucketName(s.name, "EVENTS") // Use same naming convention as KV
	stream, err := s.js.StreamInfo(streamName)

	if err != nil {
		// Create if doesn't exist
		_, err = s.js.AddStream(&nats.StreamConfig{
			Name:        streamName,
			Description: fmt.Sprintf("Events for %s service", s.name),
			Subjects:    []string{fmt.Sprintf("%s.>", s.name)}, // Capture all service events
			MaxAge:      24 * time.Hour,                        // Retain for 24 hours
			Storage:     nats.FileStorage,
		})
		if err != nil {
			return fmt.Errorf("failed to create stream: %w", err)
		}
	} else {
		// Update existing stream if needed
		needsUpdate := false
		config := stream.Config

		// Add any missing subjects
		subject := fmt.Sprintf("%s.>", s.name)
		hasSubject := false
		for _, s := range config.Subjects {
			if s == subject {
				hasSubject = true
				break
			}
		}
		if !hasSubject {
			config.Subjects = append(config.Subjects, subject)
			needsUpdate = true
		}

		if needsUpdate {
			_, err = s.js.UpdateStream(&config)
			if err != nil {
				return fmt.Errorf("failed to update stream: %w", err)
			}
		}
	}

	return nil
}

// MakeSubject generates a standardized subject for this service
func (s *BaseService) MakeSubject(parts ...string) string {
	return MakeSubject(parts...)
}

// Init initializes the service
func (s *BaseService) Init(ctx context.Context) error {
	// Initialize JetStream first
	if err := s.initJetStream(); err != nil {
		return err
	}

	srv, err := micro.AddService(s.nc, micro.Config{
		Name:     s.name,
		Version:  s.version,
		Metadata: s.metadata,
	})
	if err != nil {
		return fmt.Errorf("failed to create micro service: %w", err)
	}

	// Add handlers to service using correct method signature
	for subject, handler := range s.handlers {
		// Use simplified name for endpoint, but keep full subject
		name := MakeHandlerName(subject)
		if err := srv.AddEndpoint(name, handler, micro.WithEndpointSubject(subject)); err != nil {
			return fmt.Errorf("failed to add endpoint %s: %w", subject, err)
		}
	}

	s.srv = srv
	return nil
}

// Start starts the service
func (s *BaseService) Start(ctx context.Context) error {
	return nil
}

// Stop stops the service
func (s *BaseService) Stop(ctx context.Context) error {
	if s.srv != nil {
		s.srv.Stop()
	}
	if s.nc != nil {
		s.nc.Close()
	}
	return nil
}

// Run initializes and runs the service until context is canceled
func (s *BaseService) Run(ctx context.Context) error {
	// Initialize service
	if err := s.Init(ctx); err != nil {
		return fmt.Errorf("failed to initialize service: %w", err)
	}

	// Start service
	if err := s.Start(ctx); err != nil {
		return fmt.Errorf("failed to start service: %w", err)
	}

	// Wait for context cancellation
	<-ctx.Done()

	// Stop service
	if err := s.Stop(ctx); err != nil {
		return fmt.Errorf("failed to stop service: %w", err)
	}

	return nil
}
