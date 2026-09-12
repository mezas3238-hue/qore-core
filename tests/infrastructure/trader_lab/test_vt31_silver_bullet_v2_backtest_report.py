from __future__ import annotations

from typing import cast

import pytest

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest_report import (
    Vt31SilverBulletV2BacktestReportError,
    enrich_vt31_silver_bullet_v2_backtest_payload,
)


def _trade(*, side: str, outcome: str, r_multiple: str | None) -> dict[str, object]:
    exit_price: str | None
    if outcome == "breakeven":
        exit_price = "100"
    elif r_multiple is not None:
        exit_price = "102"
    else:
        exit_price = None
    return {
        "signal_at": "2026-07-08T14:03:00+00:00",
        "filled_at": "2026-07-08T14:04:00+00:00",
        "resolved_at": "2026-07-08T14:05:00+00:00",
        "side": side,
        "entry_price": "100",
        "stop_loss": "99",
        "take_profit": "102",
        "exit_price": exit_price,
        "outcome": outcome,
        "r_multiple": r_multiple,
    }


def _payload() -> dict[str, object]:
    trades = [
        _trade(side="long", outcome="target", r_multiple="2"),
        _trade(side="long", outcome="stop", r_multiple="-1"),
        _trade(side="short", outcome="gap_censored", r_multiple=None),
    ]
    return {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1",
        "symbol": "NAS100",
        "setup_count": 5,
        "filled_count": len(trades),
        "trades": trades,
    }


def test_directional_report_uses_core_setup_side_semantics() -> None:
    result = enrich_vt31_silver_bullet_v2_backtest_payload(
        _payload(),
        setup_side_counts={"long": 3, "short": 2},
    )

    assert result["side_counts"] == {"long": 3, "short": 2}
    assert result["long_setup_count"] == 3
    assert result["short_setup_count"] == 2
    assert result["long_trade_count"] == 2
    assert result["short_trade_count"] == 1

    by_side = cast(dict[str, object], result["by_side"])
    long = cast(dict[str, object], by_side["long"])
    short = cast(dict[str, object], by_side["short"])

    assert long == {
        "setup_count": 3,
        "filled_count": 2,
        "unfilled_count": 1,
        "fill_rate": "0.6666666666666666666666666667",
        "terminal_sample_size": 2,
        "target_count": 1,
        "stop_count": 1,
        "breakeven_count": 0,
        "gap_censored_count": 0,
        "data_end_censored_count": 0,
        "win_rate": "0.5",
        "expectancy_r": "0.5",
        "population_variance_r": "2.25",
    }
    assert short == {
        "setup_count": 2,
        "filled_count": 1,
        "unfilled_count": 1,
        "fill_rate": "0.5",
        "terminal_sample_size": 0,
        "target_count": 0,
        "stop_count": 0,
        "breakeven_count": 0,
        "gap_censored_count": 1,
        "data_end_censored_count": 0,
        "win_rate": "0",
        "expectancy_r": "0",
        "population_variance_r": "0",
    }


def test_directional_report_treats_breakeven_as_terminal_zero_r() -> None:
    payload = _payload()
    trades = cast(list[object], payload["trades"])
    trades.append(_trade(side="short", outcome="breakeven", r_multiple="0"))
    payload["filled_count"] = 4

    result = enrich_vt31_silver_bullet_v2_backtest_payload(
        payload,
        setup_side_counts={"long": 3, "short": 2},
    )
    by_side = cast(dict[str, object], result["by_side"])
    short = cast(dict[str, object], by_side["short"])

    assert short["terminal_sample_size"] == 1
    assert short["breakeven_count"] == 1
    assert short["expectancy_r"] == "0"


def test_directional_report_fails_closed_when_setup_counts_do_not_reconcile() -> None:
    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="setup counts must reconcile",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(
            _payload(),
            setup_side_counts={"long": 2, "short": 2},
        )


def test_directional_report_fails_closed_when_filled_count_does_not_reconcile() -> None:
    payload = _payload()
    payload["filled_count"] = 4

    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="filled_count must equal",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(
            payload,
            setup_side_counts={"long": 3, "short": 2},
        )


def test_directional_report_fails_closed_when_fills_exceed_side_setups() -> None:
    payload = _payload()
    payload["setup_count"] = 3

    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="filled long trades cannot exceed long setups",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(
            payload,
            setup_side_counts={"long": 1, "short": 2},
        )


def test_directional_report_fails_closed_on_noncanonical_side() -> None:
    payload = _payload()
    trades = cast(list[object], payload["trades"])
    trade = cast(dict[str, object], trades[0])
    trade["side"] = "buy"

    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="canonical LONG/SHORT",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(
            payload,
            setup_side_counts={"long": 3, "short": 2},
        )


def test_directional_report_requires_both_canonical_side_keys() -> None:
    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="exactly canonical LONG/SHORT",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(
            _payload(),
            setup_side_counts={"long": 5},
        )
