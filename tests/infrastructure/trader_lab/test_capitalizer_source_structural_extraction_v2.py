from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    extract_previous_day_liquidity_target,
    protected_swing_from_cisd,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _bullish_cisd() -> tuple[
    CapitalizerCISDObservation,
    tuple[CapitalizerSourceBar, ...],
    CapitalizerSourceBar,
]:
    htf = detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert htf is not None
    causal = (
        _bar("100", "100.5", "99", "99.4"),
        _bar("99.4", "99.8", "98.7", "99.0"),
    )
    confirmation = _bar("99", "101", "98.9", "100.2")
    cisd = detect_cisd(
        causal_series=causal,
        confirmation_bar=confirmation,
        direction=CapitalizerSourceDirection.BULLISH,
        important_level_reached=True,
        higher_timeframe_closure=htf,
    )
    return cisd, causal, confirmation


def test_protected_swing_is_extracted_from_confirmed_cisd_extreme() -> None:
    cisd, causal, confirmation = _bullish_cisd()
    protected = protected_swing_from_cisd(
        cisd=cisd,
        causal_series=causal,
        confirmation_bar=confirmation,
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
    )

    assert protected.confirmed is True
    assert protected.direction is CapitalizerSourceDirection.BULLISH
    assert protected.swing_price == Decimal("98.7")


def test_protected_swing_extraction_rejects_unconfirmed_cisd() -> None:
    cisd, causal, confirmation = _bullish_cisd()
    invalid = type(cisd)(
        direction=cisd.direction,
        causal_series_kind=cisd.causal_series_kind,
        causal_series_open=cisd.causal_series_open,
        confirmation_close=cisd.confirmation_close,
        important_level_reached=cisd.important_level_reached,
        higher_timeframe_closure_confirmed=False,
        structural_confirmed=False,
        setup_confirmed=False,
        reasons=("TEST_UNCONFIRMED",),
    )
    with pytest.raises(ValueError, match="structurally confirmed CISD"):
        protected_swing_from_cisd(
            cisd=invalid,
            causal_series=causal,
            confirmation_bar=confirmation,
            origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        )


def test_previous_day_high_is_valid_bullish_target_only_while_untouched() -> None:
    previous = _bar("100", "105", "95", "102")
    intact = extract_previous_day_liquidity_target(
        previous_daily_bar=previous,
        bars_since_current_day_open=(
            _bar("100", "103", "99", "102"),
            _bar("102", "104", "101", "103"),
        ),
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("103"),
    )
    touched = extract_previous_day_liquidity_target(
        previous_daily_bar=previous,
        bars_since_current_day_open=(
            _bar("100", "105.5", "99", "104"),
        ),
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("103"),
    )

    assert intact.prior_day_level == Decimal("105")
    assert intact.touched_before_decision is False
    assert intact.observation.valid is True
    assert touched.touched_before_decision is True
    assert touched.observation.valid is False


def test_previous_day_low_is_valid_bearish_target_only_while_untouched() -> None:
    previous = _bar("100", "105", "95", "98")
    target = extract_previous_day_liquidity_target(
        previous_daily_bar=previous,
        bars_since_current_day_open=(
            _bar("100", "101", "96", "97"),
        ),
        direction=CapitalizerSourceDirection.BEARISH,
        entry_price=Decimal("97"),
    )

    assert target.prior_day_level == Decimal("95")
    assert target.observation.valid is True
