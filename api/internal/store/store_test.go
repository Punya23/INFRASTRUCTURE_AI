package store_test

import (
	"compress/gzip"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"math"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

const (
	testdata     = "../../testdata/invest"
	realFixtures = "../../../web/fixtures/invest" // present once the pipeline has run; TestParity then checks it too
)

func mustLoad(t *testing.T, dir string) *store.Store {
	t.Helper()
	s, err := store.Load(dir)
	if err != nil {
		t.Fatalf("Load(%s): %v", dir, err)
	}
	return s
}

func cityIDs(cs []*store.City) []string {
	ids := make([]string, 0, len(cs))
	for _, c := range cs {
		ids = append(ids, c.ID)
	}
	return ids
}

func TestLoad_ok(t *testing.T) {
	s := mustLoad(t, testdata)

	if got := len(s.Cities()); got != 5 {
		t.Errorf("cities = %d, want 5", got)
	}
	if got := len(s.States()); got != 4 {
		t.Errorf("states = %d, want 4", got)
	}
	if got, want := cityIDs(s.CitiesInState("MH")), []string{"mumbai", "pune", "nashik"}; !slices.Equal(got, want) {
		t.Errorf("CitiesInState(MH) = %v, want %v (population descending)", got, want)
	}
	if a, ok := s.Areas("pune"); !ok || len(a.Features) != 6 {
		t.Errorf("Areas(pune) ok=%v, want 6 features", ok)
	}
	if got := s.DefaultPreset(); got != "balanced" {
		t.Errorf("DefaultPreset = %q, want balanced", got)
	}
	if got, want := s.PresetIDs(), []string{"balanced", "commuter", "highway", "growth"}; !slices.Equal(got, want) {
		t.Errorf("PresetIDs = %v, want %v", got, want)
	}
	if got := s.Meta().Disclaimer; !strings.Contains(got, "not forecasts") {
		t.Errorf("Meta().Disclaimer = %q", got)
	}
}

// A state without cities (Goa here) is a real state with an empty, non-nil list, so a handler can answer
// 200 with [] rather than 404 or null.
func TestLoad_lookups(t *testing.T) {
	s := mustLoad(t, testdata)

	for code, want := range map[string]bool{"GA": true, "MH": true, "ZZ": false, "mh": false} {
		if got := s.HasState(code); got != want {
			t.Errorf("HasState(%q) = %v, want %v", code, got, want)
		}
	}
	for _, code := range []string{"GA", "ZZ"} { // known-but-empty and unknown both give [] not null
		if got := s.CitiesInState(code); got == nil || len(got) != 0 {
			t.Errorf("CitiesInState(%q) = %#v, want a non-nil empty slice", code, got)
		}
	}
	if _, ok := s.City("nowhere"); ok {
		t.Error("City(nowhere) found")
	}
	if _, ok := s.Areas("nowhere"); ok {
		t.Error("Areas(nowhere) found")
	}
	if _, ok := s.Assets("nowhere"); ok {
		t.Error("Assets(nowhere) found")
	}

	nashik, _ := s.City("nashik")
	if nashik.Aliases == nil || len(nashik.Aliases) != 0 {
		t.Errorf("nashik aliases = %#v, want a non-nil empty slice", nashik.Aliases)
	}
	if got := nashik.Scores["balanced"].Gaps; len(got) != 1 || got[0].Factor != "metro_access" {
		t.Errorf("nashik balanced gaps = %+v, want [metro_access]", got)
	}
	pune, _ := s.City("pune")
	if pune.Data.Bus == nil || pune.Data.Bus.Operator != "PMPML" || pune.Data.Bus.Stops != 6713 {
		t.Errorf("pune bus = %+v", pune.Data.Bus)
	}
	if nashik.Data.Bus != nil {
		t.Errorf("nashik bus = %+v, want nil", nashik.Data.Bus)
	}

	// A city without a feed has null bus stops; a city with one keeps its layer and source.
	if a, _ := s.Assets("nashik"); a.BusStops != nil || a.BusSource != nil {
		t.Errorf("nashik assets have bus data: %+v %+v", a.BusStops, a.BusSource)
	}
	if a, _ := s.Assets("pune"); a.BusStops == nil || len(a.BusStops.Features) == 0 || a.BusSource == nil {
		t.Errorf("pune assets lack bus data")
	}

	// Null is not zero: Pune has a feed, so a cell with no stops is 0; Mumbai has none, so every cell is nil.
	byName := map[string]store.AreaProps{}
	for _, city := range []string{"pune", "mumbai"} {
		a, _ := s.Areas(city)
		for _, f := range a.Features {
			name := "(unnamed)"
			if f.Properties.Name != nil {
				name = *f.Properties.Name
			}
			byName[city+"/"+name] = f.Properties
		}
	}
	if p := byName["pune/Wagholi"]; p.BusStops == nil || *p.BusStops != 0 || p.Elig {
		t.Errorf("Wagholi = %+v, want bus_stops 0 (not nil) and not eligible", p)
	}
	if p := byName["pune/Hinjewadi"]; p.BusStops == nil || *p.BusStops != 31 {
		t.Errorf("Hinjewadi bus_stops = %v, want 31", p.BusStops)
	}
	if _, ok := byName["pune/(unnamed)"]; !ok {
		t.Error("pune has no unnamed cell")
	}
	if p := byName["mumbai/Powai"]; p.BusStops != nil {
		t.Errorf("Powai bus_stops = %v, want nil", *p.BusStops)
	}
	if p := byName["pune/Wakad"]; len(p.D["balanced"]) == 0 || p.D["balanced"][0].Factor != "built_up_growth" {
		t.Errorf("Wakad drivers = %+v, want built_up_growth first", p.D["balanced"])
	}
}

// --- fail-closed -------------------------------------------------------------------------------------

func copyTestdata(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.CopyFS(dir, os.DirFS(testdata)); err != nil {
		t.Fatal(err)
	}
	return dir
}

// editJSON parses a copied fixture, lets edit change the tree in place, and writes it back.
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

func gzipFile(t *testing.T, path string) {
	t.Helper()
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	f, err := os.Create(path + ".gz")
	if err != nil {
		t.Fatal(err)
	}
	zw, _ := gzip.NewWriterLevel(f, gzip.BestCompression)
	if _, err := zw.Write(b); err != nil {
		t.Fatal(err)
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	if err := f.Close(); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
}

func obj(v any) map[string]any { return v.(map[string]any) }
func arr(v any) []any          { return v.([]any) }

// feature returns the properties of the i-th feature of a parsed areas file.
func feature(root any, i int) map[string]any {
	return obj(obj(arr(obj(root)["features"])[i])["properties"])
}

func TestLoad_failsClosed(t *testing.T) {
	inDir := func(dir string, parts ...string) string { return filepath.Join(append([]string{dir}, parts...)...) }
	edit := func(file string, fn func(root any)) func(*testing.T, string) {
		return func(t *testing.T, dir string) { editJSON(t, inDir(dir, file), fn) }
	}
	write := func(file, content string) func(*testing.T, string) {
		return func(t *testing.T, dir string) {
			if err := os.WriteFile(inDir(dir, file), []byte(content), 0o644); err != nil {
				t.Fatal(err)
			}
		}
	}

	cases := []struct {
		name   string
		mutate func(t *testing.T, dir string)
		want   string // the error must name the offending file or field
		is     error  // and, where it applies, wrap this cause
	}{
		// the brief's table
		{"missing directory", func(t *testing.T, dir string) { _ = os.RemoveAll(dir) }, "meta.json", fs.ErrNotExist},
		{"malformed cities.json", write("cities.json", "[{"), "cities.json", nil},
		{"city state not in states.json", edit("cities.json", func(r any) { obj(arr(r)[0])["state"] = "ZZ" }), `state "ZZ"`, nil},
		{"city without an areas file", func(t *testing.T, dir string) {
			if err := os.Remove(inDir(dir, "areas", "pune.geojson")); err != nil {
				t.Fatal(err)
			}
		}, "areas/pune.geojson", fs.ErrNotExist},
		{"preset weights sum to 0.9", edit("meta.json", func(r any) {
			obj(obj(arr(obj(r)["presets"])[0])["weights"])["nh_access"] = 0.15
		}), "weights sum", nil},
		{"duplicate city id", edit("cities.json", func(r any) { obj(arr(r)[1])["id"] = obj(arr(r)[0])["id"] }), "duplicate city id", nil},
		{"invalid city id", edit("cities.json", func(r any) { obj(arr(r)[0])["id"] = "Bad_ID" }), `"Bad_ID"`, nil},
		{"city id that would escape the data directory", edit("cities.json", func(r any) {
			obj(arr(r)[0])["id"] = "../../etc/passwd"
		}), "does not match", nil},
		{"area factor missing from meta.factors", edit("areas/pune.geojson", func(r any) {
			feature(r, 0)["f"].(map[string]any)["bogus_factor"] = 1.0
		}), "bogus_factor", nil},

		// contract drift and cross-file consistency
		{"unknown field", edit("cities.json", func(r any) { obj(arr(r)[0])["price_growth"] = 1.0 }), `unknown field "price_growth"`, nil},
		{"trailing data", func(t *testing.T, dir string) {
			b, _ := os.ReadFile(inDir(dir, "states.json"))
			write("states.json", string(b)+"{}")(t, dir)
		}, "unexpected data", nil},
		{"state city_count disagrees with cities.json", edit("states.json", func(r any) {
			for _, s := range arr(r) {
				if obj(s)["code"] == "MH" {
					obj(s)["city_count"] = 2.0
				}
			}
		}), "city_count", nil},
		{"no default preset", edit("meta.json", func(r any) { obj(arr(obj(r)["presets"])[0])["default"] = false }), "default", nil},
		{"city lacks a preset score", edit("cities.json", func(r any) { delete(obj(obj(arr(r)[0])["scores"]), "growth") }), `missing preset "growth"`, nil},
		{"city scores an unknown preset", edit("cities.json", func(r any) {
			s := obj(obj(arr(r)[0])["scores"])
			s["bogus"] = s["balanced"]
		}), `unknown preset "bogus"`, nil},
		{"driver names an unknown factor", edit("cities.json", func(r any) {
			obj(arr(obj(obj(obj(arr(r)[0])["scores"])["balanced"])["drivers"])[0])["factor"] = "vibes"
		}), `"vibes"`, nil},
		{"area lacks a preset score", edit("areas/pune.geojson", func(r any) { delete(feature(r, 0)["sc"].(map[string]any), "growth") }), `sc: missing preset "growth"`, nil},
		{"gap names an unknown factor", edit("areas/pune.geojson", func(r any) {
			feature(r, 0)["g"].(map[string]any)["balanced"] = []any{[]any{"vibes", 10.0}}
		}), `unknown factor "vibes"`, nil},
		{"malformed driver pair", edit("areas/pune.geojson", func(r any) {
			feature(r, 0)["d"].(map[string]any)["balanced"] = []any{[]any{"metro_access"}}
		}), `want ["factor", number]`, nil},
		{"driver pair with a null number", edit("areas/pune.geojson", func(r any) {
			feature(r, 0)["d"].(map[string]any)["balanced"] = []any{[]any{"metro_access", nil}}
		}), `want ["factor", number]`, nil},
		{"duplicate area id", edit("areas/pune.geojson", func(r any) { feature(r, 1)["id"] = feature(r, 0)["id"] }), "duplicate id", nil},
		{"cells disagrees with the areas file", edit("cities.json", func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] == "pune" {
					obj(c)["cells"] = 7.0
				}
			}
		}), "cells", nil},
		{"best_area is not a feature of the areas file", edit("cities.json", func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] == "pune" {
					obj(obj(obj(c)["scores"])["balanced"])["best_area"].(map[string]any)["id"] = "0000"
				}
			}
		}), "best_area", nil},
		{"areas file belongs to another city", edit("areas/pune.geojson", func(r any) { obj(r)["city"] = "nashik" }), `"nashik"`, nil},
		{"bus stops without a source", edit("assets/pune.json", func(r any) { obj(r)["bus_source"] = nil }), "bus_source", nil},
		{"layer is not a feature collection", edit("assets/pune.json", func(r any) { obj(obj(r)["stations"])["type"] = "Feature" }), "stations", nil},
		{"plain and gzip copies both exist", func(t *testing.T, dir string) {
			b, _ := os.ReadFile(inDir(dir, "assets", "pune.json"))
			write("assets/pune.json.gz", string(b))(t, dir)
		}, "both", nil},
		{"corrupt gzip", func(t *testing.T, dir string) {
			if err := os.Remove(inDir(dir, "assets", "pune.json")); err != nil {
				t.Fatal(err)
			}
			write("assets/pune.json.gz", "not gzip")(t, dir)
		}, "assets/pune.json.gz", nil},
		{"gzip with a damaged checksum", func(t *testing.T, dir string) {
			gzipFile(t, inDir(dir, "assets", "pune.json"))
			path := inDir(dir, "assets", "pune.json.gz")
			b, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			b[len(b)-8] ^= 0xff // the CRC-32 in the trailer
			if err := os.WriteFile(path, b, 0o644); err != nil {
				t.Fatal(err)
			}
		}, "checksum", nil},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			dir := copyTestdata(t)
			tc.mutate(t, dir)
			s, err := store.Load(dir)
			if err == nil {
				t.Fatalf("Load succeeded (%d cities), want an error containing %q", len(s.Cities()), tc.want)
			}
			if !strings.Contains(err.Error(), tc.want) {
				t.Errorf("error %q does not name %q", err, tc.want)
			}
			if tc.is != nil && !errors.Is(err, tc.is) {
				t.Errorf("error %q does not wrap %v", err, tc.is)
			}
		})
	}
}

func TestLoad_gzip(t *testing.T) {
	dir := copyTestdata(t)
	gzipFile(t, filepath.Join(dir, "areas", "pune.geojson"))
	gzipFile(t, filepath.Join(dir, "assets", "pune.json"))

	s := mustLoad(t, dir)
	if a, ok := s.Areas("pune"); !ok || len(a.Features) != 6 {
		t.Errorf("Areas(pune) ok=%v, want 6 features", ok)
	}
	if a, ok := s.Assets("pune"); !ok || a.BusStops == nil || len(a.Stations.Features) == 0 {
		t.Errorf("Assets(pune) lost its layers: ok=%v", ok)
	}
}

// A list that a fixture writes as null, or leaves out, still comes out as [] so no handler can serialise null.
func TestLoad_missingListsBecomeEmpty(t *testing.T) {
	dir := copyTestdata(t)
	editJSON(t, filepath.Join(dir, "cities.json"), func(r any) {
		for _, c := range arr(r) {
			if obj(c)["id"] == "pune" {
				delete(obj(c), "aliases")
				bal := obj(obj(obj(c)["scores"])["balanced"])
				bal["drivers"], bal["gaps"] = nil, nil
			}
		}
	})
	editJSON(t, filepath.Join(dir, "areas", "pune.geojson"), func(r any) {
		feature(r, 0)["d"].(map[string]any)["balanced"] = nil
		feature(r, 0)["g"] = map[string]any{"balanced": nil, "commuter": nil, "highway": nil, "growth": nil}
	})

	s := mustLoad(t, dir)
	pune, _ := s.City("pune")
	if pune.Aliases == nil || pune.Scores["balanced"].Drivers == nil || pune.Scores["balanced"].Gaps == nil {
		t.Errorf("city lists are nil: aliases=%#v drivers=%#v gaps=%#v",
			pune.Aliases, pune.Scores["balanced"].Drivers, pune.Scores["balanced"].Gaps)
	}
	a, _ := s.Areas("pune")
	p := a.Features[0].Properties
	if p.D["balanced"] == nil || p.G["balanced"] == nil {
		t.Errorf("area lists are nil: d=%#v g=%#v", p.D["balanced"], p.G["balanced"])
	}
}

// Invariant 2: an unobserved factor is nil and stays a key, so it can be shown as "—" and never as 0.
func TestLoad_unobservedFactorStaysNil(t *testing.T) {
	dir := copyTestdata(t)
	editJSON(t, filepath.Join(dir, "areas", "mumbai.geojson"), func(r any) {
		feature(r, 0)["f"].(map[string]any)["metro_access"] = nil
		feature(r, 0)["s"].(map[string]any)["metro_access"] = nil
	})

	a, _ := mustLoad(t, dir).Areas("mumbai")
	p := a.Features[0].Properties
	for name, m := range map[string]map[string]*float64{"f": p.F, "s": p.S} {
		if v, ok := m["metro_access"]; !ok || v != nil {
			t.Errorf("%s[metro_access] = %v (present=%v), want a nil entry", name, v, ok)
		}
	}
}

// --- parity with the Python scorer -------------------------------------------------------------------

// TestParity ties what is served to the exported sub-scores and weights (spec §7, last bullet). It always
// checks the synthetic world and, once the pipeline has produced them, the real fixtures.
func TestParity(t *testing.T) {
	for _, d := range []struct {
		name, dir string
		optional  bool
	}{{"testdata", testdata, false}, {"web fixtures", realFixtures, true}} {
		t.Run(d.name, func(t *testing.T) {
			if _, err := os.Stat(filepath.Join(d.dir, "meta.json")); d.optional && err != nil {
				t.Skipf("no fixtures in %s", d.dir)
			}
			for _, p := range parityProblems(mustLoad(t, d.dir)) {
				t.Error(p)
			}
		})
	}
}

// The parity check is only worth having if it notices drift, so doctor a copy and expect it to speak up.
func TestParity_detectsDrift(t *testing.T) {
	setScore := func(city, preset string, v float64) func(r any) {
		return func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] == city {
					obj(obj(obj(c)["scores"])[preset])["score"] = v
				}
			}
		}
	}
	cases := []struct {
		name, file string
		edit       func(r any)
		want       string
	}{
		{"area score off its sub-scores", "areas/pune.geojson", func(r any) {
			feature(r, 0)["sc"].(map[string]any)["balanced"] = 99.0
		}, "weighted mean of s"},
		{"driver points above the score", "areas/pune.geojson", func(r any) {
			feature(r, 0)["d"].(map[string]any)["balanced"] = []any{[]any{"nh_access", 60.0}, []any{"rail_access", 60.0}}
		}, "driver points"},
		{"no weighted factor observed", "areas/pune.geojson", func(r any) {
			s := feature(r, 0)["s"].(map[string]any)
			for k := range s {
				s[k] = nil
			}
		}, "no weighted factor observed"},
		{"no eligible area", "areas/nashik.geojson", func(r any) {
			for i := range arr(obj(r)["features"]) {
				feature(r, i)["elig"] = false
			}
		}, "no eligible area"},
		{"best_area score off the eligible maximum", "cities.json", func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] == "pune" {
					obj(obj(obj(c)["scores"])["balanced"])["best_area"].(map[string]any)["score"] = 99.0
				}
			}
		}, "best_area.score"},
		{"city score off its areas", "cities.json", setScore("pune", "commuter", 10.0), "population-weighted mean"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			dir := copyTestdata(t)
			editJSON(t, filepath.Join(dir, tc.file), tc.edit)
			problems := parityProblems(mustLoad(t, dir))
			if !slices.ContainsFunc(problems, func(p string) bool { return strings.Contains(p, tc.want) }) {
				t.Errorf("no problem mentions %q; got %q", tc.want, problems)
			}
		})
	}
}

// parityProblems returns every way the stored scores disagree with the weights in meta.json.
func parityProblems(s *store.Store) []string {
	// Scores and sub-scores are stored with one decimal: a score can be off by 0.05 from the exact weighted
	// mean of rounded sub-scores, and a sum of three rounded driver points by 3 x 0.05 on top of that.
	const (
		tol        = 0.15
		driverSlop = 0.2
	)
	weights := map[string]map[string]float64{}
	for _, p := range s.Meta().Presets {
		weights[p.ID] = p.Weights
	}
	var problems []string
	add := func(format string, args ...any) { problems = append(problems, fmt.Sprintf(format, args...)) }
	checked := 0

	for _, c := range s.Cities() {
		areas, _ := s.Areas(c.ID)
		for _, pid := range s.PresetIDs() {
			var popSum, scoreSum, bestElig float64
			eligible := false
			for _, f := range areas.Features {
				p := f.Properties
				var num, den float64
				for fid, sub := range p.S {
					if sub != nil {
						num += weights[pid][fid] * *sub
						den += weights[pid][fid]
					}
				}
				if den == 0 {
					add("%s/%s preset %s: no weighted factor observed, so there is no score to store", c.ID, p.ID, pid)
					continue
				}
				if want := num / den; math.Abs(p.Sc[pid]-want) > tol {
					add("%s/%s preset %s: sc = %.2f, weighted mean of s = %.2f", c.ID, p.ID, pid, p.Sc[pid], want)
				}
				var top float64
				for _, d := range p.D[pid] {
					top += d.Value
				}
				if top > p.Sc[pid]+driverSlop {
					add("%s/%s preset %s: driver points sum to %.2f, above sc %.2f", c.ID, p.ID, pid, top, p.Sc[pid])
				}
				popSum += p.Pop
				scoreSum += p.Pop * p.Sc[pid]
				if p.Elig {
					eligible = true
					bestElig = math.Max(bestElig, p.Sc[pid])
				}
				checked++
			}
			ps := c.Scores[pid]
			switch {
			case !eligible:
				add("%s preset %s: no eligible area, so best_area cannot exist", c.ID, pid)
			case math.Abs(ps.BestArea.Score-bestElig) > tol:
				add("%s preset %s: best_area.score = %.2f, highest eligible sc = %.2f", c.ID, pid, ps.BestArea.Score, bestElig)
			}
			// The city score is the population-weighted mean of its areas' scores (spec §4).
			if popSum == 0 {
				add("%s preset %s: areas have no population", c.ID, pid)
			} else if want := scoreSum / popSum; math.Abs(ps.Score-want) > tol {
				add("%s preset %s: score = %.2f, population-weighted mean of area scores = %.2f", c.ID, pid, ps.Score, want)
			}
		}
	}
	if checked == 0 {
		add("no area was checked")
	}
	return problems
}
