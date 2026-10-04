"""Preregistered source-only acquisition protocol for B-16 sensors.

The protocol freezes the candidate set and the five causal pilot windows before
any new provider history is queried. It is a source-evidence protocol only:
pilot success may authorize full R8 source acquisition, never scientific value,
sensor admission, trading or productive use.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Final, cast

EXPECTED_QUEUE: Final = "SHARED_B16_SOURCE_ACQUISITION_QUEUE_001"
EXPECTED_R8_MANIFEST_SHA256: Final = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)
FROZEN_PILOT_INDICES: Final = (0, 736, 1473, 2210, 2947)


class B16SourceAcquisitionPreregistrationError(ValueError):
    """B16 source-only preregistration failed closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def build_b16_source_acquisition_preregistration(
    queue: dict[str, object],
    *,
    preregistered_at: datetime,
) -> dict[str, object]:
    if queue.get("identity") != EXPECTED_QUEUE:
        raise B16SourceAcquisitionPreregistrationError(
            "unexpected B16 source queue identity"
        )
    if preregistered_at.tzinfo is None or preregistered_at.utcoffset() is None:
        raise B16SourceAcquisitionPreregistrationError(
            "preregistered_at must be timezone-aware"
        )
    queue_fp = queue.get("queue_fingerprint_sha256")
    if not isinstance(queue_fp, str) or len(queue_fp) != 64:
        raise B16SourceAcquisitionPreregistrationError(
            "source queue fingerprint missing"
        )
    int(queue_fp, 16)
    if queue.get("target_or_outcome_read") is not False:
        raise B16SourceAcquisitionPreregistrationError(
            "outcome-aware queue cannot be preregistered"
        )
    if queue.get("scientific_value_decided") is not False:
        raise B16SourceAcquisitionPreregistrationError(
            "scientific-value-selected queue cannot be preregistered"
        )
    records = queue.get("records")
    if not isinstance(records, list) or len(records) != 177:
        raise B16SourceAcquisitionPreregistrationError(
            "source queue must contain exact 177 records"
        )

    candidates: list[dict[str, object]] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise B16SourceAcquisitionPreregistrationError(
                "source queue row invalid"
            )
        row = cast(dict[str, Any], raw)
        if row.get("state") != "READY_FOR_SOURCE_ACQUISITION":
            continue
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
            or row.get("identity_ready") is not True
            or row.get("real_source_evidence_status")
            != "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE"
        ):
            raise B16SourceAcquisitionPreregistrationError(
                "candidate does not satisfy frozen source-acquisition prerequisites"
            )
        candidates.append(
            {
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
            }
        )

    candidates.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    declared_count = queue.get("source_acquisition_candidate_count")
    if declared_count != len(candidates):
        raise B16SourceAcquisitionPreregistrationError(
            "candidate count disagrees with queue records"
        )
    if len(candidates) != 87:
        raise B16SourceAcquisitionPreregistrationError(
            "current frozen B16 acquisition population must be exact 87"
        )

    candidate_set_sha256 = _sha256(candidates)
    payload: dict[str, object] = {
        "identity": "SHARED_B16_SOURCE_ACQUISITION_PREREGISTRATION_001",
        "preregistered_at": preregistered_at.isoformat(),
        "source_queue_fingerprint_sha256": queue_fp,
        "candidate_count": len(candidates),
        "candidate_set_sha256": candidate_set_sha256,
        "candidates": candidates,
        "r8_source_manifest_sha256": EXPECTED_R8_MANIFEST_SHA256,
        "pilot_indices": FROZEN_PILOT_INDICES,
        "quote_sides": ("BID", "ASK"),
        "pilot_classification_law": {
            "FULL_PILOT_HISTORY": (
                "BID_COUNT_GT_0_AND_ASK_COUNT_GT_0_AT_ALL_5_FROZEN_WINDOWS"
            ),
            "NO_PILOT_HISTORY": (
                "BID_COUNT_EQ_0_AND_ASK_COUNT_EQ_0_AT_ALL_5_FROZEN_WINDOWS"
            ),
            "PARTIAL_PILOT_HISTORY": "ANY_OTHER_NON_TECHNICAL_PATTERN",
            "TECHNICAL_ERROR": "UNKNOWN_DO_NOT_CLASSIFY_AS_NO_HISTORY",
        },
        "full_r8_acquisition_authorization_law": (
            "ONLY_FULL_PILOT_HISTORY_MAY_PROCEED_TO_FULL_R8_SOURCE_ACQUISITION"
        ),
        "partial_history_auto_retry_authorized": False,
        "technical_error_as_absence_authorized": False,
        "candidate_removal_after_observation_authorized": False,
        "candidate_addition_after_observation_authorized": False,
        "target_or_outcome_read": False,
        "research_labels_opened": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_value_decided": False,
        "sensor_admission_authority": False,
        "trade_priority_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["preregistration_fingerprint_sha256"] = _sha256(payload)
    return payload
