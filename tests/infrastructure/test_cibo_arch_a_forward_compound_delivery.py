from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_arch_a_forward_compound_delivery import (
    build_arch_a_forward_compound_delivery,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
    PortfolioAllocationReservation,
    PortfolioAllocationReservationState,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_state import (
    CompoundCycleDeployment,
    CompoundCycleMarketRecord,
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    protect_compound_capital,
    settlement_sha256,
)
from qore.infrastructure.cibo_compound_market_cycle import (
    settle_compound_deployment,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 22, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="a-forward-compound",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _t19() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
    )


def _settlement(*, signal: str, position: int, deal: int, pnl: str):
    return apply_settlement(
        CmaSettlementState(
            signal_fingerprint=signal,
            position_id=position,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=deal,
            signal_fingerprint=signal,
            position_id=position,
            net_profit_usd=Decimal(pnl),
            position_open_after=False,
        ),
    )


def _settled_compound_state():
    origin = _settlement(
        signal="origin-signal",
        position=1001,
        deal=2001,
        pnl="20",
    )
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="origin-profit",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=origin,
    )
    state = classify_compound_capital(
        state,
        event_id="compoundable",
        occurred_at=T0 + timedelta(minutes=1),
        source_lot_id="origin-profit:gen1",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("20"),
    )
    state = classify_compound_capital(
        state,
        event_id="activate",
        occurred_at=T0 + timedelta(minutes=2),
        source_lot_id="compoundable:moved",
        to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        amount_usd=Decimal("20"),
    )

    reservation = PortfolioAllocationReservation(
        signal_fingerprint="compound-signal",
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        stop_risk_usd=Decimal("2"),
        margin_usd=Decimal("5"),
        concentration_group="EQUITY_BETA",
        concentration_risk_usd=Decimal("2"),
        state=PortfolioAllocationReservationState.ACTIVE,
    )
    t19 = replace(
        state.t19_ledger,
        reservations=state.t19_ledger.reservations + (reservation,),
    )
    source = state.compound_ledger.lot("activate:moved")
    ledger = state.compound_ledger.transition(
        source_lot_id=source.lot_id,
        to_state=CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
        amount_usd=Decimal("10"),
        moved_lot_id="market:deployed",
        remainder_lot_id="market:remainder",
        event_id="market:deploy",
        occurred_at=T0 + timedelta(minutes=3),
    )
    market = CompoundCycleMarketRecord(
        event_id="market",
        occurred_at=T0 + timedelta(minutes=3),
        decision_id="decision-compound",
        action="ALLOCATE",
        candidate_id="candidate-compound",
        amount_usd=Decimal("10"),
        scarcity_event_id="scarcity-1",
        portfolio_state_sha256="sha256:" + "8" * 64,
        t19_ledger_sha256="sha256:" + "9" * 64,
    )
    deployment = CompoundCycleDeployment(
        deployment_id="market:deployment",
        market_event_id="market",
        decision_id="decision-compound",
        candidate_id="candidate-compound",
        deployed_at=T0 + timedelta(minutes=3),
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="compound-signal",
        source_lot_id=source.lot_id,
        deployed_lot_id="market:deployed",
        amount_usd=Decimal("10"),
        source_generation=source.generation,
        stop_risk_usd=Decimal("2"),
        margin_usd=Decimal("5"),
    )
    state = replace(
        state,
        compound_ledger=ledger,
        t19_ledger=t19,
        market_records=state.market_records + (market,),
        deployments=state.deployments + (deployment,),
        event_ids=state.event_ids + ("market",),
        last_event_at=T0 + timedelta(minutes=3),
    )
    compound = _settlement(
        signal="compound-signal",
        position=1002,
        deal=2002,
        pnl="5",
    )
    state = settle_compound_deployment(
        state,
        event_id="compound-close",
        occurred_at=T0 + timedelta(minutes=10),
        deployment_id="market:deployment",
        settlement=compound,
    )
    state = protect_compound_capital(
        state,
        event_id="protect-next",
        occurred_at=T0 + timedelta(minutes=11),
        source_lot_id="compound-close:next-generation",
        amount_usd=Decimal("2"),
    )
    return state, origin, compound


def _row(
    *,
    decision_epoch: str,
    signal: str,
    fold: str,
    decision_at: datetime,
    outcome_at: datetime,
    settlement,
    risk_digit: str,
    provider_digit: str,
) -> ArchBForwardEconomicManifestRow:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    return ArchBForwardEconomicManifestRow(
        decision_epoch_id=decision_epoch,
        decision_evidence_sha256="sha256:" + risk_digit * 64,
        decision_at=decision_at,
        fold_id=fold,
        signal_fingerprint=signal,
        trader_id=TraderLineage.VT31_NAS100.value,
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        collector_git_sha="a" * 40,
        provider_key=_identity().provider_key,
        account_ref=_identity().account_ref,
        environment=_identity().environment.value,
        provider_evidence_id=f"provider-{signal}",
        qore_symbol="NAS100",
        provider_symbol="US100",
        provider_economics_sha256="sha256:" + provider_digit * 64,
        provider_observed_at=(decision_at - timedelta(seconds=1)).isoformat(),
        provider_contract_size=Decimal("1"),
        provider_tick_size=Decimal("1"),
        provider_tick_value=Decimal("1"),
        provider_minimum_volume=Decimal("0.01"),
        provider_volume_step=Decimal("0.01"),
        provider_margin_per_volume_usd=Decimal("1"),
        provider_commission_per_volume_usd=Decimal("0"),
        provider_slippage_reserve_per_volume_usd=Decimal("0"),
        provider_bid=Decimal("20000"),
        provider_ask=Decimal("20001"),
        policy_record_sha256="sha256:" + "3" * 64,
        policy_selected=True,
        baseline_policy_id=plan.baseline_policy_id,
        baseline_selected=True,
        execution_risk_evidence_id=f"risk-{signal}",
        executed_risk_sha256="sha256:" + "4" * 64,
        executed_source_volume=Decimal("0.01"),
        executed_initial_stop_risk_usd=Decimal("1"),
        settlement_sha256=settlement_sha256(settlement),
        settlement_deal_ids=tuple(item.deal_id for item in settlement.records),
        realized_net_pnl_usd=settlement.realized_net_pnl_usd,
        outcome_observed_at=outcome_at,
        release_evidence_sha256="sha256:" + "5" * 64,
        release_chain_sha256="sha256:" + "6" * 64,
        released_stop_risk_capacity_usd=Decimal("1"),
        released_margin_capacity_usd=Decimal("1"),
        terminal_release_at=outcome_at - timedelta(minutes=1),
        capital_minutes=Decimal("9"),
    )


def _manifest(origin, compound) -> ArchBForwardEconomicManifest:
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    rows = (
        _row(
            decision_epoch="origin",
            signal="origin-signal",
            fold="WF1",
            decision_at=T0 - timedelta(minutes=1),
            outcome_at=T0,
            settlement=origin,
            risk_digit="1",
            provider_digit="2",
        ),
        _row(
            decision_epoch="compound",
            signal="compound-signal",
            fold="WF2",
            decision_at=T0 + timedelta(minutes=3),
            outcome_at=T0 + timedelta(minutes=10),
            settlement=compound,
            risk_digit="7",
            provider_digit="8",
        ),
    )
    return ArchBForwardEconomicManifest(
        manifest_id=ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
        frozen_candidate_id=frozen.candidate_id,
        frozen_code_sha=frozen.code_sha,
        frozen_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_id=plan.plan_id,
        qualification_plan_sha256=phase20d_qualification_plan_sha256(),
        baseline_policy_id=plan.baseline_policy_id,
        qualification_status="NOT_READY",
        decision_epochs=2,
        candidate_rows=2,
        complete_lineage_rows=2,
        rows=rows,
        gaps=(),
        ready_for_scientific_consumption=False,
    )


def _source_ledger() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="origin-profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
        .add_source(
            source_id="compound-profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("5"),
        )
    )


_BINDINGS = (
    RealizedProfitEquivalenceBinding(
        source_id="origin-profit-source",
        admission_lot_ids=("origin-profit:gen1",),
    ),
    RealizedProfitEquivalenceBinding(
        source_id="compound-profit-source",
        admission_lot_ids=("compound-close:next-generation",),
    ),
)


def test_bridge_emits_existing_a_contract_with_derived_floor_evidence() -> None:
    state, origin, compound = _settled_compound_state()
    manifest = _manifest(origin, compound)

    delivery = build_arch_a_forward_compound_delivery(
        manifest=manifest,
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=state,
        realized_profit_bindings=_BINDINGS,
    )

    assert delivery.source_manifest_sha256 == manifest.fingerprint()
    assert delivery.exact_capital_truth_bound is True
    assert delivery.compound_episode_count == 1
    assert delivery.represented_folds == ("WF2",)
    assert delivery.ready_for_arch_a_compound_binding is False
    assert "FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in delivery.blockers
    assert "COMPOUND_FORWARD_FOUR_FOLD_COVERAGE_NOT_MET" in delivery.blockers

    record = delivery.records[0]
    assert record.deployment_id == "market:deployment"
    assert record.source_generation == 1
    assert record.deployed_capital_usd == Decimal("10")
    assert record.stop_risk_usd == Decimal("2")
    assert record.margin_usd == Decimal("5")
    assert record.realized_pnl_usd == Decimal("5")
    assert record.protected_floor_graduation_usd == Decimal("2")
    assert record.floor_evidence_sha256 is not None
    assert record.source_manifest_sha256 == manifest.fingerprint()
    assert record.cma_lineage_sha256 != record.terminal_settlement_sha256


def test_unrelated_open_deployment_does_not_destroy_settled_delivery() -> None:
    state, origin, compound = _settled_compound_state()
    open_deployment = CompoundCycleDeployment(
        deployment_id="open:deployment",
        market_event_id="open-market",
        decision_id="open-decision",
        candidate_id="open-candidate",
        deployed_at=T0 + timedelta(minutes=12),
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="open-signal",
        source_lot_id="unrelated-source",
        deployed_lot_id="unrelated-deployed",
        amount_usd=Decimal("1"),
        source_generation=1,
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("1"),
    )
    state = replace(
        state,
        deployments=state.deployments + (open_deployment,),
        last_event_at=T0 + timedelta(minutes=12),
    )

    delivery = build_arch_a_forward_compound_delivery(
        manifest=_manifest(origin, compound),
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=state,
        realized_profit_bindings=_BINDINGS,
    )

    assert delivery.compound_episode_count == 1
    assert delivery.records[0].deployment_id == "market:deployment"
