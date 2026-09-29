// Package store loads the investor fixtures (spec §6) into memory, validates them, and serves read-only
// lookups. It holds no scoring logic: scores, sub-scores and drivers are the pipeline's stored values, and
// TestParity ties them back to the scoring model.
//
// Load fails closed (AGENTS invariant 2): an unknown or missing field, a dangling reference, or files that
// disagree with each other stop start-up with an error naming the file and the field. A Store never changes
// after Load, so it is safe for concurrent use; callers must not modify what it returns.
package store

import (
	"cmp"
	"compress/gzip"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"slices"
)

var (
	idPattern        = regexp.MustCompile(`^[a-z0-9-]{2,64}$`)
	stateCodePattern = regexp.MustCompile(`^[A-Z]{2}$`)
)

// Store is the in-memory dataset. Every accessor that returns a slice returns a non-nil one, so an empty
// list is [] in JSON, never null.
type Store struct {
	meta          Meta
	states        []State
	cities        []City
	byID          map[string]*City
	byState       map[string][]*City // one entry per state in states.json, possibly empty
	areas         map[string]*AreaSet
	assets        map[string]*AssetSet
	factorIDs     map[string]bool
	presetIDs     []string
	presetSet     map[string]bool
	defaultPreset string
}

// Load reads meta.json, states.json and cities.json from dir, then areas/<id>.geojson[.gz] and
// assets/<id>.json[.gz] for every city, and validates them. The first problem is returned wrapped with %w
// and the path of the file it was found in.
func Load(dir string) (*Store, error) {
	s := &Store{
		byID:    map[string]*City{},
		byState: map[string][]*City{},
		areas:   map[string]*AreaSet{},
		assets:  map[string]*AssetSet{},
	}
	statesPath := filepath.Join(dir, "states.json")
	if err := s.loadMeta(filepath.Join(dir, "meta.json")); err != nil {
		return nil, err
	}
	if err := s.loadStates(statesPath); err != nil {
		return nil, err
	}
	if err := s.loadCities(filepath.Join(dir, "cities.json")); err != nil {
		return nil, err
	}
	if err := s.checkCityCounts(); err != nil {
		return nil, fmt.Errorf("%s: %w", statesPath, err)
	}
	for i := range s.cities {
		if err := s.loadCityFiles(dir, &s.cities[i]); err != nil {
			return nil, err
		}
	}
	for _, l := range s.byState { // largest city first; id keeps the order stable
		slices.SortFunc(l, func(a, b *City) int {
			return cmp.Or(cmp.Compare(b.Population, a.Population), cmp.Compare(a.ID, b.ID))
		})
	}
	return s, nil
}

// Meta returns meta.json.
func (s *Store) Meta() Meta { return s.meta }

// States returns states.json in file order.
func (s *Store) States() []State { return s.states }

// Cities returns every city in cities.json order (population, descending).
func (s *Store) Cities() []City { return s.cities }

// City looks up a city by id.
func (s *Store) City(id string) (*City, bool) {
	c, ok := s.byID[id]
	return c, ok
}

// Areas returns a city's H3 cells as stored. The pipeline writes them sorted by the balanced score; ranking
// for another preset is the caller's job.
func (s *Store) Areas(id string) (*AreaSet, bool) {
	a, ok := s.areas[id]
	return a, ok
}

// Assets returns a city's map layers.
func (s *Store) Assets(id string) (*AssetSet, bool) {
	a, ok := s.assets[id]
	return a, ok
}

// CitiesInState returns the cities of a state, largest first. A state with no city, and an unknown code,
// both give an empty slice; HasState tells them apart.
func (s *Store) CitiesInState(code string) []*City {
	if l, ok := s.byState[code]; ok {
		return l
	}
	return []*City{}
}

// HasState reports whether code is listed in states.json.
func (s *Store) HasState(code string) bool {
	_, ok := s.byState[code]
	return ok
}

// PresetIDs returns the preset ids in meta.json order.
func (s *Store) PresetIDs() []string { return s.presetIDs }

// DefaultPreset returns the id of the preset marked default.
func (s *Store) DefaultPreset() string { return s.defaultPreset }

// --- reading -----------------------------------------------------------------------------------------

// readJSON decodes one JSON document (gzip when the name ends in .gz) into v. Unknown fields and trailing
// data are errors: a fixture that drifts from the contract must stop start-up, not be half-read.
func readJSON(path string, v any) error {
	f, err := os.Open(path)
	if err != nil {
		return err // a *fs.PathError already names the path
	}
	defer f.Close()

	var r io.Reader = f
	if filepath.Ext(path) == ".gz" {
		zr, err := gzip.NewReader(f)
		if err != nil {
			return fmt.Errorf("%s: %w", path, err)
		}
		defer zr.Close()
		r = zr
	}
	dec := json.NewDecoder(r)
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	if _, err := dec.Token(); err != io.EOF {
		if err != nil { // reading on to the end also verifies the gzip trailer
			return fmt.Errorf("%s: %w", path, err)
		}
		return fmt.Errorf("%s: unexpected data after the JSON value", path)
	}
	return nil
}

// fixturePath returns dir/sub/name or dir/sub/name.gz; exactly one of the two must exist.
func fixturePath(dir, sub, name string) (string, error) {
	plain := filepath.Join(dir, sub, name)
	_, errPlain := os.Stat(plain)
	_, errGzip := os.Stat(plain + ".gz")
	switch {
	case errPlain == nil && errGzip == nil:
		return "", fmt.Errorf("%s: both the plain and the .gz file exist; keep one", plain)
	case errPlain == nil:
		return plain, nil
	case errGzip == nil:
		return plain + ".gz", nil
	case errors.Is(errPlain, fs.ErrNotExist):
		return "", fmt.Errorf("%s[.gz]: %w", plain, fs.ErrNotExist)
	}
	return "", errPlain
}

// loadFixture reads and checks one per-city file.
func loadFixture[T any](dir, sub, name string, check func(*T) error) (*T, error) {
	path, err := fixturePath(dir, sub, name)
	if err != nil {
		return nil, err
	}
	v := new(T)
	if err := readJSON(path, v); err != nil {
		return nil, err
	}
	if err := check(v); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return v, nil
}

// --- validation --------------------------------------------------------------------------------------

func (s *Store) loadMeta(path string) error {
	if err := readJSON(path, &s.meta); err != nil {
		return err
	}
	if err := s.checkMeta(); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	return nil
}

// checkMeta validates the scoring model and builds the factor and preset indexes every other file is
// checked against.
func (s *Store) checkMeta() error {
	m := &s.meta
	if m.SchemaVersion != 1 {
		return fmt.Errorf("schema_version is %d, this build reads 1", m.SchemaVersion)
	}
	if err := requireText([2]string{"as_of", m.AsOf}, [2]string{"disclaimer", m.Disclaimer}); err != nil {
		return err
	}
	s.factorIDs = map[string]bool{}
	for _, f := range m.Factors {
		if f.ID == "" || s.factorIDs[f.ID] {
			return fmt.Errorf("factors: empty or duplicate id %q", f.ID)
		}
		s.factorIDs[f.ID] = true
	}
	s.presetSet = map[string]bool{}
	defaults := 0
	for _, p := range m.Presets {
		if p.ID == "" || s.presetSet[p.ID] {
			return fmt.Errorf("presets: empty or duplicate id %q", p.ID)
		}
		s.presetSet[p.ID] = true
		s.presetIDs = append(s.presetIDs, p.ID)
		if err := checkKeys("weights of preset "+p.ID, "factor", p.Weights, s.factorIDs); err != nil {
			return err
		}
		sum := 0.0
		for _, w := range p.Weights {
			if w < 0 {
				return fmt.Errorf("preset %q: negative weight", p.ID)
			}
			sum += w
		}
		if math.Abs(sum-1) > 1e-6 {
			return fmt.Errorf("preset %q: weights sum to %.3f, want 1", p.ID, sum)
		}
		if p.Default {
			defaults++
			s.defaultPreset = p.ID
		}
	}
	if defaults != 1 {
		return fmt.Errorf("presets: %d marked default, want exactly 1", defaults)
	}
	return nil
}

func (s *Store) loadStates(path string) error {
	if err := readJSON(path, &s.states); err != nil {
		return err
	}
	if len(s.states) == 0 {
		return fmt.Errorf("%s: no states", path)
	}
	for i, st := range s.states {
		var err error
		switch _, dup := s.byState[st.Code]; {
		case !stateCodePattern.MatchString(st.Code):
			err = fmt.Errorf("code %q does not match %s", st.Code, stateCodePattern)
		case dup:
			err = fmt.Errorf("duplicate code %q", st.Code)
		case st.Name == "" || st.CityCount < 0:
			err = fmt.Errorf("name %q and city_count %d must be set and non-negative", st.Name, st.CityCount)
		}
		if err != nil {
			return fmt.Errorf("%s: state %d: %w", path, i, err)
		}
		s.byState[st.Code] = []*City{}
	}
	return nil
}

func (s *Store) loadCities(path string) error {
	if err := readJSON(path, &s.cities); err != nil {
		return err
	}
	if len(s.cities) == 0 {
		return fmt.Errorf("%s: no cities", path)
	}
	for i := range s.cities {
		c := &s.cities[i]
		// The id is checked before anything builds a file name from it.
		if !idPattern.MatchString(c.ID) {
			return fmt.Errorf("%s: city %d: id %q does not match %s", path, i, c.ID, idPattern)
		}
		if s.byID[c.ID] != nil {
			return fmt.Errorf("%s: duplicate city id %q", path, c.ID)
		}
		if err := s.checkCity(c); err != nil {
			return fmt.Errorf("%s: city %q: %w", path, c.ID, err)
		}
		s.byID[c.ID] = c
		s.byState[c.State] = append(s.byState[c.State], c)
	}
	return nil
}

// checkCityCounts requires states.json city_count to match the cities that were actually loaded: the UI
// prints both, and a mismatch means the two files came from different runs.
func (s *Store) checkCityCounts() error {
	for _, st := range s.states {
		if got := len(s.byState[st.Code]); got != st.CityCount {
			return fmt.Errorf("state %q has city_count %d, but cities.json lists %d", st.Code, st.CityCount, got)
		}
	}
	return nil
}

func (s *Store) checkCity(c *City) error {
	if err := requireText(
		[2]string{"name", c.Name}, [2]string{"tier", c.Tier}, [2]string{"source", c.Source},
		[2]string{"source_ref", c.SourceRef}, [2]string{"fetched_at", c.FetchedAt}, [2]string{"license", c.License},
	); err != nil {
		return err
	}
	if _, ok := s.byState[c.State]; !ok {
		return fmt.Errorf("state %q is not in states.json", c.State)
	}
	if c.Population <= 0 || c.Cells <= 0 || c.Confidence <= 0 || c.Confidence > 1 {
		return fmt.Errorf("population %g, cells %d and confidence %g must be positive (confidence at most 1)",
			c.Population, c.Cells, c.Confidence)
	}
	if b := c.Data.Bus; b != nil {
		if err := requireText([2]string{"data.bus.operator", b.Operator}, [2]string{"data.bus.tier", b.Tier}); err != nil {
			return err
		}
	}
	if err := checkKeys("factors", "factor", c.Factors, s.factorIDs); err != nil {
		return err
	}
	if err := checkKeys("scores", "preset", c.Scores, s.presetSet); err != nil {
		return err
	}
	for _, pid := range s.presetIDs {
		ps := c.Scores[pid]
		if ps.BestArea.ID == "" {
			return fmt.Errorf("scores.%s.best_area: id is empty", pid)
		}
		for _, d := range ps.Drivers {
			if !s.factorIDs[d.Factor] {
				return fmt.Errorf("scores.%s.drivers: unknown factor %q", pid, d.Factor)
			}
		}
		for _, g := range ps.Gaps {
			if !s.factorIDs[g.Factor] {
				return fmt.Errorf("scores.%s.gaps: unknown factor %q", pid, g.Factor)
			}
		}
		ps.Drivers, ps.Gaps = nonNil(ps.Drivers), nonNil(ps.Gaps)
		c.Scores[pid] = ps
	}
	c.Aliases = nonNil(c.Aliases)
	return nil
}

func (s *Store) loadCityFiles(dir string, c *City) error {
	areas, err := loadFixture(dir, "areas", c.ID+".geojson", func(a *AreaSet) error { return s.checkAreas(c, a) })
	if err != nil {
		return err
	}
	assets, err := loadFixture(dir, "assets", c.ID+".json", func(a *AssetSet) error { return checkAssets(c, a) })
	if err != nil {
		return err
	}
	s.areas[c.ID], s.assets[c.ID] = areas, assets
	return nil
}

func (s *Store) checkAreas(c *City, a *AreaSet) error {
	if a.Type != "FeatureCollection" {
		return fmt.Errorf(`type %q, want "FeatureCollection"`, a.Type)
	}
	if a.City != c.ID {
		return fmt.Errorf("city is %q, want %q", a.City, c.ID)
	}
	if err := requireText([2]string{"source", a.Source}, [2]string{"fetched_at", a.FetchedAt}, [2]string{"license", a.License}); err != nil {
		return err
	}
	if len(a.Features) != c.Cells {
		return fmt.Errorf("%d features, but cities.json says cells is %d", len(a.Features), c.Cells)
	}
	ids := make(map[string]bool, len(a.Features))
	for i := range a.Features {
		ft := &a.Features[i]
		if err := s.checkFeature(ft); err != nil {
			return fmt.Errorf("feature %d (id %q): %w", i, ft.Properties.ID, err)
		}
		if ids[ft.Properties.ID] {
			return fmt.Errorf("feature %d: duplicate id %q", i, ft.Properties.ID)
		}
		ids[ft.Properties.ID] = true
	}
	for _, pid := range s.presetIDs {
		if best := c.Scores[pid].BestArea.ID; !ids[best] {
			return fmt.Errorf("best_area %q of preset %q (cities.json) is not a feature of this file", best, pid)
		}
	}
	return nil
}

func (s *Store) checkFeature(ft *AreaFeature) error {
	p := &ft.Properties
	if ft.Type != "Feature" {
		return fmt.Errorf(`type %q, want "Feature"`, ft.Type)
	}
	if len(ft.Geometry) == 0 || string(ft.Geometry) == "null" {
		return errors.New("geometry is missing")
	}
	if err := requireText([2]string{"id", p.ID}, [2]string{"source_ref", p.SourceRef}); err != nil {
		return err
	}
	if p.Pop < 0 {
		return fmt.Errorf("pop %g is negative", p.Pop)
	}
	for _, err := range []error{
		checkKeys("f", "factor", p.F, s.factorIDs),
		checkKeys("s", "factor", p.S, s.factorIDs),
		checkKeys("sc", "preset", p.Sc, s.presetSet),
		checkKeys("ac", "preset", p.Ac, s.presetSet),
	} {
		if err != nil {
			return err
		}
	}
	for _, l := range []struct {
		what string
		m    map[string][]FactorPoint
	}{{"d", p.D}, {"g", p.G}} {
		if err := checkKeys(l.what, "preset", l.m, s.presetSet); err != nil {
			return err
		}
		for pid, pts := range l.m {
			for _, fp := range pts {
				if !s.factorIDs[fp.Factor] {
					return fmt.Errorf("%s.%s: unknown factor %q", l.what, pid, fp.Factor)
				}
			}
			l.m[pid] = nonNil(pts)
		}
	}
	return nil
}

func checkAssets(c *City, a *AssetSet) error {
	if a.City != c.ID {
		return fmt.Errorf("city is %q, want %q", a.City, c.ID)
	}
	for _, err := range []error{
		checkCollection("stations", &a.Stations),
		checkCollection("highways", &a.Highways),
		checkCollection("toll_plazas", &a.TollPlazas),
	} {
		if err != nil {
			return err
		}
	}
	if a.BusStops != nil {
		if err := checkCollection("bus_stops", a.BusStops); err != nil {
			return err
		}
	}
	if (a.BusStops == nil) != (a.BusSource == nil) {
		return errors.New("bus_stops and bus_source must both be present or both null: bus stops need their provenance")
	}
	if b := a.BusSource; b != nil {
		return requireText([2]string{"bus_source.operator", b.Operator}, [2]string{"bus_source.tier", b.Tier},
			[2]string{"bus_source.license", b.License}, [2]string{"bus_source.fetched_at", b.FetchedAt})
	}
	return nil
}

func checkCollection(name string, fc *FeatureCollection) error {
	if fc.Type != "FeatureCollection" || fc.Features == nil {
		return fmt.Errorf(`%s: want a "FeatureCollection" with a features list, got type %q`, name, fc.Type)
	}
	return nil
}

// checkKeys requires got to have exactly the keys in want (factor ids or preset ids).
func checkKeys[V any](what, kind string, got map[string]V, want map[string]bool) error {
	for k := range got {
		if !want[k] {
			return fmt.Errorf("%s: unknown %s %q", what, kind, k)
		}
	}
	for k := range want {
		if _, ok := got[k]; !ok {
			return fmt.Errorf("%s: missing %s %q", what, kind, k)
		}
	}
	return nil
}

// requireText returns an error naming the first {name, value} pair whose value is empty.
func requireText(fields ...[2]string) error {
	for _, f := range fields {
		if f[1] == "" {
			return fmt.Errorf("%s is empty", f[0])
		}
	}
	return nil
}

// nonNil turns a missing list into an empty one so it serialises as [] rather than null.
func nonNil[T any](s []T) []T {
	if s == nil {
		return []T{}
	}
	return s
}
