"""The parser keeps dimensions, skips nil and text facts, and fails loud on a dangling context."""
import json

import pytest

from wtpw.xbrl_facts import parse_instance

DOC = b"""<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
  xmlns:us-gaap="http://fasb.org/us-gaap/2025" xmlns:lmt="http://www.lockheedmartin.com/20251231"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <xbrli:context id="FY"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="FY_AERO"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>
    <xbrli:segment>
      <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">lmt:AeronauticsMember</xbrldi:explicitMember>
      <xbrldi:explicitMember dimension="srt:ConsolidationItemsAxis">us-gaap:OperatingSegmentsMember</xbrldi:explicitMember>
    </xbrli:segment></xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
  <us-gaap:Revenues contextRef="FY" unitRef="usd" decimals="-6">75048000000</us-gaap:Revenues>
  <us-gaap:Revenues contextRef="FY_AERO" unitRef="usd" decimals="-6">30000000000</us-gaap:Revenues>
  <us-gaap:OperatingIncomeLoss contextRef="FY" unitRef="usd" decimals="-6" xsi:nil="true"/>
  <us-gaap:SegmentReportingDisclosureTextBlock contextRef="FY">text</us-gaap:SegmentReportingDisclosureTextBlock>
</xbrli:xbrl>"""


def test_dimensions_kept_and_noise_skipped():
    rows = parse_instance(DOC, "0000936468-26-000001")
    assert len(rows) == 2
    seg = next(r for r in rows if r["n_dims"] == 2)
    dims = json.loads(seg["dims"])
    assert dims["us-gaap:StatementBusinessSegmentsAxis"] == "lmt:AeronauticsMember"
    assert seg["value"] == 30_000_000_000
    cons = next(r for r in rows if r["n_dims"] == 0)
    assert cons["concept"] == "us-gaap:Revenues" and cons["period_end"] == "2025-12-31"


def test_dangling_context_fails_loud():
    bad = DOC.replace(b'contextRef="FY_AERO"', b'contextRef="MISSING"')
    with pytest.raises(ValueError, match="unknown context"):
        parse_instance(bad, "x")
