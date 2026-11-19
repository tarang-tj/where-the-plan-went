"""Parse an XBRL instance document into a flat fact table.

One row per numeric fact: concept (prefix:name), period, dimensions (axis=member pairs, sorted),
unit, decimals and value. Dimensions are kept, which is the point: segment revenue and operating
profit live on dimensional contexts that SEC's companyfacts API drops (research r2, item 1).
"""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from lxml import etree

XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
NON_FACT_NS = {XBRLI, "http://www.xbrl.org/2003/linkbase", "http://www.w3.org/1999/xlink"}


def _qname(el: etree._Element, text: str | None = None) -> str:
    """Render an element (or a QName string in element text) as prefix:local."""
    if text is not None:
        prefix, _, local = text.strip().rpartition(":")
        return f"{prefix}:{local}" if prefix else local
    q = etree.QName(el)
    prefix = el.prefix or next((p for p, ns in el.nsmap.items() if ns == q.namespace), "")
    return f"{prefix}:{q.localname}" if prefix else q.localname


def _contexts(root: etree._Element) -> dict[str, dict]:
    out = {}
    for ctx in root.iter(f"{{{XBRLI}}}context"):
        period = ctx.find(f"{{{XBRLI}}}period")
        start = period.findtext(f"{{{XBRLI}}}startDate")
        end = period.findtext(f"{{{XBRLI}}}endDate")
        instant = period.findtext(f"{{{XBRLI}}}instant")
        dims = {}
        for mem in ctx.iter(f"{{{XBRLDI}}}explicitMember"):
            dims[_qname(mem, mem.get("dimension"))] = _qname(mem, mem.text)
        for mem in ctx.iter(f"{{{XBRLDI}}}typedMember"):
            dims[_qname(mem, mem.get("dimension"))] = "".join(mem.itertext()).strip()
        out[ctx.get("id")] = {
            "start": start, "end": end or instant, "instant": instant is not None,
            "dims": json.dumps(dict(sorted(dims.items()))),
            "n_dims": len(dims),
        }
    return out


def parse_instance(xml: bytes, accession: str) -> list[dict]:
    root = etree.fromstring(xml, parser=etree.XMLParser(huge_tree=True, resolve_entities=False))
    contexts = _contexts(root)
    rows = []
    for el in root:
        if not isinstance(el.tag, str) or etree.QName(el).namespace in NON_FACT_NS:
            continue
        ctx_id, unit = el.get("contextRef"), el.get("unitRef")
        if ctx_id is None or unit is None:  # text blocks and non-numeric facts
            continue
        if el.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            continue
        try:
            value = Decimal((el.text or "").strip())
        except InvalidOperation:
            continue
        ctx = contexts.get(ctx_id)
        if ctx is None:
            raise ValueError(f"{accession}: fact {el.tag} references unknown context {ctx_id}")
        rows.append({
            "accession": accession, "concept": _qname(el), "context_id": ctx_id,
            "period_start": ctx["start"], "period_end": ctx["end"], "instant": ctx["instant"],
            "dims": ctx["dims"], "n_dims": ctx["n_dims"], "unit": unit,
            "decimals": el.get("decimals"), "value": float(value),
        })
    return rows
