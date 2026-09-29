"""Download registered sources into data/raw/ and record a manifest in data/manifests/.

Sources are declared once in config/sources.yaml. A download is kept only if its first bytes match
the declared kind — dead government links often answer HTTP 200 with an HTML page
(skill add-data-source). Re-running skips files already present with the manifest's size.

    uv run python -m common.fetch               # every source
    uv run python -m common.fetch osm_india     # selected sources
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFESTS = ROOT / "data" / "manifests"
REGISTRY = ROOT / "config" / "sources.yaml"
USER_AGENT = "INFRA-AI data pipeline (+https://github.com/Punya23/INFRASTRUCTURE_AI)"
CHUNK = 1 << 20

SIGNATURES = {
    "pbf": lambda head: b"OSMHeader" in head[:64],
    "tiff": lambda head: head[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"),
    "zip": lambda head: head[:4] == b"PK\x03\x04",
    "pdf": lambda head: head[:5] == b"%PDF-",
    "shp": lambda head: head[:4] == b"\x00\x00\x27\x0a",
    "dbf": lambda head: head[:1] in (b"\x03", b"\x30", b"\x83", b"\x8b"),
    "text": lambda head: head.lstrip()[:1] != b"<",  # CSV, PRJ, CPG — anything but an HTML page
    "html": lambda head: b"<" in head[:1024],
}


class FetchError(RuntimeError):
    """A download failed or did not look like the declared file type."""


def matches_kind(head: bytes, kind: str) -> bool:
    """True if the first bytes of a file look like the declared kind."""
    if kind not in SIGNATURES:
        raise FetchError(f"unknown kind {kind!r}")
    return SIGNATURES[kind](head)


def load_registry(path: Path = REGISTRY) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _files(source: dict) -> list[dict]:
    if "files" in source:
        return source["files"]
    keys = ("url", "dest", "kind", "layer", "keep", "srs", "tls_max")
    return [{k: source[k] for k in keys if k in source}]


def tls_context(tls_max: str | None) -> ssl.SSLContext | None:
    """Certificate-verifying context, optionally capped at TLS 1.2 (`tls_max: "1.2"` in the registry).

    Some government servers drop the large TLS 1.3 ClientHello that OpenSSL 3.5 sends (post-quantum
    key share) and fail with UNEXPECTED_EOF; TLS 1.2 sends no key share. Verification stays on.
    """
    if tls_max is None:
        return None
    if str(tls_max) != "1.2":
        raise FetchError(f"unsupported tls_max {tls_max!r} (only '1.2')")
    ctx = ssl.create_default_context()
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def _get(url: str, attempts: int = 3, context: ssl.SSLContext | None = None) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=180, context=context) as response:
                return response.read()
        except (OSError, http.client.HTTPException) as exc:  # network errors: retry, then fail loudly
            last_error = exc
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise FetchError(f"{url}: {last_error}") from last_error


def _download_wfs(
    url: str, layer: str, keep: list[str], dest: Path, srs: str | None = "EPSG:4326", page: int = 5000,
    context: ssl.SSLContext | None = None,
) -> tuple[int, str]:
    """Page through a WFS layer (read-only GetFeature) and write one GeoJSON file.

    Only properties in `keep` survive — a keep-list, so unknown or personal fields never land on
    disk (ADR-0011). Fails if the feature count differs from the server's numberMatched.
    """
    features: list[dict] = []
    matched = None
    start = 0
    while True:
        params = {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer,
            "outputFormat": "application/json", "count": page,
        }
        if start:  # layers without a primary key reject startIndex; only send it when paging
            params["startIndex"] = start
        if srs:  # layers without geometry reject srsName
            params["srsName"] = srs
        query = urllib.parse.urlencode(params)
        payload = _get(f"{url}?{query}", context=context)
        if not matches_kind(payload[:1024], "text"):
            raise FetchError(f"{layer}: server returned HTML/XML instead of GeoJSON")
        data = json.loads(payload)
        batch = data.get("features", [])
        matched = data.get("numberMatched", matched)
        for feature in batch:
            feature["properties"] = {k: v for k, v in feature["properties"].items() if k in keep}
        features += batch
        if len(batch) < page:
            break
        start += page
        time.sleep(1)  # be polite to a government server
    if isinstance(matched, int) and matched != len(features):
        raise FetchError(f"{layer}: got {len(features)} features, server reported {matched}")
    body = json.dumps({"type": "FeatureCollection", "features": features}).encode()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return len(body), hashlib.sha256(body).hexdigest()


def _download(url: str, dest: Path, kind: str, attempts: int = 3,
              context: ssl.SSLContext | None = None) -> tuple[int, str]:
    """Stream url to dest atomically; return (bytes, sha256). Raises FetchError."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            digest, size, head = hashlib.sha256(), 0, b""
            with urllib.request.urlopen(request, timeout=60, context=context) as response, part.open("wb") as out:
                while chunk := response.read(CHUNK):
                    if len(head) < 1024:
                        head += chunk[: 1024 - len(head)]
                    digest.update(chunk)
                    out.write(chunk)
                    size += len(chunk)
            if not matches_kind(head, kind):
                part.unlink(missing_ok=True)
                raise FetchError(f"{url} did not return a {kind} file (got {head[:40]!r})")
            part.replace(dest)
            return size, digest.hexdigest()
        except FetchError:
            raise
        except (OSError, http.client.HTTPException) as exc:  # network errors: retry, then fail loudly
            last_error = exc
            part.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise FetchError(f"{url}: {last_error}") from last_error


def fetch(source_id: str, source: dict, force: bool = False) -> Path:
    """Fetch one registered source and write its manifest. Returns the manifest path."""
    manifest_path = MANIFESTS / f"{source_id}.yaml"
    previous = {}
    if manifest_path.exists() and not force:
        previous = {f["file"]: f for f in yaml.safe_load(manifest_path.read_text())["files"]}
    records = []
    for spec in _files(source):
        dest = RAW / spec["dest"]
        rel = str(dest.relative_to(ROOT))
        old = previous.get(rel)
        if old and dest.exists() and dest.stat().st_size == old["bytes"]:
            records.append(old)
            print(f"  skip {rel} (already fetched)")
            continue
        print(f"  get  {spec['url']} {spec.get('layer', '')}", flush=True)
        context = tls_context(spec.get("tls_max"))
        if spec["kind"] == "wfs":
            size, sha = _download_wfs(
                spec["url"], spec["layer"], spec["keep"], dest, spec.get("srs", "EPSG:4326"), context=context
            )
        else:
            size, sha = _download(spec["url"], dest, spec["kind"], context=context)
        records.append({
            "file": rel,
            "url": spec["url"],
            "bytes": size,
            "sha256": sha,
            "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    manifest = {
        "id": source_id,
        "license": source["license"],
        "attribution": source["attribution"],
        "used_by": source.get("used_by", []),
        "files": records,
    }
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="*", help="source ids (default: all)")
    parser.add_argument("--force", action="store_true", help="download again even if present")
    args = parser.parse_args(argv)
    registry = load_registry()
    unknown = [s for s in args.sources if s not in registry]
    if unknown:
        print(f"unknown source ids: {unknown}", file=sys.stderr)
        return 2
    failures = 0
    for source_id in args.sources or list(registry):
        print(f"{source_id}:")
        try:
            fetch(source_id, registry[source_id], force=args.force)
        except FetchError as exc:
            failures += 1
            print(f"  FAILED: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
