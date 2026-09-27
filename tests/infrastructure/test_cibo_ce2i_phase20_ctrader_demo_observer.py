from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_ctrader_demo_observer import (
    observe_ctrader_demo_phase20_batch,
)
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochAggregator,
    Phase20DecisionEpochSlot,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

OPENED_AT = datetime(2026, 9, 27, 19, 30, tzinfo=UTC)
DECISION_AT = OPENED_AT + timedelta(seconds=1)


def _batch():
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="demo-observer-vt31",
        qore_symbol="NAS100",
        provider_symbol="NDX100",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )
    observed = Phase20ForwardObservedOpportunity(
        provider_evidence_id="demo-provider-vt31",
        opportunity=opportunity,
        provider_observation=ProviderEconomicObservation(
            provider_key="ctrader-demo",
            qore_symbol="NAS100",
            provider_symbol="NDX100",
            bid=Decimal("100"),
            ask=Decimal("100"),
            contract_size=Decimal("1"),
            tick_size=Decimal("0.1"),
            tick_value=Decimal("1"),
            minimum_volume=Decimal("1"),
            maximum_volume=Decimal("10"),
            volume_step=Decimal("1"),
            margin_per_volume=Decimal("10"),
            commission_per_volume_usd=Decimal("0"),
            slippage_reserve_per_volume_usd=Decimal("0"),
            observed_at=OPENED_AT + timedelta(milliseconds=100),
        ),
        concentration_group="INDEX",
        concentration_risk_usd=Decimal("10"),
    )
    aggregator = Phase20DecisionEpochAggregator(
        epoch_scope="ctrader-demo:phase20d",
        opened_at=OPENED_AT,
        deadline_at=OPENED_AT + timedelta(seconds=2),
        expected_slots=(
            Phase20DecisionEpochSlot(
                slot_id="VT31_NAS100|NAS100",
                trader_id=TraderLineage.VT31_NAS100,
                qore_symbol="NAS100",
            ),
        ),
    )
    aggregator.record_candidate(
        slot_id="VT31_NAS100|NAS100",
        opportunity=observed,
        observed_at=OPENED_AT + timedelta(milliseconds=200),
    )
    return aggregator.seal(decision_at=DECISION_AT)


def test_ctrader_demo_observer_collects_forward_shadow_without_execution(
    tmp_path: Path,
) -> None:
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "forward.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )
    capital_state = VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="demo-base",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("1000"),
        ),
    )

    observation = observe_ctrader_demo_phase20_batch(
        batch=_batch(),
        evidence_store=evidence_store,
        policy_store=policy_store,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="ctrader-demo-free",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        account_state=CTraderDemoAccountState(
            balance=Decimal("1000"),
            equity=Decimal("1000"),
            margin=Decimal("0"),
            free_margin=Decimal("1000"),
            observed_at=DECISION_AT - timedelta(milliseconds=100),
        ),
        risk=risk,
        executed_risk_book=VersionedPhase20ExecutedRiskBook(
            generation=0
        ),
        open_position_ids=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        capital_state=capital_state,
        concentration_limit_by_group=(("INDEX", Decimal("1000")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0"),
            margin_utilization=Decimal("0"),
            drawdown_utilization=Decimal("0"),
            opportunity_count=1,
        ),
        current_step=0,
    )

    assert evidence_store.load().generation == 1
    assert policy_store.load().generation == 1
    assert observation.broker_mutation_performed is False
    assert observation.allocation_authority is False
    assert observation.risk_authority is False
    assert observation.execution_authority is False
    assert observation.collected.result.evidence.account_identity.provider_key == (
        "ctrader-demo"
    )
