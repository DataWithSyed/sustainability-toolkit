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


COMPONENT_COLOURS = {"activity": "#7D3C98", "WTT": "#E67E22", "T&D losses": "#16A085", "WTT of T&D losses": "#F4D03F"}


def plot_scope123(result, inventory=None, path: str | Path | None = None, title: str = "Scope 1, 2 and 3 emissions", dpi: int = 200):
    """Stacked bars: Scope 1, Scope 2 (location-based) and each Scope 3 category split by component."""
    import matplotlib

    if path is not None:
        matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    cat = result.by_category()
    labels, parts = [], []
    if inventory is not None:
        labels += ["Scope 1", "Scope 2 (location-based)"]
        parts += [{"Scope 1": inventory.scope1_t}, {"Scope 2": inventory.scope2_location_t}]
    for name, row in cat.iterrows():
        labels.append("Scope 3 " + name)
        parts.append({k: row[k] for k in COMPONENT_COLOURS if k in row.index and row[k] > 0})
    labels, parts = labels[::-1], parts[::-1]
    fig, ax = plt.subplots(figsize=(10, max(3.0, 0.55 * len(labels) + 1.6)))
    left = np.zeros(len(labels))
    keys = ["Scope 1", "Scope 2", *COMPONENT_COLOURS]
    colours = {**SCOPE_COLOURS, **COMPONENT_COLOURS}
    names = {"activity": "Scope 3: activity", "WTT": "Scope 3: well-to-tank", "T&D losses": "Scope 3: T&D losses",
             "WTT of T&D losses": "Scope 3: WTT of T&D losses", "Scope 2": "Scope 2 (location-based)"}
    for k in keys:
        vals = np.array([p.get(k, 0.0) for p in parts])
        if vals.sum() <= 0:
            continue
        ax.barh(labels, vals, left=left, color=colours[k], label=names.get(k, k))
        left += vals
    for y, v in enumerate(left):
        ax.text(v, y, f"  {v:,.1f}", va="center", fontsize=8)
    ax.set_xlabel("t CO2e")
    ax.set_xlim(0, max(left.max() * 1.18, 1e-9))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=3, fontsize=8)
    total3 = result.total_t()
    sub = f"Scope 3 (categories reported) {total3:,.1f} t CO2e"
    if inventory is not None:
        sub = f"Scope 1 + 2 (location-based) {inventory.scope1_t + inventory.scope2_location_t:,.1f} t; " + sub
    if result.rows["rf_memo_kg_co2e"].notna().any():
        sub += f".\nMemo: flights with radiative forcing {result.rf_memo_t:,.1f} t (not in totals)"
    fig.suptitle(title, fontsize=14, fontweight="bold", x=0.02, ha="left")
    ax.set_title(sub + ". Factors: UK Gov GHG Conversion Factors 2025", fontsize=8, loc="left", color="#555")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return fig
