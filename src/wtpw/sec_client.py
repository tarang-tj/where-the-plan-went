"""Polite, cached SEC EDGAR client.

SEC fair-access policy (https://www.sec.gov/os/webmaster-faq): declare a User-Agent with a
contact, stay under 10 requests per second. The contact comes ONLY from the SEC_UA environment
variable, so it never lands in this repo. Every response is cached under data/raw/ by URL path,
with its sha256 in data/raw/manifest.jsonl, so a rerun never re-hits SEC.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

RAW = Path("data/raw")
MANIFEST = RAW / "manifest.jsonl"
MIN_INTERVAL_S = 0.2  # 5 requests per second, half the SEC limit
# Bodies SEC returns instead of the document when it blocks a client. Never cache these.
BLOCK_MARKERS = (b"Undeclared Automated Tool", b"Request Rate Threshold Exceeded")

_last_request = 0.0


class SecBlocked(RuntimeError):
    """SEC refused the request (missing contact UA or rate threshold)."""


def user_agent() -> str:
    ua = os.environ.get("SEC_UA", "").strip()
    if "@" not in ua:
        raise SystemExit(
            "SEC_UA is not set. SEC requires a User-Agent with a contact email, e.g.\n"
            "  export SEC_UA=\"Your Name you@example.com\"\n"
            "Set it in your shell profile; it is read at runtime and never written to the repo."
        )
    return ua


def cache_path(url: str) -> Path:
    """Mirror the URL host and path under data/raw/ (query strings are not used by our URLs)."""
    parsed = urlparse(url)
    if parsed.query:
        raise ValueError(f"query strings are not cacheable by path: {url}")
    path = RAW / parsed.netloc / parsed.path.lstrip("/")
    if not path.resolve().is_relative_to(RAW.resolve()):  # a name with ".." from an index.json
        raise ValueError(f"refusing to cache outside {RAW}: {url}")
    return path


def _throttle() -> None:
    global _last_request
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _record(url: str, path: Path, body: bytes) -> None:
    row = {
        "url": url,
        "path": str(path),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    with MANIFEST.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def get(url: str, retries: int = 4) -> bytes:
    """Return the body for url, from cache if present, else from SEC (then cached)."""
    path = cache_path(url)
    if path.exists():
        return path.read_bytes()
    headers = {"User-Agent": user_agent(), "Accept-Encoding": "identity"}
    for attempt in range(retries + 1):
        _throttle()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                body = r.read()
        except urllib.error.HTTPError as err:
            body = err.read() if hasattr(err, "read") else b""
            blocked = any(m in body for m in BLOCK_MARKERS)
            if err.code in (403, 429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt * (30 if blocked else 2))
                continue
            if blocked:
                raise SecBlocked(f"SEC blocked {url}: {body[:200]!r}") from err
            raise
        if any(m in body for m in BLOCK_MARKERS):
            raise SecBlocked(f"SEC returned a block page with HTTP 200 for {url}")
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        part.write_bytes(body)
        os.replace(part, path)  # atomic: an interrupted download never leaves a truncated cache file
        _record(url, path, body)
        return body
    raise RuntimeError(f"unreachable: retries exhausted for {url}")


def get_json(url: str) -> dict:
    return json.loads(get(url))
