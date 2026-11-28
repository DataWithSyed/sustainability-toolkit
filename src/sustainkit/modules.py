"""Registry of toolkit modules and their status (shown by ``sustainkit modules``)."""

MODULES = [
    # name, status, summary
    ("materiality", "available", "Double materiality assessment, stakeholder survey weighting, matrix plots"),
    ("ghg", "available", "Scope 1-2 inventory + Scope 3 cat 3/6/7 (WTT, T&D, travel, commuting), UK Gov 2025 factors"),
    ("stakeholders", "available", "Stakeholder register, influence x interest map, engagement plan, survey weights"),
    ("kpis", "available", "KPI library (ESRS/GRI references), multi-year E/S/G data log, year-on-year change, charts"),
    ("energy", "planned", "Energy audit: baseline, saving measures, payback/NPV, abatement cost curve"),
    ("water", "planned", "Water balance, intensity metrics and practice checklist scoring"),
    ("circularity", "planned", "Circular economy self-assessment across the product life cycle"),
    ("impact", "planned", "Environmental impact screening: inputs/outputs inventory and severity"),
    ("supplychain", "planned", "Supplier risk screening and ethical sourcing workflow"),
    ("social", "planned", "Social responsibility and human-rights due-diligence checklists"),
    ("governance", "planned", "ESG governance maturity scoring"),
    ("checklists", "planned", "Generic checklist engine: status, evidence, completeness, gap lists"),
    ("actions", "planned", "Action plans and initiative tracker with owners, deadlines and impact"),
    ("risk", "planned", "Sustainability risk register and trend (PESTLE-style) analysis"),
    ("regwatch", "planned", "Regulatory watchlist with deadlines and applicability"),
    ("disclosure", "planned", "ESRS / GRI disclosure index and reporting completeness"),
    ("reporting", "planned", "Report export (Word, PDF, Excel, slides)"),
    ("app", "planned", "Streamlit app over all modules"),
]
