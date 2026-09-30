package httpapi

import (
	"cmp"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"net/http"
	"net/url"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// The contract's two id patterns (openapi.yaml). An id is only ever looked up in memory, never used to build
// a path.
var (
	idPattern        = regexp.MustCompile(`^[a-z0-9-]{2,64}$`)
	stateCodePattern = regexp.MustCompile(`^[A-Z]{2}$`)
)

// layerNames are the map layers of /assets, in the contract's order.
var layerNames = []string{"stations", "bus_stops", "highways", "toll_plazas"}

// The length of a search text, in characters.
const (
	minSearch = 2
	maxSearch = 64
)

// api is what the handlers share. It is read-only after newAPI, so requests need no lock.
type api struct {
	store   *store.Store
	cities  []*store.City     // every city, for search and compare
	presets []string          // preset ids, in meta.json order
	units   map[string]string // factor id -> unit, for the drivers and gaps of an area
}

func newAPI(s *store.Store) *api {
	all := s.Cities()
	a := &api{store: s, cities: make([]*store.City, len(all)), presets: s.PresetIDs(), units: map[string]string{}}
	for i := range all {
		a.cities[i] = &all[i]
	}
	for _, f := range s.Meta().Factors {
		a.units[f.ID] = f.Unit
	}
	return a
}

// --- answering -------------------------------------------------------------------------------------------

// writeJSON answers 200 with v. The body is built first, so an encoding failure is a clean 500 and never a
// half-written 200.
func writeJSON(w http.ResponseWriter, v any) {
	body, err := json.Marshal(v)
	if err != nil {
		internalError(w, "encode response", "err", err)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(body) // a write fails only when the client has left or the request timed out: nothing to recover
}

// internalError logs what went wrong and answers a 500 that says nothing about it.
func internalError(w http.ResponseWriter, msg string, args ...any) {
	slog.Error(msg, args...)
	writeError(w, http.StatusInternalServerError, "internal", "internal error")
}

// bad answers 400 for a parameter error and reports whether it did. Parameter errors are worded for the
// client and never echo the value they reject.
func bad(w http.ResponseWriter, err error) bool {
	if err == nil {
		return false
	}
	writeError(w, http.StatusBadRequest, "bad_request", err.Error())
	return true
}

// notFound is the catch-all route: an unknown path, or a method the API does not have, is a JSON 404 rather
// than the mux's plain text.
func notFound(w http.ResponseWriter, _ *http.Request) {
	writeError(w, http.StatusNotFound, "not_found", "no such endpoint")
}

// --- parameters ------------------------------------------------------------------------------------------

func validate(v string, re *regexp.Regexp, what string) error {
	if !re.MatchString(v) {
		return fmt.Errorf("%s must match %s", what, re)
	}
	return nil
}

// parsePreset returns the preset asked for, the default one when the parameter is absent, and an error for
// anything else - including an empty value.
func (a *api) parsePreset(q url.Values) (string, error) {
	if !q.Has("preset") {
		return a.store.DefaultPreset(), nil
	}
	if p := q.Get("preset"); slices.Contains(a.presets, p) {
		return p, nil
	}
	return "", fmt.Errorf("preset must be one of %s", strings.Join(a.presets, ", "))
}

// parseLimit reads limit as an integer from lo to hi; absent means def. An out-of-range value is an error,
// never clamped.
func parseLimit(q url.Values, lo, hi, def int) (int, error) {
	if !q.Has("limit") {
		return def, nil
	}
	n, err := strconv.Atoi(q.Get("limit"))
	if err != nil || n < lo || n > hi {
		return 0, fmt.Errorf("limit must be an integer from %d to %d", lo, hi)
	}
	return n, nil
}

// parseScope returns the compare scope, or "" when the parameter is absent (compare then picks the default).
func parseScope(q url.Values) (string, error) {
	if !q.Has("scope") {
		return "", nil
	}
	if s := q.Get("scope"); scopes[s] != nil {
		return s, nil
	}
	return "", errors.New("scope must be one of metros, peers, state, india")
}

// parseLayers returns the set of layers asked for: all four when the parameter is absent, else the
// comma-separated list, which may not be empty or hold an unknown name. A layer named twice is one layer.
func parseLayers(q url.Values) (map[string]bool, error) {
	raw := strings.Join(layerNames, ",")
	if q.Has("layers") {
		raw = q.Get("layers")
	}
	want := map[string]bool{}
	for _, l := range strings.Split(raw, ",") {
		if !slices.Contains(layerNames, l) {
			return nil, fmt.Errorf("layers must be a comma-separated list of %s", strings.Join(layerNames, ", "))
		}
		want[l] = true
	}
	return want, nil
}

// parseSearch validates q and returns it normalized: valid UTF-8, at most 64 characters as sent and at
// least 2 once trimmed and collapsed.
func parseSearch(q url.Values) (string, error) {
	raw := q.Get("q")
	text := normalize(raw)
	if !utf8.ValidString(raw) || utf8.RuneCountInString(raw) > maxSearch || utf8.RuneCountInString(text) < minSearch {
		return "", fmt.Errorf("q must be %d to %d characters", minSearch, maxSearch)
	}
	return text, nil
}

// pathState validates {code} and checks it is a listed state, answering 400 or 404 itself when it is not.
func (a *api) pathState(w http.ResponseWriter, r *http.Request) (string, bool) {
	code := r.PathValue("code")
	if bad(w, validate(code, stateCodePattern, "state code")) {
		return "", false
	}
	if !a.store.HasState(code) {
		writeError(w, http.StatusNotFound, "not_found", "state not found")
		return "", false
	}
	return code, true
}

// pathCity validates {id} and looks the city up, answering 400 or 404 itself when it cannot.
func (a *api) pathCity(w http.ResponseWriter, r *http.Request) (*store.City, bool) {
	id := r.PathValue("id")
	if bad(w, validate(id, idPattern, "city id")) {
		return nil, false
	}
	c, ok := a.store.City(id)
	if !ok {
		writeError(w, http.StatusNotFound, "not_found", "city not found")
		return nil, false
	}
	return c, true
}

// --- ranking ---------------------------------------------------------------------------------------------

// ranked returns cities best first for a preset: score, then larger population, then id, so the order is
// total and does not depend on how the store holds them. The caller's slice is not modified.
func ranked(cities []*store.City, preset string) []*store.City {
	out := slices.Clone(cities)
	slices.SortFunc(out, func(a, b *store.City) int {
		return cmp.Or(
			cmp.Compare(b.Scores[preset].Score, a.Scores[preset].Score),
			cmp.Compare(b.Population, a.Population),
			cmp.Compare(a.ID, b.ID),
		)
	})
	return out
}

// people rounds a population to whole people: the contract says integer.
func people(f float64) int64 { return int64(math.Round(f)) }

// --- city views ------------------------------------------------------------------------------------------

// cityView is a city as one preset sees it - the ranked card without its rank. All of it is stored data: the
// API computes no score.
type cityView struct {
	ID         string         `json:"id"`
	Name       string         `json:"name"`
	State      string         `json:"state"`
	Tier       string         `json:"tier"`
	Population int64          `json:"population"`
	Score      float64        `json:"score"`
	Access     *float64       `json:"access"`
	Momentum   *float64       `json:"momentum"`
	Coverage   float64        `json:"coverage"`
	Confidence float64        `json:"confidence"` // the preset's (0.8 x coverage), not the record's provenance confidence
	Drivers    []store.Driver `json:"drivers"`
	Gaps       []store.Gap    `json:"gaps"`
	BestArea   store.BestArea `json:"best_area"`
	Source     string         `json:"source"`
	SourceRef  string         `json:"source_ref"`
	FetchedAt  string         `json:"fetched_at"`
	License    string         `json:"license"`
}

func newCityView(c *store.City, preset string) cityView {
	ps := c.Scores[preset]
	return cityView{
		ID: c.ID, Name: c.Name, State: c.State, Tier: c.Tier, Population: people(c.Population),
		Score: ps.Score, Access: ps.Access, Momentum: ps.Momentum, Coverage: ps.Coverage, Confidence: ps.Confidence,
		Drivers: ps.Drivers, Gaps: ps.Gaps, BestArea: ps.BestArea,
		Source: c.Source, SourceRef: c.SourceRef, FetchedAt: c.FetchedAt, License: c.License,
	}
}

// card is a city in a ranked list.
type card struct {
	Rank int `json:"rank"`
	cityView
}

// cityDetail is the answer of GET /v1/cities/{id}: the card's content without a rank, plus the city summary.
type cityDetail struct {
	cityView
	Aliases []string                       `json:"aliases"`
	Lat     float64                        `json:"lat"`
	Lon     float64                        `json:"lon"`
	AreaKm2 float64                        `json:"area_km2"`
	Cells   int                            `json:"cells"`
	Factors map[string]store.FactorSummary `json:"factors"`
	Data    store.CityData                 `json:"data"`
}

// --- handlers --------------------------------------------------------------------------------------------

func (a *api) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, struct {
		Status string `json:"status"`
		AsOf   string `json:"as_of"`
	}{"ok", a.store.Meta().AsOf})
}

func (a *api) meta(w http.ResponseWriter, _ *http.Request) { writeJSON(w, a.store.Meta()) }

func (a *api) states(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, struct {
		AsOf   string        `json:"as_of"`
		States []store.State `json:"states"`
	}{a.store.Meta().AsOf, a.store.States()})
}

func (a *api) stateCities(w http.ResponseWriter, r *http.Request) {
	code, ok := a.pathState(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	preset, err := a.parsePreset(q)
	if bad(w, err) {
		return
	}
	limit, err := parseLimit(q, 1, 20, 5)
	if bad(w, err) {
		return
	}

	list := ranked(a.store.CitiesInState(code), preset)
	cards := make([]card, min(limit, len(list)))
	for i := range cards {
		cards[i] = card{Rank: i + 1, cityView: newCityView(list[i], preset)}
	}
	writeJSON(w, struct {
		State  string `json:"state"`
		Preset string `json:"preset"`
		Total  int    `json:"total"`
		Cities []card `json:"cities"`
	}{code, preset, len(list), cards})
}

// normalize is how search text and city names are compared: lower case, edges trimmed, runs of white space
// collapsed to one space.
func normalize(s string) string { return strings.ToLower(strings.Join(strings.Fields(s), " ")) }

// searchHit is a city found by name or alias; Matched is the name or alias that matched.
type searchHit struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	State      string `json:"state"`
	Tier       string `json:"tier"`
	Population int64  `json:"population"`
	Matched    string `json:"matched"`
}

// searchCities returns the cities with a name or alias that contains text (already normalized): those that
// start with it first, then larger population, then id. For a city that matches by several names, Matched
// is the best one - a prefix beats a substring, the city's own name beats its aliases.
func searchCities(cities []*store.City, text string) []searchHit {
	type match struct {
		hit    searchHit
		prefix bool
	}
	var found []match
	for _, c := range cities {
		var best *match
		for _, name := range append([]string{c.Name}, c.Aliases...) {
			n := normalize(name)
			if !strings.Contains(n, text) {
				continue
			}
			m := match{searchHit{c.ID, c.Name, c.State, c.Tier, people(c.Population), name}, strings.HasPrefix(n, text)}
			if best == nil || (m.prefix && !best.prefix) {
				best = &m
			}
		}
		if best != nil {
			found = append(found, *best)
		}
	}
	slices.SortFunc(found, func(a, b match) int {
		if a.prefix != b.prefix {
			if a.prefix {
				return -1
			}
			return 1
		}
		return cmp.Or(cmp.Compare(b.hit.Population, a.hit.Population), cmp.Compare(a.hit.ID, b.hit.ID))
	})
	hits := make([]searchHit, len(found))
	for i, m := range found {
		hits[i] = m.hit
	}
	return hits
}

func (a *api) search(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	text, err := parseSearch(q)
	if bad(w, err) {
		return
	}
	limit, err := parseLimit(q, 1, 20, 8)
	if bad(w, err) {
		return
	}
	hits := searchCities(a.cities, text)
	writeJSON(w, struct {
		Cities []searchHit `json:"cities"`
	}{hits[:min(limit, len(hits))]})
}

func (a *api) city(w http.ResponseWriter, r *http.Request) {
	c, ok := a.pathCity(w, r)
	if !ok {
		return
	}
	preset, err := a.parsePreset(r.URL.Query())
	if bad(w, err) {
		return
	}
	writeJSON(w, cityDetail{
		cityView: newCityView(c, preset), Aliases: c.Aliases, Lat: c.Lat, Lon: c.Lon, AreaKm2: c.AreaKm2,
		Cells: c.Cells, Factors: c.Factors, Data: c.Data,
	})
}

// areaFeature is one H3 cell as served: the stored facts for the preset asked for, ranked among all the
// city's cells, with the collection's provenance copied in.
type areaFeature struct {
	Type       string          `json:"type"`
	Geometry   json.RawMessage `json:"geometry"`
	Properties areaProps       `json:"properties"`
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
	D          []areaDriver        `json:"d"`
	G          []areaGap           `json:"g"`
	Source     string              `json:"source"`
	SourceRef  string              `json:"source_ref"`
	FetchedAt  string              `json:"fetched_at"`
	License    string              `json:"license"`
}

// areaDriver and areaGap carry the cell's own raw value (from f) and the factor's unit next to the stored
// points or sub-score.
type areaDriver struct {
	Factor string   `json:"factor"`
	Points float64  `json:"points"`
	Value  *float64 `json:"value"`
	Unit   string   `json:"unit"`
}

type areaGap struct {
	Factor   string   `json:"factor"`
	Subscore float64  `json:"subscore"`
	Value    *float64 `json:"value"`
	Unit     string   `json:"unit"`
}

func (a *api) areas(w http.ResponseWriter, r *http.Request) {
	c, ok := a.pathCity(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	preset, err := a.parsePreset(q)
	if bad(w, err) {
		return
	}
	limit, err := parseLimit(q, 1, 1000, 500)
	if bad(w, err) {
		return
	}
	set, ok := a.store.Areas(c.ID)
	if !ok {
		internalError(w, "a loaded city has no areas", "city", c.ID)
		return
	}

	cells := make([]*store.AreaFeature, len(set.Features))
	for i := range set.Features {
		cells[i] = &set.Features[i]
	}
	slices.SortFunc(cells, func(x, y *store.AreaFeature) int {
		return cmp.Or(
			cmp.Compare(y.Properties.Sc[preset], x.Properties.Sc[preset]),
			cmp.Compare(y.Properties.Pop, x.Properties.Pop),
			cmp.Compare(x.Properties.ID, y.Properties.ID),
		)
	})

	features := make([]areaFeature, min(limit, len(cells)))
	for i := range features {
		p := &cells[i].Properties
		d := make([]areaDriver, len(p.D[preset]))
		for j, fp := range p.D[preset] {
			d[j] = areaDriver{Factor: fp.Factor, Points: fp.Value, Value: p.F[fp.Factor], Unit: a.units[fp.Factor]}
		}
		g := make([]areaGap, len(p.G[preset]))
		for j, fp := range p.G[preset] {
			g[j] = areaGap{Factor: fp.Factor, Subscore: fp.Value, Value: p.F[fp.Factor], Unit: a.units[fp.Factor]}
		}
		features[i] = areaFeature{
			Type: "Feature", Geometry: cells[i].Geometry,
			Properties: areaProps{
				ID: p.ID, Name: p.Name, Pop: p.Pop, Elig: p.Elig, BusStops: p.BusStops, Rank: i + 1,
				Score: p.Sc[preset], Access: p.Ac[preset], Coverage: p.Cov, Confidence: p.Conf,
				F: p.F, S: p.S, D: d, G: g,
				Source: set.Source, SourceRef: p.SourceRef, FetchedAt: set.FetchedAt, License: set.License,
			},
		}
	}
	writeJSON(w, struct {
		Type     string        `json:"type"`
		Features []areaFeature `json:"features"`
	}{"FeatureCollection", features})
}

func (a *api) assets(w http.ResponseWriter, r *http.Request) {
	c, ok := a.pathCity(w, r)
	if !ok {
		return
	}
	want, err := parseLayers(r.URL.Query())
	if bad(w, err) {
		return
	}
	set, ok := a.store.Assets(c.ID)
	if !ok {
		internalError(w, "a loaded city has no assets", "city", c.ID)
		return
	}

	// The file's provenance is always sent, for whichever layers were asked. Of the layers only those asked for
	// are present, and a city without a bus feed has bus_stops and bus_source null: the null is sent, so a
	// missing feed is never mistaken for a layer that was not requested.
	out := map[string]any{"source": set.Source, "fetched_at": set.FetchedAt, "license": set.License}
	if want["stations"] {
		out["stations"] = set.Stations
	}
	if want["bus_stops"] {
		out["bus_stops"], out["bus_source"] = set.BusStops, set.BusSource
	}
	if want["highways"] {
		out["highways"] = set.Highways
	}
	if want["toll_plazas"] {
		out["toll_plazas"] = set.TollPlazas
	}
	writeJSON(w, out)
}

func (a *api) compareCity(w http.ResponseWriter, r *http.Request) {
	c, ok := a.pathCity(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	preset, err := a.parsePreset(q)
	if bad(w, err) {
		return
	}
	scope, err := parseScope(q)
	if bad(w, err) {
		return
	}
	limit, err := parseLimit(q, 1, 10, 5)
	if bad(w, err) {
		return
	}
	writeJSON(w, compare(c, a.cities, preset, scope, limit))
}

// projects answers a city's upcoming bus and metro projects: an empty list when none was found in the news.
func (a *api) projects(w http.ResponseWriter, r *http.Request) {
	c, ok := a.pathCity(w, r)
	if !ok {
		return
	}
	writeJSON(w, struct {
		City     string          `json:"city"`
		AsOf     string          `json:"as_of"`
		Projects []store.Project `json:"projects"`
	}{c.ID, a.store.ProjectsAsOf(), a.store.Projects(c.ID)})
}
