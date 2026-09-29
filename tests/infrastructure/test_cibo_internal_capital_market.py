from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_MARKET_ID,
    GENC6_POLICY_FROZEN_AT,
    GENC6_POLICY_ID,
    GENC6_RESERVE_ID,
    Genc6Action,
    Genc6CapitalEvidenceFact,
    Genc6EvidenceDirection,
    Genc6EvidenceKind,
    Genc6EvidenceUse,
    Genc6MarginalCapitalCandidate,
    Genc6ReserveAlternative,
    build_capital_scarcity_event,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
    genc6_policy_sha256,
)
from qore.infrastructure.cibo_internal_capital_market_oos_binding import (
    Genc6OosBindingStatus,
    bind_genc6_to_causal_outcomes,
)
from qore.infrastructure.cibo_internal_capital_market_population import (
    Genc6PopulationStatus,
    describe_genc6_fresh_scarcity_population,
)
from qore.infrastructure.cibo_internal_capital_market_store import (
    DurableGenc6InternalCapitalMarketStore,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence import (
    MarginalCapitalUtilityEvidence,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    DurableGenc4MarginalEvidenceStore,
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

T0 = datetime(2026, 9, 29, 20, 5, tzinfo=UTC)


def _identity(account_ref: str = "genc6-demo") -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _portfolio(
    *,
    account_ref: str = "genc6-demo",
) -> tuple[AccountCoreCompoundPortfolio, str]:
    identity = _identity(account_ref)
    realized = create_realized_profit_lot(
        CompoundRealizedProfitEvidence(
            evidence_id=f"settlement-{account_ref}",
            account_identity=identity,
            origin_trader=TraderLineage.VT31_NAS100,
            signal_fingerprint=f"origin-{account_ref}",
            position_id=1001,
            settlement_deal_ids=(2001,),
            realized_net_profit_usd=Decimal("100"),
            realized_at=T0 - timedelta(minutes=10),
            source_settlement_sha256="sha256:" + "a" * 64,
            settlement_reconciled=True,
            position_closed=True,
        ),
        lot_id=f"realized-{account_ref}",
        created_at=T0 - timedelta(minutes=9),
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        realized,
        event_id=f"admit-{account_ref}",
        occurred_at=T0 - timedelta(minutes=8),
    )
    ledger = ledger.transition(
        source_lot_id=realized.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id=f"floor-{account_ref}",
        remainder_lot_id=f"remaining-{account_ref}",
        event_id=f"protect-{account_ref}",
        occurred_at=T0 - timedelta(minutes=7),
    )
    ledger = ledger.transition(
        source_lot_id=f"remaining-{account_ref}",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
        moved_lot_id=f"compoundable-{account_ref}",
        event_id=f"compoundable-{account_ref}",
        occurred_at=T0 - timedelta(minutes=6),
    )
    floor = ProtectedCapitalFloorLedger(
        account_identity=identity
    ).admit_retired_lot(
        ledger.lot(f"floor-{account_ref}"),
        tranche_id=f"floor-tranche-{account_ref}",
        event_id=f"floor-admit-{account_ref}",
        admitted_at=T0 - timedelta(minutes=5),
    )
    floor = floor.upgrade_to_policy_protected(
        tranche_id=f"floor-tranche-{account_ref}",
        event_id=f"floor-policy-{account_ref}",
        occurred_at=T0 - timedelta(minutes=4),
        policy_id="GEN-C2-GENC6-TEST",
        policy_sha256="sha256:" + "b" * 64,
    )
    return (
        AccountCoreCompoundPortfolio(
            account_identity=identity,
            compound_ledger=ledger,
            protected_floor_ledger=floor,
        ),
        f"compoundable-{account_ref}",
    )


def _marginal(
    *,
    portfolio: AccountCoreCompoundPortfolio,
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
    request: str = "40",
) -> MarginalCapitalUtilityEvidence:
    return MarginalCapitalUtilityEvidence(
        evidence_id=f"marginal-{signal}",
        decision_at=T0,
        account_identity=portfolio.account_identity,
        trader_id=trader,
        signal_fingerprint=signal,
        source_opportunity_decision_sha256=(
            "sha256:" + ("1" if signal.endswith("a") else "2") * 64
        ),
        source_baseline_policy_record_sha256=(
            "sha256:" + ("3" if signal.endswith("a") else "4") * 64
        ),
        current_compound_capacity_usd=Decimal("60"),
        requested_incremental_capital_usd=Decimal(request),
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
    sha_digit: str,
    use: Genc6EvidenceUse = Genc6EvidenceUse.CAPITAL_ELIGIBLE,
) -> Genc6CapitalEvidenceFact:
    return Genc6CapitalEvidenceFact(
        fact_id=f"fact-{kind.value}-{sha_digit}",
        kind=kind,
        value=value,
        direction={
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
            Genc6EvidenceKind.PROVIDER_CONSTRAINT_PRESSURE:
                Genc6EvidenceDirection.LOWER_IS_BETTER,
        }[kind],
        evidence_sha256="sha256:" + sha_digit * 64,
        produced_at=T0 - timedelta(seconds=2),
        observed_at=T0 - timedelta(seconds=1),
        source="GENC6_TEST_CAUSAL_SOURCE",
        policy_version="GENC6_TEST_V1",
        calibration_lineage="GENC6_TEST_CALIBRATION_V1",
        use=use,
        model_identity=(
            "GENC6_EXPECTATION_TEST_MODEL"
            if kind is Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL
            else None
        ),
        calibrated=(
            kind is Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL
            and use is Genc6EvidenceUse.CAPITAL_ELIGIBLE
        ),
        oos_validated=(
            kind is Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL
            and use is Genc6EvidenceUse.CAPITAL_ELIGIBLE
        ),
    )


def _facts(
    evidence: MarginalCapitalUtilityEvidence,
    *,
    prefix: str,
    expected_use: Genc6EvidenceUse = Genc6EvidenceUse.CAPITAL_ELIGIBLE,
) -> tuple[Genc6CapitalEvidenceFact, ...]:
    amount = evidence.requested_incremental_capital_usd
    return (
        _fact(
            kind=Genc6EvidenceKind.EXPECTED_NET_VALUE_PER_CAPITAL,
            value=evidence.expected_incremental_return_usd / amount,
            sha_digit=prefix,
            use=expected_use,
        ),
        _fact(
            kind=Genc6EvidenceKind.EPISTEMIC_UNCERTAINTY,
            value=evidence.epistemic_uncertainty,
            sha_digit="d",
        ),
        _fact(
            kind=Genc6EvidenceKind.CAPITAL_DURATION_MINUTES,
            value=evidence.expected_capital_minutes,
            sha_digit="e",
        ),
        _fact(
            kind=Genc6EvidenceKind.MARGIN_PER_CAPITAL,
            value=evidence.incremental_margin_usd / amount,
            sha_digit="f",
        ),
        _fact(
            kind=Genc6EvidenceKind.EXECUTION_COST_PER_CAPITAL,
            value=evidence.incremental_execution_cost_usd / amount,
            sha_digit="1",
        ),
        _fact(
            kind=Genc6EvidenceKind.CONCENTRATION_RISK_PER_CAPITAL,
            value=evidence.incremental_concentration_risk_usd / amount,
            sha_digit="2",
        ),
        _fact(
            kind=Genc6EvidenceKind.DRAWDOWN_RISK_PER_CAPITAL,
            value=evidence.incremental_drawdown_risk_proxy_usd / amount,
            sha_digit="3",
        ),
        _fact(
            kind=Genc6EvidenceKind.OPTIONALITY_CONSUMED_PER_CAPITAL,
            value=evidence.incremental_optionality_consumed_usd / amount,
            sha_digit="4",
        ),
        _fact(
            kind=Genc6EvidenceKind.PROVIDER_CONSTRAINT_PRESSURE,
            value=Decimal("0.10"),
            sha_digit="5",
        ),
    )


def _candidate(
    *,
    tmp_path: Path,
    portfolio: AccountCoreCompoundPortfolio,
    source_lot_id: str,
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
    expected_use: Genc6EvidenceUse = Genc6EvidenceUse.CAPITAL_ELIGIBLE,
) -> Genc6MarginalCapitalCandidate:
    marginal = _marginal(
        portfolio=portfolio,
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
        portfolio=portfolio,
        evidence=marginal,
        source_lot_id=source_lot_id,
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
    return Genc6MarginalCapitalCandidate(
        candidate_id=f"candidate-{signal}",
        account_identity=portfolio.account_identity,
        trader_id=trader,
        qore_symbol="NAS100" if trader is TraderLineage.VT31_NAS100 else "XAUUSD",
        provider_symbol="US100" if trader is TraderLineage.VT31_NAS100 else "XAUUSD",
        signal_fingerprint=signal,
        decision_at=T0,
        valid_from=T0 - timedelta(seconds=1),
        valid_until=T0 + timedelta(minutes=15),
        technical_valid=True,
        cancelled=False,
        marginal_unit_index=1,
        concentration_group="EQUITY_BETA",
        marginal_evidence=marginal,
        genc5_seal=seal,
        provider_feasible=True,
        provider_feasibility_evidence_sha256="sha256:" + "5" * 64,
        comparable_facts=_facts(
            marginal,
            prefix="a" if signal.endswith("a") else "b",
            expected_use=expected_use,
        ),
    )


def _state(
    portfolio: AccountCoreCompoundPortfolio,
):
    return build_genc6_portfolio_state(
        snapshot_id="portfolio-state-1",
        decision_at=T0,
        portfolio=portfolio,
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        ),
    )


def _reserve(
    identity: CiboAccountCapitalIdentity,
) -> Genc6ReserveAlternative:
    return Genc6ReserveAlternative(
        alternative_id=GENC6_RESERVE_ID,
        account_identity=identity,
        decision_at=T0,
    )


def test_genc6_true_scarcity_and_reserve_on_pareto_ambiguity(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio()
    candidate_a = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
        signal="signal-a",
        expected_return="10",
        stop_risk="2",
        margin="8",
        execution_cost="0.2",
        concentration="1.2",
        drawdown="1.3",
        optionality="1.0",
        duration="60",
        uncertainty="0.30",
    )
    candidate_b = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-b",
        expected_return="7",
        stop_risk="2",
        margin="4",
        execution_cost="0.1",
        concentration="0.5",
        drawdown="0.5",
        optionality="0.3",
        duration="20",
        uncertainty="0.10",
    )
    event = build_capital_scarcity_event(
        event_id="scarcity-1",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(candidate_a, candidate_b),
        reserve_alternative=_reserve(portfolio.account_identity),
    )

    assert event.true_scarcity is True
    assert event.simultaneously_valid_count == 2
    assert event.available_capital_usd == Decimal("60")
    assert event.total_requested_capital_usd == Decimal("80")
    assert event.capital_shortfall_usd == Decimal("20")
    assert event.mutually_fundable_candidate_count == 1
    assert event.competition_intensity == Decimal("0.25")

    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id="genc6-decision-1",
    )

    assert decision.market_id == GENC6_MARKET_ID
    assert decision.policy_id == GENC6_POLICY_ID
    assert decision.policy_sha256 == genc6_policy_sha256()
    assert decision.policy_frozen_at == GENC6_POLICY_FROZEN_AT
    assert decision.control_action is Genc6Action.ALLOCATE_MARGINAL_UNIT
    assert decision.control_candidate_id == "candidate-signal-b"
    assert decision.control_amount_usd == Decimal("40")
    assert decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.treatment_candidate_id is None
    assert decision.treatment_amount_usd == Decimal("0")
    assert decision.reserve_amount_usd == Decimal("40")
    assert decision.treatment_differs_from_control is True
    assert decision.outcome_present_at_seal is False
    assert decision.runtime_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False


def test_genc6_unique_pareto_dominator_gets_only_next_marginal_unit(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio()
    dominant = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
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
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.R34_XAUUSD,
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
    event = build_capital_scarcity_event(
        event_id="scarcity-dominance",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(dominant, inferior),
        reserve_alternative=_reserve(portfolio.account_identity),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id="genc6-dominance",
    )

    assert decision.treatment_action is Genc6Action.ALLOCATE_MARGINAL_UNIT
    assert decision.treatment_candidate_id == "candidate-signal-a"
    assert decision.treatment_amount_usd == Decimal("40")
    assert decision.available_capital_usd == Decimal("60")
    assert decision.treatment_amount_usd < decision.available_capital_usd


def test_genc6_observe_only_mandatory_evidence_cannot_influence_capital(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio()
    candidate = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
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
        expected_use=Genc6EvidenceUse.OBSERVE_ONLY,
    )
    event = build_capital_scarcity_event(
        event_id="observe-only",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(candidate,),
        reserve_alternative=_reserve(portfolio.account_identity),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id="genc6-observe-only",
    )

    assert decision.control_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert any(
        "MANDATORY_CAPITAL_EVIDENCE_NOT_ELIGIBLE" in item
        for item in decision.blocker_codes
    )


def test_genc6_cross_account_candidate_fails_closed(
    tmp_path: Path,
) -> None:
    portfolio_a, source_a = _portfolio(account_ref="account-a")
    portfolio_b, source_b = _portfolio(account_ref="account-b")
    candidate_a = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio_a,
        source_lot_id=source_a,
        trader=TraderLineage.VT31_NAS100,
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
    candidate_b = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio_b,
        source_lot_id=source_b,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-b",
        expected_return="7",
        stop_risk="2",
        margin="4",
        execution_cost="0.2",
        concentration="0.5",
        drawdown="0.5",
        optionality="0.3",
        duration="30",
        uncertainty="0.10",
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cross-account candidate",
    ):
        build_capital_scarcity_event(
            event_id="cross-account",
            decision_at=T0,
            portfolio_state=_state(portfolio_a),
            candidates=(candidate_a, candidate_b),
            reserve_alternative=_reserve(portfolio_a.account_identity),
        )


def test_genc6_expired_candidate_is_not_false_competition(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio()
    candidate_a = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
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
    candidate_b = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-b",
        expected_return="7",
        stop_risk="2",
        margin="4",
        execution_cost="0.2",
        concentration="0.5",
        drawdown="0.5",
        optionality="0.3",
        duration="30",
        uncertainty="0.10",
    )
    expired = replace(
        candidate_b,
        valid_until=T0 - timedelta(microseconds=1),
    )
    event = build_capital_scarcity_event(
        event_id="expired-not-competition",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(candidate_a, expired),
        reserve_alternative=_reserve(portfolio.account_identity),
    )

    assert event.simultaneously_valid_count == 1
    assert event.true_scarcity is False


def test_genc6_store_hash_chain_cas_restart_and_conflict(
    tmp_path: Path,
) -> None:
    portfolio, source = _portfolio()
    candidate_a = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
        signal="signal-a",
        expected_return="10",
        stop_risk="2",
        margin="8",
        execution_cost="0.2",
        concentration="1.2",
        drawdown="1.3",
        optionality="1.0",
        duration="60",
        uncertainty="0.30",
    )
    candidate_b = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-b",
        expected_return="7",
        stop_risk="2",
        margin="4",
        execution_cost="0.1",
        concentration="0.5",
        drawdown="0.5",
        optionality="0.3",
        duration="20",
        uncertainty="0.10",
    )
    event = build_capital_scarcity_event(
        event_id="durable-scarcity",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(candidate_a, candidate_b),
        reserve_alternative=_reserve(portfolio.account_identity),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id="durable-genc6",
    )
    store = DurableGenc6InternalCapitalMarketStore(
        tmp_path / "genc6-market.json"
    )
    sealed_at = T0 + timedelta(seconds=2)

    first = store.seal(
        event=event,
        decision=decision,
        sealed_at=sealed_at,
        expected_generation=0,
    )
    assert first.generation == 1
    assert first.chain_sha256.startswith("sha256:")
    assert store.load() == first

    idempotent = store.seal(
        event=event,
        decision=decision,
        sealed_at=sealed_at,
        expected_generation=1,
    )
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        store.seal(
            event=event,
            decision=decision,
            sealed_at=sealed_at,
            expected_generation=0,
        )

    conflicting = replace(
        decision,
        treatment_reason="CONFLICTING_REWRITE",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="conflicting decision rewrite",
    ):
        store.seal(
            event=event,
            decision=conflicting,
            sealed_at=sealed_at,
            expected_generation=1,
        )


def _oos_books(
    *,
    tmp_path: Path,
    event,
    decision,
    include_release_timing: bool = True,
    include_second_outcome: bool = True,
):
    market_store = DurableGenc6InternalCapitalMarketStore(
        tmp_path / "genc6-oos-market.json"
    )
    genc6_book = market_store.seal(
        event=event,
        decision=decision,
        sealed_at=T0 + timedelta(seconds=2),
        expected_generation=0,
    )

    c4_store = DurableGenc4MarginalEvidenceStore(
        tmp_path / "genc6-oos-c4.json"
    )
    generation = 0
    for candidate in event.candidates:
        c4_book = c4_store.seal(
            candidate.marginal_evidence,
            sealed_at=T0 + timedelta(seconds=1),
            expected_generation=generation,
        )
        generation += 1

    phase20_decisions = []
    phase20_policies = []
    phase20_outcomes = []
    for index, candidate in enumerate(event.candidates, start=1):
        evidence = candidate.marginal_evidence
        source_sha = evidence.source_opportunity_decision_sha256
        phase20_decisions.append(
            Phase20ForwardDecisionSeal(
                evidence_id=f"phase20-source-{index}",
                decision_epoch_id=f"phase20-epoch-{index}",
                evidence_sha256=source_sha,
                decision_at=T0,
                candidate_id=(
                    "CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3"
                ),
                code_sha="a" * 40,
                parameter_sha256="sha256:" + "b" * 64,
                signal_fingerprints=(candidate.signal_fingerprint,),
                canonical_payload_json=(
                    '{"account_identity":{"account_ref":"genc6-demo",'
                    '"provider_key":"ctrader"}}'
                ),
            )
        )
        phase20_policies.append(
            Phase20ForwardPolicyDecisionSeal(
                evidence_sha256=source_sha,
                policy_record_sha256=(
                    evidence.source_baseline_policy_record_sha256
                ),
                allocator_disposition="ALLOW",
                selected_signal_fingerprints=(
                    candidate.signal_fingerprint,
                ),
                canonical_record_json="{}",
            )
        )
        if index == 2 and not include_second_outcome:
            continue
        deployed_at = (
            T0 + timedelta(minutes=index)
            if include_release_timing
            else None
        )
        released_at = (
            T0 + timedelta(minutes=index + 10)
            if include_release_timing
            else None
        )
        capital_minutes = (
            Decimal("10") if include_release_timing else None
        )
        phase20_outcomes.append(
            Phase20ForwardOutcomeSeal(
                evidence_id=f"phase20-outcome-{index}",
                decision_evidence_sha256=source_sha,
                signal_fingerprint=candidate.signal_fingerprint,
                position_id=5000 + index,
                execution_risk_evidence_id=f"risk-{index}",
                settlement_deal_ids=(6000 + index,),
                fill_evidence_refs=(f"fill-{index}",),
                observed_at=T0 + timedelta(minutes=index + 11),
                realized_net_pnl_usd=Decimal(str(index)),
                executed_initial_stop_risk_usd=Decimal("1"),
                realized_structural_outcome_r=Decimal(str(index)),
                capital_deployed_at=deployed_at,
                capital_released_at=released_at,
                capital_minutes=capital_minutes,
            )
        )

    phase20_book = VersionedPhase20ForwardEvidenceBook(
        generation=len(phase20_decisions) + len(phase20_outcomes),
        decisions=tuple(phase20_decisions),
        outcomes=tuple(phase20_outcomes),
    )
    policy_book = VersionedPhase20ForwardPolicyBook(
        generation=len(phase20_policies),
        decisions=tuple(phase20_policies),
    )
    return (
        genc6_book,
        c4_book,
        tuple(candidate.genc5_seal for candidate in event.candidates),
        phase20_book,
        policy_book,
    )


def _ambiguous_event_and_decision(tmp_path: Path):
    portfolio, source = _portfolio()
    candidate_a = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.VT31_NAS100,
        signal="signal-a",
        expected_return="10",
        stop_risk="2",
        margin="8",
        execution_cost="0.2",
        concentration="1.2",
        drawdown="1.3",
        optionality="1.0",
        duration="60",
        uncertainty="0.30",
    )
    candidate_b = _candidate(
        tmp_path=tmp_path,
        portfolio=portfolio,
        source_lot_id=source,
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-b",
        expected_return="7",
        stop_risk="2",
        margin="4",
        execution_cost="0.1",
        concentration="0.5",
        drawdown="0.5",
        optionality="0.3",
        duration="20",
        uncertainty="0.10",
    )
    event = build_capital_scarcity_event(
        event_id="oos-scarcity",
        decision_at=T0,
        portfolio_state=_state(portfolio),
        candidates=(candidate_a, candidate_b),
        reserve_alternative=_reserve(portfolio.account_identity),
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id="oos-genc6-decision",
    )
    return event, decision


def test_genc6_oos_binding_requires_full_causal_chain_and_release(
    tmp_path: Path,
) -> None:
    event, decision = _ambiguous_event_and_decision(tmp_path)
    genc6_book, c4_book, c5_seals, phase20_book, policy_book = _oos_books(
        tmp_path=tmp_path,
        event=event,
        decision=decision,
        include_release_timing=True,
    )

    report = bind_genc6_to_causal_outcomes(
        genc6_book=genc6_book,
        c4_book=c4_book,
        genc5_seals=c5_seals,
        phase20_evidence_book=phase20_book,
        phase20_policy_book=policy_book,
    )

    assert report.status is Genc6OosBindingStatus.COMPLETE
    assert report.decision_count == 1
    assert report.candidate_count == 2
    assert report.c4_bound_count == 2
    assert report.c5_bound_count == 2
    assert report.source_decision_bound_count == 2
    assert report.source_policy_bound_count == 2
    assert report.settlement_bound_count == 2
    assert report.release_timing_bound_count == 2
    assert report.missing_outcome_keys == ()
    assert report.missing_release_keys == ()
    assert report.failures == ()
    assert report.hypothetical_genc6_pnl_computed is False
    assert report.economic_utility_ready is False
    assert report.certification_ready is False
    assert all(
        row.hypothetical_genc6_pnl_computed is False
        and row.economic_utility_claimed is False
        for row in report.rows
    )


def test_genc6_missing_release_stays_partial_without_imputation(
    tmp_path: Path,
) -> None:
    event, decision = _ambiguous_event_and_decision(tmp_path)
    genc6_book, c4_book, c5_seals, phase20_book, policy_book = _oos_books(
        tmp_path=tmp_path,
        event=event,
        decision=decision,
        include_release_timing=False,
    )

    report = bind_genc6_to_causal_outcomes(
        genc6_book=genc6_book,
        c4_book=c4_book,
        genc5_seals=c5_seals,
        phase20_evidence_book=phase20_book,
        phase20_policy_book=policy_book,
    )

    assert report.status is Genc6OosBindingStatus.PARTIAL
    assert report.settlement_bound_count == 2
    assert report.release_timing_bound_count == 0
    assert len(report.missing_release_keys) == 2
    assert report.hypothetical_genc6_pnl_computed is False


def test_genc6_missing_candidate_outcome_stays_partial(
    tmp_path: Path,
) -> None:
    event, decision = _ambiguous_event_and_decision(tmp_path)
    genc6_book, c4_book, c5_seals, phase20_book, policy_book = _oos_books(
        tmp_path=tmp_path,
        event=event,
        decision=decision,
        include_release_timing=True,
        include_second_outcome=False,
    )

    report = bind_genc6_to_causal_outcomes(
        genc6_book=genc6_book,
        c4_book=c4_book,
        genc5_seals=c5_seals,
        phase20_evidence_book=phase20_book,
        phase20_policy_book=policy_book,
    )

    assert report.status is Genc6OosBindingStatus.PARTIAL
    assert report.settlement_bound_count == 1
    assert report.release_timing_bound_count == 1
    assert len(report.missing_outcome_keys) == 1


def test_genc6_population_is_descriptive_even_when_coverage_complete(
    tmp_path: Path,
) -> None:
    event, decision = _ambiguous_event_and_decision(tmp_path)
    genc6_book, c4_book, c5_seals, phase20_book, policy_book = _oos_books(
        tmp_path=tmp_path,
        event=event,
        decision=decision,
        include_release_timing=True,
    )
    binding = bind_genc6_to_causal_outcomes(
        genc6_book=genc6_book,
        c4_book=c4_book,
        genc5_seals=c5_seals,
        phase20_evidence_book=phase20_book,
        phase20_policy_book=policy_book,
    )
    population = describe_genc6_fresh_scarcity_population(
        genc6_book=genc6_book,
        binding=binding,
    )

    assert population.status is Genc6PopulationStatus.COVERAGE_COMPLETE
    assert population.decision_epoch_count == 1
    assert population.true_scarcity_epoch_count == 1
    assert population.non_scarcity_epoch_count == 0
    assert population.candidate_count == 2
    assert population.treatment_control_divergence_count == 1
    assert population.treatment_reserve_count == 1
    assert population.treatment_allocation_count == 0
    assert population.account_keys == ("ctrader:genc6-demo",)
    assert set(population.trader_ids) == {
        TraderLineage.VT31_NAS100.value,
        TraderLineage.R34_XAUUSD.value,
    }
    assert population.decision_calendar_days == 1
    assert population.calendar_span_days == 1
    assert population.total_available_capital_usd == Decimal("60")
    assert population.total_requested_capital_usd == Decimal("80")
    assert population.total_capital_shortfall_usd == Decimal("20")
    assert population.mean_competition_intensity == Decimal("0.25")
    assert population.mean_true_scarcity_intensity == Decimal("0.25")
    assert population.mean_mutually_fundable_candidates == Decimal("1")
    assert population.candidate_c4_coverage == Decimal("1")
    assert population.candidate_c5_coverage == Decimal("1")
    assert population.source_decision_coverage == Decimal("1")
    assert population.source_policy_coverage == Decimal("1")
    assert population.settlement_coverage == Decimal("1")
    assert population.release_timing_coverage == Decimal("1")
    assert population.descriptive_only is True
    assert population.economic_utility_ready is False
    assert population.certification_ready is False
