"""Charts for GHG inventories."""

from __future__ import annotations

from pathlib import Path

import numpy as np

SCOPE_COLOURS = {"Scope 1": "#C0392B", "Scope 2": "#2E86C1"}


def plot_breakdown(inv, path: str | Path | None = None, by: str = "level2", title: str = "Scope 1 and 2 emissions", dpi: int = 200):
    """Horizontal stacked bar chart of t CO2e by ``by`` (category, site, period...) and scope."""
    import matplotlib

    if path is not None:
        matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    table = inv.by(by).sort_values("total")
    scopes = [c for c in ("Scope 1", "Scope 2") if c in table.columns]
    fig, ax = plt.subplots(figsize=(10, max(3.0, 0.45 * len(table) + 1.5)))
    left = np.zeros(len(table))
    labels = [str(i) if str(i) else "(blank)" for i in table.index]
    for s in scopes:
        ax.barh(labels, table[s], left=left, color=SCOPE_COLOURS[s], label=s + (" (location-based)" if s == "Scope 2" else ""))
        left += table[s].to_numpy()
    for y, v in enumerate(table["total"]):
        ax.text(v, y, f"  {v:,.1f}", va="center", fontsize=8)
    ax.set_xlabel("t CO2e")
    ax.set_xlim(0, max(left.max() * 1.15, 1e-9))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    total = inv.scope1_t + inv.scope2_location_t
    fig.suptitle(title, fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title(f"Total {total:,.1f} t CO2e (Scope 1 + location-based Scope 2). Factors: {inv.factor_set}", fontsize=8, loc="left", color="#555")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return fig
