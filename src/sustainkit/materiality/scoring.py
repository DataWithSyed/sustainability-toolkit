"""Double materiality scoring.

Impact materiality (ESRS 1 section 3.4):

* severity of a negative impact = mean of *scale*, *scope* and
  *irremediable character* (ESRS 1 para 45); of a positive impact = mean
  of *scale* and *scope* (para 46);
* actual impacts have likelihood 1; potential impacts are weighted by
  their likelihood (paras 45-46);
* for potential negative human-rights impacts, severity takes precedence
  over likelihood (para 45). Here that is implemented, as a conservative
  simplification, by ignoring likelihood for rows flagged ``human_rights``.

Financial materiality (ESRS 1 section 3.5, para 49): potential magnitude of
financial effects x likelihood of occurrence.

Stakeholder survey ratings, where present, are aggregated per group, then
across groups using group weights, and blended with the assessment. The
blend shares and thresholds are *user choices*: ESRS does not prescribe
numeric thresholds or a scoring formula. All scores are on a 1-5 scale
(a likelihood-weighted score can fall below 1, down to 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sustainkit.materiality.io import MaterialityData

SCALE_MAX = 5.0


@dataclass
class ScoringConfig:
    """Settings for :func:`score`.

    Attributes:
        impact_threshold: impact score at or above which a topic is material.
        financial_threshold: financial score at or above which a topic is material.
        survey_blend_impact: share of the survey in the impact score (0-1).
        survey_blend_financial: share of the survey in the financial score (0-1).
        group_weights: overrides the ``weights`` table; groups missing from both
            get weight 1.
        aggregation: ``"mean"`` or ``"median"`` for ratings within a group.
        human_rights_precedence: ignore likelihood for potential negative
            impacts flagged ``human_rights``.
    """

    impact_threshold: float = 3.0
    financial_threshold: float = 3.0
    survey_blend_impact: float = 0.3
    survey_blend_financial: float = 0.3
    group_weights: dict[str, float] = field(default_factory=dict)
    aggregation: str = "mean"
    human_rights_precedence: bool = True

    def __post_init__(self):
        for name in ("survey_blend_impact", "survey_blend_financial"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v}")
        for name in ("impact_threshold", "financial_threshold"):
            v = getattr(self, name)
            if not 0.0 <= v <= SCALE_MAX:
                raise ValueError(f"{name} must be in [0, {SCALE_MAX}], got {v}")
        if self.aggregation not in {"mean", "median"}:
            raise ValueError("aggregation must be 'mean' or 'median'")


def rescale(values, scale_max: float, target_max: float = SCALE_MAX):
    """Linearly map ratings from [1, scale_max] to [1, target_max]."""
    v = np.asarray(values, dtype=float)
    if scale_max == target_max:
        return v
    return 1.0 + (v - 1.0) * (target_max - 1.0) / (scale_max - 1.0)


def impact_assessment(topics: pd.DataFrame, human_rights_precedence: bool = True) -> pd.DataFrame:
    """Severity, likelihood and impact score from the analyst assessment."""
    t = topics
    out = pd.DataFrame(index=t.index)
    if not all(c in t.columns for c in ("scale", "scope")):
        out["severity"] = np.nan
        out["impact_likelihood_used"] = np.nan
        out["impact_assessed"] = np.nan
        return out
    scale = pd.to_numeric(t["scale"], errors="coerce")
    scope = pd.to_numeric(t["scope"], errors="coerce")
    irr = pd.to_numeric(t.get("irremediability", pd.Series(np.nan, index=t.index)), errors="coerce")
    itype = t["impact_type"].astype(str)
    negative = itype.str.endswith("negative")
    potential = itype.str.startswith("potential")
    sev = np.where(negative, (scale + scope + irr) / 3.0, (scale + scope) / 2.0)
    lik = pd.to_numeric(t.get("impact_likelihood", pd.Series(np.nan, index=t.index)), errors="coerce")
    lik = lik.where(potential, 1.0)
    if human_rights_precedence:
        hr = t["human_rights"].astype(bool) & negative & potential
        lik = lik.where(~hr, 1.0)
    out["severity"] = sev
    out["impact_likelihood_used"] = lik
    out["impact_assessed"] = out["severity"] * lik
    return out


def financial_assessment(topics: pd.DataFrame) -> pd.Series:
    if "fin_magnitude" not in topics.columns:
        return pd.Series(np.nan, index=topics.index)
    mag = pd.to_numeric(topics["fin_magnitude"], errors="coerce")
    lik = pd.to_numeric(topics["fin_likelihood"], errors="coerce")
    return mag * lik


def resolve_weights(data: MaterialityData, cfg: ScoringConfig) -> dict[str, float]:
    weights: dict[str, float] = {}
    if data.weights is not None and not data.weights.empty:
        weights.update(
            {
                str(g): float(w)
                for g, w in zip(data.weights["stakeholder_group"], data.weights["weight"])
            }
        )
    weights.update({str(k): float(v) for k, v in cfg.group_weights.items()})
    if data.survey is not None:
        for g in data.survey["stakeholder_group"].unique():
            weights.setdefault(str(g), 1.0)
    return weights


def aggregate_survey(data: MaterialityData, cfg: ScoringConfig | None = None) -> pd.DataFrame:
    """Aggregate survey ratings per topic.

    Each group's ratings are first summarised (mean or median), then groups
    are combined with their weights, renormalised over groups that rated the
    topic. A group therefore counts by its weight, not its head-count.

    Returns, per ``topic_id``: ``survey_impact``, ``survey_financial``
    (rescaled to 1-5), ``n_responses``, ``n_groups`` and ``group_spread``
    (max minus min of group means for impact, a simple disagreement measure).
    """
    cfg = cfg or ScoringConfig()
    cols = ["survey_impact", "survey_financial", "n_responses", "n_groups", "group_spread"]
    s = data.survey
    if s is None or s.empty:
        return pd.DataFrame(columns=cols).rename_axis("topic_id")
    weights = resolve_weights(data, cfg)
    s = s.copy()
    for col in ("impact_rating", "financial_rating"):
        if col in s.columns:
            s[col] = rescale(pd.to_numeric(s[col], errors="coerce"), data.rating_scale)
        else:
            s[col] = np.nan
    agg = cfg.aggregation
    g = s.groupby(["topic_id", "stakeholder_group"])[["impact_rating", "financial_rating"]].agg(agg)
    g = g.reset_index()
    g["w"] = g["stakeholder_group"].map(weights).astype(float)

    def wmean(frame: pd.DataFrame, col: str) -> float:
        m = frame[col].notna() & (frame["w"] > 0)
        if not m.any():
            return np.nan
        return float(np.average(frame.loc[m, col], weights=frame.loc[m, "w"]))

    rows = []
    for tid, frame in g.groupby("topic_id"):
        imp = frame["impact_rating"].dropna()
        rows.append(
            {
                "topic_id": tid,
                "survey_impact": wmean(frame, "impact_rating"),
                "survey_financial": wmean(frame, "financial_rating"),
                "n_groups": int(frame["stakeholder_group"].nunique()),
                "group_spread": float(imp.max() - imp.min()) if len(imp) else np.nan,
            }
        )
    out = pd.DataFrame(rows).set_index("topic_id")
    out["n_responses"] = s.groupby("topic_id")["respondent_id"].nunique()
    return out[cols]


def _blend(assessed: pd.Series, survey: pd.Series, share: float) -> pd.Series:
    both = assessed.notna() & survey.notna()
    out = assessed.where(assessed.notna(), survey)
    out[both] = (1 - share) * assessed[both] + share * survey[both]
    return out


def quadrant(impact: float, financial: float, cfg: ScoringConfig) -> str:
    i = impact >= cfg.impact_threshold
    f = financial >= cfg.financial_threshold
    if i and f:
        return "double"
    if i:
        return "impact"
    if f:
        return "financial"
    return "not material"


def score(data: MaterialityData, config: ScoringConfig | None = None) -> pd.DataFrame:
    """Score every topic. Returns one row per topic, sorted by priority.

    Key columns: ``impact_score``, ``financial_score`` (1-5 scale),
    ``material`` (either score at/above its threshold, i.e. double
    materiality's "either" rule), ``quadrant`` and ``priority`` (Euclidean
    distance from the origin, a common ranking convention).
    """
    cfg = config or ScoringConfig()
    t = data.topics.copy()
    imp = impact_assessment(t, cfg.human_rights_precedence)
    t = pd.concat([t, imp], axis=1)
    t["financial_assessed"] = financial_assessment(t)
    sv = aggregate_survey(data, cfg)
    t = t.join(sv, on="topic_id")
    t["impact_score"] = _blend(t["impact_assessed"], t["survey_impact"], cfg.survey_blend_impact)
    t["financial_score"] = _blend(t["financial_assessed"], t["survey_financial"], cfg.survey_blend_financial)
    t["material"] = (t["impact_score"] >= cfg.impact_threshold) | (
        t["financial_score"] >= cfg.financial_threshold
    )
    t["quadrant"] = [quadrant(i, f, cfg) for i, f in zip(t["impact_score"], t["financial_score"])]
    t["priority"] = np.hypot(t["impact_score"], t["financial_score"])
    t = t.sort_values("priority", ascending=False).reset_index(drop=True)
    t["rank"] = np.arange(1, len(t) + 1)
    t.attrs["config"] = cfg
    t.attrs["method"] = "double"
    return t


def score_classic(classic: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
    """Turn a classic two-axis matrix into the scored-table format.

    Stakeholder importance becomes the y-axis and business impact the
    x-axis, both rescaled to 1-5. **This is not double materiality**: the
    y-axis measures stakeholder concern, not the undertaking's impacts.
    """
    sm = float(classic["scale_max"].iloc[0]) if len(classic) else 10.0
    out = pd.DataFrame(
        {
            "topic_id": [f"T{i + 1:02d}" for i in range(len(classic))],
            "topic": classic["topic"].astype(str).values,
            "pillar": "S",
            "impact_score": rescale(classic["stakeholder_importance"], sm),
            "financial_score": rescale(classic["business_impact"], sm),
        }
    )
    try:
        from sustainkit.materiality.text import guess_pillar

        out["pillar"] = [guess_pillar(x) for x in out["topic"]]
    except Exception:  # pragma: no cover - optional helper
        pass
    cfg = ScoringConfig(impact_threshold=threshold, financial_threshold=threshold)
    out["material"] = (out["impact_score"] >= threshold) | (out["financial_score"] >= threshold)
    out["quadrant"] = [quadrant(i, f, cfg) for i, f in zip(out["impact_score"], out["financial_score"])]
    out["priority"] = np.hypot(out["impact_score"], out["financial_score"])
    out = out.sort_values("priority", ascending=False).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    out.attrs["config"] = cfg
    out.attrs["method"] = "classic"
    return out
