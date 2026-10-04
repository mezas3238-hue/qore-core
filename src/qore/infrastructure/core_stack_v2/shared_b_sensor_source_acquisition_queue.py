"""Outcome-free source-acquisition queue for Architect-B6 B-16.

The queue decides only whether a sensor has enough provider/canonical identity
evidence to justify read-only source acquisition. It does not decide predictive
or scientific value and never prioritizes trades or capital.

Current rules:
- full real BID/ASK history -> source complete;
- partial real history -> explicit blindspot requiring separate governed
  preregistration before any retry/extension;
- identity-ready + no bound real history -> read-only acquisition candidate;
- identity not ready -> fail closed, do not acquire by provider name alone.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from enum import StrEnum
from typing import Any, Final, cast

EXPECTED_WORKLIST: Final = "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001"


class B16SourceAcquisitionState(StrEnum):
    SOURCE_COMPLETE = "SOURCE_COMPLETE"
    READY_FOR_SOURCE_ACQUISITION = "READY_FOR_SOURCE_ACQUISITION"
    PARTIAL_SOURCE_BLINDSPOT = "PARTIAL_SOURCE_BLINDSPOT"
    IDENTITY_BLOCKED_DO_NOT_ACQUIRE = "IDENTITY_BLOCKED_DO_NOT_ACQUIRE"


class B16SourceAcquisitionQueueError(ValueError):
    """B16 source-acquisition queue failed closed."""


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def build_b16_source_acquisition_queue(
    worklist: dict[str, object],
    *,
    provider_credentials_available: bool,
) -> dict[str, object]:
    if worklist.get("identity") != EXPECTED_WORKLIST:
        raise B16SourceAcquisitionQueueError(
            "unexpected B16 qualification worklist identity"
        )
    records = worklist.get("records")
    if not isinstance(records, list) or len(records) != 177:
        raise B16SourceAcquisitionQueueError(
            "B16 source queue requires exact 177 records"
        )
    if type(provider_credentials_available) is not bool:
        raise B16SourceAcquisitionQueueError(
            "provider credential availability must be bool"
        )
    if worklist.get("outcome_used") is not False:
        raise B16SourceAcquisitionQueueError(
            "outcome-aware worklist cannot drive acquisition"
        )
    if worklist.get("sensor_admission_authority") is not False:
        raise B16SourceAcquisitionQueueError(
            "admission-authoritative worklist cannot drive acquisition"
        )

    output: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    candidates: list[str] = []
    partials: list[str] = []

    for raw in records:
        if not isinstance(raw, dict):
            raise B16SourceAcquisitionQueueError("B16 worklist row invalid")
        row = cast(dict[str, Any], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        symbol = row.get("provider_symbol")
        identity_ready = row.get("identity_ready")
        source_status = row.get("real_source_evidence_status")
        if (
            not isinstance(provider, str)
            or not provider
            or type(symbol_id) is not int
            or symbol_id <= 0
            or not isinstance(symbol, str)
            or not symbol
            or type(identity_ready) is not bool
        ):
            raise B16SourceAcquisitionQueueError(
                "B16 worklist row identity drift"
            )

        if source_status == "FULL_REAL_BID_ASK_HISTORY_EVIDENCE":
            if not identity_ready:
                raise B16SourceAcquisitionQueueError(
                    "full source evidence exists without identity readiness"
                )
            state = B16SourceAcquisitionState.SOURCE_COMPLETE
            reason = "FULL_REAL_CAUSAL_HISTORY_ALREADY_BOUND"
        elif source_status == "PARTIAL_REAL_BID_ASK_HISTORY_EVIDENCE":
            if not identity_ready:
                raise B16SourceAcquisitionQueueError(
                    "partial source evidence exists without identity readiness"
                )
            state = B16SourceAcquisitionState.PARTIAL_SOURCE_BLINDSPOT
            reason = "PARTIAL_HISTORY_REQUIRES_SEPARATE_GOVERNED_PREREGISTRATION"
            partials.append(symbol)
        elif source_status == "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE":
            if identity_ready:
                state = B16SourceAcquisitionState.READY_FOR_SOURCE_ACQUISITION
                reason = (
                    "IDENTITY_READY__READ_ONLY_SOURCE_ACQUISITION_REQUIRED"
                )
                candidates.append(symbol)
            else:
                state = (
                    B16SourceAcquisitionState.IDENTITY_BLOCKED_DO_NOT_ACQUIRE
                )
                reason = "IDENTITY_NOT_PROVEN__PROVIDER_NAME_INSUFFICIENT"
        else:
            raise B16SourceAcquisitionQueueError(
                "unsupported source evidence status"
            )

        counts[state.value] += 1
        output.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "state": state.value,
                "reason": reason,
                "identity_ready": identity_ready,
                "real_source_evidence_status": source_status,
                "provider_credentials_available": (
                    provider_credentials_available
                ),
                "acquisition_execution_ready": (
                    state
                    is B16SourceAcquisitionState.READY_FOR_SOURCE_ACQUISITION
                    and provider_credentials_available
                ),
                "target_or_outcome_read": False,
                "scientific_value_decided": False,
                "trade_priority_authority": False,
                "sensor_admission_authority": False,
                "broker_mutation": False,
            }
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": "SHARED_B16_SOURCE_ACQUISITION_QUEUE_001",
        "sensor_count": 177,
        "state_counts": dict(sorted(counts.items())),
        "source_acquisition_candidate_count": len(candidates),
        "source_acquisition_candidate_symbols": tuple(candidates),
        "partial_source_blindspot_symbols": tuple(partials),
        "provider_credentials_available": provider_credentials_available,
        "execution_ready_candidate_count": (
            len(candidates) if provider_credentials_available else 0
        ),
        "execution_status": (
            "READY_FOR_READ_ONLY_ACQUISITION"
            if provider_credentials_available and candidates
            else "BLOCKED_MISSING_PROVIDER_CREDENTIALS"
            if candidates
            else "NO_SOURCE_ACQUISITION_CANDIDATES"
        ),
        "records": output,
        "selection_basis": "IDENTITY_AND_SOURCE_EVIDENCE_ONLY",
        "target_or_outcome_read": False,
        "research_labels_opened": False,
        "scientific_value_decided": False,
        "trade_priority_authority": False,
        "economic_priority_authority": False,
        "sensor_admission_authority": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["queue_fingerprint_sha256"] = _fingerprint(payload)
    return payload
