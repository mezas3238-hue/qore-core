"""Outcome-free evidence-completion worklist for B-16 sensor qualification.

The worklist transforms the frozen 177-sensor qualification frontier into an
explicit scientific evidence queue. Ordering is based only on missing
qualification prerequisites; it is not trading priority, predictive ranking,
economic ranking or sensor admission.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Final, cast

IDENTITY: Final = "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001"
EXPECTED_FRONTIER: Final = "SHARED_B_SENSOR_QUALIFICATION_FRONTIER_001"
FULL_SOURCE = "FULL_REAL_BID_ASK_HISTORY_EVIDENCE"


class SharedBSensorQualificationWorklistError(ValueError):
    """B-16 worklist input violated frozen qualification semantics."""


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_sensor_qualification_worklist(
    frontier: dict[str, object],
) -> dict[str, object]:
    if frontier.get("identity") != EXPECTED_FRONTIER:
        raise SharedBSensorQualificationWorklistError(
            "unexpected qualification frontier identity"
        )
    records = frontier.get("records")
    if not isinstance(records, list) or len(records) != 177:
        raise SharedBSensorQualificationWorklistError(
            "qualification frontier must contain exact 177 records"
        )
    if frontier.get("sensor_count") != 177:
        raise SharedBSensorQualificationWorklistError(
            "qualification frontier sensor_count drift"
        )
    if frontier.get("target_or_outcome_used_for_selection") is not False:
        raise SharedBSensorQualificationWorklistError(
            "outcome-aware frontier cannot enter B16 worklist"
        )
    if frontier.get("productive_authority") is not False:
        raise SharedBSensorQualificationWorklistError(
            "productive frontier cannot enter B16 worklist"
        )

    output: list[dict[str, object]] = []
    gap_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()

    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBSensorQualificationWorklistError(
                "qualification frontier row invalid"
            )
        row = cast(dict[str, Any], raw)
        symbol = row.get("provider_symbol")
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        if (
            not isinstance(symbol, str)
            or not symbol
            or not isinstance(provider, str)
            or not provider
            or type(symbol_id) is not int
            or symbol_id <= 0
        ):
            raise SharedBSensorQualificationWorklistError(
                "qualification row identity invalid"
            )

        admitted = row.get("sensor_admitted")
        complete = row.get("causal_qualification_complete")
        scientific_value = row.get("scientific_value_proven")
        identity_ready = row.get(
            "identity_ready_for_next_qualification_step"
        )
        calendar_ready = row.get("canonical_calendar_binding_verified")
        source_status = row.get("real_source_evidence_status")
        for name, value in (
            ("sensor_admitted", admitted),
            ("causal_qualification_complete", complete),
            ("scientific_value_proven", scientific_value),
            ("identity_ready", identity_ready),
            ("calendar_ready", calendar_ready),
        ):
            if type(value) is not bool:
                raise SharedBSensorQualificationWorklistError(
                    f"{name} must be bool"
                )
        if admitted and not complete:
            raise SharedBSensorQualificationWorklistError(
                "sensor admitted before causal qualification completion"
            )

        missing: list[str] = []
        if not identity_ready:
            missing.append("CANONICAL_IDENTITY_EVIDENCE")
        if not calendar_ready:
            missing.append("CANONICAL_CALENDAR_EVIDENCE")
        if source_status != FULL_SOURCE:
            missing.append("FULL_REAL_CAUSAL_HISTORY_EVIDENCE")
        if not scientific_value:
            missing.append("SCIENTIFIC_VALUE_PROOF")

        if complete:
            state = "CAUSAL_QUALIFICATION_COMPLETE"
            if missing:
                raise SharedBSensorQualificationWorklistError(
                    "complete sensor retains qualification evidence gaps"
                )
        elif (
            identity_ready
            and calendar_ready
            and source_status == FULL_SOURCE
        ):
            state = "READY_FOR_SCIENTIFIC_VALUE_EXAM"
        else:
            state = "EVIDENCE_COMPLETION_REQUIRED"

        for gap in missing:
            gap_counts[gap] += 1
        state_counts[state] += 1
        output.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "state": state,
                "missing_evidence": tuple(sorted(missing)),
                "missing_evidence_count": len(missing),
                "identity_ready": identity_ready,
                "calendar_ready": calendar_ready,
                "real_source_evidence_status": source_status,
                "scientific_value_proven": scientific_value,
                "causal_qualification_complete": complete,
                "sensor_admitted": admitted,
                "research_sequence_hint_only": True,
                "trade_priority_authority": False,
                "economic_priority_authority": False,
                "sensor_admission_authority": False,
            }
        )

    output.sort(
        key=lambda item: (
            int(cast(int, item["missing_evidence_count"])),
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    minimum_gap = min(
        int(cast(int, item["missing_evidence_count"])) for item in output
    )
    nearest = tuple(
        str(item["provider_symbol"])
        for item in output
        if item["state"] == "EVIDENCE_COMPLETION_REQUIRED"
        and item["missing_evidence_count"] == minimum_gap
    )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "sensor_count": 177,
        "state_counts": dict(sorted(state_counts.items())),
        "gap_counts": dict(sorted(gap_counts.items())),
        "minimum_missing_evidence_count": minimum_gap,
        "nearest_evidence_completion_symbols": nearest,
        "ready_for_scientific_value_exam_count": state_counts[
            "READY_FOR_SCIENTIFIC_VALUE_EXAM"
        ],
        "causal_qualification_complete_count": state_counts[
            "CAUSAL_QUALIFICATION_COMPLETE"
        ],
        "records": output,
        "ordering_basis": "MISSING_QUALIFICATION_EVIDENCE_ONLY",
        "outcome_used": False,
        "pnl_used": False,
        "trade_priority_authority": False,
        "economic_priority_authority": False,
        "sensor_admission_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "execution_authority": False,
        "productive_authority": False,
    }
    payload["worklist_fingerprint_sha256"] = _fingerprint(payload)
    return payload
