# Changelog

## 0.4.0 - 2026-11-27

- **New module `sustainkit.kpis`**: KPI library and multi-year E/S/G data log.
  - Bundled library of 24 KPIs (unit, pillar, direction, kind, allowed range) with ESRS Set 1 disclosure-requirement and GRI disclosure references; three derived ratios (GHG intensity, energy intensity, TRIR per 1 000 000 hours). Custom or extra KPI files supported. Simplified-ESRS mapping reported as not done yet.
  - Data log loader for long or wide CSV/Excel; validation that lists every problem (unknown or derived KPIs entered, bad years, non-numeric values, duplicates, out-of-range values, unit mismatch; no silent unit conversion).
  - Report: year-on-year change only between consecutive years (gaps reported as incomplete), percentage points for shares, direction-aware status, CAGR, "check data" flag above a 25 % change (tool choice), derived KPIs only when all inputs exist, "All sites" totals for additive KPIs only.
  - Small-multiple chart (PNG), Markdown/CSV exports, `sustainkit kpis library|report|example`, fictional 2022-2025 example log for Example Manufacturing Co.
- `sustainkit modules` lists kpis as available. 8 new tests (80 in total).

## 0.3.0 - 2026-11-26

- **New module `sustainkit.stakeholders`**: stakeholder register and map.
  - Register loader (CSV/Excel) with validation that lists every problem (missing columns, duplicates, ratings outside the scale, unknown categories, bad dates).
  - Influence x interest classification into Manage closely / Keep satisfied / Keep informed / Monitor; cut-off, names and review intervals are documented tool choices.
  - Optional ESRS 1 para 22-23 stakeholder category (affected stakeholders, users of sustainability statements, both).
  - Engagement plan: next due date from last engagement and the strategy interval (or a per-row interval), status overdue / due soon / ok / never engaged.
  - Group weights for the materiality survey (`salience`, `influence`, `interest`, `mean`, `equal`; mean over groups = 1; mean not sum, so head-count does not add weight) and a group-name check against a survey.
  - Map chart (PNG), Markdown/CSV export, `sustainkit stakeholders map|example`, fictional example register for Example Manufacturing Co. (15 stakeholders, the 6 survey groups).
- `sustainkit modules` now lists stakeholders as available. 8 new tests (72 in total).

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
