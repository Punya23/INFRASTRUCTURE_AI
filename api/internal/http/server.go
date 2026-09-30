// Package httpapi is the read-only HTTP API of the investor flow (spec section 7, api/openapi.yaml): handlers
// over an in-memory store, wrapped in recovery, security headers, CORS, a per-client rate limit and a
// per-request timeout. Every error, whichever layer makes it, is {"error":{"code","message"}}.
package httpapi

import (
	"net/http"
	"time"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// Defaults for the zero Config values.
const (
	defaultRate    = 120
	defaultTimeout = 5 * time.Second
)

// Config tunes the middleware. The zero value is safe: no browser origin is allowed, a client may make 120
// requests a minute and a request gets 5 seconds.
type Config struct {
	CORSOrigins    []string         // exact origins, like "http://localhost:8765", whose pages may read the responses
	RatePerMinute  int              // requests per client in each fixed one-minute window; 0 means 120
	RequestTimeout time.Duration    // time one request may take before it is answered 503; 0 means 5 s
	Now            func() time.Time // the rate limiter's clock; nil means time.Now (tests inject one)
}

// New returns the API over s. The chain, outermost first: recover, security headers, CORS, rate limit,
// timeout, routes.
func New(s *store.Store, cfg Config) http.Handler {
	rate, timeout := cfg.RatePerMinute, cfg.RequestTimeout
	if rate <= 0 {
		rate = defaultRate
	}
	if timeout <= 0 {
		timeout = defaultTimeout
	}

	a := newAPI(s)
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", a.health)
	mux.HandleFunc("GET /v1/meta", a.meta)
	mux.HandleFunc("GET /v1/states", a.states)
	mux.HandleFunc("GET /v1/states/{code}/cities", a.stateCities)
	mux.HandleFunc("GET /v1/cities", a.search)
	mux.HandleFunc("GET /v1/cities/{id}", a.city)
	mux.HandleFunc("GET /v1/cities/{id}/areas", a.areas)
	mux.HandleFunc("GET /v1/cities/{id}/assets", a.assets)
	mux.HandleFunc("GET /v1/cities/{id}/projects", a.projects)
	mux.HandleFunc("GET /v1/cities/{id}/compare", a.compareCity)
	mux.HandleFunc("/", notFound)

	var h http.Handler = mux
	h = withTimeout(timeout)(h)
	h = withRateLimit(rate, cfg.Now)(h)
	h = withCORS(cfg.CORSOrigins)(h)
	h = withHeaders(h)
	return withRecover(h)
}
