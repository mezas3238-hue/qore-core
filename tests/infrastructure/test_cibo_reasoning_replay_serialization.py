from datetime import UTC, datetime
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
from qore.infrastructure.cibo_reasoning_replay_serialization import (
    cibo_reasoning_replay_record_from_payload,
    cibo_reasoning_replay_record_payload,
    cibo_reasoning_replay_record_sha256,
)
from qore.infrastructure.cibo_reasoning_runtime import CiboReasoningProposal
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertaintyKind,
)


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
DONE = datetime(2026, 10, 5, 12, 0, 2, tzinfo=UTC)


def _record() -> CiboReasoningReplayRecord:
    proposal = CiboReasoningProposal(
        directive=CiboExecutiveDirectiveKind.RECOMMEND,
        reasoning_mode=CiboReasoningMode.MAX,
        uncertainty_kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence_level=CiboConfidenceLevel.HIGH,
        used_evidence_refs=(
            CiboCognitiveEvidenceRef("cibo:consultation:abc"),
        ),
        response_text="Proceed with governed capital evaluation.",
        recommendation_code="cibo.evaluate-capital",
        limitations=("qore-risk-remains-sovereign",),
    )
    route = CiboReasoningRoute(
        tier=CiboReasoningRouteTier.SOL_MAX,
        semantic_mode=CiboReasoningMode.MAX,
        model="gpt-5.6-sol",
        provider_reasoning_effort="max",
        routing_reason="critical-material-uncertainty-or-serious-controversy",
    )
    receipt = CiboReasoningEngineReceipt(
        route=route,
        provider_code="openai",
        engine_code="openai.responses",
        request_digest="sha256:" + "1" * 64,
        request_payload_digest="sha256:" + "2" * 64,
        response_digest="sha256:" + "3" * 64,
        configuration_fingerprint="sha256:" + "4" * 64,
        schema_fingerprint="sha256:" + "5" * 64,
        provider_response_ref="resp-test",
        admitted_proposal_digest=cibo_reasoning_proposal_digest(proposal),
        started_at=NOW,
        completed_at=DONE,
    )
    return CiboReasoningReplayRecord(
        request_id=UUID("90000000-0000-0000-0000-000000000001"),
        proposal=proposal,
        receipt=receipt,
    )


def test_reasoning_replay_record_round_trips_exactly() -> None:
    record = _record()
    payload = cibo_reasoning_replay_record_payload(record)
    restored = cibo_reasoning_replay_record_from_payload(payload)

    assert restored == record
    assert (
        cibo_reasoning_replay_record_sha256(restored)
        == cibo_reasoning_replay_record_sha256(record)
    )


def test_reasoning_replay_payload_contains_no_secret_or_outcome_fields() -> None:
    payload = cibo_reasoning_replay_record_payload(_record())
    rendered = str(payload).lower()

    assert "api_key" not in rendered
    assert "secret" not in rendered
    assert "realized_pnl" not in rendered
    assert "future_outcome" not in rendered
    assert "broker_credential" not in rendered
