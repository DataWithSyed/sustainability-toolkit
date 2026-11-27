"""``sustainkit kpis ...`` commands."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

from sustainkit.kpis.datalog import KPILogError, build_report, load_log
from sustainkit.kpis.library import load_library, search


def example_log_path() -> Path:
    return Path(str(resources.files("sustainkit.kpis") / "data" / "example" / "kpi_log.csv"))


def cmd_library(args) -> int:
    lib = load_library(args.library, args.library_extra)
    out = search(lib, " ".join(args.text) if args.text else None, args.pillar)
    cols = ["kpi_id", "pillar", "unit", "direction", "kind", "esrs", "gri", "name"]
    print(out[cols].fillna("").to_string(index=False))
    return 0


def cmd_report(args) -> int:
    lib = load_library(args.library, args.library_extra)
    rep = build_report(load_log(args.input, args.sheet), lib, swing_threshold=args.swing)
    for w in rep.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for m in rep.incomplete:
        print(f"incomplete: {m}", file=sys.stderr)
    outs = [(args.markdown, lambda p: Path(p).write_text(rep.to_markdown(), encoding="utf-8")),
            (args.csv, lambda p: rep.summary.to_csv(p, index=False, float_format="%.6g")),
            (args.changes, lambda p: rep.changes.to_csv(p, index=False, float_format="%.6g"))]
    for path, write in outs:
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            write(path)
            print(f"wrote {path}")
    if args.chart:
        from sustainkit.kpis.plot import plot_kpis

        plot_kpis(rep, args.chart, kpis=args.kpi or None, site=args.site)
        print(f"wrote {args.chart}")
    cols = ["kpi_id", "site", "years", "latest", "change_text", "status", "flags"]
    print(rep.summary[cols].to_string(index=False))
    return 0


def cmd_example(args) -> int:
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(example_log_path().read_bytes())
    print(f"wrote {dest} (fictional example data)")
    return 0


def add_parser(sub) -> None:
    p = sub.add_parser("kpis", help="KPI library, multi-year E/S/G data log, year-on-year change")
    s = p.add_subparsers(dest="kpis_command", required=True)
    lib = s.add_parser("library", help="list or search the KPI library")
    lib.add_argument("text", nargs="*", help="search text (name, id, definition, ESRS/GRI code)")
    lib.add_argument("--pillar", choices=["E", "S", "G"], default=None)
    r = s.add_parser("report", help="validate a data log and report year-on-year change")
    r.add_argument("input", help="data log CSV or Excel (long: kpi_id,year,value[,site,unit]; or wide: one column per year)")
    r.add_argument("--sheet", default=None)
    r.add_argument("--swing", type=float, default=0.25, help="flag |change| above this share (default 0.25)")
    r.add_argument("--markdown", default=None)
    r.add_argument("--csv", default=None, help="write the per-KPI summary")
    r.add_argument("--changes", default=None, help="write all year-on-year changes")
    r.add_argument("--chart", default=None, help="write small-multiple bar charts (PNG)")
    r.add_argument("--kpi", action="append", default=[], help="limit the chart to these kpi_id (repeatable)")
    r.add_argument("--site", default=None)
    for q in (lib, r):
        q.add_argument("--library", default=None, help="custom KPI library CSV (default: bundled)")
        q.add_argument("--library-extra", default=None, help="extra KPI definitions appended to the library")
    lib.set_defaults(func=cmd_library)
    r.set_defaults(func=cmd_report)
    e = s.add_parser("example", help="write the fictional example data log")
    e.add_argument("dest", nargs="?", default="kpi_log.csv")
    e.set_defaults(func=cmd_example)


__all__ = ["KPILogError", "add_parser"]
