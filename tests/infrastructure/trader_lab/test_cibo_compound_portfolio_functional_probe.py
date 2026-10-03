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
from qore.infrastructure.cibo_compound_floor import ProtectedCapitalFloorLedger
from qore.infrastructure.cibo_compound_portfolio_ledger import CompoundPortfolioLedger
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
    QoreCoreCompoundPortfolio,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_RESERVE_ID,
    Genc6Action,
    Genc6ReserveAlternative,
    build_capital_scarcity_event,
    build_genc6_portfolio_state,
    evaluate_genc6_internal_capital_market_shadow,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 20, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _account(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    trader: TraderLineage,
    profit: str,
    floor_amount: str,
) -> AccountCoreCompoundPortfolio:
    identity = CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, suffix),
        environment=MarketRuntimeEnvironment.TEST,
    )
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=_tag(candidate, f"{suffix}:settlement"),
        account_identity=identity,
        origin_trader=trader,
        signal_fingerprint=_tag(candidate, f"{suffix}:signal"),
        position_id=95001 if suffix == "left" else 95002,
        settlement_deal_ids=(95101 if suffix == "left" else 95102,),
        realized_net_profit_usd=Decimal(profit),
        realized_at=NOW,
        source_settlement_sha256=(
            "sha256:" + ("a" if suffix == "left" else "b") * 64
        ),
        settlement_reconciled=True,
        position_closed=True,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id=_tag(candidate, f"{suffix}:realized"),
        created_at=NOW + timedelta(seconds=1),
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        lot,
        event_id=_tag(candidate, f"{suffix}:admit"),
        occurred_at=NOW + timedelta(seconds=2),
    )

    floor = ProtectedCapitalFloorLedger(account_identity=identity)
    floor_value = Decimal(floor_amount)
    if floor_value > 0:
        floor_lot_id = _tag(candidate, f"{suffix}:floor")
        remainder_id = _tag(candidate, f"{suffix}:remainder")
        ledger = ledger.transition(
            source_lot_id=lot.lot_id,
            to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
            amount_usd=floor_value,
            moved_lot_id=floor_lot_id,
            remainder_lot_id=(
                None if floor_value == Decimal(profit) else remainder_id
            ),
            event_id=_tag(candidate, f"{suffix}:protect"),
            occurred_at=NOW + timedelta(seconds=3),
        )
        floor = floor.admit_retired_lot(
            ledger.lot(floor_lot_id),
            tranche_id=_tag(candidate, f"{suffix}:tranche"),
            event_id=_tag(candidate, f"{suffix}:floor-admit"),
            admitted_at=NOW + timedelta(seconds=4),
        )
        if floor_value < Decimal(profit):
            ledger = ledger.transition(
                source_lot_id=remainder_id,
                to_state=CompoundCapitalState.COMPOUNDABLE,
                amount_usd=Decimal(profit) - floor_value,
                moved_lot_id=_tag(candidate, f"{suffix}:compoundable"),
                event_id=_tag(candidate, f"{suffix}:compoundable-event"),
                occurred_at=NOW + timedelta(seconds=5),
            )

    return AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=ledger,
        protected_floor_ledger=floor,
    )


def test_trader_lab_core_compound_portfolio_preserves_account_boundaries(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=950)
    left = _account(
        candidate,
        suffix="left",
        trader=TraderLineage.VT31_NAS100,
        profit="100",
        floor_amount="40",
    )
    right = _account(
        candidate,
        suffix="right",
        trader=TraderLineage.R34_XAUUSD,
        profit="60",
        floor_amount="10",
    )

    portfolio = QoreCoreCompoundPortfolio(accounts=(left, right))

    assert portfolio.total_admitted_realized_profit_usd == Decimal("160")
    assert portfolio.total_current_economic_value_usd == Decimal("160")
    assert portfolio.total_protected_floor_usd == Decimal("50")
    assert portfolio.read_only is True
    assert portfolio.cross_account_transfer_authority is False
    assert portfolio.runtime_authority is False
    assert left.account_identity != right.account_identity


def test_trader_lab_genc6_internal_market_preserves_reserve_when_no_candidate(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=951)
    account = _account(
        candidate,
        suffix="market",
        trader=TraderLineage.VT31_NAS100,
        profit="60",
        floor_amount="10",
    )
    t19 = PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        concentration_limit_by_group=(("TRADER_LAB", Decimal("10")),),
    )
    state = build_genc6_portfolio_state(
        snapshot_id=_tag(candidate, "genc6-state"),
        decision_at=NOW + timedelta(minutes=1),
        portfolio=account,
        t19_ledger=t19,
    )
    reserve = Genc6ReserveAlternative(
        alternative_id=GENC6_RESERVE_ID,
        account_identity=account.account_identity,
        decision_at=NOW + timedelta(minutes=1),
        evidence_facts=(),
    )
    event = build_capital_scarcity_event(
        event_id=_tag(candidate, "genc6-event"),
        decision_at=NOW + timedelta(minutes=1),
        portfolio_state=state,
        candidates=(),
        reserve_alternative=reserve,
    )
    decision = evaluate_genc6_internal_capital_market_shadow(
        event=event,
        decision_id=_tag(candidate, "genc6-decision"),
    )

    assert event.eligible_candidate_count == 0
    assert event.true_scarcity is False
    assert decision.control_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.treatment_action is Genc6Action.RESERVE_NO_DEPLOYMENT
    assert decision.reserve_action_legal is True
    assert decision.outcome_present_at_seal is False
    assert decision.runtime_authority is False
    assert decision.risk_authority is False
    assert decision.execution_authority is False
    assert decision.live_authority is False
    assert decision.real_capital_authority is False
