# INFRA-AI investor API

Read-only JSON API behind the "where should I invest?" flow. Go stdlib only. It loads the fixtures the pipeline
exports (`web/fixtures/invest/`) into memory at start-up and serves them; it holds no scoring logic. The
contract is [`openapi.yaml`](openapi.yaml). Scores describe existing infrastructure and past growth; they are
not forecasts, price predictions or financial advice.

## Run, test, point at other data

```bash
go -C api run ./cmd/api                                  # :8080, real fixtures (../web/fixtures/invest)
go -C api vet ./... && go -C api test ./... -race        # checks before every commit
go -C api run ./cmd/api -data testdata/invest            # the 5-city synthetic world used by the tests
```

Paths are relative to `api/` because of `-C api`. The `api` entry in `.claude/launch.json` (`preview_start`
name `api`) runs the first command. The synthetic world (`source: synthetic-test`) is invented data: use it for
tests and demos of edge cases only, never show its numbers as real.

Flags and environment:

| Setting | Default | Meaning |
|---|---|---|
| `-addr` | `:8080` | Listen address. |
| `-data` | `../web/fixtures/invest` | Fixture directory. Any load or validation error is logged and the process exits 1. |
| `INVEST_CORS_ORIGINS` | `http://localhost:8765` | Comma-separated exact origins allowed to read responses, written as the browser sends them: `scheme://host[:port]`, no `*`, no path, no trailing slash (anything else: exit 1). Blank means the default. |
| `INVEST_RATE_LIMIT` | `120` | Requests per client per minute. Not a positive integer: exit 1. |

SIGINT/SIGTERM drain in-flight requests for up to 10 s, then exit.

## Endpoints

All `GET`. Presets are the ids in `/v1/meta`; omitted means the default (`balanced`).

| Path | Returns |
|---|---|
| `/healthz` | `{status, as_of}`. |
| `/v1/meta` | The scoring model: factors, presets, tiers, sources, disclaimer. |
| `/v1/states` | Every state and union territory with its city count. |
| `/v1/states/{code}/cities?preset&limit` | Top cities of a state (limit 1-20, default 5). Fewer than `limit`, or none, is 200; `total` is the state's count. |
| `/v1/cities?q&limit` | City search by name or alias (Devanagari works); `q` 2-64 characters, limit 1-20, default 8. |
| `/v1/cities/{id}` | One city with its factor summary, flags and drivers. |
| `/v1/cities/{id}/areas?preset&limit` | H3 cells as GeoJSON, ranked (limit 1-1000, default 500). |
| `/v1/cities/{id}/assets?layers` | Stations, bus stops, highways, toll plazas. |
| `/v1/cities/{id}/compare?preset&scope&limit` | The city against others (`metros`, `peers`, `state`, `india`), with reasons for each difference; limit 1-10, default 5. |

Data routes send `Cache-Control: public, max-age=300`; every response sends `X-Content-Type-Options: nosniff`.

## Errors

Always `{"error":{"code","message"}}`; the message is safe to show and carries no internal detail.

| Code | Status | When |
|---|---|---|
| `bad_request` | 400 | Malformed state code (`^[A-Z]{2}$`) or city id (`^[a-z0-9-]{2,64}$`), unknown preset, out-of-range `limit`, `q` too short or too long. |
| `not_found` | 404 | Unknown route, state or city. |
| `rate_limited` | 429 | Over the per-client limit; `Retry-After` is set. |
| `timeout` | 503 | The request outlived its 5 s budget. |
| `internal` | 500 | A recovered panic. |

## Deployment notes

- **Rate limiter keys on the socket peer.** Behind a reverse proxy every user shares one bucket, so raise
  `INVEST_RATE_LIMIT` or put per-client limiting in the proxy. `X-Forwarded-For` is deliberately not trusted.
- **Responses are not compressed.** The largest real body is about 1.3 MB (Mumbai `/assets`); let the proxy or
  CDN gzip.
- **Start-up is slow on the full dataset.** Every fixture is parsed twice (about 4-7 s for 381 cities). The log
  says `loading fixtures`, then `fixtures loaded` with `cities`, `areas`, `as_of` and `took`, then `listening`.
  The port opens only after loading, so readiness is simply "port open" (a probe before that is refused).
