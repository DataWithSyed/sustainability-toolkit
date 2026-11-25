import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest


@pytest.fixture
def topics():
    return pd.DataFrame(
        {
            "topic_id": ["A", "B", "C", "D"],
            "topic": ["Climate", "Safety", "Training", "Bribery"],
            "esrs": ["E1", "S1", "S1", "G1"],
            "impact_type": ["actual_negative", "potential_negative", "actual_positive", "potential_negative"],
            "scale": [4, 5, 3, 3],
            "scope": [4, 3, 3, 2],
            "irremediability": [4, 4, None, 1],
            "impact_likelihood": [None, 0.5, None, 0.2],
            "human_rights": [False, True, False, False],
            "fin_magnitude": [4, 3, 2, 5],
            "fin_likelihood": [1.0, 0.5, 0.5, 0.2],
        }
    )


@pytest.fixture
def survey():
    rows = []
    for g, n in (("Employees", 3), ("Investors", 1)):
        for r in range(n):
            for t in "ABCD":
                rows.append(
                    {
                        "respondent_id": f"{g}-{r}",
                        "stakeholder_group": g,
                        "topic_id": t,
                        "impact_rating": 5 if g == "Employees" else 1,
                        "financial_rating": 3,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def weights():
    return pd.DataFrame({"stakeholder_group": ["Employees", "Investors"], "weight": [1.0, 1.0]})
