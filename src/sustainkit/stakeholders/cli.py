"""``sustainkit stakeholders ...`` commands."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

import pandas as pd

from sustainkit.stakeholders.register import WEIGHT_SCHEMES, MapConfig, RegisterError, build_map, load_register


def example_register_path() -> Path:
    return Path(str(resources.files("sustainkit.stakeholders") / "data" / "example" / "register.csv"))


def cmd_map(args) -> int:
    cfg = MapConfig(scale=args.scale, threshold=args.threshold, weight_scheme=args.weight_scheme)
    smap = build_map(load_register(args.input, args.sheet), cfg, as_of=args.as_of)
    for w in smap.warnings:
        print(f"warning: {w}", file=sys.stderr)
    if args.survey:
        sv = pd.read_csv(args.survey) if str(args.survey).endswith(".csv") else pd.read_excel(args.survey, sheet_name="survey")
        sv.columns = [str(c).strip().lower().replace(" ", "_") for c in sv.columns]
        link = smap.link_survey(sv["stakeholder_group"].dropna().unique())
        for k, v in link.items():
            if v:
                print(f"warning: groups {k.replace('_', ' ')}: {v}", file=sys.stderr)
    outs = [(args.csv, lambda p: smap.table.to_csv(p, index=False, date_format="%Y-%m-%d")),
            (args.weights, lambda p: smap.weights[["stakeholder_group", "weight"]].to_csv(p, index=False, float_format="%.4f")),
            (args.markdown, lambda p: Path(p).write_text(smap.to_markdown(), encoding="utf-8"))]
    for path, write in outs:
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            write(path)
            print(f"wrote {path}")
    if args.chart:
        from sustainkit.stakeholders.plot import plot_map

        plot_map(smap, args.chart, title=args.title)
        print(f"wrote {args.chart}")
    print(smap.quadrant_counts().to_string())
    print()
    print(smap.engagement_status_counts().to_string())
    return 0


def cmd_example(args) -> int:
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(example_register_path().read_bytes())
    print(f"wrote {dest} (fictional example data)")
    return 0


def add_parser(sub) -> None:
    p = sub.add_parser("stakeholders", help="stakeholder register, influence x interest map, engagement plan, survey weights")
    s = p.add_subparsers(dest="stakeholders_command", required=True)
    m = s.add_parser("map", help="classify a register, plan engagement, derive materiality survey weights")
    m.add_argument("input", help="register CSV or Excel")
    m.add_argument("--sheet", default=None)
    m.add_argument("--scale", type=int, default=5, help="ratings run 1..scale (default 5)")
    m.add_argument("--threshold", type=float, default=None, help="'high' cut-off (default: scale midpoint)")
    m.add_argument("--weight-scheme", default="salience", choices=WEIGHT_SCHEMES)
    m.add_argument("--as-of", default=None, help="date for the engagement status (default today)")
    m.add_argument("--survey", default=None, help="materiality survey CSV/XLSX to check group names against")
    m.add_argument("--csv", default=None, help="write the classified register")
    m.add_argument("--weights", default=None, help="write stakeholder_group,weight for `sustainkit materiality`")
    m.add_argument("--markdown", default=None)
    m.add_argument("--chart", default=None, help="write the influence x interest map (PNG)")
    m.add_argument("--title", default=None)
    m.set_defaults(func=cmd_map)
    e = s.add_parser("example", help="write the fictional example register")
    e.add_argument("dest", nargs="?", default="stakeholders.csv")
    e.set_defaults(func=cmd_example)


__all__ = ["RegisterError", "add_parser"]
