"""KPI library: bundled E/S/G indicator definitions with units, direction and references.

References point to disclosure requirements, not to individual datapoints:

* ESRS codes are the disclosure requirements of ESRS Set 1 (Commission Delegated Regulation (EU)
  2023/2772), e.g. ``E1-6`` (gross Scopes 1, 2, 3 and total GHG emissions). The simplified ESRS that
  follow the 2026 Omnibus amendments may renumber or drop datapoints; that mapping is **not done yet**
  (reported as incomplete rather than guessed).
* GRI codes are disclosures of the GRI Standards: GRI 2 (2021), 205 (2016), 302 (2016), 303 (2018),
  305 (2016), 306 (2020), 403 (2018), 404 (2016), 405 (2016).

Definitions are short paraphrases written for this toolkit, not quotations. ``direction`` says which
way is an improvement; ``neutral`` means the standard sets no preferred direction (a company may set
its own target). ``kind`` controls validation and aggregation:

* ``sum``   additive amount (energy, emissions, waste, counts)
* ``last``  stock at period end (headcount)
* ``mean``  average per unit (training hours per employee)
* ``share`` percentage 0-100 (or the ``min``/``max`` given)
* ``ratio`` derived: (sum of ``numerator`` KPIs) x ``scale`` / ``denominator`` KPI
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pandas as pd

KINDS = ("sum", "last", "mean", "share", "ratio")
DIRECTIONS = ("lower_better", "higher_better", "neutral")
PILLARS = ("E", "S", "G")
COLUMNS = ["kpi_id", "name", "pillar", "unit", "direction", "kind", "min", "max", "numerator", "denominator",
           "scale", "esrs", "gri", "definition"]


def library_path() -> Path:
    return Path(str(resources.files("sustainkit.kpis") / "data" / "library.csv"))


def load_library(path: str | Path | None = None, extra: str | Path | None = None) -> pd.DataFrame:
    """Bundled library, or a custom one with the same columns; ``extra`` rows are appended
    (and override bundled rows with the same ``kpi_id``)."""
    lib = pd.read_csv(path or library_path(), dtype={"esrs": str, "gri": str})
    if extra is not None:
        add = pd.read_csv(extra, dtype={"esrs": str, "gri": str})
        lib = pd.concat([lib[~lib["kpi_id"].isin(add["kpi_id"])], add], ignore_index=True)
    missing = [c for c in ["kpi_id", "name", "pillar", "unit", "direction", "kind"] if c not in lib.columns]
    if missing:
        raise ValueError(f"KPI library is missing columns: {missing}")
    for c in COLUMNS:
        if c not in lib.columns:
            lib[c] = pd.NA
    problems = []
    if lib["kpi_id"].duplicated().any():
        problems.append(f"duplicate kpi_id: {sorted(lib.loc[lib['kpi_id'].duplicated(), 'kpi_id'])}")
    for col, allowed in (("kind", KINDS), ("direction", DIRECTIONS), ("pillar", PILLARS)):
        bad = lib.loc[~lib[col].isin(allowed), "kpi_id"].tolist()
        if bad:
            problems.append(f"{col} must be one of {allowed}: {bad}")
    ids = set(lib["kpi_id"])
    for _, r in lib[lib["kind"] == "ratio"].iterrows():
        comps = components(r)
        if not comps or pd.isna(r["denominator"]):
            problems.append(f"ratio KPI {r['kpi_id']} needs numerator and denominator")
            continue
        unknown = [c for c in comps + [r["denominator"]] if c not in ids]
        if unknown:
            problems.append(f"ratio KPI {r['kpi_id']} refers to unknown KPIs {unknown}")
    if problems:
        raise ValueError("KPI library problems:\n- " + "\n- ".join(problems))
    lib["scale"] = pd.to_numeric(lib["scale"], errors="coerce").fillna(1.0)
    lib["min"] = pd.to_numeric(lib["min"], errors="coerce")
    lib["max"] = pd.to_numeric(lib["max"], errors="coerce")
    return lib[COLUMNS].reset_index(drop=True)


def components(row) -> list[str]:
    num = row.get("numerator") if hasattr(row, "get") else row["numerator"]
    if num is None or (isinstance(num, float) and pd.isna(num)) or num is pd.NA:
        return []
    return [p.strip() for p in str(num).split("+") if p.strip()]


def search(lib: pd.DataFrame, text: str | None = None, pillar: str | None = None) -> pd.DataFrame:
    out = lib
    if pillar:
        out = out[out["pillar"] == pillar.upper()]
    if text:
        t = text.lower()
        hay = (out["kpi_id"] + " " + out["name"] + " " + out["definition"].fillna("") + " "
               + out["esrs"].fillna("") + " " + out["gri"].fillna("")).str.lower()
        out = out[hay.str.contains(t, regex=False)]
    return out.reset_index(drop=True)
