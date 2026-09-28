from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as metrics,
)


def _trade(
    *,
    symbol: str,
    session: str,
    side: str,
    operating_date: str,
    entry_at: str,
    realized_r: str,
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session=session,
        operating_date=operating_date,
        side=side,
        entry_at=entry_at,
        exit_at=entry_at.replace("10:00:00", "11:00:00"),
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TARGET" if Decimal(realized_r) > 0 else "STOP",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _control() -> tuple[milestone.SimulatedTrade, ...]:
    return (
        _trade(
            symbol="EURUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T10:00:00+00:00",
            realized_r="2",
        ),
        _trade(
            symbol="GBPUSD",
            session="LONDON",
            side="SHORT",
            operating_date="2026-01-06",
            entry_at="2026-01-06T10:00:00+00:00",
            realized_r="-1",
        ),
        _trade(
            symbol="NAS100",
            session="NEW_YORK",
            side="LONG",
            operating_date="2026-01-07",
            entry_at="2026-01-07T10:00:00+00:00",
            realized_r="2",
        ),
        _trade(
            symbol="USDCAD",
            session="NEW_YORK",
            side="SHORT",
            operating_date="2026-01-08",
            entry_at="2026-01-08T10:00:00+00:00",
            realized_r="-1",
        ),
    )


def test_certification_metrics_bind_economics_and_daily_policy() -> None:
    report = metrics.build_certification_metrics_report(
        _control(),
        population_role="CONSUMED_TEST",
        window_start=date(2026, 1, 5),
        window_end_exclusive=date(2026, 1, 10),
    )

    assert report.identity == metrics.IDENTITY
    assert report.economics.trades == 4
    assert report.economics.wins == 2
    assert report.economics.losses == 2
    assert report.economics.win_rate == "0.5"
    assert report.economics.total_r == "2"
    assert report.economics.expectancy_r_per_trade == "0.5"
    assert report.economics.profit_factor == "2"
    assert report.economics.average_winner_r == "2"
    assert report.economics.average_loser_r_abs == "1"
    assert report.economics.payoff_ratio == "2"
    assert report.economics.max_drawdown_r == "1"
    assert report.economics.max_losing_streak == 1

    daily = report.daily_risk_adjusted
    assert daily.return_unit == "NEW_YORK_OPERATING_DATE_REALIZED_R"
    assert daily.business_day_observations == 5
    assert daily.active_trade_days == 4
    assert daily.zero_trade_days == 1
    assert daily.zero_trade_weekdays_included is True
    assert daily.risk_free_rate_per_day == "0"
    assert daily.minimum_acceptable_return_per_day == "0"
    assert daily.annualization_periods_per_year == 252
    assert daily.sharpe_annualized is not None
    assert Decimal(daily.sharpe_annualized) > 0
    assert daily.sortino_annualized is not None
    assert Decimal(daily.sortino_annualized) > 0

    clusters = report.loss_clustering
    assert clusters.cluster_count == 2
    assert clusters.losing_trade_count == 2
    assert clusters.max_cluster_length == 1
    assert clusters.worst_cluster_total_r == "-1"

    assert {row.value for row in report.by_session} == {
        "LONDON",
        "NEW_YORK",
    }
    assert {row.value for row in report.by_symbol} == {
        "EURUSD",
        "GBPUSD",
        "NAS100",
        "USDCAD",
    }


def test_zero_trade_weekdays_are_included_without_weekend_inflation() -> None:
    rows = (
        _trade(
            symbol="EURUSD",
            session="LONDON",
            side="LONG",
            operating_date="2026-01-05",
            entry_at="2026-01-05T10:00:00+00:00",
            realized_r="1",
        ),
    )
    report = metrics.build_certification_metrics_report(
        rows,
        population_role="CONSUMED_TEST",
        window_start=date(2026, 1, 5),
        window_end_exclusive=date(2026, 1, 12),
    )

    daily = report.daily_risk_adjusted
    assert daily.business_day_observations == 5
    assert daily.active_trade_days == 1
    assert daily.zero_trade_days == 4


def test_winner_preservation_and_loss_recall_are_identity_aligned() -> None:
    control = _control()
    candidate = (
        replace(control[0], realized_gross_r="1"),
        replace(control[1], realized_gross_r="0.2"),
        control[2],
        control[3],
    )

    report = metrics.compare_winner_preservation(
        control,
        candidate,
        window_start=date(2026, 1, 5),
        window_end_exclusive=date(2026, 1, 10),
    )

    assert report.same_entrant_identities is True
    assert report.control_winners == 2
    assert report.preserved_control_winners == 2
    assert report.winner_count_preservation == "1"
    assert report.control_winner_r == "4"
    assert report.candidate_r_on_control_winners == "3"
    assert report.winner_r_preservation == "0.75"
    assert report.control_losers == 2
    assert report.recalled_control_losses == 1
    assert report.loss_recall == "0.5"
    assert report.density_retention == "1"


def test_duplicate_entrant_identity_fails_closed() -> None:
    row = _control()[0]
    try:
        metrics.build_certification_metrics_report(
            (row, row),
            population_role="INVALID",
            window_start=date(2026, 1, 5),
            window_end_exclusive=date(2026, 1, 10),
        )
    except ValueError as error:
        assert "unique entrant identities" in str(error)
    else:
        raise AssertionError("duplicate entrant identity must fail closed")
