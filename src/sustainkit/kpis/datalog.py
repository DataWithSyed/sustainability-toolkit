"""Multi-year KPI data log: loading (long or wide), validation, derived KPIs, year-on-year change.

Rules that no standard prescribes are **tool choices** and are named as such:

* Year-on-year change is only computed between consecutive years; a missing year is reported as a gap
  (the change across a gap is not shown as a one-year change).
* Percentage KPIs (``kind = share``) get the change in percentage points as the headline; the relative
  change is also listed.
* A change larger than ``swing_threshold`` (default 25 %) is flagged for a data check. It is a prompt to
  look at the source data, not an error.
* Derived ratio KPIs are only computed when every component and the denominator are present for that
  year (otherwise the cell is reported as incomplete, naming the missing input).
* With a ``site`` column, additive KPIs (``sum``, ``last``) are also totalled over sites as
  "All sites"; averages and percentages are not totalled because that needs weights the log does not
  contain.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from sustainkit.kpis.library import components, load_library

ALL_SITES = "All sites"
ENTITY = "Entity"
SWING_THRESHOLD = 0.25


class KPILogError(ValueError):
    """Raised when a KPI data log fails validation; the message lists every problem."""


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") if not re.fullmatch(r"\s*\d{4}\s*", str(c))
                   else str(c).strip() for c in out.columns]
    return out


def load_log(path: str | Path, sheet: str | None = None) -> pd.DataFrame:
    """Read a data log from CSV or Excel.

    Long format: ``kpi_id, year, value`` (+ optional ``site, unit, source, note``).
    Wide format: ``kpi_id`` (+ optional ``site, unit``) and one column per year (``2022, 2023, ...``).
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        xls = pd.ExcelFile(path)
        name = sheet or next((s for s in xls.sheet_names if "kpi" in s.lower() or "data" in s.lower()),
                             xls.sheet_names[0])
        df = xls.parse(name)
    else:
        df = pd.read_csv(path, comment="#")
    return to_long(_norm(df).dropna(how="all"))


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    df = _norm(df)
    years = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c))]
    if years and "value" not in df.columns:
        ids = [c for c in df.columns if c not in years]
        df = df.melt(id_vars=ids, value_vars=years, var_name="year", value_name="value")
        df = df[df["value"].notna() & (df["value"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def validate_log(log: pd.DataFrame, library: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors stop the report; warnings are reported with it."""
    errors: list[str] = []
    warnings: list[str] = []
    missing = [c for c in ("kpi_id", "year", "value") if c not in log.columns]
    if missing:
        return [f"missing columns: {missing} (long format needs kpi_id, year, value)"], warnings
    lib = library.set_index("kpi_id")
    unknown = sorted(set(log["kpi_id"]) - set(lib.index))
    if unknown:
        errors.append(f"unknown kpi_id (add them with a custom library via --library-extra): {unknown}")
    derived = sorted(set(log["kpi_id"]) & set(lib.index[lib["kind"] == "ratio"]))
    if derived:
        errors.append(f"derived ratio KPIs are calculated, not entered: {derived}")
    yr = pd.to_numeric(log["year"], errors="coerce")
    bad_year = log.index[yr.isna() | (yr % 1 != 0) | (yr < 1900) | (yr > 2100)]
    for i in bad_year:
        errors.append(f"row {i + 2}: year {log.at[i, 'year']!r} is not a calendar year")
    val = pd.to_numeric(log["value"], errors="coerce")
    for i in log.index[val.isna()]:
        errors.append(f"row {i + 2}: value {log.at[i, 'value']!r} for {log.at[i, 'kpi_id']} is not a number")
    keys = ["kpi_id", "year"] + (["site"] if "site" in log.columns else [])
    dup = log.assign(year=yr)[keys].duplicated(keep=False)
    if dup.any():
        errors.append("duplicate rows for " + ", ".join(
            sorted({" / ".join(str(v) for v in r) for r in log.loc[dup, keys].itertuples(index=False)})))
    for i, r in log.iterrows():
        k = r["kpi_id"]
        if k not in lib.index:
            continue
        if "unit" in log.columns and pd.notna(r.get("unit")) and str(r["unit"]).strip() != str(lib.at[k, "unit"]):
            errors.append(f"row {i + 2}: {k} unit {r['unit']!r} differs from the library unit "
                          f"{lib.at[k, 'unit']!r} (convert before loading; no silent conversion)")
        if pd.isna(val.at[i]):
            continue
        lo, hi = lib.at[k, "min"], lib.at[k, "max"]
        if pd.notna(lo) and val.at[i] < lo:
            errors.append(f"row {i + 2}: {k} {val.at[i]:g} is below the minimum {lo:g}")
        if pd.notna(hi) and val.at[i] > hi:
            errors.append(f"row {i + 2}: {k} {val.at[i]:g} is above the maximum {hi:g}")
    if "site" in log.columns and log["site"].isna().any():
        warnings.append(f"{int(log['site'].isna().sum())} rows without site are reported under '{ENTITY}'")
    return errors, warnings


@dataclass
class KPIReport:
    library: pd.DataFrame
    values: pd.DataFrame          # kpi_id, site, year, value, derived, note
    changes: pd.DataFrame         # kpi_id, site, year, prev_year, value, prev_value, abs_change, pct_change, pp_change, status, flag
    summary: pd.DataFrame         # one row per kpi x site
    warnings: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)
    swing_threshold: float = SWING_THRESHOLD

    @property
    def years(self) -> list[int]:
        return sorted(self.values["year"].unique().tolist())

    def wide(self, site: str | None = None) -> pd.DataFrame:
        v = self.values if site is None else self.values[self.values["site"] == site]
        return v.pivot_table(index=["kpi_id", "site"], columns="year", values="value", aggfunc="first")

    def to_markdown(self, site: str | None = None) -> str:
        s = self.summary if site is None else self.summary[self.summary["site"] == site]
        lines = ["| KPI | Site | Unit | Years | Latest | Change vs prior year | Status | CAGR | ESRS | GRI | Flags |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in s.iterrows():
            lines.append(
                f"| {r['name']} | {r['site']} | {r['unit']} | {r['years']} | {_fmt(r['latest'])} ({r['latest_year']}) | "
                f"{r['change_text']} | {r['status']} | {_pct(r['cagr'])} | {r['esrs'] or ''} | {r['gri'] or ''} | {r['flags']} |")
        out = ["## KPI summary", "", *lines]
        if self.incomplete:
            out += ["", "### Incomplete", "", *[f"- {m}" for m in self.incomplete]]
        if self.warnings:
            out += ["", "### Warnings", "", *[f"- {m}" for m in self.warnings]]
        out += ["", f"Change flags: |change| > {self.swing_threshold:.0%} is marked 'check data' (tool choice). "
                "Years with no value are marked as gaps; no change is computed across a gap."]
        return "\n".join(out) + "\n"


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    a = abs(v)
    return f"{v:,.0f}" if a >= 1000 else (f"{v:,.1f}" if a >= 10 else f"{v:,.2f}")


def _pct(v) -> str:
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:+.1%}"


def _status(direction: str, change: float) -> str:
    if change is None or (isinstance(change, float) and math.isnan(change)):
        return "n/a"
    if abs(change) < 1e-12:
        return "no change"
    if direction == "neutral":
        return "up" if change > 0 else "down"
    better = change < 0 if direction == "lower_better" else change > 0
    return "improved" if better else "worsened"


def build_report(log: pd.DataFrame, library: pd.DataFrame | None = None,
                 swing_threshold: float = SWING_THRESHOLD) -> KPIReport:
    library = load_library() if library is None else library
    log = to_long(log)
    errors, warnings = validate_log(log, library)
    if errors:
        raise KPILogError("KPI data log problems:\n- " + "\n- ".join(errors))
    lib = library.set_index("kpi_id")
    v = log.assign(year=pd.to_numeric(log["year"]).astype(int), value=pd.to_numeric(log["value"]))
    if "site" not in v.columns:
        v["site"] = ENTITY
    v["site"] = v["site"].fillna(ENTITY).astype(str)
    v = v[["kpi_id", "site", "year", "value"]].assign(derived=False, note="")
    sites = sorted(v["site"].unique())
    if len(sites) > 1 or sites != [ENTITY]:
        add = v[v["kpi_id"].map(lib["kind"]).isin(["sum", "last"])]
        if len(set(add["site"])) > 1:
            n_sites = add.groupby(["kpi_id", "year"])["site"].nunique()
            tot = add.groupby(["kpi_id", "year"], as_index=False)["value"].sum()
            tot["note"] = [f"sum of {n_sites[(k, y)]} site(s)" for k, y in zip(tot["kpi_id"], tot["year"])]
            v = pd.concat([v, tot.assign(site=ALL_SITES, derived=False)], ignore_index=True)
    incomplete: list[str] = []
    years = sorted(v["year"].unique())
    rows = []
    for k, r in lib[lib["kind"] == "ratio"].iterrows():
        need = components(r) + [r["denominator"]]
        for site in sorted(v["site"].unique()):
            sv = v[v["site"] == site]
            if not set(need) & set(sv["kpi_id"]):
                continue
            for y in years:
                have = sv[sv["year"] == y].set_index("kpi_id")["value"]
                miss = [c for c in need if c not in have.index]
                if miss:
                    if any(c in have.index for c in need):
                        incomplete.append(f"{k} {site} {y}: not calculated, missing {miss}")
                    continue
                den = have[r["denominator"]]
                if den == 0:
                    incomplete.append(f"{k} {site} {y}: denominator {r['denominator']} is zero")
                    continue
                rows.append({"kpi_id": k, "site": site, "year": y, "value": float(sum(have[c] for c in components(r))
                             * r["scale"] / den), "derived": True, "note": "derived"})
    if rows:
        v = pd.concat([v, pd.DataFrame(rows)], ignore_index=True)
    v = v.sort_values(["kpi_id", "site", "year"]).reset_index(drop=True)

    ch_rows, sum_rows = [], []
    order = {k: i for i, k in enumerate(lib.index)}
    for (k, site), g in sorted(v.groupby(["kpi_id", "site"]), key=lambda t: (order[t[0][0]], t[0][1])):
        info = lib.loc[k]
        g = g.sort_values("year")
        ys, vals = g["year"].tolist(), g["value"].tolist()
        gaps = [y for y in range(ys[0], ys[-1] + 1) if y not in ys]
        for (y0, v0), (y1, v1) in zip(zip(ys, vals), zip(ys[1:], vals[1:])):
            if y1 - y0 != 1:
                continue
            absch = v1 - v0
            pct = absch / abs(v0) if v0 != 0 else float("nan")
            pp = absch if info["kind"] == "share" else float("nan")
            flag = "check data" if (not math.isnan(pct) and abs(pct) > swing_threshold) else ""
            ch_rows.append({"kpi_id": k, "site": site, "year": y1, "prev_year": y0, "value": v1, "prev_value": v0,
                            "abs_change": absch, "pct_change": pct, "pp_change": pp,
                            "status": _status(info["direction"], absch), "flag": flag})
        last_y, last_v = ys[-1], vals[-1]
        prev = [c for c in ch_rows if c["kpi_id"] == k and c["site"] == site and c["year"] == last_y]
        if prev:
            c = prev[0]
            text = (f"{c['pp_change']:+.1f} pp" if info["kind"] == "share" else f"{_fmt(c['abs_change'])}")
            if not math.isnan(c["pct_change"]):
                text += f" ({c['pct_change']:+.1%})"
            status = c["status"]
        else:
            text, status = ("gap before latest year" if len(ys) > 1 else "single year"), "n/a"
        span = ys[-1] - ys[0]
        cagr = ((last_v / vals[0]) ** (1 / span) - 1) if span > 0 and vals[0] > 0 and last_v > 0 \
            and info["kind"] in ("sum", "last", "ratio", "mean") else float("nan")
        flags = []
        if gaps:
            flags.append("gap " + ", ".join(map(str, gaps)))
        flags += [f"check data {c['year']}" for c in ch_rows if c["kpi_id"] == k and c["site"] == site and c["flag"]]
        if last_y < years[-1]:
            flags.append(f"no {years[-1]} value")
        sum_rows.append({"kpi_id": k, "name": info["name"], "pillar": info["pillar"], "site": site, "unit": info["unit"],
                         "years": f"{ys[0]}-{ys[-1]}" if len(ys) > 1 else str(ys[0]), "n_years": len(ys),
                         "latest_year": last_y, "latest": last_v, "change_text": text, "status": status, "cagr": cagr,
                         "esrs": info["esrs"] if pd.notna(info["esrs"]) else "", "gri": info["gri"] if pd.notna(info["gri"]) else "",
                         "flags": "; ".join(flags), "derived": bool(g["derived"].any())})
    changes = pd.DataFrame(ch_rows)
    summary = pd.DataFrame(sum_rows)
    for _, r in summary[summary["flags"].str.contains("gap")].iterrows():
        incomplete.append(f"{r['kpi_id']} {r['site']}: {r['flags']}")
    return KPIReport(library=library, values=v, changes=changes, summary=summary, warnings=warnings,
                     incomplete=incomplete, swing_threshold=swing_threshold)


__all__ = ["ALL_SITES", "ENTITY", "KPILogError", "KPIReport", "SWING_THRESHOLD", "build_report", "load_log",
           "to_long", "validate_log"]
