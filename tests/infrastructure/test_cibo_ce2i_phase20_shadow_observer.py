from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
    TraderLineage,
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
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochAggregator,
    Phase20DecisionEpochSlot,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_shadow_observer import (
    observe_phase20_forward_batch,
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
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

OPENED_AT = datetime(2026, 9, 27, 16, 15, tzinfo=UTC)
DECISION_AT = OPENED_AT + timedelta(milliseconds=500)


@dataclass(frozen=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("100")
    max_risk_at_any_time: Decimal = Decimal("100")
    active_mll: Decimal = Decimal("1000")
    hard_breach: bool = False


def _observed() -> Phase20ForwardObservedOpportunity:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="shadow-vt31",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
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
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id="provider:shadow-vt31",
        opportunity=opportunity,
        provider_observation=ProviderEconomicObservation(
            provider_key="ctrader",
            qore_symbol="NAS100",
            provider_symbol="NAS100",
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


def test_shadow_observer_persists_epoch_without_execution_authority(
    tmp_path: Path,
) -> None:
    aggregator = Phase20DecisionEpochAggregator(
        epoch_scope="ctrader:demo-forward:shadow",
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
        opportunity=_observed(),
        observed_at=OPENED_AT + timedelta(milliseconds=200),
    )
    batch = aggregator.seal(decision_at=DECISION_AT)

    reconciled_at = DECISION_AT - timedelta(milliseconds=100)
    account_snapshot = AccountRiskSnapshot(
        account_binding_id="demo-forward",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("2000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=_ProviderBudget(),
        reconciled_at=reconciled_at,
    )
    risk_constraints = RiskCapitalConstraintEnvelope(
        account_binding_id="demo-forward",
        aggregate_pre_order_worst_case_usd=Decimal("0"),
        active_reserved_stop_risk_usd=Decimal("0"),
        active_reserved_margin_usd=Decimal("0"),
        provider_remaining_headroom_usd=Decimal("100"),
        internal_qore_remaining_headroom_usd=Decimal("100"),
        max_risk_remaining_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("2000"),
        provider_hard_breach=False,
        survival_blocked=False,
        reason="canonical-shadow-risk",
        reconciled_at=reconciled_at,
    )
    capital_state = VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="base",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
    )
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )
    observation = observe_phase20_forward_batch(
        batch=batch,
        evidence_store=evidence_store,
        policy_store=policy_store,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader",
            account_ref="demo-forward",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        account_snapshot=account_snapshot,
        risk_constraints=risk_constraints,
        capital_state=capital_state,
        capital_captured_at=DECISION_AT - timedelta(milliseconds=50),
        concentration_limit_by_group=(("INDEX", Decimal("100")),),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.10"),
            margin_utilization=Decimal("0.10"),
            drawdown_utilization=Decimal("0.10"),
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
    assert (
        observation.collected.result.evidence.decision_epoch_id
        == batch.decision_epoch_id
    )



def test_shadow_observer_seals_zero_candidate_population_without_bias(
    tmp_path: Path,
) -> None:
    aggregator = Phase20DecisionEpochAggregator(
        epoch_scope="ctrader:demo-forward:zero-candidate",
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
    aggregator.record_non_candidate(
        slot_id="VT31_NAS100|NAS100",
        disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
        observed_at=OPENED_AT + timedelta(milliseconds=200),
        reason="CAUSAL_ABSTAIN",
    )
    batch = aggregator.seal(decision_at=DECISION_AT)

    reconciled_at = DECISION_AT - timedelta(milliseconds=100)
    account_snapshot = AccountRiskSnapshot(
        account_binding_id="demo-forward",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("2000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=_ProviderBudget(),
        reconciled_at=reconciled_at,
    )
    risk_constraints = RiskCapitalConstraintEnvelope(
        account_binding_id="demo-forward",
        aggregate_pre_order_worst_case_usd=Decimal("0"),
        active_reserved_stop_risk_usd=Decimal("0"),
        active_reserved_margin_usd=Decimal("0"),
        provider_remaining_headroom_usd=Decimal("100"),
        internal_qore_remaining_headroom_usd=Decimal("100"),
        max_risk_remaining_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("2000"),
        provider_hard_breach=False,
        survival_blocked=False,
        reason="canonical-shadow-risk",
        reconciled_at=reconciled_at,
    )
    capital_state = VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="base",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
    )
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )

    observation = observe_phase20_forward_batch(
        batch=batch,
        evidence_store=evidence_store,
        policy_store=policy_store,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader",
            account_ref="demo-forward",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        account_snapshot=account_snapshot,
        risk_constraints=risk_constraints,
        capital_state=capital_state,
        capital_captured_at=DECISION_AT - timedelta(milliseconds=50),
        concentration_limit_by_group=(),
        regime_state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.10"),
            margin_utilization=Decimal("0.10"),
            drawdown_utilization=Decimal("0.10"),
            opportunity_count=0,
        ),
        current_step=0,
    )

    assert evidence_store.load().generation == 1
    assert policy_store.load().generation == 1
    assert observation.collected.result.evidence.candidates == ()
    assert observation.collected.result.evidence.population_slots[0].reason == (
        "CAUSAL_ABSTAIN"
    )
