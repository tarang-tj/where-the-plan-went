"""The memo renderer only lets numbers.csv put numbers into the memo."""
import pytest

from wtpw.memo import MemoError, build_markdown, hand_typed, render, to_html

NUMBERS = {"lmt_charges": "-1,615", "cover": "98%"}


def _build(tmp_path, text):
    template, nums, out = tmp_path / "t.md", tmp_path / "n.csv", tmp_path / "memo.md"
    template.write_text(text)
    nums.write_text("key,value,display,note\n" + "".join(f'{k},0,"{v}",x\n' for k, v in NUMBERS.items()))
    return build_markdown(template, out, nums), out


def test_unknown_key_fails(tmp_path):
    with pytest.raises(MemoError, match="line 2: no_such_key"):
        _build(tmp_path, "# Memo\nCharges were {{no_such_key}} $M.\n")


def test_hand_typed_number_fails_with_line(tmp_path):
    with pytest.raises(MemoError, match=r"t\.md:3: '\$1,615' in: LMT booked \$1,615M"):
        _build(tmp_path, "# Memo\n\nLMT booked $1,615M in charges.\n")
    assert not (tmp_path / "memo.md").exists()


def test_allowed_year_and_substituted_numbers_pass(tmp_path):
    text, out = _build(tmp_path, "# Memo\n\n1. In 2025, charges of {{lmt_charges}} $M covered {{cover}}.\n")
    assert "In 2025, charges of -1,615 $M covered 98%." in text
    assert out.read_text() == text


@pytest.mark.parametrize("line", ["Cover was 98%.", "EPS of 6.42", "1,615 in charges", "in 2031", "{{cover}}5"])
def test_other_hand_typed_tokens_fail(line):
    assert hand_typed(render(line, NUMBERS)[1]), line


@pytest.mark.parametrize("line", ["The 10-K for FY2025 Q3", "See https://www.sec.gov/Archives/edgar/data/936468/x.htm"])
def test_identifiers_and_urls_pass(line):
    assert not hand_typed(render(line, NUMBERS)[1])


def test_html_converter_covers_basic_markdown():
    h = to_html("# T\n\npara **b**\n\n- a\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n<!-- hidden -->")
    assert "<h1>T</h1>" in h and "<strong>b</strong>" in h and "<ul><li>a</li><li>b</li></ul>" in h
    assert "<td>1</td><td>2</td>" in h and "hidden" not in h


def test_program_designators_are_names_not_figures():
    from wtpw.memo import hand_typed
    assert hand_typed("The B-21 and KC-46A programs.") == []
    assert hand_typed("A B-21 loss of $477 million.")[0][1] == "$477"
