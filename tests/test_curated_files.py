"""Standing gate: every committed curated CSV meets the contract (header, enums, keys)."""
from pathlib import Path

import pytest

from wtpw.curation_contract import validate

FILES = sorted(Path("curated").glob("*.csv"))


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_curated_file_meets_contract(path):
    assert validate(path) == []


def test_contract_rejects_a_bad_vintage(tmp_path):
    src = Path("curated/guidance_LMT.csv").read_text()
    bad = tmp_path / "guidance_LMT.csv"
    bad.write_text(src.replace(",Plan,", ",Budget,", 1))
    assert any("vintage='Budget'" in e for e in validate(bad))
