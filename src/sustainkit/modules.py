"""Registry of toolkit modules and their status (shown by ``sustainkit modules``)."""

MODULES = [
    # name, status, summary
    ("materiality", "available", "Double materiality assessment, stakeholder survey weighting, matrix plots"),
    ("ghg", "available", "Scope 1 and 2 inventory with UK Government 2025 emission factors"),
    ("stakeholders", "planned", "Stakeholder mapping (influence x interest), engagement and communication plans"),
    ("kpis", "planned", "KPI library, multi-year E/S/G data logs, year-on-year change, targets"),
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
