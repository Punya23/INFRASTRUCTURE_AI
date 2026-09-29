package httpapi_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"strings"
	"testing"

	httpapi "github.com/Punya23/INFRASTRUCTURE_AI/api/internal/http"
	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// newServer serves the synthetic world with a rate limit no test comes near.
func newServer(t *testing.T) http.Handler {
	t.Helper()
	s, err := store.Load("../../testdata/invest")
	if err != nil {
		t.Fatalf("load the synthetic world: %v", err)
	}
	return httpapi.New(s, httpapi.Config{RatePerMinute: 1000})
}

func get(t *testing.T, h http.Handler, target string) *httptest.ResponseRecorder {
	t.Helper()
	return do(h, http.MethodGet, target)
}

func do(h http.Handler, method, target string) *httptest.ResponseRecorder {
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, target, nil))
	return rec
}

// wantOK checks a 200 whose body is JSON.
func wantOK(t *testing.T, rec *httptest.ResponseRecorder) {
	t.Helper()
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", rec.Code, rec.Body)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

// wantError checks the error envelope {"error":{"code","message"}}, its JSON content type and that an error
// is never cached.
func wantError(t *testing.T, rec *httptest.ResponseRecorder, status int, code string) {
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
	if err := dec.Decode(&body); err != nil {
		t.Fatalf("error body is not {\"error\":{\"code\",\"message\"}}: %v (%s)", err, rec.Body)
	}
	if body.Error.Code != code || body.Error.Message == "" {
		t.Errorf("error = %+v, want code %q and a message", body.Error, code)
	}
}

func decode(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.Unmarshal(rec.Body.Bytes(), v); err != nil {
		t.Fatalf("decode %s: %v", rec.Body, err)
	}
}

// wantKeys fails unless the JSON object has exactly the space-separated keys. The OpenAPI schemas are closed
// (additionalProperties false), so a missing or an extra key is a contract break.
func wantKeys(t *testing.T, raw []byte, want string) {
	t.Helper()
	var m map[string]json.RawMessage
	if err := json.Unmarshal(raw, &m); err != nil {
		t.Fatalf("not a JSON object: %s", raw)
	}
	got := make([]string, 0, len(m))
	for k := range m {
		got = append(got, k)
	}
	slices.Sort(got)
	w := strings.Fields(want)
	slices.Sort(w)
	if !slices.Equal(got, w) {
		t.Errorf("keys = %v, want %v", got, w)
	}
}

func near(a, b float64) bool { return math.Abs(a-b) < 1e-9 }

func round1(x float64) float64 { return math.Round(x*10) / 10 }

// serverWith serves a copy of the synthetic world after edit changed its files (in a temp dir), so a test can
// build data the shipped world lacks - here, factors nobody observed.
func serverWith(t *testing.T, edit func(dir string)) http.Handler {
	t.Helper()
	dir := t.TempDir()
	if err := os.CopyFS(dir, os.DirFS("../../testdata/invest")); err != nil {
		t.Fatal(err)
	}
	edit(dir)
	s, err := store.Load(dir)
	if err != nil {
		t.Fatalf("load the edited world: %v", err)
	}
	return httpapi.New(s, httpapi.Config{RatePerMinute: 1000})
}

// editJSON parses a fixture, lets edit change the tree in place, and writes it back.
func editJSON(t *testing.T, path string, edit func(root any)) {
	t.Helper()
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var root any
	if err := json.Unmarshal(b, &root); err != nil {
		t.Fatal(err)
	}
	edit(root)
	if b, err = json.Marshal(root); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, b, 0o644); err != nil {
		t.Fatal(err)
	}
}

func obj(v any) map[string]any { return v.(map[string]any) }
func arr(v any) []any          { return v.([]any) }

// TestOpenAPIExamples ties the handlers to the contract (spec section 9, invariant 10): every 200 example in
// api/openapi.yaml, requested with the URL it describes, is what the server answers - value for value, with
// [] and null kept apart. testdata/openapi_examples.json is those examples, extracted from the YAML; when an
// example changes, regenerate it together with the handler.
func TestOpenAPIExamples(t *testing.T) {
	raw, err := os.ReadFile("testdata/openapi_examples.json")
	if err != nil {
		t.Fatal(err)
	}
	var examples []struct {
		Name string          `json:"name"`
		URL  string          `json:"url"`
		Body json.RawMessage `json:"body"`
	}
	if err := json.Unmarshal(raw, &examples); err != nil || len(examples) == 0 {
		t.Fatalf("read the examples: %v", err)
	}
	h := newServer(t)
	for _, ex := range examples {
		t.Run(ex.Name, func(t *testing.T) {
			rec := get(t, h, ex.URL)
			wantOK(t, rec)
			var got, want any
			decode(t, rec, &got)
			if err := json.Unmarshal(ex.Body, &want); err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(got, want) {
				t.Errorf("%s differs from its OpenAPI example\n got  %s\n want %s", ex.URL, rec.Body, ex.Body)
			}
		})
	}
}

func TestStateCities(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, url string
		status    int
		code      string // error code when status is not 200
		preset    string
		ids       []string // expected order
		total     int
	}{
		{"balanced", "/v1/states/MH/cities?preset=balanced", 200, "", "balanced", []string{"pune", "mumbai", "nashik"}, 3},
		{"commuter", "/v1/states/MH/cities?preset=commuter&limit=2", 200, "", "commuter", []string{"mumbai", "pune"}, 3},
		{"highway", "/v1/states/MH/cities?preset=highway", 200, "", "highway", []string{"pune", "nashik", "mumbai"}, 3},
		{"growth", "/v1/states/MH/cities?preset=growth", 200, "", "growth", []string{"pune", "nashik", "mumbai"}, 3},
		{"default preset", "/v1/states/MH/cities", 200, "", "balanced", []string{"pune", "mumbai", "nashik"}, 3},
		{"limit 1 keeps the total", "/v1/states/MH/cities?limit=1", 200, "", "balanced", []string{"pune"}, 3},
		{"limit 20", "/v1/states/MH/cities?limit=20", 200, "", "balanced", []string{"pune", "mumbai", "nashik"}, 3},
		{"no cities", "/v1/states/GA/cities", 200, "", "balanced", []string{}, 0}, // Review Focus 1: 200, not 404
		{"unknown state", "/v1/states/ZZ/cities", 404, "not_found", "", nil, 0},
		{"lowercase code", "/v1/states/mh/cities", 400, "bad_request", "", nil, 0},
		{"three letters", "/v1/states/MHA/cities", 400, "bad_request", "", nil, 0},
		{"digits", "/v1/states/M1/cities", 400, "bad_request", "", nil, 0},
		{"bad preset", "/v1/states/MH/cities?preset=bogus", 400, "bad_request", "", nil, 0},
		{"empty preset", "/v1/states/MH/cities?preset=", 400, "bad_request", "", nil, 0},
		{"limit 0", "/v1/states/MH/cities?limit=0", 400, "bad_request", "", nil, 0},
		{"limit 21", "/v1/states/MH/cities?limit=21", 400, "bad_request", "", nil, 0},
		{"limit not a number", "/v1/states/MH/cities?limit=three", 400, "bad_request", "", nil, 0},
		{"limit empty", "/v1/states/MH/cities?limit=", 400, "bad_request", "", nil, 0},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := get(t, h, tc.url)
			if tc.status != http.StatusOK {
				wantError(t, rec, tc.status, tc.code)
				return
			}
			wantOK(t, rec)
			var got struct {
				State  string `json:"state"`
				Preset string `json:"preset"`
				Total  int    `json:"total"`
				Cities []struct {
					Rank int    `json:"rank"`
					ID   string `json:"id"`
				} `json:"cities"`
			}
			decode(t, rec, &got)
			if got.Total != tc.total || got.Preset != tc.preset {
				t.Errorf("total, preset = %d, %q; want %d, %q", got.Total, got.Preset, tc.total, tc.preset)
			}
			ids := make([]string, len(got.Cities))
			for i, c := range got.Cities {
				ids[i] = c.ID
				if c.Rank != i+1 {
					t.Errorf("city %d (%s) has rank %d, want %d", i, c.ID, c.Rank, i+1)
				}
			}
			if !slices.Equal(ids, tc.ids) {
				t.Errorf("cities = %v, want %v", ids, tc.ids)
			}
		})
	}
}

// Review Focus 1: a state with fewer than five cities, or none, is a normal answer - never a 404, never null.
func TestStateCities_noCities(t *testing.T) {
	h := newServer(t)

	rec := get(t, h, "/v1/states/GA/cities")
	wantOK(t, rec)
	if !strings.Contains(rec.Body.String(), `"cities":[]`) {
		t.Errorf("a state without a city must answer an empty list, not null: %s", rec.Body)
	}

	for _, tc := range []struct {
		state string
		n     int
	}{{"DL", 1}, {"KA", 1}, {"MH", 3}} { // all below the default limit of 5
		var got struct {
			Total  int   `json:"total"`
			Cities []any `json:"cities"`
		}
		decode(t, get(t, h, "/v1/states/"+tc.state+"/cities"), &got)
		if got.Total != tc.n || len(got.Cities) != tc.n {
			t.Errorf("%s: total %d and %d cards, want %d of each", tc.state, got.Total, len(got.Cities), tc.n)
		}
	}
}

func TestSearch(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, q, limit string
		ids, matched   []string
	}{
		{"prefix of a name", "pu", "", []string{"pune"}, []string{"Pune"}},
		{"alias finds the region", "thane", "", []string{"mumbai"}, []string{"Thane"}},
		{"prefix of an alias", "Bang", "", []string{"bengaluru"}, []string{"Bangalore"}},
		{"case-insensitive", "BENGALURU", "", []string{"bengaluru"}, []string{"Bengaluru"}},
		{"alias of the capital", "noida", "", []string{"delhi"}, []string{"Noida"}},
		{"inside an alias", "chinchwad", "", []string{"pune"}, []string{"Pimpri-Chinchwad"}},
		{"spaces are trimmed and collapsed", "  navi   mumbai ", "", []string{"mumbai"}, []string{"Navi Mumbai"}},
		// "ba" starts Bangalore but only sits inside Mumbai, whose population is larger: prefix comes first.
		{"prefix before substring", "ba", "", []string{"bengaluru", "mumbai"}, []string{"Bangalore", "Mumbai"}},
		// two substring matches: the larger city first.
		{"population breaks a tie", "ne", "", []string{"mumbai", "pune"}, []string{"Thane", "Pune"}},
		{"limit", "ne", "1", []string{"mumbai"}, []string{"Thane"}},
		{"no match", "zzz", "", []string{}, []string{}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			target := "/v1/cities?q=" + url.QueryEscape(tc.q)
			if tc.limit != "" {
				target += "&limit=" + tc.limit
			}
			rec := get(t, h, target)
			wantOK(t, rec)
			var got struct {
				Cities []json.RawMessage `json:"cities"`
			}
			decode(t, rec, &got)
			ids, matched := []string{}, []string{}
			for _, raw := range got.Cities {
				wantKeys(t, raw, "id name state tier population matched")
				var c struct{ ID, Matched string }
				if err := json.Unmarshal(raw, &c); err != nil {
					t.Fatal(err)
				}
				ids, matched = append(ids, c.ID), append(matched, c.Matched)
			}
			if !slices.Equal(ids, tc.ids) || !slices.Equal(matched, tc.matched) {
				t.Errorf("q=%q: ids %v matched %v, want %v %v", tc.q, ids, matched, tc.ids, tc.matched)
			}
		})
	}
}

// Review Focus 4: hostile or odd input is answered, never crashes and is never echoed back.
func TestSearch_badInput(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, q string
		status  int
	}{
		{"one character", "p", 400},
		{"one character with spaces around", "  p  ", 400},
		{"only spaces", "    ", 400},
		{"nothing", "", 400},
		{"65 characters", strings.Repeat("a", 65), 400},
		{"200 characters", strings.Repeat("a", 200), 400},
		{"65 Devanagari letters", strings.Repeat("प", 65), 400},
		{"64 characters", strings.Repeat("a", 64), 200},
		{"two characters", "zq", 200},
		{"Devanagari", "पुने", 200}, // the brief's %E0%A4%AA%E0%A5%81%E0%A4%A8%E0%A5%87
		{"64 Devanagari letters", strings.Repeat("प", 64), 200},
		{"65 characters, most of them spaces", strings.Repeat(" ", 61) + "zqzq", 400}, // the limit is on what was sent
		{"64 characters, most of them spaces", strings.Repeat(" ", 60) + "zqzq", 200},
		{"markup", "<script>alert(1)</script>", 200},
		{"path traversal", "../../etc/passwd", 200},
		{"sql-like", "'; DROP TABLE cities; --", 200},
		{"nul byte", "pu\x00ne", 200},
		{"invalid UTF-8", "\xff\xfe", 400},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := get(t, h, "/v1/cities?q="+url.QueryEscape(tc.q))
			if tc.status == http.StatusBadRequest {
				wantError(t, rec, 400, "bad_request")
				return
			}
			wantOK(t, rec)
			if strings.Contains(rec.Body.String(), "<script>") || strings.Contains(rec.Body.String(), "DROP TABLE") {
				t.Errorf("the response echoes the query: %s", rec.Body)
			}
			var got struct {
				Cities []any `json:"cities"`
			}
			decode(t, rec, &got)
			if len(got.Cities) != 0 {
				t.Errorf("q=%q matched %d cities, want none", tc.q, len(got.Cities))
			}
		})
	}

	for _, target := range []string{"/v1/cities", "/v1/cities?q=pu&limit=0", "/v1/cities?q=pu&limit=21", "/v1/cities?q=pu&limit=x"} {
		wantError(t, get(t, h, target), 400, "bad_request")
	}
}

func TestCity(t *testing.T) {
	h := newServer(t)
	const keys = "id name state tier population score access momentum coverage confidence drivers gaps best_area " +
		"source source_ref fetched_at license aliases lat lon area_km2 cells factors data"

	rec := get(t, h, "/v1/cities/pune?preset=commuter")
	wantOK(t, rec)
	wantKeys(t, rec.Body.Bytes(), keys) // R2: state is there; a detail has no rank
	var got struct {
		ID      string   `json:"id"`
		State   string   `json:"state"`
		Score   float64  `json:"score"`
		Aliases []string `json:"aliases"`
		Drivers []struct {
			Factor string `json:"factor"`
		} `json:"drivers"`
		BestArea struct {
			Name string `json:"name"`
		} `json:"best_area"`
		Factors map[string]json.RawMessage `json:"factors"`
		Data    struct {
			Bus *struct {
				Operator string `json:"operator"`
				Stops    int    `json:"stops"`
			} `json:"bus"`
		} `json:"data"`
	}
	decode(t, rec, &got)
	if got.ID != "pune" || got.State != "MH" || math.Abs(got.Score-63.5) > 0.15 {
		t.Errorf("id, state, score = %q, %q, %v; want pune, MH, 63.5", got.ID, got.State, got.Score)
	}
	if len(got.Drivers) == 0 || len(got.Drivers) > 3 {
		t.Errorf("%d drivers, want 1 to 3", len(got.Drivers))
	}
	if len(got.Factors) != 5 {
		t.Errorf("%d factors, want 5", len(got.Factors))
	}
	if got.Data.Bus == nil || got.Data.Bus.Operator != "PMPML" || got.Data.Bus.Stops != 6713 {
		t.Errorf("data.bus = %+v, want PMPML with 6713 stops", got.Data.Bus)
	}
	if !slices.Equal(got.Aliases, []string{"Pimpri-Chinchwad"}) || got.BestArea.Name != "Hinjewadi" {
		t.Errorf("aliases %v, best area %q", got.Aliases, got.BestArea.Name)
	}

	// The preset changes the score, not the city; the default preset is the one marked default.
	var balanced struct {
		Score float64 `json:"score"`
	}
	decode(t, get(t, h, "/v1/cities/pune"), &balanced)
	if !near(balanced.Score, 70.5) {
		t.Errorf("default preset score = %v, want balanced 70.5", balanced.Score)
	}

	// Review Focus 2/R3: what is absent stays absent - null for the missing feed, [] for empty lists.
	nashik := get(t, h, "/v1/cities/nashik?preset=highway").Body.String()
	for _, want := range []string{`"bus":null`, `"aliases":[]`, `"gaps":[]`} {
		if !strings.Contains(nashik, want) {
			t.Errorf("nashik lacks %s: %s", want, nashik)
		}
	}
}

func TestCity_badID(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, id string
		status   int
	}{
		{"upper case", "Pune", 400},
		{"one character", "a", 400},
		{"65 characters", strings.Repeat("a", 65), 400},
		{"64 characters, unknown", strings.Repeat("a", 64), 404},
		{"dot segment", "..%2Fx", 400}, // a raw ../ is cleaned by the mux before any handler sees it
		{"deep traversal", "..%2F..%2Fetc%2Fpasswd", 400},
		{"backslash", "..%5Cx", 400},
		{"space", "pu%20ne", 400},
		{"underscore", "pu_ne", 400},
		{"dot", "pu.ne", 400},
		{"Devanagari", "%E0%A4%AA%E0%A5%81%E0%A4%A8%E0%A5%87", 400},
		{"unknown", "nowhere", 404},
	}
	for _, tc := range cases {
		for _, suffix := range []string{"", "/areas", "/assets", "/compare"} {
			t.Run(tc.name+suffix, func(t *testing.T) {
				code := map[int]string{400: "bad_request", 404: "not_found"}[tc.status]
				wantError(t, get(t, h, "/v1/cities/"+tc.id+suffix), tc.status, code)
			})
		}
	}
}

type areaProps struct {
	ID         string              `json:"id"`
	Name       *string             `json:"name"`
	Pop        float64             `json:"pop"`
	Elig       bool                `json:"elig"`
	BusStops   *float64            `json:"bus_stops"`
	Rank       int                 `json:"rank"`
	Score      float64             `json:"score"`
	Access     *float64            `json:"access"`
	Coverage   float64             `json:"coverage"`
	Confidence float64             `json:"confidence"`
	F          map[string]*float64 `json:"f"`
	S          map[string]*float64 `json:"s"`
	D          []struct {
		Factor string   `json:"factor"`
		Points float64  `json:"points"`
		Value  *float64 `json:"value"`
		Unit   string   `json:"unit"`
	} `json:"d"`
	G []struct {
		Factor   string   `json:"factor"`
		Subscore float64  `json:"subscore"`
		Value    *float64 `json:"value"`
		Unit     string   `json:"unit"`
	} `json:"g"`
	Source    string `json:"source"`
	SourceRef string `json:"source_ref"`
	FetchedAt string `json:"fetched_at"`
	License   string `json:"license"`
}

func areas(t *testing.T, h http.Handler, target string) (feats []areaProps, raw string) {
	t.Helper()
	rec := get(t, h, target)
	wantOK(t, rec)
	var fc struct {
		Type     string `json:"type"`
		Features []struct {
			Type       string          `json:"type"`
			Geometry   json.RawMessage `json:"geometry"`
			Properties json.RawMessage `json:"properties"`
		} `json:"features"`
	}
	decode(t, rec, &fc)
	wantKeys(t, rec.Body.Bytes(), "type features")
	if fc.Type != "FeatureCollection" {
		t.Errorf("type = %q, want FeatureCollection", fc.Type)
	}
	for _, f := range fc.Features {
		if f.Type != "Feature" || !bytes.Contains(f.Geometry, []byte(`"Polygon"`)) {
			t.Errorf("feature type %q, geometry %s", f.Type, f.Geometry)
		}
		wantKeys(t, f.Properties, "id name pop elig bus_stops rank score access coverage confidence f s d g source source_ref fetched_at license")
		var p areaProps
		if err := json.Unmarshal(f.Properties, &p); err != nil {
			t.Fatal(err)
		}
		feats = append(feats, p)
	}
	return feats, rec.Body.String()
}

func ids(feats []areaProps) []string {
	out := make([]string, len(feats))
	for i, f := range feats {
		out[i] = f.ID
	}
	return out
}

func TestAreas(t *testing.T) {
	h := newServer(t)

	feats, raw := areas(t, h, "/v1/cities/pune/areas?preset=balanced")
	if len(feats) != 6 {
		t.Fatalf("%d features, want 6", len(feats))
	}
	for i, f := range feats {
		if f.Rank != i+1 {
			t.Errorf("feature %d has rank %d", i, f.Rank)
		}
		if i > 0 && f.Score > feats[i-1].Score {
			t.Errorf("scores must not increase down the list: %v after %v", f.Score, feats[i-1].Score)
		}
		// provenance comes from the collection (source, fetched_at, license) and from the cell (source_ref)
		if f.Source != "synthetic-test" || f.License != "synthetic-test" || f.FetchedAt != "2026-09-29" || f.SourceRef != "h3:"+f.ID {
			t.Errorf("%s: provenance %q %q %q %q", f.ID, f.Source, f.License, f.FetchedAt, f.SourceRef)
		}
		if len(f.D) == 0 || f.D[0].Factor == "" || f.D[0].Unit == "" || f.D[0].Value == nil {
			t.Errorf("%s: d[0] = %+v, want factor, points, value and unit", f.ID, f.D)
		}
		for _, d := range f.D { // the raw value is the cell's own, taken from f
			if d.Value == nil || f.F[d.Factor] == nil || *d.Value != *f.F[d.Factor] {
				t.Errorf("%s: driver %s value %v is not f[%s] %v", f.ID, d.Factor, d.Value, d.Factor, f.F[d.Factor])
			}
		}
		if len(f.F) != 5 || len(f.S) != 5 {
			t.Errorf("%s: f has %d and s has %d factors, want 5 each", f.ID, len(f.F), len(f.S))
		}
	}
	// rank 1 is the tiny cell that is not eligible: it still draws, the UI never offers it as a best area.
	if first := feats[0]; first.Elig || first.Pop != 1200 || first.BusStops == nil || *first.BusStops != 0 {
		t.Errorf("rank 1 = %+v, want the ineligible 1,200-person cell with 0 bus stops (0, not null)", first)
	}
	if unnamed := feats[3]; unnamed.Name != nil || !unnamed.Elig {
		t.Errorf("rank 4 = %+v, want the eligible cell without a name", unnamed)
	}
	for _, want := range []string{`"name":null`, `"g":[]`} {
		if !strings.Contains(raw, want) {
			t.Errorf("response lacks %s", want)
		}
	}

	// The order is re-computed for the preset asked for.
	commuter, _ := areas(t, h, "/v1/cities/pune/areas?preset=commuter")
	var commuterScores []float64
	for _, f := range commuter {
		commuterScores = append(commuterScores, f.Score)
	}
	if want := []float64{81.0, 70.0, 62.8, 61.5, 61.2, 59.6}; !slices.Equal(commuterScores, want) {
		t.Errorf("commuter scores %v, want %v (the score is the requested preset's)", commuterScores, want)
	}
	wantOrder := []string{"87608850effffff", "876088500ffffff", "876088505ffffff", "876088501ffffff", "87608850cffffff", "876088503ffffff"}
	if !slices.Equal(ids(commuter), wantOrder) {
		t.Errorf("commuter order %v, want %v", ids(commuter), wantOrder)
	}
	if def, _ := areas(t, h, "/v1/cities/pune/areas"); !slices.Equal(ids(def), ids(feats)) {
		t.Errorf("default preset order %v, want balanced %v", ids(def), ids(feats))
	}

	// The fixtures carry drivers and gaps for all four presets; the answer holds the requested preset's only.
	byID := func(fs []areaProps, id string) areaProps {
		for _, f := range fs {
			if f.ID == id {
				return f
			}
		}
		t.Fatalf("no cell %s", id)
		return areaProps{}
	}
	var hinjewadi []string // its drivers under the commuter preset, not the balanced ones
	for _, d := range byID(commuter, "876088500ffffff").D {
		hinjewadi = append(hinjewadi, fmt.Sprintf("%s %.1f", d.Factor, d.Points))
	}
	if want := []string{"built_up_growth 23.0", "metro_access 18.0", "rail_access 15.0"}; !slices.Equal(hinjewadi, want) {
		t.Errorf("Hinjewadi commuter drivers %v, want %v", hinjewadi, want)
	}
	highway, _ := areas(t, h, "/v1/cities/pune/areas?preset=highway")
	wakadBalanced, wakadHighway := byID(feats, "876088501ffffff"), byID(highway, "876088501ffffff")
	if len(wakadBalanced.G) != 1 || wakadBalanced.G[0].Factor != "metro_access" || wakadBalanced.G[0].Subscore != 30 || len(wakadHighway.G) != 0 {
		t.Errorf("Wakad gaps: balanced %+v, highway %+v; want metro_access 30 and none (metro has no weight in highway)", wakadBalanced.G, wakadHighway.G)
	}

	// limit cuts the list, not the rank: rank runs over every cell.
	two, _ := areas(t, h, "/v1/cities/pune/areas?preset=commuter&limit=2")
	if len(two) != 2 || two[0].Rank != 1 || two[1].Rank != 2 || !slices.Equal(ids(two), wantOrder[:2]) {
		t.Errorf("limit=2 gave %v", ids(two))
	}
	if all, _ := areas(t, h, "/v1/cities/pune/areas?limit=1000"); len(all) != 6 {
		t.Errorf("limit=1000 gave %d features, want 6", len(all))
	}

	for _, target := range []string{
		"/v1/cities/pune/areas?limit=1001", "/v1/cities/pune/areas?limit=0", "/v1/cities/pune/areas?limit=-1",
		"/v1/cities/pune/areas?limit=", "/v1/cities/pune/areas?preset=bogus",
	} {
		wantError(t, get(t, h, target), 400, "bad_request")
	}
}

// Nashik's four cells score the same under every preset: the larger cell comes first, then the id.
func TestAreas_tiesBreakByPopulationThenID(t *testing.T) {
	h := newServer(t)
	feats, raw := areas(t, h, "/v1/cities/nashik/areas?preset=highway")
	want := []string{"876099a04ffffff", "876099a00ffffff", "876099a05ffffff", "876099a06ffffff"} // 24k, 19k, 16k, 11k
	if !slices.Equal(ids(feats), want) {
		t.Errorf("order %v, want %v", ids(feats), want)
	}
	if !strings.Contains(raw, `"bus_stops":null`) { // no feed for this city: null, not 0
		t.Errorf("a city without a bus feed must report bus_stops null: %s", raw)
	}

	// equal score and equal population: the id decides, whatever order the file lists the cells in
	same := serverWith(t, func(dir string) {
		editJSON(t, filepath.Join(dir, "areas", "nashik.geojson"), func(r any) {
			for _, f := range arr(obj(r)["features"]) {
				obj(obj(f)["properties"])["pop"] = 20000
			}
		})
	})
	feats, _ = areas(t, same, "/v1/cities/nashik/areas")
	want = []string{"876099a00ffffff", "876099a04ffffff", "876099a05ffffff", "876099a06ffffff"}
	if !slices.Equal(ids(feats), want) {
		t.Errorf("order %v, want by id %v", ids(feats), want)
	}
}

func TestAssets(t *testing.T) {
	h := newServer(t)
	// The file's provenance (source, fetched_at, license) comes with every answer, whichever layers are asked for.
	const provenance = "source fetched_at license "
	cases := []struct {
		name, url string
		keys      string
	}{
		{"default is all four with the source", "/v1/cities/pune/assets", "stations bus_stops bus_source highways toll_plazas"},
		{"stations only", "/v1/cities/pune/assets?layers=stations", "stations"},
		{"bus stops come with their source", "/v1/cities/pune/assets?layers=bus_stops", "bus_stops bus_source"},
		{"two layers", "/v1/cities/pune/assets?layers=highways,toll_plazas", "highways toll_plazas"},
		{"a layer twice is one layer", "/v1/cities/pune/assets?layers=stations,stations", "stations"},
		{"no feed", "/v1/cities/nashik/assets", "stations bus_stops bus_source highways toll_plazas"},
		{"no feed, only the bus layer", "/v1/cities/nashik/assets?layers=bus_stops", "bus_stops bus_source"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := get(t, h, tc.url)
			wantOK(t, rec)
			wantKeys(t, rec.Body.Bytes(), provenance+tc.keys)
			var p struct {
				Source    string `json:"source"`
				FetchedAt string `json:"fetched_at"`
				License   string `json:"license"`
			}
			decode(t, rec, &p)
			if p.Source != "synthetic-test" || p.FetchedAt != "2026-09-29" || p.License != "synthetic-test" {
				t.Errorf("provenance = %+v, want the stored synthetic-test, 2026-09-29, synthetic-test", p)
			}
		})
	}

	// a city without a bus feed says so, for both keys
	body := get(t, h, "/v1/cities/nashik/assets").Body.String()
	for _, want := range []string{`"bus_stops":null`, `"bus_source":null`} {
		if !strings.Contains(body, want) {
			t.Errorf("nashik lacks %s: %s", want, body)
		}
	}
	// and with a feed the source travels with the stops
	var pune struct {
		BusSource struct{ Operator, Tier string } `json:"bus_source"`
	}
	decode(t, get(t, h, "/v1/cities/pune/assets?layers=bus_stops"), &pune)
	if pune.BusSource.Operator != "PMPML" || pune.BusSource.Tier != "secondary" {
		t.Errorf("bus_source = %+v", pune.BusSource)
	}

	for _, target := range []string{
		"/v1/cities/pune/assets?layers=bogus", "/v1/cities/pune/assets?layers=", "/v1/cities/pune/assets?layers=stations,",
		"/v1/cities/pune/assets?layers=stations,bogus", "/v1/cities/pune/assets?layers=Stations", "/v1/cities/pune/assets?layers=stations%20",
	} {
		wantError(t, get(t, h, target), 400, "bad_request")
	}
}

func TestMetaStatesHealth(t *testing.T) {
	h := newServer(t)

	rec := get(t, h, "/healthz")
	wantOK(t, rec)
	if body := rec.Body.String(); body != `{"status":"ok","as_of":"2026-09-29"}` {
		t.Errorf("/healthz = %s", body)
	}

	rec = get(t, h, "/v1/meta")
	wantOK(t, rec)
	wantKeys(t, rec.Body.Bytes(), "schema_version as_of grid factors presets tiers sources disclaimer")
	var meta struct {
		Presets []struct {
			ID      string `json:"id"`
			Default bool   `json:"default"`
		} `json:"presets"`
		Factors    []json.RawMessage `json:"factors"`
		Disclaimer string            `json:"disclaimer"`
	}
	decode(t, rec, &meta)
	var presets []string
	for _, p := range meta.Presets {
		presets = append(presets, p.ID)
	}
	if !slices.Equal(presets, []string{"balanced", "commuter", "highway", "growth"}) || len(meta.Factors) != 5 {
		t.Errorf("presets %v, %d factors", presets, len(meta.Factors))
	}
	if !strings.Contains(meta.Disclaimer, "not forecasts") {
		t.Errorf("disclaimer = %q", meta.Disclaimer)
	}

	rec = get(t, h, "/v1/states")
	wantOK(t, rec)
	var states struct {
		AsOf   string `json:"as_of"`
		States []struct {
			Code      string `json:"code"`
			Name      string `json:"name"`
			CityCount int    `json:"city_count"`
		} `json:"states"`
	}
	decode(t, rec, &states)
	if states.AsOf != "2026-09-29" || len(states.States) != 4 {
		t.Fatalf("states = %+v", states)
	}
	if ga := states.States[1]; ga.Code != "GA" || ga.CityCount != 0 {
		t.Errorf("Goa = %+v, want city_count 0 (a state may have no city)", ga)
	}
}

// Review Focus 2 and invariant 2: a factor that was not observed is null in every answer - a driver-less
// score is not a zero, a missing sub-score is not compared, coverage is what the pipeline stored. The shipped
// world observes everything, so this one is edited: Pune's Hinjewadi lacks metro data and commuter access,
// Nashik lacks growth.
func TestUnobservedStaysNull(t *testing.T) {
	h := serverWith(t, func(dir string) {
		editJSON(t, filepath.Join(dir, "areas", "pune.geojson"), func(r any) {
			p := obj(obj(arr(obj(r)["features"])[1])["properties"]) // Hinjewadi, second in the balanced order
			obj(p["f"])["metro_access"] = nil
			obj(p["s"])["metro_access"] = nil
			obj(p["ac"])["commuter"] = nil
			p["cov"], p["conf"] = 0.85, 0.68
		})
		editJSON(t, filepath.Join(dir, "cities.json"), func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] != "nashik" {
					continue
				}
				g := obj(obj(obj(c)["factors"])["built_up_growth"])
				g["value"], g["share"], g["band_km"], g["subscore"] = nil, nil, nil, nil
				for _, ps := range obj(obj(c)["scores"]) {
					obj(ps)["momentum"] = nil
					obj(ps)["coverage"], obj(ps)["confidence"] = 0.85, 0.68
				}
				obj(obj(obj(c)["scores"])["commuter"])["access"] = nil
			}
		})
	})

	// area: the key stays, the value is null; access is null only for the preset that lacks it
	for preset, wantAccess := range map[string]bool{"commuter": false, "balanced": true} {
		var hinjewadi areaProps
		feats, raw := areas(t, h, "/v1/cities/pune/areas?preset="+preset)
		for _, f := range feats {
			if f.ID == "876088500ffffff" {
				hinjewadi = f
			}
		}
		for name, m := range map[string]map[string]*float64{"f": hinjewadi.F, "s": hinjewadi.S} {
			if v, ok := m["metro_access"]; !ok || v != nil {
				t.Errorf("%s: %s.metro_access = %v (present %v), want a null entry, not 0", preset, name, v, ok)
			}
		}
		if got := hinjewadi.Access != nil; got != wantAccess {
			t.Errorf("%s: access observed = %v, want %v (null must not become 0: %v)", preset, got, wantAccess, hinjewadi.Access)
		}
		if hinjewadi.Coverage != 0.85 || hinjewadi.Confidence != 0.68 {
			t.Errorf("%s: coverage %v confidence %v, want the stored 0.85 and 0.68", preset, hinjewadi.Coverage, hinjewadi.Confidence)
		}
		if !strings.Contains(raw, `"metro_access":null`) {
			t.Errorf("%s: the response has no null metro_access: %s", preset, raw)
		}
	}

	// city: card and detail keep momentum, access and the factor summary null
	var list struct {
		Cities []struct {
			ID         string   `json:"id"`
			Momentum   *float64 `json:"momentum"`
			Access     *float64 `json:"access"`
			Coverage   float64  `json:"coverage"`
			Confidence float64  `json:"confidence"`
		} `json:"cities"`
	}
	decode(t, get(t, h, "/v1/states/MH/cities?preset=commuter"), &list)
	for _, c := range list.Cities {
		if c.ID == "nashik" && (c.Momentum != nil || c.Access != nil || c.Coverage != 0.85 || c.Confidence != 0.68) {
			t.Errorf("nashik card: momentum %v access %v coverage %v confidence %v; want null, null, 0.85, 0.68",
				c.Momentum, c.Access, c.Coverage, c.Confidence)
		}
		if c.ID == "pune" && (c.Momentum == nil || c.Access == nil) {
			t.Errorf("pune card lost a value that was observed: %+v", c)
		}
	}
	rec := get(t, h, "/v1/cities/nashik?preset=commuter")
	var detail struct {
		Factors map[string]struct {
			Value    *float64 `json:"value"`
			Share    *float64 `json:"share"`
			BandKm   *float64 `json:"band_km"`
			Subscore *float64 `json:"subscore"`
			Unit     string   `json:"unit"`
		} `json:"factors"`
	}
	decode(t, rec, &detail)
	if g := detail.Factors["built_up_growth"]; g.Value != nil || g.Share != nil || g.BandKm != nil || g.Subscore != nil || g.Unit != "pp" {
		t.Errorf("built_up_growth summary = %+v, want nulls and the unit", g)
	}
	if !strings.Contains(rec.Body.String(), `"momentum":null`) || !strings.Contains(rec.Body.String(), `"access":null`) {
		t.Errorf("nashik detail: %s", rec.Body)
	}

	// compare: Pune's growth sub-score is 90 and Nashik's is unobserved - that is not a 90-point gap
	var compared compareResponse
	decode(t, get(t, h, "/v1/cities/pune/compare?scope=india&limit=10"), &compared)
	for _, o := range compared.Others {
		for _, d := range append(slices.Clone(o.Better), o.Worse...) {
			if o.ID == "nashik" && d.Factor == "built_up_growth" {
				t.Errorf("nashik vs pune compares the unobserved growth factor: %+v", d)
			}
		}
	}
}

// The messages the OpenAPI shows as examples are the messages the API sends, and a message never repeats the
// value it rejects (so nothing a client sent comes back as markup).
func TestErrorMessages(t *testing.T) {
	h := newServer(t)
	for target, want := range map[string]string{
		"/v1/states/MH/cities?limit=0": `{"error":{"code":"bad_request","message":"limit must be an integer from 1 to 20"}}`,
		"/v1/cities/nowhere":           `{"error":{"code":"not_found","message":"city not found"}}`,
	} {
		if got := get(t, h, target).Body.String(); got != want {
			t.Errorf("%s: %s, want the OpenAPI example %s", target, got, want)
		}
	}

	hostile := "%3Cscript%3Ealert(1)%3C%2Fscript%3E"
	for _, target := range []string{
		"/v1/states/MH/cities?preset=" + hostile, "/v1/states/MH/cities?limit=" + hostile,
		"/v1/cities/" + hostile, "/v1/cities/pune?preset=" + hostile,
		"/v1/cities/pune/areas?limit=" + hostile, "/v1/cities/pune/assets?layers=" + hostile,
		"/v1/cities/pune/compare?scope=" + hostile, "/v1/states/" + hostile + "/cities",
	} {
		rec := get(t, h, target)
		wantError(t, rec, http.StatusBadRequest, "bad_request")
		if strings.Contains(rec.Body.String(), "script") || strings.Contains(rec.Body.String(), "alert") {
			t.Errorf("%s: the message repeats the input: %s", target, rec.Body)
		}
	}
}

// Errors are always the JSON envelope, also for a path or a method the API does not have.
func TestUnknownRoutes(t *testing.T) {
	h := newServer(t)
	for _, tc := range []struct{ method, target string }{
		{"GET", "/"}, {"GET", "/nope"}, {"GET", "/v1"}, {"GET", "/v1/cities/"}, {"GET", "/v1/states/MH"},
		{"GET", "/healthz/"}, {"POST", "/v1/meta"}, {"DELETE", "/healthz"}, {"PUT", "/v1/cities/pune"},
	} {
		wantError(t, do(h, tc.method, tc.target), 404, "not_found")
	}
}
