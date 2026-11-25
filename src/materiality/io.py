"""Loaders for Excel workbooks and CSV folders."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import pandas as pd

from materiality.schema import (
    ValidationError,
    check,
    normalise_survey,
    normalise_topics,
    normalise_weights,
)


@dataclass
class MaterialityData:
    """Validated inputs for one assessment."""

    topics: pd.DataFrame
    survey: pd.DataFrame | None = None
    weights: pd.DataFrame | None = None
    rating_scale: int = 5
    warnings: list[str] = field(default_factory=list)
    source: str | None = None


def _build(topics, survey, weights, rating_scale, source) -> MaterialityData:
    t = normalise_topics(topics)
    s = None if survey is None else normalise_survey(survey)
    w = None if weights is None else normalise_weights(weights)
    rep = check(t, s, w, rating_scale=rating_scale)
    if not rep.ok:
        raise ValidationError(rep.errors)
    return MaterialityData(t, s, w, rating_scale, rep.warnings, source)


def _find_sheet(names: list[str], wanted: str) -> str | None:
    for n in names:
        if n.strip().lower() == wanted:
            return n
    return None


def load_excel(path: str | Path, rating_scale: int = 5) -> MaterialityData:
    """Load a workbook with sheets ``topics`` and optionally ``survey``/``weights``.

    Sheet names are matched case-insensitively.
    """
    path = Path(path)
    xls = pd.ExcelFile(path)
    names = list(xls.sheet_names)
    t_name = _find_sheet(names, "topics")
    if t_name is None:
        raise ValidationError([f"{path.name}: no sheet named 'topics' (found {names})"])
    topics = xls.parse(t_name)
    s_name = _find_sheet(names, "survey")
    w_name = _find_sheet(names, "weights")
    survey = xls.parse(s_name) if s_name else None
    weights = xls.parse(w_name) if w_name else None
    return _build(topics, survey, weights, rating_scale, str(path))


def load_csv_dir(path: str | Path, rating_scale: int = 5) -> MaterialityData:
    """Load ``topics.csv`` and optional ``survey.csv``/``weights.csv`` from a folder."""
    path = Path(path)
    tp = path / "topics.csv"
    if not tp.exists():
        raise ValidationError([f"{path}: topics.csv not found"])
    sp, wp = path / "survey.csv", path / "weights.csv"
    survey = pd.read_csv(sp) if sp.exists() else None
    weights = pd.read_csv(wp) if wp.exists() else None
    return _build(pd.read_csv(tp), survey, weights, rating_scale, str(path))


def load(path: str | Path, rating_scale: int = 5) -> MaterialityData:
    """Load from an ``.xlsx`` workbook, a folder of CSVs, or a single topics CSV."""
    path = Path(path)
    if path.is_dir():
        return load_csv_dir(path, rating_scale)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return load_excel(path, rating_scale)
    if suffix == ".csv":
        return _build(pd.read_csv(path), None, None, rating_scale, str(path))
    raise ValidationError([f"{path}: unsupported file type {suffix!r}"])


def example_path() -> Path:
    """Path of the bundled fictional example workbook."""
    return Path(str(resources.files("materiality") / "data" / "example" / "example_assessment.xlsx"))


def load_example() -> MaterialityData:
    """Load the bundled example. **The data is fictional** (see its README)."""
    return load_excel(example_path())


# ---------------------------------------------------------------------------
# Classic (single-axis-pair) matrices
# ---------------------------------------------------------------------------

_CLASSIC_PATTERNS = {
    "topic": re.compile(r"(issue|topic|matter)", re.I),
    "stakeholder": re.compile(r"stakeholder", re.I),
    "business": re.compile(r"(business|financial|company)", re.I),
}


def _scale_from_header(header: str, default: float) -> float:
    m = re.search(r"(\d+)\s*[-\u2013]\s*(\d+)", header)
    return float(m.group(2)) if m else default


def load_classic_matrix(path: str | Path, sheet: str | int | None = None, scale_max: float | None = None) -> pd.DataFrame:
    """Load a classic two-axis matrix (stakeholder importance vs business impact).

    Many spreadsheet templates have a table like::

        ESG Issue | Stakeholder Importance (1-10) | Business Impact (1-10) | Priority

    possibly below a few title rows. The header row is found automatically;
    the scale maximum is read from ``(1-10)``-style headers unless given.
    Returns columns ``topic, stakeholder_importance, business_impact,
    scale_max``; rows without both scores are dropped.
    """
    path = Path(path)
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path, header=None)
    else:
        raw = pd.read_excel(path, sheet_name=0 if sheet is None else sheet, header=None)
    header_row = None
    cols: dict[str, int] = {}
    for r in range(min(len(raw), 30)):
        row = [str(v) if pd.notna(v) else "" for v in raw.iloc[r].tolist()]
        found = {}
        for key, pat in _CLASSIC_PATTERNS.items():
            for j, cell in enumerate(row):
                if pat.search(cell) and j not in found.values():
                    found[key] = j
                    break
        if len(found) == 3:
            header_row, cols = r, found
            break
    if header_row is None:
        raise ValidationError([f"{path.name}: could not find an issue / stakeholder / business header row"])
    headers = [str(v) for v in raw.iloc[header_row].tolist()]
    body = raw.iloc[header_row + 1 :]
    out = pd.DataFrame(
        {
            "topic": body.iloc[:, cols["topic"]].astype("string").str.strip(),
            "stakeholder_importance": pd.to_numeric(body.iloc[:, cols["stakeholder"]], errors="coerce"),
            "business_impact": pd.to_numeric(body.iloc[:, cols["business"]], errors="coerce"),
        }
    )
    out = out.dropna(subset=["topic"])
    out = out[out["topic"] != ""]
    sm = scale_max or max(
        _scale_from_header(headers[cols["stakeholder"]], 10.0),
        _scale_from_header(headers[cols["business"]], 10.0),
    )
    out = out.dropna(subset=["stakeholder_importance", "business_impact"]).reset_index(drop=True)
    bad = (out[["stakeholder_importance", "business_impact"]] < 0).any(axis=1) | (
        out[["stakeholder_importance", "business_impact"]] > sm
    ).any(axis=1)
    if bad.any():
        raise ValidationError([f"classic matrix: scores outside [0, {sm:g}] for {out.loc[bad, 'topic'].tolist()}"])
    out["scale_max"] = sm
    return out
