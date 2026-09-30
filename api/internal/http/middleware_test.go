package httpapi

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// ok is the stub the middleware tests wrap.
var ok = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { _, _ = io.WriteString(w, "ok") })

func request(h http.Handler, method, target string, mod func(*http.Request)) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, target, nil)
	if mod != nil {
		mod(req)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func from(addr string) func(*http.Request) { return func(r *http.Request) { r.RemoteAddr = addr } }

// errorCode returns the code of {"error":{"code","message"}} and fails on any other body, on a wrong status,
// a wrong content type, or a response a shared cache could keep.
func errorCode(t *testing.T, rec *httptest.ResponseRecorder, status int) string {
	t.Helper()
	if rec.Code != status {
		t.Fatalf("status = %d, want %d (body %s)", rec.Code, status, rec.Body)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	if cc := rec.Header().Get("Cache-Control"); cc != "no-store" {
		t.Errorf("Cache-Control = %q on an error, want no-store", cc)
	}
	var body struct {
		Error struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	dec := json.NewDecoder(bytes.NewReader(rec.Body.Bytes()))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil || body.Error.Message == "" {
		t.Fatalf("body is not {\"error\":{\"code\",\"message\"}}: %v (%s)", err, rec.Body)
	}
	return body.Error.Code
}

func TestCORS(t *testing.T) {
	h := withCORS([]string{"http://localhost:8765", "https://invest.example.org"})(ok)
	cases := []struct{ name, origin, want string }{
		{"allowed", "http://localhost:8765", "http://localhost:8765"},
		{"second allowed origin", "https://invest.example.org", "https://invest.example.org"},
		{"other origin", "https://evil.example", ""},
		{"same host, other port", "http://localhost:8080", ""},
		{"other scheme", "https://localhost:8765", ""},
		{"trailing text", "http://localhost:8765.evil.example", ""},
		{"sandboxed page", "null", ""},
		{"no Origin header", "", ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := request(h, "GET", "/v1/meta", func(r *http.Request) {
				if tc.origin != "" {
					r.Header.Set("Origin", tc.origin)
				}
			})
			if rec.Code != http.StatusOK || rec.Body.String() != "ok" {
				t.Errorf("a cross-origin GET is still served: %d %q", rec.Code, rec.Body)
			}
			if got := rec.Header().Get("Access-Control-Allow-Origin"); got != tc.want {
				t.Errorf("Access-Control-Allow-Origin = %q, want %q", got, tc.want)
			}
			// the answer depends on the Origin header, so a shared cache must key on it
			if !slices.Contains(rec.Header().Values("Vary"), "Origin") {
				t.Errorf("Vary = %v, want Origin", rec.Header().Values("Vary"))
			}
			if got := rec.Header().Get("Access-Control-Allow-Credentials"); got != "" {
				t.Errorf("Access-Control-Allow-Credentials = %q; the API uses no credentials", got)
			}
		})
	}

	if got := request(withCORS(nil)(ok), "GET", "/v1/meta", func(r *http.Request) {
		r.Header.Set("Origin", "http://localhost:8765")
	}).Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Errorf("no configured origin must mean no CORS header, got %q", got)
	}

	// An empty entry (an empty environment variable split on commas) allows nothing: no empty header either.
	rec := request(withCORS([]string{""})(ok), "GET", "/v1/meta", nil)
	if _, sent := rec.Header()["Access-Control-Allow-Origin"]; sent {
		t.Errorf("a request without Origin got Access-Control-Allow-Origin %q", rec.Header().Get("Access-Control-Allow-Origin"))
	}
}

func TestCORS_preflight(t *testing.T) {
	reached := false
	h := withCORS([]string{"http://localhost:8765"})(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { reached = true }))
	for origin, want := range map[string]string{"http://localhost:8765": "http://localhost:8765", "https://evil.example": ""} {
		rec := request(h, "OPTIONS", "/v1/cities", func(r *http.Request) {
			r.Header.Set("Origin", origin)
			r.Header.Set("Access-Control-Request-Method", "GET")
		})
		if rec.Code != http.StatusNoContent || rec.Body.Len() != 0 {
			t.Errorf("%s: preflight = %d with %d body bytes, want 204 and none", origin, rec.Code, rec.Body.Len())
		}
		if got := rec.Header().Get("Access-Control-Allow-Methods"); got != "GET, OPTIONS" {
			t.Errorf("%s: Allow-Methods = %q, want %q", origin, got, "GET, OPTIONS")
		}
		if got := rec.Header().Get("Access-Control-Allow-Origin"); got != want {
			t.Errorf("%s: Allow-Origin = %q, want %q", origin, got, want)
		}
	}
	if reached {
		t.Error("a preflight must not reach the handler")
	}
}

type clock struct{ t time.Time }

func (c *clock) now() time.Time { return c.t }

func newClock() *clock { return &clock{time.Date(2026, 9, 30, 12, 0, 0, 0, time.UTC)} }

func TestRateLimit(t *testing.T) {
	clk := newClock()
	start := clk.t
	h := withRateLimit(2, clk.now)(ok)
	get := func(addr string) *httptest.ResponseRecorder { return request(h, "GET", "/v1/meta", from(addr)) }

	for i := 1; i <= 2; i++ {
		if rec := get("192.0.2.1:1000"); rec.Code != http.StatusOK {
			t.Fatalf("request %d = %d, want 200", i, rec.Code)
		}
	}
	rec := get("192.0.2.1:1000")
	if code := errorCode(t, rec, http.StatusTooManyRequests); code != "rate_limited" {
		t.Errorf("code = %q, want rate_limited", code)
	}
	if got := rec.Header().Get("Retry-After"); got != "60" {
		t.Errorf("Retry-After = %q, want 60 (the whole window is left)", got)
	}
	if got, want := rec.Body.String(), `{"error":{"code":"rate_limited","message":"too many requests; retry later"}}`; got != want {
		t.Errorf("body = %s, want the OpenAPI example %s", got, want)
	}

	// The client is the host: another port is the same client, another host is not.
	if got := get("192.0.2.1:2000").Code; got != http.StatusTooManyRequests {
		t.Errorf("same host, other port = %d, want 429", got)
	}
	if got := get("192.0.2.2:1000").Code; got != http.StatusOK {
		t.Errorf("other host = %d, want 200", got)
	}
	for i, want := range []int{200, 200, 429} { // IPv6, and an address without a port
		if got := get("[2001:db8::1]:" + fmt.Sprint(1000+i)).Code; got != want {
			t.Errorf("IPv6 request %d = %d, want %d", i+1, got, want)
		}
	}
	if got := get("no-port").Code; got != http.StatusOK {
		t.Errorf("an address without a port = %d, want 200", got)
	}

	// Retry-After counts down with the window; the window is fixed: 60 s after its first request it resets.
	clk.t = start.Add(10 * time.Second)
	if got := get("192.0.2.1:1000").Header().Get("Retry-After"); got != "50" {
		t.Errorf("after 10 s Retry-After = %q, want 50", got)
	}
	clk.t = start.Add(59*time.Second + 900*time.Millisecond)
	rec = get("192.0.2.1:1000")
	if rec.Code != http.StatusTooManyRequests || rec.Header().Get("Retry-After") != "1" {
		t.Errorf("after 59.9 s = %d, Retry-After %q; want 429 and 1", rec.Code, rec.Header().Get("Retry-After"))
	}
	clk.t = start.Add(time.Minute)
	for i, want := range []int{200, 200, 429} {
		if got := get("192.0.2.1:1000").Code; got != want {
			t.Errorf("new window, request %d = %d, want %d", i+1, got, want)
		}
	}
}

// The limiter's bookkeeping is shared by every request: -race checks the lock, the count checks the logic.
func TestRateLimit_concurrent(t *testing.T) {
	t0 := newClock().t
	h := withRateLimit(10, func() time.Time { return t0 })(ok)
	var served atomic.Int32
	var wg sync.WaitGroup
	for range 50 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if request(h, "GET", "/v1/meta", from("192.0.2.1:1")).Code == http.StatusOK {
				served.Add(1)
			}
		}()
	}
	wg.Wait()
	if got := served.Load(); got != 10 {
		t.Errorf("%d of 50 concurrent requests were served, want exactly 10", got)
	}
}

// ponytail ceiling: the table is emptied when it reaches 10,000 clients, so memory stays bounded and a
// flood of addresses can only make the limiter forget, never grow without limit.
func TestRateLimit_tableIsBounded(t *testing.T) {
	t0 := newClock().t
	h := withRateLimit(1, func() time.Time { return t0 })(ok)
	old := from("192.0.2.1:1")
	if request(h, "GET", "/", old).Code != http.StatusOK || request(h, "GET", "/", old).Code != http.StatusTooManyRequests {
		t.Fatal("the first client should be served once, then limited")
	}
	for i := range 10_001 {
		request(h, "GET", "/", from(fmt.Sprintf("10.%d.%d.%d:1", i>>16&255, i>>8&255, i&255)))
	}
	if got := request(h, "GET", "/", old).Code; got != http.StatusOK {
		t.Errorf("the table was never emptied: the first client is still limited (%d)", got)
	}
}

func TestHeaders(t *testing.T) {
	silent := http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}) // writes nothing at all
	for _, tc := range []struct {
		name, path string
		next       http.Handler
		cache      string
	}{
		{"data route", "/v1/meta", ok, "public, max-age=300"},
		{"deeper data route", "/v1/cities/pune/areas", ok, "public, max-age=300"},
		{"handler that writes nothing", "/v1/states", silent, "public, max-age=300"},
		{"health is not cached", "/healthz", ok, ""},
		{"root is not cached", "/", ok, ""},
		{"not a data route", "/v1", ok, ""},
	} {
		t.Run(tc.name, func(t *testing.T) {
			rec := request(withHeaders(tc.next), "GET", tc.path, nil)
			if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
				t.Errorf("X-Content-Type-Options = %q, want nosniff", got)
			}
			if got := rec.Header().Get("Cache-Control"); got != tc.cache {
				t.Errorf("Cache-Control = %q, want %q", got, tc.cache)
			}
		})
	}

	// an error on a data route replaces the cache header: 404s and 400s are never kept
	notFound := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { writeError(w, 404, "not_found", "city not found") })
	rec := request(withHeaders(notFound), "GET", "/v1/cities/nowhere", nil)
	if code := errorCode(t, rec, 404); code != "not_found" {
		t.Errorf("code = %q", code)
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Errorf("nosniff missing on an error: %q", got)
	}
}

// syncBuffer lets the test read what a handler goroutine logged.
type syncBuffer struct {
	mu sync.Mutex
	b  bytes.Buffer
}

func (s *syncBuffer) Write(p []byte) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.b.Write(p)
}

func (s *syncBuffer) String() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.b.String()
}

// captureLogs redirects the default logger into a buffer for the rest of the test.
func captureLogs(t *testing.T) *syncBuffer {
	t.Helper()
	logs := &syncBuffer{}
	prev := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(logs, nil)))
	t.Cleanup(func() { slog.SetDefault(prev) })
	return logs
}

func TestRecover(t *testing.T) {
	logs := captureLogs(t)

	for name, panicWith := range map[string]func(){
		"a string":        func() { panic("secret internal detail") },
		"an error":        func() { panic(errors.New("secret internal detail")) },
		"a runtime error": func() { var m map[string]int; m["secret internal detail"]++ },
		"nil":             func() { panic(nil) },
	} {
		t.Run(name, func(t *testing.T) {
			boom := http.HandlerFunc(func(http.ResponseWriter, *http.Request) { panicWith() })
			var rec *httptest.ResponseRecorder
			func() {
				defer func() {
					if v := recover(); v != nil {
						t.Fatalf("the panic escaped withRecover: %v", v)
					}
				}()
				// withHeaders inside: the eager cache header must not survive on the 500
				rec = request(withRecover(withHeaders(boom)), "GET", "/v1/meta", nil)
			}()
			if code := errorCode(t, rec, http.StatusInternalServerError); code != "internal" {
				t.Errorf("code = %q, want internal", code)
			}
			if got, want := rec.Body.String(), `{"error":{"code":"internal","message":"internal error"}}`; got != want {
				t.Errorf("body = %s, want the OpenAPI example %s", got, want)
			}
			for _, leak := range []string{"secret", "goroutine", ".go:", "panic", "runtime", "nil map"} {
				if strings.Contains(rec.Body.String(), leak) {
					t.Errorf("the body leaks %q: %s", leak, rec.Body)
				}
			}
			if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
				t.Errorf("nosniff missing on the 500: %q", got)
			}
		})
	}

	// nothing is swallowed: the operator gets the value and the stack in the log
	if out := logs.String(); !strings.Contains(out, "secret internal detail") || !strings.Contains(out, "goroutine") {
		t.Errorf("the panic and its stack must be logged, got: %s", out)
	}
	// and the next request is served normally
	if rec := request(withRecover(ok), "GET", "/", nil); rec.Code != http.StatusOK {
		t.Errorf("after a panic the next request = %d", rec.Code)
	}
}

// http.TimeoutHandler runs the handler in its own goroutine and hands a panic back to the caller: the chain's
// recovery, which sits outside it, must still turn that into the 500.
func TestRecover_panicBehindTheTimeoutHandler(t *testing.T) {
	captureLogs(t)
	boom := http.HandlerFunc(func(http.ResponseWriter, *http.Request) { panic("secret internal detail") })
	rec := request(withRecover(withTimeout(time.Second)(boom)), "GET", "/v1/meta", nil)
	if code := errorCode(t, rec, http.StatusInternalServerError); code != "internal" || strings.Contains(rec.Body.String(), "secret") {
		t.Errorf("code %q, body %s", code, rec.Body)
	}
}

func TestTimeout(t *testing.T) {
	saw := make(chan error, 1)
	slow := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-r.Context().Done():
			saw <- r.Context().Err()
		case <-time.After(5 * time.Second):
			saw <- nil
		}
		_, _ = io.WriteString(w, "too late")
	})
	// withHeaders outside: the 503 that http.TimeoutHandler writes itself must still be JSON and uncached
	rec := request(withHeaders(withTimeout(20*time.Millisecond)(slow)), "GET", "/v1/meta", nil)
	if code := errorCode(t, rec, http.StatusServiceUnavailable); code != "timeout" {
		t.Errorf("code = %q, want timeout", code)
	}
	if got, want := rec.Body.String(), `{"error":{"code":"timeout","message":"the request took too long"}}`; got != want {
		t.Errorf("body = %s, want the OpenAPI example %s", got, want)
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Errorf("nosniff missing on the 503: %q", got)
	}
	select {
	case err := <-saw:
		if !errors.Is(err, context.DeadlineExceeded) {
			t.Errorf("the handler's context ended with %v, want a deadline", err)
		}
	case <-time.After(3 * time.Second):
		t.Error("the handler's context was never cancelled")
	}
}

func TestTimeout_fastRequestUnchanged(t *testing.T) {
	rec := request(withHeaders(withTimeout(time.Second)(ok)), "GET", "/v1/meta", nil)
	if rec.Code != http.StatusOK || rec.Body.String() != "ok" {
		t.Errorf("a fast request = %d %q", rec.Code, rec.Body)
	}
	if got := rec.Header().Get("Cache-Control"); got != "public, max-age=300" {
		t.Errorf("a successful answer lost its cache header: %q", got)
	}
	if got := rec.Header().Get("Content-Type"); strings.Contains(got, "json") {
		t.Errorf("the timeout's JSON content type leaked onto a plain answer: %q", got)
	}
}

func loadWorld(t *testing.T) *store.Store {
	t.Helper()
	s, err := store.Load("../../testdata/invest")
	if err != nil {
		t.Fatalf("load the synthetic world: %v", err)
	}
	return s
}

// The whole chain: CORS runs before the rate limit, so the page can read its own 429.
func TestNew_chain(t *testing.T) {
	clk := newClock()
	h := New(loadWorld(t), Config{CORSOrigins: []string{"http://localhost:8765"}, RatePerMinute: 2, Now: clk.now})
	withOrigin := func(r *http.Request) { r.Header.Set("Origin", "http://localhost:8765") }

	rec := request(h, "GET", "/v1/meta", withOrigin)
	if rec.Code != http.StatusOK || rec.Header().Get("Access-Control-Allow-Origin") != "http://localhost:8765" ||
		rec.Header().Get("X-Content-Type-Options") != "nosniff" || rec.Header().Get("Cache-Control") != "public, max-age=300" ||
		rec.Header().Get("Content-Type") != "application/json" {
		t.Errorf("/v1/meta = %d, headers %v", rec.Code, rec.Header())
	}
	rec = request(h, "GET", "/healthz", withOrigin)
	if rec.Code != http.StatusOK || rec.Header().Get("Cache-Control") != "" {
		t.Errorf("/healthz = %d, Cache-Control %q; want 200 and none", rec.Code, rec.Header().Get("Cache-Control"))
	}

	rec = request(h, "GET", "/v1/meta", withOrigin) // the third request of the minute
	if code := errorCode(t, rec, http.StatusTooManyRequests); code != "rate_limited" {
		t.Errorf("code = %q", code)
	}
	if rec.Header().Get("Access-Control-Allow-Origin") != "http://localhost:8765" || rec.Header().Get("Retry-After") == "" {
		t.Errorf("the 429 must be readable by the page and say when to retry: %v", rec.Header())
	}
	if got := request(h, "OPTIONS", "/v1/meta", withOrigin).Code; got != http.StatusNoContent {
		t.Errorf("a preflight = %d, want 204 (CORS answers before the rate limit)", got)
	}

	clk.t = clk.t.Add(time.Minute) // Config.Now drives the limiter's window
	if got := request(h, "GET", "/v1/meta", withOrigin).Code; got != http.StatusOK {
		t.Errorf("after the window = %d, want 200", got)
	}
}

// The zero Config must be safe: no CORS origin, 600 requests a minute, 5 seconds a request.
func TestNew_zeroConfig(t *testing.T) {
	h := New(loadWorld(t), Config{})
	rec := request(h, "GET", "/v1/states", func(r *http.Request) { r.Header.Set("Origin", "http://localhost:8765") })
	if rec.Code != http.StatusOK {
		t.Fatalf("a zero timeout must not time every request out: %d %s", rec.Code, rec.Body)
	}
	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Errorf("no configured origin, yet Allow-Origin = %q", got)
	}
	for i := 2; i <= 600; i++ {
		if got := request(h, "GET", "/healthz", nil).Code; got != http.StatusOK {
			t.Fatalf("request %d = %d, want 200 (the default is 600 a minute)", i, got)
		}
	}
	if got := request(h, "GET", "/healthz", nil).Code; got != http.StatusTooManyRequests {
		t.Errorf("request 601 = %d, want 429", got)
	}
}
