"""``sustainkit ghg ...`` commands."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

import pandas as pd

from sustainkit.ghg.calc import InventoryError, calculate, load_activities
from sustainkit.ghg.factors import load_factors


def example_activities_path() -> Path:
    return Path(str(resources.files("sustainkit.ghg") / "data" / "example" / "activities.csv"))


def cmd_calc(args) -> int:
    fs = load_factors(args.factors)
    inv = calculate(load_activities(args.input, args.sheet), fs)
    for w in inv.warnings:
        print(f"warning: {w}", file=sys.stderr)
    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        inv.rows.to_csv(args.csv, index=False, float_format="%.6g")
        print(f"wrote {args.csv}")
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(inv.to_markdown(), encoding="utf-8")
        print(f"wrote {args.markdown}")
    if args.chart:
        from sustainkit.ghg.plot import plot_breakdown

        plot_breakdown(inv, args.chart, by=args.by, title=args.title)
        print(f"wrote {args.chart}")
    with pd.option_context("display.float_format", "{:,.2f}".format):
        print(inv.summary().to_string(index=False))
    return 0


def cmd_factors(args) -> int:
    fs = load_factors(args.factors)
    hits = fs.search(" ".join(args.terms), scope=args.scope, unit=args.unit)
    cols = ["scope", "level1", "level2", "level3", "level4", "variant", "unit", "kg_co2e"]
    with pd.option_context("display.max_rows", args.limit, "display.width", 200, "display.max_colwidth", 40):
        print(hits[cols].head(args.limit).to_string(index=False))
    print(f"{len(hits)} factor(s) from {fs.name}")
    return 0


def cmd_example(args) -> int:
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(example_activities_path().read_bytes())
    print(f"wrote {dest} (fictional example data)")
    return 0


def add_parser(sub) -> None:
    g = sub.add_parser("ghg", help="Scope 1 and 2 GHG inventory with sourced emission factors")
    gs = g.add_subparsers(dest="ghg_command", required=True)
    c = gs.add_parser("calc", help="calculate an inventory from activity data")
    c.add_argument("input", type=Path, help="activities .csv or .xlsx")
    c.add_argument("--sheet", default=None)
    c.add_argument("--factors", type=Path, default=None, help="custom factor CSV (default: UK Gov 2025)")
    c.add_argument("--csv", type=Path)
    c.add_argument("--markdown", type=Path)
    c.add_argument("--chart", type=Path)
    c.add_argument("--title", default="Scope 1 and 2 emissions")
    c.add_argument("--by", default="level2", help="chart grouping column (level1, level2, site, period...)")
    c.set_defaults(func=cmd_calc)
    f = gs.add_parser("factors", help="search the emission factor table")
    f.add_argument("terms", nargs="*")
    f.add_argument("--scope", default=None)
    f.add_argument("--unit", default=None)
    f.add_argument("--factors", type=Path, default=None)
    f.add_argument("--limit", type=int, default=40)
    f.set_defaults(func=cmd_factors)
    e = gs.add_parser("example", help="copy the fictional example activity file")
    e.add_argument("dest", nargs="?", default="activities.csv")
    e.set_defaults(func=cmd_example)


def handle_error(exc: Exception) -> int:
    if isinstance(exc, InventoryError):
        print(str(exc), file=sys.stderr)
        return 2
    raise exc


def main(argv=None) -> int:  # standalone: python -m sustainkit.ghg.cli
    p = argparse.ArgumentParser(prog="sustainkit")
    sub = p.add_subparsers(dest="command", required=True)
    add_parser(sub)
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except InventoryError as exc:
        return handle_error(exc)
