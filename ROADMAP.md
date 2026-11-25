# Roadmap

`sustainkit` grows by one feature at a time, each a self-contained release
with tests and docs. Order may change with feedback; suggestions are welcome
in issues. Planned modules are listed in the README.

## ghg (available: Scope 1 and 2)
1. Scope 3 categories 1-15 scaffolding with spend- and activity-based methods (sourced factors only).
2. Scope 3 business travel and employee commuting (UK 2025 Scope 3 factors).
3. Well-to-tank and transmission-and-distribution factors (UK 2025).
4. Multi-year factor sets (2023-2025) and automatic year selection by period.
5. Intensity metrics (t CO2e per revenue, FTE, unit produced) and base-year recalculation.
6. Data-quality scores per activity row and an uncertainty range for totals.
7. Custom country grid factors from cited public sources.
8. Excel inventory export with factor audit trail.

## materiality (available)
9. IRO register (impacts, risks, opportunities) rolled up to topics.
10. Monte-Carlo sensitivity: probability each topic is material.
11. Alternative severity rules (ESRS 1 AR 11), time-horizon and value-chain views.
12. Simplified ESRS taxonomy option; year-over-year movement arrows.
13. Survey importers (wide format, Google/Microsoft Forms exports) and quality checks.
14. Rule-based (LLM-free) mapping of free-text topics to ESRS topics.

## stakeholders
15. Stakeholder register and influence x interest map (plot + quadrant strategies).
16. Engagement plan and communication plan tables with schedule export.
17. Link stakeholder groups to materiality survey weights.

## kpis
18. KPI library (E/S/G) with units, definitions and ESRS/GRI references.
19. Multi-year data log with year-on-year change, validation and charts.
20. Targets and trajectories (linear and science-based-style paths, labelled as tool choices).
21. KPI selection scoring (relevance, measurability, data availability).

## energy
22. Energy baseline from meter/bill data, normalised by degree days.
23. Saving-measure appraisal: simple payback, NPV, IRR.
24. Marginal abatement cost curve combining energy and GHG modules.

## water
25. Site water balance (withdrawal, consumption, discharge) and intensity.
26. Water-stress flagging from user-supplied, cited basin data.

## circularity, impact, social, governance, checklists
27. Generic checklist engine (status, evidence, owner, completeness, gap list).
28. Circular-economy self-assessment scoring by life-cycle stage.
29. Environmental impact screening (inputs/outputs, severity, improvement priorities).
30. Social / human-rights due-diligence checklist scoring.
31. ESG governance maturity score with radar chart.

## supplychain
32. Supplier register with risk screening by country and commodity (cited indices only).
33. Supplier engagement tracker.

## actions, risk, regwatch
34. Action plan / initiative tracker with owners, deadlines and expected impact.
35. Sustainability risk register with likelihood x impact heatmap.
36. Trend (PESTLE-style) analysis table and chart.
37. Regulatory watchlist with deadlines, applicability tests and calendar export.

## disclosure and reporting
38. ESRS disclosure-requirement index with completeness tracking.
39. GRI content index generator.
40. Word (.docx) report export across modules.
41. PDF and slide export.
42. Excel workbook export with all module outputs.

## app and engineering
43. Streamlit app over all modules.
44. YAML/TOML project config to run every module in one command.
45. Docs site with tutorials and notebook gallery.
46. JSON Schemas for all inputs.
47. PyPI release.
