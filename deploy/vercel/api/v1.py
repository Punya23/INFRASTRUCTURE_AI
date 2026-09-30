"""Vercel function for /v1/*: the read-only investor API, served by mock_api.py from the bundled fixtures.

scripts/deploy-vercel.sh copies mock_api.py and web/fixtures/invest into ../_lib before every deploy.
The Go API (api/) is a long-running server with an in-memory store; it does not fit a serverless function.
"""
import os
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_HERE, "_lib")
os.environ.setdefault("INVEST_FIXTURES", os.path.join(_LIB, "fixtures", "invest"))
sys.path.insert(0, _LIB)

from mock_api import Handler as _Handler  # noqa: E402  (needs the lines above)


class handler(_Handler):
    def do_GET(self):
        # vercel.json rewrites /v1/<path> to /api/v1?__p=<path>; put the original path back for the routes
        url = urlsplit(self.path)
        query = parse_qsl(url.query, keep_blank_values=True)
        sub = next((v for k, v in query if k == "__p"), None)
        if sub is not None:
            rest = urlencode([(k, v) for k, v in query if k != "__p"])
            self.path = f"/v1/{sub}" + (f"?{rest}" if rest else "")
        super().do_GET()
