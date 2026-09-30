from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_audit import (
    reconcile_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.cibo_compound_market_cycle import (
    apply_internal_capital_market_decision,
    settle_compound_deployment,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_RESERVE_ID,
    Genc6Action,
    Genc6CapitalEvidenceFact,
    Genc6EvidenceDirection,
    Genc6EvidenceKind,
    Genc6EvidenceUse,
    Genc6MarginalCapitalCandidate,
    Genc6ProviderCapitalActionEvidence,
    Genc6ReserveAlternative,
    build_capital_scarcity_event,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    evaluate_genc5_sequential_compounding_shadow,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    DurableGenc5SequentialCompoundingShadowStore,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 1, 30, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="compound-market-cycle",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _t19() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        concentration_limit_by_group=(
            ("EQUITY_BETA", Decimal("10")),
        ),
    )


def _settlement(
    *,
    signal: str,
    position_id: int,
    deal_id: int,
    pnl: str,
) -> CmaSettlementState:
    state = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=position_id,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=deal_id,
            signal_fingerprint=signal,
            position_id=position_id,
            net_profit_usd=Decimal(pnl),
            position_open_after=False,
        ),
    )


def _funded_compound_state() -> CiboCompoundCycleState:
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="origin-profit",
        occurred_at=T0 - timedelta(minutes=10),
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(
            signal="vt31-origin",
            position_id=1001,
            deal_id=2001,
            pnl="100",
        ),
    )
    state = protect_compound_capital(
        state,
        event_id="protect-origin",
        occurred_at=T0 - timedelta(minutes=9),
        source_lot_id="origin-profit:gen1",
        amount_usd=Decimal("40"),
    )
    state = policy_protect_floor(
        state,
        event_id="policy-floor",
        occurred_at=T0 - timedelta(minutes=8),
        tranche_id="protect-origin:tranche",
        policy_id="COMPOUND_MARKET_TEST_FLOOR",
        policy_sha256="sha256:" + "a" * 64,
    )
    state = classify_compound_capital(
        state,
        event_id="compoundable",
        occurred_at=T0 - timedelta(minutes=7),
        source_lot_id="protect-origin:remainder",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
    )
    return classify_compound_capital(
        state,
        event_id="activate",
        occurred_at=T0 - timedelta(minutes=6),
        source_lot_id="compoundable:moved",
        to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        amount_usd=Decimal("60"),
    )


def _marginal(
    *,
    state: CiboCompoundCycleState,
    trader: TraderLineage,
    signal: str,
    expected_return: str,
    stop_risk: str,
    margin: str,
    execution_cost: str,
    concentration: str,
    drawdown: str,
    optionality: str,
    duration: str,
    uncertainty: str,
) -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id=f"marginal-{signal}",
        decision_at=T0,
        account_identity=state.account_identity,
        trader_id=trader,
        signal_fingerprint=signal,
        source_opportunity_decision_sha256=(
            "sha256:" + ("1" if signal.endswith("a") else "2") * 64
        ),
        source_baseline_policy_record_sha256=(
            "sha256:" + ("3" if signal.endswith("a") else "4") * 64
        ),
        current_compound_capacity_usd=Decimal("60"),
        requested_incremental_capital_usd=Decimal("40"),
        expected_incremental_return_usd=Decimal(expected_return),
        incremental_stop_risk_usd=Decimal(stop_risk),
        incremental_margin_usd=Decimal(margin),
        incremental_execution_cost_usd=Decimal(execution_cost),
        incremental_concentration_risk_usd=Decimal(concentration),
        incremental_drawdown_risk_proxy_usd=Decimal(drawdown),
        incremental_optionality_consumed_usd=Decimal(optionality),
        expected_capital_minutes=Decimal(duration),
        epistemic_uncertainty=Decimal(uncertainty),
        provider_evidence_sha256="sha256:" + "5" * 64,
        expectation_evidence_sha256="sha256:" + "6" * 64,
        factor_evidence_sha256="sha256:" + "7" * 64,
        duration_evidence_sha256="sha256:" + "8" * 64,
        execution_evidence_sha256="sha256:" + "9" * 64,
        optionality_evidence_sha256="sha256:" + "c" * 64,
    )


def _fact(
    *,
    kind: Genc6EvidenceKind,
    value: Decimal,
    digit: str,
) -> Genc6CapitalEvidenceFact:
    direction = {
        Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL:
            Genc6EvidenceDirection.HIGHER_IS_BETTER,
        Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.CAPITAL_DURATION_MINUTES:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.MARGIN_PER_CAPITAL:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL:
            Genc6EvidenceDirection.LOWER_IS_BETTER,
        Genc6EvidenceKind.RESERVE_VALUE:
            Genc6EvidenceDirection.HIGHER_IS_BETTER,
    }[kind]
    model = (
        "COMPOUND_MARKET_VALUE_MODEL"
        if kind
        in {
            Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL,
            Genc6EvidenceKind.RESERVE_VALUE,
        }
        else None
    )
    return Genc6CapitalEvidenceFact(
        fact_id=f"fact-{kind.value}-{digit}",
        kind=kind,
        value=value,
        direction=direction,
        evidence_sha256="sha256:" + digit * 64,
        produced_at=T0 - timedelta(seconds=1),
        observed_at=T0 - timedelta(seconds=2),
        source="COMPOUND_MARKET_CAUSAL_EVIDENCE",
        policy_version="COMPOUND_MARKET_TEST_V1",
        calibration_lineage="COMPOUND_MARKET_CALIBRATION_V1",
        use=Genc6EvidenceUse.CAPITAL_ELIGIBLE,
        model_identity=model,
        calibrated=model is not None,
        oos_validated=model is not None,
    )


def _facts(
    evidence: MarginalCapitalUtilityEvidence,
    *,
    prefix: str,
) -> tuple[Genc6CapitalEvidenceFact, ...]:
    amount = evidence.requested_incremental_capital_usd
    return (
        _fact(
            kind=Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL,
            value=(
                evidence.expected_incremental_return_usd
                - evidence.incremental_execution_cost_usd
                - evidence.incremental_optionality_consumed_usd
            )
            / amount,
            digit=prefix,
        ),
        _fact(
            kind=Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY,
            value=evidence.epistemic_uncertainty,
            digit="d",
        ),
        _fact(
            kind=Genc6EvidenceKind.CAPITAL_DURATION_MINUTES,
            value=evidence.expected_capital_minutes,
            digit="e",
        ),
        _fact(
            kind=Genc6EvidenceKind.MARGIN_PER_CAPITAL,
            value=evidence.incremental_margin_usd / amount,
            digit="f",
        ),
        _fact(
            kind=Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL,
            value=evidence.incremental_execution_cost_usd / amount,
            digit="1",
        ),
        _fact(
            kind=Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL,
            value=evidence.incremental_concentration_risk_usd / amount,
            digit="2",
        ),
        _fact(
            kind=Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL,
            value=evidence.incremental_drawdown_risk_proxy_usd / amount,
            digit="3",
        ),
        _fact(
            kind=Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL,
            value=evidence.incremental_optionality_consumed_usd / amount,
            digit="4",
        ),
    )


def _candidate(
    *,
    tmp_path: Path,
    state: CiboCompoundCycleState,
    trader: TraderLineage,
    signal: str,
    expected_return: str,
    stop_risk: str,
    margin: str,
    execution_cost: str,
    concentration: str,
    drawdown: str,
    optionality: str,
    duration: str,
    uncertainty: str,
) -> Genc6MarginalCapitalCandidate:
    evidence = _marginal(
        state=state,
        trader=trader,
        signal=signal,
        expected_return=expected_return,
        stop_risk=stop_risk,
        margin=margin,
        execution_cost=execution_cost,
        concentration=concentration,
        drawdown=drawdown,
        optionality=optionality,
        duration=duration,
        uncertainty=uncertainty,
    )
    decision = evaluate_genc5_sequential_compounding_shadow(
        portfolio=state.core_portfolio,
        evidence=evidence,
        source_lot_id="activate:moved",
        decision_id=f"genc5-{signal}",
    )
    store = DurableGenc5SequentialCompoundingShadowStore(
        tmp_path / f"genc5-{signal}.json"
    )
    book = store.seal(
        decision,
        sealed_at=T0 + timedelta(seconds=1),
        expected_generation=0,
    )
    seal = book.seal_for_decision(f"genc5-{signal}")
    assert seal is not None

    symbol = "XAUUSD" if trader is TraderLineage.R34_XAUUSD else "NAS100"
    provider_symbol = (
        "XAUUSD" if trader is TraderLineage.R34_XAUUSD else "US100"
    )
    return Genc6MarginalCapitalCandidate(
        candidate_id=f"candidate-{signal}",
        account_identity=state.account_identity,
        trader_id=trader,
        qore_symbol=symbol,
        provider_symbol=provider_symbol,
        signal_fingerprint=signal,
        decision_at=T0,
        valid_from=T0 - timedelta(seconds=1),
        valid_until=T0 + timedelta(minutes=15),
        technical_valid=True,
        cancelled=False,
        marginal_unit_index=1,
        concentration_group="EQUITY_BETA",
        marginal_evidence=evidence,
        genc5_seal=seal,
        provider_action=Genc6ProviderCapitalActionEvidence(
            evidence_id=f"provider-{signal}",
            evidence_sha256="sha256:" + "5" * 64,
            produced_at=T0 - timedelta(seconds=1),
            observed_at=T0 - timedelta(seconds=2),
            source="COMPOUND_MARKET_PROVIDER_EVIDENCE",
            policy_version="COMPOUND_MARKET_PROVIDER_V1",
            account_identity=state.account_identity,
            qore_symbol=symbol,
            provider_symbol=provider_symbol,
            requested_capital_usd=Decimal("40"),
            executable_volume=Decimal("0.01"),
            minimum_executable_volume=Decimal("0.01"),
            maximum_volume=Decimal("100"),
            volume_step=Decimal("0.01"),
            minimum_execution_steps=1,
            projected_stop_risk_usd=evidence.incremental_stop_risk_usd,
            minimum_stop_risk_usd=Decimal("0.10"),
            projected_margin_usd=evidence.incremental_margin_usd,
            minimum_margin_usd=Decimal("1"),
            projected_execution_cost_usd=(
                evidence.incremental_execution_cost_usd
            ),
            feasible=True,
            use=Genc6EvidenceUse.CAPITAL_ELIGIBLE,
            reason="provider action is executable",
        ),
        comparable_facts=_facts(
            evidence,
            prefix="a" if signal.endswith("a") else "b",
        ),
    )


def _reserve() -> Genc6ReserveAlternative:
    return Genc6ReserveAlternative(
        alternative_id=GENC6_RESERVE_ID,
        account_identity=_identity(),
        decision_at=T0,
        evidence_facts=(
            _fact(
                kind=Genc6EvidenceKind.RESERVE_VALUE,
                value=Decimal("0.01"),
                digit="6",
            ),
        ),
    )


def test_compound_portfolio_icm_cycle_creates_cross_trader_gen2(
    tmp_path: Path,
) -> None:
    state = _funded_compound_state()
    dominant = _candidate(
        tmp_path=tmp_path,
        state=state,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-a",
        expected_return="9",
        stop_risk="1.5",
        margin="3",
        execution_cost="0.1",
        concentration="0.3",
        drawdown="0.3",
        optionality="0.2",
        duration="15",
        uncertainty="0.05",
    )
    inferior = _candidate(
        tmp_path=tmp_path,
        state=state,
        trader=TraderLineage.VT31_NAS100,
        signal="signal-b",
        expected_return="6",
        stop_risk="2.5",
        margin="6",
        execution_cost="0.3",
        concentration="0.8",
        drawdown="0.9",
        optionality="0.6",
        duration="45",
        uncertainty="0.20",
    )
    portfolio_state = build_genc6_portfolio_state(
        snapshot_id="compound-cycle-state",
        decision_at=T0,
        portfolio=state.core_portfolio,
        t19_ledger=state.t19_ledger,
    )
    scarcity = build_capital_scarcity_event(
        event_id="compound-scarcity",
        decision_at=T0,
        portfolio_state=portfolio_state,
        candidates=(dominant, inferior),
        reserve_alternative=_reserve(),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=scarcity,
        decision_id="compound-market-decision",
    )

    assert decision.treatment_action is Genc6Action.ALLOCATE_MARGINAL_UNIT
    assert decision.treatment_candidate_id == "candidate-signal-a"

    state = apply_internal_capital_market_decision(
        state,
        event_id="market-allocate",
        scarcity_event=scarcity,
        decision=decision,
        source_lot_id="activate:moved",
    )

    assert len(state.t19_ledger.active_reservations) == 1
    assert state.compound_ledger.balance(
        CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL
    ) == Decimal("40")
    assert state.compound_ledger.balance(
        CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
    ) == Decimal("20")

    state = settle_compound_deployment(
        state,
        event_id="r34-settlement",
        occurred_at=T0 + timedelta(minutes=30),
        deployment_id="market-allocate:deployment",
        settlement=_settlement(
            signal="signal-a",
            position_id=3001,
            deal_id=4001,
            pnl="30",
        ),
    )

    assert len(state.t19_ledger.active_reservations) == 0
    assert state.closing_realized_capital_usd == Decimal("230")
    assert state.accounting_identity_usd == Decimal("230")
    assert state.highest_generation == 2
    assert state.floor_ledger.policy_protected_floor_usd == Decimal("40")
    assert state.compound_ledger.balance(
        CompoundCapitalState.COMPOUNDABLE
    ) == Decimal("40")

    gen2 = state.compound_ledger.lot(
        "r34-settlement:next-generation"
    )
    assert gen2.generation == 2
    assert gen2.origin_trader is TraderLineage.R34_XAUUSD
    assert gen2.parent_lot_ids[-1] == "market-allocate:deployed"

    deployment = state.deployments[0]
    assert deployment.source_generation == 1
    assert deployment.trader_id is TraderLineage.R34_XAUUSD
    assert deployment.settled is True

    origin = next(
        item
        for item in state.compound_ledger.archived_lots
        if item.lot_id == "origin-profit:gen1"
    )
    assert origin.origin_trader is TraderLineage.VT31_NAS100

    audit = reconcile_compound_cycle(state)
    assert audit.accounting_integrity_pass is True
    assert audit.provenance_pass is True
    assert audit.no_double_counting_pass is True
    assert audit.no_unexplained_creation_pass is True
    assert audit.no_unexplained_destruction_pass is True
    assert audit.path_dependence_mechanics_pass is True
    assert audit.accounting_residual_usd == Decimal("0")
    assert audit.highest_generation == 2
    assert len(audit.generation_edges) == 1
    edge = audit.generation_edges[0]
    assert edge.parent_origin_trader is TraderLineage.VT31_NAS100
    assert edge.child_origin_trader is TraderLineage.R34_XAUUSD
    assert audit.economic_value_demonstrated is False
    assert audit.certification_ready is False


def test_compound_deployment_loss_consumes_compound_before_gen0(
    tmp_path: Path,
) -> None:
    state = _funded_compound_state()
    dominant = _candidate(
        tmp_path=tmp_path,
        state=state,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-a",
        expected_return="9",
        stop_risk="1.5",
        margin="3",
        execution_cost="0.1",
        concentration="0.3",
        drawdown="0.3",
        optionality="0.2",
        duration="15",
        uncertainty="0.05",
    )
    inferior = _candidate(
        tmp_path=tmp_path,
        state=state,
        trader=TraderLineage.VT31_NAS100,
        signal="signal-b",
        expected_return="6",
        stop_risk="2.5",
        margin="6",
        execution_cost="0.3",
        concentration="0.8",
        drawdown="0.9",
        optionality="0.6",
        duration="45",
        uncertainty="0.20",
    )
    portfolio_state = build_genc6_portfolio_state(
        snapshot_id="compound-loss-state",
        decision_at=T0,
        portfolio=state.core_portfolio,
        t19_ledger=state.t19_ledger,
    )
    scarcity = build_capital_scarcity_event(
        event_id="compound-loss-scarcity",
        decision_at=T0,
        portfolio_state=portfolio_state,
        candidates=(dominant, inferior),
        reserve_alternative=_reserve(),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=scarcity,
        decision_id="compound-loss-decision",
    )
    state = apply_internal_capital_market_decision(
        state,
        event_id="loss-allocation",
        scarcity_event=scarcity,
        decision=decision,
        source_lot_id="activate:moved",
    )
    state = settle_compound_deployment(
        state,
        event_id="loss-settlement",
        occurred_at=T0 + timedelta(minutes=30),
        deployment_id="loss-allocation:deployment",
        settlement=_settlement(
            signal="signal-a",
            position_id=3002,
            deal_id=4002,
            pnl="-15",
        ),
    )

    assert state.current_original_base_usd == Decimal("100")
    assert state.cumulative_realized_losses_usd == Decimal("15")
    assert state.compound_ledger.balance(
        CompoundCapitalState.CONSUMED
    ) == Decimal("15")
    assert state.compound_ledger.balance(
        CompoundCapitalState.COMPOUNDABLE
    ) == Decimal("25")
    assert state.closing_realized_capital_usd == Decimal("185")
    assert state.accounting_identity_usd == Decimal("185")

    audit = reconcile_compound_cycle(state)
    assert audit.consumed_compound_capital_usd == Decimal("15")
    assert audit.base_capital_loss_usd == Decimal("0")
    assert audit.accounting_residual_usd == Decimal("0")
    assert audit.no_unexplained_destruction_pass is True
