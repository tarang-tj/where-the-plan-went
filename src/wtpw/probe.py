"""Boot probe for the public page: serve web/ on a local port, load it in Chrome through Playwright at
1440x900 and 375x812, and fail on console errors, failed or off-host requests, a broken story or a
layout wider than the phone screen. Screenshots go to outputs/probe-1440.png and outputs/probe-375.png.
Usage: python -m wtpw.probe [web_dir]   (exit 1 on any failure)
"""
from __future__ import annotations

import functools
import json
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

WEB = Path("web")
OUT = Path("outputs")
SIZES = [(1440, 900), (375, 812)]
DEFAULT_KEY = "LMT-2025-SegmentOP"
SWITCH = ("NOC", "2023")

OVERFLOW_JS = """() => {
  const w = window.innerWidth, bad = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width > w + 1 || (r.width > 0 && r.right > w + 1)) {
      bad.push(`${el.tagName.toLowerCase()}#${el.id}.${el.className.baseVal ?? el.className} right=${Math.round(r.right)}`);
    }
  }
  return {scroll: document.documentElement.scrollWidth, width: w, bad: bad.slice(0, 8)};
}"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # keep probe output to the verdict
        pass


def serve(root: Path) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _num(text: str) -> float:
    """'-1,615', '−950', '+88', '$300 million' -> magnitude as a float (signs and commas stripped)."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text or "")
    return float(m.group().replace(",", "")) if m else float("nan")


def check_numbers(page, numbers: dict) -> list[str]:
    """The default view must print exactly the values in data.json numbers (catches a wrong number, not just a crash)."""
    fails = []
    want = {k: _num(numbers[f"bridge_LMT_2025_{k}"]["display"]) for k in ("plan_op", "named_charges", "actual_op")}
    totals = page.locator("#bridge-chart text.wv.total").all_text_contents()
    charges = page.locator("#bridge-chart text.wv.charge").all_text_contents()
    got = {"plan_op": _num(totals[0]) if totals else None, "actual_op": _num(totals[-1]) if totals else None,
           "named_charges": sum(_num(t) for t in charges)}
    row = "#cube-table tr[data-key='LMT-2025']"
    got_cube = {"plan_op": _num(page.inner_text(f"{row} td.plan")), "actual_op": _num(page.inner_text(f"{row} td.actual"))}
    for k, v in want.items():
        if got[k] != v:
            fails.append(f"bridge {k} shows {got[k]}, numbers says {v}")
        if k in got_cube and got_cube[k] != v:
            fails.append(f"cube LMT 2025 {k} shows {got_cube[k]}, numbers says {v}")
    threshold = numbers["large_miss_threshold"]["display"]
    if threshold not in page.inner_text("#pattern-text"):
        fails.append(f"pattern sentence lacks the large-miss threshold {threshold!r}")
    return fails


def check_page(browser, base: str, width: int, height: int, numbers: dict) -> list[str]:
    fails: list[str] = []
    host = urlparse(base).netloc
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    page.on("console", lambda m: fails.append(f"console error: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: fails.append(f"page error: {e}"))
    page.on("requestfailed", lambda r: fails.append(f"request failed: {r.url} {r.failure}"))
    page.on("response", lambda r: fails.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 else None)
    page.on("request", lambda r: fails.append(f"off-host request: {r.url}")
            if urlparse(r.url).scheme not in ("data", "blob") and urlparse(r.url).netloc != host else None)
    try:
        page.goto(base + "index.html")
        page.wait_for_selector("body[data-ready=true]", timeout=15000)
        headline = page.inner_text("#hero-h").strip()
        if not re.search(r"\$\d", headline):
            fails.append(f"hero headline has no dollar amount: {headline!r}")
        if page.get_attribute("#hero", "data-key") != DEFAULT_KEY:
            fails.append(f"default selection is {page.get_attribute('#hero', 'data-key')}, want {DEFAULT_KEY}")
        if "950" not in page.inner_text("#callout"):
            fails.append("callout does not list the 950 charge")
        fails += check_numbers(page, numbers)
        lay = page.evaluate(OVERFLOW_JS)
        if lay["scroll"] > lay["width"] or lay["bad"]:
            fails.append(f"wider than the {width}px viewport: scrollWidth={lay['scroll']} {lay['bad']}")
        OUT.mkdir(exist_ok=True)
        page.screenshot(path=str(OUT / f"probe-{width}.png"), full_page=True)
        page.select_option("#pick-ticker", SWITCH[0])
        page.select_option("#pick-year", SWITCH[1])
        want = f"{SWITCH[0]}-{SWITCH[1]}"
        if page.get_attribute("#hero", "data-key") != f"{want}-SegmentOP":
            fails.append(f"hero did not switch to {want}: {page.get_attribute('#hero', 'data-key')}")
        if page.inner_text("#hero-h").strip() == headline:
            fails.append("hero headline did not change on switch")
        if page.get_attribute("#bridge", "data-key") != want:
            fails.append(f"bridge did not switch to {want}: {page.get_attribute('#bridge', 'data-key')}")
        if not page.query_selector("#bridge-chart svg"):
            fails.append("bridge chart missing after switch")
    except PlaywrightError as exc:  # a timeout or missing node is a failure, not a crash
        fails.append(f"probe step failed: {type(exc).__name__}: {str(exc).splitlines()[0]}")
    finally:
        ctx.close()
    return [f"[{width}] {f}" for f in fails]


def run(root: Path = WEB) -> int:
    server = serve(root)
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    fails: list[str] = []
    numbers = json.loads((root / "data.json").read_text())["numbers"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            for w, h in SIZES:
                fails += check_page(browser, base, w, h, numbers)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    for f in fails:
        print("FAIL", f)
    print(f"probe: {'FAIL' if fails else 'PASS'} ({len(fails)} failures) serving {root} at {base}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]) if len(sys.argv) > 1 else WEB))
