"""Source-fidelity tests: two C3 readings must NOT mutate the frozen trader."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_c3_source_variants_v1 import (
    C3AsOfInput,
    C3SourceVariant,
    compare_c3_primary_readings,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)

T2 = datetime(2026, 5, 4, 12, tzinfo=UTC)
T3 = T2 + timedelta(hours=1)


def _bar(o: str, h: str, low: str, c: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(o), high=Decimal(h),
        low=Decimal(low), close=Decimal(c),
    )


def _probe(
    c3: CapitalizerSourceBar,
    *,
    poi: bool = True,
    ltf: bool = True,
    already_c2: bool = False,
) -> C3AsOfInput:
    return C3AsOfInput(
        candle2=_bar("100", "103", "97", "98"),
        candle3=c3,
        candle2_closed_at=T2,
        candle3_closed_at=T3,
        candle2_reversal_already_confirmed=already_c2,
        poi_confirmed_at=T2 if poi else None,
        ltf_cisd_confirmed_at=T2 + timedelta(minutes=20) if ltf else None,
    )


def test_december_inside_range_bullish_is_not_january_beyond_range() -> None:
    got = compare_c3_primary_readings(_probe(_bar("98", "102", "97.5", "100.5")))
    assert got[0].variant is C3SourceVariant.DECEMBER_2025_NO_SWEEP_BODY_ENGULF
    assert got[0].geometric_direction == "BULLISH"
    assert got[0].chain_observed_as_of_c3_close
    assert not got[1].geometric_match
    assert all(not r.authorizes_execution and not r.changes_v49_admission for r in got)


def test_january_beyond_c2_range_bullish_is_not_december() -> None:
    got = compare_c3_primary_readings(_probe(_bar("98", "105", "97.5", "104")))
    assert not got[0].geometric_match
    assert got[1].variant is C3SourceVariant.JANUARY_2026_CLOSE_BEYOND_C2_RANGE
    assert got[1].geometric_direction == "BULLISH"


def test_bearish_geometry_both_readings_and_no_poi_proof() -> None:
    c2 = _bar("98", "103", "97", "101")
    dec = C3AsOfInput(c2, _bar("101", "102", "97.1", "97.5"), T2, T3, False)
    jan = C3AsOfInput(c2, _bar("101", "102", "95", "96"), T2, T3, False)
    assert [v.geometric_direction for v in compare_c3_primary_readings(dec)] == [
        "BEARISH", None,
    ]
    assert [v.geometric_direction for v in compare_c3_primary_readings(jan)] == [
        None, "BEARISH",
    ]
    assert not any(v.chain_observed_as_of_c3_close
                   for v in compare_c3_primary_readings(dec))


def test_candle2_confirmed_blocks_c3_for_both_sources() -> None:
    got = compare_c3_primary_readings(
        _probe(_bar("98", "105", "97.5", "104"), already_c2=True)
    )
    assert all(not v.geometric_match for v in got)


def test_missing_poi_or_ltf_cisd_never_upgrades_geometry_to_source_chain() -> None:
    c3 = _bar("98", "102", "97.5", "100.5")
    for context in (_probe(c3, poi=False), _probe(c3, ltf=False)):
        got = compare_c3_primary_readings(context)[0]
        assert got.geometric_match
        assert not got.chain_observed_as_of_c3_close
        assert not got.source_fidelity_certified


@pytest.mark.parametrize("when", [T3 + timedelta(minutes=1), T3.replace(tzinfo=None)])
def test_future_or_naive_poi_is_forbidden(when: datetime) -> None:
    with pytest.raises(ValueError, match="POI"):
        C3AsOfInput(
            _bar("100", "103", "97", "98"),
            _bar("98", "102", "97.5", "100.5"),
            T2, T3, False, poi_confirmed_at=when,
        )


def test_ltf_before_c3_and_future_c3_are_forbidden() -> None:
    with pytest.raises(ValueError, match="inside H1"):
        C3AsOfInput(
            _bar("100", "103", "97", "98"),
            _bar("98", "102", "97.5", "100.5"),
            T2, T3, False, ltf_cisd_confirmed_at=T2,
        )
    with pytest.raises(ValueError, match="strict aware"):
        C3AsOfInput(
            _bar("100", "103", "97", "98"),
            _bar("98", "102", "97.5", "100.5"),
            T3, T2, False,
        )
