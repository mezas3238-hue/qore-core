from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningProposal,
    CiboReasoningRequest,
    CiboReasoningRuntime,
    CiboReasoningRuntimeError,
    CiboReasoningRuntimeValidationError,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAICiboReasoningConfiguration,
    OpenAICiboReasoningEngine,
    OpenAIResponsesTransportBoundary,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertaintyKind,
)

_NOW = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
_REQUEST_ID = UUID("81000000-0000-0000-0000-000000000001")
_REF = CiboCognitiveEvidenceRef("input:user-dialogue")


def _request() -> CiboReasoningRequest:
    return CiboReasoningRequest(
        request_id=_REQUEST_ID,
        subject_code="cibo.self-assessment",
        asked_at=_NOW,
        prompt="Assess your current cognitive readiness and state what you would do next.",
        evidence_refs=(_REF,),
        observations=("runtime.first-ignition",),
    )


def _proposal(
    *,
    used_evidence_refs: tuple[CiboCognitiveEvidenceRef, ...] = (_REF,),
) -> CiboReasoningProposal:
    return CiboReasoningProposal(
        directive=CiboExecutiveDirectiveKind.RECOMMEND,
        reasoning_mode=CiboReasoningMode.MAX,
        uncertainty_kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence_level=CiboConfidenceLevel.HIGH,
        used_evidence_refs=used_evidence_refs,
        response_text="CIBO can reason under governed evidence and should remain advisory.",
        recommendation_code="cibo.continue-governed-evaluation",
        limitations=("no-live-trader-input",),
    )


class _FakeEngine:
    def __init__(self, proposal: CiboReasoningProposal) -> None:
        self.proposal = proposal

    def reason(
        self,
        request: CiboReasoningRequest,
    ) -> Result[CiboReasoningProposal, CiboReasoningRuntimeError]:
        assert request == _request()
        return Success(self.proposal)


def test_runtime_converts_engine_proposal_into_validated_cibo_synthesis() -> None:
    result = CiboReasoningRuntime(engine=_FakeEngine(_proposal())).run(
        _request(),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.synthesis.directive is CiboExecutiveDirectiveKind.RECOMMEND
    assert result.value.synthesis.reasoning_mode is CiboReasoningMode.MAX
    assert result.value.synthesis.recommendation is not None
    assert (
        result.value.synthesis.recommendation.recommendation_code
        == "cibo.continue-governed-evaluation"
    )
    assert not hasattr(result.value.synthesis, "order")
    assert not hasattr(result.value.synthesis, "quantity")
    assert not hasattr(result.value.synthesis, "risk_approval")


def test_runtime_rejects_engine_invented_evidence() -> None:
    invented = CiboCognitiveEvidenceRef("evidence:invented")
    result = CiboReasoningRuntime(
        engine=_FakeEngine(_proposal(used_evidence_refs=(invented,)))
    ).run(
        _request(),
        synthesized_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboReasoningRuntimeValidationError)
    assert "invent" in str(result.error)


def test_proposal_rejects_secret_bearing_visible_response() -> None:
    with pytest.raises(CiboReasoningRuntimeValidationError):
        CiboReasoningProposal(
            directive=CiboExecutiveDirectiveKind.ABSTAIN,
            reasoning_mode=CiboReasoningMode.MAX,
            uncertainty_kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE,
            confidence_level=None,
            used_evidence_refs=(_REF,),
            response_text="token=abc123456 should never be retained",
        )


class _FakeOpenAITransport(OpenAIResponsesTransportBoundary):
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.payload: bytes | None = None
        self.seen_secret: SecretMaterial | None = None
        self.timeout_seconds: float | None = None

    def post_json(
        self,
        payload: bytes,
        *,
        api_key: SecretMaterial,
        timeout_seconds: float,
    ) -> Result[bytes, CiboReasoningRuntimeError]:
        self.payload = payload
        self.seen_secret = api_key
        self.timeout_seconds = timeout_seconds
        return Success(self.body)


def _openai_body() -> bytes:
    proposal = {
        "directive": "recommend",
        "reasoning_mode": "max",
        "uncertainty_kind": "bounded-confidence",
        "confidence_level": "high",
        "used_evidence_refs": ["input:user-dialogue"],
        "response_text": "I can reason under evidence and authority constraints.",
        "recommendation_code": "cibo.continue-governed-evaluation",
        "questions": [],
        "request_code": None,
        "limitations": ["no-live-trader-input"],
    }
    return json.dumps(
        {
            "id": "resp_test",
            "status": "completed",
            "output_text": json.dumps(proposal),
        }
    ).encode("utf-8")


def test_openai_engine_uses_max_reasoning_structured_output_and_store_false() -> None:
    transport = _FakeOpenAITransport(_openai_body())
    secret = SecretMaterial(b"sk-test-material-not-real")
    engine = OpenAICiboReasoningEngine(
        api_key=secret,
        transport=transport,
        configuration=OpenAICiboReasoningConfiguration(),
    )

    result = engine.reason(_request())

    assert isinstance(result, Success)
    assert result.value.reasoning_mode is CiboReasoningMode.MAX
    assert transport.payload is not None
    raw: object = json.loads(transport.payload.decode("utf-8"))
    assert isinstance(raw, dict)
    payload = cast(dict[str, object], raw)
    assert payload["model"] == "gpt-5.6-sol"
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "max"}
    text = cast(dict[str, object], payload["text"])
    response_format = cast(dict[str, object], text["format"])
    assert response_format["type"] == "json_schema"
    assert response_format["strict"] is True
    assert b"sk-test-material-not-real" not in transport.payload
    assert transport.seen_secret is secret


def test_openai_engine_repr_redacts_secret() -> None:
    secret = SecretMaterial(b"sk-test-material-not-real")
    engine = OpenAICiboReasoningEngine(
        api_key=secret,
        transport=_FakeOpenAITransport(_openai_body()),
    )
    rendered = repr(engine)
    assert "sk-test-material-not-real" not in rendered
    assert "<redacted>" in rendered
