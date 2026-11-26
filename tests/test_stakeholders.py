import pandas as pd
import pytest

from sustainkit.cli import main as sk_main
from sustainkit.materiality.io import load_example
from sustainkit.stakeholders import MapConfig, RegisterError, build_map, group_weights, load_register, validate_register
from sustainkit.stakeholders.cli import example_register_path


def _reg(**over):
    d = {
        "stakeholder": ["A", "B", "C", "D"],
        "group": ["G1", "G1", "G2", "G3"],
        "influence": [5, 2, 4, 1],
        "interest": [4, 5, 1, 2],
        "category": ["user", "affected", "both", None],
        "last_engaged": ["2026-11-01", "2026-01-01", "2026-11-20", None],
    }
    d.update(over)
    return pd.DataFrame(d)


def test_quadrants_and_threshold_boundary():
    m = build_map(_reg(), as_of="2026-11-26")
    s = dict(zip(m.table["stakeholder"], m.table["strategy"]))
    assert s == {"A": "Manage closely", "B": "Keep informed", "C": "Keep satisfied", "D": "Monitor"}
    # rating equal to the cut-off counts as high (midpoint 3 on a 1-5 scale)
    m3 = build_map(_reg(influence=[3, 3, 3, 3], interest=[3, 2, 3, 2]), as_of="2026-11-26")
    assert m3.table["strategy"].tolist() == ["Manage closely", "Keep satisfied", "Manage closely", "Keep satisfied"]
    m4 = build_map(_reg(influence=[3, 3, 3, 3], interest=[3, 2, 3, 2]), MapConfig(threshold=3.5), as_of="2026-11-26")
    assert set(m4.table["strategy"]) == {"Monitor"}


def test_engagement_status_uses_strategy_interval_and_override():
    m = build_map(_reg(), as_of="2026-11-26")
    st = dict(zip(m.table["stakeholder"], m.table["engagement_status"]))
    # A: manage closely, 30 days from 1 Nov -> due 1 Dec -> within 14 days -> due soon
    assert st["A"] == "due soon"
    assert st["B"] == "overdue"          # keep informed, 90 days from 1 Jan
    assert st["C"] == "ok"               # keep satisfied, 90 days from 20 Nov
    assert st["D"] == "never engaged"
    m2 = build_map(_reg(frequency_days=[365, 365, None, None]), as_of="2026-11-26")
    assert m2.table.set_index("stakeholder").at["B", "engagement_status"] == "ok"
    assert any("no last_engaged" in w for w in m.warnings)


def test_group_weights_mean_not_headcount_and_scale():
    t = build_map(_reg(), as_of="2026-11-26").table
    w = group_weights(t, "salience").set_index("stakeholder_group")
    # G1 mean salience (20 + 10)/2 = 15, G2 4, G3 2 -> mean 7 -> weights 15/7, 4/7, 2/7
    assert w.loc["G1", "weight"] == pytest.approx(15 / 7)
    assert w.loc["G3", "weight"] == pytest.approx(2 / 7)
    assert w["weight"].mean() == pytest.approx(1.0)
    # duplicating a group's members does not change its weight
    t2 = pd.concat([t, t[t["group"] == "G1"].assign(stakeholder=lambda x: x["stakeholder"] + "2")])
    assert group_weights(t2, "salience").set_index("stakeholder_group").loc["G1", "weight"] == pytest.approx(15 / 7)
    assert (group_weights(t, "equal")["weight"] == 1).all()
    with pytest.raises(ValueError):
        group_weights(t, "votes")


def test_validation_lists_every_problem():
    bad = _reg(influence=[6, "x", 3, 3], category=["user", "investor", None, None],
               last_engaged=["soon", None, None, None])
    bad.loc[1, "stakeholder"] = "A"
    errors, warnings = validate_register(bad)
    text = "\n".join(errors)
    assert "outside 1-5" in text and "must be a number" in text
    assert "duplicate stakeholder" in text and "not a date" in text and "investor" in text
    with pytest.raises(RegisterError):
        build_map(bad)
    errors, _ = validate_register(pd.DataFrame({"stakeholder": ["A"], "group": ["G"]}))
    assert "missing required column" in errors[0]


def test_example_register_links_to_materiality_example_survey():
    reg = load_register(example_register_path())
    m = build_map(reg, as_of="2026-11-26")
    assert len(m.table) == 15
    data = load_example()
    link = m.link_survey(data.survey["stakeholder_group"].unique())
    assert link == {"in_survey_not_register": [], "in_register_not_survey": []}
    assert m.quadrant_counts().sum() == 15


def test_cli_map_writes_outputs_and_weights_feed_materiality(tmp_path):
    reg = tmp_path / "reg.csv"
    assert sk_main(["stakeholders", "example", str(reg)]) == 0
    out = tmp_path / "out"
    rc = sk_main(["stakeholders", "map", str(reg), "--as-of", "2026-11-26", "--weights", str(out / "weights.csv"),
                  "--markdown", str(out / "map.md"), "--csv", str(out / "map.csv"), "--chart", str(out / "map.png")])
    assert rc == 0
    w = pd.read_csv(out / "weights.csv")
    assert list(w.columns) == ["stakeholder_group", "weight"] and w["weight"].mean() == pytest.approx(1.0, abs=1e-3)
    assert (out / "map.png").stat().st_size > 10_000
    assert "Manage closely" in (out / "map.md").read_text()
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"stakeholder": ["A"], "group": ["G"], "influence": [9], "interest": [1]}).to_csv(bad, index=False)
    assert sk_main(["stakeholders", "map", str(bad)]) == 2


def test_modules_registry_marks_stakeholders_available(capsys):
    sk_main(["modules"])
    line = [l for l in capsys.readouterr().out.splitlines() if l.startswith("stakeholders")][0]
    assert "available" in line


def test_derived_weights_change_materiality_survey_scores():
    from sustainkit.materiality.scoring import ScoringConfig, aggregate_survey

    data = load_example()
    m = build_map(load_register(example_register_path()), as_of="2026-11-26")
    gw = dict(zip(m.weights["stakeholder_group"], m.weights["weight"]))
    base = aggregate_survey(data, ScoringConfig())
    derived = aggregate_survey(data, ScoringConfig(group_weights=gw))
    assert base.shape == derived.shape
    num = derived.select_dtypes("number").columns
    assert not base[num].round(6).equals(derived[num].round(6))
