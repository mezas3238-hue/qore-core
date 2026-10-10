"""Future first-selection != proof of original CISD absent from all candidates."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (\n    capitalizer_scalper_a2_eleventh_cisd_prefix_membership_v1 as membership,\n)\n\n# Short binding keeps the source import within repo Ruff's 100-character limit.\n
    aggregate,
    classify_row,
    route_first_at,
)

T = "2026-05-04T12:00:00+00:00"
EARLY = "2026-05-04T11:55:00+00:00"


def _witness(family: str, moment: str) -> dict[str, object]:
    return {
        "first_family": family, "first_at": moment,
        "fvg_cisd_confirmed_at": T if family == "FVG_RETRACE_CISD" else None,
        "sweep_confirmed_at": moment if family == "LIQUIDITY_SWEEP_CISD" else None,
    }


def test_sweep_earlier_does_not_prove_later_fvg_unavailable() -> None:
    row = {
        "source_opportunity_id": "sha",
        "symbol": "EURUSD",
        "source_entry_at": T,
        "source_family": "FVG_RETRACE_CISD",
        "sensor_first_at": EARLY,
        "sensor_family": "LIQUIDITY_SWEEP_CISD",
        "source_sensor_disagree": True,
        "full_matches_original": True,
        "prefix_matches_sensor": True,
        "full_window_witness": _witness("FVG_RETRACE_CISD", T),
        "closed_prefix_witness": _witness("LIQUIDITY_SWEEP_CISD", EARLY),
    }
    got = classify_row(row)
    assert not got["original_is_first_online_candidate"]
    assert got["original_route_first_at_source_close"] is True
    assert got["original_absent_from_all_asof_candidates"] is None
    assert got["future_dependent_offline_first_selection"]


def test_same_close_opposite_family_requires_candidate_enumeration() -> None:
    row = {
        "source_opportunity_id": "sha",
        "symbol": "EURUSD",
        "source_entry_at": T,
        "source_family": "LIQUIDITY_SWEEP_CISD",
        "sensor_first_at": T,
        "sensor_family": "FVG_RETRACE_CISD",
        "source_sensor_disagree": True,
        "full_matches_original": True,
        "prefix_matches_sensor": True,
        "full_window_witness": _witness("LIQUIDITY_SWEEP_CISD", T),
        "closed_prefix_witness": _witness("FVG_RETRACE_CISD", T),
    }
    got = classify_row(row)
    assert not got["original_is_first_online_candidate"]
    assert not got["original_route_first_at_source_close"]
    assert got["original_absent_from_all_asof_candidates"] is None


def test_no_fake_source_event_when_m15_is_unproven() -> None:
    got = classify_row({
        "source_opportunity_id": "sha",
        "classification": "M15_PARENT_NOT_RECONSTRUCTED",
    })
    assert got["original_is_first_online_candidate"] is None
    assert got["changes_admission"] is False


def test_unknown_route_or_missing_nine_market_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown"):
        route_first_at({}, "UNKNOWN")
    with pytest.raises(ValueError, match="nine different"):
        aggregate(tmp_path)
