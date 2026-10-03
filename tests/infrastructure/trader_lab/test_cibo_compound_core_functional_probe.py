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
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_state import (
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 10, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _identity(candidate: TraderLabCandidateBinding) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, "compound-account"),
        environment=MarketRuntimeEnvironment.TEST,
    )


def _t19() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("20"),
        total_margin_capacity_usd=Decimal("200"),
        concentration_limit_by_group=(("LAB", Decimal("20")),),
    )


def _settlement(
    candidate: TraderLabCandidateBinding,
    *,
    pnl: str,
) -> CmaSettlementState:
    signal = _tag(candidate, "compound-signal")
    state = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=94001,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=94010,
            signal_fingerprint=signal,
            position_id=94001,
            net_profit_usd=Decimal(pnl),
            position_open_after=False,
        ),
    )


def test_trader_lab_compound_core_full_cycle(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=940)
    state = initialize_compound_cycle(
        account_identity=_identity(candidate),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )

    state = ingest_base_settlement(
        state,
        event_id=_tag(candidate, "base-win"),
        occurred_at=NOW,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(candidate, pnl="20"),
    )

    source_lot = _tag(candidate, "base-win") + ":gen1"
    state = protect_compound_capital(
        state,
        event_id=_tag(candidate, "protect"),
        occurred_at=NOW + timedelta(seconds=1),
        source_lot_id=source_lot,
        amount_usd=Decimal("5"),
    )
    tranche_id = _tag(candidate, "protect") + ":tranche"
    state = policy_protect_floor(
        state,
        event_id=_tag(candidate, "policy-protect"),
        occurred_at=NOW + timedelta(seconds=2),
        tranche_id=tranche_id,
        policy_id="TRADER_LAB_COMPOUND_POLICY",
        policy_sha256="sha256:" + "a" * 64,
    )
    remainder = _tag(candidate, "protect") + ":remainder"
    state = classify_compound_capital(
        state,
        event_id=_tag(candidate, "compoundable"),
        occurred_at=NOW + timedelta(seconds=3),
        source_lot_id=remainder,
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("15"),
    )
    state = classify_compound_capital(
        state,
        event_id=_tag(candidate, "activate"),
        occurred_at=NOW + timedelta(seconds=4),
        source_lot_id=_tag(candidate, "compoundable") + ":moved",
        to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        amount_usd=Decimal("15"),
    )

    assert state.floor_ledger.total_floor_usd == Decimal("5")
    assert state.floor_ledger.policy_protected_floor_usd == Decimal("5")
    assert state.compound_ledger.balance(
        CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
    ) == Decimal("15")
    assert state.cumulative_realized_gains_usd == Decimal("20")
    assert state.closing_realized_capital_usd == Decimal("120")
    assert state.accounting_identity_usd == Decimal("120")
    assert state.highest_generation == 1


def test_trader_lab_compound_loss_cannot_create_phantom_capital(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=941)
    state = initialize_compound_cycle(
        account_identity=_identity(candidate),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id=_tag(candidate, "base-loss"),
        occurred_at=NOW,
        trader_id=TraderLineage.R34_XAUUSD,
        settlement=_settlement(candidate, pnl="-12"),
    )

    assert state.current_original_base_usd == Decimal("88")
    assert state.compound_ledger.current_economic_value_usd == Decimal("0")
    assert state.closing_realized_capital_usd == Decimal("88")
    assert state.accounting_identity_usd == Decimal("88")
    assert state.highest_generation == 0
