from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    CiboAdaptiveReasoningRuntime,
    CiboReasoningEngineAdmission,
    CiboReasoningProviderEvidence,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
from qore.infrastructure.cibo_reasoning_policy import (
    CiboReasoningSituation,
    select_cibo_reasoning_route,
)
from qore.infrastructure.cibo_reasoning_runtime import (
    CiboReasoningProposal,
    cibo_reasoning_proposal_digest,
    cibo_reasoning_request_digest,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)
from qore.infrastructure.cibo_sovereign_reasoning_request import (
    build_sovereign_reasoning_request,
)
from qore.kernel.result import Result, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertaintyKind,
)


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _opp() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-maxcap-001",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("103"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("2"),
        decision_context=(
            ("ctx_regime", "trend"),
            ("ctx_volatility", "medium"),
            ("ctx_structure", "displacement"),
        ),
    )


def _faculty(code: str, faculty: str) -> object:
    semantic = {
        "result_type": "dict",
        "result_sha256": "sha256:" + code[-2:].lower().rjust(64, "0"),
        "semantic_transport": "FULL_CANONICAL_READ_ONLY",
        "advisory_only": True,
        "economic_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "result_semantics": {
            "state": "supportive",
            "function_code": code,
        },
    }
    return SimpleNamespace(
        function_code=code,
        faculty=SimpleNamespace(value=faculty),
        output_payload={
            "native_engine_called": True,
            "native_engine_name": "fixture",
            "native_engine_status": "SUCCESS",
            "native_engine_output": semantic,
            "evidence_status": "insufficient",
            "contribution_code": f"{code.lower()}-contribution",
        },
    )


def _consultation() -> object:
    rows = tuple(
        _faculty(f"CF{index:02d}", f"faculty-{index:02d}")
        for index in range(1, 20)
    )
    return SimpleNamespace(
        consultation_id="sha256:" + "a" * 64,
        decision_at=NOW,
        outcome_used=False,
        broker_mutation=False,
        opportunity_fingerprints=("signal-maxcap-001",),
        coordination_disposition="request-evidence",
        coordination_request_code="authority-rooted-evidence-required",
        mission_disposition="continue",
        faculty_receipts=rows,
    )


class _FakeRoutedEngine:
    def __init__(self, route) -> None:
        self.route = route
        self.seen_request = None

    def reason_with_evidence(self, request) -> Result:
        self.seen_request = request
        proposal = CiboReasoningProposal(
            directive=CiboExecutiveDirectiveKind.RECOMMEND,
            reasoning_mode=self.route.semantic_mode,
            uncertainty_kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
            confidence_level=CiboConfidenceLevel.HIGH,
            used_evidence_refs=request.evidence_refs,
            response_text=(
                "Current causal semantics support governed capital evaluation."
            ),
            recommendation_code="cibo.evaluate-capital",
            limitations=("qore-risk-remains-sovereign",),
        )
        digest = cibo_reasoning_request_digest(request)
        evidence = CiboReasoningProviderEvidence(
            route=self.route,
            provider_code="fixture",
            engine_code="fixture.reasoning",
            request_digest=digest,
            request_payload_digest="sha256:" + "1" * 64,
            response_digest="sha256:" + "2" * 64,
            configuration_fingerprint="sha256:" + "3" * 64,
            schema_fingerprint="sha256:" + "4" * 64,
            provider_response_ref="fixture-response",
            admitted_proposal_digest=cibo_reasoning_proposal_digest(proposal),
        )
        return Success(
            CiboReasoningEngineAdmission(
                proposal=proposal,
                provider_evidence=evidence,
            )
        )


def test_sovereign_reasoning_request_contains_context_and_all_faculties() -> None:
    request = build_sovereign_reasoning_request(
        consultation=_consultation(),
        opportunity=_opp(),
    )

    assert request.subject_code == "single-account-maxcap"
    assert "signal-maxcap-001" in request.prompt
    assert "ctx_regime" in request.prompt
    for index in range(1, 20):
        assert f"CF{index:02d}" in request.prompt
    assert "outcome" not in request.prompt.lower()
    assert "realized_pnl" not in request.prompt.lower()
    assert request.memory_refs == ()


def test_existing_adaptive_runtime_can_reason_from_sovereign_request() -> None:
    route = select_cibo_reasoning_route(
        CiboReasoningSituation(serious_controversy=True)
    )
    engine = _FakeRoutedEngine(route)
    runtime = CiboAdaptiveReasoningRuntime(engine=engine, route=route)
    request = build_sovereign_reasoning_request(
        consultation=_consultation(),
        opportunity=_opp(),
    )

    result = runtime.run(request, synthesized_at=NOW)

    assert isinstance(result, Success)
    assert engine.seen_request == request
    assert (
        result.value.runtime_result.synthesis.directive
        is CiboExecutiveDirectiveKind.RECOMMEND
    )
    assert (
        result.value.runtime_result.synthesis.reasoning_mode
        is CiboReasoningMode.MAX
    )
    assert result.value.runtime_result.synthesis.recommendation is not None
    assert not hasattr(result.value.runtime_result.synthesis, "quantity")
    assert not hasattr(result.value.runtime_result.synthesis, "risk_approval")
