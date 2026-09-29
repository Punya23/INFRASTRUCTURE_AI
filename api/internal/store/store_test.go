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
	// Every layer file names where it came from (AGENTS invariant 1).
	for _, c := range s.Cities() {
		if a, _ := s.Assets(c.ID); a.Source != "synthetic-test" || a.FetchedAt != "2026-09-29" || a.License != "synthetic-test" {
			t.Errorf("Assets(%s) provenance = %q %q %q", c.ID, a.Source, a.FetchedAt, a.License)
		}
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

// The by-state order (largest first, then id) is what handlers rank from. Reverse the file and tie two cities
// so that neither the file order nor a size-only comparison can produce it by luck.
func TestLoad_ordersStateCitiesBySizeThenID(t *testing.T) {
	dir := copyTestdata(t)
	editJSON(t, filepath.Join(dir, "cities.json"), func(r any) {
		cities := arr(r)
		slices.Reverse(cities)
		for _, c := range cities {
			if obj(c)["id"] == "mumbai" {
				obj(c)["population"] = 6100000.0 // the same as pune
			}
		}
	})

	got := cityIDs(mustLoad(t, dir).CitiesInState("MH"))
	if want := []string{"mumbai", "pune", "nashik"}; !slices.Equal(got, want) {
		t.Errorf("CitiesInState(MH) = %v, want %v (larger first; the tie by id)", got, want)
	}
}

// Every list an accessor returns is a copy: a caller that sorts or overwrites it cannot change what the next
// caller sees. (The values the copies point to are shared and read-only.)
func TestAccessors_returnCopies(t *testing.T) {
	s := mustLoad(t, testdata)

	s.States()[0].Code = "XX"
	s.Cities()[0].ID = "xx"
	s.PresetIDs()[0] = "xx"
	s.CitiesInState("MH")[0] = nil
	m := s.Meta()
	m.Factors[0].ID, m.Presets[0].ID, m.Sources[0].ID = "xx", "xx", "xx"

	if got := s.States()[0].Code; got != "DL" {
		t.Errorf("States()[0].Code = %q after a caller overwrote its copy", got)
	}
	if got := s.Cities()[0].ID; got != "delhi" {
		t.Errorf("Cities()[0].ID = %q after a caller overwrote its copy", got)
	}
	if got := s.PresetIDs()[0]; got != "balanced" {
		t.Errorf("PresetIDs()[0] = %q after a caller overwrote its copy", got)
	}
	if got := s.CitiesInState("MH")[0]; got == nil || got.ID != "mumbai" {
		t.Errorf("CitiesInState(MH)[0] = %v after a caller overwrote its copy", got)
	}
	if m := s.Meta(); m.Factors[0].ID != "nh_access" || m.Presets[0].ID != "balanced" || m.Sources[0].ID != "synthetic-test" {
		t.Errorf("Meta() lists changed after a caller overwrote its copy: %q %q %q", m.Factors[0].ID, m.Presets[0].ID, m.Sources[0].ID)
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
	// Shorthand for the records the rows below break: the first city of cities.json (delhi) and its balanced
	// score, the first cell of Pune (Wagholi), meta.json and Pune's assets file.
	city := func(fn func(c map[string]any)) func(*testing.T, string) {
		return edit("cities.json", func(r any) { fn(obj(arr(r)[0])) })
	}
	preset := func(fn func(p map[string]any)) func(*testing.T, string) {
		return city(func(c map[string]any) { fn(obj(obj(c["scores"])["balanced"])) })
	}
	cell := func(fn func(p map[string]any)) func(*testing.T, string) {
		return edit("areas/pune.geojson", func(r any) { fn(feature(r, 0)) })
	}
	meta := func(fn func(m map[string]any)) func(*testing.T, string) {
		return edit("meta.json", func(r any) { fn(obj(r)) })
	}
	assets := func(fn func(a map[string]any)) func(*testing.T, string) {
		return edit("assets/pune.json", func(r any) { fn(obj(r)) })
	}
	del := func(key string) func(m map[string]any) { return func(m map[string]any) { delete(m, key) } }
	set := func(key string, v any) func(m map[string]any) { return func(m map[string]any) { m[key] = v } }
	inSub := func(key string, fn func(m map[string]any)) func(m map[string]any) {
		return func(m map[string]any) { fn(obj(m[key])) }
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

		// meta.json: the model itself
		{"schema_version is not 1", meta(set("schema_version", 2.0)), "schema_version is 2", nil},
		{"preset weight for an unknown factor", meta(func(m map[string]any) {
			obj(obj(arr(m["presets"])[0])["weights"])["vibes"] = 0.0
		}), `unknown factor "vibes"`, nil},
		{"grid null", meta(set("grid", nil)), "$.grid: want an object", nil},
		{"grid h3_res omitted", meta(inSub("grid", del("h3_res"))), "$.grid.h3_res: missing", nil},
		{"grid h3_res zero", meta(inSub("grid", set("h3_res", 0.0))), "h3_res 0,", nil},
		{"grid min_area_population zero", meta(inSub("grid", set("min_area_population", 0.0))), "min_area_population 0 and", nil},
		{"grid best_area_min_population zero", meta(inSub("grid", set("best_area_min_population", 0.0))), "best_area_min_population 0 must", nil},
		{"metro tier threshold not above the large one", meta(inSub("tiers", set("metro_min_population", 1000000.0))),
			"metro_min_population 1000000 must be above large_min_population 1000000", nil},
		{"large tier threshold zero", meta(inSub("tiers", set("large_min_population", 0.0))), "large_min_population 0,", nil},
		{"sources omitted", meta(del("sources")), "$.sources: missing", nil},
		{"sources null", meta(set("sources", nil)), "sources: none", nil},

		// states.json
		{"state code not upper case", edit("states.json", func(r any) { obj(arr(r)[0])["code"] = "dl" }), `code "dl" does not match`, nil},
		{"duplicate state code", edit("states.json", func(r any) { obj(arr(r)[1])["code"] = obj(arr(r)[0])["code"] }), `duplicate code "DL"`, nil},

		// cities.json: a required value that is missing or null must never load as 0 (AGENTS invariant 2)
		{"city lat omitted", city(del("lat")), "$[0].lat: missing", nil},
		{"city lon omitted", city(del("lon")), "$[0].lon: missing", nil},
		{"city at latitude 0 and longitude 0", city(func(c map[string]any) { c["lat"], c["lon"] = 0.0, 0.0 }), "lat and lon are both 0", nil},
		{"city area_km2 omitted", city(del("area_km2")), "$[0].area_km2: missing", nil},
		{"city area_km2 zero", city(set("area_km2", 0.0)), "area_km2 0 must be positive", nil},
		{"city population null", city(set("population", nil)), "$[0].population: null", nil},
		{"city tier not metro, large or mid", city(set("tier", "huge")), `tier "huge"`, nil},
		{"city aliases omitted", city(del("aliases")), "$[0].aliases: missing", nil},
		{"city data null", city(set("data", nil)), "$[0].data: want an object", nil},
		{"city best_area null", preset(set("best_area", nil)), "$[0].scores.balanced.best_area: want an object", nil},
		{"city score omitted", preset(del("score")), "$[0].scores.balanced.score: missing", nil},
		{"city score null", preset(set("score", nil)), "$[0].scores.balanced.score: null", nil},
		{"city access omitted", preset(del("access")), "$[0].scores.balanced.access: missing", nil},
		{"city momentum omitted", preset(del("momentum")), "$[0].scores.balanced.momentum: missing", nil},
		{"city coverage null", preset(set("coverage", nil)), "$[0].scores.balanced.coverage: null", nil},
		{"city coverage zero", preset(set("coverage", 0.0)), "coverage 0 and", nil},
		{"city coverage above 1", preset(set("coverage", 1.5)), "coverage 1.5 and", nil},
		{"city confidence null", preset(set("confidence", nil)), "$[0].scores.balanced.confidence: null", nil},
		{"city confidence zero", preset(set("confidence", 0.0)), "confidence 0 must", nil},
		{"city confidence above 1", preset(set("confidence", 1.5)), "confidence 1.5 must", nil},

		// areas/<city>.geojson
		{"cell pop omitted", cell(del("pop")), "properties.pop: missing", nil},
		{"cell pop null", cell(set("pop", nil)), "properties.pop: null", nil},
		{"cell elig omitted", cell(del("elig")), "properties.elig: missing", nil},
		{"cell score null", cell(inSub("sc", set("balanced", nil))), "properties.sc.balanced: null", nil},
		{"cell cov null", cell(set("cov", nil)), "properties.cov: null", nil},
		{"cell cov zero", cell(set("cov", 0.0)), "cov 0 and", nil},
		{"cell cov above 1", cell(set("cov", 1.2)), "cov 1.2 and", nil},
		{"cell conf null", cell(set("conf", nil)), "properties.conf: null", nil},
		{"cell conf zero", cell(set("conf", 0.0)), "conf 0 must", nil},
		{"cell conf above 1", cell(set("conf", 1.2)), "conf 1.2 must", nil},

		// assets/<city>.json: the provenance of the layers
		{"assets source omitted", assets(del("source")), "$.source: missing", nil},
		{"assets source empty", assets(set("source", "")), "source is empty", nil},
		{"assets fetched_at null", assets(set("fetched_at", nil)), "$.fetched_at: null", nil},
		{"assets license omitted", assets(del("license")), "$.license: missing", nil},
		{"assets license empty", assets(set("license", "")), "license is empty", nil},
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

// A list that a fixture writes as null still comes out as [] so no handler can serialise null. (A list whose
// key is left out is an error: see "city aliases omitted".)
func TestLoad_nullListsBecomeEmpty(t *testing.T) {
	dir := copyTestdata(t)
	editJSON(t, filepath.Join(dir, "cities.json"), func(r any) {
		for _, c := range arr(r) {
			if obj(c)["id"] == "pune" {
				obj(c)["aliases"] = nil
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

// Invariant 2: a value that may be unobserved (a pointer) loads as nil, and stays a key, so it can be shown as
// "—" and never as 0. The key still has to be there: see the "omitted" rows above.
func TestLoad_unobservedValuesStayNil(t *testing.T) {
	dir := copyTestdata(t)
	editJSON(t, filepath.Join(dir, "areas", "mumbai.geojson"), func(r any) {
		feature(r, 0)["f"].(map[string]any)["metro_access"] = nil
		feature(r, 0)["s"].(map[string]any)["metro_access"] = nil
		feature(r, 0)["name"] = nil
		feature(r, 0)["ac"].(map[string]any)["balanced"] = nil
	})
	editJSON(t, filepath.Join(dir, "cities.json"), func(r any) {
		for _, c := range arr(r) {
			if obj(c)["id"] == "mumbai" {
				bal := obj(obj(obj(c)["scores"])["balanced"])
				bal["access"], bal["momentum"] = nil, nil
			}
		}
	})

	s := mustLoad(t, dir)
	a, _ := s.Areas("mumbai")
	p := a.Features[0].Properties
	for name, m := range map[string]map[string]*float64{"f": p.F, "s": p.S} {
		if v, ok := m["metro_access"]; !ok || v != nil {
			t.Errorf("%s[metro_access] = %v (present=%v), want a nil entry", name, v, ok)
		}
	}
	if v, ok := p.Ac["balanced"]; !ok || v != nil || p.Name != nil {
		t.Errorf("ac[balanced] = %v (present=%v), name = %v, want both nil", v, ok, p.Name)
	}
	mumbai, _ := s.City("mumbai")
	if ps := mumbai.Scores["balanced"]; ps.Access != nil || ps.Momentum != nil {
		t.Errorf("mumbai balanced access/momentum = %v/%v, want nil", ps.Access, ps.Momentum)
	}
}

// --- parity with the Python scorer -------------------------------------------------------------------

// Stored numbers are one-decimal roundings, so each comparison carries the tolerance its rounding needs.
const (
	meanTol = 0.15 // a stored score against the weighted mean of stored sub-scores
	sumTol  = 0.2  // three rounded driver points, or one point, against the score they belong to
	eqTol   = 0.01 // one stored number quoting another
	covTol  = 0.05 // coverage may be stored to one decimal
)

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
	pune, _ := mustLoad(t, testdata).Areas("pune")
	ineligible := pune.Features[0].Properties // Wagholi: the cell that tops every preset but is too small to rank
	if ineligible.Elig {
		t.Fatal("the first Pune cell is meant to be ineligible")
	}

	inCity := func(id string, fn func(c map[string]any)) func(r any) {
		return func(r any) {
			for _, c := range arr(r) {
				if obj(c)["id"] == id {
					fn(obj(c))
				}
			}
		}
	}
	balanced := func(c map[string]any) map[string]any { return obj(obj(c["scores"])["balanced"]) }
	puneCell := func(i int, fn func(p map[string]any)) (string, func(r any)) {
		return "areas/pune.geojson", func(r any) { fn(feature(r, i)) }
	}
	type row struct {
		name, file string
		edit       func(r any)
		want       string
	}
	rows := []row{
		{"city score off its areas", "cities.json", inCity("pune", func(c map[string]any) { balanced(c)["score"] = 10.0 }), "population-weighted mean"},
		{"best_area score off the eligible maximum", "cities.json", inCity("pune", func(c map[string]any) { balanced(c)["best_area"].(map[string]any)["score"] = 99.0 }), "best_area.score"},
		{"best_area score off its own cell", "cities.json", inCity("pune", func(c map[string]any) { balanced(c)["best_area"].(map[string]any)["score"] = 74.0 }), "the cell's sc"},
		{"best_area names an ineligible cell", "cities.json", inCity("pune", func(c map[string]any) { balanced(c)["best_area"].(map[string]any)["id"] = ineligible.ID }), "is not an eligible cell"},
		{"factor unit off meta", "cities.json", inCity("delhi", func(c map[string]any) { obj(obj(c["factors"])["nh_access"])["unit"] = "mi" }), "factors.nh_access.unit"},
		{"driver unit off meta", "cities.json", inCity("delhi", func(c map[string]any) {
			obj(arr(balanced(c)["drivers"])[0])["unit"] = "mi"
		}), "driver nh_access unit"},
	}
	for _, c := range []struct {
		name string
		cell int
		edit func(p map[string]any)
		want string
	}{
		{"area score off its sub-scores", 0, func(p map[string]any) { p["sc"].(map[string]any)["balanced"] = 99.0 }, "weighted mean of s"},
		{"driver points above the score", 0, func(p map[string]any) {
			p["d"].(map[string]any)["balanced"] = []any{[]any{"nh_access", 60.0}, []any{"rail_access", 60.0}}
		}, "driver points sum"},
		{"driver points off w*s/sum(w)", 0, func(p map[string]any) {
			p["d"].(map[string]any)["balanced"] = []any{[]any{"built_up_growth", 5.0}}
		}, "driver built_up_growth: points"},
		{"gap value off the sub-score", 2, func(p map[string]any) {
			p["g"].(map[string]any)["balanced"] = []any{[]any{"metro_access", 20.0}}
		}, "gap metro_access: value"},
		{"ac off the access mean", 0, func(p map[string]any) { p["ac"].(map[string]any)["balanced"] = 10.0 }, "weighted mean of the access factors"},
		{"ac null though access factors were observed", 0, func(p map[string]any) { p["ac"].(map[string]any)["balanced"] = nil }, "ac is null"},
		{"ac given though no access factor was observed", 0, func(p map[string]any) {
			for _, f := range []string{"nh_access", "rail_access", "metro_access", "road_strength"} {
				p["s"].(map[string]any)[f] = nil
			}
		}, "but no access factor was observed"},
		{"cov off the observed weight", 0, func(p map[string]any) { p["cov"] = 0.5 }, "observed weight"},
		{"no weighted factor observed", 0, func(p map[string]any) {
			s := p["s"].(map[string]any)
			for k := range s {
				s[k] = nil
			}
		}, "no weighted factor observed"},
		{"eligible below the population minimum", 0, func(p map[string]any) { p["elig"] = true }, "elig = true"},
		{"ineligible above the population minimum", 1, func(p map[string]any) { p["elig"] = false }, "elig = false"},
	} {
		file, edit := puneCell(c.cell, c.edit)
		rows = append(rows, row{c.name, file, edit, c.want})
	}
	rows = append(rows, row{"no eligible area", "areas/nashik.geojson", func(r any) {
		for i := range arr(obj(r)["features"]) {
			feature(r, i)["elig"] = false
		}
	}, "no eligible area"})

	for _, tc := range rows {
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

// parity holds what meta.json says the stored numbers are made of.
type parity struct {
	weights  map[string]map[string]float64 // preset -> factor -> weight
	group    map[string]string             // factor -> access | momentum
	unit     map[string]string             // factor -> unit
	presets  []string
	def      string // the default preset: the one cov and conf, and the order of the file, describe
	minPop   float64
	problems []string
}

func (p *parity) addf(format string, args ...any) {
	p.problems = append(p.problems, fmt.Sprintf(format, args...))
}

// parityProblems returns every way the stored numbers disagree with what meta.json says they are made of.
func parityProblems(s *store.Store) []string {
	meta := s.Meta()
	p := &parity{
		weights: map[string]map[string]float64{}, group: map[string]string{}, unit: map[string]string{},
		presets: s.PresetIDs(), def: s.DefaultPreset(), minPop: float64(meta.Grid.BestAreaMinPopulation),
	}
	for _, pr := range meta.Presets {
		p.weights[pr.ID] = pr.Weights
	}
	for _, f := range meta.Factors {
		p.group[f.ID], p.unit[f.ID] = f.Group, f.Unit
	}
	checked := 0
	for _, c := range s.Cities() {
		areas, _ := s.Areas(c.ID)
		p.city(&c, areas)
		checked += len(areas.Features)
	}
	if checked == 0 {
		p.addf("no area was checked")
	}
	return p.problems
}

func (p *parity) city(c *store.City, areas *store.AreaSet) {
	for fid, fs := range c.Factors {
		if fs.Unit != p.unit[fid] {
			p.addf("%s: factors.%s.unit = %q, meta says %q", c.ID, fid, fs.Unit, p.unit[fid])
		}
	}
	// Spec section 4: a cell is eligible from the population minimum; with fewer than 3 such cells all count.
	qualifying := 0
	cells := map[string]store.AreaProps{}
	for _, f := range areas.Features {
		cells[f.Properties.ID] = f.Properties
		if f.Properties.Pop >= p.minPop {
			qualifying++
		}
	}
	for _, f := range areas.Features {
		a := f.Properties
		if want := qualifying < 3 || a.Pop >= p.minPop; a.Elig != want {
			p.addf("%s/%s: elig = %v, but pop %.0f (minimum %.0f, %d cells qualify) makes it %v",
				c.ID, a.ID, a.Elig, a.Pop, p.minPop, qualifying, want)
		}
		p.cell(c.ID, a)
	}
	for _, pid := range p.presets {
		p.cityScore(c, pid, areas, cells)
	}
}

// cell checks one cell under every preset, and its coverage under the default one.
func (p *parity) cell(city string, a store.AreaProps) {
	for _, pid := range p.presets {
		at := fmt.Sprintf("%s/%s preset %s", city, a.ID, pid)
		w := p.weights[pid]
		var obsW, num, accN, accW float64 // observed weight, weighted sum, and the same over the access group
		for fid, sub := range a.S {
			if sub == nil || w[fid] == 0 {
				continue
			}
			obsW += w[fid]
			num += w[fid] * *sub
			if p.group[fid] == "access" {
				accN += w[fid] * *sub
				accW += w[fid]
			}
		}
		if obsW == 0 {
			p.addf("%s: no weighted factor observed, so there is no score to store", at)
			continue
		}
		sc := a.Sc[pid]
		if want := num / obsW; math.Abs(sc-want) > meanTol {
			p.addf("%s: sc = %.2f, weighted mean of s = %.2f", at, sc, want)
		}
		switch ac := a.Ac[pid]; {
		case accW == 0 && ac != nil:
			p.addf("%s: ac = %.2f, but no access factor was observed", at, *ac)
		case accW > 0 && ac == nil:
			p.addf("%s: ac is null, but access factors were observed", at)
		case accW > 0 && math.Abs(*ac-accN/accW) > meanTol:
			p.addf("%s: ac = %.2f, weighted mean of the access factors = %.2f", at, *ac, accN/accW)
		}
		var top float64
		for _, d := range a.D[pid] {
			top += d.Value
			sub := a.S[d.Factor]
			if sub == nil || w[d.Factor] == 0 {
				p.addf("%s: driver %s is not an observed, weighted factor", at, d.Factor)
				continue
			}
			if want := w[d.Factor] * *sub / obsW; math.Abs(d.Value-want) > sumTol {
				p.addf("%s: driver %s: points %.2f, w*s/sum(w) = %.2f", at, d.Factor, d.Value, want)
			}
		}
		if top > sc+sumTol {
			p.addf("%s: driver points sum to %.2f, above sc %.2f", at, top, sc)
		}
		for _, g := range a.G[pid] {
			switch sub := a.S[g.Factor]; {
			case sub == nil:
				p.addf("%s: gap %s is not observed", at, g.Factor)
			case math.Abs(g.Value-*sub) > eqTol:
				p.addf("%s: gap %s: value %.2f, s = %.2f", at, g.Factor, g.Value, *sub)
			}
		}
	}
	var covW float64
	for fid, sub := range a.S {
		if sub != nil {
			covW += p.weights[p.def][fid]
		}
	}
	if math.Abs(a.Cov-covW) > covTol {
		p.addf("%s/%s: cov = %.2f, observed weight under %s = %.2f", city, a.ID, a.Cov, p.def, covW)
	}
}

// cityScore checks a city's score, best area and units under one preset.
func (p *parity) cityScore(c *store.City, pid string, areas *store.AreaSet, cells map[string]store.AreaProps) {
	at := fmt.Sprintf("%s preset %s", c.ID, pid)
	ps := c.Scores[pid]
	var popSum, scoreSum, bestElig float64
	eligible := false
	for _, f := range areas.Features {
		a := f.Properties
		popSum += a.Pop
		scoreSum += a.Pop * a.Sc[pid]
		if a.Elig {
			eligible = true
			bestElig = math.Max(bestElig, a.Sc[pid])
		}
	}
	switch {
	case !eligible:
		p.addf("%s: no eligible area, so best_area cannot exist", at)
	case math.Abs(ps.BestArea.Score-bestElig) > meanTol:
		p.addf("%s: best_area.score = %.2f, highest eligible sc = %.2f", at, ps.BestArea.Score, bestElig)
	}
	if best, ok := cells[ps.BestArea.ID]; ok { // Load guarantees the cell exists
		switch {
		case !best.Elig:
			p.addf("%s: best_area %s is not an eligible cell", at, best.ID)
		case math.Abs(best.Sc[pid]-ps.BestArea.Score) > eqTol:
			p.addf("%s: best_area.score = %.2f, but the cell's sc is %.2f", at, ps.BestArea.Score, best.Sc[pid])
		}
	}
	// The city score is the population-weighted mean of its areas' scores (spec section 4).
	if popSum == 0 {
		p.addf("%s: areas have no population", at)
	} else if want := scoreSum / popSum; math.Abs(ps.Score-want) > meanTol {
		p.addf("%s: score = %.2f, population-weighted mean of area scores = %.2f", at, ps.Score, want)
	}
	for _, d := range ps.Drivers {
		if d.Unit != p.unit[d.Factor] {
			p.addf("%s: driver %s unit = %q, meta says %q", at, d.Factor, d.Unit, p.unit[d.Factor])
		}
	}
	for _, g := range ps.Gaps {
		if g.Unit != p.unit[g.Factor] {
			p.addf("%s: gap %s unit = %q, meta says %q", at, g.Factor, g.Unit, p.unit[g.Factor])
		}
	}
}
