from datetime import date

import numpy as np
import pandas as pd
import pytest
import yaml

from fields.national_highways.schedule import (
    MULTI_STATE,
    delay_table,
    flag_projects,
    project_state,
    stage_group,
)
from pipeline.shared_layers import ROOT

CFG = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())["schedule"]
AS_OF = date(2026, 9, 29)

UC = "Under Construction (AD issued)"
PCC = "PCC Issued, CC Pending"
AWARDED = "Awarded, Not Appointed"
DONE = "CC Issued & O&M by Construction Agency"


def row(upc, state="Uttar Pradesh", stage=UC, appointed="03-05-2024", scheduled="02-05-2025",
        loa="01-01-2024", physical="77.28", capex="100.5"):
    return {
        "upc": upc, "state": state, "current_st": stage, "adv_appointed_date": appointed,
        "adv_scheduled_completion_date": scheduled, "loa_date": loa,
        "adv_cumphysical_progress_tilllastmonth": physical, "adv_total_capital_cost": capex,
    }


@pytest.mark.parametrize("label, group", [
    ("Balance for Award", "not_awarded"),
    (AWARDED, "awarded_not_started"),
    (UC, "under_construction"),
    (PCC, "provisionally_complete"),
    (DONE, "completed"),
    ("Under O&M through OMT/TOT/O&M Agency at Site", "completed"),
    ("Completed & Agency Demobilised (Civil/O&M)", "completed"),
    ("O&M on Project no more required", "completed"),
    ("Terminated", "terminated"),
    ("  Terminated ", "terminated"),
    ("Some new NHAI label", "unknown"),
    (None, "unknown"),
    (float("nan"), "unknown"),
])
def test_stage_group(label, group):
    assert stage_group(label, CFG["stage_groups"]) == group


@pytest.mark.parametrize("text, expected", [
    ("Uttar Pradesh", "Uttar Pradesh"),
    ("Haryana, Punjab", MULTI_STATE),
    ("Tamil Nadu,Puducherry", MULTI_STATE),
    ("Haryana, Haryana", "Haryana"),
    ("Haryana, Atlantis", None),
    ("", None),
    (None, None),
])
def test_project_state(text, expected):
    assert project_state(text) == expected


def flagged():
    rows = [
        row("overdue"),
        row("ahead", scheduled="20-03-2028"),
        row("pcc_late", stage=PCC, physical="100"),
        row("done", stage=DONE, physical="100"),
        row("not_started", stage=AWARDED, appointed=None, scheduled=None, loa="01-02-2026", physical=None),
        row("no_schedule", scheduled=None),
        row("year_2051", scheduled="15-12-2051"),
        row("reversed", appointed="03-05-2024", scheduled="02-05-2023"),
        row("bad_progress", scheduled="20-03-2028", physical="105"),
        row("new_label", stage="Some new NHAI label"),
        row("bad_date", scheduled="31/12/2025"),
        row("two_states", state="Haryana, Punjab", scheduled="20-03-2028"),
        row("no_state", state=None, scheduled="20-03-2028"),
    ]
    return flag_projects(pd.DataFrame(rows), AS_OF, CFG).set_index("upc")


def test_flags():
    f = flagged()
    assert f["flag"].to_dict() == {
        "overdue": "overdue", "ahead": "scheduled_ahead",
        "pcc_late": "not_applicable",   # no PCC date in the layer, so a passed schedule proves nothing
        "done": "not_applicable", "not_started": "not_started", "no_schedule": "unknown",
        "year_2051": "unknown", "reversed": "unknown", "bad_progress": "scheduled_ahead",
        "new_label": "not_applicable", "bad_date": "unknown", "two_states": "scheduled_ahead",
        "no_state": "scheduled_ahead",
    }


def test_drivers():
    f = flagged()
    assert f.loc["overdue", "days_overdue"] == (AS_OF - date(2025, 5, 2)).days == 515
    assert f.loc["not_started", "days_since_loa"] == (AS_OF - date(2026, 2, 1)).days
    assert np.isnan(f.loc["ahead", "days_overdue"])
    assert np.isnan(f.loc["overdue", "days_since_loa"])


def test_unreadable_values_are_listed_not_defaulted():
    f = flagged()
    assert f.loc["overdue", "reasons"] == ""
    assert f.loc["no_schedule", "reasons"] == "no_scheduled_date"
    assert f.loc["year_2051", "reasons"] == "scheduled_out_of_range;no_scheduled_date"
    assert f.loc["reversed", "reasons"] == "scheduled_before_appointed"
    assert f.loc["bad_progress", "reasons"] == "progress_out_of_range"
    assert np.isnan(f.loc["bad_progress", "physical_pct"])
    assert f.loc["new_label", "reasons"] == "unknown_stage"
    assert f.loc["bad_date", "reasons"] == "unparseable_scheduled;no_scheduled_date"
    assert f.loc["no_state", "reasons"] == "unknown_state"
    assert f.loc["two_states", "state"] == MULTI_STATE


def test_delay_table():
    t = delay_table(flagged().reset_index())
    india = t.loc["India"]
    # under construction: overdue, ahead, no_schedule, 2051, reversed, bad_progress, bad_date, 2 states, no_state
    assert india["under_construction"] == 9
    assert (india["overdue"], india["scheduled_ahead"], india["unknown"]) == (1, 4, 4)
    assert india["not_started"] == 1
    assert india["overdue_share"] == pytest.approx(1 / 5, abs=1e-3)   # overdue ÷ projects with a schedule
    assert india["median_days_overdue"] == 515
    assert india["capex_under_construction_cr"] == round(9 * 100.5)
    assert india["capex_overdue_cr"] == round(100.5)
    assert t.loc["Uttar Pradesh", "overdue"] == 1
    assert t.loc[MULTI_STATE, "scheduled_ahead"] == 1
