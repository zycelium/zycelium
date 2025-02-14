package agent

import (
	"flag"
	"fmt"
	"log"
	"reflect"
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

	// Load config
	cfg, err := LoadConfig[T](configFile)
	if err != nil {
		var zero T
		return zero, nil, fmt.Errorf("failed to load config: %w", err)
	}

	// Check if config has Debug field and merge with CLI option
	val := reflect.ValueOf(&cfg).Elem()
	if debugField := val.FieldByName("Debug"); debugField.IsValid() && debugField.Kind() == reflect.Bool {
		opts.Debug = opts.Debug || debugField.Bool()
	}

	if opts.Debug {
		log.Printf("DEBUG: Using config file: %s", configFile)
	}

	return cfg, opts, nil
}
