"""Canonical serialization for sealed CIBO reasoning replay records.

The replay record contains only the authority-free admitted proposal and its
provider provenance receipt. It never contains API credentials, hidden chain of
thought, broker credentials, order authority, or future trade outcome.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboReasoningEngineReceipt,
    CiboReasoningReplayRecord,
    cibo_reasoning_proposal_digest,
)
from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningRoute,
    CiboReasoningRouteTier,
)
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningProposal,
    CiboReasoningRuntimeValidationError,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertaintyKind,
)


def cibo_reasoning_replay_record_payload(
    record: CiboReasoningReplayRecord,
) -> dict[str, object]:
    if not isinstance(record, CiboReasoningReplayRecord):
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay serialization requires canonical replay record"
        )
    record.__post_init__()
    proposal = record.proposal
    receipt = record.receipt
    route = receipt.route
    return {
        "schema": "qore.cibo.reasoning-replay-record.v1",
        "request_id": str(record.request_id),
        "proposal": {
            "directive": proposal.directive.value,
            "reasoning_mode": proposal.reasoning_mode.value,
            "uncertainty_kind": proposal.uncertainty_kind.value,
            "confidence_level": (
                None
                if proposal.confidence_level is None
                else proposal.confidence_level.value
            ),
            "used_evidence_refs": [
                item.value for item in proposal.used_evidence_refs
            ],
            "response_text": proposal.response_text,
            "recommendation_code": proposal.recommendation_code,
            "questions": list(proposal.questions),
            "request_code": proposal.request_code,
            "limitations": list(proposal.limitations),
        },
        "receipt": {
            "route": {
                "tier": route.tier.value,
                "semantic_mode": route.semantic_mode.value,
                "model": route.model,
                "provider_reasoning_effort": (
                    route.provider_reasoning_effort
                ),
                "routing_reason": route.routing_reason,
            },
            "provider_code": receipt.provider_code,
            "engine_code": receipt.engine_code,
            "request_digest": receipt.request_digest,
            "request_payload_digest": receipt.request_payload_digest,
            "response_digest": receipt.response_digest,
            "configuration_fingerprint": (
                receipt.configuration_fingerprint
            ),
            "schema_fingerprint": receipt.schema_fingerprint,
            "provider_response_ref": receipt.provider_response_ref,
            "admitted_proposal_digest": (
                receipt.admitted_proposal_digest
            ),
            "started_at": receipt.started_at.isoformat(),
            "completed_at": receipt.completed_at.isoformat(),
        },
    }


def cibo_reasoning_replay_record_from_payload(
    payload: dict[str, Any],
) -> CiboReasoningReplayRecord:
    if not isinstance(payload, dict) or payload.get("schema") != (
        "qore.cibo.reasoning-replay-record.v1"
    ):
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay payload schema is invalid"
        )
    proposal_payload = payload.get("proposal")
    receipt_payload = payload.get("receipt")
    if not isinstance(proposal_payload, dict) or not isinstance(
        receipt_payload,
        dict,
    ):
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay payload sections are invalid"
        )
    route_payload = receipt_payload.get("route")
    if not isinstance(route_payload, dict):
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay route payload is invalid"
        )

    route = CiboReasoningRoute(
        tier=CiboReasoningRouteTier(str(route_payload["tier"])),
        semantic_mode=CiboReasoningMode(
            str(route_payload["semantic_mode"])
        ),
        model=str(route_payload["model"]),
        provider_reasoning_effort=str(
            route_payload["provider_reasoning_effort"]
        ),
        routing_reason=str(route_payload["routing_reason"]),
    )
    confidence_raw = proposal_payload.get("confidence_level")
    proposal = CiboReasoningProposal(
        directive=CiboExecutiveDirectiveKind(
            str(proposal_payload["directive"])
        ),
        reasoning_mode=CiboReasoningMode(
            str(proposal_payload["reasoning_mode"])
        ),
        uncertainty_kind=CiboUncertaintyKind(
            str(proposal_payload["uncertainty_kind"])
        ),
        confidence_level=(
            None
            if confidence_raw is None
            else CiboConfidenceLevel(str(confidence_raw))
        ),
        used_evidence_refs=tuple(
            CiboCognitiveEvidenceRef(str(item))
            for item in proposal_payload["used_evidence_refs"]
        ),
        response_text=str(proposal_payload["response_text"]),
        recommendation_code=(
            None
            if proposal_payload.get("recommendation_code") is None
            else str(proposal_payload["recommendation_code"])
        ),
        questions=tuple(
            str(item) for item in proposal_payload.get("questions", ())
        ),
        request_code=(
            None
            if proposal_payload.get("request_code") is None
            else str(proposal_payload["request_code"])
        ),
        limitations=tuple(
            str(item)
            for item in proposal_payload.get("limitations", ())
        ),
    )
    receipt = CiboReasoningEngineReceipt(
        route=route,
        provider_code=str(receipt_payload["provider_code"]),
        engine_code=str(receipt_payload["engine_code"]),
        request_digest=str(receipt_payload["request_digest"]),
        request_payload_digest=str(
            receipt_payload["request_payload_digest"]
        ),
        response_digest=str(receipt_payload["response_digest"]),
        configuration_fingerprint=str(
            receipt_payload["configuration_fingerprint"]
        ),
        schema_fingerprint=str(
            receipt_payload["schema_fingerprint"]
        ),
        provider_response_ref=str(
            receipt_payload["provider_response_ref"]
        ),
        admitted_proposal_digest=str(
            receipt_payload["admitted_proposal_digest"]
        ),
        started_at=_aware(str(receipt_payload["started_at"])),
        completed_at=_aware(str(receipt_payload["completed_at"])),
    )
    record = CiboReasoningReplayRecord(
        request_id=UUID(str(payload["request_id"])),
        proposal=proposal,
        receipt=receipt,
    )
    if receipt.admitted_proposal_digest != cibo_reasoning_proposal_digest(
        proposal
    ):
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay admitted proposal digest mismatch"
        )
    return record


def cibo_reasoning_replay_record_sha256(
    record: CiboReasoningReplayRecord,
) -> str:
    payload = cibo_reasoning_replay_record_payload(record)
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _aware(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboReasoningRuntimeValidationError(
            "reasoning replay timestamp must be timezone-aware"
        )
    return result
