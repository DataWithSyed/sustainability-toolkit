# Roadmap

Planned additions, roughly in order. Each item is meant to be a self-contained
release with tests and docs. Order may change with feedback; suggestions welcome in issues.

## Assessment core
1. IRO register: impacts, risks and opportunities as separate rows linked to a topic, rolled up to topic scores (ESRS 1 chapter 3).
2. Alternative severity rules: max, weighted mean, and "any criterion" rule (ESRS 1 AR 11).
3. Time-horizon views: short / medium / long matrices and a horizon filter.
4. Value-chain views: upstream / own operations / downstream breakdown.
5. Gross vs net (before / after mitigation) scoring with a two-point arrow plot.
6. Simplified ESRS taxonomy option alongside ESRS Set 1.
7. Full ESRS AR 16 sub-sub-topics and entity-specific topic helpers.
8. GRI 3 and ISSB/SASB-style topic crosswalk tables (sourced).
9. Year-over-year comparison: movement arrows between two assessments.
10. Threshold calibration helpers: show how many topics are material at each threshold.

## Uncertainty and robustness
11. Monte-Carlo sensitivity: sample ratings and weights, report the probability each topic is material.
12. Bootstrap confidence ellipses for survey-driven scores.
13. Tornado chart: which input moves each topic's rank most.
14. Stakeholder-weight sensitivity sweep and "what weights would flip this topic" solver.
15. Inter-rater agreement statistics (e.g. Krippendorff's alpha) per topic and group.

## Surveys
16. Wide-format survey import (one column per topic) and auto-reshape.
17. Importers for exported Google Forms / Microsoft Forms / SurveyMonkey / Qualtrics CSVs.
18. Survey response-quality checks: straight-lining, speeders, missing-ness.
19. Survey design helper: generate a questionnaire from the topic list.

## Text and mapping (rule-based, no LLM)
20. Map free-text topic names to ESRS topics with keyword and fuzzy matching, with scores and explanations.
21. Map an existing risk register to ESRS topics.
22. Glossary of ESRS terms with sources.

## Outputs
23. Streamlit app: upload a workbook, tune thresholds and weights live, download outputs.
24. Report export to Word (.docx) with matrix, ranked table and method appendix.
25. Report export to PDF.
26. PowerPoint slide export of the matrix.
27. Excel export with formatted scores and a matrix chart sheet.
28. Plot themes (print, dark, colour-blind-safe) and bubble-size options.
29. Label strategies: numbered markers with side legend for dense matrices.
30. Bar / lollipop charts by pillar and ESRS standard.
31. Heatmap of group-by-topic ratings.

## Benchmarks and data
32. Benchmarks against published CSRD sustainability statements: material topics by sector (from public reports, cited per report).
33. Sector starter topic lists with sources.
34. More example datasets (all clearly fictional) for different sectors.

## Engineering
35. JSON Schema for inputs and a `materiality schema` command.
36. Config files (YAML/TOML) for repeatable runs.
37. Documentation site with tutorials.
38. PyPI release and conda-forge recipe.
39. Type hints throughout and strict mypy.
40. Performance for large surveys (10k+ responses).
