import pandas as pd
import pytest

from sustainkit.cli import main as sk_main
from sustainkit.ghg import FactorError, FactorSet, InventoryError, calculate, load_factors
from sustainkit.ghg.cli import example_activities_path
from sustainkit.ghg.plot import plot_breakdown


@pytest.fixture(scope="module")
def fs():
    return load_factors()


def act(**kw):
    base = {"activity": "Natural gas", "quantity": 1000.0, "unit": "kWh (Gross CV)"}
    base.update(kw)
    return pd.DataFrame([base])


def test_bundled_factors_match_published_2025_values(fs):
    # spot checks against the UK Government 2025 flat file (v1)
    row, _ = fs.lookup("Natural gas", "kWh (Gross CV)")
    assert row["kg_co2e"] == pytest.approx(0.18296)
    assert row["kg_co2"] == pytest.approx(0.18259)
    row, _ = fs.lookup("Electricity: UK", "kWh")
    assert row["kg_co2e"] == pytest.approx(0.177) and row["scope"] == "Scope 2"
    row, _ = fs.lookup("Diesel (average biofuel blend)", "litres", level1="Fuels")
    assert row["kg_co2e"] == pytest.approx(2.57082)
    row, _ = fs.lookup("R410A", "kg", variant="Emissions including only Kyoto products")
    assert row["kg_co2e"] == pytest.approx(1924)
    assert fs.biogenic("Wood pellets", "tonnes") == pytest.approx(1677.18)


def test_factor_table_shape(fs):
    t = fs.table
    assert set(t["scope"]) == {"Scope 1", "Scope 2", "Outside of scopes"}
    assert len(t) > 900
    assert not t.duplicated(["scope", "level1", "level2", "level3", "level4", "variant", "unit"]).any()
    assert t["source"].str.contains("2025").all()


def test_simple_calculation(fs):
    inv = calculate(act(), fs)
    assert inv.rows.loc[0, "kg_co2e"] == pytest.approx(182.96)
    assert inv.scope1_t == pytest.approx(0.18296)
    gas = inv.rows.loc[0, ["kg_co2", "kg_ch4_co2e", "kg_n2o_co2e"]].sum()
    assert gas == pytest.approx(182.96, abs=0.01)


def test_unit_aliases_and_scaling(fs):
    a = calculate(act(activity="Electricity: UK", quantity=2, unit="MWh"), fs)
    assert a.rows.loc[0, "kg_co2e"] == pytest.approx(354.0)
    b = calculate(act(quantity=1, unit="m3"), fs)
    assert b.rows.loc[0, "factor_unit"] == "cubic metres"
    c = calculate(act(quantity=1, unit="MWh (Gross CV)"), fs)
    assert c.rows.loc[0, "kg_co2e"] == pytest.approx(182.96)
    d = calculate(act(quantity=500, unit="kg"), fs)  # kg -> tonnes factor
    assert d.rows.loc[0, "kg_co2e"] == pytest.approx(0.5 * 2575.46441)


def test_plain_kwh_is_ambiguous_for_fuels(fs):
    with pytest.raises(InventoryError, match="ambiguous"):
        calculate(act(unit="kWh"), fs)


def test_ambiguous_activity_needs_variant(fs):
    with pytest.raises(InventoryError, match="add level1/level2/level4/variant"):
        calculate(act(activity="Medium car", unit="km"), fs)
    inv = calculate(act(activity="Medium car", unit="km", level2="Cars (by size)", variant="Diesel"), fs)
    assert inv.rows.loc[0, "factor_kg_co2e"] == pytest.approx(0.17174)


def test_all_problems_collected(fs):
    df = pd.DataFrame(
        [
            {"activity": "Unobtainium", "quantity": 1, "unit": "kg"},
            {"activity": "Natural gas", "quantity": -5, "unit": "kWh (Gross CV)"},
            {"activity": "Natural gas", "quantity": "lots", "unit": "kWh (Gross CV)"},
            {"activity": "Natural gas", "quantity": 1, "unit": "barrels"},
        ]
    )
    with pytest.raises(InventoryError) as exc:
        calculate(df, fs)
    assert len(exc.value.problems) == 4


def test_missing_columns(fs):
    with pytest.raises(InventoryError, match="missing required"):
        calculate(pd.DataFrame({"activity": ["Natural gas"]}), fs)


def test_market_based_scope2(fs):
    df = pd.DataFrame(
        [
            {"activity": "Electricity: UK", "quantity": 1000, "unit": "kWh", "market_factor": 0.0},
            {"activity": "Electricity: UK", "quantity": 1000, "unit": "kWh", "market_factor": 0.3},
        ]
    )
    inv = calculate(df, fs)
    assert inv.scope2_location_t == pytest.approx(0.354)
    assert inv.scope2_market_t == pytest.approx(0.3)
    df.loc[1, "market_factor"] = None
    inv2 = calculate(df, fs)
    assert inv2.scope2_market_t is None
    assert any("market-based total incomplete" in w for w in inv2.warnings)


def test_biogenic_reported_outside_scopes(fs):
    inv = calculate(act(activity="Wood pellets", quantity=2, unit="tonnes"), fs)
    assert inv.scope1_t == pytest.approx(2 * 55.19389 / 1000)
    assert inv.biogenic_t == pytest.approx(2 * 1677.18 / 1000)


def test_example_inventory_hand_check(fs):
    inv = calculate(pd.read_csv(example_activities_path()), fs)
    assert inv.scope2_location_t == pytest.approx((2_100_000 + 650_000) * 0.177 / 1000)
    gas = (1_200_000 + 450_000) * 0.18296 / 1000
    assert inv.by("level3").loc["Natural gas", "total"] == pytest.approx(gas)
    assert inv.scope2_market_t is None  # one site has no contractual factor
    s = inv.summary()
    assert s.loc[s["item"] == "Scope 1 + 2 (location-based)", "t_co2e"].iloc[0] == pytest.approx(
        inv.scope1_t + inv.scope2_location_t
    )
    assert "incomplete" in inv.to_markdown()
    assert set(inv.gases().columns) == {"CO2", "CH4", "N2O"}


def test_search(fs):
    hits = fs.search("natural gas", unit="kWh (Gross CV)")
    assert len(hits) >= 1 and (hits["unit"] == "kWh (Gross CV)").all()
    assert fs.search("electricity", scope="Scope 2").shape[0] >= 1


def test_custom_factor_table(tmp_path):
    t = pd.DataFrame(
        [{"factor_id": "X1", "scope": "Scope 2", "level1": "Electricity", "level2": "Grid", "level3": "Grid DE",
          "level4": "", "variant": "", "unit": "kWh", "kg_co2e": 0.4}]
    )
    p = tmp_path / "f.csv"
    t.to_csv(p, index=False)
    fs = load_factors(p)
    inv = calculate(act(activity="Grid DE", unit="kWh", quantity=10), fs)
    assert inv.scope2_location_t == pytest.approx(0.004)
    with pytest.raises(ValueError):
        FactorSet(t.drop(columns=["kg_co2e"]))


def test_lookup_error_type(fs):
    with pytest.raises(FactorError):
        fs.lookup("Nothing", "kg")


def test_breakdown_chart(tmp_path, fs):
    inv = calculate(pd.read_csv(example_activities_path()), fs)
    out = tmp_path / "c.png"
    plot_breakdown(inv, out, by="site")
    assert out.stat().st_size > 10_000


def test_cli_ghg(tmp_path, capsys):
    rc = sk_main(["ghg", "calc", str(example_activities_path()), "--csv", str(tmp_path / "r.csv"),
                  "--markdown", str(tmp_path / "r.md"), "--chart", str(tmp_path / "r.png")])
    assert rc == 0
    assert len(pd.read_csv(tmp_path / "r.csv")) == 9
    assert sk_main(["ghg", "factors", "wood", "pellets"]) == 0
    assert sk_main(["ghg", "example", str(tmp_path / "a.csv")]) == 0
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"activity": ["x"], "quantity": [1], "unit": ["kg"]}).to_csv(bad, index=False)
    assert sk_main(["ghg", "calc", str(bad)]) == 2


def test_cli_modules_and_materiality_passthrough(capsys, tmp_path):
    assert sk_main(["modules"]) == 0
    out = capsys.readouterr().out
    assert "ghg" in out and "available" in out
    assert sk_main(["materiality", "example", str(tmp_path / "e.xlsx")]) == 0
