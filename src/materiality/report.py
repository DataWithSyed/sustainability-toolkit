"""Plain-text exports of a scored assessment."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPORT_COLUMNS = [
    "rank", "topic_id", "topic", "esrs", "pillar", "impact_score", "financial_score",
    "quadrant", "material", "severity", "impact_likelihood_used", "impact_assessed",
    "financial_assessed", "survey_impact", "survey_financial", "n_responses", "n_groups",
    "group_spread",
]


def export_table(scored: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in EXPORT_COLUMNS if c in scored.columns]
    return scored[cols].copy()


def to_markdown(scored: pd.DataFrame, title: str = "Materiality assessment") -> str:
    """A short Markdown summary: counts per quadrant and the ranked topic table."""
    cfg = scored.attrs.get("config")
    lines = [f"# {title}", ""]
    if cfg is not None:
        lines.append(
            f"Thresholds: impact {cfg.impact_threshold:g}, financial {cfg.financial_threshold:g} (1-5 scale)."
        )
        lines.append("")
    counts = scored["quadrant"].value_counts()
    for q in ("double", "impact", "financial", "not material"):
        lines.append(f"- **{q}**: {int(counts.get(q, 0))}")
    lines += ["", "| # | Topic | ESRS | Impact | Financial | Quadrant |", "|---|---|---|---|---|---|"]
    for _, r in scored.iterrows():
        esrs = r.get("esrs", "") if pd.notna(r.get("esrs", "")) else ""
        lines.append(
            f"| {int(r['rank'])} | {r['topic']} | {esrs} | {r['impact_score']:.2f} | "
            f"{r['financial_score']:.2f} | {r['quadrant']} |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(scored: pd.DataFrame, csv: str | Path | None = None, markdown: str | Path | None = None, title: str = "Materiality assessment"):
    if csv:
        Path(csv).parent.mkdir(parents=True, exist_ok=True)
        export_table(scored).to_csv(csv, index=False, float_format="%.4f")
    if markdown:
        Path(markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown).write_text(to_markdown(scored, title), encoding="utf-8")
