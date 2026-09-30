#!/usr/bin/env bash
# Deploy the investor pages (web/) and the /v1/* API (mock_api.py over web/fixtures/invest) to Vercel,
# then smoke-test the live URL.
#
#   scripts/deploy-vercel.sh                 preview deploy
#   scripts/deploy-vercel.sh --prod          production deploy
#   scripts/deploy-vercel.sh --stage-only    build deploy/vercel locally, do not deploy
#   scripts/deploy-vercel.sh --smoke URL     only smoke-test an existing deployment
#   --skip-tests                             skip the node/python checks
#
# Env: VERCEL_PROJECT (default infra-ai-invest), VERCEL_SCOPE (team slug, optional),
#      SMOKE_CITY (default pune), VERCEL_PROTECTION_BYPASS (deployment-protection bypass secret, optional).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$ROOT/deploy/vercel"
PROJECT="${VERCEL_PROJECT:-infra-ai-invest}"
CITY="${SMOKE_CITY:-pune}"
PROD=0 SKIP_TESTS=0 STAGE_ONLY=0 SMOKE_URL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --prod) PROD=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --stage-only) STAGE_ONLY=1 ;;
    --smoke) SMOKE_URL="${2:?--smoke needs a URL}"; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\033[31mFAIL: %s\033[0m\n' "$*" >&2; exit 1; }

smoke() {
  local base="${1%/}" failed=0 hdr=()
  [ -n "${VERCEL_PROTECTION_BYPASS:-}" ] && hdr=(-H "x-vercel-protection-bypass: $VERCEL_PROTECTION_BYPASS")
  say "Smoke test $base"

  check() { # name, path, python expression over parsed JSON `j` (empty = status only)
    local name="$1" path="$2" expr="${3:-}" body code
    body="$(mktemp)"
    code="$(curl -sS -o "$body" -w '%{http_code}' --max-time 30 ${hdr[@]+"${hdr[@]}"} "$base$path" || echo 000)"
    if [ "$code" = 401 ]; then
      echo "  FAIL $name: 401, Vercel deployment protection is on. Set VERCEL_PROTECTION_BYPASS or turn protection off for this project."
      failed=1; rm -f "$body"; return
    fi
    if [ "$code" != 200 ]; then echo "  FAIL $name: HTTP $code"; failed=1; rm -f "$body"; return; fi
    if [ -n "$expr" ] && ! python3 -c 'import json,sys; j=json.load(open(sys.argv[1])); assert '"$expr" "$body" 2>/dev/null; then
      echo "  FAIL $name: unexpected body"; failed=1; rm -f "$body"; return
    fi
    echo "  ok   $name"; rm -f "$body"
  }

  # pages
  for page in / /invest/ /invest/start.html "/invest/city.html?c=$CITY" /invest/state.html /invest/js/city.js; do
    check "page $page" "$page"
  done
  # API: every endpoint the city page calls
  check "meta"      "/v1/meta"                              'j.get("presets")'
  check "states"    "/v1/states"                            'j.get("states")'
  check "city"      "/v1/cities/$CITY"                      'j["id"]=="'"$CITY"'"'
  check "areas"     "/v1/cities/$CITY/areas?limit=5"        'j["features"]'
  check "assets"    "/v1/cities/$CITY/assets?layers=bus_stops" ''
  check "projects"  "/v1/cities/$CITY/projects"             '"projects" in j'
  check "compare"   "/v1/cities/$CITY/compare"              '"others" in j'
  # an unknown city must be a JSON 404, not a page or a 500
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 ${hdr[@]+"${hdr[@]}"} "$base/v1/cities/no-such-city" || echo 000)"
  if [ "$code" = 404 ]; then echo "  ok   unknown city is 404"; else echo "  FAIL unknown city: HTTP $code (want 404)"; failed=1; fi

  [ "$failed" = 0 ] || die "smoke test failed for $base"
  echo "  all checks passed"
}

if [ -n "$SMOKE_URL" ]; then smoke "$SMOKE_URL"; exit 0; fi

if [ "$SKIP_TESTS" = 0 ]; then
  say "Checks"
  command -v node >/dev/null || die "node not found"
  (cd "$ROOT" && node --test 'web/invest/js/*.test.mjs' >/dev/null) || die "web/invest page tests failed"
  python3 -m py_compile "$ROOT/mock_api.py" "$STAGE/api/v1.py" || die "python does not compile"
  echo "  ok"
fi

say "Stage $STAGE"
# only generated directories are cleared; the committed vercel.json and api/v1.py stay
rm -r "$STAGE/public" "$STAGE/api/_lib" 2>/dev/null || true
mkdir -p "$STAGE/public" "$STAGE/api/_lib/fixtures"
# pages + the non-invest fixtures the other pages fetch; the invest fixtures live with the function
rsync -a --exclude 'fixtures/invest' --exclude '*.test.mjs' --exclude '*.lock' --exclude '.DS_Store' "$ROOT/web/" "$STAGE/public/"
cp "$ROOT/mock_api.py" "$STAGE/api/_lib/mock_api.py"
rsync -a --exclude '.DS_Store' "$ROOT/web/fixtures/invest" "$STAGE/api/_lib/fixtures/"
for f in cities.json meta.json states.json projects.json; do
  [ -f "$STAGE/api/_lib/fixtures/invest/$f" ] || die "missing fixture $f"
done
# config.js only maps :8765/:8766 to a local API, so on Vercel the pages call same-origin /v1
echo "  public: $(du -sh "$STAGE/public" | cut -f1), function bundle: $(du -sh "$STAGE/api" | cut -f1)"

# the function must answer locally before anything is uploaded
say "Local function check"
python3 - "$STAGE" "$CITY" <<'PY'
import importlib.util, json, sys, threading, urllib.request
from http.server import HTTPServer
stage, city = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("fn", f"{stage}/api/v1.py")
fn = importlib.util.module_from_spec(spec); spec.loader.exec_module(fn)
srv = HTTPServer(("127.0.0.1", 0), fn.handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
for path in (f"/v1/cities/{city}", f"/api/v1?__p=cities/{city}/projects", f"/api/v1?__p=cities/{city}/areas&limit=1"):
    with urllib.request.urlopen(base + path, timeout=20) as r:
        assert r.status == 200 and isinstance(json.load(r), dict), path
    print("  ok  ", path)
srv.shutdown()
PY

[ "$STAGE_ONLY" = 1 ] && { echo; echo "Staged. Deploy with: cd deploy/vercel && vercel deploy"; exit 0; }

command -v vercel >/dev/null || die "vercel CLI not found (npm i -g vercel)"
vercel whoami >/dev/null 2>&1 || die "not logged in: run 'vercel login'"
scope=(); [ -n "${VERCEL_SCOPE:-}" ] && scope=(--scope "$VERCEL_SCOPE")

cd "$STAGE"
if [ ! -f .vercel/project.json ]; then
  say "Link project $PROJECT"
  vercel link --yes --project "$PROJECT" ${scope[@]+"${scope[@]}"}
fi

say "Deploy ($([ "$PROD" = 1 ] && echo production || echo preview))"
args=(deploy --yes ${scope[@]+"${scope[@]}"}); [ "$PROD" = 1 ] && args+=(--prod)
OUT="$(vercel "${args[@]}" 2>&1 | tee /dev/stderr)"
# the stable alias is public; the per-deployment URL sits behind Vercel login on most accounts
URL="$(printf '%s\n' "$OUT" | grep -Eo 'Aliased +https://[^ ]+' | grep -Eo 'https://.*' | head -n1)"
[ -n "$URL" ] || URL="$(printf '%s\n' "$OUT" | grep -Eo 'https://[^ ]+\.vercel\.app' | tail -n1)"
[ -n "$URL" ] || die "could not read the deployment URL from vercel"
echo "  $URL"

smoke "$URL"
say "Done: $URL"
