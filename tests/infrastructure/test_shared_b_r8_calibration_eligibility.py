from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_calibration_eligibility import (
    SharedBR8CalibrationEligibilityError,
    build_r8_temporal_calibration_eligibility,
)


CHECKPOINTS = [0, 736, 1473, 2210, 2947]


def _cadence() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for symbol, symbol_id, populated in (
        ("US2000", 10012, 5),
        ("XAUUSD", 41, 5),
        ("XTIUSD", 10019, 2),
    ):
        for side in ("bid", "ask"):
            records.append(
                {
                    "provider_symbol": symbol,
                    "provider_symbol_id": symbol_id,
                    "quote_side": side,
                    "populated_checkpoint_count": populated,
                }
            )
    return {
        "identity": "SHARED_B_R8_EMPIRICAL_CADENCE_DIAGNOSTIC_001",
        "sensor_count": 3,
        "sensor_side_count": 6,
        "checkpoint_indices": CHECKPOINTS,
        "records": records,
        "cadence_policy_registry_frozen": False,
        "stale_thresholds_frozen": False,
        "liquidity_thresholds_frozen": False,
        "temporal_skew_thresholds_frozen": False,
        "comparability_thresholds_frozen": False,
        "global_threshold_extrapolation_authorized": False,
        "relational_comparability_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b08_complete": False,
    }


def _calendar() -> dict[str, object]:
    special = (
        ("JP225", 10006),
        ("US2000", 10012),
        ("XAUUSD", 41),
        ("XTIUSD", 10019),
    )
    rows: list[dict[str, object]] = []
    for symbol, symbol_id in special:
        row: dict[str, object] = {
            "provider_symbol": symbol,
            "provider_symbol_id": symbol_id,
        }
        if symbol == "JP225":
            row["r8_historical_session_schedule_verified"] = True
            row["r8_holiday_calendar_verified"] = False
        rows.append(row)
    for index in range(173):
        rows.append(
            {
                "provider_symbol": f"S{index:03d}",
                "provider_symbol_id": 20000 + index,
            }
        )
    assert len(rows) == 177
    return {
        "identity": "SHARED_B_R8_HISTORICAL_CALENDAR_FRONTIER_001",
        "sensor_count": 177,
        "records": rows,
        "r8_historical_session_schedule_verified_count": 1,
        "r8_historical_holiday_calendar_verified_count": 0,
        "current_schedule_backfilled_into_r8": False,
        "provider_schedule_is_canonical_calendar": False,
        "relational_comparability_authorized": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b07_complete": False,
        "b08_complete": False,
    }


def test_joint_calibration_eligibility_is_zero() -> None:
    payload = build_r8_temporal_calibration_eligibility(
        cadence_diagnostic=_cadence(),
        historical_calendar=_calendar(),
    )

    assert payload["cadence_observed_sensor_count"] == 3
    assert payload["cadence_full_checkpoint_sensor_count"] == 2
    assert payload["historical_session_verified_sensor_count"] == 1
    assert payload["historical_full_calendar_verified_sensor_count"] == 0
    assert payload["joint_calibration_eligible_sensor_count"] == 0
    assert payload["joint_calibration_eligible_symbols"] == ()
    assert payload["cadence_policy_registry_freeze_authorized"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b08_complete"] is False

    rows = {
        row["provider_symbol"]: row
        for row in payload["records"]
    }
    assert rows["US2000"]["cadence_full_checkpoint_coverage"] is True
    assert (
        "R8_HISTORICAL_SESSION_UNVERIFIED"
        in rows["US2000"]["blockers"]
    )
    assert "R8_EMPIRICAL_CADENCE_ABSENT" in rows["JP225"]["blockers"]
    assert (
        "R8_CADENCE_CHECKPOINT_COVERAGE_PARTIAL"
        in rows["XTIUSD"]["blockers"]
    )


def test_rejects_cadence_policy_promotion() -> None:
    cadence = deepcopy(_cadence())
    cadence["cadence_policy_registry_frozen"] = True
    with pytest.raises(
        SharedBR8CalibrationEligibilityError,
        match="cadence_policy_registry_frozen",
    ):
        build_r8_temporal_calibration_eligibility(
            cadence_diagnostic=cadence,
            historical_calendar=_calendar(),
        )


def test_rejects_historical_calendar_promotion_drift() -> None:
    calendar = deepcopy(_calendar())
    calendar["r8_historical_holiday_calendar_verified_count"] = 1
    with pytest.raises(
        SharedBR8CalibrationEligibilityError,
        match="holiday population drift",
    ):
        build_r8_temporal_calibration_eligibility(
            cadence_diagnostic=_cadence(),
            historical_calendar=calendar,
        )
