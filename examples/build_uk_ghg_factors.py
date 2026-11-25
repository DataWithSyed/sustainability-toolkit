"""Rebuild the bundled UK Government GHG conversion factor table (Scope 1, 2, outside of scopes).

Source: UK Government GHG Conversion Factors for Company Reporting 2025,
flat file, version 1 (DESNZ; produced by Ricardo Energy & Environment and
Aether Ltd). Open Government Licence v3.0.
https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025

Usage:  python examples/build_uk_ghg_factors.py [path-to-flat-file.xlsx]
Without a path the flat file is downloaded.
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://assets.publishing.service.gov.uk/media/6846b6ea57f3515d9611f0dd/ghg-conversion-factors-2025-flat-format.xlsx"
OUT = Path(__file__).resolve().parents[1] / "src" / "sustainkit" / "ghg" / "data" / "uk_gov_ghg_2025_scope12.csv"
GAS = {
    "kg CO2e": "kg_co2e",
    "kg CO2e of CO2 per unit": "kg_co2",
    "kg CO2e of CH4 per unit": "kg_ch4_co2e",
    "kg CO2e of N2O per unit": "kg_n2o_co2e",
}


def build(src: Path) -> pd.DataFrame:
    df = pd.read_excel(src, sheet_name="Factors by Category", header=5)
    value_col = [c for c in df.columns if str(c).startswith("GHG Conversion Factor")][0]
    df = df[df["Scope"].isin(["Scope 1", "Scope 2", "Outside of Scopes"])]
    df = df[~df["Level 1"].astype(str).str.startswith("SECR")]
    df = df[df["GHG/Unit"].isin(GAS)]
    df = df.rename(
        columns={
            "Scope": "scope", "Level 1": "level1", "Level 2": "level2", "Level 3": "level3",
            "Level 4": "level4", "Column Text": "variant", "UOM": "unit",
        }
    )
    df["factor_id"] = df["ID"].astype(str).str.rsplit("_", n=1).str[0]
    df["gas"] = df["GHG/Unit"].map(GAS)
    keys = ["factor_id", "scope", "level1", "level2", "level3", "level4", "variant", "unit"]
    df[keys] = df[keys].fillna("").astype(str).apply(lambda s: s.str.strip())
    wide = (
        df.pivot_table(index=keys, columns="gas", values=value_col, aggfunc="first")
        .reset_index()
        .dropna(subset=["kg_co2e", "kg_co2"], how="all")
    )
    wide.columns.name = None
    for c in GAS.values():
        if c not in wide.columns:
            wide[c] = pd.NA
    wide["scope"] = wide["scope"].replace({"Outside of Scopes": "Outside of scopes"})
    wide["source"] = "UK Gov GHG Conversion Factors 2025 v1 (OGL v3.0)"
    cols = keys + list(GAS.values()) + ["source"]
    return wide[cols].sort_values(["scope", "level1", "level2", "level3", "unit"]).reset_index(drop=True)


def main() -> None:
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    else:
        src = Path(tempfile.mkdtemp()) / "flat.xlsx"
        urllib.request.urlretrieve(URL, src)
    table = build(src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, float_format="%.10g")
    print(f"wrote {OUT} ({len(table)} factors)")
    print(table.groupby("scope").size().to_string())


if __name__ == "__main__":
    main()
