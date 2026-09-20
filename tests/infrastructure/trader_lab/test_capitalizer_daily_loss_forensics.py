from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_daily_loss_forensics import (
    _daily_groups,
    _distribution,
    _intraday_realized_drawdown,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    realized: str,
) -> CapitalizerExposureCandidate:
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=at,
        entry_at=at,
        exit_at=at + timedelta(minutes=10),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal(realized),
    )


def test_cross_session_operating_day_groups_asia_london_new_york() -> None:
    # Jan 5 20:00 NY = Jan 6 01:00 UTC; still belongs to Jan 5 operating date.
    asia = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        at=datetime(2026, 1, 6, 1, 0, tzinfo=UTC),
        realized="-1",
    )
    london = _candidate(
        "EURUSD",
        CapitalizerSide.SHORT,
        at=datetime(2026, 1, 5, 13, 0, tzinfo=UTC),
        realized="-1",
    )
    new_york = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=datetime(2026, 1, 5, 19, 0, tzinfo=UTC),
        realized="2",
    )

    grouped = _daily_groups((asia, london, new_york))
    assert len(grouped) == 1
    rows = next(iter(grouped.values()))
    assert sum((item.realized_r for item in rows), Decimal("0")) == Decimal("0")


def test_intraday_realized_drawdown_tracks_peak_to_later_losses() -> None:
    base = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)
    rows = (
        _candidate(
            "EURUSD",
            CapitalizerSide.LONG,
            at=base,
            realized="2",
        ),
        _candidate(
            "GBPUSD",
            CapitalizerSide.LONG,
            at=base + timedelta(minutes=20),
            realized="-1",
        ),
        _candidate(
            "NAS100",
            CapitalizerSide.SHORT,
            at=base + timedelta(hours=6),
            realized="-2",
        ),
    )
    ordered = tuple(sorted(rows, key=lambda item: item.exit_at))
    assert _intraday_realized_drawdown(ordered) == Decimal("3")


def test_daily_distribution_counts_loss_bands_without_selecting_gate() -> None:
    base = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)
    grouped = {
        base.date(): (
            _candidate(
                "EURUSD",
                CapitalizerSide.LONG,
                at=base,
                realized="-3",
            ),
        ),
        (base + timedelta(days=1)).date(): (
            _candidate(
                "EURUSD",
                CapitalizerSide.LONG,
                at=base + timedelta(days=1),
                realized="1",
            ),
        ),
        (base + timedelta(days=2)).date(): (
            _candidate(
                "EURUSD",
                CapitalizerSide.LONG,
                at=base + timedelta(days=2),
                realized="-1",
            ),
        ),
        (base + timedelta(days=3)).date(): (
            _candidate(
                "EURUSD",
                CapitalizerSide.LONG,
                at=base + timedelta(days=3),
                realized="-6",
            ),
        ),
    }
    distribution = _distribution(grouped)
    assert distribution.days == 4
    assert distribution.negative_days == 3
    assert distribution.days_le_minus_1r == 3
    assert distribution.days_le_minus_2r == 2
    assert distribution.days_le_minus_3r == 2
    assert distribution.days_le_minus_6r == 1
    assert distribution.worst_day_r == "-6"
