"""Write the SYNTHETIC Program FPD-1 tables to CSV: python -m wtpw.program [--out DIR]."""

from __future__ import annotations

import argparse
from pathlib import Path

from wtpw.program.simulate import PRICE, PROGRAM, simulate

DEFAULT_OUT = Path(__file__).resolve().parents[3] / "data" / "program"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Write {PROGRAM} ledger, EVM and revrec CSVs.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = parser.parse_args(argv)
    tables = simulate()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        path = args.out / f"program_{name}.csv"
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")
    rr = tables["revrec"]
    loss = rr[rr["eac"] > PRICE]
    first = int(loss["month"].iloc[0]) if len(loss) else None
    print(f"{PROGRAM}: first loss month {first}, final cost {rr['cum_cost'].iloc[-1]:.3f}, "
          f"final cumulative gross profit {rr['cum_gross_profit'].iloc[-1]:.3f} (SYNTHETIC)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
