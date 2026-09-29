package httpapi

import (
	"encoding/json"
	"math"
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"testing"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// White-box tests for the pure helpers, with hand-built cities: the cases the synthetic world cannot make -
// tied scores, factors nobody observed, names in other scripts.

func ptr(v float64) *float64 { return &v }

// mkCity builds a city that has one preset, "balanced", with the given score; subs are its factor sub-scores
// (a nil entry is a factor that was not observed).
func mkCity(id, state, tier string, pop, score float64, subs map[string]*float64) *store.City {
	c := &store.City{
		ID: id, Name: strings.ToUpper(id[:1]) + id[1:], State: state, Tier: tier, Population: pop,
		Factors: map[string]store.FactorSummary{},
		Scores:  map[string]store.PresetScore{"balanced": {Score: score, Drivers: []store.Driver{}, Gaps: []store.Gap{}}},
	}
	for f, v := range subs {
		c.Factors[f] = store.FactorSummary{Subscore: v}
	}
	return c
}

// row returns the i-th compared city, or stops the test if the comparison came back shorter.
func row(t *testing.T, r CompareResult, i int) compareRow {
	t.Helper()
	if i >= len(r.Others) {
		t.Fatalf("want at least %d compared cities, got %d", i+1, len(r.Others))
	}
	return r.Others[i]
}

func idsOf(cs []*store.City) []string {
	ids := make([]string, len(cs))
	for i, c := range cs {
		ids[i] = c.ID
	}
	return ids
}

func TestRanked(t *testing.T) {
	a := mkCity("a", "MH", "metro", 100, 50, nil)
	b := mkCity("b", "MH", "metro", 300, 50, nil)
	c := mkCity("c", "MH", "metro", 300, 50, nil)
	d := mkCity("d", "MH", "metro", 1, 60, nil)
	e := mkCity("e", "MH", "metro", 999, 40, nil)
	in := []*store.City{a, e, c, d, b}

	got := idsOf(ranked(in, "balanced"))
	if want := []string{"d", "b", "c", "a", "e"}; !slices.Equal(got, want) { // score, then population, then id
		t.Errorf("ranked = %v, want %v", got, want)
	}
	if got := idsOf(in); !slices.Equal(got, []string{"a", "e", "c", "d", "b"}) {
		t.Errorf("ranked reordered the caller's slice (the store's own): %v", got)
	}
}

func TestCompare_ties(t *testing.T) {
	subs := func(v float64) map[string]*float64 { return map[string]*float64{"f": ptr(v)} }
	base := mkCity("base", "MH", "metro", 500, 60, subs(50))
	big := mkCity("big", "KA", "metro", 900, 60, subs(50))
	small := mkCity("small", "KA", "metro", 100, 60, subs(50))
	top := mkCity("top", "DL", "metro", 800, 70, subs(80))
	low := mkCity("low", "DL", "metro", 800, 50, subs(20))

	r := compare(base, []*store.City{low, base, small, top, big}, "balanced", "metros", 10)
	if r.Total != 4 || r.BaseRank != 2 || r.Base.Rank != 2 || r.Scope != "metros" || r.Preset != "balanced" {
		t.Errorf("total %d base_rank %d base.rank %d scope %q preset %q", r.Total, r.BaseRank, r.Base.Rank, r.Scope, r.Preset)
	}
	// Cities that tie with the base share its rank: a rank is 1 + the cities that score higher.
	want := []struct {
		id    string
		rank  int
		delta float64
	}{{"top", 1, 10}, {"big", 2, 0}, {"small", 2, 0}, {"low", 5, -10}}
	if len(r.Others) != len(want) {
		t.Fatalf("%d others, want %d", len(r.Others), len(want))
	}
	for i, w := range want {
		if o := r.Others[i]; o.ID != w.id || o.Rank != w.rank || o.Delta != w.delta {
			t.Errorf("others[%d] = %s rank %d delta %v; want %s %d %v", i, o.ID, o.Rank, o.Delta, w.id, w.rank, w.delta)
		}
	}

	// equal sub-scores explain nothing: both lists are empty, and empty is [] not null
	b, err := json.Marshal(row(t, r, 1))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(b), `"better":[],"worse":[]`) {
		t.Errorf("a tie has no reasons, and no reasons is []: %s", b)
	}
	if top := row(t, r, 0); !slices.Equal(top.Better, []factorDelta{{"f", 30, 50, 80}}) {
		t.Errorf("top better = %+v", top.Better)
	}
}

func TestCompare_limitKeepsTotalAndRanks(t *testing.T) {
	var all []*store.City
	for i, id := range []string{"c1", "c2", "c3", "c4", "c5", "c6"} {
		all = append(all, mkCity(id, "MH", "mid", float64(100-i), float64(90-10*i), nil))
	}
	r := compare(all[2], all, "balanced", "peers", 2) // base c3 (70): c1 90, c2 80 above; c4 60, c5 50, c6 40 below
	if r.Total != 5 || r.BaseRank != 3 || len(r.Others) != 2 || row(t, r, 0).ID != "c1" || row(t, r, 1).ID != "c2" {
		t.Errorf("total %d base_rank %d others %+v", r.Total, r.BaseRank, r.Others)
	}
	r = compare(all[2], all, "balanced", "peers", 4)
	if next := row(t, r, 2); next.ID != "c4" || next.Rank != 4 {
		t.Errorf("the base city takes rank 3, so the next city is 4: %+v", next)
	}
}

// A sub-score nobody observed is not a zero: it is left out of the reasons instead of being compared.
func TestCompare_unobservedFactorIsSkipped(t *testing.T) {
	base := mkCity("base", "MH", "metro", 1, 60, map[string]*float64{"a": ptr(50), "b": nil, "c": ptr(50)})
	other := mkCity("other", "MH", "metro", 1, 70, map[string]*float64{"a": ptr(80), "b": ptr(90), "c": nil})
	r := compare(base, []*store.City{base, other}, "balanced", "metros", 5)
	got := row(t, r, 0)
	if want := []factorDelta{{"a", 30, 50, 80}}; !slices.Equal(got.Better, want) || len(got.Worse) != 0 {
		t.Errorf("better %+v worse %+v; want only a: b and c are unobserved on one side", got.Better, got.Worse)
	}
}

func TestCompare_reasonsAreCappedAndOrdered(t *testing.T) {
	sub := func(v ...float64) map[string]*float64 {
		m := map[string]*float64{}
		for i, x := range v {
			m[string(rune('a'+i))] = ptr(x)
		}
		return m
	}
	base := mkCity("base", "MH", "metro", 1, 50, sub(10, 10, 10, 50, 50, 50))
	other := mkCity("other", "MH", "metro", 1, 50, sub(60, 50, 40, 30, 30, 45))
	// deltas a +50, b +40, c +30, d -20, e -20, f -5
	got := row(t, compare(base, []*store.City{base, other}, "balanced", "metros", 5), 0)
	better := []factorDelta{{"a", 50, 10, 60}, {"b", 40, 10, 50}}
	worse := []factorDelta{{"d", -20, 50, 30}, {"e", -20, 50, 30}} // tie on |delta|: factor id ascending
	if !slices.Equal(got.Better, better) || !slices.Equal(got.Worse, worse) {
		t.Errorf("better %+v worse %+v; want %+v %+v", got.Better, got.Worse, better, worse)
	}
}

func TestCompare_defaultScope(t *testing.T) {
	for tier, want := range map[string]string{"metro": "metros", "large": "peers", "mid": "peers"} {
		base := mkCity("base", "MH", tier, 1, 50, nil)
		if got := compare(base, []*store.City{base}, "balanced", "", 5).Scope; got != want {
			t.Errorf("default scope of a %s city = %q, want %q", tier, got, want)
		}
	}
}

func TestSearchCities_otherScripts(t *testing.T) {
	pune := mkCity("pune", "MH", "metro", 6_100_000, 50, nil)
	pune.Name = "पुणे" // Devanagari
	pune.Aliases = []string{"Pimpri-Chinchwad"}
	blr := mkCity("bengaluru", "KA", "metro", 11_000_000, 50, nil)
	blr.Name = "ಬೆಂಗಳೂರು" // Kannada
	all := []*store.City{pune, blr}

	for _, tc := range []struct{ q, id, matched string }{
		{"पु", "pune", pune.Name},
		{"  पुणे ", "pune", pune.Name},
		{"ಬೆ", "bengaluru", blr.Name},
		{"chinchwad", "pune", "Pimpri-Chinchwad"},
	} {
		hits := searchCities(all, normalize(tc.q))
		if len(hits) != 1 || hits[0].ID != tc.id || hits[0].Matched != tc.matched {
			t.Errorf("q=%q: %+v, want %s matched %q", tc.q, hits, tc.id, tc.matched)
		}
	}
	// One city, two names: a prefix on an alias beats a substring of the name; between two prefixes the
	// city's own name is the one reported.
	sub := mkCity("x", "MH", "mid", 10, 50, nil)
	sub.Name, sub.Aliases = "Xpune", []string{"Pune East"}
	both := mkCity("y", "MH", "mid", 10, 50, nil)
	both.Name, both.Aliases = "Punekar", []string{"Pune West"}
	for _, tc := range []struct {
		c       *store.City
		matched string
	}{{sub, "Pune East"}, {both, "Punekar"}} {
		if hits := searchCities([]*store.City{tc.c}, "pune"); len(hits) != 1 || hits[0].Matched != tc.matched {
			t.Errorf("%s: %+v, want matched %q", tc.c.Name, hits, tc.matched)
		}
	}

	if got := normalize("  A   b\t\nC "); got != "a b c" {
		t.Errorf("normalize = %q, want %q", got, "a b c")
	}
}

// The body is built before anything is sent, so a value that cannot be encoded is a clean 500 - and the
// reason goes to the log, not to the client.
func TestWriteJSON_encodingFailureIsACleanError(t *testing.T) {
	logs := captureLogs(t)
	rec := httptest.NewRecorder()
	writeJSON(rec, map[string]float64{"score": math.NaN()})

	if code := errorCode(t, rec, http.StatusInternalServerError); code != "internal" {
		t.Errorf("code = %q, want internal", code)
	}
	if strings.Contains(rec.Body.String(), "NaN") || strings.Contains(rec.Body.String(), "unsupported") {
		t.Errorf("the encoder's error reached the client: %s", rec.Body)
	}
	if !strings.Contains(logs.String(), "unsupported value") {
		t.Errorf("the encoding error must be logged, got: %s", logs.String())
	}
}

// The contract says population is an integer; a fixture that carries a fractional count is served as whole people.
func TestPopulationIsWholePeople(t *testing.T) {
	for in, want := range map[float64]int64{6_100_000: 6_100_000, 6_099_999.6: 6_100_000, 1234.4: 1234, 1234.5: 1235, 0.4: 0} {
		if got := people(in); got != want {
			t.Errorf("people(%v) = %d, want %d", in, got, want)
		}
	}
	c := mkCity("x", "MH", "mid", 1234.6, 50, nil)
	if got := newCityView(c, "balanced").Population; got != 1235 {
		t.Errorf("a card's population = %d, want 1235", got)
	}
}
