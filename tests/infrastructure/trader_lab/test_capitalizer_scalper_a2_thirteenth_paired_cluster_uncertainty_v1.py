"""Deterministic date-cluster bootstrap and frozen source-ID guards."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_thirteenth_paired_cluster_uncertainty_v1 as audit,
)


def _row(date: str, a: bool, b: bool) -> dict[str, object]:
    return {
        "operating_date": date,
        "paired": {
            "15": {
                "v49": {"covered": True, "positive": a},
                "online": {"covered": True, "positive": b},
            }
        },
    }


def test_cluster_bootstrap_reproducible_and_no_future_gate() -> None:
    rows=[_row("2026-06-01",False,True),_row("2026-06-02",False,True)]
    x=audit.bootstrap_pp(rows,15)
    assert x==audit.bootstrap_pp(rows,15)
    assert x["paired_covered"]==2
    assert x["day_cluster_95ci_pp"]==[100.0,100.0]
    assert x["exploratory_5pp_label"]=="DIAGNOSTIC_ONLINE_ADVANTAGE_ABOVE_5PP"
    assert x["uncertainty_is_not_an_execution_cost_or_trade_CI"] is True


def test_zero_difference_remains_diagnostic_only() -> None:
    value=audit.bootstrap_pp([_row("2026-06-01",True,True)],15)
    assert value["day_cluster_95ci_pp"]==[0.0,0.0]
    assert value["exploratory_5pp_label"]=="DIAGNOSTIC_5PP_BAND_WITHIN_CI"


def test_zero_coverage_and_missing_book_are_unknown(tmp_path: Path) -> None:
    assert audit.bootstrap_pp([],15)["day_cluster_95ci_pp"] is None
    with pytest.raises(ValueError,match="nine-market"):
        audit.audit(tmp_path,tmp_path)
