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
)
from qore.infrastructure.cibo_compound_cycle_state import initialize_compound_cycle
from qore.infrastructure.cibo_compound_path_history import (
    materialize_compound_path_history,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 22, 30, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="compound-path-history",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _initial_state():
    return initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
        ),
    )


def _settlement(*, signal: str, position_id: int, deal_id: int, pnl: str):
    return apply_settlement(
        CmaSettlementState(
            signal_fingerprint=signal,
            position_id=position_id,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=deal_id,
            signal_fingerprint=signal,
            position_id=position_id,
            net_profit_usd=Decimal(pnl),
            position_open_after=False,
        ),
    )


def _events():
    return (
        BaseSettlementEvent(
            event_id="win",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(
                signal="win-signal",
                position_id=101,
                deal_id=201,
                pnl="20",
            ),
        ),
        ClassificationEvent(
            event_id="compoundable",
            occurred_at=T0 + timedelta(minutes=1),
            source_lot_id="win:gen1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("20"),
        ),
        ProtectProfitEvent(
            event_id="protect",
            occurred_at=T0 + timedelta(minutes=2),
            source_lot_id="compoundable:moved",
            amount_usd=Decimal("5"),
        ),
        BaseSettlementEvent(
            event_id="loss",
            occurred_at=T0 + timedelta(minutes=3),
            trader_id=TraderLineage.R34_XAUUSD,
            settlement=_settlement(
                signal="loss-signal",
                position_id=102,
                deal_id=202,
                pnl="-10",
            ),
        ),
    )


def test_path_history_materializes_initial_and_each_chronological_state() -> None:
    history = materialize_compound_path_history(
        initial_state=_initial_state(),
        initial_observed_at=T0 - timedelta(minutes=1),
        events=_events(),
    )

    assert history.event_count == 4
    assert len(history.snapshots) == 5
    assert tuple(item.event_id for item in history.snapshots) == (
        "INITIAL_STATE",
        "win",
        "compoundable",
        "protect",
        "loss",
    )
    assert all(item.state_sha256.startswith("sha256:") for item in history.snapshots)

    summary = history.summary
    assert summary.minimum_original_base_usd == Decimal("90")
    assert summary.minimum_compound_economic_value_usd == Decimal("0")
    assert summary.maximum_protected_floor_usd == Decimal("5")
    assert summary.peak_closing_realized_capital_usd == Decimal("120")
    assert summary.terminal_closing_realized_capital_usd == Decimal("110")
    assert summary.maximum_realized_capital_giveback_usd == Decimal("10")
    assert summary.descriptive_only is True
    assert summary.causal_effect_identified is False
    assert summary.certification_ready is False
    assert history.future_leakage_used is False
    assert history.productive_authority is False
    assert history.fingerprint().startswith("sha256:")


def test_path_history_fingerprint_is_deterministic() -> None:
    left = materialize_compound_path_history(
        initial_state=_initial_state(),
        initial_observed_at=T0 - timedelta(minutes=1),
        events=_events(),
    )
    right = materialize_compound_path_history(
        initial_state=_initial_state(),
        initial_observed_at=T0 - timedelta(minutes=1),
        events=_events(),
    )

    assert left == right
    assert left.fingerprint() == right.fingerprint()


def test_initial_observation_cannot_postdate_first_event() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="initial observation postdates first event",
    ):
        materialize_compound_path_history(
            initial_state=_initial_state(),
            initial_observed_at=T0 + timedelta(seconds=1),
            events=_events(),
        )


def test_reversed_event_chronology_fails_closed() -> None:
    events = list(_events())
    events[2] = ProtectProfitEvent(
        event_id="protect",
        occurred_at=T0 - timedelta(seconds=1),
        source_lot_id="compoundable:moved",
        amount_usd=Decimal("5"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="chronology is reversed",
    ):
        materialize_compound_path_history(
            initial_state=_initial_state(),
            initial_observed_at=T0 - timedelta(minutes=1),
            events=tuple(events),
        )
