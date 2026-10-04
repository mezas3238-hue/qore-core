from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_compound_capital import (
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
    GENC6_RESERVE_ID,
    Genc6Action,
    Genc6CapitalEvidenceFact,
    Genc6EvidenceDirection,
    Genc6EvidenceKind,
    Genc6EvidenceUse,
    Genc6ReserveAlternative,
    build_capital_scarcity_event,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 30, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _portfolio(
    candidate: TraderLabCandidateBinding,
) -> AccountCoreCompoundPortfolio:
    identity = CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, "portfolio-account"),
        environment=MarketRuntimeEnvironment.DEMO,
    )
    lot = create_realized_profit_lot(
        CompoundRealizedProfitEvidence(
            evidence_id=_tag(candidate, "settlement"),
            account_identity=identity,
            origin_trader=TraderLineage.VT31_NAS100,
            signal_fingerprint=_tag(candidate, "origin-signal"),
            position_id=95001,
            settlement_deal_ids=(95010,),
            realized_net_profit_usd=Decimal("100"),
            realized_at=NOW - timedelta(minutes=10),
            source_settlement_sha256="sha256:" + "a" * 64,
            settlement_reconciled=True,
            position_closed=True,
        ),
        lot_id=_tag(candidate, "realized"),
        created_at=NOW - timedelta(minutes=9),
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity,
    ).admit_realized_profit(
        lot,
        event_id=_tag(candidate, "admit"),
        occurred_at=NOW - timedelta(minutes=8),
    )
    floor_lot_id = _tag(candidate, "floor")
    remainder_id = _tag(candidate, "remaining")
    ledger = ledger.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id=floor_lot_id,
        remainder_lot_id=remainder_id,
        event_id=_tag(candidate, "protect"),
        occurred_at=NOW - timedelta(minutes=7),
    )
    compoundable_id = _tag(candidate, "compoundable")
    ledger = ledger.transition(
        source_lot_id=remainder_id,
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("60"),
        moved_lot_id=compoundable_id,
        event_id=_tag(candidate, "compoundable-event"),
        occurred_at=NOW - timedelta(minutes=6),
    )
    floor = ProtectedCapitalFloorLedger(
        account_identity=identity,
    ).admit_retired_lot(
        ledger.lot(floor_lot_id),
        tranche_id=_tag(candidate, "floor-tranche"),
        event_id=_tag(candidate, "floor-admit"),
        admitted_at=NOW - timedelta(minutes=5),
    )
    floor = floor.upgrade_to_policy_protected(
        tranche_id=_tag(candidate, "floor-tranche"),
        event_id=_tag(candidate, "floor-policy"),
        occurred_at=NOW - timedelta(minutes=4),
        policy_id="TRADER_LAB_COMPOUND_PORTFOLIO_V1",
        policy_sha256="sha256:" + "b" * 64,
    )
    return AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=ledger,
        protected_floor_ledger=floor,
    )


def _t19() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        concentration_limit_by_group=(
            ("EQUITY_BETA", Decimal("10")),
        ),
    )


def _reserve_fact(
    candidate: TraderLabCandidateBinding,
) -> Genc6CapitalEvidenceFact:
    return Genc6CapitalEvidenceFact(
        fact_id=_tag(candidate, "reserve-value"),
        kind=Genc6EvidenceKind.RESERVE_VALUE,
        value=Decimal("0.01"),
        direction=Genc6EvidenceDirection.HIGHER_IS_BETTER,
        evidence_sha256="sha256:" + "c" * 64,
        produced_at=NOW - timedelta(seconds=1),
        observed_at=NOW - timedelta(seconds=2),
        source="TRADER_LAB_GENC6_RESERVE_MODEL",
        policy_version="TRADER_LAB_GENC6_V1",
        calibration_lineage=_tag(candidate, "reserve-calibration"),
        use=Genc6EvidenceUse.CAPITAL_ELIGIBLE,
        model_identity="TRADER_LAB_RESERVE_VALUE_MODEL",
        calibrated=True,
        oos_validated=True,
    )


def test_trader_lab_core_compound_portfolio_conserves_partition(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=950)
    portfolio = _portfolio(candidate)

    assert portfolio.admitted_realized_profit_usd == Decimal("100")
    assert portfolio.current_partition_usd == Decimal("100")
    assert portfolio.current_economic_value_usd == Decimal("100")
    assert portfolio.protected_floor_usd == Decimal("40")
    assert portfolio.compoundable_usd == Decimal("60")
    assert portfolio.protected_floor_usd + portfolio.compoundable_usd == Decimal(
        "100"
    )
    assert portfolio.runtime_authority is False
    assert portfolio.cross_account_transfer_authority is False


def test_trader_lab_internal_capital_market_reserves_without_legal_candidate(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=951)
    portfolio = _portfolio(candidate)
    state = build_genc6_portfolio_state(
        snapshot_id=_tag(candidate, "portfolio-state"),
        decision_at=NOW,
        portfolio=portfolio,
        t19_ledger=_t19(),
    )
    reserve = Genc6ReserveAlternative(
        alternative_id=GENC6_RESERVE_ID,
        account_identity=portfolio.account_identity,
        decision_at=NOW,
        evidence_facts=(_reserve_fact(candidate),),
    )
    event = build_capital_scarcity_event(
        event_id=_tag(candidate, "scarcity"),
        decision_at=NOW,
        portfolio_state=state,
        candidates=(),
        reserve_alternative=reserve,
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id=_tag(candidate, "icm-decision"),
    )

    assert event.available_capital_usd == Decimal("60")
    assert event.eligible_candidate_count == 0
    assert event.true_scarcity is False
    assert decision.control_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.control_amount_usd == 0
    assert decision.treatment_amount_usd == 0
    assert decision.reserve_amount_usd == Decimal("60")
    assert decision.runtime_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False
    assert decision.live_authority is False
    assert decision.real_capital_authority is False
