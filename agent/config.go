package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"strings"
	"time"

	"github.com/BurntSushi/toml"
	"github.com/nats-io/nats.go"
)

// Configurable interface ensures that configs implement validation
type Configurable interface {
	Validate() error
}

// loadConfig loads and decodes a TOML config file into the provided struct type T
func LoadConfig[T Configurable](path string) (T, error) {
	var config T
	if _, err := toml.DecodeFile(path, &config); err != nil {
		return config, err
	}
	if err := config.Validate(); err != nil {
		return config, err
	}
	return config, nil
}

func FindConfigFile(name string) (string, error) {
	// Try current directory first
	if _, err := os.Stat(name + ".conf"); err == nil {
		return name + ".conf", nil
	}

	// Get config directory based on OS
	var configDir string
	switch runtime.GOOS {
	case "windows":
		configDir = os.Getenv("APPDATA")
	case "darwin":
		configDir = filepath.Join(os.Getenv("HOME"), "Library", "Application Support")
	default: // linux, freebsd, etc.
		if xdgHome := os.Getenv("XDG_CONFIG_HOME"); xdgHome != "" {
			configDir = xdgHome
		} else {
			configDir = filepath.Join(os.Getenv("HOME"), ".config")
		}
	}

	configFile := filepath.Join(configDir, "zycelium", name+".conf")
	if _, err := os.Stat(configFile); err == nil {
		return configFile, nil
	}

	return "", fmt.Errorf("config file not found for service: %s", name)
}

// validKeyRe defines valid characters for KV store keys
var validKeyRe = regexp.MustCompile(`^[-/_=\.a-zA-Z0-9]+$`)

// SyncConfig synchronizes configuration with NATS KV store
func SyncConfig[T Configurable](nc *nats.Conn, name string, config *T) error {
	js, err := nc.JetStream()
	if err != nil {
		return fmt.Errorf("failed to get JetStream context: %w", err)
	}

	bucketName := fmt.Sprintf("zycelium.agent.%s.config", name)
	kv, err := js.KeyValue(bucketName)
	if err != nil {
		// Try to create if doesn't exist
		kv, err = js.CreateKeyValue(&nats.KeyValueConfig{
			Bucket:       bucketName,
			Description:  fmt.Sprintf("Configuration for Zycelium agent %s", name),
			MaxValueSize: 1048576, // 1MB max value size
			History:      1,       // Keep only latest value
			Storage:      nats.FileStorage,
		})
		if err != nil {
			return fmt.Errorf("failed to create/get KV bucket: %w", err)
		}
	}

	// Convert config to map using reflection
	configMap := make(map[string]interface{})
	val := reflect.ValueOf(config).Elem()

	var process func(reflect.Value, string)
	process = func(v reflect.Value, prefix string) {
		t := v.Type()
		for i := 0; i < v.NumField(); i++ {
			field := v.Field(i)
			fieldType := t.Field(i)

			// Skip unexported fields
			if !fieldType.IsExported() {
				continue
			}

			key := fieldType.Tag.Get("toml")
			if key == "" {
				key = strings.ToLower(fieldType.Name)
			}

			if prefix != "" {
				key = prefix + "." + key
			}

			// Validate key format
			if !validKeyRe.MatchString(key) {
				continue
			}

			// Handle embedded structs
			if field.Kind() == reflect.Struct {
				process(field, key)
				continue
			}

			// Store value
			configMap[key] = field.Interface()
		}
	}
	process(val, "")

	// Sync each key-value pair
	for key, value := range configMap {
		// Convert value to JSON for storage
		jsonValue, err := json.Marshal(value)
		if err != nil {
			return fmt.Errorf("failed to marshal value for key %s: %w", key, err)
		}

		// Try to put the value, create if it doesn't exist
		_, err = kv.Get(key)
		if err != nil {
			if errors.Is(err, nats.ErrKeyNotFound) {
				if _, err := kv.Create(key, jsonValue); err != nil {
					if errors.Is(err, nats.ErrKeyExists) {
						// Race condition - key was created between Get and Create
						if _, err := kv.Put(key, jsonValue); err != nil {
							return fmt.Errorf("failed to update key %s: %w", key, err)
						}
					} else {
						return fmt.Errorf("failed to create key %s: %w", key, err)
					}
				}
			} else {
				return fmt.Errorf("failed to check key %s: %w", key, err)
			}
		}
	}

	return nil
}

// ConfigEvent represents a configuration change event
type ConfigEvent struct {
	Key      string
	Value    interface{}
	Revision uint64
	Created  time.Time
}

// WatchConfig monitors configuration changes and calls the provided callback function
func WatchConfig(ctx context.Context, nc *nats.Conn, name string, callback func(ConfigEvent)) error {
	js, err := nc.JetStream()
	if err != nil {
		return fmt.Errorf("failed to get JetStream context: %w", err)
	}

	bucketName := fmt.Sprintf("zycelium.agent.%s.config", name)
	kv, err := js.KeyValue(bucketName)
	if err != nil {
		return fmt.Errorf("failed to get KV bucket: %w", err)
	}

	watcher, err := kv.WatchAll()
	if err != nil {
		return fmt.Errorf("failed to create watcher: %w", err)
	}

	// Start watching in a goroutine
	go func() {
		defer watcher.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case entry := <-watcher.Updates():
				if entry == nil {
					continue
				}

				// Skip delete operations
				if entry.Operation() == nats.KeyValueDelete {
					continue
				}

				// Unmarshal JSON value
				var value interface{}
				if err := json.Unmarshal(entry.Value(), &value); err != nil {
					// Skip invalid JSON values
					continue
				}

				// Create and send event
				event := ConfigEvent{
					Key:      entry.Key(),
					Value:    value,
					Revision: entry.Revision(),
					Created:  entry.Created(),
				}
				callback(event)
			}
		}
	}()

	return nil
}

// WatchConfigKey monitors specific configuration keys and calls the provided callback function
func WatchConfigKeys(ctx context.Context, nc *nats.Conn, name string, keys []string, callback func(ConfigEvent)) error {
	js, err := nc.JetStream()
	if err != nil {
		return fmt.Errorf("failed to get JetStream context: %w", err)
	}

	bucketName := fmt.Sprintf("zycelium.agent.%s.config", name)
	kv, err := js.KeyValue(bucketName)
	if err != nil {
		return fmt.Errorf("failed to get KV bucket: %w", err)
	}

	// Validate keys
	for _, key := range keys {
		if !validKeyRe.MatchString(key) {
			return fmt.Errorf("invalid key format: %s", key)
		}
	}

	watcher, err := kv.WatchFiltered(keys)
	if err != nil {
		return fmt.Errorf("failed to create watcher: %w", err)
	}

	// Start watching in a goroutine
	go func() {
		defer watcher.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case entry := <-watcher.Updates():
				if entry == nil {
					continue
				}

				// Skip delete operations
				if entry.Operation() == nats.KeyValueDelete {
					continue
				}

				// Unmarshal JSON value
				var value interface{}
				if err := json.Unmarshal(entry.Value(), &value); err != nil {
					// Skip invalid JSON values
					continue
				}

				// Create and send event
				event := ConfigEvent{
					Key:      entry.Key(),
					Value:    value,
					Revision: entry.Revision(),
					Created:  entry.Created(),
				}
				callback(event)
			}
		}
	}()

	return nil
}
