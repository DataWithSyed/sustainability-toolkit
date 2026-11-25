"""Input schema and validation.

Three tables make up an assessment (see ``docs/SCHEMA.md``):

* ``topics``  - one row per sustainability matter, with the analyst's
  impact and financial assessment;
* ``survey``  - optional, long format, one row per respondent x topic;
* ``weights`` - optional, one row per stakeholder group.

Validation collects *all* problems before raising, so a user can fix a
spreadsheet in one pass.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sustainkit.materiality.taxonomy import ENTITY_SPECIFIC, is_known_code, pillar_for

IMPACT_TYPES = (
    "actual_negative",
    "potential_negative",
    "actual_positive",
    "potential_positive",
)

TOPIC_REQUIRED = ("topic_id", "topic", "esrs")
TOPIC_SEVERITY = ("scale", "scope", "irremediability")
TOPIC_OPTIONAL = (
    "pillar",
    "subtopic",
    "impact_type",
    "scale",
    "scope",
    "irremediability",
    "impact_likelihood",
    "human_rights",
    "fin_magnitude",
    "fin_likelihood",
    "time_horizon",
    "value_chain",
    "description",
)
SURVEY_REQUIRED = ("respondent_id", "stakeholder_group", "topic_id")
SURVEY_RATINGS = ("impact_rating", "financial_rating")
WEIGHTS_REQUIRED = ("stakeholder_group", "weight")

TIME_HORIZONS = ("short", "medium", "long")
VALUE_CHAIN = ("upstream", "own_operations", "downstream")


class ValidationError(ValueError):
    """Raised when input tables do not match the schema."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        msg = "Invalid materiality input:\n" + "\n".join(f"  - {p}" for p in problems)
        super().__init__(msg)


@dataclass
class Report:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def _check_range(df, col, lo, hi, errors, table, allow_missing=True):
    if col not in df.columns:
        return
    vals = pd.to_numeric(df[col], errors="coerce")
    bad_type = df[col].notna() & vals.isna()
    for i in df.index[bad_type]:
        errors.append(f"{table} row {i + 2}: {col}={df.at[i, col]!r} is not a number")
    out = vals.notna() & ((vals < lo) | (vals > hi))
    for i in df.index[out]:
        errors.append(f"{table} row {i + 2}: {col}={vals[i]:g} outside [{lo:g}, {hi:g}]")
    if not allow_missing:
        for i in df.index[df[col].isna()]:
            errors.append(f"{table} row {i + 2}: {col} is missing")


def normalise_topics(topics: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names and fill derived columns (pillar, impact_type)."""
    t = _norm_cols(topics).dropna(how="all").reset_index(drop=True)
    if "topic_id" in t.columns:
        t["topic_id"] = t["topic_id"].astype(str).str.strip()
    if "esrs" in t.columns:
        t["esrs"] = t["esrs"].astype(str).str.strip().str.upper()
        derived = t["esrs"].map(pillar_for)
        if "pillar" in t.columns:
            t["pillar"] = t["pillar"].where(t["pillar"].notna(), derived)
        else:
            t["pillar"] = derived
        t["pillar"] = t["pillar"].astype("string").str.strip().str.upper().str[:1]
    if "impact_type" in t.columns:
        t["impact_type"] = t["impact_type"].astype("string").str.strip().str.lower()
        t["impact_type"] = t["impact_type"].fillna("actual_negative")
    else:
        t["impact_type"] = "actual_negative"
    if "human_rights" in t.columns:
        t["human_rights"] = (
            t["human_rights"]
            .map(lambda v: str(v).strip().lower() in {"true", "1", "yes", "y", "x"})
            .astype(bool)
        )
    else:
        t["human_rights"] = False
    return t


def normalise_survey(survey: pd.DataFrame) -> pd.DataFrame:
    s = _norm_cols(survey).dropna(how="all").reset_index(drop=True)
    for c in ("respondent_id", "stakeholder_group", "topic_id"):
        if c in s.columns:
            s[c] = s[c].astype(str).str.strip()
    return s


def normalise_weights(weights: pd.DataFrame) -> pd.DataFrame:
    w = _norm_cols(weights).dropna(how="all").reset_index(drop=True)
    if "stakeholder_group" in w.columns:
        w["stakeholder_group"] = w["stakeholder_group"].astype(str).str.strip()
    return w


def check(
    topics: pd.DataFrame,
    survey: pd.DataFrame | None = None,
    weights: pd.DataFrame | None = None,
    rating_scale: int = 5,
) -> Report:
    """Check already-normalised tables and return errors and warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    t = topics

    missing = [c for c in TOPIC_REQUIRED if c not in t.columns]
    if missing:
        errors.append(f"topics: missing required column(s) {missing}")
        return Report(errors, warnings)
    if t.empty:
        errors.append("topics: no rows")
        return Report(errors, warnings)

    dup = t["topic_id"][t["topic_id"].duplicated()].unique()
    if len(dup):
        errors.append(f"topics: duplicate topic_id {sorted(dup)}")
    for i in t.index[t["topic"].isna() | (t["topic"].astype(str).str.strip() == "")]:
        errors.append(f"topics row {i + 2}: topic name is missing")
    for i in t.index:
        code = t.at[i, "esrs"]
        if not is_known_code(code):
            errors.append(
                f"topics row {i + 2}: esrs={code!r} is not E1-E5, S1-S4, G1 or {ENTITY_SPECIFIC}"
            )
    if "pillar" in t.columns:
        bad = t["pillar"].isna() | ~t["pillar"].isin(["E", "S", "G"])
        for i in t.index[bad]:
            errors.append(f"topics row {i + 2}: pillar must be E, S or G (set it for {ENTITY_SPECIFIC} topics)")
    bad_type = ~t["impact_type"].isin(IMPACT_TYPES)
    for i in t.index[bad_type]:
        errors.append(f"topics row {i + 2}: impact_type={t.at[i, 'impact_type']!r} not in {IMPACT_TYPES}")

    for col in TOPIC_SEVERITY + ("fin_magnitude",):
        _check_range(t, col, 1, 5, errors, "topics")
    for col in ("impact_likelihood", "fin_likelihood"):
        _check_range(t, col, 0, 1, errors, "topics")

    has_impact = all(c in t.columns for c in ("scale", "scope"))
    if has_impact:
        neg = t["impact_type"].astype(str).str.endswith("negative")
        if "irremediability" not in t.columns:
            if neg.any():
                errors.append("topics: negative impacts need an irremediability column")
        else:
            rows = t.index[neg & t["scale"].notna() & t["irremediability"].isna()]
            for i in rows:
                errors.append(f"topics row {i + 2}: negative impact needs irremediability")
        pot = t["impact_type"].astype(str).str.startswith("potential")
        if "impact_likelihood" not in t.columns:
            if (pot & t["scale"].notna()).any():
                errors.append("topics: potential impacts need an impact_likelihood column")
        else:
            rows = t.index[pot & t["scale"].notna() & t["impact_likelihood"].isna()]
            for i in rows:
                errors.append(f"topics row {i + 2}: potential impact needs impact_likelihood")
    if "fin_magnitude" in t.columns and "fin_likelihood" not in t.columns:
        errors.append("topics: fin_magnitude given without fin_likelihood")

    for col, allowed in (("time_horizon", TIME_HORIZONS), ("value_chain", VALUE_CHAIN)):
        if col in t.columns:
            vals = t[col].dropna().astype(str).str.strip().str.lower()
            for i in vals.index[~vals.isin(allowed)]:
                warnings.append(f"topics row {i + 2}: {col}={t.at[i, col]!r} not in {allowed}")

    topic_ids = set(t["topic_id"])
    if survey is not None and not survey.empty:
        s = survey
        miss = [c for c in SURVEY_REQUIRED if c not in s.columns]
        if miss:
            errors.append(f"survey: missing required column(s) {miss}")
        elif not any(c in s.columns for c in SURVEY_RATINGS):
            errors.append(f"survey: needs at least one of {SURVEY_RATINGS}")
        else:
            unknown = sorted(set(s["topic_id"]) - topic_ids)
            if unknown:
                errors.append(f"survey: topic_id not in topics: {unknown[:10]}")
            for col in SURVEY_RATINGS:
                _check_range(s, col, 1, rating_scale, errors, "survey")
            dups = s.duplicated(["respondent_id", "topic_id"])
            if dups.any():
                errors.append(f"survey: {int(dups.sum())} duplicate respondent x topic rows")

        if weights is not None and not weights.empty:
            w = weights
            miss = [c for c in WEIGHTS_REQUIRED if c not in w.columns]
            if miss:
                errors.append(f"weights: missing required column(s) {miss}")
            else:
                _check_range(w, "weight", 0, float("inf"), errors, "weights", allow_missing=False)
                if w["stakeholder_group"].duplicated().any():
                    errors.append("weights: duplicate stakeholder_group")
                if "stakeholder_group" in s.columns:
                    groups = set(s["stakeholder_group"])
                    no_w = sorted(groups - set(w["stakeholder_group"]))
                    if no_w:
                        errors.append(f"weights: no weight for group(s) {no_w}")
                    unused = sorted(set(w["stakeholder_group"]) - groups)
                    if unused:
                        warnings.append(f"weights: group(s) with no survey answers {unused}")
                if pd.to_numeric(w["weight"], errors="coerce").fillna(0).sum() <= 0:
                    errors.append("weights: weights must sum to more than zero")

    # every topic needs some evidence on each axis
    for i in t.index:
        tid = t.at[i, "topic_id"]
        has_survey = survey is not None and not survey.empty and "topic_id" in survey.columns and (survey["topic_id"] == tid).any()
        has_imp = has_impact and pd.notna(t.at[i, "scale"])
        has_fin = "fin_magnitude" in t.columns and pd.notna(t.at[i, "fin_magnitude"])
        if not (has_imp or has_survey):
            errors.append(f"topic {tid!r}: no impact assessment and no survey answers")
        if not (has_fin or has_survey):
            errors.append(f"topic {tid!r}: no financial assessment and no survey answers")
    return Report(errors, warnings)


def validate(topics, survey=None, weights=None, rating_scale: int = 5):
    """Normalise and validate tables; raise :class:`ValidationError` on problems.

    Returns the normalised ``(topics, survey, weights)``.
    """
    t = normalise_topics(topics)
    s = None if survey is None else normalise_survey(survey)
    w = None if weights is None else normalise_weights(weights)
    rep = check(t, s, w, rating_scale=rating_scale)
    if not rep.ok:
        raise ValidationError(rep.errors)
    return t, s, w
