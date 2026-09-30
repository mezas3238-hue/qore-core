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
    PolicyProtectFloorEvent,
    ProtectProfitEvent,
    replay_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    initialize_compound_cycle,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 2, 0, tzinfo=UTC)


def _initial():
    return initialize_compound_cycle(
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader",
            account_ref="compound-replay-test",
            environment=MarketRuntimeEnvironment.TEST,
        ),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        ),
    )


def _settlement() -> CmaSettlementState:
    state = CmaSettlementState(
        signal_fingerprint="replay-profit",
        position_id=7001,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=8001,
            signal_fingerprint="replay-profit",
            position_id=7001,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )


def test_compound_cycle_runner_is_chronological_and_reconciled() -> None:
    events = (
        BaseSettlementEvent(
            event_id="settle",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
        ProtectProfitEvent(
            event_id="protect",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="settle:gen1",
            amount_usd=Decimal("5"),
        ),
        PolicyProtectFloorEvent(
            event_id="policy",
            occurred_at=T0 + timedelta(seconds=2),
            tranche_id="protect:tranche",
            policy_id="REPLAY_FLOOR_V1",
            policy_sha256="sha256:" + "a" * 64,
        ),
        ClassificationEvent(
            event_id="compoundable",
            occurred_at=T0 + timedelta(seconds=3),
            source_lot_id="protect:remainder",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("15"),
        ),
    )

    result = replay_compound_cycle(
        initial_state=_initial(),
        events=events,
    )

    assert result.event_count == 4
    assert result.chronological is True
    assert result.future_leakage_used is False
    assert result.productive_authority is False
    assert result.final_state.closing_realized_capital_usd == Decimal("120")
    assert result.reconciliation.accounting_residual_usd == Decimal("0")
    assert result.reconciliation.accounting_integrity_pass is True
    assert result.reconciliation.protected_floor_usd == Decimal("5")
    assert result.reconciliation.compoundable_usd == Decimal("15")
    assert result.reconciliation.certification_ready is False


def test_compound_cycle_runner_rejects_reversed_input() -> None:
    events = (
        BaseSettlementEvent(
            event_id="late",
            occurred_at=T0 + timedelta(seconds=2),
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
        ClassificationEvent(
            event_id="early",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="late:gen1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("20"),
        ),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="input chronology is reversed",
    ):
        replay_compound_cycle(
            initial_state=_initial(),
            events=events,
        )
