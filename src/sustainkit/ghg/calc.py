"""Scope 1 and Scope 2 inventory calculation.

Method (GHG Protocol Corporate Standard, revised edition, 2004; Scope 2
Guidance, 2015): emissions = activity data x emission factor, summed by
scope. Scope 2 is reported **location-based** (grid-average factor from the
factor table) and, where the user supplies a contractual factor per row,
**market-based**. No residual-mix factor is bundled, so market-based totals
are only reported as complete when every Scope 2 row has a factor.
Biogenic CO2 from bioenergy is reported separately ("outside of scopes"),
as the UK conversion factors and the GHG Protocol require.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from sustainkit.ghg.factors import FactorError, FactorSet, load_factors

REQUIRED = ("activity", "quantity", "unit")
OPTIONAL = ("id", "site", "period", "level1", "level2", "level4", "variant", "scope", "market_factor", "note")


class InventoryError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("Invalid activity data:\n" + "\n".join(f"  - {p}" for p in problems))


@dataclass
class Inventory:
    """Result of :func:`calculate`: one row per activity plus summaries (tonnes CO2e)."""

    rows: pd.DataFrame
    factor_set: str
    warnings: list[str] = field(default_factory=list)

    @property
    def scope1_t(self) -> float:
        return float(self.rows.loc[self.rows["scope"] == "Scope 1", "kg_co2e"].sum()) / 1000

    @property
    def scope2_location_t(self) -> float:
        return float(self.rows.loc[self.rows["scope"] == "Scope 2", "kg_co2e"].sum()) / 1000

    @property
    def scope2_market_t(self) -> float | None:
        s2 = self.rows[self.rows["scope"] == "Scope 2"]
        if s2.empty:
            return 0.0
        if s2["market_kg_co2e"].isna().any():
            return None
        return float(s2["market_kg_co2e"].sum()) / 1000

    @property
    def biogenic_t(self) -> float:
        return float(self.rows["biogenic_kg_co2"].fillna(0).sum()) / 1000

    def summary(self) -> pd.DataFrame:
        s2m = self.scope2_market_t
        rows = [
            ("Scope 1", self.scope1_t),
            ("Scope 2 (location-based)", self.scope2_location_t),
            ("Scope 2 (market-based)", np.nan if s2m is None else s2m),
            ("Scope 1 + 2 (location-based)", self.scope1_t + self.scope2_location_t),
            ("Biogenic CO2 (outside of scopes)", self.biogenic_t),
        ]
        return pd.DataFrame(rows, columns=["item", "t_co2e"])

    def by(self, column: str) -> pd.DataFrame:
        """Tonnes CO2e by scope and another column (e.g. ``site``, ``period``, ``level1``)."""
        if column not in self.rows.columns:
            raise KeyError(column)
        g = self.rows.groupby([column, "scope"], dropna=False)["kg_co2e"].sum().unstack(fill_value=0.0) / 1000
        g["total"] = g.sum(axis=1)
        return g.sort_values("total", ascending=False)

    def gases(self) -> pd.DataFrame:
        """Tonnes CO2e by gas (CO2, CH4, N2O) and scope, where the factor table splits them."""
        cols = ["kg_co2", "kg_ch4_co2e", "kg_n2o_co2e"]
        g = self.rows.groupby("scope")[cols].sum(min_count=1) / 1000
        return g.rename(columns={"kg_co2": "CO2", "kg_ch4_co2e": "CH4", "kg_n2o_co2e": "N2O"})

    def to_markdown(self, title: str = "GHG inventory (Scope 1 and 2)") -> str:
        lines = [f"# {title}", "", f"Factors: {self.factor_set}.", "", "| Item | t CO2e |", "|---|---|"]
        for _, r in self.summary().iterrows():
            v = "incomplete (market factor missing)" if pd.isna(r["t_co2e"]) else f"{r['t_co2e']:,.2f}"
            lines.append(f"| {r['item']} | {v} |")
        lines += ["", "| Activity | Quantity | Unit | Scope | Factor (kg CO2e/unit) | t CO2e |", "|---|---|---|---|---|---|"]
        for _, r in self.rows.iterrows():
            lines.append(
                f"| {r['activity']} | {r['quantity']:,.2f} | {r['unit']} | {r['scope']} | "
                f"{r['factor_kg_co2e']:.5g} | {r['kg_co2e'] / 1000:,.3f} |"
            )
        if self.warnings:
            lines += ["", "Warnings:", *[f"- {w}" for w in self.warnings]]
        return "\n".join(lines) + "\n"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out.dropna(how="all").reset_index(drop=True)


def calculate(activities: pd.DataFrame, factors: FactorSet | None = None) -> Inventory:
    """Compute a Scope 1 + 2 inventory from an activity table.

    Required columns: ``activity`` (factor name, e.g. ``Natural gas``,
    ``Electricity: UK``, ``Small car``, ``R410A``, or a ``factor_id``),
    ``quantity`` (>= 0) and ``unit`` (e.g. ``kWh (Gross CV)``, ``litres``,
    ``km``, ``kg``; ``MWh``/``GWh`` and ``kg``->``tonnes`` are converted).
    Optional: ``level1``, ``level2``, ``level4``, ``variant`` to disambiguate;
    ``site``, ``period``, ``id``, ``note`` for grouping; ``market_factor``
    (kg CO2e/kWh from contractual instruments) for market-based Scope 2.
    All problems are collected and raised together as :class:`InventoryError`.
    """
    fs = factors or load_factors()
    a = _clean(activities)
    problems: list[str] = []
    warnings: list[str] = []
    missing = [c for c in REQUIRED if c not in a.columns]
    if missing:
        raise InventoryError([f"missing required column(s) {missing}"])
    if a.empty:
        raise InventoryError(["no activity rows"])
    qty = pd.to_numeric(a["quantity"], errors="coerce")
    for col in OPTIONAL:
        if col not in a.columns:
            a[col] = np.nan if col == "market_factor" else ""
    a[["site", "period", "level1", "level2", "level4", "variant", "scope", "id", "note"]] = (
        a[["site", "period", "level1", "level2", "level4", "variant", "scope", "id", "note"]].fillna("").astype(str)
    )
    mf = pd.to_numeric(a["market_factor"], errors="coerce")

    out = []
    for i, r in a.iterrows():
        rown = i + 2
        if pd.isna(qty[i]):
            problems.append(f"row {rown}: quantity {r['quantity']!r} is not a number")
            continue
        if qty[i] < 0:
            problems.append(f"row {rown}: quantity must be >= 0")
            continue
        if pd.notna(r["market_factor"]) and str(r["market_factor"]).strip() != "" and (pd.isna(mf[i]) or mf[i] < 0):
            problems.append(f"row {rown}: market_factor must be a number >= 0")
            continue
        try:
            f, mult = fs.lookup(r["activity"], r["unit"], r["level1"], r["level2"], r["level4"], r["variant"], r["scope"])
        except FactorError as exc:
            problems.append(f"row {rown}: {exc}")
            continue
        q = float(qty[i]) * mult
        rec = {
            "id": r["id"], "site": r["site"], "period": r["period"], "activity": r["activity"],
            "quantity": float(qty[i]), "unit": r["unit"], "factor_unit": f["unit"], "quantity_in_factor_unit": q,
            "scope": f["scope"], "level1": f["level1"], "level2": f["level2"], "level3": f["level3"],
            "level4": f["level4"], "variant": f["variant"], "factor_id": f["factor_id"],
            "factor_kg_co2e": f["kg_co2e"], "kg_co2e": q * f["kg_co2e"],
        }
        for g in ("kg_co2", "kg_ch4_co2e", "kg_n2o_co2e"):
            rec[g] = q * f[g] if pd.notna(f[g]) else np.nan
        bio = fs.biogenic(f["level3"], f["unit"])
        rec["biogenic_kg_co2"] = q * bio if bio is not None and f["scope"] == "Scope 1" else np.nan
        if f["scope"] == "Scope 2":
            is_kwh = str(f["unit"]).lower().startswith("kwh")
            if pd.notna(mf[i]) and is_kwh:
                rec["market_kg_co2e"] = q * float(mf[i])
            else:
                rec["market_kg_co2e"] = np.nan
                warnings.append(f"row {rown}: no market_factor for Scope 2 '{r['activity']}'; market-based total incomplete")
        else:
            rec["market_kg_co2e"] = np.nan
            if pd.notna(mf[i]):
                warnings.append(f"row {rown}: market_factor ignored for {f['scope']} activity")
        rec["note"] = r["note"]
        out.append(rec)
    if problems:
        raise InventoryError(problems)
    return Inventory(pd.DataFrame(out), fs.name, warnings)


def load_activities(path: str | Path, sheet: str | int | None = None) -> pd.DataFrame:
    """Read an activity table from CSV or Excel (sheet ``activities`` if present)."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    xls = pd.ExcelFile(path)
    if sheet is None:
        names = {n.lower(): n for n in xls.sheet_names}
        sheet = names.get("activities", xls.sheet_names[0])
    return xls.parse(sheet)
