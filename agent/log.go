package agent

import (
	"fmt"
	"log/slog"
	"os"
)

// Logger provides logging interface
type Logger interface {
	Debug(format string, v ...interface{})
	Info(format string, v ...interface{})
	Warning(format string, v ...interface{})
	Error(format string, v ...interface{})
}

// DefaultLogger implements basic logging
type DefaultLogger struct {
	logger *slog.Logger
	debug  bool
}

// NewLogger creates a new logger
func NewLogger(debug bool) Logger {
	opts := &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}
	if debug {
		opts.Level = slog.LevelDebug
	}

	handler := slog.NewTextHandler(os.Stdout, opts)
	logger := slog.New(handler)

	return &DefaultLogger{
		logger: logger,
		debug:  debug,
	}
}

func (l *DefaultLogger) Debug(format string, v ...interface{}) {
	if l.debug {
		l.logger.Debug(fmt.Sprintf(format, v...))
	}
}

func (l *DefaultLogger) Info(format string, v ...interface{}) {
	l.logger.Info(fmt.Sprintf(format, v...))
}

func (l *DefaultLogger) Warning(format string, v ...interface{}) {
	l.logger.Warn(fmt.Sprintf(format, v...))
}

func (l *DefaultLogger) Error(format string, v ...interface{}) {
	l.logger.Error(fmt.Sprintf(format, v...))
}
