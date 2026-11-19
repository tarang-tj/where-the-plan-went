"""Standing gate: the README's findings block equals a fresh render from numbers.csv, so a stale
headline (68% that became 61%) fails the build. Set membership was not enough: 62% is also a value."""
from wtpw import readme_block


def test_readme_findings_are_current():
    assert readme_block.main(check=True) == 0
