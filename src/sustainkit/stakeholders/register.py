"""Stakeholder register: validation, influence x interest classification, engagement plan, group weights.

Concepts and sources
--------------------
* ESRS 1 (Commission Delegated Regulation (EU) 2023/2772), para 22: stakeholders are those who can
  affect or be affected by the undertaking; two main groups, (a) *affected stakeholders* and (b) *users
  of sustainability statements*; para 23: some stakeholders belong to both. The optional ``category``
  column uses exactly these three values (``affected``, ``user``, ``both``).
* The influence x interest grid is the power-interest grid of strategy textbooks, an adaptation of
  Mendelow (1981, ICIS proceedings), whose original matrix set stakeholder power against the
  *dynamism* of the stakeholder's environment. Quadrant names, the high/low threshold, review
  intervals and weighting schemes below are **tool choices**, not requirements of any standard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ["stakeholder", "group", "influence", "interest"]
OPTIONAL = ["category", "owner", "channel", "last_engaged", "frequency_days", "notes"]
CATEGORIES = ("affected", "user", "both")

# (influence high?, interest high?) -> strategy
QUADRANTS = {
    (True, True): "Manage closely",
    (True, False): "Keep satisfied",
    (False, True): "Keep informed",
    (False, False): "Monitor",
}
# Default review interval per strategy in days (tool choice; override per row with frequency_days).
DEFAULT_FREQUENCY_DAYS = {"Manage closely": 30, "Keep satisfied": 90, "Keep informed": 90, "Monitor": 180}
WEIGHT_SCHEMES = ("salience", "influence", "interest", "mean", "equal")
DUE_SOON_DAYS = 14


class RegisterError(ValueError):
    """Raised when a stakeholder register fails validation; message lists every problem."""


@dataclass
class MapConfig:
    scale: int = 5                       # ratings run 1..scale
    threshold: float | None = None       # score >= threshold is "high"; default = scale midpoint
    weight_scheme: str = "salience"      # how group weights are derived (see group_weights)
    frequency_days: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_FREQUENCY_DAYS))

    def __post_init__(self) -> None:
        if self.scale < 2:
            raise ValueError("scale must be >= 2")
        if self.weight_scheme not in WEIGHT_SCHEMES:
            raise ValueError(f"weight_scheme must be one of {WEIGHT_SCHEMES}")

    @property
    def cut(self) -> float:
        return (1 + self.scale) / 2 if self.threshold is None else float(self.threshold)


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def load_register(path: str | Path, sheet: str | None = None) -> pd.DataFrame:
    """Read a register from CSV or Excel (first sheet, or a sheet whose name contains 'stakeholder')."""
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        xls = pd.ExcelFile(path)
        name = sheet or next((s for s in xls.sheet_names if "stakeholder" in s.lower()), xls.sheet_names[0])
        df = xls.parse(name)
    else:
        df = pd.read_csv(path)
    return _norm_cols(df).dropna(how="all").reset_index(drop=True)


def validate_register(df: pd.DataFrame, scale: int = 5) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Row numbers are spreadsheet rows (header = row 1)."""
    df = _norm_cols(df)
    errors: list[str] = []
    warnings: list[str] = []
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return [f"register: missing required column(s) {missing}"], warnings
    if df.empty:
        return ["register: no rows"], warnings
    for col in ("stakeholder", "group"):
        blank = df[col].isna() | (df[col].astype(str).str.strip() == "")
        errors += [f"row {i + 2}: {col} is missing" for i in df.index[blank]]
    names = df["stakeholder"].astype(str).str.strip().str.lower()
    for n in sorted(names[names.duplicated() & (names != "nan")].unique()):
        errors.append(f"register: duplicate stakeholder {n!r}")
    for col in ("influence", "interest"):
        v = pd.to_numeric(df[col], errors="coerce")
        for i in df.index[v.isna()]:
            errors.append(f"row {i + 2}: {col} must be a number 1-{scale} (got {df.at[i, col]!r})")
        for i in df.index[v.notna() & ((v < 1) | (v > scale))]:
            errors.append(f"row {i + 2}: {col} {v[i]:g} outside 1-{scale}")
    if "category" in df.columns:
        c = df["category"].dropna().astype(str).str.strip().str.lower()
        for i in c.index[~c.isin(CATEGORIES)]:
            errors.append(f"row {i + 2}: category {df.at[i, 'category']!r} not in {CATEGORIES} (ESRS 1 para 22-23)")
        if df["category"].isna().any():
            warnings.append(f"{int(df['category'].isna().sum())} stakeholder(s) without category (affected/user/both)")
    else:
        warnings.append("no 'category' column: affected stakeholders vs users (ESRS 1 para 22) not recorded")
    if "last_engaged" in df.columns:
        d = pd.to_datetime(df["last_engaged"], errors="coerce")
        for i in df.index[df["last_engaged"].notna() & d.isna()]:
            errors.append(f"row {i + 2}: last_engaged {df.at[i, 'last_engaged']!r} is not a date (use YYYY-MM-DD)")
    if "frequency_days" in df.columns:
        f = pd.to_numeric(df["frequency_days"], errors="coerce")
        for i in df.index[df["frequency_days"].notna() & (f.isna() | (f <= 0))]:
            errors.append(f"row {i + 2}: frequency_days must be a positive number")
    extra = [c for c in df.columns if c not in REQUIRED + OPTIONAL]
    if extra:
        warnings.append(f"ignored column(s) {extra}")
    return errors, warnings


@dataclass
class StakeholderMap:
    table: pd.DataFrame          # one row per stakeholder, with quadrant, strategy, salience, engagement status
    weights: pd.DataFrame        # stakeholder_group, weight (+ n, mean influence/interest)
    config: MapConfig
    as_of: pd.Timestamp
    warnings: list[str]

    def quadrant_counts(self) -> pd.Series:
        order = list(QUADRANTS.values())
        return self.table["strategy"].value_counts().reindex(order, fill_value=0)

    def engagement_status_counts(self) -> pd.Series:
        order = ["overdue", "due soon", "ok", "never engaged"]
        return self.table["engagement_status"].value_counts().reindex(order, fill_value=0)

    def link_survey(self, survey_groups) -> dict[str, list[str]]:
        """Compare register groups with the groups used in a materiality survey."""
        reg = set(self.weights["stakeholder_group"])
        sur = {str(g).strip() for g in survey_groups}
        return {"in_survey_not_register": sorted(sur - reg), "in_register_not_survey": sorted(reg - sur)}

    def to_markdown(self) -> str:
        t = self.table
        cut = self.config.cut
        lines = [
            "# Stakeholder map", "",
            f"{len(t)} stakeholders in {t['group'].nunique()} groups. Ratings 1-{self.config.scale}; "
            f"'high' means a rating >= {cut:g} (tool choice). Engagement status as of {self.as_of.date()}.", "",
            "| Strategy | Stakeholders |", "|---|---|",
        ]
        lines += [f"| {k} | {v} |" for k, v in self.quadrant_counts().items()]
        lines += ["", "| Stakeholder | Group | Category | Influence | Interest | Strategy | Last engaged | Next due | Status |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for _, r in t.sort_values(["salience", "stakeholder"], ascending=[False, True]).iterrows():
            last = "" if pd.isna(r["last_engaged"]) else str(pd.Timestamp(r["last_engaged"]).date())
            nxt = "" if pd.isna(r["next_due"]) else str(pd.Timestamp(r["next_due"]).date())
            cat = "" if pd.isna(r.get("category")) else r["category"]
            lines.append(f"| {r['stakeholder']} | {r['group']} | {cat} | {r['influence']:g} | {r['interest']:g} | "
                         f"{r['strategy']} | {last} | {nxt} | {r['engagement_status']} |")
        lines += ["", f"## Survey group weights (scheme: {self.config.weight_scheme}, mean weight = 1)", "",
                  "| Group | Stakeholders | Mean influence | Mean interest | Weight |", "|---|---|---|---|---|"]
        for _, r in self.weights.iterrows():
            lines.append(f"| {r['stakeholder_group']} | {r['n_stakeholders']} | {r['mean_influence']:.2f} | "
                         f"{r['mean_interest']:.2f} | {r['weight']:.3f} |")
        if self.warnings:
            lines += ["", "## Warnings", ""] + [f"- {w}" for w in self.warnings]
        return "\n".join(lines) + "\n"


def _salience(influence: pd.Series, interest: pd.Series, scheme: str) -> pd.Series:
    if scheme == "salience":
        return influence * interest
    if scheme == "influence":
        return influence.astype(float)
    if scheme == "interest":
        return interest.astype(float)
    if scheme == "mean":
        return (influence + interest) / 2.0
    return pd.Series(1.0, index=influence.index)


def group_weights(table: pd.DataFrame, scheme: str = "salience") -> pd.DataFrame:
    """Per-group survey weights for ``sustainkit.materiality`` (columns stakeholder_group, weight).

    A group's weight is the mean stakeholder score in that group under ``scheme``:
    ``salience`` = influence x interest, ``influence``, ``interest``, ``mean`` = (influence + interest) / 2,
    ``equal`` = 1. Weights are scaled so the mean over groups is 1 (the scale of the example weights
    file). Using the *mean* (not the sum) keeps a group from gaining weight just by listing more
    entries, in line with the materiality module counting a group by its weight, not its head-count.
    """
    if scheme not in WEIGHT_SCHEMES:
        raise ValueError(f"scheme must be one of {WEIGHT_SCHEMES}")
    t = table.copy()
    t["_s"] = _salience(t["influence"], t["interest"], scheme)
    g = t.groupby("group", sort=True).agg(n_stakeholders=("stakeholder", "size"), mean_influence=("influence", "mean"),
                                          mean_interest=("interest", "mean"), raw=("_s", "mean")).reset_index()
    g["weight"] = g["raw"] / g["raw"].mean()
    return g.rename(columns={"group": "stakeholder_group"})[
        ["stakeholder_group", "weight", "n_stakeholders", "mean_influence", "mean_interest"]]


def build_map(df: pd.DataFrame, config: MapConfig | None = None, as_of=None) -> StakeholderMap:
    """Validate, classify into quadrants, schedule engagement and derive group weights."""
    cfg = config or MapConfig()
    errors, warnings = validate_register(df, cfg.scale)
    if errors:
        raise RegisterError("stakeholder register has problems:\n- " + "\n- ".join(errors))
    t = _norm_cols(df)
    for c in OPTIONAL:
        if c not in t.columns:
            t[c] = np.nan
    t["stakeholder"] = t["stakeholder"].astype(str).str.strip()
    t["group"] = t["group"].astype(str).str.strip()
    t["category"] = t["category"].where(t["category"].isna(), t["category"].astype(str).str.strip().str.lower())
    t["influence"] = pd.to_numeric(t["influence"]).astype(float)
    t["interest"] = pd.to_numeric(t["interest"]).astype(float)
    cut = cfg.cut
    hi_inf, hi_int = t["influence"] >= cut, t["interest"] >= cut
    t["strategy"] = [QUADRANTS[(a, b)] for a, b in zip(hi_inf, hi_int)]
    t["salience"] = t["influence"] * t["interest"]
    as_of = pd.Timestamp(as_of if as_of is not None else pd.Timestamp.today()).normalize()
    t["last_engaged"] = pd.to_datetime(t["last_engaged"], errors="coerce")
    freq = pd.to_numeric(t["frequency_days"], errors="coerce")
    t["frequency_days"] = freq.fillna(t["strategy"].map(cfg.frequency_days)).astype(float)
    t["next_due"] = t["last_engaged"] + pd.to_timedelta(t["frequency_days"], unit="D")
    days_left = (t["next_due"] - as_of).dt.days
    t["engagement_status"] = np.select(
        [t["last_engaged"].isna(), days_left < 0, days_left <= DUE_SOON_DAYS],
        ["never engaged", "overdue", "due soon"], default="ok")
    w = group_weights(t, cfg.weight_scheme)
    never = int((t["engagement_status"] == "never engaged").sum())
    if never:
        warnings.append(f"{never} stakeholder(s) have no last_engaged date")
    cols = ["stakeholder", "group", "category", "influence", "interest", "salience", "strategy", "owner", "channel",
            "last_engaged", "frequency_days", "next_due", "engagement_status", "notes"]
    return StakeholderMap(table=t[cols], weights=w, config=cfg, as_of=as_of, warnings=warnings)
