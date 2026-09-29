package store

import (
	"encoding/json"
	"fmt"
)

// The types below mirror the fixture contract (spec §6) field for field. Every field is present in every
// fixture. Only a pointer (nil = "not observed", never 0), a list or a map may be null; Load rejects a missing
// field, or a null anywhere else, instead of reading it as 0. Everything a caller receives is shared with the
// Store: do not modify it.

// Provenance is embedded inline in every city record (AGENTS invariant 1: no anonymous data).
type Provenance struct {
	Source     string  `json:"source"`
	SourceRef  string  `json:"source_ref"`
	FetchedAt  string  `json:"fetched_at"`
	License    string  `json:"license"`
	Confidence float64 `json:"confidence"`
}

// Meta is meta.json: the scoring model the fixtures were built with.
type Meta struct {
	SchemaVersion int      `json:"schema_version"`
	AsOf          string   `json:"as_of"`
	Grid          Grid     `json:"grid"`
	Factors       []Factor `json:"factors"`
	Presets       []Preset `json:"presets"`
	Tiers         Tiers    `json:"tiers"`
	Sources       []Source `json:"sources"`
	Disclaimer    string   `json:"disclaimer"`
}

// Grid describes the area unit (config/scoring.yaml grid:).
type Grid struct {
	H3Res                 int `json:"h3_res"`
	BufferRings           int `json:"buffer_rings"`
	MinAreaPopulation     int `json:"min_area_population"`
	BestAreaMinPopulation int `json:"best_area_min_population"`
}

// Tiers holds the population thresholds behind City.Tier (config/scoring.yaml cities.tiers).
type Tiers struct {
	MetroMinPopulation int `json:"metro_min_population"`
	LargeMinPopulation int `json:"large_min_population"`
}

// Factor is one scored factor; Bands are (raw value, sub-score) knots.
type Factor struct {
	ID             string      `json:"id"`
	Group          string      `json:"group"`
	Unit           string      `json:"unit"`
	Better         string      `json:"better"`
	HeadlineBandKm *float64    `json:"headline_band_km"`
	Bands          [][]float64 `json:"bands"`
}

// Preset is a named weighting of the factors; weights sum to 1 and exactly one preset is the default.
type Preset struct {
	ID      string             `json:"id"`
	Weights map[string]float64 `json:"weights"`
	Default bool               `json:"default"`
}

// Source is a data source with its license and attribution text.
type Source struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	License     string `json:"license"`
	Attribution string `json:"attribution"`
}

// State is one entry of states.json; CityCount may be 0.
type State struct {
	Code      string `json:"code"`
	Name      string `json:"name"`
	CityCount int    `json:"city_count"`
}

// City is one entry of cities.json. Factors is keyed by factor id and Scores by preset id.
// Population is a float only so a whole number written as 1.9e6 or 1900000.0 still loads.
type City struct {
	ID         string                   `json:"id"`
	Name       string                   `json:"name"`
	State      string                   `json:"state"`
	Aliases    []string                 `json:"aliases"`
	Lat        float64                  `json:"lat"`
	Lon        float64                  `json:"lon"`
	Population float64                  `json:"population"`
	AreaKm2    float64                  `json:"area_km2"`
	Tier       string                   `json:"tier"`
	Cells      int                      `json:"cells"`
	Factors    map[string]FactorSummary `json:"factors"`
	Scores     map[string]PresetScore   `json:"scores"`
	Data       CityData                 `json:"data"`
	Provenance
}

// FactorSummary is a city's summary of one factor, population-weighted (spec §4).
type FactorSummary struct {
	Value    *float64 `json:"value"`
	Unit     string   `json:"unit"`
	Share    *float64 `json:"share"`
	BandKm   *float64 `json:"band_km"`
	Subscore *float64 `json:"subscore"`
}

// PresetScore is a city's score under one preset.
type PresetScore struct {
	Score      float64  `json:"score"`
	Access     *float64 `json:"access"`
	Momentum   *float64 `json:"momentum"`
	Coverage   float64  `json:"coverage"`
	Confidence float64  `json:"confidence"`
	Drivers    []Driver `json:"drivers"`
	Gaps       []Gap    `json:"gaps"`
	BestArea   BestArea `json:"best_area"`
}

// Driver is a factor that lifts a score: its contribution in score points.
type Driver struct {
	Factor string   `json:"factor"`
	Points float64  `json:"points"`
	Value  *float64 `json:"value"`
	Unit   string   `json:"unit"`
	Share  *float64 `json:"share"`
	BandKm *float64 `json:"band_km"`
}

// Gap is a factor that holds a score back: its sub-score (below the config threshold).
type Gap struct {
	Factor   string   `json:"factor"`
	Subscore float64  `json:"subscore"`
	Value    *float64 `json:"value"`
	Unit     string   `json:"unit"`
	Share    *float64 `json:"share"`
	BandKm   *float64 `json:"band_km"`
}

// BestArea is the highest-scoring eligible area of a city; Name is nil for an unnamed cell.
type BestArea struct {
	ID    string  `json:"id"`
	Name  *string `json:"name"`
	Score float64 `json:"score"`
}

// CityData holds the data flags shown next to a city; Bus is nil when the city has no bus feed.
type CityData struct {
	Bus           *Bus `json:"bus"`
	MetroStations int  `json:"metro_stations"`
	RailStations  int  `json:"rail_stations"`
}

// Bus describes the GTFS bus feed of a city (shown, never scored).
type Bus struct {
	Operator string `json:"operator"`
	Tier     string `json:"tier"`
	Stops    int    `json:"stops"`
}

// AreaSet is areas/<city>.geojson: provenance sits once on the collection, source_ref and conf per feature.
type AreaSet struct {
	Type      string        `json:"type"`
	City      string        `json:"city"`
	Source    string        `json:"source"`
	FetchedAt string        `json:"fetched_at"`
	License   string        `json:"license"`
	Features  []AreaFeature `json:"features"`
}

// AreaFeature is one H3 cell. Geometry is served verbatim.
type AreaFeature struct {
	Type       string          `json:"type"`
	Geometry   json.RawMessage `json:"geometry"`
	Properties AreaProps       `json:"properties"`
}

// AreaProps are a cell's stored facts. F holds raw values and S sub-scores by factor id (nil = not observed);
// Sc, Ac, D and G are keyed by preset id.
type AreaProps struct {
	ID        string                   `json:"id"`
	Name      *string                  `json:"name"`
	Pop       float64                  `json:"pop"`
	Elig      bool                     `json:"elig"`
	BusStops  *float64                 `json:"bus_stops"`
	F         map[string]*float64      `json:"f"`
	S         map[string]*float64      `json:"s"`
	Sc        map[string]float64       `json:"sc"`
	Ac        map[string]*float64      `json:"ac"`
	D         map[string][]FactorPoint `json:"d"`
	G         map[string][]FactorPoint `json:"g"`
	Cov       float64                  `json:"cov"`
	Conf      float64                  `json:"conf"`
	SourceRef string                   `json:"source_ref"`
}

// FactorPoint is one ["factor", number] pair: points in D, sub-score in G.
type FactorPoint struct {
	Factor string
	Value  float64
}

// UnmarshalJSON decodes ["factor", number]; anything else, including a null number, is an error.
func (p *FactorPoint) UnmarshalJSON(b []byte) error {
	var pair []json.RawMessage
	if err := json.Unmarshal(b, &pair); err != nil || len(pair) != 2 {
		return fmt.Errorf(`want ["factor", number], got %s`, b)
	}
	var v *float64
	if err := json.Unmarshal(pair[0], &p.Factor); err != nil || p.Factor == "" {
		return fmt.Errorf(`want ["factor", number], got %s`, b)
	}
	if err := json.Unmarshal(pair[1], &v); err != nil || v == nil {
		return fmt.Errorf(`want ["factor", number], got %s`, b)
	}
	p.Value = *v
	return nil
}

// AssetSet is assets/<city>.json: the map layers. Source, FetchedAt and License are the provenance of the
// stations, highways and toll plazas; BusSource is the provenance of BusStops, and both are nil for a city
// without a bus feed. Features are served verbatim.
type AssetSet struct {
	City       string             `json:"city"`
	Source     string             `json:"source"`
	FetchedAt  string             `json:"fetched_at"`
	License    string             `json:"license"`
	Stations   FeatureCollection  `json:"stations"`
	BusStops   *FeatureCollection `json:"bus_stops"`
	BusSource  *BusSource         `json:"bus_source"`
	Highways   FeatureCollection  `json:"highways"`
	TollPlazas FeatureCollection  `json:"toll_plazas"`
}

// FeatureCollection is a GeoJSON collection whose features are passed through untouched.
type FeatureCollection struct {
	Type     string            `json:"type"`
	Features []json.RawMessage `json:"features"`
}

// BusSource is the provenance of a city's bus stops.
type BusSource struct {
	Operator  string `json:"operator"`
	Tier      string `json:"tier"`
	License   string `json:"license"`
	FetchedAt string `json:"fetched_at"`
}
