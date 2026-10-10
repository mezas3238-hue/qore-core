from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_h4_profile_v48 import (
    IDENTITY as H4_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_forex_h4_profile_v48 import (
    V48ForexH4Profile,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_h4_15m_execution_v48 import (
    observe_first_h4_15m_execution,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
)


def _h4(
    opened: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48ForexH4Profile:
    return V48ForexH4Profile(
        identity=H4_IDENTITY,
        symbol="EURUSD",
        profile_opened_at=opened,
        profile_closed_at=opened + timedelta(hours=4),
        ny_anchor_hour=opened.hour,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        retained_m1=240,
        expected_wall_profile_minutes=240,
        completeness=Decimal("1"),
    )


def _m15(
    opened: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48TimedSourceBar:
    return V48TimedSourceBar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
    )


def test_h4_c2_then_m15_cisd_confirms_execution_layer() -> None:
    base = datetime(2026, 1, 6, 1, 0, tzinfo=UTC)
    h4 = (
        _h4(base, "10.0", "11.0", "9.0", "10.5"),
        _h4(base + timedelta(hours=4), "10.5", "10.8", "8.5", "9.5"),
        _h4(base + timedelta(hours=8), "9.5", "11.5", "9.2", "11.0"),
    )
    m15_start = h4[1].profile_closed_at
    m15 = (
        _m15(m15_start, "9.5", "9.6", "9.1", "9.3"),
        _m15(m15_start + timedelta(minutes=15), "9.3", "9.4", "8.9", "9.1"),
        _m15(m15_start + timedelta(minutes=30), "9.1", "9.2", "8.7", "8.9"),
        _m15(m15_start + timedelta(minutes=45), "8.9", "9.3", "8.8", "9.2"),
        _m15(m15_start + timedelta(minutes=60), "9.2", "9.7", "9.1", "9.6"),
    )
    result = observe_first_h4_15m_execution(
        h4,
        m15,
        direction=CapitalizerSourceDirection.BULLISH,
        bias_known_at=h4[0].profile_closed_at,
        deadline_at=h4[-1].profile_closed_at,
    )
    assert result.confirmed is True
    assert result.m15_cisd is not None
    assert result.m15_cisd.source_valid is True
    assert result.outcome_used is False


def test_h4_closure_against_bias_does_not_confirm_route() -> None:
    base = datetime(2026, 1, 6, 1, 0, tzinfo=UTC)
    h4 = (
        _h4(base, "10.0", "11.0", "9.0", "10.5"),
        _h4(base + timedelta(hours=4), "10.5", "10.8", "8.5", "9.5"),
        _h4(base + timedelta(hours=8), "9.5", "11.5", "9.2", "11.0"),
    )
    result = observe_first_h4_15m_execution(
        h4,
        (),
        direction=CapitalizerSourceDirection.BEARISH,
        bias_known_at=h4[0].profile_closed_at,
        deadline_at=h4[-1].profile_closed_at,
    )
    assert result.confirmed is False
