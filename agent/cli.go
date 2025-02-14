package agent

import (
	"flag"
	"fmt"
	"log"
)

// Options holds common CLI options
type Options struct {
	ConfigFile string
	Debug      bool
}

// ParseFlags parses command line flags and loads config
func ParseFlags[T Configurable](name string) (T, *Options, error) {
	opts := &Options{}
	flag.BoolVar(&opts.Debug, "debug", false, "Enable debug logging")
	flag.Parse()

	// Find config file
	configFile, err := FindConfigFile(name)
	if err != nil {
		var zero T
		return zero, nil, err
	}
	opts.ConfigFile = configFile

	if opts.Debug {
		log.Printf("DEBUG: Using config file: %s", configFile)
	}

	// Load config
	cfg, err := LoadConfig[T](configFile)
	if err != nil {
		var zero T
		return zero, nil, fmt.Errorf("failed to load config: %w", err)
	}

	return cfg, opts, nil
}
