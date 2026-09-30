"""NHAI project schedule and delay flags (docs/fields/national-highways.md, M3).

Input is the NHAI dashboard layer (`adv_upc_wise_alignments_wfs_layers`, ADR-0014): appointed date,
scheduled completion, LOA date, cost and physical progress for each of ~1,800 projects. A flag is an
observed fact — a scheduled date that has passed while the project is still under construction, or an
award that was never followed by an appointed date — with its driver (days) in the same row. No
progress-versus-plan score: physical progress follows an S-curve, so any straight-line benchmark
would label most healthy projects "behind" (ADR-0003: explainable, no prediction). A row that cannot
be read stays unflagged and is listed with its reason; nothing is defaulted (AGENTS.md invariant 2).
Only aggregates leave data/ (ADR-0014).
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import yaml

from fields.national_highways.build import OUT
from pipeline.shared_layers import RAW, ROOT, normalize_state

MANIFEST = ROOT / "data" / "manifests" / "nhai_projects_schedule.yaml"
SOURCE = RAW / "nhai" / "upc_projects_schedule.geojson"

DATE_COLUMNS = {"adv_appointed_date": "appointed", "adv_scheduled_completion_date": "scheduled",
                "loa_date": "loa"}
NOT_APPLICABLE = "not_applicable"
MULTI_STATE = "Multiple states"


def as_of_date() -> date:
    """Date the NHAI schedule layer was fetched — the day 'overdue' is measured against."""
    return date.fromisoformat(yaml.safe_load(MANIFEST.read_text())["files"][0]["fetched_at"][:10])


def stage_group(label: object, groups: dict[str, list[str]]) -> str:
    """NHAI `current_st` label -> configured group; "unknown" for a missing or unlisted label."""
    if isinstance(label, str):
        for group, labels in groups.items():
            if label.strip() in labels:
                return group
    return "unknown"


def project_state(text: object) -> str | None:
    """'Uttar Pradesh' -> its canonical name; 'Haryana, Punjab' -> 'Multiple states';
    None when the field is empty or any listed state is not recognised."""
    if not isinstance(text, str):
        return None
    states = [normalize_state(part) for part in text.split(",")]
    if None in states:
        return None
    return states[0] if len(set(states)) == 1 else MULTI_STATE


def flag_projects(df: pd.DataFrame, as_of: date, cfg: dict) -> pd.DataFrame:
    """Parse the schedule columns and flag every project still being executed.

    `as_of` is the fetch date. Flags: overdue (under construction, scheduled date passed) ·
    scheduled_ahead (under construction, scheduled date still ahead) · not_started (awarded, no
    appointed date yet) · unknown (under construction, no usable scheduled date) · not_applicable.
    days_overdue and days_since_loa are the drivers; `reasons` lists every unreadable value.
    """
    out = df.copy()
    lo, hi = cfg["date_year_range"]
    out["state"] = out["state"].map(project_state)
    reasons: dict[str, pd.Series] = {"unknown_state": out["state"].isna()}
    for source, name in DATE_COLUMNS.items():
        out[name] = pd.to_datetime(out[source], format="%d-%m-%Y", errors="coerce")
        reasons[f"unparseable_{name}"] = out[name].isna() & out[source].notna()
        outside = out[name].notna() & ~out[name].dt.year.between(lo, hi)
        reasons[f"{name}_out_of_range"] = outside
        out.loc[outside, name] = pd.NaT  # a 1999 or 2051 date is a data error, not a schedule
    progress = out["adv_cumphysical_progress_tilllastmonth"]
    out["physical_pct"] = pd.to_numeric(progress, errors="coerce")
    out["capex_cr"] = pd.to_numeric(out["adv_total_capital_cost"], errors="coerce")
    reasons["unparseable_progress"] = out["physical_pct"].isna() & progress.notna()
    reasons["progress_out_of_range"] = ~out["physical_pct"].between(0, 100) & out["physical_pct"].notna()
    out.loc[reasons["progress_out_of_range"], "physical_pct"] = np.nan

    out["group"] = out["current_st"].map(lambda label: stage_group(label, cfg["stage_groups"]))
    reasons["unknown_stage"] = out["group"] == "unknown"
    building = out["group"] == "under_construction"
    reversed_window = building & (out["scheduled"] < out["appointed"])
    reasons["scheduled_before_appointed"] = reversed_window
    out.loc[reversed_window, "scheduled"] = pd.NaT
    reasons["no_scheduled_date"] = building & out["scheduled"].isna() & ~reversed_window

    as_of_ts = pd.Timestamp(as_of)
    overdue = building & (out["scheduled"] < as_of_ts)
    ahead = building & (out["scheduled"] >= as_of_ts)
    unawarded = out["group"] == "awarded_not_started"
    out["days_overdue"] = np.where(overdue, (as_of_ts - out["scheduled"]).dt.days, np.nan)
    out["days_since_loa"] = np.where(unawarded, (as_of_ts - out["loa"]).dt.days, np.nan)
    out["flag"] = np.select(
        [~out["group"].isin(cfg["in_execution"]), unawarded, overdue, ahead],
        [NOT_APPLICABLE, "not_started", "overdue", "scheduled_ahead"], default="unknown")
    out["reasons"] = [";".join(name for name, hit in reasons.items() if hit.iloc[i])
                      for i in range(len(out))]
    return out


def delay_table(flags: pd.DataFrame) -> pd.DataFrame:
    """Executing projects per state (plus an India row): counts by flag, the overdue share of
    projects with a usable schedule, medians of the drivers, and rupee totals."""
    executing = flags[flags["flag"] != NOT_APPLICABLE]
    rows = {}
    for key, group in [*executing.groupby("state"), ("India", executing)]:
        counts = group["flag"].value_counts()
        overdue = group[group["flag"] == "overdue"]
        scheduled = int(counts.get("overdue", 0) + counts.get("scheduled_ahead", 0))
        building = group[group["flag"].isin(["overdue", "scheduled_ahead", "unknown"])]
        rows[key] = {
            "under_construction": len(building), "overdue": int(counts.get("overdue", 0)),
            "scheduled_ahead": int(counts.get("scheduled_ahead", 0)), "unknown": int(counts.get("unknown", 0)),
            "not_started": int(counts.get("not_started", 0)),
            "overdue_share": round(counts.get("overdue", 0) / scheduled, 3) if scheduled else np.nan,
            "median_days_overdue": overdue["days_overdue"].median() if len(overdue) else np.nan,
            "median_physical_pct_overdue": overdue["physical_pct"].median() if len(overdue) else np.nan,
            "median_days_since_loa_not_started":
                group.loc[group["flag"] == "not_started", "days_since_loa"].median(),
            "capex_under_construction_cr": round(building["capex_cr"].sum()),
            "capex_overdue_cr": round(overdue["capex_cr"].sum()),
        }
    return pd.DataFrame.from_dict(rows, orient="index").sort_values("under_construction", ascending=False)


def build_schedule() -> pd.DataFrame:
    """Read the fetched NHAI schedule layer, flag it, and write nhai_schedule.parquet plus
    nhai_schedule_errors.csv (one row per unreadable value). Raises on a repeated project id."""
    if not SOURCE.exists():
        raise FileNotFoundError(f"{SOURCE} missing — run: cd ml && uv run python -m common.fetch")
    cfg = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())["schedule"]
    as_of = as_of_date()

    df = pd.DataFrame([f["properties"] for f in json.loads(SOURCE.read_text())["features"]])
    if df["upc"].isna().any() or df["upc"].duplicated().any():
        raise ValueError("NHAI schedule layer: missing or repeated upc — project ids are not unique")
    flags = flag_projects(df, as_of, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    flags.to_parquet(OUT / "nhai_schedule.parquet")
    errors = flags.loc[flags["reasons"] != "", ["upc", "reasons"]].assign(
        reason=lambda t: t["reasons"].str.split(";")).explode("reason")
    errors[["upc", "reason"]].to_csv(OUT / "nhai_schedule_errors.csv", index=False)
    print(f"schedule: {len(flags):,} projects as of {as_of}; flags {flags['flag'].value_counts().to_dict()}; "
          f"{len(errors):,} unreadable values")
    return flags
