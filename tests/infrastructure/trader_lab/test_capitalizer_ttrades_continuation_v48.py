from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_continuation_v48 import (
    V48ContinuationPOIKind,
    assess_source_native_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    IDENTITY as CISD_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
)


def _cisd(
    *,
    direction: CapitalizerSourceDirection,
    source_valid: bool = True,
) -> V48StructuralCISDObservation:
    at = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    return V48StructuralCISDObservation(
        identity=CISD_IDENTITY,
        direction=direction,
        higher_timeframe_closure_confirmed=source_valid,
        swing_occurred_at=at,
        swing_price=Decimal("10"),
        causal_series_started_at=at,
        causal_series_ended_at=at,
        causal_series_open=Decimal("10"),
        confirmed_at=at,
        confirmation_close=Decimal("11"),
        structural_confirmed=True,
        source_valid=source_valid,
    )


def test_fvg_plus_cisd_can_confirm_continuation_without_other_entry_models() -> None:
    result = assess_source_native_continuation(
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_direction=CapitalizerSourceDirection.BULLISH,
        poi_kind=V48ContinuationPOIKind.FAIR_VALUE_GAP,
        poi_reached=True,
        cisd=_cisd(direction=CapitalizerSourceDirection.BULLISH),
    )
    assert result.confirmed is True
    assert result.entry_price_selected is False
    assert result.outcome_used is False


def test_liquidity_sweep_plus_cisd_can_confirm_continuation() -> None:
    result = assess_source_native_continuation(
        direction=CapitalizerSourceDirection.BEARISH,
        higher_timeframe_direction=CapitalizerSourceDirection.BEARISH,
        poi_kind=V48ContinuationPOIKind.LIQUIDITY_SWEEP,
        poi_reached=True,
        cisd=_cisd(direction=CapitalizerSourceDirection.BEARISH),
    )
    assert result.confirmed is True


def test_poi_without_cisd_is_not_continuation() -> None:
    result = assess_source_native_continuation(
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_direction=CapitalizerSourceDirection.BULLISH,
        poi_kind=V48ContinuationPOIKind.FAIR_VALUE_GAP,
        poi_reached=True,
        cisd=_cisd(
            direction=CapitalizerSourceDirection.BULLISH,
            source_valid=False,
        ),
    )
    assert result.confirmed is False


def test_cisd_against_higher_timeframe_direction_is_not_continuation() -> None:
    result = assess_source_native_continuation(
        direction=CapitalizerSourceDirection.BULLISH,
        higher_timeframe_direction=CapitalizerSourceDirection.BEARISH,
        poi_kind=V48ContinuationPOIKind.LIQUIDITY_SWEEP,
        poi_reached=True,
        cisd=_cisd(direction=CapitalizerSourceDirection.BULLISH),
    )
    assert result.confirmed is False
