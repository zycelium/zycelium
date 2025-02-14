package agent

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	// validNameRe defines valid characters for names
	validNameRe = regexp.MustCompile(`^[a-zA-Z][a-zA-Z0-9_-]*$`)
	// validSubjectRe defines valid characters for NATS subjects
	validSubjectRe = regexp.MustCompile(`^[-/_=\.a-zA-Z0-9]+$`)
)

// ValidateName checks if a name is valid
func ValidateName(name string) error {
	if !validNameRe.MatchString(name) {
		return fmt.Errorf("invalid name format: %s (must start with letter, contain only letters, numbers, underscore, hyphen)", name)
	}
	return nil
}

// ValidateSubject checks if a NATS subject is valid
func ValidateSubject(subject string) error {
	if !validSubjectRe.MatchString(subject) {
		return fmt.Errorf("invalid subject format: %s", subject)
	}
	return nil
}

// MakeKVBucketName generates a standardized KV bucket name
func MakeKVBucketName(name, purpose string) string {
	parts := []string{strings.ToLower(name), strings.ToLower(purpose)}
	return strings.Join(parts, "_")
}

// MakeHandlerName generates a standardized handler name from a subject
func MakeHandlerName(subject string) string {
	return strings.ReplaceAll(subject, ".", "_")
}

// MakeSubject generates a standardized subject for a service
func MakeSubject(parts ...string) string {
	return strings.Join(parts, ".")
}
