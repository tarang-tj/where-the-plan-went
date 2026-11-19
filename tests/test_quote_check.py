"""quote_check passes a true row and catches a wrong digit, a paraphrased quote and a missing file."""
import pandas as pd

from wtpw import quote_check
from wtpw.sec_client import cache_path

HTML = (
    "<html><body><p>2025 Financial Outlook</p><table><tr><td>Business segment operating profit</td>"
    "<td>~$8,100 &#8211; $8,200</td></tr></table>"
    "<p>we recognized a reach&#8209;forward loss of $950&nbsp;million on a classified program</p></body></html>"
)


def _row(**kw):
    base = {"cik": 936468, "accession": "0000936468-25-000006", "document": "ex991.htm",
            "quote": "Business segment operating profit ~$8,100 - $8,200", "low": 8100, "high": 8200}
    base.update(kw)
    return pd.Series(base)


def _cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    quote_check.filing_text.cache_clear()
    url = "https://www.sec.gov/Archives/edgar/data/936468/000093646825000006/ex991.htm"
    path = cache_path(url)
    path.parent.mkdir(parents=True)
    path.write_text(HTML)


def test_true_row_passes(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    assert quote_check.check_row(_row()) == []
    charge = _row(quote="reach-forward loss of $950 million on a classified program",
                  low=None, high=None, amount=950)
    assert quote_check.check_row(charge) == []


def test_wrong_digit_fails(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    errors = quote_check.check_row(_row(high=8300))
    assert errors == ["high=8300 not printed in quote"]


def test_paraphrase_fails(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    errors = quote_check.check_row(_row(quote="Segment operating profit of $8,100 to $8,200"))
    assert "quote not found in filing text" in errors


def test_uncached_filing_fails(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    errors = quote_check.check_row(_row(document="missing.htm"))
    assert errors and errors[0].startswith("not cached")
