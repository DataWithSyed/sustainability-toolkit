"""Emission factor tables.

The bundled table is the Scope 1, Scope 2 and "outside of scopes" part of
the **UK Government GHG Conversion Factors for Company Reporting 2025**
(flat file, version 1; DESNZ, produced by Ricardo Energy & Environment and
Aether Ltd), published under the Open Government Licence v3.0:
https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025

Values are copied unchanged (kg CO2e per unit, with the CO2 / CH4 / N2O
split where published). Rebuild with ``examples/build_uk_ghg_factors.py``.
Most 2025 factors use IPCC AR5 GWP100 values; see Table 1 of the 2025
methodology paper for the exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import pandas as pd

UK_2025 = "uk_gov_ghg_2025_scope12.csv"
TEXT_COLS = ["factor_id", "scope", "level1", "level2", "level3", "level4", "variant", "unit"]
VALUE_COLS = ["kg_co2e", "kg_co2", "kg_ch4_co2e", "kg_n2o_co2e"]

UNIT_ALIASES = {
    "m3": "cubic metres", "m^3": "cubic metres", "cubic meter": "cubic metres", "cubic meters": "cubic metres",
    "cubic metre": "cubic metres", "l": "litres", "litre": "litres", "liter": "litres", "liters": "litres",
    "t": "tonnes", "tonne": "tonnes", "ton": "tonnes", "tons": "tonnes", "kilogram": "kg", "kgs": "kg",
    "mile": "miles", "kilometre": "km", "kilometres": "km", "tkm": "tonne.km",
}


class FactorError(LookupError):
    """No unique emission factor matches an activity."""


def _norm(s) -> str:
    return " ".join(str(s).strip().lower().split()) if pd.notna(s) else ""


@dataclass
class FactorSet:
    """A table of emission factors with lookup helpers."""

    table: pd.DataFrame
    name: str = "custom"

    def __post_init__(self):
        t = self.table.copy()
        missing = [c for c in TEXT_COLS + ["kg_co2e"] if c not in t.columns]
        if missing:
            raise ValueError(f"factor table missing columns {missing}")
        for c in TEXT_COLS:
            t[c] = t[c].fillna("").astype(str)
        for c in VALUE_COLS:
            if c not in t.columns:
                t[c] = float("nan")
            t[c] = pd.to_numeric(t[c], errors="coerce")
        t["_l3"] = t["level3"].map(_norm)
        t["_unit"] = t["unit"].map(_norm)
        self.table = t

    # -- discovery -----------------------------------------------------------
    def search(self, text: str = "", scope: str | None = None, unit: str | None = None) -> pd.DataFrame:
        """Case-insensitive search over all category levels and the variant."""
        t = self.table
        hay = (t["level1"] + " " + t["level2"] + " " + t["level3"] + " " + t["level4"] + " " + t["variant"]).str.lower()
        m = pd.Series(True, index=t.index)
        for word in _norm(text).split():
            m &= hay.str.contains(word, regex=False)
        if scope:
            m &= t["scope"].str.lower() == _norm(scope)
        if unit:
            m &= t["_unit"] == _norm(unit)
        return t.loc[m, TEXT_COLS + VALUE_COLS]

    # -- lookup --------------------------------------------------------------
    def _candidates(self, activity, level1="", level2="", level4="", variant="", scope=""):
        t = self.table
        a = _norm(activity)
        m = (t["_l3"] == a) | (t["factor_id"].str.lower() == a)
        if not m.any():
            raise FactorError(f"no factor for activity {activity!r}; try FactorSet.search({activity!r})")
        for col, val in (("level1", level1), ("level2", level2), ("level4", level4), ("variant", variant)):
            if _norm(val):
                m &= t[col].map(_norm) == _norm(val)
        if _norm(scope):
            m &= t["scope"].str.lower() == _norm(scope)
        else:
            m &= t["scope"].isin(["Scope 1", "Scope 2"])
        return t[m]

    def resolve_unit(self, cands: pd.DataFrame, unit: str) -> tuple[pd.DataFrame, float]:
        """Return rows matching ``unit`` and a multiplier for the quantity."""
        u = _norm(unit)
        u = UNIT_ALIASES.get(u, u)
        exact = cands[cands["_unit"] == u]
        if len(exact):
            return exact, 1.0
        # MWh / GWh -> kWh, keeping any "(gross cv)" / "(net cv)" qualifier
        for big, (small, mult) in (("mwh", ("kwh", 1e3)), ("gwh", ("kwh", 1e6))):
            if u.startswith(big):
                target = small + u[len(big):]
                hit = cands[cands["_unit"] == target]
                if len(hit):
                    return hit, mult
        if u == "kg":
            hit = cands[cands["_unit"] == "tonnes"]
            if len(hit):
                return hit, 0.001
        # plain "kwh" against gross/net factors is ambiguous unless only one exists
        if u == "kwh":
            hit = cands[cands["_unit"].str.startswith("kwh")]
            if len(hit["_unit"].unique()) == 1:
                return hit, 1.0
            if len(hit):
                raise FactorError(
                    f"unit 'kWh' is ambiguous here; use one of {sorted(hit['unit'].unique())}"
                )
        raise FactorError(f"unit {unit!r} not available; options: {sorted(cands['unit'].unique())}")

    def lookup(self, activity: str, unit: str, level1="", level2="", level4="", variant="", scope="") -> tuple[pd.Series, float]:
        """Find exactly one factor; returns ``(row, quantity multiplier)``."""
        cands = self._candidates(activity, level1, level2, level4, variant, scope)
        if cands.empty:
            raise FactorError(f"no factor for {activity!r} with the given filters")
        rows, mult = self.resolve_unit(cands, unit)
        if len(rows) > 1:
            opts = rows[["level1", "level2", "level4", "variant"]].drop_duplicates().to_dict("records")
            raise FactorError(
                f"{len(rows)} factors match {activity!r} in {unit!r}; add level1/level2/level4/variant. Options: {opts[:8]}"
            )
        return rows.iloc[0], mult

    def biogenic(self, activity: str, unit: str) -> float | None:
        """Outside-of-scopes (biogenic) CO2 per unit for the same fuel and unit, if published."""
        t = self.table
        u = UNIT_ALIASES.get(_norm(unit), _norm(unit))
        m = (t["scope"] == "Outside of scopes") & (t["_l3"] == _norm(activity)) & (t["_unit"] == u)
        if not m.any():
            return None
        return float(t.loc[m, "kg_co2"].iloc[0])


def load_factors(path: str | Path | None = None) -> FactorSet:
    """Load the bundled UK 2025 table, or a custom CSV with the same columns."""
    if path is None:
        p = resources.files("sustainkit.ghg") / "data" / UK_2025
        with resources.as_file(p) as fp:
            df = pd.read_csv(fp, keep_default_na=False, na_values=[""])
        return FactorSet(df, name="UK Government GHG Conversion Factors 2025 v1")
    df = pd.read_csv(path, keep_default_na=False, na_values=[""])
    return FactorSet(df, name=str(path))
