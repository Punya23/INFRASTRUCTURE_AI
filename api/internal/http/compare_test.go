package httpapi_test

import (
	"encoding/json"
	"slices"
	"strings"
	"testing"
)

type factorDelta struct {
	Factor string  `json:"factor"`
	Delta  float64 `json:"delta"`
	Base   float64 `json:"base"`
	Other  float64 `json:"other"`
}

type compareResponse struct {
	Base struct {
		Rank  int     `json:"rank"`
		ID    string  `json:"id"`
		Score float64 `json:"score"`
	} `json:"base"`
	Preset   string `json:"preset"`
	Scope    string `json:"scope"`
	Total    int    `json:"total"`
	BaseRank int    `json:"base_rank"`
	Others   []struct {
		Rank   int           `json:"rank"`
		ID     string        `json:"id"`
		Name   string        `json:"name"`
		State  string        `json:"state"`
		Tier   string        `json:"tier"`
		Score  float64       `json:"score"`
		Delta  float64       `json:"delta"`
		Better []factorDelta `json:"better"`
		Worse  []factorDelta `json:"worse"`
	} `json:"others"`
}

// Pune under the commuter preset, default scope (Pune is a metro, so its metros): the brief's numbers.
func TestCompare(t *testing.T) {
	h := newServer(t)
	rec := get(t, h, "/v1/cities/pune/compare?preset=commuter")
	wantOK(t, rec)
	wantKeys(t, rec.Body.Bytes(), "base preset scope total base_rank others")
	var got compareResponse
	decode(t, rec, &got)

	if got.Scope != "metros" || got.Preset != "commuter" || got.Total != 3 || got.BaseRank != 3 {
		t.Errorf("scope %q preset %q total %d base_rank %d; want metros commuter 3 3", got.Scope, got.Preset, got.Total, got.BaseRank)
	}
	// delhi 73.8, mumbai 69.5, pune 63.5, bengaluru 61.8: the base city sits inside the ranking
	if got.Base.ID != "pune" || got.Base.Rank != got.BaseRank || !near(got.Base.Score, 63.5) {
		t.Errorf("base = %+v", got.Base)
	}
	want := []struct {
		id    string
		rank  int
		delta float64
	}{{"delhi", 1, 10.3}, {"mumbai", 2, 6.0}, {"bengaluru", 4, -1.7}}
	if len(got.Others) != len(want) {
		t.Fatalf("%d others, want %d", len(got.Others), len(want))
	}
	for i, w := range want {
		o := got.Others[i]
		if o.ID != w.id || o.Rank != w.rank || !near(o.Delta, w.delta) {
			t.Errorf("others[%d] = %s rank %d delta %v; want %s rank %d delta %v", i, o.ID, o.Rank, o.Delta, w.id, w.rank, w.delta)
		}
	}

	// Delhi against Pune: where it is stronger and where weaker, largest gap first, ties by factor id.
	delhi := got.Others[0]
	wantBetter := []factorDelta{{"metro_access", 50, 40, 90}, {"rail_access", 20, 60, 80}} // road_strength +20 ties: rail_access sorts first
	wantWorse := []factorDelta{{"built_up_growth", -45, 90, 45}, {"nh_access", -5, 75, 70}}
	if !slices.Equal(delhi.Better, wantBetter) || !slices.Equal(delhi.Worse, wantWorse) {
		t.Errorf("delhi better %+v worse %+v; want %+v %+v", delhi.Better, delhi.Worse, wantBetter, wantWorse)
	}
	for _, o := range got.Others {
		if o.State == "" || o.Tier == "" || o.Name == "" {
			t.Errorf("row %s lacks state, tier or name: %+v", o.ID, o)
		}
	}

	// the base is a full ranked card, each row exactly the documented members
	var raw struct {
		Base   json.RawMessage   `json:"base"`
		Others []json.RawMessage `json:"others"`
	}
	decode(t, rec, &raw)
	wantKeys(t, raw.Base, "rank id name state tier population score access momentum coverage confidence drivers gaps best_area "+
		"source source_ref fetched_at license")
	for _, row := range raw.Others {
		wantKeys(t, row, "rank id name state tier score delta better worse")
	}
}

func TestCompare_scopes(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, url string
		scope     string
		total     int
		baseRank  int
		ids       []string // in order, after limit
	}{
		// balanced: pune 70.5, delhi 69.3, bengaluru 65.0, mumbai 63.0, nashik 55.0
		{"state", "/v1/cities/pune/compare?scope=state", "state", 2, 1, []string{"mumbai", "nashik"}},
		{"india", "/v1/cities/pune/compare?scope=india", "india", 4, 1, []string{"delhi", "bengaluru", "mumbai", "nashik"}},
		{"metros", "/v1/cities/pune/compare?scope=metros", "metros", 3, 1, []string{"delhi", "bengaluru", "mumbai"}},
		{"a metro's default", "/v1/cities/mumbai/compare", "metros", 3, 4, []string{"pune", "delhi", "bengaluru"}},
		{"peers of a metro are the metros", "/v1/cities/pune/compare?scope=peers", "peers", 3, 1, []string{"delhi", "bengaluru", "mumbai"}},
		// Nashik is the only large city: nobody to compare with is a normal empty answer
		{"large city, default scope", "/v1/cities/nashik/compare", "peers", 0, 1, []string{}},
		{"large city, peers", "/v1/cities/nashik/compare?scope=peers", "peers", 0, 1, []string{}},
		{"large city against the metros", "/v1/cities/nashik/compare?scope=metros", "metros", 4, 5, []string{"pune", "delhi", "bengaluru", "mumbai"}},
		{"alone in its state", "/v1/cities/delhi/compare?scope=state", "state", 0, 1, []string{}},
		{"limit keeps total and rank", "/v1/cities/pune/compare?preset=commuter&limit=2", "metros", 3, 3, []string{"delhi", "mumbai"}},
		{"limit 10", "/v1/cities/pune/compare?limit=10&scope=india", "india", 4, 1, []string{"delhi", "bengaluru", "mumbai", "nashik"}},
		{"highway preset", "/v1/cities/nashik/compare?preset=highway&scope=india", "india", 4, 2, []string{"pune", "bengaluru", "delhi", "mumbai"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := get(t, h, tc.url)
			wantOK(t, rec)
			var got compareResponse
			decode(t, rec, &got)
			if got.Scope != tc.scope || got.Total != tc.total || got.BaseRank != tc.baseRank || got.Base.Rank != tc.baseRank {
				t.Errorf("scope %q total %d base_rank %d (base.rank %d); want %q %d %d", got.Scope, got.Total, got.BaseRank, got.Base.Rank, tc.scope, tc.total, tc.baseRank)
			}
			gotIDs := []string{}
			for _, o := range got.Others {
				gotIDs = append(gotIDs, o.ID)
				if o.ID == got.Base.ID {
					t.Errorf("the base city %s appears in others", o.ID)
				}
				if !near(o.Delta, round1(o.Score-got.Base.Score)) {
					t.Errorf("%s: delta %v, want score %v minus base %v", o.ID, o.Delta, o.Score, got.Base.Score)
				}
				for _, d := range append(slices.Clone(o.Better), o.Worse...) {
					if !near(d.Delta, round1(d.Other-d.Base)) {
						t.Errorf("%s %s: delta %v, want other %v minus base %v", o.ID, d.Factor, d.Delta, d.Other, d.Base)
					}
				}
				for _, d := range o.Better {
					if d.Delta <= 0 {
						t.Errorf("%s better holds %+v", o.ID, d)
					}
				}
				for _, d := range o.Worse {
					if d.Delta >= 0 {
						t.Errorf("%s worse holds %+v", o.ID, d)
					}
				}
				if len(o.Better) > 2 || len(o.Worse) > 2 {
					t.Errorf("%s: %d better, %d worse; at most 2 each", o.ID, len(o.Better), len(o.Worse))
				}
			}
			if !slices.Equal(gotIDs, tc.ids) {
				t.Errorf("others = %v, want %v", gotIDs, tc.ids)
			}
			if len(tc.ids) == 0 && !strings.Contains(rec.Body.String(), `"others":[]`) {
				t.Errorf("no cities to compare with must be an empty list, not null: %s", rec.Body)
			}
		})
	}
}

func TestCompare_badInput(t *testing.T) {
	h := newServer(t)
	cases := []struct {
		name, url string
		status    int
		code      string
	}{
		{"limit 11", "/v1/cities/pune/compare?limit=11", 400, "bad_request"},
		{"limit 0", "/v1/cities/pune/compare?limit=0", 400, "bad_request"},
		{"limit not a number", "/v1/cities/pune/compare?limit=all", 400, "bad_request"},
		{"scope galaxy", "/v1/cities/pune/compare?scope=galaxy", 400, "bad_request"},
		{"empty scope", "/v1/cities/pune/compare?scope=", 400, "bad_request"},
		{"scope in capitals", "/v1/cities/pune/compare?scope=India", 400, "bad_request"},
		{"bad preset", "/v1/cities/pune/compare?preset=bogus", 400, "bad_request"},
		{"unknown city", "/v1/cities/nowhere/compare", 404, "not_found"},
		{"bad id", "/v1/cities/Pune/compare", 400, "bad_request"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			wantError(t, get(t, h, tc.url), tc.status, tc.code)
		})
	}
}
