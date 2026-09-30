from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_daily_c2_bias_v48 import (
    V48DailyC2BiasState,
    observe_daily_c2_bias,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_daily_profile_v48 import (
    IDENTITY as DAILY_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_daily_profile_v48 import (
    V48ForexDailyProfile,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
)


def _daily(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48ForexDailyProfile:
    return V48ForexDailyProfile(
        identity=DAILY_IDENTITY,
        symbol="EURUSD",
        profile_opened_at=opened,
        profile_closed_at=opened + timedelta(days=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        retained_m1=1440,
        expected_profile_minutes=1440,
        completeness=Decimal("1"),
    )


def _h1(
    opened: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48TimedSourceBar:
    return V48TimedSourceBar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=1),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
    )


def test_bullish_daily_c2_plus_h1_cisd_confirms_bias_at_daily_close() -> None:
    start = datetime(2026, 1, 5, 22, 0, tzinfo=UTC)
    previous = _daily(
        start,
        open_="101",
        high="102",
        low="100",
        close="101.5",
    )
    current = _daily(
        start + timedelta(days=1),
        open_="101.5",
        high="101.9",
        low="99.0",
        close="101.6",
    )
    h1_start = current.profile_opened_at
    h1 = (
        _h1(h1_start, "101.5", "101.6", "100.8", "101.0"),
        _h1(h1_start + timedelta(hours=1), "101.0", "101.1", "99.5", "100.2"),
        _h1(h1_start + timedelta(hours=2), "100.2", "100.3", "99.0", "99.8"),
        _h1(h1_start + timedelta(hours=3), "99.8", "100.4", "99.2", "100.1"),
        _h1(h1_start + timedelta(hours=4), "100.1", "101.8", "100.0", "101.6"),
    )
    result = observe_daily_c2_bias(previous, current, lower_timeframe_bars=h1)
    assert result.state is V48DailyC2BiasState.CONFIRMED
    assert result.direction is CapitalizerSourceDirection.BULLISH
    assert result.known_at_iso == current.profile_closed_at.isoformat()
    assert result.complete_daily_bias_universe_claimed is False
    assert result.outcome_used is False


def test_daily_c2_without_ltf_cisd_stays_wait() -> None:
    start = datetime(2026, 1, 5, 22, 0, tzinfo=UTC)
    previous = _daily(
        start,
        open_="101",
        high="102",
        low="100",
        close="101.5",
    )
    current = _daily(
        start + timedelta(days=1),
        open_="101.5",
        high="101.9",
        low="99.0",
        close="100.5",
    )
    h1_start = current.profile_opened_at
    h1 = (
        _h1(h1_start, "101.5", "101.6", "100.8", "101.0"),
        _h1(h1_start + timedelta(hours=1), "101.0", "101.1", "99.5", "100.2"),
        _h1(h1_start + timedelta(hours=2), "100.2", "100.3", "99.0", "99.8"),
        _h1(h1_start + timedelta(hours=3), "99.8", "100.0", "99.1", "99.6"),
    )
    result = observe_daily_c2_bias(previous, current, lower_timeframe_bars=h1)
    assert result.state is V48DailyC2BiasState.WAIT
    assert result.direction is None
