"""Parity gate: the gold tables Databricks built must equal the gold tables DuckDB built.

Reads each gold table through the SQL Statement Execution API (via the authenticated
`databricks` CLI, profile pf), normalizes both sides (numbers to 6 decimals, NULL as empty,
rows sorted) and compares row sets. Exit 1 on any difference.
Usage: python -m wtpw.parity   (run `python -m wtpw.pipeline local` first)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from wtpw.pipeline import GOLD_EXPORT, WORK

CLI = os.environ.get("DATABRICKS_CLI", str(Path.home() / ".local/bin/databricks"))
PROFILE = os.environ.get("DATABRICKS_PROFILE", "pf")
SCHEMA = "workspace.wtpw"


def _api(method: str, path: str, body: dict | None = None) -> dict:
    cmd = [CLI, "api", method, path, "-p", PROFILE]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def warehouse_id() -> str:
    whs = _api("get", "/api/2.0/sql/warehouses").get("warehouses", [])
    if not whs:
        raise SystemExit("no SQL warehouse in this workspace")
    return whs[0]["id"]


def query(sql: str, wh: str) -> pd.DataFrame:
    res = _api("post", "/api/2.0/sql/statements",
               {"warehouse_id": wh, "statement": sql, "wait_timeout": "30s",
                "format": "JSON_ARRAY", "disposition": "INLINE"})
    while res["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        res = _api("get", f"/api/2.0/sql/statements/{res['statement_id']}")
    if res["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"statement failed: {res['status']}")
    cols = [c["name"] for c in res["manifest"]["schema"]["columns"]]
    if res["manifest"].get("total_chunk_count", 1) > 1:
        raise RuntimeError("result spans multiple chunks; extend parity to fetch them")
    return pd.DataFrame(res["result"].get("data_array", []), columns=cols)


def normalize(df: pd.DataFrame) -> list[tuple]:
    def cell(v):
        if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
            return ""
        try:
            return f"{float(v):.6f}"
        except (TypeError, ValueError):
            return str(v)[:10] if str(v)[:4].isdigit() and len(str(v)) >= 10 else str(v)
    return sorted(tuple(cell(v) for v in row) for row in df.astype(object).itertuples(index=False))


def main() -> int:
    wh, failures = warehouse_id(), 0
    for name in GOLD_EXPORT:
        local = pd.read_csv(WORK / "gold_local" / f"{name}.csv", dtype=str, keep_default_na=False)
        remote = query(f"SELECT {', '.join(local.columns)} FROM {SCHEMA}.{name}", wh)
        a, b = normalize(local), normalize(remote)
        only_local, only_remote = set(a) - set(b), set(b) - set(a)
        ok = not only_local and not only_remote and len(a) == len(b)
        failures += not ok
        print(f"{name}: local {len(a)} rows, databricks {len(b)} rows -> {'MATCH' if ok else 'DIFF'}")
        for row in sorted(only_local)[:3]:
            print("   only local:     ", row)
        for row in sorted(only_remote)[:3]:
            print("   only databricks:", row)
    print("parity:", "PASS" if not failures else "FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
