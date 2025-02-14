package agent

import (
	"fmt"

	"github.com/nats-io/nats.go/micro"
)

// Endpoint represents a service endpoint
type Endpoint struct {
	Name        string
	Subject     string
	Handler     micro.Handler
	Description string
}

// RegisterEndpoint registers an endpoint with the micro service
func (s *BaseService) RegisterEndpoint(e Endpoint) error {
	if s.srv == nil {
		return fmt.Errorf("service not initialized")
	}

	opts := []micro.EndpointOpt{
		micro.WithEndpointSubject(e.Subject),
	}
	if e.Description != "" {
		opts = append(opts, micro.WithEndpointMetadata(map[string]string{
			"description": e.Description,
		}))
	}

	if err := s.srv.AddEndpoint(e.Name, e.Handler, opts...); err != nil {
		return fmt.Errorf("failed to add endpoint %s: %w", e.Name, err)
	}

	return nil
}
