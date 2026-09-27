from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

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
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardObservedOpportunity,
    collect_phase20_forward_observed_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyError,
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_snapshots import (
    build_phase20_forward_snapshot_bundle,
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
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

DECISION_AT = datetime(2026, 9, 27, 15, 30, tzinfo=UTC)


@dataclass(frozen=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("100")
    max_risk_at_any_time: Decimal = Decimal("100")
    active_mll: Decimal = Decimal("1000")
    hard_breach: bool = False


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="demo-forward",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _snapshots():
    reconciled_at = DECISION_AT - timedelta(seconds=1)
    account = AccountRiskSnapshot(
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
    constraints = RiskCapitalConstraintEnvelope(
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
        reason="hard-constraints-observed",
        reconciled_at=reconciled_at,
    )
    capital = VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="base",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        ),
    )
    return build_phase20_forward_snapshot_bundle(
        account_snapshot=account,
        risk_constraints=constraints,
        capital_state=capital,
        captured_at=DECISION_AT - timedelta(milliseconds=500),
    )


def _observed() -> Phase20ForwardObservedOpportunity:
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="collector-vt31-1",
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
    provider = ProviderEconomicObservation(
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
        observed_at=DECISION_AT - timedelta(seconds=1),
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id="provider:collector-vt31-1",
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group="INDEX",
        concentration_risk_usd=Decimal("10"),
    )


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=1,
    )


def _collect(
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
):
    return collect_phase20_forward_observed_epoch(
        evidence_store=evidence_store,
        policy_store=policy_store,
        decision_at=DECISION_AT,
        account_identity=_identity(),
        snapshots=_snapshots(),
        concentration_limit_by_group=(("INDEX", Decimal("100")),),
        regime_state=_regime(),
        current_step=0,
        opportunities=(_observed(),),
    )


def test_forward_collector_persists_evidence_then_policy_decision(
    tmp_path: Path,
) -> None:
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )

    collected = _collect(evidence_store, policy_store)

    assert collected.evidence_generation == 1
    assert collected.policy_generation == 1
    evidence_book = evidence_store.load()
    policy_book = policy_store.load()
    assert len(evidence_book.decisions) == 1
    assert len(policy_book.decisions) == 1
    policy = policy_book.decisions[0]
    assert policy.evidence_sha256 == (
        collected.result.decision_record.evidence_sha256
    )
    assert policy.selected_signal_fingerprints == ("collector-vt31-1",)


def test_forward_collector_retry_is_idempotent_across_both_stores(
    tmp_path: Path,
) -> None:
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )

    first = _collect(evidence_store, policy_store)
    second = _collect(evidence_store, policy_store)

    assert first.result.evidence.evidence_id == second.result.evidence.evidence_id
    assert first.evidence_generation == second.evidence_generation == 1
    assert first.policy_generation == second.policy_generation == 1
    assert evidence_store.load().generation == 1
    assert policy_store.load().generation == 1


def test_forward_policy_store_rejects_record_without_sealed_evidence(
    tmp_path: Path,
) -> None:
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )
    real_evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "real-evidence.json"
    )
    real_policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "real-policy.json"
    )
    collected = _collect(real_evidence_store, real_policy_store)

    with pytest.raises(
        DurablePhase20ForwardPolicyError,
        match="no previously sealed evidence",
    ):
        policy_store.seal_policy_decision(
            collected.result.decision_record,
            evidence_store=evidence_store,
            expected_generation=0,
        )


def test_forward_policy_store_rejects_conflicting_policy_rewrite(
    tmp_path: Path,
) -> None:
    evidence_store = DurablePhase20ForwardEvidenceStore(
        tmp_path / "evidence.json"
    )
    policy_store = DurablePhase20ForwardPolicyStore(
        tmp_path / "policy.json"
    )
    collected = _collect(evidence_store, policy_store)
    record = collected.result.decision_record
    changed_allocator = replace(
        record.allocator_decision,
        reason=record.allocator_decision.reason + " changed",
    )
    changed_record = replace(
        record,
        allocator_decision=changed_allocator,
    )

    with pytest.raises(
        DurablePhase20ForwardPolicyError,
        match="conflicting forward policy decision rewrite",
    ):
        policy_store.seal_policy_decision(
            changed_record,
            evidence_store=evidence_store,
            expected_generation=1,
        )

    assert policy_store.load().generation == 1
