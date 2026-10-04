"""Deterministic reducer for preregistered B-16 source pilot evidence."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from enum import StrEnum
from typing import Any, Final, cast

EXPECTED_PREREGISTRATION: Final = (
    "SHARED_B16_SOURCE_ACQUISITION_PREREGISTRATION_001"
)
FROZEN_PILOT_INDICES: Final = (0, 736, 1473, 2210, 2947)


class B16PilotCoverageState(StrEnum):
    FULL_PILOT_HISTORY = "FULL_PILOT_HISTORY"
    PARTIAL_PILOT_HISTORY = "PARTIAL_PILOT_HISTORY"
    NO_PILOT_HISTORY = "NO_PILOT_HISTORY"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class B16SourcePilotReducerError(ValueError):
    """B16 source pilot evidence failed closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _candidate_key(row: dict[str, Any]) -> tuple[str, int, str]:
    provider = row.get("provider")
    symbol_id = row.get("provider_symbol_id")
    symbol = row.get("provider_symbol")
    if (
        not isinstance(provider, str)
        or not provider
        or type(symbol_id) is not int
        or symbol_id <= 0
        or not isinstance(symbol, str)
        or not symbol
    ):
        raise B16SourcePilotReducerError("candidate identity invalid")
    return provider, symbol_id, symbol


def reduce_b16_source_pilot(
    *,
    preregistration: dict[str, object],
    raw_report: dict[str, object],
) -> dict[str, object]:
    if preregistration.get("identity") != EXPECTED_PREREGISTRATION:
        raise B16SourcePilotReducerError(
            "unexpected source preregistration identity"
        )
    candidates = preregistration.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 87:
        raise B16SourcePilotReducerError(
            "preregistration must contain exact 87 candidates"
        )
    expected = {
        _candidate_key(cast(dict[str, Any], row))
        for row in candidates
        if isinstance(row, dict)
    }
    if len(expected) != 87:
        raise B16SourcePilotReducerError(
            "candidate set is incomplete or duplicated"
        )
    expected_set_hash = preregistration.get("candidate_set_sha256")
    if not isinstance(expected_set_hash, str) or len(expected_set_hash) != 64:
        raise B16SourcePilotReducerError("candidate set hash missing")
    sorted_candidates = sorted(
        cast(list[dict[str, object]], candidates),
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        ),
    )
    if _sha256(sorted_candidates) != expected_set_hash:
        raise B16SourcePilotReducerError("candidate set hash mismatch")
    prereg_pilot_indices = preregistration.get("pilot_indices")
    if (
        not isinstance(prereg_pilot_indices, (list, tuple))
        or tuple(prereg_pilot_indices) != FROZEN_PILOT_INDICES
    ):
        raise B16SourcePilotReducerError("pilot indices drift")
    for key in (
        "target_or_outcome_read",
        "research_labels_opened",
        "fresh_holdout_opened",
        "scientific_value_decided",
        "broker_mutation",
        "productive_authority",
    ):
        if preregistration.get(key) is not False:
            raise B16SourcePilotReducerError(
                f"forbidden preregistration state: {key}"
            )

    if raw_report.get("identity") != "SHARED_B16_SOURCE_PILOT_RAW_001":
        raise B16SourcePilotReducerError("unexpected raw pilot identity")
    if raw_report.get("candidate_set_sha256") != expected_set_hash:
        raise B16SourcePilotReducerError("raw pilot candidate-set drift")
    raw_pilot_indices = raw_report.get("pilot_indices")
    if (
        not isinstance(raw_pilot_indices, (list, tuple))
        or tuple(raw_pilot_indices) != FROZEN_PILOT_INDICES
    ):
        raise B16SourcePilotReducerError("raw pilot indices drift")
    for key in (
        "target_or_outcome_read",
        "research_labels_opened",
        "fresh_holdout_opened",
        "broker_mutation",
        "productive_authority",
    ):
        if raw_report.get(key) is not False:
            raise B16SourcePilotReducerError(f"forbidden raw state: {key}")

    reports = raw_report.get("candidate_reports")
    if not isinstance(reports, list) or len(reports) != 87:
        raise B16SourcePilotReducerError(
            "raw pilot must contain exact 87 candidate reports"
        )

    seen: set[tuple[str, int, str]] = set()
    reduced: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for raw in reports:
        if not isinstance(raw, dict):
            raise B16SourcePilotReducerError("raw candidate report invalid")
        row = cast(dict[str, Any], raw)
        candidate_key = _candidate_key(row)
        if candidate_key not in expected:
            raise B16SourcePilotReducerError(
                "raw report contains unpreregistered candidate"
            )
        if candidate_key in seen:
            raise B16SourcePilotReducerError(
                "raw report duplicates candidate"
            )
        seen.add(candidate_key)

        technical = row.get("technical_error")
        if type(technical) is not bool:
            raise B16SourcePilotReducerError(
                "candidate technical_error must be bool"
            )
        windows = row.get("window_reports")
        if not isinstance(windows, list):
            raise B16SourcePilotReducerError(
                "candidate window reports missing"
            )

        if technical:
            state = B16PilotCoverageState.TECHNICAL_ERROR
        else:
            if len(windows) != len(FROZEN_PILOT_INDICES):
                raise B16SourcePilotReducerError(
                    "nontechnical candidate must contain all five pilot windows"
                )
            by_index: dict[int, tuple[int, int]] = {}
            for window in windows:
                if not isinstance(window, dict):
                    raise B16SourcePilotReducerError("pilot window invalid")
                index = window.get("manifest_index")
                bid = window.get("bid_tick_count")
                ask = window.get("ask_tick_count")
                if (
                    type(index) is not int
                    or index not in FROZEN_PILOT_INDICES
                    or type(bid) is not int
                    or bid < 0
                    or type(ask) is not int
                    or ask < 0
                ):
                    raise B16SourcePilotReducerError(
                        "pilot window count/index invalid"
                    )
                if index in by_index:
                    raise B16SourcePilotReducerError(
                        "duplicate pilot window"
                    )
                by_index[index] = (bid, ask)
            if tuple(sorted(by_index)) != tuple(sorted(FROZEN_PILOT_INDICES)):
                raise B16SourcePilotReducerError(
                    "pilot window set incomplete"
                )
            values = tuple(by_index[index] for index in FROZEN_PILOT_INDICES)
            if all(bid > 0 and ask > 0 for bid, ask in values):
                state = B16PilotCoverageState.FULL_PILOT_HISTORY
            elif all(bid == 0 and ask == 0 for bid, ask in values):
                state = B16PilotCoverageState.NO_PILOT_HISTORY
            else:
                state = B16PilotCoverageState.PARTIAL_PILOT_HISTORY

        counts[state.value] += 1
        reduced.append(
            {
                "provider": candidate_key[0],
                "provider_symbol_id": candidate_key[1],
                "provider_symbol": candidate_key[2],
                "pilot_coverage_state": state.value,
                "full_r8_source_acquisition_authorized": (
                    state is B16PilotCoverageState.FULL_PILOT_HISTORY
                ),
                "scientific_value_decided": False,
                "sensor_admission_authority": False,
                "trade_priority_authority": False,
                "broker_mutation": False,
            }
        )

    if seen != expected:
        raise B16SourcePilotReducerError(
            "raw pilot omitted preregistered candidate"
        )
    reduced.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": "SHARED_B16_SOURCE_PILOT_REDUCTION_001",
        "candidate_count": 87,
        "candidate_set_sha256": expected_set_hash,
        "pilot_indices": FROZEN_PILOT_INDICES,
        "state_counts": dict(sorted(counts.items())),
        "records": reduced,
        "technical_error_as_absence": False,
        "partial_history_auto_retry_authorized": False,
        "target_or_outcome_read": False,
        "research_labels_opened": False,
        "scientific_value_decided": False,
        "sensor_admission_authority": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["reduction_fingerprint_sha256"] = _sha256(payload)
    return payload
