package main

import (
	"io"
	"path/filepath"
	"strings"
	"testing"
)

func env(m map[string]string) func(string) string { return func(k string) string { return m[k] } }

func TestConfigFromEnv(t *testing.T) {
	cfg, err := configFromEnv(env(nil))
	if err != nil || cfg.RatePerMinute != 120 || len(cfg.CORSOrigins) != 1 || cfg.CORSOrigins[0] != "http://localhost:8765" {
		t.Fatalf("defaults wrong: %+v, %v", cfg, err)
	}
	cfg, err = configFromEnv(env(map[string]string{
		"INVEST_CORS_ORIGINS": " https://a.example , ,https://b.example ", "INVEST_RATE_LIMIT": "30"}))
	if err != nil || cfg.RatePerMinute != 30 || strings.Join(cfg.CORSOrigins, "|") != "https://a.example|https://b.example" {
		t.Fatalf("overrides wrong: %+v, %v", cfg, err)
	}
	for _, bad := range []string{"0", "-5", "abc", "1.5"} {
		if _, err := configFromEnv(env(map[string]string{"INVEST_RATE_LIMIT": bad})); err == nil {
			t.Errorf("INVEST_RATE_LIMIT=%q should be rejected, not defaulted", bad)
		}
	}
}

func TestRunFailsClosedOnMissingOrCorruptData(t *testing.T) {
	err := run([]string{"-data", filepath.Join(t.TempDir(), "nope")}, env(nil), io.Discard)
	if err == nil || !strings.Contains(err.Error(), "cannot load") {
		t.Fatalf("a missing data directory must stop start-up with a clear error, got %v", err)
	}
	if err := run([]string{"-bogus"}, env(nil), io.Discard); err == nil {
		t.Fatal("an unknown flag must be an error")
	}
	if err := run([]string{"-data", t.TempDir()}, env(map[string]string{"INVEST_RATE_LIMIT": "x"}), io.Discard); err == nil {
		t.Fatal("a bad rate limit must be an error before any data is read")
	}
}
