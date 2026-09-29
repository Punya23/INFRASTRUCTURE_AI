// Command api serves the investor API (api/openapi.yaml) from the fixture directory written by
// `cd ml && uv run python -m pipeline.invest all`. Data loads once at start; a missing or malformed
// fixture stops the process with a clear message (fail closed).
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	httpapi "github.com/Punya23/INFRASTRUCTURE_AI/api/internal/http"
	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

const (
	defaultOrigin = "http://localhost:8765" // the dev web server (python3 -m http.server 8765 --directory web)
	defaultRate   = 120                     // requests per client per minute
)

func main() {
	if err := run(os.Args[1:], os.Getenv, os.Stderr); err != nil {
		fmt.Fprintln(os.Stderr, "api:", err)
		os.Exit(1)
	}
}

// run parses flags and environment, loads the data and serves until SIGINT or SIGTERM.
func run(args []string, getenv func(string) string, logOut io.Writer) error {
	fs := flag.NewFlagSet("api", flag.ContinueOnError)
	addr := fs.String("addr", ":8080", "listen address")
	dataDir := fs.String("data", "../web/fixtures/invest", "fixture directory (meta.json, states.json, cities.json, areas/, assets/)")
	if err := fs.Parse(args); err != nil {
		return err
	}
	cfg, err := configFromEnv(getenv)
	if err != nil {
		return err
	}
	log := slog.New(slog.NewTextHandler(logOut, nil))

	st, err := store.Load(*dataDir)
	if err != nil {
		return fmt.Errorf("cannot load %s: %w", *dataDir, err)
	}
	areas := 0
	for _, c := range st.Cities() {
		if a, ok := st.Areas(c.ID); ok {
			areas += len(a.Features)
		}
	}
	log.Info("data loaded", "dir", *dataDir, "cities", len(st.Cities()), "areas", areas, "as_of", st.Meta().AsOf)

	srv := &http.Server{
		Addr:              *addr,
		Handler:           httpapi.New(st, cfg),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	failed := make(chan error, 1)
	go func() {
		log.Info("listening", "addr", *addr, "cors", cfg.CORSOrigins, "rate_per_minute", cfg.RatePerMinute)
		failed <- srv.ListenAndServe()
	}()

	select {
	case err := <-failed:
		if !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	case <-ctx.Done():
		log.Info("shutting down")
		shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdown); err != nil {
			return fmt.Errorf("shutdown: %w", err)
		}
	}
	return nil
}

// configFromEnv reads INVEST_CORS_ORIGINS (comma-separated exact origins) and INVEST_RATE_LIMIT.
// A rate that is not a positive integer is an error, not a silent default.
func configFromEnv(getenv func(string) string) (httpapi.Config, error) {
	cfg := httpapi.Config{CORSOrigins: []string{defaultOrigin}, RatePerMinute: defaultRate}
	if v := strings.TrimSpace(getenv("INVEST_CORS_ORIGINS")); v != "" {
		cfg.CORSOrigins = nil
		for _, o := range strings.Split(v, ",") {
			if o = strings.TrimSpace(o); o != "" {
				cfg.CORSOrigins = append(cfg.CORSOrigins, o)
			}
		}
	}
	if v := strings.TrimSpace(getenv("INVEST_RATE_LIMIT")); v != "" {
		n, err := strconv.Atoi(v)
		if err != nil || n < 1 {
			return cfg, fmt.Errorf("INVEST_RATE_LIMIT must be a positive integer, got %q", v)
		}
		cfg.RatePerMinute = n
	}
	return cfg, nil
}
