"""CHARACTERIZATION, not endorsement, of disputed source C3 H1 primitive.

Primary December 2025 article: C3 does not sweep C2 but closes through
C2 body; January 2026 article describes closing beyond C2 opening/range.
The current V49 engine implements the December/inside-range reading.
Tests freeze its current behavior WITHOUT promoting a changed strategy.
"""

from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceClosureKind,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)


def _bar(o: str, h: str, l: str, c: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(o), high=Decimal(h),
        low=Decimal(l), close=Decimal(c),
    )


def test_h1_c2_requires_sweep_close_back_inside_and_poi() -> None:
    first = _bar("100", "104", "96", "101")
    second = _bar("101", "103", "94", "99")
    bullish = detect_candle2_reversal_closure(
        previous=first, candle2=second, point_of_interest_present=True,
    )
    assert bullish is not None
    assert bullish.kind is CapitalizerSourceClosureKind.CANDLE2_REVERSAL
    assert bullish.source_rule_satisfied
    absent_poi = detect_candle2_reversal_closure(
        previous=first, candle2=second, point_of_interest_present=False,
    )
    assert absent_poi is not None
    assert not absent_poi.source_rule_satisfied
    # Merely trading through the previous low and closing below it
    # is continuation, not the author's bullish reversal C2.
    assert detect_candle2_reversal_closure(
        previous=first, candle2=_bar("101", "102", "94", "95"),
        point_of_interest_present=True,
    ) is None


def test_current_c3_accepts_december_inside_range_beyond_body() -> None:
    c2 = _bar("100", "103", "97", "98")
    c3 = _bar("98", "102", "97.5", "100.5")
    got = detect_candle3_confirmation(
        candle2=c2, candle3=c3,
        point_of_interest_present=True,
        candle2_reversal_already_confirmed=False,
    )
    assert got is not None
    assert got.kind is CapitalizerSourceClosureKind.CANDLE3_CONFIRMATION
    assert got.source_rule_satisfied
    assert "CANDLE3_DID_NOT_SWEEP_CANDLE2_RANGE" in got.reasons


def test_current_c3_rejects_january_outside_range_reading_source_unresolved() -> None:
    # January 2026 source: 'Candle 3 closes beyond ... range of candle 2'.
    # V49 explicitly rejects the below, notwithstanding POI and body close.
    # This documents a source conflict; it does NOT prove which author
    # interpretation to operationalize or justify modifying V49 in sample.
    c2 = _bar("100", "103", "97", "98")
    c3 = _bar("98", "104.5", "97.5", "104")
    assert detect_candle3_confirmation(
        candle2=c2, candle3=c3,
        point_of_interest_present=True,
        candle2_reversal_already_confirmed=False,
    ) is None
