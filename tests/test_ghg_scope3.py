import pandas as pd
import pytest

from sustainkit.cli import main as sk_main
from sustainkit.ghg import calculate, load_scope3_factors
from sustainkit.ghg.cli import example_activities_path, example_path
from sustainkit.ghg.plot import plot_scope123
from sustainkit.ghg.scope3 import (
    Scope3Error,
    commuting_trips,
    fuel_and_energy,
    haversine_km,
    lookup_travel,
    scope3_inventory,
    travel,
)


@pytest.fixture(scope="module")
def fs3():
    return load_scope3_factors()


def trip(**kw):
    base = {"category": 6, "activity": "National rail", "quantity": 1000.0, "unit": "passenger.km"}
    base.update(kw)
    return pd.DataFrame([base])


def test_scope3_factors_match_published_2025_values(fs3):
    # spot checks against the UK Government 2025 flat file (v1)
    row, _ = lookup_travel(fs3, "Long-haul, to/from UK", "passenger.km", level4="Economy class")
    assert row["variant"] == "Without RF"  # default for the inventory figure
    row, _ = lookup_travel(fs3, "National rail", "passenger.km")
    assert row["kg_co2e"] == pytest.approx(0.03546)
    row, _ = lookup_travel(fs3, "Medium car", "km", level2="Cars (by size)", variant="Diesel")
    assert row["kg_co2e"] == pytest.approx(0.17174)
    row, _ = lookup_travel(fs3, "Germany", "nights")
    assert row["kg_co2e"] == pytest.approx(13.2)
    row, _ = lookup_travel(fs3, "Homeworking (office equipment + heating)", "FTE hours")
    assert row["kg_co2e"] == pytest.approx(0.33378)
    t = fs3.table
    assert not t.duplicated(["level1", "level2", "level3", "level4", "variant", "unit"]).any()
    assert set(t["scope"]) == {"Scope 3"}


def test_travel_adds_wtt_and_ev_td(fs3):
    r = travel(trip(), fs3)
    assert list(r.rows["component"]) == ["activity", "WTT"]
    assert r.total_t() * 1000 == pytest.approx(1000 * (0.03546 + 0.00897))
    ev = travel(trip(activity="Medium car", unit="km", level2="Cars (by size)", variant="Battery Electric Vehicle"), fs3)
    comps = dict(zip(ev.rows["component"], ev.rows["factor_kg_co2e"]))
    assert comps == pytest.approx({"activity": 0.03882, "WTT": 0.01022, "T&D losses": 0.00368})
    no_wtt = travel(trip(), fs3, include_wtt=False)
    assert len(no_wtt.rows) == 1


def test_flights_rf_memo_and_travellers(fs3):
    r = travel(trip(activity="Short-haul, to/from UK", quantity=1000, unit="km", level4="Economy class", travellers=3), fs3)
    act = r.rows[r.rows["component"] == "activity"].iloc[0]
    assert act["quantity_in_factor_unit"] == 3000
    t = fs3.table
    with_rf = t[(t["level3"] == "Short-haul, to/from UK") & (t["level4"] == "Economy class") & (t["variant"] == "With RF")]
    assert act["rf_memo_kg_co2e"] == pytest.approx(3000 * with_rf["kg_co2e"].sum())
    assert r.rf_memo_t > r.total_t()  # RF memo larger and not in the total
    # car km are per vehicle: travellers do not multiply
    car = travel(trip(activity="Medium car", unit="km", level2="Cars (by size)", variant="Petrol", travellers=3), fs3)
    assert car.rows.iloc[0]["quantity_in_factor_unit"] == 1000
    assert any("travellers ignored" in w for w in car.warnings)


def test_travel_validation_collects_all_problems(fs3):
    bad = pd.concat([
        trip(category=3),
        trip(quantity=-1),
        trip(activity="Teleporter"),
        trip(activity="Homeworking (office equipment + heating)", unit="FTE hours"),
        trip(activity="Atlantis", unit="nights"),
    ], ignore_index=True)
    with pytest.raises(Scope3Error) as e:
        travel(bad, fs3)
    assert len(e.value.problems) == 5
    with pytest.raises(Scope3Error):
        travel(pd.DataFrame({"activity": ["x"]}), fs3)


def test_commuting_survey_conversion():
    s = pd.DataFrame([
        {"activity": "Medium car", "level2": "Cars (by size)", "variant": "Petrol", "employees": 10, "one_way_km": 20, "occupancy": 2},
        {"activity": "National rail", "employees": 5, "one_way_km": 30, "days_per_year": 100},
    ])
    t = commuting_trips(s, days_per_year=200, homeworking_fte_hours=750)
    assert list(t["quantity"]) == [10 * 20 * 2 * 200 / 2, 5 * 30 * 2 * 100, 750]
    assert list(t["unit"]) == ["km", "passenger.km", "per FTE Working Hour"]
    r = travel(t)
    assert set(r.rows["category"]) == {7}
    assert "Homeworking" in set(r.rows["subcategory"])
    with pytest.raises(Scope3Error):
        commuting_trips(s.drop(columns="days_per_year"))  # no office days anywhere


def test_category3_from_inventory(fs3):
    acts = pd.DataFrame([
        {"activity": "Electricity: UK", "quantity": 1000, "unit": "kWh"},
        {"activity": "Natural gas", "quantity": 1000, "unit": "kWh (Gross CV)"},
        {"activity": "R410A", "quantity": 1, "unit": "kg", "variant": "Emissions including only Kyoto products"},
        {"activity": "District heat and steam", "quantity": 100, "unit": "kWh"},
    ])
    r = fuel_and_energy(calculate(acts), fs3)
    by = r.rows.groupby("subcategory")["kg_co2e"].sum()
    assert by["(a) WTT of Scope 1 fuels"] == pytest.approx(1000 * 0.03021)
    assert by["(b) WTT of purchased electricity/heat"] == pytest.approx(1000 * 0.04590 + 100 * 0.03341)
    assert by["(c) T&D losses (incl. WTT)"] == pytest.approx(1000 * (0.01853 + 0.00397) + 100 * (0.00945 + 0.00176))
    assert not r.incomplete  # refrigerant skipped silently (no upstream by nature)


def test_example_inventory_and_outputs(tmp_path):
    d = example_path("trips.csv").parent
    inv = calculate(pd.read_csv(example_activities_path()))
    r = scope3_inventory(pd.read_csv(d / "trips.csv"), inv, pd.read_csv(d / "commuting_survey.csv"),
                         homeworking_fte_hours=41250, period="2025")
    assert r.total_t(3) == pytest.approx(263.31, abs=0.01)
    assert r.total_t(6) == pytest.approx(18.09, abs=0.01)
    assert r.total_t(7) == pytest.approx(491.74, abs=0.01)
    assert r.rf_memo_t == pytest.approx(10.10, abs=0.01)
    md = r.to_markdown()
    assert "Memo: flights incl. radiative forcing" in md
    fig = plot_scope123(r, inv, tmp_path / "s3.png")
    assert (tmp_path / "s3.png").stat().st_size > 10_000
    import matplotlib.pyplot as plt

    plt.close(fig)


def test_cli_scope3(tmp_path, capsys):
    assert sk_main(["ghg", "scope3-example", str(tmp_path / "ex")]) == 0
    rc = sk_main([
        "ghg", "scope3", "--trips", str(tmp_path / "ex" / "trips.csv"), "--commuting", str(tmp_path / "ex" / "commuting_survey.csv"),
        "--inventory", str(tmp_path / "ex" / "activities.csv"), "--markdown", str(tmp_path / "s3.md"),
    ])
    assert rc == 0 and (tmp_path / "s3.md").exists()
    assert "Cat 6 Business travel" in capsys.readouterr().out
    assert sk_main(["ghg", "scope3"]) == 2  # nothing to calculate


def test_haversine_known_distance():
    # London Heathrow (51.4700, -0.4543) to New York JFK (40.6413, -73.7781): about 5,540 km great circle
    assert haversine_km(51.4700, -0.4543, 40.6413, -73.7781) == pytest.approx(5540, abs=15)
