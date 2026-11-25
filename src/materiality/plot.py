"""Materiality matrix plots: static (matplotlib) and interactive (Plotly)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from materiality.scoring import SCALE_MAX, ScoringConfig
from materiality.taxonomy import PILLARS

PILLAR_COLOURS = {"E": "#2E8B57", "S": "#D9822B", "G": "#3B5BA9"}
QUADRANT_FILL = {
    "double": "#F3D9D9",
    "impact": "#F7EAD7",
    "financial": "#DCE6F2",
    "not material": "#F4F4F4",
}


def _axis_labels(method: str) -> tuple[str, str]:
    if method == "classic":
        return ("Impact on business", "Importance to stakeholders")
    return (
        "Financial materiality (outside-in) \u2192",
        "Impact materiality (inside-out) \u2192",
    )


def _short(label: str, width: int = 34) -> str:
    label = str(label)
    return label if len(label) <= width else label[: width - 1] + "\u2026"


def _repel(ax, texts, points_disp, iterations: int = 250, pad: float = 3.0):
    """Nudge text labels apart in display space (simple force-free repel)."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    for _ in range(iterations):
        moved = False
        boxes = [t.get_window_extent(renderer).expanded(1.0, 1.0) for t in texts]
        for i, bi in enumerate(boxes):
            dx = dy = 0.0
            for j, bj in enumerate(boxes):
                if i == j:
                    continue
                if bi.overlaps(bj):
                    cx = (bi.x0 + bi.x1 - bj.x0 - bj.x1) / 2
                    cy = (bi.y0 + bi.y1 - bj.y0 - bj.y1) / 2
                    dx += np.sign(cx or (i - j)) * pad
                    dy += np.sign(cy or (i - j)) * pad
            for k, (px, py) in enumerate(points_disp):
                if k != i and bi.x0 - 4 < px < bi.x1 + 4 and bi.y0 - 4 < py < bi.y1 + 4:
                    dy += pad if (bi.y0 + bi.y1) / 2 >= py else -pad
            if dx or dy:
                x, y = ax.transData.transform(texts[i].get_position())
                nx, ny = inv.transform((x + dx, y + dy))
                texts[i].set_position((nx, ny))
                moved = True
        if not moved:
            break


def plot_matrix(
    scored: pd.DataFrame,
    path: str | Path | None = None,
    title: str = "Double materiality matrix",
    subtitle: str | None = None,
    config: ScoringConfig | None = None,
    label: str = "topic",
    dpi: int = 200,
    figsize: tuple[float, float] = (11, 8.5),
    show_ranks: bool = True,
):
    """Draw a publication-quality matrix and optionally save it.

    Points are coloured by E/S/G pillar, sized by survey responses when
    available, and shaded by quadrant. Returns the matplotlib ``Figure``.
    """
    import matplotlib

    if path is not None:
        matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    cfg = config or scored.attrs.get("config") or ScoringConfig()
    method = scored.attrs.get("method", "double")
    xlab, ylab = _axis_labels(method)
    ti, tf = cfg.impact_threshold, cfg.financial_threshold

    fig, ax = plt.subplots(figsize=figsize)
    lo, hi = 0.0, SCALE_MAX + 0.15
    fills = [
        ((tf, ti), hi - tf, hi - ti, "double"),
        ((lo, ti), tf - lo, hi - ti, "impact"),
        ((tf, lo), hi - tf, ti - lo, "financial"),
        ((lo, lo), tf - lo, ti - lo, "not material"),
    ]
    for (x0, y0), w, h, q in fills:
        ax.add_patch(Rectangle((x0, y0), w, h, color=QUADRANT_FILL[q], zorder=0, lw=0))
    ax.axvline(tf, color="#888888", lw=1, ls="--", zorder=1)
    ax.axhline(ti, color="#888888", lw=1, ls="--", zorder=1)
    corner = dict(fontsize=9, color="#666666", style="italic", zorder=2)
    if method == "classic":
        names = ("High priority", "High stakeholder concern", "High business impact", "Lower priority")
    else:
        names = ("Double material", "Impact material", "Financially material", "Not material")
    ax.text(hi - 0.05, hi - 0.05, names[0], ha="right", va="top", **corner)
    ax.text(lo + 0.05, hi - 0.05, names[1], ha="left", va="top", **corner)
    ax.text(hi - 0.05, lo + 0.05, names[2], ha="right", va="bottom", **corner)
    ax.text(lo + 0.05, lo + 0.05, names[3], ha="left", va="bottom", **corner)

    x = scored["financial_score"].to_numpy(float)
    y = scored["impact_score"].to_numpy(float)
    if "n_responses" in scored.columns and scored["n_responses"].notna().any():
        n = scored["n_responses"].fillna(0).to_numpy(float)
        sizes = 60 + 240 * (n / max(n.max(), 1))
    else:
        sizes = np.full(len(scored), 120.0)
    colours = [PILLAR_COLOURS.get(str(p), "#777777") for p in scored.get("pillar", ["S"] * len(scored))]
    ax.scatter(x, y, s=sizes, c=colours, edgecolor="white", linewidth=1.2, zorder=4, alpha=0.95)

    texts = []
    for i, row in scored.reset_index(drop=True).iterrows():
        txt = _short(row[label])
        if show_ranks and "rank" in row:
            txt = f"{int(row['rank'])}. {txt}"
        right = x[i] > SCALE_MAX - 1.4
        texts.append(
            ax.text(
                x[i] + (-0.12 if right else 0.05), y[i] + 0.1, txt, fontsize=8, zorder=5,
                ha="right" if right else "left", va="bottom", color="#222222",
            )
        )
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    points_disp = ax.transData.transform(np.column_stack([x, y]))
    _repel(ax, texts, points_disp)
    for i, t in enumerate(texts):
        tx, ty = t.get_position()
        if np.hypot(tx - x[i], ty - y[i]) > 0.25:
            ax.plot([x[i], tx], [y[i], ty], color="#999999", lw=0.6, zorder=3)

    ax.set_xlabel(xlab, fontsize=11)
    ax.set_ylabel(ylab, fontsize=11)
    ax.set_xticks(range(0, 6))
    ax.set_yticks(range(0, 6))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle(title, fontsize=15, fontweight="bold", x=0.06, ha="left")
    sub = subtitle or (
        f"Scores on a 1-5 scale; thresholds impact {ti:g}, financial {tf:g}. "
        "Bubble size = survey responses." if method == "double" else
        f"Classic two-axis matrix rescaled to 1-5; threshold {ti:g}."
    )
    ax.set_title(sub, fontsize=9, color="#555555", loc="left")

    from matplotlib.lines import Line2D

    present = [p for p in ("E", "S", "G") if p in set(scored.get("pillar", []))]
    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PILLAR_COLOURS[p], markersize=10, label=PILLARS[p])
        for p in present
    ]
    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, title="Pillar")
    fig.tight_layout()
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return fig


def plot_interactive(
    scored: pd.DataFrame,
    path: str | Path | None = None,
    title: str = "Double materiality matrix",
    config: ScoringConfig | None = None,
):
    """Interactive Plotly matrix with hover details. Needs ``pip install materiality-matrix[interactive]``."""
    try:
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover
        raise ImportError("plotly is required: pip install 'materiality-matrix[interactive]'") from exc

    cfg = config or scored.attrs.get("config") or ScoringConfig()
    method = scored.attrs.get("method", "double")
    xlab, ylab = _axis_labels(method)
    ti, tf = cfg.impact_threshold, cfg.financial_threshold
    hi = SCALE_MAX + 0.15
    fig = go.Figure()
    for q, (x0, x1, y0, y1) in {
        "double": (tf, hi, ti, hi),
        "impact": (0, tf, ti, hi),
        "financial": (tf, hi, 0, ti),
        "not material": (0, tf, 0, ti),
    }.items():
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=QUADRANT_FILL[q], line_width=0, layer="below")
    fig.add_shape(type="line", x0=tf, x1=tf, y0=0, y1=hi, line=dict(color="#888", dash="dash", width=1))
    fig.add_shape(type="line", x0=0, x1=hi, y0=ti, y1=ti, line=dict(color="#888", dash="dash", width=1))

    pillars = scored["pillar"] if "pillar" in scored.columns else pd.Series(["S"] * len(scored))
    for p in ("E", "S", "G"):
        sub = scored[pillars.values == p]
        if sub.empty:
            continue
        hover = []
        for _, r in sub.iterrows():
            parts = [f"<b>{r['topic']}</b>"]
            if "esrs" in r and pd.notna(r.get("esrs")):
                parts.append(f"ESRS {r['esrs']}")
            parts.append(f"Impact: {r['impact_score']:.2f}")
            parts.append(f"Financial: {r['financial_score']:.2f}")
            parts.append(f"Quadrant: {r['quadrant']}")
            if "n_responses" in r and pd.notna(r.get("n_responses")):
                parts.append(f"Survey responses: {int(r['n_responses'])}")
            if "description" in r and pd.notna(r.get("description")):
                parts.append(str(r["description"]))
            hover.append("<br>".join(parts))
        fig.add_trace(
            go.Scatter(
                x=sub["financial_score"],
                y=sub["impact_score"],
                mode="markers+text",
                name=PILLARS[p],
                text=[_short(t, 22) for t in sub["topic"]],
                textposition="top center",
                textfont=dict(size=10),
                marker=dict(size=14, color=PILLAR_COLOURS[p], line=dict(color="white", width=1)),
                hovertext=hover,
                hoverinfo="text",
            )
        )
    fig.update_layout(
        title=title,
        xaxis=dict(title=xlab, range=[0, hi], dtick=1),
        yaxis=dict(title=ylab, range=[0, hi], dtick=1),
        template="simple_white",
        width=950,
        height=760,
        legend_title_text="Pillar",
    )
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(path, include_plotlyjs="cdn")
    return fig
