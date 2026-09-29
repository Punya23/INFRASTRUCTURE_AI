package httpapi

import (
	"cmp"
	"math"
	"slices"

	"github.com/Punya23/INFRASTRUCTURE_AI/api/internal/store"
)

// scopes maps each compare scope to "is c in the comparison set of base". The base city itself is left out by
// compare, not here.
var scopes = map[string]func(base, c *store.City) bool{
	"metros": func(_, c *store.City) bool { return c.Tier == "metro" },
	"peers":  func(base, c *store.City) bool { return c.Tier == base.Tier },
	"state":  func(base, c *store.City) bool { return c.State == base.State },
	"india":  func(_, _ *store.City) bool { return true },
}

// maxReasons is how many factors better and worse hold each.
const maxReasons = 2

// CompareResult is the answer of GET /v1/cities/{id}/compare (spec section 7).
type CompareResult struct {
	Base     card         `json:"base"`
	Preset   string       `json:"preset"`
	Scope    string       `json:"scope"`
	Total    int          `json:"total"`
	BaseRank int          `json:"base_rank"`
	Others   []compareRow `json:"others"`
}

// compareRow is one compared city: its score, how far it is from the base city's, and why.
type compareRow struct {
	Rank   int           `json:"rank"`
	ID     string        `json:"id"`
	Name   string        `json:"name"`
	State  string        `json:"state"`
	Tier   string        `json:"tier"`
	Score  float64       `json:"score"`
	Delta  float64       `json:"delta"`
	Better []factorDelta `json:"better"`
	Worse  []factorDelta `json:"worse"`
}

// factorDelta is a sub-score difference between a compared city (other) and the base city.
type factorDelta struct {
	Factor string  `json:"factor"`
	Delta  float64 `json:"delta"`
	Base   float64 `json:"base"`
	Other  float64 `json:"other"`
}

// compare sets base against the cities of all that fall in scope ("" picks metros for a metro and peers
// for any other tier), for one preset. Scores, sub-scores and their order are the stored ones; the only
// arithmetic is subtraction, rounded to one decimal. scope must be a key of scopes (the handler checks).
//
// Others holds at most limit cities, best first (ties: larger population, then id), never the base city.
// Total counts all of them, before limit. A rank is 1 + the number of compared cities, the base included,
// that score higher, so cities with equal scores share a rank and BaseRank is the base city's own.
func compare(base *store.City, all []*store.City, preset, scope string, limit int) CompareResult {
	if scope == "" {
		scope = "peers"
		if base.Tier == "metro" {
			scope = "metros"
		}
	}
	inScope := scopes[scope]
	var set []*store.City
	for _, c := range all {
		if c.ID != base.ID && inScope(base, c) {
			set = append(set, c)
		}
	}
	others := ranked(set, preset)

	score := func(c *store.City) float64 { return c.Scores[preset].Score }
	baseScore := score(base)
	rank := func(s float64) int {
		n := 1
		if baseScore > s {
			n++
		}
		for _, o := range others {
			if score(o) > s {
				n++
			}
		}
		return n
	}

	rows := make([]compareRow, 0, min(limit, len(others)))
	for _, o := range others[:min(limit, len(others))] {
		better, worse := reasons(base, o)
		rows = append(rows, compareRow{
			Rank: rank(score(o)), ID: o.ID, Name: o.Name, State: o.State, Tier: o.Tier,
			Score: score(o), Delta: round1(score(o) - baseScore), Better: better, Worse: worse,
		})
	}
	baseRank := rank(baseScore)
	return CompareResult{
		Base:   card{Rank: baseRank, cityView: newCityView(base, preset)},
		Preset: preset, Scope: scope, Total: len(others), BaseRank: baseRank, Others: rows,
	}
}

// reasons says why other scores differently from base: the factors where its sub-score is higher (better)
// and lower (worse), at most maxReasons of each, the largest gap first, ties by factor id. A factor that one
// of the two cities has not observed is left out: an unobserved value is not a zero.
func reasons(base, other *store.City) (better, worse []factorDelta) {
	var all []factorDelta
	for f, b := range base.Factors {
		o := other.Factors[f]
		if b.Subscore == nil || o.Subscore == nil {
			continue
		}
		all = append(all, factorDelta{Factor: f, Delta: round1(*o.Subscore - *b.Subscore), Base: *b.Subscore, Other: *o.Subscore})
	}
	slices.SortFunc(all, func(x, y factorDelta) int {
		return cmp.Or(cmp.Compare(math.Abs(y.Delta), math.Abs(x.Delta)), cmp.Compare(x.Factor, y.Factor))
	})
	better, worse = []factorDelta{}, []factorDelta{}
	for _, d := range all {
		switch {
		case d.Delta > 0 && len(better) < maxReasons:
			better = append(better, d)
		case d.Delta < 0 && len(worse) < maxReasons:
			worse = append(worse, d)
		}
	}
	return better, worse
}

func round1(x float64) float64 { return math.Round(x*10) / 10 }
