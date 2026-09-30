from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_h4_15m_execution_v48 import (
    IDENTITY as H4_EXECUTION_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_h4_15m_execution_v48 import (
    V48H415MExecutionObservation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_london_continuation_v48 import (
    observe_london_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    IDENTITY as CISD_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
    V48TimedSourceBar,
)


def _cisd(at: datetime) -> V48StructuralCISDObservation:
    return V48StructuralCISDObservation(
        identity=CISD_IDENTITY,
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_closure_confirmed=True,
        swing_occurred_at=at - timedelta(minutes=30),
        swing_price=Decimal("9.0"),
        causal_series_started_at=at - timedelta(minutes=45),
        causal_series_ended_at=at - timedelta(minutes=15),
        causal_series_open=Decimal("10.0"),
        confirmed_at=at,
        confirmation_close=Decimal("10.1"),
        structural_confirmed=True,
        source_valid=True,
    )


def _bar(
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


def test_london_requires_continuation_after_protected_swing_confirmation() -> None:
    at = datetime(2026, 1, 6, 8, 0, tzinfo=UTC)
    execution = V48H415MExecutionObservation(
        identity=H4_EXECUTION_IDENTITY,
        direction=CapitalizerSourceDirection.BULLISH,
        bias_known_at=at - timedelta(hours=8),
        h4_c2_confirmed_at=at - timedelta(hours=1),
        h4_profile_opened_at=at - timedelta(hours=5),
        next_h4_profile_closed_at=at + timedelta(hours=4),
        m15_cisd=_cisd(at),
        confirmed=True,
    )
    bars = (
        _bar(at, "10.00", "10.10", "9.90", "10.05"),
        _bar(at + timedelta(minutes=15), "10.05", "10.30", "10.00", "10.25"),
        _bar(at + timedelta(minutes=30), "10.25", "10.50", "10.20", "10.45"),
        _bar(at + timedelta(minutes=45), "10.45", "10.48", "10.05", "10.15"),
        _bar(at + timedelta(minutes=60), "10.15", "10.25", "10.00", "10.08"),
        _bar(at + timedelta(minutes=75), "10.08", "10.20", "9.95", "10.02"),
        _bar(at + timedelta(minutes=90), "10.02", "10.20", "10.00", "10.12"),
        _bar(at + timedelta(minutes=105), "10.12", "10.60", "10.10", "10.55"),
    )
    result = observe_london_continuation(
        execution,
        bars,
        deadline_at=at + timedelta(hours=4),
    )
    assert result.confirmed is True
    assert result.continuation is not None
    assert result.lower_bound_route is True
    assert result.outcome_used is False


def test_london_does_not_treat_structural_cisd_alone_as_final_entry() -> None:
    at = datetime(2026, 1, 6, 8, 0, tzinfo=UTC)
    execution = V48H415MExecutionObservation(
        identity=H4_EXECUTION_IDENTITY,
        direction=CapitalizerSourceDirection.BULLISH,
        bias_known_at=at - timedelta(hours=8),
        h4_c2_confirmed_at=at - timedelta(hours=1),
        h4_profile_opened_at=at - timedelta(hours=5),
        next_h4_profile_closed_at=at + timedelta(hours=4),
        m15_cisd=_cisd(at),
        confirmed=True,
    )
    result = observe_london_continuation(
        execution,
        (),
        deadline_at=at + timedelta(hours=4),
    )
    assert result.confirmed is False
