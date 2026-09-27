from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as audit,
)


def test_drawdown_episode_extractor_recovers_peak_and_trough() -> None:
    episodes = audit._drawdown_episodes(
        (
            Decimal("2"),
            Decimal("-1"),
            Decimal("-1"),
            Decimal("2"),
            Decimal("1"),
            Decimal("-0.5"),
            Decimal("0.5"),
        )
    )

    assert len(episodes) == 2
    first, second = episodes
    assert first.peak_equity_r == "2"
    assert first.trough_equity_r == "0"
    assert first.max_drawdown_r == "2"
    assert first.start_index == 1
    assert first.trough_index == 2
    assert first.end_index == 3
    assert first.recovered_peak is True

    assert second.peak_equity_r == "3"
    assert second.trough_equity_r == "2.5"
    assert second.max_drawdown_r == "0.5"
    assert second.start_index == 5
    assert second.end_index == 6
    assert second.descent_trade_count == 1
    assert second.recovered_peak is True


def test_drawdown_episode_extractor_keeps_unrecovered_tail() -> None:
    episodes = audit._drawdown_episodes(
        (
            Decimal("1"),
            Decimal("-0.25"),
            Decimal("-0.50"),
        )
    )

    assert len(episodes) == 1
    row = episodes[0]
    assert row.peak_equity_r == "1"
    assert row.trough_equity_r == "0.25"
    assert row.max_drawdown_r == "0.75"
    assert row.start_index == 1
    assert row.trough_index == 2
    assert row.end_index == 2
    assert row.descent_trade_count == 2
    assert row.recovered_peak is False


def test_feasibility_audit_frozen_contract() -> None:
    assert audit.IDENTITY == (
        "QORE_CAPITALIZER_PORTFOLIO_DRAWDOWN_FEASIBILITY_EPISODE_ANATOMY_V1"
    )
    assert audit.FIRST_PROTECTION_MILESTONE_R == Decimal("0.50")
    assert len(audit.ACTION_ORDER) == 9
    assert audit.ACTION_ORDER[0] == "ORIGINAL"
