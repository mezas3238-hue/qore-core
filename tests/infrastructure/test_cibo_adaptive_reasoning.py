from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningPolicyError,
    CiboReasoningSituation,
    select_cibo_reasoning_mode,
)
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningRequest,
    CiboReasoningRuntimeError,
)
from qore.infrastructure.openai_cibo_adaptive_reasoning_engine import (
    OpenAICiboAdaptiveReasoningConfiguration,
    OpenAICiboAdaptiveReasoningEngine,
    provider_reasoning_effort_for_mode,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAICiboReasoningValidationError,
    OpenAIResponsesTransportBoundary,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboReasoningMode,
)

_NOW = datetime(2026, 9, 6, 0, 45, tzinfo=UTC)
_REQUEST_ID = UUID("82000000-0000-0000-0000-000000000001")
_REF = CiboCognitiveEvidenceRef("input:user-dialogue")


def _request() -> CiboReasoningRequest:
    return CiboReasoningRequest(
        request_id=_REQUEST_ID,
        subject_code="cibo.self-assessment",
        asked_at=_NOW,
        prompt="Assess the evidence and state the governed next step.",
        evidence_refs=(_REF,),
        observations=("runtime.adaptive-reasoning",),
    )


def _body(mode: CiboReasoningMode) -> bytes:
    proposal = {
        "directive": "recommend",
        "reasoning_mode": mode.value,
        "uncertainty_kind": "bounded-confidence",
        "confidence_level": "high",
        "used_evidence_refs": ["input:user-dialogue"],
        "response_text": "CIBO can reason under governed evidence and authority constraints.",
        "recommendation_code": "cibo.continue-governed-evaluation",
        "questions": [],
        "request_code": None,
        "limitations": ["no-live-trader-input"],
    }
    return json.dumps(
        {
            "id": "resp_adaptive_test",
            "status": "completed",
            "output_text": json.dumps(proposal),
        }
    ).encode("utf-8")


class _FakeTransport(OpenAIResponsesTransportBoundary):
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.payload: bytes | None = None
        self.seen_secret: SecretMaterial | None = None

    def post_json(
        self,
        payload: bytes,
        *,
        api_key: SecretMaterial,
        timeout_seconds: float,
    ) -> Result[bytes, CiboReasoningRuntimeError]:
        assert timeout_seconds > 0
        self.payload = payload
        self.seen_secret = api_key
        return Success(self.body)


def test_reasoning_policy_projects_routine_to_fast_and_escalates_explicitly() -> None:
    assert (
        select_cibo_reasoning_mode(CiboReasoningSituation())
        is CiboReasoningMode.FAST
    )
    assert (
        select_cibo_reasoning_mode(
            CiboReasoningSituation(serious_controversy=True)
        )
        is CiboReasoningMode.MAX
    )
    assert (
        select_cibo_reasoning_mode(
            CiboReasoningSituation(
                material_trader_disagreement=True,
                unresolved_after_ordinary_analysis=True,
                adversarial_council=True,
            )
        )
        is CiboReasoningMode.COUNCIL_ADVERSARIAL
    )


def test_reasoning_policy_rejects_runtime_type_laundering() -> None:
    with pytest.raises(CiboReasoningPolicyError):
        CiboReasoningSituation(serious_controversy=cast(bool, 1))


def test_legacy_adaptive_engine_remains_exact_sol_high_by_default() -> None:
    transport = _FakeTransport(_body(CiboReasoningMode.HIGH))
    secret = SecretMaterial(b"sk-test-adaptive-not-real")
    config = OpenAICiboAdaptiveReasoningConfiguration()
    engine = OpenAICiboAdaptiveReasoningEngine(
        api_key=secret,
        transport=transport,
        configuration=config,
    )

    result = engine.reason(_request())

    assert isinstance(result, Success)
    assert result.value.reasoning_mode is CiboReasoningMode.HIGH
    assert config.provider_reasoning_effort == "high"
    assert transport.payload is not None
    raw: object = json.loads(transport.payload.decode("utf-8"))
    assert isinstance(raw, dict)
    payload = cast(dict[str, object], raw)
    assert payload["model"] == "gpt-5.6-sol"
    assert payload["store"] is False
    assert payload["reasoning"] == {"effort": "high"}
    text = cast(dict[str, object], payload["text"])
    response_format = cast(dict[str, object], text["format"])
    schema = cast(dict[str, object], response_format["schema"])
    properties = cast(dict[str, object], schema["properties"])
    mode_schema = cast(dict[str, object], properties["reasoning_mode"])
    assert mode_schema["enum"] == ["high"]
    assert b"sk-test-adaptive-not-real" not in transport.payload
    assert transport.seen_secret is secret


def test_serious_controversy_routes_to_real_provider_max() -> None:
    mode = select_cibo_reasoning_mode(
        CiboReasoningSituation(serious_controversy=True)
    )
    config = OpenAICiboAdaptiveReasoningConfiguration(semantic_mode=mode)
    transport = _FakeTransport(_body(CiboReasoningMode.MAX))
    result = OpenAICiboAdaptiveReasoningEngine(
        api_key=SecretMaterial(b"sk-test-adaptive-not-real"),
        transport=transport,
        configuration=config,
    ).reason(_request())

    assert isinstance(result, Success)
    assert result.value.reasoning_mode is CiboReasoningMode.MAX
    assert config.provider_reasoning_effort == "max"
    assert transport.payload is not None
    payload = cast(
        dict[str, object],
        json.loads(transport.payload.decode("utf-8")),
    )
    assert payload["reasoning"] == {"effort": "max"}


def test_adversarial_council_preserves_semantic_mode_while_using_provider_max() -> None:
    mode = select_cibo_reasoning_mode(
        CiboReasoningSituation(
            material_trader_disagreement=True,
            unresolved_after_ordinary_analysis=True,
            adversarial_council=True,
        )
    )
    config = OpenAICiboAdaptiveReasoningConfiguration(semantic_mode=mode)
    transport = _FakeTransport(_body(CiboReasoningMode.COUNCIL_ADVERSARIAL))
    result = OpenAICiboAdaptiveReasoningEngine(
        api_key=SecretMaterial(b"sk-test-adaptive-not-real"),
        transport=transport,
        configuration=config,
    ).reason(_request())

    assert isinstance(result, Success)
    assert result.value.reasoning_mode is CiboReasoningMode.COUNCIL_ADVERSARIAL
    assert config.provider_reasoning_effort == "max"
    assert provider_reasoning_effort_for_mode(mode) == "max"


def test_adaptive_engine_fails_closed_when_provider_claims_wrong_reasoning_mode() -> None:
    engine = OpenAICiboAdaptiveReasoningEngine(
        api_key=SecretMaterial(b"sk-test-adaptive-not-real"),
        transport=_FakeTransport(_body(CiboReasoningMode.MAX)),
        configuration=OpenAICiboAdaptiveReasoningConfiguration(
            semantic_mode=CiboReasoningMode.HIGH
        ),
    )

    result = engine.reason(_request())

    assert isinstance(result, Failure)
    assert isinstance(result.error, OpenAICiboReasoningValidationError)
    assert "did not match" in str(result.error)


def test_adaptive_engine_repr_redacts_secret_and_reports_actual_route() -> None:
    engine = OpenAICiboAdaptiveReasoningEngine(
        api_key=SecretMaterial(b"sk-test-adaptive-not-real"),
        transport=_FakeTransport(_body(CiboReasoningMode.HIGH)),
    )
    rendered = repr(engine)
    assert "sk-test-adaptive-not-real" not in rendered
    assert "<redacted>" in rendered
    assert "semantic_mode='high'" in rendered
    assert "provider_reasoning_effort='high'" in rendered
