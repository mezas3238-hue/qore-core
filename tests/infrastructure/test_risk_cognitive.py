from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.risk_authority as risk_authority
import qore.infrastructure.risk_cognitive as risk_cognitive
from qore.kernel.result import Failure, Result, Success

_REQ_ID = UUID("52000000-0000-0000-0000-000000000001")
_ANALYSIS_ID = UUID("52000000-0000-0000-0000-000000000002")
_RECEIPT_ID = UUID("52000000-0000-0000-0000-000000000003")
_T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=UTC)
_CFG = risk_authority.compute_fingerprint("cognitive-config-v1")
_CONCLUSION = "advisory conclusion: exposure remains within policy"


def _fp(seed: str) -> risk_authority.RiskFingerprint:
    return risk_authority.compute_fingerprint(seed)


def _request(
    *,
    situation: risk_cognitive.RiskSituationKind = (
        risk_cognitive.RiskSituationKind.ORDINARY_MONITORING
    ),
    prompt: str = "explain the observed drawdown trend",
    source_refs: tuple[str, ...] = ("ref.alpha", "ref.beta"),
) -> risk_cognitive.CognitiveRequest:
    return risk_cognitive.CognitiveRequest(
        request_id=_REQ_ID,
        situation=situation,
        evidence_digest=_fp("evidence"),
        source_refs=source_refs,
        prompt=prompt,
    )


class _FakeTransport:
    def __init__(
        self,
        model: risk_cognitive.RiskCognitiveModel,
        effort: risk_cognitive.RiskCognitiveEffort,
        *,
        response_text: str = _CONCLUSION,
        provider: str = "fake-provider",
        provider_response_ref: str | None = None,
    ) -> None:
        self._model = model
        self._effort = effort
        self._response_text = response_text
        self._provider = provider
        self._provider_response_ref = provider_response_ref
        self.calls = 0

    def respond(
        self, request: risk_cognitive.CognitiveRequest
    ) -> Result[
        risk_cognitive.CognitiveTransportResult, risk_cognitive.RiskCognitiveError
    ]:
        self.calls += 1
        return Success(
            risk_cognitive.CognitiveTransportResult(
                provider=self._provider,
                model=self._model,
                effort=self._effort,
                response_text=self._response_text,
                provider_response_ref=self._provider_response_ref,
            )
        )


class _ExplodingTransport:
    """A transport that must never be invoked during replay."""

    def __init__(self) -> None:
        self.called = False

    def respond(
        self, request: risk_cognitive.CognitiveRequest
    ) -> Result[
        risk_cognitive.CognitiveTransportResult, risk_cognitive.RiskCognitiveError
    ]:
        self.called = True
        raise AssertionError("transport must not be called during replay")


def _build_analysis(
    *,
    analysis_id: UUID = _ANALYSIS_ID,
    receipt_id: UUID = _RECEIPT_ID,
) -> risk_cognitive.CognitiveAnalysis:
    request = _request()
    route = risk_cognitive.RiskCognitiveRoute(
        risk_cognitive.RiskCognitiveModel.TERRA, risk_cognitive.RiskCognitiveEffort.MEDIUM
    )
    receipt = risk_cognitive.CognitiveReceipt(
        receipt_id=receipt_id,
        provider="fake-provider",
        model=risk_cognitive.RiskCognitiveModel.TERRA,
        effort=risk_cognitive.RiskCognitiveEffort.MEDIUM,
        request_digest=risk_authority.compute_fingerprint(request.logical_values()),
        source_refs=request.source_refs,
        routing_fingerprint=risk_authority.compute_fingerprint(
            risk_cognitive.RiskCognitiveModel.TERRA.value,
            risk_cognitive.RiskCognitiveEffort.MEDIUM.value,
        ),
        config_fingerprint=_CFG,
        provider_response_ref=None,
        admitted_output_digest=risk_authority.compute_fingerprint(_CONCLUSION),
        completed_at=_T0,
    )
    return risk_cognitive.CognitiveAnalysis(
        analysis_id=analysis_id,
        route=route,
        situation=risk_cognitive.RiskSituationKind.ORDINARY_MONITORING,
        evidence_digest=request.evidence_digest,
        source_refs=request.source_refs,
        conclusion=_CONCLUSION,
        limitations=(),
        receipt=receipt,
        completed_at=_T0,
    )


def test_default_route_is_terra_medium() -> None:
    route = risk_cognitive.RiskCognitiveRoute()
    assert route.model is risk_cognitive.RiskCognitiveModel.TERRA
    assert route.effort is risk_cognitive.RiskCognitiveEffort.MEDIUM
    assert route.model.value == "gpt-5.6-terra"
    assert route.effort.value == "medium"

    default = risk_cognitive.route_for_situation(
        risk_cognitive.RiskSituationKind.ORDINARY_MONITORING
    )
    assert default.model is risk_cognitive.RiskCognitiveModel.TERRA
    assert default.effort is risk_cognitive.RiskCognitiveEffort.MEDIUM


@pytest.mark.parametrize(
    ("situation", "model", "effort"),
    [
        (
            risk_cognitive.RiskSituationKind.ORDINARY_MONITORING,
            risk_cognitive.RiskCognitiveModel.TERRA,
            risk_cognitive.RiskCognitiveEffort.MEDIUM,
        ),
        (
            risk_cognitive.RiskSituationKind.MATERIAL_AMBIGUITY,
            risk_cognitive.RiskCognitiveModel.TERRA,
            risk_cognitive.RiskCognitiveEffort.HIGH,
        ),
        (
            risk_cognitive.RiskSituationKind.CONTRADICTORY_SOURCES,
            risk_cognitive.RiskCognitiveModel.SOL,
            risk_cognitive.RiskCognitiveEffort.HIGH,
        ),
        (
            risk_cognitive.RiskSituationKind.EXCEPTIONAL_BREACH_RISK,
            risk_cognitive.RiskCognitiveModel.SOL,
            risk_cognitive.RiskCognitiveEffort.MAX,
        ),
    ],
)
def test_escalation_routing_maps_each_situation_exactly(
    situation: risk_cognitive.RiskSituationKind,
    model: risk_cognitive.RiskCognitiveModel,
    effort: risk_cognitive.RiskCognitiveEffort,
) -> None:
    route = risk_cognitive.route_for_situation(situation)
    assert route.model is model
    assert route.effort is effort


def test_de_escalation_is_a_pure_function_with_no_sticky_state() -> None:
    assert (
        risk_cognitive.route_for_situation(
            risk_cognitive.RiskSituationKind.CONTRADICTORY_SOURCES
        ).effort
        is risk_cognitive.RiskCognitiveEffort.HIGH
    )
    assert (
        risk_cognitive.route_for_situation(
            risk_cognitive.RiskSituationKind.EXCEPTIONAL_BREACH_RISK
        ).effort
        is risk_cognitive.RiskCognitiveEffort.MAX
    )

    # After any high/max situation, the original lower situation always maps
    # back to its lower route: there is no sticky high/max state.
    for _ in range(3):
        route = risk_cognitive.route_for_situation(
            risk_cognitive.RiskSituationKind.ORDINARY_MONITORING
        )
        assert route.model is risk_cognitive.RiskCognitiveModel.TERRA
        assert route.effort is risk_cognitive.RiskCognitiveEffort.MEDIUM


def test_route_for_situation_rejects_non_enum() -> None:
    with pytest.raises(risk_cognitive.RiskCognitiveValidationError):
        risk_cognitive.route_for_situation(
            cast(risk_cognitive.RiskSituationKind, "ordinary_monitoring")
        )


def test_analyze_matching_transport_binds_receipt_to_digests() -> None:
    transport = _FakeTransport(
        risk_cognitive.RiskCognitiveModel.TERRA,
        risk_cognitive.RiskCognitiveEffort.MEDIUM,
    )
    runtime = risk_cognitive.RiskCognitiveRuntime(transport, config_fingerprint=_CFG)
    request = _request()

    result = runtime.analyze(
        request,
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )

    assert isinstance(result, Success)
    analysis = result.value
    assert analysis.analysis_id == _ANALYSIS_ID
    assert analysis.route.model is risk_cognitive.RiskCognitiveModel.TERRA
    assert analysis.route.effort is risk_cognitive.RiskCognitiveEffort.MEDIUM
    assert analysis.conclusion == _CONCLUSION
    assert analysis.receipt.receipt_id == _RECEIPT_ID
    assert analysis.receipt.request_digest == risk_authority.compute_fingerprint(
        request.logical_values()
    )
    assert (
        analysis.receipt.admitted_output_digest
        == risk_authority.compute_fingerprint(_CONCLUSION)
    )
    assert analysis.receipt.routing_fingerprint == risk_authority.compute_fingerprint(
        risk_cognitive.RiskCognitiveModel.TERRA.value,
        risk_cognitive.RiskCognitiveEffort.MEDIUM.value,
    )
    assert analysis.receipt.config_fingerprint == _CFG
    assert transport.calls == 1


def test_transport_model_mismatch_is_failure() -> None:
    transport = _FakeTransport(
        risk_cognitive.RiskCognitiveModel.SOL,
        risk_cognitive.RiskCognitiveEffort.MEDIUM,
    )
    runtime = risk_cognitive.RiskCognitiveRuntime(transport, config_fingerprint=_CFG)
    result = runtime.analyze(
        _request(),
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, risk_cognitive.RiskCognitiveError)


def test_transport_effort_mismatch_is_failure() -> None:
    transport = _FakeTransport(
        risk_cognitive.RiskCognitiveModel.TERRA,
        risk_cognitive.RiskCognitiveEffort.HIGH,
    )
    runtime = risk_cognitive.RiskCognitiveRuntime(transport, config_fingerprint=_CFG)
    result = runtime.analyze(
        _request(),
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, risk_cognitive.RiskCognitiveError)


def test_transport_failure_is_propagated() -> None:
    class _FailingTransport:
        def respond(
            self, request: risk_cognitive.CognitiveRequest
        ) -> Result[
            risk_cognitive.CognitiveTransportResult, risk_cognitive.RiskCognitiveError
        ]:
            return Failure(
                risk_cognitive.RiskCognitiveError("provider unavailable")
            )

    runtime = risk_cognitive.RiskCognitiveRuntime(
        _FailingTransport(), config_fingerprint=_CFG
    )
    result = runtime.analyze(
        _request(),
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, risk_cognitive.RiskCognitiveError)


def test_replay_never_invokes_transport() -> None:
    transport = _FakeTransport(
        risk_cognitive.RiskCognitiveModel.TERRA,
        risk_cognitive.RiskCognitiveEffort.MEDIUM,
    )
    runtime = risk_cognitive.RiskCognitiveRuntime(transport, config_fingerprint=_CFG)
    result = runtime.analyze(
        _request(),
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )
    assert isinstance(result, Success)
    analysis = result.value
    assert transport.calls == 1

    ledger = risk_cognitive.CognitiveLedger((analysis,))
    assert ledger.replay(_ANALYSIS_ID) is analysis
    assert risk_cognitive.replay_analysis(ledger, _ANALYSIS_ID) is analysis
    assert ledger.replay(UUID("52000000-0000-0000-0000-000000000099")) is None
    # Replay made no additional provider calls.
    assert transport.calls == 1


def test_replay_does_not_call_transport() -> None:
    exploding = _ExplodingTransport()
    analysis = _build_analysis()
    ledger = risk_cognitive.CognitiveLedger((analysis,))

    assert ledger.replay(analysis.analysis_id) is analysis
    assert risk_cognitive.replay_analysis(ledger, analysis.analysis_id) is analysis
    assert exploding.called is False


def test_prompt_with_password_assignment_is_rejected() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _request(prompt="password=x")


def test_prompt_with_bearer_token_is_rejected() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _request(prompt="Authorization: Bearer abc123def456")


def test_prompt_with_control_characters_is_rejected() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _request(prompt="explain\nthe drawdown")


def test_request_rejects_secret_source_ref() -> None:
    with pytest.raises(risk_authority.RiskValidationError):
        _request(source_refs=("ref.alpha", "sk-abcdefgh"))


def test_response_text_with_secret_is_rejected() -> None:
    transport = _FakeTransport(
        risk_cognitive.RiskCognitiveModel.TERRA,
        risk_cognitive.RiskCognitiveEffort.MEDIUM,
        response_text="client_secret=abc123",
    )
    runtime = risk_cognitive.RiskCognitiveRuntime(transport, config_fingerprint=_CFG)
    result = runtime.analyze(
        _request(),
        analysis_id=_ANALYSIS_ID,
        receipt_id=_RECEIPT_ID,
        completed_at=_T0,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, risk_cognitive.RiskCognitiveError)


def test_transport_result_rejects_secret_response_ref() -> None:
    with pytest.raises(risk_cognitive.RiskCognitiveValidationError):
        risk_cognitive.CognitiveTransportResult(
            provider="fake-provider",
            model=risk_cognitive.RiskCognitiveModel.TERRA,
            effort=risk_cognitive.RiskCognitiveEffort.MEDIUM,
            response_text=_CONCLUSION,
            provider_response_ref="token=abc123def",
        )


def test_validate_no_secret_material_helper() -> None:
    risk_cognitive.validate_no_secret_material(
        "plain advisory text", field_name="text"
    )
    with pytest.raises(risk_cognitive.RiskCognitiveValidationError):
        risk_cognitive.validate_no_secret_material("password=abc", field_name="text")


def test_no_authority_symbols_in_module_namespace() -> None:
    import qore.infrastructure.risk_cognitive as module

    for name in ("RiskDecision", "RiskAuthorization", "RiskDecisionId"):
        assert not hasattr(module, name)
    # CIBO/Trader bypass: no formal decision entry point exists.
    assert not hasattr(module, "evaluate_risk_admission")
    assert not hasattr(module, "RiskDecision")


def test_cognitive_analysis_has_no_authority_fields() -> None:
    analysis_fields = {f.name for f in fields(risk_cognitive.CognitiveAnalysis)}
    receipt_fields = {f.name for f in fields(risk_cognitive.CognitiveReceipt)}
    assert analysis_fields == {
        "analysis_id",
        "route",
        "situation",
        "evidence_digest",
        "source_refs",
        "conclusion",
        "limitations",
        "receipt",
        "completed_at",
    }
    assert receipt_fields == {
        "receipt_id",
        "provider",
        "model",
        "effort",
        "request_digest",
        "source_refs",
        "routing_fingerprint",
        "config_fingerprint",
        "provider_response_ref",
        "admitted_output_digest",
        "completed_at",
    }
    for field_name in ("decision", "authorization", "decision_id"):
        assert field_name not in analysis_fields
        assert field_name not in receipt_fields


def test_exact_type_validation_rejects_bool_and_int() -> None:
    # The cognitive value objects carry no integer-typed fields, so the exact
    # runtime-type discipline is enforced on the UUID/str/enum fields instead:
    # bool/int are rejected wherever a UUID/str/enum is expected.
    with pytest.raises(risk_authority.RiskValidationError):
        risk_cognitive.CognitiveRequest(
            request_id=cast(UUID, True),
            situation=risk_cognitive.RiskSituationKind.ORDINARY_MONITORING,
            evidence_digest=_fp("evidence"),
            source_refs=("ref.alpha",),
            prompt="ok",
        )
    with pytest.raises(risk_authority.RiskValidationError):
        risk_cognitive.CognitiveRequest(
            request_id=cast(UUID, 123),
            situation=risk_cognitive.RiskSituationKind.ORDINARY_MONITORING,
            evidence_digest=_fp("evidence"),
            source_refs=("ref.alpha",),
            prompt="ok",
        )
    with pytest.raises(risk_authority.RiskValidationError):
        risk_cognitive.CognitiveRequest(
            request_id=_REQ_ID,
            situation=cast(
                risk_cognitive.RiskSituationKind, "ordinary_monitoring"
            ),
            evidence_digest=_fp("evidence"),
            source_refs=("ref.alpha",),
            prompt="ok",
        )
    with pytest.raises(risk_cognitive.RiskCognitiveValidationError):
        risk_cognitive.RiskCognitiveRoute(
            model=cast(risk_cognitive.RiskCognitiveModel, True),
            effort=risk_cognitive.RiskCognitiveEffort.MEDIUM,
        )
    with pytest.raises(risk_cognitive.RiskCognitiveValidationError):
        risk_cognitive.CognitiveTransportResult(
            provider=cast(str, True),
            model=risk_cognitive.RiskCognitiveModel.TERRA,
            effort=risk_cognitive.RiskCognitiveEffort.MEDIUM,
            response_text="ok",
            provider_response_ref=None,
        )
