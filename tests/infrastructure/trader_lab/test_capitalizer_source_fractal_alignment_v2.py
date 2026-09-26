from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    assess_fractal_alignment,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _bullish_h1_closure() -> CapitalizerSourceClosureObservation | None:
    return detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )


def _bullish_m15_cisd(
    h1: CapitalizerSourceClosureObservation,
) -> CapitalizerCISDObservation:
    return detect_cisd(
        causal_series=(
            _bar("100", "100.5", "99", "99.4"),
            _bar("99.4", "99.8", "98.7", "99.0"),
        ),
        confirmation_bar=_bar("99", "101", "98.9", "100.2"),
        direction=CapitalizerSourceDirection.BULLISH,
        important_level_reached=True,
        higher_timeframe_closure=h1,
    )


def test_fractal_alignment_requires_all_three_layers_in_same_direction() -> None:
    h1 = _bullish_h1_closure()
    assert h1 is not None
    m15 = _bullish_m15_cisd(h1)
    m1 = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("98.8"),
        origin=CapitalizerProtectedSwingOrigin.FAIR_VALUE_GAP,
        closure_through_causal_series_confirmed=True,
    )

    observed = assess_fractal_alignment(
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
        h1_closure=h1,
        m15_cisd=m15,
        m1_protected_swing=m1,
    )

    assert observed.confirmed is True
    assert observed.h1_closure_confirmed is True
    assert observed.m15_cisd_confirmed is True
    assert observed.m1_protected_swing_confirmed is True
    assert observed.numeric_score_used is False
    assert observed.grants_entry_authority is False


def test_fractal_alignment_fails_if_m1_protected_swing_points_opposite() -> None:
    h1 = _bullish_h1_closure()
    assert h1 is not None
    m15 = _bullish_m15_cisd(h1)
    wrong_m1 = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BEARISH,
        swing_price=Decimal("101.2"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )

    observed = assess_fractal_alignment(
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
        h1_closure=h1,
        m15_cisd=m15,
        m1_protected_swing=wrong_m1,
    )

    assert observed.confirmed is False
    assert observed.m1_protected_swing_confirmed is False
