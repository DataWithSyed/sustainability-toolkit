import math

import pandas as pd
import pytest

from sustainkit.cli import main as cli_main
from sustainkit.kpis import ALL_SITES, KPILogError, build_report, load_library, load_log, search, validate_log
from sustainkit.kpis.cli import example_log_path


@pytest.fixture
def lib():
    return load_library()


def test_library_is_consistent_and_referenced(lib):
    assert lib["kpi_id"].is_unique
    assert set(lib["pillar"]) == {"E", "S", "G"}
    # every non-denominator KPI carries a GRI or ESRS reference
    refs = lib[~lib["kpi_id"].isin(["revenue_meur"])]
    assert (refs["gri"].notna() | refs["esrs"].notna()).all()
    assert search(lib, "305-1").kpi_id.tolist() == ["ghg_scope1_t"]
    assert set(search(lib, pillar="G")["pillar"]) == {"G"}


def test_example_report_numbers(lib):
    rep = build_report(load_log(example_log_path()), lib)
    s = rep.summary.set_index("kpi_id")
    # derived intensity 2025 = (392.36 + 486.75) / 66.5
    v = rep.values
    gi = v[(v.kpi_id == "ghg_intensity_s12_t_per_meur") & (v.year == 2025)]["value"].item()
    assert gi == pytest.approx((392.36 + 486.75) / 66.5)
    trir = v[(v.kpi_id == "trir") & (v.year == 2025)]["value"].item()
    assert trir == pytest.approx(5 * 1e6 / 731000)
    assert s.loc["ghg_scope1_t", "status"] == "improved"
    assert s.loc["training_hours_per_employee", "status"] == "worsened"
    assert s.loc["employees_headcount", "status"] == "up"            # neutral direction
    assert "gap 2023" in s.loc["water_consumption_m3", "flags"]
    assert "check data 2024" in s.loc["waste_hazardous_t", "flags"]
    assert s.loc["energy_renewable_share_pct", "change_text"].startswith("+3.5 pp")
    assert s.loc["corruption_incidents", "status"] == "no change"
    assert any("water_consumption_m3" in m for m in rep.incomplete)
    # no change is computed across the 2023 gap
    c = rep.changes
    assert c[(c.kpi_id == "water_consumption_m3")]["year"].tolist() == [2025]
    cagr = s.loc["energy_total_mwh", "cagr"]
    assert cagr == pytest.approx((4380 / 4850) ** (1 / 3) - 1)


def test_wide_format_equals_long(lib, tmp_path):
    long = load_log(example_log_path())
    wide = long.pivot(index=["kpi_id", "unit"], columns="year", values="value").reset_index()
    wide.columns = [str(c) for c in wide.columns]
    p = tmp_path / "wide.csv"
    wide.to_csv(p, index=False)
    a = build_report(load_log(example_log_path()), lib).summary
    b = build_report(load_log(p), lib).summary
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))


def test_validation_lists_every_problem(lib):
    bad = pd.DataFrame({
        "kpi_id": ["ghg_scope1_t", "ghg_scope1_t", "nonsense", "energy_renewable_share_pct", "energy_total_mwh",
                   "trir", "waste_total_t"],
        "year": [2024, 2024, 2024, 2024, "20x5", 2024, 2024],
        "value": [10, 11, 1, 130, 5, 3, "abc"],
        "unit": ["t CO2e", "t CO2e", None, "%", "MWh", None, "kg"],
    })
    errors, _ = validate_log(bad, lib)
    text = "\n".join(errors)
    for needle in ("unknown kpi_id", "nonsense", "duplicate rows", "above the maximum", "not a calendar year",
                   "calculated, not entered", "not a number", "differs from the library unit"):
        assert needle in text, needle
    with pytest.raises(KPILogError):
        build_report(bad, lib)


def test_sites_total_only_additive_kpis(lib):
    log = pd.DataFrame({
        "kpi_id": ["energy_total_mwh"] * 4 + ["energy_renewable_share_pct"] * 4 + ["revenue_meur"] * 4,
        "site": ["A", "B", "A", "B"] * 3,
        "year": [2024, 2024, 2025, 2025] * 3,
        "value": [100, 50, 90, 60, 10, 50, 20, 60, 5, 5, 6, 6],
    })
    rep = build_report(log, lib)
    v = rep.values
    tot = v[(v.site == ALL_SITES) & (v.kpi_id == "energy_total_mwh")].set_index("year")["value"]
    assert tot.to_dict() == {2024: 150, 2025: 150}
    assert v[(v.site == ALL_SITES) & (v.kpi_id == "energy_renewable_share_pct")].empty   # shares not totalled
    # derived intensity works per site and for the total
    ei = v[(v.kpi_id == "energy_intensity_mwh_per_meur")].set_index(["site", "year"])["value"]
    assert ei[(ALL_SITES, 2025)] == pytest.approx(150 / 12)
    assert ei[("A", 2024)] == pytest.approx(20)


def test_ratio_reported_incomplete_when_input_missing(lib):
    log = pd.DataFrame({"kpi_id": ["ghg_scope1_t", "revenue_meur", "ghg_scope1_t", "ghg_scope2_lb_t", "revenue_meur"],
                        "year": [2024, 2024, 2025, 2025, 2025], "value": [10, 2, 9, 3, 2]})
    rep = build_report(log, lib)
    assert any("ghg_intensity_s12_t_per_meur" in m and "2024" in m and "ghg_scope2_lb_t" in m for m in rep.incomplete)
    gi = rep.values[rep.values.kpi_id == "ghg_intensity_s12_t_per_meur"]
    assert gi["year"].tolist() == [2025] and gi["value"].item() == pytest.approx(6.0)


def test_custom_library_extra(tmp_path):
    extra = tmp_path / "extra.csv"
    extra.write_text("kpi_id,name,pillar,unit,direction,kind,min,max,numerator,denominator,scale,esrs,gri,definition\n"
                     "volunteer_hours,Employee volunteering hours,S,h,higher_better,sum,0,,,,,,,Company choice\n")
    lib = load_library(extra=extra)
    rep = build_report(pd.DataFrame({"kpi_id": ["volunteer_hours"] * 2, "year": [2024, 2025], "value": [100, 140]}), lib)
    r = rep.summary.iloc[0]
    assert r["status"] == "improved" and "check data 2025" in r["flags"]   # +40 % > 25 % swing threshold


def test_cli_report_and_chart(tmp_path, capsys):
    log = tmp_path / "log.csv"
    assert cli_main(["kpis", "example", str(log)]) == 0
    md, chart = tmp_path / "kpis.md", tmp_path / "kpis.png"
    assert cli_main(["kpis", "report", str(log), "--markdown", str(md), "--chart", str(chart),
                     "--csv", str(tmp_path / "s.csv"), "--changes", str(tmp_path / "c.csv")]) == 0
    text = md.read_text()
    assert "Gross Scope 1 GHG emissions" in text and "### Incomplete" in text
    assert chart.stat().st_size > 10_000
    assert cli_main(["kpis", "library", "water"]) == 0
    assert "water_consumption_m3" in capsys.readouterr().out
    bad = tmp_path / "bad.csv"
    bad.write_text("kpi_id,year,value\nunknown_kpi,2024,1\n")
    assert cli_main(["kpis", "report", str(bad)]) == 2
