"""materiality: double materiality assessments and matrices in Python.

Load topic assessments and stakeholder survey data from Excel or CSV,
score impact and financial materiality in the style of ESRS 1 (CSRD),
and draw publication-quality and interactive materiality matrices.
"""

from materiality.io import (
    MaterialityData,
    load,
    load_classic_matrix,
    load_csv_dir,
    load_example,
    load_excel,
)
from materiality.schema import ValidationError, validate
from materiality.scoring import ScoringConfig, score, score_classic

__all__ = [
    "MaterialityData",
    "ScoringConfig",
    "ValidationError",
    "load",
    "load_classic_matrix",
    "load_csv_dir",
    "load_example",
    "load_excel",
    "score",
    "score_classic",
    "validate",
]

__version__ = "0.1.0"
