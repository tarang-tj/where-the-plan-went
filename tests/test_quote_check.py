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


def test_number_must_be_whole():
    assert quote_check.printed("6,300", "cash of $6,300 million")
    assert not quote_check.printed("6,300", "cash of $16,300 million")
    assert not quote_check.printed("6,300", "cash of $6,300.5 million")
    assert quote_check.printed("8.1", "about $8.1 billion.")


def test_whole_values_match_printed_decimals():
    assert any(quote_check.printed(f, "eps of ~$26.00 - $26.30") for f in quote_check.number_forms(26.0))
    assert not any(quote_check.printed(f, "eps of ~$126.00") for f in quote_check.number_forms(26.0))


SIGNED = ("<p>unfavorable eac adjustments (442) (512)</p><p>net eac adjustments 209 410</p>"
          "<p>revenue $20.7b - $21.3b guidance</p><p>sales of $86.5 - $87.0 billion</p>")


def _signed_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    quote_check.filing_text.cache_clear()
    path = cache_path("https://www.sec.gov/Archives/edgar/data/936468/000093646825000006/ex991.htm")
    path.parent.mkdir(parents=True)
    path.write_text(SIGNED)


def test_sign_flip_fails(tmp_path, monkeypatch):
    _signed_cache(tmp_path, monkeypatch)
    row = _row(quote="unfavorable eac adjustments (442) (512)", low=None, high=None, value=-442.0)
    assert quote_check.check_row(row) == []
    flipped = _row(quote="unfavorable eac adjustments (442) (512)", low=None, high=None, value=442.0)
    assert any("positive but the quote prints it only in parentheses" in e for e in quote_check.check_row(flipped))
    neg_net = _row(quote="net eac adjustments 209 410", low=None, high=None, value=-209.0)
    assert any("negative but the quote prints it as positive" in e for e in quote_check.check_row(neg_net))


def test_unit_mislabel_fails(tmp_path, monkeypatch):
    _signed_cache(tmp_path, monkeypatch)
    ok_b = _row(quote="sales of $86.5 - $87.0 billion", low=86.5, high=87.0, unit="USD_B")
    assert quote_check.check_row(ok_b) == []
    lie = _row(quote="sales of $86.5 - $87.0 billion", low=86.5, high=87.0, unit="USD_M")
    assert any("printed in billions" in e for e in quote_check.check_row(lie))
    suffix = _row(quote="revenue $20.7b - $21.3b", low=20.7, high=21.3, unit="USD_B")
    assert quote_check.check_row(suffix) == []


def test_sign_stated_in_words_fails_when_flipped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    quote_check.filing_text.cache_clear()
    path = cache_path("https://www.sec.gov/Archives/edgar/data/936468/000093646825000006/ex991.htm")
    path.parent.mkdir(parents=True)
    path.write_text("<p>adjustments decreased segment operating profit by $180 million in 2024</p>")
    q = "decreased segment operating profit by $180 million in 2024"
    assert quote_check.check_row(_row(quote=q, low=None, high=None, value=-180.0)) == []
    flipped = quote_check.check_row(_row(quote=q, low=None, high=None, value=180.0))
    assert any("only states a decrease" in e for e in flipped)
