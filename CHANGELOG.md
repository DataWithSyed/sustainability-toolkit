# Changelog

## 0.2.0 - 2026-11-25

The project is now **sustainkit**, a broader sustainability management toolkit
(repository renamed from `materiality-matrix` to `sustainability-toolkit`; GitHub redirects the old URL).

- New umbrella package `sustainkit` with a module registry (`sustainkit modules`) and a single CLI.
- Double materiality moved to `sustainkit.materiality` (unchanged behaviour). `import materiality` and the `materiality` command still work.
- **New module `sustainkit.ghg`**: Scope 1 and 2 inventory.
  - Bundled UK Government GHG Conversion Factors 2025 (flat file v1, OGL v3.0): 970 Scope 1, Scope 2 and outside-of-scopes factors with the CO2/CH4/N2O split, plus a rebuild script.
  - Factor search and lookup with unit aliases, MWh/GWh and kg-to-tonnes conversion, and clear errors for ambiguous matches (e.g. plain kWh vs gross/net CV).
  - Location-based and market-based Scope 2; market-based reported as incomplete when a contractual factor is missing.
  - Biogenic CO2 reported outside the scopes.
  - Summaries by scope, site, period, category and gas; Markdown/CSV export; stacked bar chart; `sustainkit ghg calc|factors|example`.
  - Fictional example activity data.
- New docs: GHG method, module map; README and ROADMAP rewritten for the toolkit.

## 0.1.0 - 2026-11-25

First release (as `materiality-matrix`).

- Loaders for Excel workbooks and CSV folders (`topics`, `survey`, `weights`) with schema validation that reports every problem at once.
- ESRS topical standards taxonomy (E1-E5, S1-S4, G1, sub-topics from ESRS 1 AR 16) and entity-specific topics.
- Double materiality scoring: ESRS 1 severity criteria, likelihood for potential impacts, human-rights severity precedence, financial magnitude x likelihood.
- Stakeholder survey aggregation by group with explicit weights, mean/median, rating-scale rescaling and blending into the assessment.
- Static matrix plot (matplotlib) and interactive Plotly HTML matrix.
- Classic two-axis sheet import and plot; CLI; CSV and Markdown exports; fictional example dataset.
