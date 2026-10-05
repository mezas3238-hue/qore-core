from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingDecision,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_science_runtime_bridge import (
    CapitalScienceDirective,
)
from qore.infrastructure.cibo_economic_engine_wiring import CiboEconomicEngineRun
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveBrain,
    CiboExecutiveDirectiveKind,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_high_intelligence_context import (
    build_high_intelligence_context,
)
from qore.infrastructure.cibo_semantic_transport import (
    build_semantic_transport_payload,
)
from qore.infrastructure.cibo_sovereign_capital_runtime import (
    CiboSovereignCapitalDisposition,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

import qore.infrastructure.cibo_sovereign_capital_runtime as runtime


T0 = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="sovereign-signal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
        decision_context=(
            ("ctx_market_state", "trend"),
            ("ctx_structure_state", "displacement"),
        ),
    )


def _defer_synthesis():
    result = CiboExecutiveBrain().synthesize(
        synthesis_id=UUID("70000000-0000-0000-0000-000000000101"),
        directive=CiboExecutiveDirectiveKind.DEFER,
        reasoning_mode=CiboReasoningMode.HIGH,
        subject_code="sovereign-capital",
        synthesized_at=T0,
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:sovereign"),),
        uncertainty=CiboUncertainty(
            kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
        ),
    )
    assert isinstance(result, Success)
    return result.value


def test_high_intelligence_context_is_full_and_predecision_only() -> None:
    context = build_high_intelligence_context((_opportunity(),))

    assert len(context) == 1
    row = context[0]
    assert row["signal_fingerprint"] == "sovereign-signal"
    assert row["stop_loss_per_volume"] == "10"
    assert row["margin_per_volume"] == "20"
    assert row["decision_context"] == [
        ["ctx_market_state", "trend"],
        ["ctx_structure_state", "displacement"],
    ]
    assert "outcome" not in row
    assert "realized_pnl" not in row


def test_semantic_transport_preserves_full_semantics_without_authority() -> None:
    payload = build_semantic_transport_payload(
        {"regime": "trend", "confidence": Decimal("0.75")}
    )

    assert payload["semantic_transport"] == "FULL_CANONICAL_READ_ONLY"
    assert payload["result_semantics"] == {
        "regime": "trend",
        "confidence": "0.75",
    }
    assert payload["economic_authority"] is False
    assert payload["sizing_authority"] is False
    assert payload["risk_authority"] is False
    assert payload["execution_authority"] is False


def test_sovereign_cognitive_defer_blocks_risk_request(monkeypatch) -> None:
    opportunity = _opportunity()
    synthesis = _defer_synthesis()

    twin = object.__new__(CiboObservedEconomicTwin)
    object.__setattr__(twin, "captured_at", T0)
    object.__setattr__(
        twin,
        "opportunities",
        (
            SimpleNamespace(
                option_id="opt-r34",
                trader_id=opportunity.trader_id.value,
                qore_symbol=opportunity.qore_symbol,
            ),
        ),
    )

    consultation = object.__new__(CiboEconomicConsultationReceipt)
    science = object.__new__(CapitalScienceDirective)

    economic = object.__new__(CiboEconomicEngineRun)
    object.__setattr__(
        economic,
        "portfolio_plan",
        SimpleNamespace(
            lines=(
                SimpleNamespace(
                    option_id="opt-r34",
                    multiplier=1,
                    stop_risk_usd=Decimal("1"),
                    margin_usd=Decimal("2"),
                ),
            )
        ),
    )
    object.__setattr__(
        economic,
        "competition_plans",
        (
            SimpleNamespace(
                opportunity_id="opt-r34",
                admit_opportunity=True,
            ),
        ),
    )

    sizing = object.__new__(CiboAccountSizingDecision)
    object.__setattr__(
        sizing,
        "plan",
        CiboCapitalActionPlan(
            trader_id=opportunity.trader_id,
            qore_symbol=opportunity.qore_symbol,
            stage=CapitalStage.MINIMAL_SEED,
            action=CapitalAction.OPEN_MINIMAL_SEED,
            volume=Decimal("0.01"),
            stop_risk_usd=Decimal("0.10"),
            margin_usd=Decimal("0.20"),
            capital_source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            capital_source_amount_usd=Decimal("0.10"),
            reason="test sizing candidate",
        ),
    )

    monkeypatch.setattr(
        runtime,
        "_validate_capital_twin_alignment",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        runtime,
        "consult_cibo_economic_faculties",
        lambda **kwargs: consultation,
    )
    monkeypatch.setattr(
        runtime,
        "bind_cibo_cognition_to_twin",
        lambda twin, synthesis: twin,
    )
    monkeypatch.setattr(
        runtime,
        "run_cibo_economic_engine_chain",
        lambda **kwargs: economic,
    )
    monkeypatch.setattr(
        runtime,
        "plan_account_sizing",
        lambda **kwargs: sizing,
    )
    monkeypatch.setattr(
        runtime,
        "_build_capital_science_state",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        runtime,
        "evaluate_capital_science_predecision",
        lambda state: science,
    )

    decision = runtime.run_cibo_sovereign_capital_runtime(
        decision_id="decision-1",
        option_id="opt-r34",
        opportunity=opportunity,
        synthesis=synthesis,
        twin=twin,
        world_paths=(),
        option_schedules=(),
        mission_policy=object(),
        capital=object(),
        regime_state=object(),
        evidence_ref=object(),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
        request_id="risk-request-1",
        requested_at=T0,
        expires_at=datetime(2026, 10, 5, 12, 1, tzinfo=UTC),
    )

    assert decision.disposition is CiboSovereignCapitalDisposition.COGNITIVE_BLOCK
    assert decision.risk_request is None
    assert decision.final_plan.action is CapitalAction.HOLD
    assert decision.cognitive_consumed is True
    assert decision.qore_risk_sovereign is True
