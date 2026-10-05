from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
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
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
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


def _consultation():
    return consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(_opp(),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.NORMAL,
            risk_utilization=Decimal("0.10"),
            margin_utilization=Decimal("0.10"),
            drawdown_utilization=Decimal("0.00"),
            opportunity_count=1,
            position_path_adverse=False,
            evidence_stale=False,
        ),
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
