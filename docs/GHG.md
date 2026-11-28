# `sustainkit.ghg`: Scope 1 and 2 inventory (Scope 3: see GHG_SCOPE3.md)

## What it does

`calculate()` multiplies each activity (fuel burned, distance driven,
refrigerant leaked, electricity bought...) by a published emission factor and
sums the results by scope:

- **Scope 1** (direct): fuels, bioenergy, owned vehicles, refrigerants and other process gases.
- **Scope 2** (purchased electricity, heat and steam), reported two ways
  (GHG Protocol Scope 2 Guidance, 2015):
  - *location-based*: the grid-average factor from the factor table;
  - *market-based*: a contractual factor you supply per row in `market_factor`
    (kg CO2e/kWh; for example 0 for electricity backed by certificates, or a
    supplier-specific factor). No residual-mix factor is bundled, so if any
    Scope 2 row lacks a `market_factor` the market-based total is reported as
    **incomplete** instead of being estimated.
- **Biogenic CO2** from bioenergy (wood pellets, biodiesel, the biofuel share
  of forecourt diesel...) is reported separately as "outside of scopes", using
  the published outside-of-scopes factor for the same fuel and unit. Where no
  such factor exists for that unit (e.g. kWh on a gross/net CV basis), it is left blank.
- Where the factor table splits CO2, CH4 and N2O, the split is carried through (`inv.gases()`).

Scope 3 categories 3 (fuel- and energy-related: WTT and T&D), 6 (business travel)
and 7 (employee commuting) are covered by `sustainkit.ghg.scope3`, added in 0.5.0:
see [GHG_SCOPE3.md](GHG_SCOPE3.md). Other Scope 3 categories are on the [ROADMAP](../ROADMAP.md).

## Factor table

Bundled: **UK Government GHG Conversion Factors for Company Reporting 2025**,
flat file, version 1, published by the Department for Energy Security and Net
Zero (produced by Ricardo Energy & Environment and Aether Ltd), Open
Government Licence v3.0.
<https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025>

- 970 factors: Scope 1 (843), Scope 2 (71) and outside of scopes (56). The
  SECR kWh-per-km rows and all Scope 3 rows are left out.
- Values are copied unchanged: kg CO2e per unit, plus kg CO2e of CO2, CH4 and
  N2O where published. The tests check several of them against the published values.
- GWPs: the 2025 methodology paper says most factors use IPCC AR5 GWP100
  values, with exceptions listed in its Table 1.
- The UK electricity factor is a UK grid average. For other countries, load a
  custom factor CSV with the same columns (`load_factors("my_factors.csv")`)
  from a source you cite.
- Rebuild from the official file: `python examples/build_uk_ghg_factors.py`.

Spot values (2025, kg CO2e per unit):

| Activity | Unit | kg CO2e |
|---|---|---|
| Natural gas | kWh (Gross CV) | 0.18296 |
| Diesel (average biofuel blend) | litres | 2.57082 |
| Electricity: UK (generation) | kWh | 0.17700 |
| R410A (Kyoto products only) | kg | 1924 |

## Activity data

| column | required | notes |
|---|---|---|
| `activity` | yes | factor name (the table's `level3`, e.g. `Natural gas`, `Electricity: UK`, `Medium car`, `R410A`) or a `factor_id` |
| `quantity` | yes | number >= 0 |
| `unit` | yes | factor unit; `m3`, `l`, `t` aliases; `MWh`/`GWh` -> kWh; `kg` -> tonnes |
| `level1`, `level2`, `level4`, `variant` | if ambiguous | e.g. `level2=Cars (by size)`, `variant=Diesel` |
| `market_factor` | no | kg CO2e/kWh for market-based Scope 2 |
| `site`, `period`, `id`, `note` | no | for grouping and traceability |

Plain `kWh` is rejected for fuels that have both gross and net calorific-value
factors: say `kWh (Gross CV)` or `kWh (Net CV)` (energy bills in the UK are
usually on a gross basis). Every problem in a file is listed in one error.

Find the right activity name with `sustainkit ghg factors <words>` or `load_factors().search("...")`.

## Sources

1. DESNZ, *UK Government GHG Conversion Factors for Company Reporting 2025*, flat file v1, and the 2025 methodology paper.
2. WRI/WBCSD, *The Greenhouse Gas Protocol: A Corporate Accounting and Reporting Standard*, revised edition (2004).
3. WRI, *GHG Protocol Scope 2 Guidance* (2015).
