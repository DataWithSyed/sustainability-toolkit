"""Influence x interest map (matplotlib)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from sustainkit.stakeholders.register import StakeholderMap

CAT_COLOURS = {"affected": "#d1495b", "user": "#00798c", "both": "#edae49", None: "#7a7a7a"}
QUAD_POS = {"Manage closely": (1, 1), "Keep satisfied": (0, 1), "Keep informed": (1, 0), "Monitor": (0, 0)}


def _spread(points: np.ndarray, radius: float = 0.16) -> np.ndarray:
    """Deterministic offsets so stakeholders with identical ratings do not overlap."""
    out = points.astype(float).copy()
    seen: dict[tuple, int] = {}
    for i, p in enumerate(map(tuple, points)):
        k = seen.get(p, 0)
        seen[p] = k + 1
        if k:
            ang = 2.4 * k  # golden-angle-ish spiral
            r = radius * np.sqrt(k)
            out[i] += [r * np.cos(ang), r * np.sin(ang)]
    return out


def plot_map(smap: StakeholderMap, path: str | Path | None = None, title: str | None = None, label: bool = True):
    t = smap.table
    s, cut = smap.config.scale, smap.config.cut
    # With integer ratings and an integer cut-off (rating >= cut is "high"), draw the boundary half a
    # step below the cut so a rating equal to the cut sits visibly inside the "high" zone.
    ints = bool(((t[["influence", "interest"]] % 1) == 0).all().all())
    line = cut - 0.5 if ints and float(cut).is_integer() else cut
    fig, ax = plt.subplots(figsize=(8.5, 7))
    lo, hi = 0.5, s + 0.5
    shades = {"Manage closely": "#f6d6d9", "Keep satisfied": "#fbeed3", "Keep informed": "#d6ecef", "Monitor": "#eeeeee"}
    for name, (qx, qy) in QUAD_POS.items():
        x0, x1 = (line, hi) if qx else (lo, line)
        y0, y1 = (line, hi) if qy else (lo, line)
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color=shades[name], zorder=0, lw=0))
        n = int((t["strategy"] == name).sum())
        ax.text(x0 + 0.06, y1 - 0.08, f"{name} ({n})", ha="left", va="top", fontsize=10, weight="bold", color="#444")
    pts = _spread(t[["interest", "influence"]].to_numpy())
    for cat in ["affected", "user", "both", None]:
        m = (t["category"].isna() if cat is None else (t["category"] == cat)).to_numpy()
        if m.any():
            lab = {"affected": "affected stakeholders", "user": "users of sustainability statements",
                   "both": "both (ESRS 1 para 23)", None: "category not set"}[cat]
            ax.scatter(pts[m, 0], pts[m, 1], s=40 + 12 * t.loc[m, "salience"], c=CAT_COLOURS[cat], edgecolor="k",
                       lw=0.6, zorder=3, label=lab, alpha=0.9)
    if label:
        for (x, y), name in zip(pts, t["stakeholder"]):
            ax.annotate(name, (x, y), xytext=(6, 4), textcoords="offset points", fontsize=7.5, zorder=4)
    ax.axvline(line, color="#888", lw=1, ls="--")
    ax.axhline(line, color="#888", lw=1, ls="--")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xticks(range(1, s + 1))
    ax.set_yticks(range(1, s + 1))
    ax.set_xlabel("Interest in the undertaking's sustainability matters")
    ax.set_ylabel("Influence on the undertaking")
    ax.set_title(title or "Stakeholder map (influence x interest)")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
        plt.close(fig)
    return fig
