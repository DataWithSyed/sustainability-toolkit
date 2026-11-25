# Changelog

## 0.1.0 - 2026-11-25

First release.

- Loaders for Excel workbooks and CSV folders (`topics`, `survey`, `weights`) with schema validation that reports every problem at once.
- ESRS topical standards taxonomy (E1-E5, S1-S4, G1, sub-topics from ESRS 1 AR 16) and entity-specific topics.
- Double materiality scoring: ESRS 1 severity criteria, likelihood for potential impacts, human-rights severity precedence, financial magnitude x likelihood.
- Stakeholder survey aggregation by group with explicit weights, mean/median, rating-scale rescaling and blending into the assessment.
- Static matrix plot (matplotlib) with quadrants, thresholds, E/S/G colours and overlap-avoiding labels; interactive Plotly HTML matrix.
- Classic two-axis (stakeholder importance vs business impact) sheet import and plot.
- CLI: `materiality build | validate | classic | example | template`; CSV and Markdown exports.
- Fictional example dataset and generator script.
