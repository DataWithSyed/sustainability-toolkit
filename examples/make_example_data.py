"""Generate the bundled example assessment.

ALL DATA HERE IS FICTIONAL. The company ("Example Manufacturing Co."), its
assessment scores and every survey answer are invented for demonstration.
Topic names follow the ESRS 1 AR 16 list of sustainability matters.

Run from the repository root:  python examples/make_example_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "src" / "materiality" / "data" / "example"
SEED = 2026

# topic_id, topic, esrs, subtopic, impact_type, scale, scope, irremediability,
# impact_likelihood, human_rights, fin_magnitude, fin_likelihood, time_horizon, value_chain
TOPICS = [
    ("E1-MIT", "GHG emissions from operations and energy use", "E1", "Climate change mitigation", "actual_negative", 4, 4, 4, None, False, 4, 0.9, "short", "own_operations"),
    ("E1-ADA", "Physical climate risk to plants", "E1", "Climate change adaptation", "potential_negative", 3, 2, 3, 0.5, False, 4, 0.6, "long", "own_operations"),
    ("E1-ENE", "Energy consumption and efficiency", "E1", "Energy", "actual_negative", 3, 3, 2, None, False, 4, 0.8, "short", "own_operations"),
    ("E2-AIR", "Air emissions from coating lines", "E2", "Pollution of air", "actual_negative", 3, 2, 2, None, False, 2, 0.5, "medium", "own_operations"),
    ("E2-SOC", "Substances of concern in products", "E2", "Substances of concern", "potential_negative", 4, 3, 3, 0.4, False, 3, 0.6, "medium", "downstream"),
    ("E3-WAT", "Water withdrawal in water-stressed sites", "E3", "Water", "actual_negative", 3, 2, 3, None, False, 2, 0.4, "medium", "own_operations"),
    ("E4-LND", "Land use and biodiversity near sites", "E4", "Direct impact drivers of biodiversity loss", "potential_negative", 2, 2, 4, 0.3, False, 1, 0.3, "long", "own_operations"),
    ("E5-INF", "Virgin metal and plastic inputs", "E5", "Resources inflows, including resource use", "actual_negative", 3, 4, 3, None, False, 3, 0.7, "medium", "upstream"),
    ("E5-WST", "Production waste and scrap", "E5", "Waste", "actual_negative", 2, 2, 2, None, False, 2, 0.6, "short", "own_operations"),
    ("S1-HS", "Occupational health and safety", "S1", "Working conditions", "potential_negative", 5, 3, 5, 0.4, True, 3, 0.5, "short", "own_operations"),
    ("S1-EQ", "Gender equality and equal pay", "S1", "Equal treatment and opportunities for all", "actual_negative", 3, 3, 2, None, False, 2, 0.5, "medium", "own_operations"),
    ("S1-TRN", "Training and skills development", "S1", "Equal treatment and opportunities for all", "actual_positive", 3, 3, None, None, False, 3, 0.6, "medium", "own_operations"),
    ("S2-FOR", "Forced labour risk in raw-material supply", "S2", "Other work-related rights", "potential_negative", 5, 3, 5, 0.2, True, 3, 0.4, "medium", "upstream"),
    ("S3-COM", "Local community nuisance (noise, traffic)", "S3", "Communities' economic, social and cultural rights", "actual_negative", 2, 2, 1, None, False, 1, 0.4, "short", "own_operations"),
    ("S4-PRI", "Customer data privacy", "S4", "Information-related impacts for consumers and/or end-users", "potential_negative", 3, 3, 2, 0.3, False, 3, 0.4, "short", "downstream"),
    ("S4-SAF", "Product safety for end-users", "S4", "Personal safety of consumers and/or end-users", "potential_negative", 4, 3, 4, 0.2, False, 5, 0.4, "short", "downstream"),
    ("G1-COR", "Corruption and bribery", "G1", "Corruption and bribery", "potential_negative", 3, 2, 2, 0.2, False, 4, 0.3, "medium", "own_operations"),
    ("G1-WHB", "Protection of whistle-blowers", "G1", "Protection of whistle-blowers", "potential_negative", 2, 2, 2, 0.3, False, 2, 0.3, "medium", "own_operations"),
    ("G1-SUP", "Supplier relationships and payment practices", "G1", "Management of relationships with suppliers including payment practices", "actual_negative", 2, 3, 1, None, False, 2, 0.5, "short", "upstream"),
]
COLS = [
    "topic_id", "topic", "esrs", "subtopic", "impact_type", "scale", "scope", "irremediability",
    "impact_likelihood", "human_rights", "fin_magnitude", "fin_likelihood", "time_horizon", "value_chain",
]

# group: (respondents, weight, impact bias, financial bias, response rate)
GROUPS = {
    "Employees": (12, 1.0, 0.2, 0.0, 0.9),
    "Customers": (8, 1.0, 0.0, 0.2, 0.8),
    "Investors": (5, 1.0, -0.2, 0.4, 0.85),
    "Suppliers": (6, 0.75, -0.1, 0.1, 0.7),
    "Local community": (6, 1.0, 0.3, -0.3, 0.75),
    "NGOs": (4, 0.75, 0.6, -0.2, 0.8),
}


def main() -> None:
    rng = np.random.default_rng(SEED)
    topics = pd.DataFrame(TOPICS, columns=COLS)
    topics["description"] = "Fictional example topic."

    # a latent "true" view per topic drives the fake survey answers
    sev = topics[["scale", "scope", "irremediability"]].mean(axis=1)
    latent_imp = sev.to_numpy(float)
    latent_fin = (topics["fin_magnitude"] * (0.5 + topics["fin_likelihood"])).clip(1, 5).to_numpy(float)

    rows = []
    for group, (n, _w, bi, bf, rate) in GROUPS.items():
        for r in range(n):
            rid = f"{group[:3].upper()}-{r + 1:02d}"
            for k, tid in enumerate(topics["topic_id"]):
                if rng.random() > rate:
                    continue
                imp = latent_imp[k] + bi + rng.normal(0, 0.8)
                fin = latent_fin[k] + bf + rng.normal(0, 0.8)
                rows.append(
                    {
                        "respondent_id": rid,
                        "stakeholder_group": group,
                        "topic_id": tid,
                        "impact_rating": int(np.clip(round(imp), 1, 5)),
                        "financial_rating": int(np.clip(round(fin), 1, 5)),
                    }
                )
    survey = pd.DataFrame(rows)
    weights = pd.DataFrame({"stakeholder_group": list(GROUPS), "weight": [g[1] for g in GROUPS.values()]})
    about = pd.DataFrame(
        {
            "about": [
                "FICTIONAL EXAMPLE DATA - not a real company, assessment or survey.",
                "Company: Example Manufacturing Co. (invented).",
                "Topic names follow ESRS 1 AR 16; all scores and answers are invented.",
                f"Generated by examples/make_example_data.py with seed {SEED}.",
            ]
        }
    )
    OUT.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT / "example_assessment.xlsx") as xw:
        about.to_excel(xw, sheet_name="about", index=False)
        topics.to_excel(xw, sheet_name="topics", index=False)
        survey.to_excel(xw, sheet_name="survey", index=False)
        weights.to_excel(xw, sheet_name="weights", index=False)
    csv_dir = OUT / "csv"
    csv_dir.mkdir(exist_ok=True)
    topics.to_csv(csv_dir / "topics.csv", index=False)
    survey.to_csv(csv_dir / "survey.csv", index=False)
    weights.to_csv(csv_dir / "weights.csv", index=False)
    classic = pd.DataFrame(
        {
            "ESG Issue": ["Climate Change", "Data Privacy", "Labor Standards", "Diversity", "Water Use", "Business Ethics"],
            "Stakeholder Importance (1-10)": [9, 6, 7, 6, 5, 7],
            "Business Impact (1-10)": [8, 7, 5, 4, 3, 6],
            "Priority": ["", "", "", "", "", ""],
        }
    )
    classic.to_csv(OUT / "classic_matrix.csv", index=False)
    print(f"topics={len(topics)} survey rows={len(survey)} respondents={survey.respondent_id.nunique()}")


if __name__ == "__main__":
    main()
