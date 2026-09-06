from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboAdaptiveReasoningRuntime,
    CiboReasoningRuntimeValidationError,
)
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningEpisodeState,
    CiboReasoningEvidenceQuality,
    CiboReasoningMateriality,
    CiboReasoningPolicyError,
    CiboReasoningRouteTier,
    CiboReasoningSituation,
    CiboReasoningUncertainty,
    select_cibo_reasoning_route,
)
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningRequest,
    CiboReasoningRuntimeError,
)
from qore.infrastructure.openai_cibo_reasoning_engine import (
    OpenAIResponsesTransportBoundary,
)
from qore.infrastructure.openai_cibo_routed_reasoning_engine import (
    OpenAICiboRoutedReasoningConfiguration,
    OpenAICiboRoutedReasoningEngine,
)
from qore.infrastructure.secret_resolution import SecretMaterial
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboReasoningMode,
)

_NOW = datetime(2026, 9, 6, 8, 0, tzinfo=UTC)
_DONE = datetime(2026, 9, 6, 8, 0, 2, tzinfo=UTC)
_REQUEST_ID = UUID("83000000-0000-0000-0000-000000000001")
_REF = CiboCognitiveEvidenceRef("input:user-dialogue")


def _request() -> CiboReasoningRequest:
    return CiboReasoningRequest(
        request_id=_REQUEST_ID,
        subject_code="cibo.router-evaluation",
        asked_at=_NOW,
        prompt="Assess the admitted evidence and produce the governed recommendation.",
        evidence_refs=(_REF,),
        observations=("runtime.router-492",),
    )


def _body(mode: CiboReasoningMode) -> bytes:
    proposal = {
        "directive": "recommend",
        "reasoning_mode": mode.value,
        "uncertainty_kind": "bounded-confidence",
        "confidence_level": "high",
        "used_evidence_refs": ["input:user-dialogue"],
        "response_text": "Proceed with governed evaluation while preserving Risk authority.",
        "recommendation_code": "cibo.continue-governed-evaluation",
        "questions": [],
        "request_code": None,
        "limitations": ["risk-authority-remains-external"],
    }
    return json.dumps(
        {
            "id": "resp_router_492",
            "status": "completed",
            "output_text": json.dumps(proposal),
        }
    ).encode("utf-8")


class _FakeTransport(OpenAIResponsesTransportBoundary):
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.payload: bytes | None = None
        self.calls = 0

    def post_json(
        self,
        payload: bytes,
        *,
        api_key: SecretMaterial,
        timeout_seconds: float,
    ) -> Result[bytes, CiboReasoningRuntimeError]:
        assert type(api_key) is SecretMaterial
        assert timeout_seconds > 0
        self.calls += 1
        self.payload = payload
        return Success(self.body)


def test_routine_and_voice_both_route_to_terra_medium() -> None:
    routine = select_cibo_reasoning_route(CiboReasoningSituation())
    voice = select_cibo_reasoning_route(CiboReasoningSituation(voice_channel=True))

    assert routine.tier is CiboReasoningRouteTier.TERRA_MEDIUM
    assert routine.model == "gpt-5.6-terra"
    assert routine.provider_reasoning_effort == "medium"
    assert routine.semantic_mode is CiboReasoningMode.FAST
    assert voice == routine


def test_router_selects_each_governed_escalation_tier_from_typed_signals() -> None:
    terra_high = select_cibo_reasoning_route(
        CiboReasoningSituation(
            materiality=CiboReasoningMateriality.MODERATE,
            uncertainty=CiboReasoningUncertainty.MODERATE,
        )
    )
    sol_high = select_cibo_reasoning_route(
        CiboReasoningSituation(materiality=CiboReasoningMateriality.MATERIAL)
    )
    sol_max = select_cibo_reasoning_route(
        CiboReasoningSituation(
            materiality=CiboReasoningMateriality.CRITICAL,
            uncertainty=CiboReasoningUncertainty.HIGH,
            serious_controversy=True,
        )
    )
    council = select_cibo_reasoning_route(
        CiboReasoningSituation(
            materiality=CiboReasoningMateriality.MATERIAL,
            material_trader_disagreement=True,
            unresolved_after_ordinary_analysis=True,
            adversarial_council=True,
        )
    )

    assert terra_high.tier is CiboReasoningRouteTier.TERRA_HIGH
    assert terra_high.model == "gpt-5.6-terra"
    assert terra_high.provider_reasoning_effort == "high"
    assert terra_high.semantic_mode is CiboReasoningMode.HIGH

    assert sol_high.tier is CiboReasoningRouteTier.SOL_HIGH
    assert sol_high.model == "gpt-5.6-sol"
    assert sol_high.provider_reasoning_effort == "high"
    assert sol_high.semantic_mode is CiboReasoningMode.HIGH

    assert sol_max.tier is CiboReasoningRouteTier.SOL_MAX
    assert sol_max.model == "gpt-5.6-sol"
    assert sol_max.provider_reasoning_effort == "max"
    assert sol_max.semantic_mode is CiboReasoningMode.MAX

    assert council.tier is CiboReasoningRouteTier.COUNCIL_ADVERSARIAL
    assert council.model == "gpt-5.6-sol"
    assert council.provider_reasoning_effort == "max"
    assert council.semantic_mode is CiboReasoningMode.COUNCIL_ADVERSARIAL


def test_limited_evidence_escalates_only_to_terra_high_when_not_material() -> None:
    route = select_cibo_reasoning_route(
        CiboReasoningSituation(
            evidence_quality=CiboReasoningEvidenceQuality.LIMITED,
        )
    )
    assert route.tier is CiboReasoningRouteTier.TERRA_HIGH


def test_council_requires_unresolved_material_trader_disagreement() -> None:
    with pytest.raises(CiboReasoningPolicyError):
        CiboReasoningSituation(adversarial_council=True)


def test_resolved_episode_deescalates_and_does_not_inherit_previous_max() -> None:
    previous = select_cibo_reasoning_route(
        CiboReasoningSituation(serious_controversy=True)
    )
    resolved = select_cibo_reasoning_route(
        CiboReasoningSituation(
            episode_state=CiboReasoningEpisodeState.RESOLVED,
            voice_channel=True,
        )
    )

    assert previous.tier is CiboReasoningRouteTier.SOL_MAX
    assert resolved.tier is CiboReasoningRouteTier.TERRA_MEDIUM
    assert resolved.routing_reason == "episode-resolved-deescalation"


def test_routed_engine_binds_exact_model_effort_schema_and_receipt() -> None:
    route = select_cibo_reasoning_route(CiboReasoningSituation())
    transport = _FakeTransport(_body(CiboReasoningMode.FAST))
    config = OpenAICiboRoutedReasoningConfiguration(route=route)
    engine = OpenAICiboRoutedReasoningEngine(
        api_key=SecretMaterial(b"sk-test-routed-not-real"),
        transport=transport,
        configuration=config,
    )

    result = CiboAdaptiveReasoningRuntime(engine=engine, route=route).run(
        _request(),
        synthesized_at=_DONE,
    )

    assert isinstance(result, Success)
    assert transport.calls == 1
    assert transport.payload is not None
    payload = cast(
        dict[str, object],
        json.loads(transport.payload.decode("utf-8")),
    )
    assert payload["model"] == "gpt-5.6-terra"
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["store"] is False

    adaptive = result.value
    assert adaptive.route == route
    assert adaptive.receipt.route == route
    assert adaptive.receipt.provider_response_ref == "resp_router_492"
    assert adaptive.receipt.request_digest.startswith("sha256:")
    assert adaptive.receipt.request_payload_digest.startswith("sha256:")
    assert adaptive.receipt.response_digest.startswith("sha256:")
    assert adaptive.receipt.configuration_fingerprint.startswith("sha256:")
    assert adaptive.receipt.schema_fingerprint.startswith("sha256:")
    assert adaptive.receipt.admitted_proposal_digest.startswith("sha256:")
    assert adaptive.receipt.started_at == _NOW
    assert adaptive.receipt.completed_at == _DONE
    assert adaptive.runtime_result.synthesis.reasoning_mode is CiboReasoningMode.FAST


def test_replay_uses_retained_proposal_without_second_provider_call() -> None:
    route = select_cibo_reasoning_route(
        CiboReasoningSituation(materiality=CiboReasoningMateriality.MATERIAL)
    )
    transport = _FakeTransport(_body(CiboReasoningMode.HIGH))
    engine = OpenAICiboRoutedReasoningEngine(
        api_key=SecretMaterial(b"sk-test-routed-not-real"),
        transport=transport,
        configuration=OpenAICiboRoutedReasoningConfiguration(route=route),
    )
    first = CiboAdaptiveReasoningRuntime(engine=engine, route=route).run(
        _request(),
        synthesized_at=_DONE,
    )
    assert isinstance(first, Success)
    assert transport.calls == 1

    replayed = CiboAdaptiveReasoningRuntime.replay(
        _request(),
        first.value.replay_record,
    )

    assert isinstance(replayed, Success)
    assert transport.calls == 1
    assert replayed.value.synthesis == first.value.runtime_result.synthesis
    assert replayed.value.response_text == first.value.runtime_result.response_text


def test_routed_engine_fails_closed_when_provider_claims_wrong_semantic_mode() -> None:
    route = select_cibo_reasoning_route(CiboReasoningSituation())
    engine = OpenAICiboRoutedReasoningEngine(
        api_key=SecretMaterial(b"sk-test-routed-not-real"),
        transport=_FakeTransport(_body(CiboReasoningMode.MAX)),
        configuration=OpenAICiboRoutedReasoningConfiguration(route=route),
    )

    result = CiboAdaptiveReasoningRuntime(engine=engine, route=route).run(
        _request(),
        synthesized_at=_DONE,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboReasoningRuntimeValidationError)


def test_routed_engine_repr_redacts_secret_and_reports_route() -> None:
    route = select_cibo_reasoning_route(CiboReasoningSituation())
    engine = OpenAICiboRoutedReasoningEngine(
        api_key=SecretMaterial(b"sk-test-routed-not-real"),
        transport=_FakeTransport(_body(CiboReasoningMode.FAST)),
        configuration=OpenAICiboRoutedReasoningConfiguration(route=route),
    )

    rendered = repr(engine)
    assert "sk-test-routed-not-real" not in rendered
    assert "<redacted>" in rendered
    assert "gpt-5.6-terra" in rendered
    assert "terra-medium" in rendered
    assert "medium" in rendered
