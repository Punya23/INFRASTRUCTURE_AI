// Command api serves the read-only investor API (api/openapi.yaml) from the fixtures in -data.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
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
	defaultCORSOrigin = "http://localhost:8765" // the web dev server (.claude/launch.json)
	defaultRate       = 120                     // requests per client per minute
	shutdownTimeout   = 10 * time.Second
)

func main() {
	if err := run(); err != nil {
		slog.Error("api failed", "err", err)
		os.Exit(1)
	}
}

func run() error {
	addr := flag.String("addr", ":8080", "listen address")
	data := flag.String("data", "../web/fixtures/invest", "directory holding the investor fixtures")
	flag.Parse()

	rate, err := rateFromEnv(os.Getenv("INVEST_RATE_LIMIT"))
	if err != nil {
		return err
	}
	origins := originsFromEnv(os.Getenv("INVEST_CORS_ORIGINS"))

	// Loading parses every fixture (and validates it), which takes several seconds on the full dataset.
	slog.Info("loading fixtures", "dir", *data)
	began := time.Now()
	st, err := store.Load(*data)
	if err != nil {
		return fmt.Errorf("load fixtures: %w", err)
	}
	cities, areas := st.Cities(), 0
	for _, c := range cities {
		if a, ok := st.Areas(c.ID); ok {
			areas += len(a.Features)
		}
	}
	slog.Info("fixtures loaded", "cities", len(cities), "areas", areas, "as_of", st.Meta().AsOf,
		"took", time.Since(began).Round(time.Millisecond).String())

	srv := &http.Server{
		Addr:              *addr,
		Handler:           httpapi.New(st, httpapi.Config{CORSOrigins: origins, RatePerMinute: rate}),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.ListenAndServe() }()
	slog.Info("listening", "addr", *addr, "cors_origins", origins, "rate_per_minute", rate)

	select {
	case err := <-serveErr: // never ErrServerClosed here: Shutdown has not been called yet
		return fmt.Errorf("serve: %w", err)
	case <-ctx.Done():
	}
	stop() // a second signal now kills the process instead of waiting for the drain

	slog.Info("shutting down")
	shutCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("serve: %w", err)
	}
	return nil
}

// rateFromEnv parses INVEST_RATE_LIMIT. Unset means the default; a value that is not a positive integer is an
// error, so a typo cannot silently leave the limiter at a rate nobody chose.
func rateFromEnv(v string) (int, error) {
	if v == "" {
		return defaultRate, nil
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 1 {
		return 0, fmt.Errorf("INVEST_RATE_LIMIT %q: want a positive integer", v)
	}
	return n, nil
}

// originsFromEnv splits INVEST_CORS_ORIGINS on commas, dropping blanks. Unset or all blank means the dev web
// server.
func originsFromEnv(v string) []string {
	var out []string
	for _, o := range strings.Split(v, ",") {
		if o = strings.TrimSpace(o); o != "" {
			out = append(out, o)
		}
	}
	if len(out) == 0 {
		return []string{defaultCORSOrigin}
	}
	return out
}
