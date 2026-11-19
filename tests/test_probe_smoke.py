"""The page probe passes on the real web/ build (skipped when Playwright or Chrome is not available)."""
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

from wtpw import probe  # imported after the skip so a missing Playwright skips, not errors

ROOT = Path(__file__).resolve().parents[1]


def _chrome() -> bool:
    try:
        with pw.sync_playwright() as p:
            p.chromium.launch(channel="chrome").close()
        return True
    except pw.Error:
        return False


@pytest.mark.skipif(not _chrome(), reason="Playwright with the Chrome channel is not available")
def test_probe_passes(monkeypatch):
    monkeypatch.chdir(ROOT)
    assert probe.run(ROOT / "web") == 0
