"""Scope 3 categories 3, 6 and 7: fuel- and energy-related activities, business travel, employee commuting.

Method
------
GHG Protocol *Corporate Value Chain (Scope 3) Accounting and Reporting
Standard* (WRI/WBCSD, 2011) and *Technical Guidance for Calculating Scope 3
Emissions* v1.0 (2013), distance-based / average-data methods:
emissions = activity x factor, with factors from the UK Government GHG
Conversion Factors for Company Reporting 2025 (flat file v1, OGL v3.0).

* **Category 6, business travel**: flights (passenger.km), land travel
  (car km per vehicle, or passenger.km for rail/bus/taxi), ferries and, as the
  Scope 3 Standard allows optionally, hotel nights. The well-to-tank (WTT)
  factor of the same mode is added as a separate component, and for battery
  and plug-in electric cars the UK "T&D for EVs" factor too.
* **Category 7, employee commuting**: same factors, from trip rows or from a
  commuting survey (employees x one-way km x 2 x office days). Homeworking
  (teleworking), optional in the Technical Guidance, uses the UK
  "Homeworking" factor per full-time-equivalent working hour.
* **Category 3, fuel- and energy-related activities** (not in Scope 1 or 2),
  derived from a Scope 1-2 :class:`~sustainkit.ghg.calc.Inventory`:
  (a) WTT of fuels burned in Scope 1, (b) WTT of purchased electricity and
  heat generation, (c) T&D losses and their WTT. Location-based factors are
  used for all electricity rows (tool choice; see docs/GHG_SCOPE3.md).

Flights: the UK factors already include the 8 % great-circle distance uplift
(2025 methodology paper, para 8.39), so enter great-circle distances. The
inventory figure uses the "Without RF" factor (direct CO2, CH4, N2O); the
"With RF" figure (1.7 multiplier on CO2, paras 8.40-8.44) is kept as a memo
item (tool choice). An explicit ``variant`` on the row overrides this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd

from sustainkit.ghg.factors import FactorError, FactorSet, _norm

UK_2025_SCOPE3 = "uk_gov_ghg_2025_scope3.csv"
CATEGORY_NAMES = {
    3: "Cat 3 Fuel- and energy-related activities",
    6: "Cat 6 Business travel",
    7: "Cat 7 Employee commuting",
}
CATEGORY_ALIASES = {
    "3": 3, "fuel and energy": 3, "fuel- and energy-related activities": 3, "fera": 3,
    "6": 6, "business travel": 6, "business_travel": 6, "travel": 6,
    "7": 7, "employee commuting": 7, "commuting": 7, "employee_commuting": 7,
}
TRAVEL_LEVEL1 = ["Business travel- air", "Business travel- land", "Business travel- sea", "Hotel stay", "Homeworking"]
UPSTREAM_LEVEL1 = [
    "WTT- fuels", "WTT- bioenergy", "WTT- heat and steam", "WTT- UK electricity", "WTT- business travel- air",
    "WTT- business travel- sea", "WTT- pass vehs & travel- land", "WTT- delivery vehs & freight",
    "Transmission and distribution", "UK electricity T&D for EVs",
]
TRAVEL_UNIT_ALIASES = {
    "pkm": "passenger.km", "passenger km": "passenger.km", "passenger-km": "passenger.km", "p.km": "passenger.km",
    "night": "room per night", "nights": "room per night", "room night": "room per night",
    "room nights": "room per night", "room-nights": "room per night",
    "fte hour": "per fte working hour", "fte hours": "per fte working hour", "fte working hours": "per fte working hour",
    "hours": "per fte working hour", "h": "per fte working hour",
    "kilometre": "km", "kilometres": "km", "mile": "miles",
}
PER_PASSENGER_UNITS = {"passenger.km"}
NO_UPSTREAM = ("refrigerant", "other", "process")  # Scope 1 level1 values with no WTT factor by nature


def load_scope3_factors(path: str | Path | None = None) -> FactorSet:
    """Bundled UK 2025 Scope 3 subset (travel, hotel, homeworking, WTT, T&D), or a custom CSV."""
    if path is None:
        p = resources.files("sustainkit.ghg") / "data" / UK_2025_SCOPE3
        with resources.as_file(p) as fp:
            df = pd.read_csv(fp, keep_default_na=False, na_values=[""])
        return FactorSet(df, name="UK Government GHG Conversion Factors 2025 v1 (Scope 3 subset)")
    return FactorSet(pd.read_csv(path, keep_default_na=False, na_values=[""]), name=str(path))


def category_of(value) -> int:
    key = _norm(value).replace("category ", "").replace("cat ", "")
    if key.endswith(".0"):
        key = key[:-2]
    if key not in CATEGORY_ALIASES:
        raise ValueError(f"unknown Scope 3 category {value!r}; use 3, 6 (business travel) or 7 (commuting)")
    return CATEGORY_ALIASES[key]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (km, mean Earth radius 6371.0088 km). Do NOT add the 8 % uplift for UK factors."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return float(2 * 6371.0088 * np.arcsin(np.sqrt(a)))


# ---------------------------------------------------------------------------
# lookups
# ---------------------------------------------------------------------------

def _travel_unit(unit: str, cands: pd.DataFrame) -> tuple[str, float]:
    u = _norm(unit)
    u = TRAVEL_UNIT_ALIASES.get(u, u)
    units = set(cands["_unit"])
    if u in units:
        return u, 1.0
    if u == "km" and units == {"passenger.km"}:
        return "passenger.km", 1.0  # distance per traveller
    if u == "miles" and "passenger.km" in units and "miles" not in units:
        return "passenger.km", 1.609344
    if u == "km" and "miles" in units and "km" not in units:
        return "miles", 1 / 1.609344
    raise FactorError(f"unit {unit!r} not available; options: {sorted(cands['unit'].unique())}")


def lookup_travel(fs: FactorSet, activity: str, unit: str, level1="", level2="", level4="", variant="") -> tuple[pd.Series, float]:
    """Find exactly one travel/hotel/homeworking factor and the quantity multiplier."""
    t = fs.table
    a = _norm(activity)
    m = t["level1"].isin(TRAVEL_LEVEL1) & ((t["_l3"] == a) | ((t["_l3"] == "") & (t["level2"].map(_norm) == a)))
    m |= t["factor_id"].str.lower() == a
    if not m.any():
        raise FactorError(f"no Scope 3 travel factor for {activity!r}; try load_scope3_factors().search({activity!r})")
    for col, val in (("level1", level1), ("level2", level2), ("level4", level4)):
        if _norm(val):
            m &= t[col].map(_norm) == _norm(val)
    cands = t[m]
    if cands.empty:
        raise FactorError(f"no factor for {activity!r} with the given filters")
    is_air = (cands["level1"] == "Business travel- air").all()
    if _norm(variant):
        cands = cands[cands["variant"].map(_norm) == _norm(variant)]
    elif is_air:
        cands = cands[cands["variant"] == "Without RF"]
    if cands.empty:
        raise FactorError(f"no factor for {activity!r} with variant {variant!r}")
    u, mult = _travel_unit(unit, cands)
    rows = cands[cands["_unit"] == u]
    if len(rows) > 1:
        opts = rows[["level2", "level4", "variant"]].drop_duplicates().to_dict("records")
        raise FactorError(f"{len(rows)} factors match {activity!r} in {unit!r}; add level2/level4/variant. Options: {opts[:8]}")
    return rows.iloc[0], mult


def _component(level1: str, level2: str) -> str:
    if level1 in ("Transmission and distribution", "UK electricity T&D for EVs"):
        return "T&D losses"
    if level1 == "WTT- UK electricity" and "T&D" in level2:
        return "WTT of T&D losses"
    if level1 == "WTT- heat and steam" and "distribution" in level2.lower():
        return "WTT of T&D losses"
    return "WTT"


def upstream_factors(fs: FactorSet, base: pd.Series) -> pd.DataFrame:
    """WTT and T&D factors belonging to one Scope 1, Scope 2 or travel factor row.

    Matches on activity (level3), level4, variant and unit within each
    upstream factor group; where a group has several matches the level2
    ("Cars (by size)" vs "WTT- cars (by size)") decides. District heat also
    gets the published 5 % distribution-loss factors.
    """
    t = fs.table
    up = t[t["level1"].isin(UPSTREAM_LEVEL1)]
    key = {"_l3": _norm(base["level3"]), "_unit": _norm(base["unit"])}
    m = (up["_l3"] == key["_l3"]) & (up["_unit"] == key["_unit"])
    m &= up["level4"].map(_norm) == _norm(base.get("level4", ""))
    m &= up["variant"].map(_norm) == _norm(base.get("variant", ""))
    hits = up[m]
    if _norm(base["level3"]) == "district heat and steam":
        hits = pd.concat([hits, up[(up["_l3"] == "5% loss") & (up["_unit"] == key["_unit"])]])
    if hits.empty:
        return hits.assign(component=pd.Series(dtype=str))
    l2 = _norm(base.get("level2", ""))
    multi_ok = ("WTT- UK electricity", "WTT- heat and steam", "Transmission and distribution")
    keep = []
    for lvl1, g in hits.groupby("level1", sort=False):
        if g["level2"].nunique() > 1 and lvl1 not in multi_ok:
            g = g[g["level2"].map(_norm).isin([l2, "wtt- " + l2])]
        keep.append(g)
    res = pd.concat(keep)
    res = res.assign(component=[_component(a, b) for a, b in zip(res["level1"], res["level2"])])
    return res


# ---------------------------------------------------------------------------
# result
# ---------------------------------------------------------------------------

@dataclass
class Scope3Result:
    """One row per (activity, component); kg CO2e. ``rf_memo_kg_co2e`` holds the With-RF flight figure."""

    rows: pd.DataFrame
    factor_set: str
    warnings: list[str] = field(default_factory=list)
    incomplete: dict[int, list[str]] = field(default_factory=dict)

    def __add__(self, other: "Scope3Result") -> "Scope3Result":
        inc = {k: list(v) for k, v in self.incomplete.items()}
        for k, v in other.incomplete.items():
            inc.setdefault(k, []).extend(v)
        return Scope3Result(pd.concat([self.rows, other.rows], ignore_index=True), self.factor_set,
                            self.warnings + other.warnings, inc)

    def total_t(self, category: int | None = None) -> float:
        r = self.rows if category is None else self.rows[self.rows["category"] == category]
        return float(r["kg_co2e"].sum()) / 1000

    @property
    def rf_memo_t(self) -> float:
        """Flights with the radiative-forcing multiplier (With RF factors incl. WTT), t CO2e; memo only."""
        return float(self.rows["rf_memo_kg_co2e"].fillna(0.0).sum()) / 1000

    def by_category(self) -> pd.DataFrame:
        """t CO2e by category and component (activity / WTT / T&D losses / WTT of T&D losses)."""
        if self.rows.empty:
            return pd.DataFrame()
        g = self.rows.groupby(["category_name", "component"])["kg_co2e"].sum().unstack(fill_value=0.0) / 1000
        g["total"] = g.sum(axis=1)
        return g

    def by(self, column: str) -> pd.DataFrame:
        """t CO2e by category and another column (e.g. ``subcategory``, ``site``, ``mode``)."""
        if column not in self.rows.columns:
            raise KeyError(column)
        g = self.rows.groupby(["category_name", column], dropna=False)["kg_co2e"].sum() / 1000
        return g.rename("t_co2e").reset_index().sort_values(["category_name", "t_co2e"], ascending=[True, False])

    def summary(self) -> pd.DataFrame:
        recs = []
        for c in sorted(set(self.rows["category"])):
            sub = self.rows[self.rows["category"] == c]
            for s, v in sub.groupby("subcategory", sort=True)["kg_co2e"].sum().items():
                recs.append((CATEGORY_NAMES[c], s, v / 1000, ""))
            status = "incomplete" if self.incomplete.get(c) else "complete for the rows given"
            recs.append((CATEGORY_NAMES[c], "Total", sub["kg_co2e"].sum() / 1000, status))
        recs.append(("Scope 3 (categories reported)", "Total", self.total_t(), ""))
        if self.rows["rf_memo_kg_co2e"].notna().any():
            recs.append(("Memo: flights incl. radiative forcing (With RF)", "", self.rf_memo_t, "not in totals"))
        return pd.DataFrame(recs, columns=["category", "item", "t_co2e", "note"])

    def to_markdown(self, title: str = "Scope 3 inventory (categories 3, 6, 7)") -> str:
        lines = [f"# {title}", "", f"Factors: {self.factor_set}.", "", "| Category | Item | t CO2e | Note |", "|---|---|---|---|"]
        for _, r in self.summary().iterrows():
            lines.append(f"| {r['category']} | {r['item']} | {r['t_co2e']:,.2f} | {r['note']} |")
        if self.incomplete:
            lines += ["", "Incomplete:"]
            for c, items in sorted(self.incomplete.items()):
                lines += [f"- {CATEGORY_NAMES[c]}: {i}" for i in items]
        if self.warnings:
            lines += ["", "Warnings:", *[f"- {w}" for w in self.warnings]]
        return "\n".join(lines) + "\n"


def _rec(category, subcategory, component, src, qty, unit, f, q, extra):
    rec = {
        "category": category, "category_name": CATEGORY_NAMES[category], "subcategory": subcategory,
        "component": component, "id": src.get("id", ""), "site": src.get("site", ""), "period": src.get("period", ""),
        "activity": src.get("activity", ""), "quantity": qty, "unit": unit, "factor_unit": f["unit"],
        "quantity_in_factor_unit": q, "level1": f["level1"], "level2": f["level2"], "level3": f["level3"],
        "level4": f["level4"], "variant": f["variant"], "factor_id": f["factor_id"],
        "factor_kg_co2e": f["kg_co2e"], "kg_co2e": q * f["kg_co2e"], "rf_memo_kg_co2e": np.nan,
        "note": src.get("note", ""),
    }
    rec.update(extra)
    return rec


def _subcategory(level1: str, level2: str) -> str:
    return {
        "Business travel- air": "Air", "Business travel- sea": "Sea (ferry)", "Hotel stay": "Hotel stays",
        "Homeworking": "Homeworking",
    }.get(level1, "Land: " + level2.split(" (")[0].lower() if level2 else "Land")


# ---------------------------------------------------------------------------
# categories 6 and 7
# ---------------------------------------------------------------------------

TRIP_REQUIRED = ("category", "activity", "quantity", "unit")
TRIP_OPTIONAL = ("id", "site", "period", "level1", "level2", "level4", "variant", "travellers", "note")


def travel(trips: pd.DataFrame, factors: FactorSet | None = None, include_wtt: bool = True) -> Scope3Result:
    """Category 6/7 emissions from trip rows.

    Required columns: ``category`` (6 / business travel, 7 / commuting),
    ``activity`` (factor name: ``Long-haul, to/from UK``, ``National rail``,
    ``Medium car``, ``Germany`` for a hotel night, ``Homeworking (office
    equipment + heating)``), ``quantity`` and ``unit`` (``passenger.km`` or
    ``km`` per traveller for flights/rail/bus, vehicle ``km``/``miles`` for
    cars, ``nights``, ``FTE hours``). Optional ``travellers`` multiplies
    per-passenger quantities only (car km are per vehicle, so car sharing is
    not double counted). ``level2``/``level4``/``variant`` disambiguate
    (e.g. ``Cars (by size)`` + ``Diesel``; ``Economy class``; ``With RF``).
    """
    fs = factors or load_scope3_factors()
    a = trips.copy()
    a.columns = [str(c).strip().lower().replace(" ", "_") for c in a.columns]
    a = a.dropna(how="all").reset_index(drop=True)
    missing = [c for c in TRIP_REQUIRED if c not in a.columns]
    if missing:
        raise Scope3Error([f"missing required column(s) {missing}"])
    if a.empty:
        raise Scope3Error(["no trip rows"])
    for c in TRIP_OPTIONAL:
        if c not in a.columns:
            a[c] = np.nan if c == "travellers" else ""
    txt = [c for c in TRIP_OPTIONAL if c != "travellers"]
    a[txt] = a[txt].fillna("").astype(str)
    qty = pd.to_numeric(a["quantity"], errors="coerce")
    trav = pd.to_numeric(a["travellers"], errors="coerce")
    problems, warnings, out = [], [], []
    for i, r in a.iterrows():
        rown = i + 2
        try:
            cat = category_of(r["category"])
            if cat not in (6, 7):
                raise ValueError(f"category {cat} is derived from the Scope 1-2 inventory, not entered as trips")
        except ValueError as exc:
            problems.append(f"row {rown}: {exc}")
            continue
        if pd.isna(qty[i]) or qty[i] < 0:
            problems.append(f"row {rown}: quantity {r['quantity']!r} must be a number >= 0")
            continue
        if pd.notna(trav[i]) and trav[i] < 1:
            problems.append(f"row {rown}: travellers must be >= 1")
            continue
        try:
            f, mult = lookup_travel(fs, r["activity"], r["unit"], r["level1"], r["level2"], r["level4"], r["variant"])
        except FactorError as exc:
            problems.append(f"row {rown}: {exc}")
            continue
        n = 1.0
        if pd.notna(trav[i]):
            if _norm(f["unit"]) in PER_PASSENGER_UNITS:
                n = float(trav[i])
            elif trav[i] != 1:
                warnings.append(f"row {rown}: travellers ignored for per-vehicle unit {f['unit']!r} (car km count once)")
        q = float(qty[i]) * mult * n
        sub = _subcategory(f["level1"], f["level2"])
        if cat == 6 and f["level1"] == "Homeworking":
            problems.append(f"row {rown}: homeworking belongs to category 7 (employee commuting)")
            continue
        src = r.to_dict()
        rows = [_rec(cat, sub, "activity", src, float(qty[i]), r["unit"], f, q, {})]
        if include_wtt:
            ups = upstream_factors(fs, f)
            if f["level1"] in ("Business travel- air", "Business travel- land", "Business travel- sea") and not (ups["component"] == "WTT").any():
                warnings.append(f"row {rown}: no WTT factor published for {f['level3']!r} ({f['variant'] or f['unit']})")
            for _, u in ups.iterrows():
                rows.append(_rec(cat, sub, u["component"], src, float(qty[i]), r["unit"], u, q, {}))
        if f["level1"] == "Business travel- air" and f["variant"] == "Without RF":
            rf = fs.table[(fs.table["level1"].isin(["Business travel- air", "WTT- business travel- air"]))
                          & (fs.table["_l3"] == f["_l3"]) & (fs.table["level4"] == f["level4"])
                          & (fs.table["variant"] == "With RF") & (fs.table["_unit"] == f["_unit"])]
            if not include_wtt:
                rf = rf[rf["level1"] == "Business travel- air"]
            rows[0]["rf_memo_kg_co2e"] = q * float(rf["kg_co2e"].sum())
        out.extend(rows)
    if problems:
        raise Scope3Error(problems)
    return Scope3Result(pd.DataFrame(out), fs.name, warnings, {})


SURVEY_REQUIRED = ("activity", "employees", "one_way_km")
SURVEY_OPTIONAL = ("level2", "level4", "variant", "days_per_year", "unit", "site", "note", "occupancy")


def commuting_trips(survey: pd.DataFrame, days_per_year: float | None = None, homeworking_fte_hours: float = 0.0,
                    period: str = "") -> pd.DataFrame:
    """Turn a commuting survey into category-7 trip rows.

    One row per mode (and site): ``activity`` (factor name), ``employees``
    (people using the mode on office days), ``one_way_km``, optional
    ``days_per_year`` (office days; otherwise the ``days_per_year`` argument,
    which has no default because it depends on the company's working pattern),
    ``occupancy`` (people per car for car sharing; car km are divided by it).
    Distance = employees x one_way_km x 2 x days / occupancy (car modes only).
    ``homeworking_fte_hours`` adds a homeworking row (FTE working hours/year).
    """
    s = survey.copy()
    s.columns = [str(c).strip().lower().replace(" ", "_") for c in s.columns]
    missing = [c for c in SURVEY_REQUIRED if c not in s.columns]
    if missing:
        raise Scope3Error([f"commuting survey missing column(s) {missing}"])
    for c in SURVEY_OPTIONAL:
        if c not in s.columns:
            s[c] = np.nan if c in ("days_per_year", "occupancy") else ""
    problems, rows = [], []
    for i, r in s.iterrows():
        rown = i + 2
        emp, km = pd.to_numeric(r["employees"], errors="coerce"), pd.to_numeric(r["one_way_km"], errors="coerce")
        days = pd.to_numeric(r["days_per_year"], errors="coerce")
        days = days_per_year if pd.isna(days) else days
        occ = pd.to_numeric(r["occupancy"], errors="coerce")
        if pd.isna(emp) or emp < 0 or pd.isna(km) or km < 0:
            problems.append(f"survey row {rown}: employees and one_way_km must be numbers >= 0")
            continue
        if days is None or pd.isna(days) or not (0 <= float(days) <= 366):
            problems.append(f"survey row {rown}: days_per_year missing or outside 0-366 (give a column or the argument)")
            continue
        unit = str(r["unit"]).strip() if str(r["unit"]).strip() not in ("", "nan") else "km"
        dist = float(emp) * float(km) * 2 * float(days)
        is_car = "car" in _norm(r["activity"]) or "car" in _norm(r["level2"]) or "motorbike" in _norm(r["level2"])
        if pd.notna(occ):
            if occ < 1:
                problems.append(f"survey row {rown}: occupancy must be >= 1")
                continue
            if is_car:
                dist /= float(occ)
        note = str(r["note"]) if str(r["note"]) not in ("", "nan") else ""
        rows.append({
            "id": f"C{i + 1}", "category": 7, "site": str(r["site"]) if str(r["site"]) != "nan" else "", "period": period,
            "activity": r["activity"], "quantity": dist, "unit": unit if is_car or unit != "km" else "passenger.km",
            "level2": "" if str(r["level2"]) == "nan" else r["level2"], "level4": "" if str(r["level4"]) == "nan" else r["level4"],
            "variant": "" if str(r["variant"]) == "nan" else r["variant"],
            "note": (note + f" | {emp:g} employees x {km:g} km x 2 x {float(days):g} days"
                     + (f" / occupancy {occ:g}" if pd.notna(occ) and is_car else "")).strip(" |"),
        })
    if homeworking_fte_hours < 0:
        problems.append("homeworking_fte_hours must be >= 0")
    elif homeworking_fte_hours > 0:
        rows.append({"id": "C-HW", "category": 7, "site": "", "period": period,
                     "activity": "Homeworking (office equipment + heating)", "quantity": float(homeworking_fte_hours),
                     "unit": "per FTE Working Hour", "level2": "", "level4": "", "variant": "", "note": "teleworking (optional in cat 7)"})
    if problems:
        raise Scope3Error(problems)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# category 3
# ---------------------------------------------------------------------------

def fuel_and_energy(inventory, factors: FactorSet | None = None) -> Scope3Result:
    """Category 3 from a Scope 1-2 :class:`~sustainkit.ghg.calc.Inventory`.

    (a) WTT of Scope 1 fuels and owned-vehicle fuel; (b) WTT of purchased
    electricity / heat generation; (c) T&D losses + WTT of T&D losses.
    Quantities are taken in the Scope 1-2 factor's unit, so the same kWh,
    litres or km are reused. Rows without a published upstream factor make
    the category **incomplete** (refrigerants and process emissions have
    none by nature and are skipped silently).
    """
    fs = factors or load_scope3_factors()
    out, inc, warnings = [], [], []
    for _, r in inventory.rows.iterrows():
        if r["scope"] not in ("Scope 1", "Scope 2"):
            continue
        if r["scope"] == "Scope 1" and any(k in _norm(r["level1"]) for k in NO_UPSTREAM):
            continue
        base = pd.Series({k: r[k] for k in ("level1", "level2", "level3", "level4", "variant")} | {"unit": r["factor_unit"]})
        ups = upstream_factors(fs, base)
        label = f"{r['activity']} ({r['factor_unit']}{', ' + r['variant'] if r['variant'] else ''})"
        if ups.empty:
            inc.append(f"no published WTT/T&D factor for {label}")
            continue
        if r["scope"] == "Scope 2" and _norm(r["level3"]).startswith("electricity") and "T&D losses" not in set(ups["component"]):
            warnings.append(f"no T&D factor for {label}")
        q = float(r["quantity_in_factor_unit"])
        src = {"id": r["id"], "site": r["site"], "period": r["period"], "activity": r["activity"], "note": r.get("note", "")}
        for _, u in ups.iterrows():
            if r["scope"] == "Scope 1":
                sub = "(a) WTT of Scope 1 fuels"
            elif u["component"] == "WTT":
                sub = "(b) WTT of purchased electricity/heat"
            else:
                sub = "(c) T&D losses (incl. WTT)"
            out.append(_rec(3, sub, u["component"], src, float(r["quantity"]), r["unit"], u, q, {"source_scope": r["scope"]}))
    res = Scope3Result(pd.DataFrame(out), fs.name, warnings, {3: inc} if inc else {})
    if res.rows.empty:
        res.rows = pd.DataFrame(columns=["category", "category_name", "subcategory", "component", "kg_co2e", "rf_memo_kg_co2e"])
    return res


class Scope3Error(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("Invalid Scope 3 input:\n" + "\n".join(f"  - {p}" for p in problems))


def scope3_inventory(trips: pd.DataFrame | None = None, inventory=None, survey: pd.DataFrame | None = None,
                     days_per_year: float | None = None, homeworking_fte_hours: float = 0.0,
                     factors: FactorSet | None = None, period: str = "") -> Scope3Result:
    """Convenience wrapper: trips (cat 6/7) + commuting survey (cat 7) + cat 3 from an inventory."""
    fs = factors or load_scope3_factors()
    parts = []
    t = [] if trips is None else [trips]
    if survey is not None:
        t.append(commuting_trips(survey, days_per_year, homeworking_fte_hours, period))
    if t:
        parts.append(travel(pd.concat(t, ignore_index=True), fs))
    if inventory is not None:
        parts.append(fuel_and_energy(inventory, fs))
    if not parts:
        raise Scope3Error(["nothing to calculate: give trips, a commuting survey and/or a Scope 1-2 inventory"])
    res = parts[0]
    for p in parts[1:]:
        res = res + p
    return res
