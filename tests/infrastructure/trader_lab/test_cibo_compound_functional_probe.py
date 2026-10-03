from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

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
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_replay import (
    BaseSettlementEvent,
    ClassificationEvent,
    ProtectProfitEvent,
    replay_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import initialize_compound_cycle
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 5, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _initial(candidate: TraderLabCandidateBinding):
    return initialize_compound_cycle(
        account_identity=CiboAccountCapitalIdentity(
            provider_key="trader-lab",
            account_ref=_tag(candidate, "compound-account"),
            environment=MarketRuntimeEnvironment.TEST,
        ),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("TRADER_LAB", Decimal("10")),
            ),
        ),
    )


def _terminal_settlement(
    candidate: TraderLabCandidateBinding,
    *,
    pnl: str,
    position_id: int,
    deal_id: int,
) -> CmaSettlementState:
    signal = _tag(candidate, f"compound-signal:{position_id}")
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


def test_trader_lab_cibo_compound_profit_protection_and_reconciliation(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=940)
    events = (
        BaseSettlementEvent(
            event_id=_tag(candidate, "settle-profit"),
            occurred_at=NOW,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_terminal_settlement(
                candidate,
                pnl="20",
                position_id=94001,
                deal_id=94010,
            ),
        ),
        ProtectProfitEvent(
            event_id=_tag(candidate, "protect"),
            occurred_at=NOW + timedelta(seconds=1),
            source_lot_id=_tag(candidate, "settle-profit") + ":gen1",
            amount_usd=Decimal("5"),
        ),
        ClassificationEvent(
            event_id=_tag(candidate, "compoundable"),
            occurred_at=NOW + timedelta(seconds=2),
            source_lot_id=_tag(candidate, "protect") + ":remainder",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("15"),
        ),
    )

    result = replay_compound_cycle(
        initial_state=_initial(candidate),
        events=events,
    )
    audit = result.reconciliation

    assert result.event_count == 3
    assert result.chronological is True
    assert result.future_leakage_used is False
    assert result.productive_authority is False

    assert result.final_state.opening_original_base_usd == Decimal("100")
    assert result.final_state.current_original_base_usd == Decimal("100")
    assert result.final_state.closing_realized_capital_usd == Decimal("120")
    assert result.final_state.accounting_identity_usd == Decimal("120")

    assert audit.admitted_realized_profit_usd == Decimal("20")
    assert audit.protected_floor_usd == Decimal("5")
    assert audit.compoundable_usd == Decimal("15")
    assert audit.accounting_residual_usd == Decimal("0")
    assert audit.accounting_integrity_pass is True
    assert audit.provenance_pass is True
    assert audit.no_double_counting_pass is True
    assert audit.no_unexplained_creation_pass is True
    assert audit.no_unexplained_destruction_pass is True
    assert audit.path_dependence_mechanics_pass is True


def test_trader_lab_cibo_compound_rejects_reversed_chronology(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=941)
    settle_id = _tag(candidate, "late-settle")
    events = (
        BaseSettlementEvent(
            event_id=settle_id,
            occurred_at=NOW + timedelta(seconds=2),
            trader_id=TraderLineage.R34_XAUUSD,
            settlement=_terminal_settlement(
                candidate,
                pnl="10",
                position_id=94101,
                deal_id=94110,
            ),
        ),
        ClassificationEvent(
            event_id=_tag(candidate, "early-classification"),
            occurred_at=NOW + timedelta(seconds=1),
            source_lot_id=settle_id + ":gen1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("10"),
        ),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="input chronology is reversed",
    ):
        replay_compound_cycle(
            initial_state=_initial(candidate),
            events=events,
        )
