package store

import (
	"encoding/json"
	"errors"
	"fmt"
	"maps"
	"math"
	"reflect"
	"slices"
	"strings"
)

var unmarshalerType = reflect.TypeFor[json.Unmarshaler]()

// requireFields checks a decoded JSON document (raw) against the Go type it was decoded into. encoding/json
// leaves a field it never saw, and a field that was null, at its zero value, so a required number that is
// missing would quietly load as 0. The contract is that every field is always present and that only a
// pointer, a list or a map may be null (a null list becomes an empty one: see nonNil). Types that decode
// themselves (FactorPoint, json.RawMessage) are not looked into.
func requireFields(raw any, t reflect.Type, path string) error {
	if reflect.PointerTo(t).Implements(unmarshalerType) {
		return nil
	}
	switch t.Kind() {
	case reflect.Pointer:
		if raw == nil {
			return nil
		}
		return requireFields(raw, t.Elem(), path)
	case reflect.Struct:
		fields, ok := raw.(map[string]any)
		if !ok {
			return fmt.Errorf("%s: want an object", path)
		}
		return requireStruct(fields, t, path)
	case reflect.Slice:
		list, _ := raw.([]any) // the typed decode has already rejected any other shape
		for i, e := range list {
			if err := requireFields(e, t.Elem(), fmt.Sprintf("%s[%d]", path, i)); err != nil {
				return err
			}
		}
	case reflect.Map:
		entries, _ := raw.(map[string]any)
		for _, k := range slices.Sorted(maps.Keys(entries)) {
			if err := requireFields(entries[k], t.Elem(), path+"."+k); err != nil {
				return err
			}
		}
	default: // a number, string or bool
		if raw == nil {
			return fmt.Errorf("%s: null, but this field cannot be null", path)
		}
	}
	return nil
}

// requireStruct requires every field of the struct type t to be a key of obj, then looks into its value.
func requireStruct(obj map[string]any, t reflect.Type, path string) error {
	for i := range t.NumField() {
		f := t.Field(i)
		if !f.IsExported() {
			continue
		}
		name, _, _ := strings.Cut(f.Tag.Get("json"), ",")
		if f.Anonymous && name == "" { // an embedded struct (Provenance) shares its parent's object
			if err := requireStruct(obj, f.Type, path); err != nil {
				return err
			}
			continue
		}
		if name == "" {
			name = f.Name
		}
		v, ok := obj[name]
		if !ok {
			return fmt.Errorf("%s.%s: missing", path, name)
		}
		if err := requireFields(v, f.Type, path+"."+name); err != nil {
			return err
		}
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
	if g := m.Grid; g.H3Res <= 0 || g.MinAreaPopulation <= 0 || g.BestAreaMinPopulation <= 0 {
		return fmt.Errorf("grid: h3_res %d, min_area_population %d and best_area_min_population %d must be positive",
			g.H3Res, g.MinAreaPopulation, g.BestAreaMinPopulation)
	}
	if t := m.Tiers; t.LargeMinPopulation <= 0 || t.MetroMinPopulation <= t.LargeMinPopulation {
		return fmt.Errorf("tiers: metro_min_population %d must be above large_min_population %d, which must be above 0",
			t.MetroMinPopulation, t.LargeMinPopulation)
	}
	if len(m.Sources) == 0 {
		return errors.New("sources: none listed, but every source needs its license and attribution")
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
		[2]string{"name", c.Name}, [2]string{"source", c.Source}, [2]string{"source_ref", c.SourceRef},
		[2]string{"fetched_at", c.FetchedAt}, [2]string{"license", c.License},
	); err != nil {
		return err
	}
	if !slices.Contains([]string{"metro", "large", "mid"}, c.Tier) {
		return fmt.Errorf("tier %q is not metro, large or mid", c.Tier)
	}
	if _, ok := s.byState[c.State]; !ok {
		return fmt.Errorf("state %q is not in states.json", c.State)
	}
	if c.Population <= 0 || c.Cells <= 0 || c.Confidence <= 0 || c.Confidence > 1 {
		return fmt.Errorf("population %g, cells %d and confidence %g must be positive (confidence at most 1)",
			c.Population, c.Cells, c.Confidence)
	}
	if c.AreaKm2 <= 0 {
		return fmt.Errorf("area_km2 %g must be positive", c.AreaKm2)
	}
	if c.Lat == 0 && c.Lon == 0 {
		return errors.New("lat and lon are both 0")
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
		if ps.Coverage <= 0 || ps.Coverage > 1 || ps.Confidence <= 0 || ps.Confidence > 1 {
			return fmt.Errorf("scores.%s: coverage %g and confidence %g must be in (0, 1]", pid, ps.Coverage, ps.Confidence)
		}
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
	if p.Cov <= 0 || p.Cov > 1 || p.Conf <= 0 || p.Conf > 1 {
		return fmt.Errorf("cov %g and conf %g must be in (0, 1]", p.Cov, p.Conf)
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
	if err := requireText([2]string{"source", a.Source}, [2]string{"fetched_at", a.FetchedAt}, [2]string{"license", a.License}); err != nil {
		return err
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
