"""Vercel function for /v1/*: the read-only investor API, served by mock_api.py from the bundled fixtures.

scripts/deploy-vercel.sh copies mock_api.py and web/fixtures/invest into ../_lib before every deploy.
The Go API (api/) is a long-running server with an in-memory store; it does not fit a serverless function.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.join(_HERE, "..", "_lib")
os.environ.setdefault("INVEST_FIXTURES", os.path.join(_LIB, "fixtures", "invest"))
sys.path.insert(0, _LIB)

from mock_api import Handler as _Handler  # noqa: E402  (needs the lines above)


class handler(_Handler):
    def do_GET(self):
        # the rewrite may reach us as /api/v1/... or /v1/...; the routes below expect /v1/...
        if self.path.startswith("/api/"):
            self.path = self.path[len("/api"):]
        super().do_GET()
