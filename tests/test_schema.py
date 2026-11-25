import pandas as pd
import pytest

from sustainkit.materiality import ValidationError, validate
from sustainkit.materiality.schema import check, normalise_topics
from sustainkit.materiality.taxonomy import ESRS_TOPICS, is_known_code, pillar_for


def test_taxonomy_has_ten_topical_standards():
    assert sorted(ESRS_TOPICS) == ["E1", "E2", "E3", "E4", "E5", "G1", "S1", "S2", "S3", "S4"]
    assert pillar_for("e3") == "E" and pillar_for("G1") == "G"
    assert is_known_code("ENTITY") and not is_known_code("X9")


def test_valid_tables_pass(topics, survey, weights):
    t, s, w = validate(topics, survey, weights)
    assert list(t["pillar"]) == ["E", "S", "S", "G"]
    assert t["human_rights"].dtype == bool


def test_column_names_are_normalised(topics):
    t = topics.rename(columns={"topic_id": "Topic ID", "fin_magnitude": "Fin Magnitude"})
    out, _, _ = validate(t)
    assert "topic_id" in out.columns and "fin_magnitude" in out.columns


def test_missing_required_column(topics):
    with pytest.raises(ValidationError, match="missing required"):
        validate(topics.drop(columns=["esrs"]))


def test_collects_all_problems(topics):
    bad = topics.copy()
    bad.loc[0, "scale"] = 9
    bad.loc[1, "impact_likelihood"] = 1.5
    bad.loc[2, "esrs"] = "Q7"
    bad.loc[3, "topic_id"] = "A"
    with pytest.raises(ValidationError) as exc:
        validate(bad)
    text = "\n".join(exc.value.problems)
    assert "scale=9" in text and "impact_likelihood=1.5" in text
    assert "Q7" in text and "duplicate topic_id" in text


def test_potential_needs_likelihood(topics):
    bad = topics.copy()
    bad.loc[1, "impact_likelihood"] = None
    with pytest.raises(ValidationError, match="needs impact_likelihood"):
        validate(bad)


def test_negative_needs_irremediability(topics):
    bad = topics.copy()
    bad.loc[0, "irremediability"] = None
    with pytest.raises(ValidationError, match="needs irremediability"):
        validate(bad)


def test_bad_impact_type(topics):
    bad = topics.copy()
    bad.loc[0, "impact_type"] = "sideways"
    with pytest.raises(ValidationError, match="impact_type"):
        validate(bad)


def test_entity_specific_needs_pillar(topics):
    bad = topics.copy()
    bad.loc[0, "esrs"] = "ENTITY"
    with pytest.raises(ValidationError, match="pillar"):
        validate(bad)
    ok = bad.copy()
    ok["pillar"] = [None, None, None, None]
    ok.loc[0, "pillar"] = "e"
    t, _, _ = validate(ok)
    assert t.loc[0, "pillar"] == "E"


def test_survey_unknown_topic_and_range(topics, survey, weights):
    s = survey.copy()
    s.loc[0, "topic_id"] = "ZZZ"
    s.loc[1, "impact_rating"] = 7
    with pytest.raises(ValidationError) as exc:
        validate(topics, s, weights)
    text = "\n".join(exc.value.problems)
    assert "ZZZ" in text and "impact_rating=7" in text


def test_survey_rating_scale_10(topics, survey, weights):
    s = survey.copy()
    s["impact_rating"] = 9
    validate(topics, s, weights, rating_scale=10)
    with pytest.raises(ValidationError):
        validate(topics, s, weights, rating_scale=5)


def test_missing_group_weight(topics, survey, weights):
    with pytest.raises(ValidationError, match="no weight for group"):
        validate(topics, survey, weights.iloc[:1])


def test_duplicate_answers(topics, survey, weights):
    s = pd.concat([survey, survey.iloc[:1]])
    with pytest.raises(ValidationError, match="duplicate respondent"):
        validate(topics, s, weights)


def test_topic_without_any_evidence(topics):
    t = topics.copy()
    t.loc[3, ["scale", "scope", "irremediability", "impact_likelihood"]] = None
    with pytest.raises(ValidationError, match="no impact assessment"):
        validate(t)


def test_survey_only_topic_is_allowed(topics, survey, weights):
    t = topics.copy()
    t.loc[3, ["scale", "scope", "irremediability", "impact_likelihood", "fin_magnitude", "fin_likelihood"]] = None
    validate(t, survey, weights)


def test_warnings_for_unknown_time_horizon(topics):
    t = normalise_topics(topics.assign(time_horizon=["short", "soon", None, "long"]))
    rep = check(t)
    assert rep.ok and any("soon" in w for w in rep.warnings)
