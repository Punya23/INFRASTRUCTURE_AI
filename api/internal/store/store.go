// Package store loads the investor fixtures (spec §6) into memory, validates them, and serves read-only
// lookups. It holds no scoring logic: scores, sub-scores and drivers are the pipeline's stored values, and
// TestParity ties them back to the scoring model.
//
// Load fails closed (AGENTS invariant 2). Start-up stops, with an error that names the file and the field, on:
//   - an unknown field, or data after the JSON value;
//   - a missing field, or a null in a field that is not nullable (only pointers, lists and maps may be null),
//     so a required number is never read as 0;
//   - a value out of range: coverage, confidence, area_km2, the grid and tier thresholds, the tier name;
//   - a factor, preset, state or best-area reference that does not resolve, preset weights that do not sum
//     to 1, and files that disagree with each other (city_count, cells, bus stops without a source).
//
// A Store never changes after Load, so it is safe for concurrent use. Accessors return copies of their
// lists; the values those copies point to are shared with the Store and must not be modified.
package store

import (
	"bytes"
	"cmp"
	"compress/gzip"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
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

// Meta returns meta.json. The Factors, Presets and Sources lists are copies; the weights, bands and other
// values inside them are shared with the Store.
func (s *Store) Meta() Meta {
	m := s.meta
	m.Factors, m.Presets, m.Sources = slices.Clone(m.Factors), slices.Clone(m.Presets), slices.Clone(m.Sources)
	return m
}

// States returns a copy of states.json, in file order.
func (s *Store) States() []State { return slices.Clone(s.states) }

// Cities returns a copy of the cities in cities.json order (the exporter writes population, descending; Load does not enforce it). Each City is a copy
// too, but the maps and slices inside it are shared with the Store: read them, never modify them.
func (s *Store) Cities() []City { return slices.Clone(s.cities) }

// City looks up a city by id. The pointer is into the Store and read-only.
func (s *Store) City(id string) (*City, bool) {
	c, ok := s.byID[id]
	return c, ok
}

// Areas returns a city's H3 cells as stored. The pipeline writes them sorted by the balanced score; ranking
// for another preset is the caller's job. The pointer is into the Store and read-only.
func (s *Store) Areas(id string) (*AreaSet, bool) {
	a, ok := s.areas[id]
	return a, ok
}

// Assets returns a city's map layers. The pointer is into the Store and read-only.
func (s *Store) Assets(id string) (*AssetSet, bool) {
	a, ok := s.assets[id]
	return a, ok
}

// CitiesInState returns a copy of the list of a state's cities, largest first. A state with no city, and an
// unknown code, both give an empty slice; HasState tells them apart. The *City values point into the Store
// and are read-only.
func (s *Store) CitiesInState(code string) []*City {
	if l, ok := s.byState[code]; ok {
		return slices.Clone(l)
	}
	return []*City{}
}

// HasState reports whether code is listed in states.json.
func (s *Store) HasState(code string) bool {
	_, ok := s.byState[code]
	return ok
}

// PresetIDs returns a copy of the preset ids in meta.json order.
func (s *Store) PresetIDs() []string { return slices.Clone(s.presetIDs) }

// DefaultPreset returns the id of the preset marked default.
func (s *Store) DefaultPreset() string { return s.defaultPreset }

// --- loading -----------------------------------------------------------------------------------------

func (s *Store) loadMeta(path string) error {
	if err := readJSON(path, &s.meta); err != nil {
		return err
	}
	if err := s.checkMeta(); err != nil {
		return fmt.Errorf("%s: %w", path, err)
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

// --- reading -----------------------------------------------------------------------------------------

// readJSON decodes one JSON document (gzip when the name ends in .gz) into v. Unknown fields, data after the
// value, a missing field and a null in a field that cannot be null are all errors (see requireFields): a
// fixture that drifts from the contract must stop start-up, not be half-read.
func readJSON(path string, v any) error {
	data, err := readFile(path)
	if err != nil {
		return err
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	if _, err := dec.Token(); err != io.EOF {
		if err != nil {
			return fmt.Errorf("%s: %w", path, err)
		}
		return fmt.Errorf("%s: unexpected data after the JSON value", path)
	}
	// The typed decode reads a missing or null number as 0, so look at the document itself as well.
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	if err := requireFields(raw, reflect.TypeOf(v).Elem(), "$"); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	return nil
}

// readFile returns the content of a fixture, gunzipped when the name ends in .gz. Reading a gzip file to the
// end also verifies its checksum.
func readFile(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err // a *fs.PathError already names the path
	}
	defer f.Close()

	var r io.Reader = f
	if filepath.Ext(path) == ".gz" {
		zr, err := gzip.NewReader(f)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		defer zr.Close()
		r = zr
	}
	data, err := io.ReadAll(r)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return data, nil
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
