"""As-of H1 phase and DST NY runway; future direction is a RESEARCH label."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    diagnostic_one,
    fixed_horizon_direction,
    h1_observed_position,
    session_end_at,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_mfe_mae_v1 import ExcursionRow
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

DAY = datetime(2026, 5, 4, 10, tzinfo=UTC)


def _bar(i: int, *, high: str = "101", low: str = "99",
         close: str = "100") -> CapitalizerM1Bar:
    at = DAY + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("100"), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
        volume=100, digits=5,
    )


def _source() -> V49Opportunity:
    return V49Opportunity(
        symbol="EURUSD", session="LONDON", operating_date="2026-05-04",
        h1_state_direction="BULLISH",
        h1_state_from=(DAY - timedelta(hours=1)).isoformat(),
        h1_state_until=(DAY + timedelta(hours=3)).isoformat(),
        h1_state_basis="H1_C2",
        m15_setup_confirmed_at=(DAY + timedelta(minutes=10)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=(DAY + timedelta(minutes=30)).isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="102",
    )


def _trade(source: V49Opportunity) -> V49EconomicTrade:
    at = source.m1_trigger_confirmed_at
    return V49EconomicTrade(
        symbol=source.symbol, session=source.session,
        operating_date=source.operating_date,
        ordinal_candidate_at=at,
        direction="LONG", entry_at=at,
        exit_at=(DAY + timedelta(minutes=45)).isoformat(),
        entry_price="100", stop_price="99", target_price="102",
        planned_reward_r="2", realized_gross_r="-0.1",
        exit_reason="SESSION_EXIT", m1_bars_held=15,
        trigger_family=source.m1_trigger_family, h1_state_basis="H1_C2",
        same_bar_stop_target_ambiguity=False,
    )


def _excursion(t: V49EconomicTrade) -> ExcursionRow:
    return ExcursionRow(
        symbol=t.symbol, session=t.session,
        operating_date=t.operating_date, entry_at=t.entry_at,
        exit_at=t.exit_at, entry_price=t.entry_price,
        direction=t.direction, trigger_family=t.trigger_family,
        h1_state_basis=t.h1_state_basis,
        exit_reason=t.exit_reason,
        realized_gross_r=t.realized_gross_r, planned_target_r=t.planned_reward_r,
        stop_width_price="1", bars_reconciled=t.m1_bars_held,
        mfe_preterminal_r="0.2", mae_preterminal_r="0.3",
        mfe_full_exitbar_upper_r="0.4", mae_full_exitbar_upper_r="0.6",
        terminal_same_bar_stop_target_ambiguity=False,
    )


def test_h1_clock_and_current_partial_h1_range_are_only_asof() -> None:
    at = DAY + timedelta(minutes=30)
    available = tuple(_bar(i) for i in range(30))
    rank, clock, count = h1_observed_position(
        available, at, Decimal("100"), "LONG"
    )
    assert rank == Decimal("0.5")
    assert clock == Decimal("0.5")
    assert count == 30
    future = _bar(30, high="150", low="98")
    assert h1_observed_position(
        available + (future,), at, Decimal("100"), "LONG"
    ) == (rank, clock, count)
    short_rank, _, _ = h1_observed_position(
        available, at, Decimal("100"), "SHORT"
    )
    assert short_rank == Decimal("0.5")


def test_h1_no_completed_m1_has_no_observed_range_and_no_future_leak() -> None:
    at = DAY
    rank, clock, count = h1_observed_position(
        (_bar(0, high="200", low="90"),), at, Decimal("100"), "LONG"
    )
    assert (rank, clock, count) == (None, Decimal(0), 0)


def test_fixed_forward_15_30_60_labels_are_only_lookahead_research() -> None:
    bars = tuple(_bar(i, high="102", close="100.5") for i in range(65))
    opened = tuple(x.opened_at for x in bars)
    forward = dict(fixed_horizon_direction(
        bars, opened, entry_at=DAY,
        entry=Decimal("100"), side=1,
        end_at=DAY + timedelta(hours=2),
    ))
    assert forward == {"15": "0.5", "30": "0.5", "60": "0.5"}
    short = dict(fixed_horizon_direction(
        bars, opened, entry_at=DAY,
        entry=Decimal("100"), side=-1,
        end_at=DAY + timedelta(hours=2),
    ))
    assert short == {"15": "-0.5", "30": "-0.5", "60": "-0.5"}
    truncated = dict(fixed_horizon_direction(
        bars, opened, entry_at=DAY,
        entry=Decimal("100"), side=1,
        end_at=DAY + timedelta(minutes=22),
    ))
    assert truncated["15"] == "0.5"
    assert truncated["30"] is None and truncated["60"] is None


def test_native_m1_gap_never_creates_direction_label() -> None:
    full = tuple(_bar(i) for i in range(65))
    missing = full[:4] + full[5:]
    result = dict(fixed_horizon_direction(
        missing, tuple(x.opened_at for x in missing),
        entry_at=DAY, entry=Decimal("100"), side=1,
        end_at=DAY + timedelta(hours=2),
    ))
    assert all(x is None for x in result.values())


def test_ny_session_runway_uses_explicit_dst_clock() -> None:
    london_summer = datetime(2026, 5, 4, 11, 0, tzinfo=UTC)
    london_winter = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    assert session_end_at(london_summer, "LONDON") == datetime(
        2026, 5, 4, 12, 30, tzinfo=UTC
    )
    assert session_end_at(london_winter, "LONDON") == datetime(
        2026, 1, 5, 13, 30, tzinfo=UTC
    )
    asia_early = datetime(2026, 5, 5, 1, 0, tzinfo=UTC)
    assert session_end_at(asia_early, "ASIA") == datetime(
        2026, 5, 5, 6, 0, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="outside LONDON"):
        session_end_at(datetime(2026, 5, 4, 19, tzinfo=UTC), "LONDON")


def test_join_rejects_mfe_or_trade_mutation_and_no_h1_future_until_use() -> None:
    source = _source()
    trade = _trade(source)
    x = _excursion(trade)
    bars = tuple(_bar(i, close="100") for i in range(70))
    opened = tuple(b.opened_at for b in bars)
    row = diagnostic_one(source, trade, x, bars, opened)
    assert row.entry_h1_clock_fraction == "0.5"
    assert Decimal(row.session_runway_minutes) == 120
    assert Decimal(row.h1_context_age_minutes) == 90
    assert row.target_hit_in_real_trade is False
    assert row.source_entry_and_exit_unchanged
    assert row.outcome_data_used_for_admission is False
    assert row.forward_15m_signed_price == "0"
    assert diagnostic_one(
        replace(source, h1_state_until=(DAY + timedelta(days=6)).isoformat()),
        trade, x, bars, opened
    ) == row
    with pytest.raises(ValueError, match="frozen V49"):
        diagnostic_one(
            source, replace(trade, target_price="103"),
            x, bars, opened
        )


def test_no_assumption_that_mae_before_exit_bar_predicts_sequence() -> None:
    trade = _trade(_source())
    x = _excursion(trade)
    row = diagnostic_one(
        _source(), trade, x, tuple(_bar(i) for i in range(65)),
        tuple(_bar(i).opened_at for i in range(65))
    )
    assert row.mae_preterminal_r == "0.3"
    assert row.mae_full_exitbar_observation_upper_r == "0.6"
    assert row.forward_returns_are_research_labels_only
