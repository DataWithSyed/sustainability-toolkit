"""Small-multiple bar charts of KPIs by year with the change vs the prior year."""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt

from sustainkit.kpis.datalog import KPIReport

COLORS = {"improved": "#2e7d32", "worsened": "#c62828", "no change": "#616161", "up": "#455a64",
          "down": "#455a64", "n/a": "#9e9e9e"}
PILLAR_COLORS = {"E": "#4f8f6b", "S": "#4f6f9f", "G": "#8f6f4f"}


def plot_kpis(report: KPIReport, path: str | Path, kpis: list[str] | None = None, site: str | None = None,
              ncols: int = 4, title: str | None = None) -> Path:
    s = report.summary
    site = site or ("All sites" if "All sites" in set(s["site"]) else s["site"].iloc[0])
    s = s[s["site"] == site]
    if kpis:
        s = s[s["kpi_id"].isin(kpis)]
    n = len(s)
    if n == 0:
        raise ValueError("nothing to plot")
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.2 * ncols, 2.5 * nrows), squeeze=False)
    years = report.years
    ch = report.changes
    for ax, (_, r) in zip(axes.flat, s.iterrows()):
        v = report.values[(report.values["kpi_id"] == r["kpi_id"]) & (report.values["site"] == site)]
        vals = dict(zip(v["year"], v["value"]))
        xs = [y for y in years if y in vals]
        cats = [str(y) for y in range(min(xs), max(xs) + 1)]  # gap years keep their slot on the axis
        ax.bar(cats, [vals.get(int(y), 0.0) for y in cats], color=PILLAR_COLORS.get(r["pillar"], "#777"),
               hatch="//" if r["derived"] else None, edgecolor="white")
        for y in cats:
            if int(y) not in vals:
                ax.text(y, 0, "gap", ha="center", va="bottom", fontsize=8, color="#c62828")
        top = max([abs(vals[y]) for y in xs] + [0.0])
        if top == 0:
            ax.set_ylim(0, 1)
        c = ch[(ch["kpi_id"] == r["kpi_id"]) & (ch["site"] == site)] if len(ch) else ch
        for _, cr in c.iterrows():
            lab = f"{cr['pp_change']:+.1f} pp" if not math.isnan(cr["pp_change"]) else (
                f"{cr['pct_change']:+.0%}" if not math.isnan(cr["pct_change"]) else "")
            ax.annotate(lab + (" !" if cr["flag"] else ""), (str(cr["year"]), cr["value"]), ha="center", va="bottom",
                        fontsize=7, color=COLORS.get(cr["status"], "#333"), xytext=(0, 2), textcoords="offset points")
        ax.set_title("\n".join(textwrap.wrap(r["name"], 38)[:2]) + f" [{r['unit']}]", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.margins(y=0.18)
        ax.grid(axis="y", alpha=0.3)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(title or f"KPI data log - {site} (green = improved, red = worsened, ! = check data, hatched = derived)",
                 fontsize=9)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
