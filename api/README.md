# Investor API

A small read-only JSON API over the fixtures the pipeline writes to `web/fixtures/invest/`. It holds the data in memory, computes nothing (scores come from the pipeline) and stops at start-up if a fixture is missing or malformed. The contract is [`openapi.yaml`](openapi.yaml).

## Run, test, point at the real data

```bash
go -C api run ./cmd/api -addr :8080 -data ../web/fixtures/invest   # serve the real fixtures
go -C api vet ./... && go -C api test ./... -race                  # checks before every commit
go -C api run ./cmd/api -data testdata/invest                      # serve the small synthetic test world
```

| Setting | Default | Meaning |
|---|---|---|
| `-addr` | `:8080` | listen address |
| `-data` | `../web/fixtures/invest` | fixture directory (`meta.json`, `states.json`, `cities.json`, `areas/`, `assets/`) |
| `INVEST_CORS_ORIGINS` | `http://localhost:8765` | comma-separated exact origins whose pages may read the responses |
| `INVEST_RATE_LIMIT` | `120` | requests per client per minute (a value that is not a positive integer stops start-up) |

To preview the pages from a second checkout, serve `web/` on `:8766` and run the API with `INVEST_CORS_ORIGINS=http://localhost:8766 ... -addr :8081`; the launch configurations `web-main` and `api-main` in `.claude/launch.json` do this.

## Endpoints

| Method and path | Query | Returns |
|---|---|---|
| `GET /healthz` | none | `{"status","as_of"}` |
| `GET /v1/meta` | none | factors, presets, tiers, sources and the disclaimer |
| `GET /v1/states` | none | all 36 states and UTs with `city_count` |
| `GET /v1/states/{code}/cities` | `preset`, `limit` 1 to 20 (5) | the state's cities ranked for the preset |
| `GET /v1/cities` | `q` (2 to 64 characters), `limit` 1 to 20 (8) | city search over names and aliases |
| `GET /v1/cities/{id}` | `preset` | one city with factors and provenance |
| `GET /v1/cities/{id}/areas` | `preset`, `limit` 1 to 1000 (500) | GeoJSON of H3 areas, best first |
| `GET /v1/cities/{id}/assets` | `layers` from `stations,bus_stops,highways,toll_plazas` | the requested map layers |
| `GET /v1/cities/{id}/compare` | `preset`, `scope` (`metros`, `peers`, `state`, `india`), `limit` 1 to 10 (5) | the city against others, with the reasons |

Codes and ids are checked against fixed patterns (`^[A-Z]{2}$`, `^[a-z0-9-]{2,64}$`) and looked up in memory. A value outside a limit is a 400, never clamped.

## Errors

Every error, from any layer, has one shape and leaks no internal detail:

```json
{"error": {"code": "not_found", "message": "city not found"}}
```

| Code | Status | When |
|---|---|---|
| `bad_request` | 400 | a bad parameter or id |
| `not_found` | 404 | an unknown state, city or route |
| `rate_limited` | 429 | over the per-client limit (`Retry-After` is set) |
| `timeout` | 503 | a request took longer than 5 seconds |
| `internal` | 500 | anything unexpected, logged server-side only |

Responses carry `X-Content-Type-Options: nosniff`, and data routes `Cache-Control: public, max-age=300`.
