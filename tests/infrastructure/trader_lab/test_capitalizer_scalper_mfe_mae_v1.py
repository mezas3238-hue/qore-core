"""Synthetic fixture tests for hindsight-only M1 excursion envelopes.

Do not confuse mocked bars/returns with actual nine-market economic results.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_mfe_mae_v1 import (
    _summary,
    observe_market_excursions,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)

ENTRY = datetime(2026, 5, 4, 10, 0, tzinfo=UTC)


def _trade(
    *,
    exit_minutes: int = 3,
    reason: str = "TARGET",
    realized: str = "2",
    direction: str = "LONG",
    same_bar_ambiguity: bool = False,
) -> V49EconomicTrade:
    entry, stop, target = (
        ("100", "99", "102")
        if direction == "LONG"
        else ("100", "101", "98")
    )
    return V49EconomicTrade(
        symbol="EURUSD", session="LONDON", operating_date="2026-05-04",
        ordinal_candidate_at=ENTRY.isoformat(), direction=direction,
        entry_at=ENTRY.isoformat(),
        exit_at=(ENTRY + timedelta(minutes=exit_minutes)).isoformat(),
        entry_price=entry, stop_price=stop, target_price=target,
        planned_reward_r="2", realized_gross_r=realized,
        exit_reason=reason, m1_bars_held=exit_minutes,
        trigger_family="FVG_RETRACE_CISD",
        h1_state_basis="BULLISH_FVG",
        same_bar_stop_target_ambiguity=same_bar_ambiguity,
    )


def _bar(i: int, *, hi: str, lo: str) -> CapitalizerM1Bar:
    opened = ENTRY + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(hi), low=Decimal(lo),
        close=Decimal("100"), volume=100, digits=5,
    )


def test_mfe_mae_separates_preterminal_excursions_from_full_exit_bar() -> None:
    trade = _trade()
    bars = (
        _bar(0, hi="100.8", lo="99.8"),
        _bar(1, hi="101.2", lo="99.9"),
        _bar(2, hi="102.1", lo="99.7"),
    )
    (result,) = observe_market_excursions((trade,), bars)
    assert result.bars_reconciled == trade.m1_bars_held == 3
    assert Decimal(result.mfe_preterminal_r) == Decimal("1.2")
    assert Decimal(result.mae_preterminal_r) == Decimal("0.2")
    assert Decimal(result.mfe_full_exitbar_upper_r) == Decimal("2.1")
    assert Decimal(result.mae_full_exitbar_upper_r) == Decimal("0.3")
    assert result.known_intrabar_sequence is False
    assert result.executable_capture_claimed is False
    assert _summary((result,))["winners_mean_realized_r"] == "2"


def test_stop_target_same_bar_extreme_is_not_realized_profit() -> None:
    trade = _trade(
        exit_minutes=1, reason="STOP", realized="-1", same_bar_ambiguity=True
    )
    bar = _bar(0, hi="103", lo="98")
    (result,) = observe_market_excursions((trade,), (bar,))
    assert Decimal(result.mfe_preterminal_r) == 0
    assert Decimal(result.mfe_full_exitbar_upper_r) == 3
    assert Decimal(result.mae_full_exitbar_upper_r) == 2
    assert result.terminal_same_bar_stop_target_ambiguity is True
    assert result.realized_gross_r == "-1"
    assert _summary((result,))["exitbar_ambiguous_stop_first_count"] == 1


def test_short_uses_reversed_directional_excursions() -> None:
    trade = _trade(
        exit_minutes=2, reason="TARGET", realized="2", direction="SHORT"
    )
    bars = (
        _bar(0, hi="100.3", lo="99.5"),
        _bar(1, hi="100.7", lo="97.9"),
    )
    (result,) = observe_market_excursions((trade,), bars)
    assert Decimal(result.mfe_preterminal_r) == Decimal("0.5")
    assert Decimal(result.mae_preterminal_r) == Decimal("0.3")
    assert Decimal(result.mfe_full_exitbar_upper_r) == Decimal("2.1")
    assert Decimal(result.mae_full_exitbar_upper_r) == Decimal("0.7")


def test_missing_terminal_or_missing_bar_count_blocks_evidence() -> None:
    trade = _trade()
    with pytest.raises(ValueError, match="incomplete M1 source lifecycle"):
        observe_market_excursions(
            (trade,), (
                _bar(0, hi="100.8", lo="99.8"),
                _bar(1, hi="101.2", lo="99.9"),
            )
        )
    with pytest.raises(ValueError, match="M1 lifecycle not reconstructed"):
        observe_market_excursions(
            (trade,), (
                _bar(0, hi="100.8", lo="99.8"),
                _bar(2, hi="102.1", lo="99.8"),
            )
        )


def test_terminal_stop_or_target_needs_bar_witness() -> None:
    t = _trade(exit_minutes=1)
    with pytest.raises(ValueError, match="TARGET exit without"):
        observe_market_excursions((t,), (_bar(0, hi="101", lo="99.5"),))
    stop = _trade(exit_minutes=1, reason="STOP", realized="-1")
    with pytest.raises(ValueError, match="STOP exit without"):
        observe_market_excursions((stop,), (_bar(0, hi="100.5", lo="99.5"),))


def test_duplicate_trades_do_not_get_silently_joined() -> None:
    trade = _trade()
    with pytest.raises(ValueError, match="duplicated trade provenance"):
        observe_market_excursions((trade, replace(trade)), (
            _bar(0, hi="100.8", lo="99.8"),
            _bar(1, hi="101.2", lo="99.9"),
            _bar(2, hi="102.1", lo="99.7"),
        ))


def test_exit_bar_extrema_cannot_create_a_backtested_entry_filter() -> None:
    trade = _trade(exit_minutes=1, reason="STOP", realized="-1")
    rows = observe_market_excursions(
        (trade,), (_bar(0, hi="100.6", lo="98.9"),)
    )
    assert rows[0].hindsight_only is True
    assert _summary(rows)["losers_mfe_preterminal_at_least_0_5r"] == 0
