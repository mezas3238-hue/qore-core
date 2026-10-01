"""Architect-B R8 temporal calibration eligibility gate.

Joins sealed empirical cadence evidence to sealed historical-calendar evidence.
No threshold is invented. A sensor can be calibration-eligible only when its
R8 cadence checkpoints and historical calendar semantics are both complete.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_R8_TEMPORAL_CALIBRATION_ELIGIBILITY_001"
EXPECTED_CADENCE = "SHARED_B_R8_EMPIRICAL_CADENCE_DIAGNOSTIC_001"
EXPECTED_CALENDAR = "SHARED_B_R8_HISTORICAL_CALENDAR_FRONTIER_001"
EXPECTED_CHECKPOINTS = (0, 736, 1473, 2210, 2947)
EXPECTED_CADENCE_SYMBOLS = {"US2000", "XAUUSD", "XTIUSD"}


class SharedBR8CalibrationEligibilityError(ValueError):
    """Calibration eligibility evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_r8_temporal_calibration_eligibility(
    *,
    cadence_diagnostic: dict[str, object],
    historical_calendar: dict[str, object],
) -> dict[str, object]:
    if cadence_diagnostic.get("identity") != EXPECTED_CADENCE:
        raise SharedBR8CalibrationEligibilityError(
            "unexpected cadence diagnostic identity"
        )
    if historical_calendar.get("identity") != EXPECTED_CALENDAR:
        raise SharedBR8CalibrationEligibilityError(
            "unexpected historical calendar identity"
        )

    if cadence_diagnostic.get("sensor_count") != 3:
        raise SharedBR8CalibrationEligibilityError(
            "cadence sensor population drift"
        )
    if cadence_diagnostic.get("sensor_side_count") != 6:
        raise SharedBR8CalibrationEligibilityError(
            "cadence side population drift"
        )
    if tuple(cadence_diagnostic.get("checkpoint_indices", ())) != (
        EXPECTED_CHECKPOINTS
    ):
        raise SharedBR8CalibrationEligibilityError(
            "cadence checkpoint population drift"
        )
    for field in (
        "cadence_policy_registry_frozen",
        "stale_thresholds_frozen",
        "liquidity_thresholds_frozen",
        "temporal_skew_thresholds_frozen",
        "comparability_thresholds_frozen",
        "global_threshold_extrapolation_authorized",
        "relational_comparability_authorized",
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "broker_mutation",
        "productive_authority",
        "b08_complete",
    ):
        if cadence_diagnostic.get(field) is not False:
            raise SharedBR8CalibrationEligibilityError(
                f"cadence governance drift: {field}"
            )

    if historical_calendar.get("sensor_count") != 177:
        raise SharedBR8CalibrationEligibilityError(
            "calendar sensor population drift"
        )
    if (
        historical_calendar.get(
            "r8_historical_session_schedule_verified_count"
        )
        != 1
    ):
        raise SharedBR8CalibrationEligibilityError(
            "historical session population drift"
        )
    if (
        historical_calendar.get(
            "r8_historical_holiday_calendar_verified_count"
        )
        != 0
    ):
        raise SharedBR8CalibrationEligibilityError(
            "historical holiday population drift"
        )
    for field in (
        "current_schedule_backfilled_into_r8",
        "provider_schedule_is_canonical_calendar",
        "relational_comparability_authorized",
        "fresh_holdout_opened",
        "broker_mutation",
        "productive_authority",
        "b07_complete",
        "b08_complete",
    ):
        if historical_calendar.get(field) is not False:
            raise SharedBR8CalibrationEligibilityError(
                f"calendar governance drift: {field}"
            )

    cadence_rows_raw = cadence_diagnostic.get("records")
    calendar_rows_raw = historical_calendar.get("records")
    if not isinstance(cadence_rows_raw, list):
        raise SharedBR8CalibrationEligibilityError(
            "cadence records missing"
        )
    if not isinstance(calendar_rows_raw, list):
        raise SharedBR8CalibrationEligibilityError(
            "calendar records missing"
        )

    cadence_by_symbol: dict[str, dict[str, dict[str, object]]] = {}
    for raw in cadence_rows_raw:
        if not isinstance(raw, dict):
            raise SharedBR8CalibrationEligibilityError(
                "cadence record invalid"
            )
        row = cast(dict[str, object], raw)
        symbol = row.get("provider_symbol")
        side = row.get("quote_side")
        if not isinstance(symbol, str) or side not in {"bid", "ask"}:
            raise SharedBR8CalibrationEligibilityError(
                "cadence identity invalid"
            )
        side_key = cast(str, side)
        bucket = cadence_by_symbol.setdefault(symbol, {})
        if side_key in bucket:
            raise SharedBR8CalibrationEligibilityError(
                "duplicate cadence sensor side"
            )
        bucket[side_key] = row

    if set(cadence_by_symbol) != EXPECTED_CADENCE_SYMBOLS:
        raise SharedBR8CalibrationEligibilityError(
            "cadence symbol population drift"
        )
    if any(
        set(bucket) != {"bid", "ask"}
        for bucket in cadence_by_symbol.values()
    ):
        raise SharedBR8CalibrationEligibilityError(
            "cadence bid/ask population incomplete"
        )

    calendar_by_symbol: dict[str, dict[str, object]] = {}
    for raw in calendar_rows_raw:
        if not isinstance(raw, dict):
            raise SharedBR8CalibrationEligibilityError(
                "calendar record invalid"
            )
        row = cast(dict[str, object], raw)
        symbol = row.get("provider_symbol")
        if not isinstance(symbol, str) or not symbol:
            raise SharedBR8CalibrationEligibilityError(
                "calendar symbol invalid"
            )
        if symbol in calendar_by_symbol:
            raise SharedBR8CalibrationEligibilityError(
                "duplicate calendar symbol"
            )
        calendar_by_symbol[symbol] = row

    if len(calendar_by_symbol) != 177:
        raise SharedBR8CalibrationEligibilityError(
            "calendar records must contain exact 177 sensors"
        )

    session_verified = {
        symbol
        for symbol, row in calendar_by_symbol.items()
        if row.get("r8_historical_session_schedule_verified") is True
    }
    fully_calendar_verified = {
        symbol
        for symbol, row in calendar_by_symbol.items()
        if row.get("r8_historical_session_schedule_verified") is True
        and row.get("r8_holiday_calendar_verified") is True
    }
    if session_verified != {"JP225"}:
        raise SharedBR8CalibrationEligibilityError(
            "historical session verified population drift"
        )
    if fully_calendar_verified:
        raise SharedBR8CalibrationEligibilityError(
            "historical full calendar unexpectedly verified"
        )

    result_rows: list[dict[str, object]] = []
    for symbol in sorted(EXPECTED_CADENCE_SYMBOLS | session_verified):
        calendar_row = calendar_by_symbol.get(symbol)
        if calendar_row is None:
            raise SharedBR8CalibrationEligibilityError(
                f"calendar row missing for {symbol}"
            )
        cadence_sides = cadence_by_symbol.get(symbol)
        cadence_present = cadence_sides is not None
        counts: dict[str, int] = {}
        cadence_complete = False
        if cadence_sides is not None:
            for side, row in cadence_sides.items():
                count = row.get("populated_checkpoint_count")
                if type(count) is not int:
                    raise SharedBR8CalibrationEligibilityError(
                        "cadence populated count invalid"
                    )
                counts[side] = count
            cadence_complete = all(
                count == len(EXPECTED_CHECKPOINTS)
                for count in counts.values()
            )

        session_ok = (
            calendar_row.get(
                "r8_historical_session_schedule_verified"
            )
            is True
        )
        holiday_ok = (
            calendar_row.get("r8_holiday_calendar_verified") is True
        )
        blockers: list[str] = []
        if not cadence_present:
            blockers.append("R8_EMPIRICAL_CADENCE_ABSENT")
        elif not cadence_complete:
            blockers.append("R8_CADENCE_CHECKPOINT_COVERAGE_PARTIAL")
        if not session_ok:
            blockers.append("R8_HISTORICAL_SESSION_UNVERIFIED")
        if not holiday_ok:
            blockers.append("R8_HISTORICAL_HOLIDAY_CALENDAR_UNVERIFIED")

        result_rows.append(
            {
                "provider_symbol": symbol,
                "provider_symbol_id": calendar_row.get(
                    "provider_symbol_id"
                ),
                "cadence_evidence_present": cadence_present,
                "cadence_full_checkpoint_coverage": cadence_complete,
                "populated_checkpoint_count_by_side": counts,
                "historical_session_schedule_verified": session_ok,
                "historical_holiday_calendar_verified": holiday_ok,
                "calibration_eligible": not blockers,
                "blockers": tuple(sorted(blockers)),
                "threshold_freeze_authorized": False,
                "relational_comparability_authorized": False,
            }
        )

    eligible = tuple(
        cast(str, row["provider_symbol"])
        for row in result_rows
        if row["calibration_eligible"] is True
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "R8_TEMPORAL_CALIBRATION_NOT_READY",
        "r8_checkpoint_count": len(EXPECTED_CHECKPOINTS),
        "cadence_observed_sensor_count": len(cadence_by_symbol),
        "cadence_full_checkpoint_sensor_count": sum(
            row["cadence_full_checkpoint_coverage"] is True
            for row in result_rows
        ),
        "historical_session_verified_sensor_count": len(
            session_verified
        ),
        "historical_full_calendar_verified_sensor_count": len(
            fully_calendar_verified
        ),
        "joint_calibration_eligible_sensor_count": len(eligible),
        "joint_calibration_eligible_symbols": eligible,
        "records": result_rows,
        "universal_cadence_threshold_authorized": False,
        "cadence_policy_registry_freeze_authorized": False,
        "liquidity_policy_registry_freeze_authorized": False,
        "temporal_skew_policy_registry_freeze_authorized": False,
        "comparability_policy_registry_freeze_authorized": False,
        "relational_comparability_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b08_complete": False,
    }
    payload["eligibility_fingerprint_sha256"] = _fingerprint(payload)
    return payload
