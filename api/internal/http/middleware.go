package httpapi

import (
	"log/slog"
	"math"
	"net"
	"net/http"
	"runtime/debug"
	"strconv"
	"strings"
	"sync"
	"time"
)

// withRecover turns a panic anywhere below it into a 500 that says nothing about the cause; the panic value
// and the stack go to the log, so nothing is swallowed.
func withRecover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				slog.Error("panic while serving a request",
					"method", r.Method, "path", r.URL.Path, "panic", v, "stack", string(debug.Stack()))
				writeError(w, http.StatusInternalServerError, "internal", "internal error")
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// withHeaders sets X-Content-Type-Options on every response and marks the data routes (/v1/...) cacheable
// for five minutes. An error replaces that: see writeError and stampErrors.
func withHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h := w.Header()
		h.Set("X-Content-Type-Options", "nosniff")
		if strings.HasPrefix(r.URL.Path, "/v1/") {
			h.Set("Cache-Control", "public, max-age=300")
		}
		next.ServeHTTP(w, r)
	})
}

// withCORS lets a browser page served from one of origins (exact match, like "http://localhost:8765") read
// the responses, and answers preflights itself. It sits before the rate limit so a page can also read its
// 429.
func withCORS(origins []string) func(http.Handler) http.Handler {
	allowed := make(map[string]bool, len(origins))
	for _, o := range origins {
		allowed[o] = true
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			h := w.Header()
			h.Add("Vary", "Origin") // the answer depends on the Origin header: shared caches must key on it
			if o := r.Header.Get("Origin"); o != "" && allowed[o] {
				h.Set("Access-Control-Allow-Origin", o)
			}
			if r.Method == http.MethodOptions {
				h.Set("Access-Control-Allow-Methods", "GET, OPTIONS")
				w.WriteHeader(http.StatusNoContent)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// maxClients bounds the rate limiter's table.
const maxClients = 10_000

// withRateLimit allows perMinute requests per client in each fixed one-minute window, which starts with the
// client's first request. A client is the host of RemoteAddr. now is the clock (nil: time.Now).
//
// ponytail: fixed window, so a client can burst up to twice the rate across a window edge; the table is
// emptied when it reaches maxClients, so a flood of addresses makes the limiter forget instead of grow; behind
// a proxy every client shares the proxy's address. Upgrade to a sliding window and a trusted forwarded-for
// header when the API is deployed behind one.
func withRateLimit(perMinute int, now func() time.Time) func(http.Handler) http.Handler {
	if now == nil {
		now = time.Now
	}
	type window struct {
		start time.Time
		n     int
	}
	var (
		mu      sync.Mutex
		clients = map[string]*window{}
	)
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			key := r.RemoteAddr
			if host, _, err := net.SplitHostPort(key); err == nil {
				key = host
			}
			t := now()

			mu.Lock()
			win := clients[key]
			if win == nil || t.Sub(win.start) >= time.Minute {
				if win == nil && len(clients) >= maxClients {
					clear(clients)
				}
				win = &window{start: t}
				clients[key] = win
			}
			win.n++
			limited := win.n > perMinute
			retry := win.start.Add(time.Minute).Sub(t)
			mu.Unlock()

			if limited {
				w.Header().Set("Retry-After", strconv.Itoa(int(math.Ceil(retry.Seconds()))))
				writeError(w, http.StatusTooManyRequests, "rate_limited", "too many requests; retry later")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// timeoutBody is what http.TimeoutHandler writes when a request runs out of time.
var timeoutBody = errorBody("timeout", "the request took too long")

// withTimeout answers 503 {"error":{"code":"timeout"}} to a request whose handler is still running after d,
// and cancels the handler's context.
func withTimeout(d time.Duration) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		th := http.TimeoutHandler(next, d, timeoutBody)
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { th.ServeHTTP(stampErrors{w}, r) })
	}
}

// stampErrors gives the 503 the JSON content type and no-store on its way out. http.TimeoutHandler writes that
// answer itself, straight to the connection, so neither writeError nor the handler's own headers reach it.
type stampErrors struct{ http.ResponseWriter }

func (w stampErrors) WriteHeader(code int) {
	if code == http.StatusServiceUnavailable {
		errorHeaders(w.Header())
	}
	w.ResponseWriter.WriteHeader(code)
}
