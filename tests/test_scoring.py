import math

import pandas as pd
import pytest

from sustainkit.materiality import ScoringConfig, score
from sustainkit.materiality.io import MaterialityData, _build
from sustainkit.materiality.scoring import aggregate_survey, impact_assessment, rescale


def data(topics, survey=None, weights=None, scale=5):
    return _build(topics, survey, weights, scale, None)


def test_severity_follows_esrs_criteria(topics):
    d = data(topics)
    imp = impact_assessment(d.topics)
    # negative: mean(scale, scope, irremediability); positive: mean(scale, scope)
    assert imp.loc[0, "severity"] == pytest.approx(4.0)
    assert imp.loc[2, "severity"] == pytest.approx(3.0)
    # actual impacts have likelihood 1
    assert imp.loc[0, "impact_likelihood_used"] == 1.0
    # potential: severity x likelihood
    assert imp.loc[3, "impact_assessed"] == pytest.approx(2.0 * 0.2)


def test_human_rights_severity_precedence(topics):
    d = data(topics)
    on = impact_assessment(d.topics, human_rights_precedence=True)
    off = impact_assessment(d.topics, human_rights_precedence=False)
    assert on.loc[1, "impact_assessed"] == pytest.approx(4.0)
    assert off.loc[1, "impact_assessed"] == pytest.approx(2.0)


def test_financial_is_magnitude_times_likelihood(topics):
    s = score(data(topics), ScoringConfig(survey_blend_financial=0))
    row = s.set_index("topic_id").loc["D"]
    assert row["financial_score"] == pytest.approx(1.0)


def test_group_weighting_not_headcount(topics, survey, weights):
    d = data(topics, survey, weights)
    agg = aggregate_survey(d)
    # 3 employees rate 5, 1 investor rates 1, equal group weights -> 3, not 4
    assert agg.loc["A", "survey_impact"] == pytest.approx(3.0)
    assert agg.loc["A", "n_responses"] == 4
    assert agg.loc["A", "n_groups"] == 2
    assert agg.loc["A", "group_spread"] == pytest.approx(4.0)


def test_weight_override(topics, survey, weights):
    d = data(topics, survey, weights)
    agg = aggregate_survey(d, ScoringConfig(group_weights={"Investors": 3.0}))
    assert agg.loc["A", "survey_impact"] == pytest.approx((5 * 1 + 1 * 3) / 4)


def test_zero_weight_drops_group(topics, survey, weights):
    w = weights.copy()
    w.loc[1, "weight"] = 0
    agg = aggregate_survey(data(topics, survey, w))
    assert agg.loc["A", "survey_impact"] == pytest.approx(5.0)


def test_blend(topics, survey, weights):
    cfg = ScoringConfig(survey_blend_impact=0.5, survey_blend_financial=0.0)
    s = score(data(topics, survey, weights), cfg).set_index("topic_id")
    assert s.loc["A", "impact_score"] == pytest.approx(0.5 * 4.0 + 0.5 * 3.0)
    assert s.loc["A", "financial_score"] == pytest.approx(4.0)


def test_survey_only_topic_uses_survey(topics, survey, weights):
    t = topics.copy()
    t.loc[3, ["scale", "scope", "irremediability", "impact_likelihood", "fin_magnitude", "fin_likelihood"]] = None
    s = score(data(t, survey, weights)).set_index("topic_id")
    assert s.loc["D", "impact_score"] == pytest.approx(3.0)
    assert s.loc["D", "financial_score"] == pytest.approx(3.0)


def test_either_rule_and_quadrants(topics):
    cfg = ScoringConfig(impact_threshold=3.0, financial_threshold=3.0)
    s = score(data(topics), cfg).set_index("topic_id")
    assert s.loc["A", "quadrant"] == "double"  # 4.0 / 4.0
    assert s.loc["B", "quadrant"] == "impact"  # 4.0 (HR precedence) / 1.5
    assert s.loc["D", "quadrant"] == "not material"
    assert s.loc["B", "material"] and not s.loc["D", "material"]


def test_ranked_by_priority(topics):
    s = score(data(topics))
    assert list(s["rank"]) == [1, 2, 3, 4]
    assert s["priority"].is_monotonic_decreasing
    assert s.loc[0, "priority"] == pytest.approx(math.hypot(4.0, 4.0))


def test_rescale_10_point_ratings():
    assert list(rescale([1, 10], 10)) == [1.0, 5.0]
    assert rescale([5.5], 10)[0] == pytest.approx(3.0)


def test_median_aggregation(topics, weights):
    rows = [
        {"respondent_id": f"E{i}", "stakeholder_group": "Employees", "topic_id": "A", "impact_rating": r}
        for i, r in enumerate([1, 2, 5])
    ]
    s = pd.DataFrame(rows)
    d = data(topics, s, weights.iloc[:1])
    assert aggregate_survey(d, ScoringConfig(aggregation="median")).loc["A", "survey_impact"] == 2
    assert aggregate_survey(d, ScoringConfig(aggregation="mean")).loc["A", "survey_impact"] == pytest.approx(8 / 3)


@pytest.mark.parametrize(
    "kwargs",
    [{"survey_blend_impact": 1.5}, {"impact_threshold": -1}, {"aggregation": "mode"}],
)
def test_bad_config(kwargs):
    with pytest.raises(ValueError):
        ScoringConfig(**kwargs)
