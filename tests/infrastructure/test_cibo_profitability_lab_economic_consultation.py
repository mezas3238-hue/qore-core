from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_profitability_lab_economic_consultation import (
    consult_cibo_economic_faculties,
)

T0 = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)


def _opportunity(
    signal: str,
    *,
    context: tuple[tuple[str, str], ...] = (
        ("ctx_market_state", "trend"),
        ("ctx_structure_state", "displacement"),
    ),
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint=signal,
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
        maximum_volume=Decimal("100"),
        decision_context=context,
    )


def _regime(count: int) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=count,
    )


def test_economic_consultation_puts_all_faculties_on_predecision_path() -> None:
    receipt = consult_cibo_economic_faculties(
        decision_at=T0,
        opportunities=(_opportunity("signal-1"),),
        regime_state=_regime(1),
    )

    assert len(receipt.consulted_faculties) == 19
    assert len(set(receipt.consulted_faculties)) == 19
    assert receipt.coordination_disposition == "request"
    assert receipt.coordination_request_code == "economic.evidence.request"
    assert receipt.mission_code == "cibo-economic-predecision"
    assert receipt.mission_faculties == receipt.consulted_faculties
    assert receipt.mission_disposition == "continue"
    assert receipt.mission_director_invoked is True
    assert receipt.functional_coordinator_invoked is True
    assert receipt.causal_predecision is True
    assert receipt.all_faculties_consulted is True
    assert receipt.economic_authority is False
    assert receipt.sizing_authority is False
    assert receipt.risk_authority is False
    assert receipt.execution_authority is False
    assert receipt.outcome_used is False
    assert receipt.broker_mutation is False
    assert receipt.consultation_id.startswith("sha256:")
    assert tuple(item.function_code for item in receipt.faculty_receipts) == tuple(
        f"CF{i:02d}" for i in range(1, 20)
    )
    assert len({item.faculty for item in receipt.faculty_receipts}) == 19
    assert len(
        {
            item.output_payload["contribution_code"]
            for item in receipt.faculty_receipts
        }
    ) == 19
    for item in receipt.faculty_receipts:
        assert item.input_payload
        assert item.output_payload
        high_context = item.input_payload["high_intelligence_context"]
        assert len(high_context) == 1
        assert high_context[0]["decision_context"] == [
            ["ctx_market_state", "trend"],
            ["ctx_structure_state", "displacement"],
        ]
        assert "outcome" not in high_context[0]
        assert "realized_pnl" not in high_context[0]
        assert item.input_sha256.startswith("sha256:")
        assert item.output_sha256.startswith("sha256:")
        assert item.downstream_consumer == "cibo-functional-coordinator"
        assert item.consumer_action == "contribution-coordinated"
        assert item.decision_context_effect == "evidence-request-context"
        assert item.advisory_only is True
        assert item.economic_authority is False
        assert item.sizing_authority is False
        assert item.risk_authority is False
        assert item.execution_authority is False
        assert item.outcome_used is False


def test_economic_cognitive_orchestration_is_deterministic() -> None:
    kwargs = {
        "decision_at": T0,
        "opportunities": (_opportunity("signal-1"), _opportunity("signal-2")),
        "regime_state": _regime(2),
    }
    left = consult_cibo_economic_faculties(**kwargs)
    right = consult_cibo_economic_faculties(**kwargs)

    assert left == right
    assert left.mission_director_invoked is True
    assert left.functional_coordinator_invoked is True
    assert left.mission_disposition == "continue"
    assert left.economic_authority is False
    assert left.sizing_authority is False
    assert left.risk_authority is False
    assert left.execution_authority is False
    assert left.outcome_used is False
    assert left.broker_mutation is False
    assert left.faculty_receipts == right.faculty_receipts

def test_consultation_identity_binds_full_causal_context() -> None:
    left = consult_cibo_economic_faculties(
        decision_at=T0,
        opportunities=(
            _opportunity(
                "signal-1",
                context=(("ctx_market_state", "trend"),),
            ),
        ),
        regime_state=_regime(1),
    )
    right = consult_cibo_economic_faculties(
        decision_at=T0,
        opportunities=(
            _opportunity(
                "signal-1",
                context=(("ctx_market_state", "range"),),
            ),
        ),
        regime_state=_regime(1),
    )

    assert left.consultation_id != right.consultation_id
    assert left.faculty_receipts != right.faculty_receipts
    assert all(item.outcome_used is False for item in left.faculty_receipts)
    assert all(item.outcome_used is False for item in right.faculty_receipts)
