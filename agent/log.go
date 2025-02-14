package agent

import (
	"log"
)

// Logger provides logging interface
type Logger interface {
	Debug(format string, v ...interface{})
	Info(format string, v ...interface{})
	Error(format string, v ...interface{})
}

// DefaultLogger implements basic logging
type DefaultLogger struct {
	debug bool
}

// NewLogger creates a new logger
func NewLogger(debug bool) Logger {
	return &DefaultLogger{debug: debug}
}

func (l *DefaultLogger) Debug(format string, v ...interface{}) {
	if l.debug {
		log.Printf("DEBUG: "+format, v...)
	}
}

func (l *DefaultLogger) Info(format string, v ...interface{}) {
	log.Printf("INFO: "+format, v...)
}

func (l *DefaultLogger) Error(format string, v ...interface{}) {
	log.Printf("ERROR: "+format, v...)
}
