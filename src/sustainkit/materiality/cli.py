"""Command-line interface: ``materiality build|validate|classic|example|template``."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from sustainkit.materiality import __version__
from sustainkit.materiality.io import example_path, load, load_classic_matrix
from sustainkit.materiality.report import to_markdown, write_outputs
from sustainkit.materiality.schema import ValidationError
from sustainkit.materiality.scoring import ScoringConfig, score, score_classic


def _add_scoring_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--impact-threshold", type=float, default=3.0)
    p.add_argument("--financial-threshold", type=float, default=3.0)
    p.add_argument("--survey-blend", type=float, default=None, help="share of survey in both scores (0-1)")
    p.add_argument("--survey-blend-impact", type=float, default=0.3)
    p.add_argument("--survey-blend-financial", type=float, default=0.3)
    p.add_argument("--aggregation", choices=["mean", "median"], default="mean")
    p.add_argument("--rating-scale", type=int, default=5, help="max of survey rating scale (e.g. 5 or 10)")
    p.add_argument(
        "--weight", action="append", default=[], metavar="GROUP=W",
        help="override a stakeholder group weight, repeatable",
    )


def _add_output_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", "-o", type=Path, help="static matrix image (.png, .svg, .pdf)")
    p.add_argument("--html", type=Path, help="interactive Plotly HTML")
    p.add_argument("--csv", type=Path, help="scored topic table as CSV")
    p.add_argument("--markdown", type=Path, help="Markdown summary")
    p.add_argument("--title", default=None)


def _config(args) -> ScoringConfig:
    weights = {}
    for item in args.weight:
        if "=" not in item:
            raise SystemExit(f"--weight expects GROUP=W, got {item!r}")
        g, w = item.split("=", 1)
        weights[g.strip()] = float(w)
    bi = args.survey_blend if args.survey_blend is not None else args.survey_blend_impact
    bf = args.survey_blend if args.survey_blend is not None else args.survey_blend_financial
    return ScoringConfig(
        impact_threshold=args.impact_threshold,
        financial_threshold=args.financial_threshold,
        survey_blend_impact=bi,
        survey_blend_financial=bf,
        group_weights=weights,
        aggregation=args.aggregation,
    )


def _emit(scored, args, default_title: str) -> None:
    title = args.title or default_title
    if args.out:
        from sustainkit.materiality.plot import plot_matrix

        plot_matrix(scored, args.out, title=title)
        print(f"wrote {args.out}")
    if args.html:
        from sustainkit.materiality.plot import plot_interactive

        plot_interactive(scored, args.html, title=title)
        print(f"wrote {args.html}")
    write_outputs(scored, csv=args.csv, markdown=args.markdown, title=title)
    for p in (args.csv, args.markdown):
        if p:
            print(f"wrote {p}")
    if not any((args.out, args.html, args.csv, args.markdown)):
        sys.stdout.write(to_markdown(scored, title))


def cmd_build(args) -> int:
    data = load(args.input, rating_scale=args.rating_scale)
    for w in data.warnings:
        print(f"warning: {w}", file=sys.stderr)
    scored = score(data, _config(args))
    _emit(scored, args, "Double materiality matrix")
    return 0


def cmd_validate(args) -> int:
    data = load(args.input, rating_scale=args.rating_scale)
    n_s = 0 if data.survey is None else len(data.survey)
    print(f"OK: {len(data.topics)} topics, {n_s} survey answers")
    for w in data.warnings:
        print(f"warning: {w}")
    return 0


def cmd_classic(args) -> int:
    classic = load_classic_matrix(args.input, sheet=args.sheet, scale_max=args.scale_max)
    scored = score_classic(classic, threshold=args.threshold)
    _emit(scored, args, "Materiality matrix")
    return 0


def cmd_example(args) -> int:
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example_path(), dest)
    print(f"wrote {dest} (fictional example data)")
    return 0


def cmd_template(args) -> int:
    import pandas as pd

    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    topics = pd.DataFrame(
        columns=[
            "topic_id", "topic", "esrs", "subtopic", "impact_type", "scale", "scope",
            "irremediability", "impact_likelihood", "human_rights", "fin_magnitude",
            "fin_likelihood", "time_horizon", "value_chain", "description",
        ]
    )
    survey = pd.DataFrame(columns=["respondent_id", "stakeholder_group", "topic_id", "impact_rating", "financial_rating"])
    weights = pd.DataFrame(columns=["stakeholder_group", "weight"])
    with pd.ExcelWriter(dest) as xw:
        topics.to_excel(xw, sheet_name="topics", index=False)
        survey.to_excel(xw, sheet_name="survey", index=False)
        weights.to_excel(xw, sheet_name="weights", index=False)
    print(f"wrote empty template {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="materiality", description="Double materiality matrices from Excel/CSV (sustainkit.materiality).")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="score an assessment and draw the matrix")
    b.add_argument("input", type=Path, help=".xlsx workbook, folder of CSVs, or topics.csv")
    _add_scoring_args(b)
    _add_output_args(b)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate", help="check an input file against the schema")
    v.add_argument("input", type=Path)
    v.add_argument("--rating-scale", type=int, default=5)
    v.set_defaults(func=cmd_validate)

    c = sub.add_parser("classic", help="plot a classic stakeholder-vs-business matrix sheet")
    c.add_argument("input", type=Path)
    c.add_argument("--sheet", default=None)
    c.add_argument("--scale-max", type=float, default=None)
    c.add_argument("--threshold", type=float, default=3.0)
    _add_output_args(c)
    c.set_defaults(func=cmd_classic)

    e = sub.add_parser("example", help="copy the fictional example workbook")
    e.add_argument("dest", nargs="?", default="example_assessment.xlsx")
    e.set_defaults(func=cmd_example)

    t = sub.add_parser("template", help="write an empty input workbook")
    t.add_argument("dest", nargs="?", default="materiality_template.xlsx")
    t.set_defaults(func=cmd_template)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
