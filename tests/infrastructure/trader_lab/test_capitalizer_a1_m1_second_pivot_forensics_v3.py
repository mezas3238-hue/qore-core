"""Source-causal SECOND protected swing research with strict no-future checks."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from test_capitalizer_a1_source_sensor_independent_attestation_v1 import (
    _fixtures,
    _m1,
    _source,
)

from qore.infrastructure.trader_lab.capitalizer_a1_m1_protected_route_forensics_v2 import (
    M1ProtectionClass,
    review_source_m1,
)
from qore.infrastructure.trader_lab.capitalizer_a1_m1_second_pivot_forensics_v3 import (
    SecondaryPivotClass,
    review_second_pivot,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)


def _second_pivot_bars(
    *, break_second: bool = False
) -> tuple[V49Opportunity, tuple[CapitalizerM1Bar, ...]]:
    older, _, _ = _fixtures()
    t = datetime(2026, 1, 5, 1, 4, tzinfo=UTC)
    extension = (
        _m1(t, open_="101", high="102", low="96", close="101"),
        _m1(t+timedelta(minutes=1), open_="100", high="101", low="95",
            close="99"),
        _m1(t+timedelta(minutes=2), open_="99", high="100", low="96",
            close="99"),
        _m1(t+timedelta(minutes=3), open_="99", high="102", low="97",
            close="101"),
        _m1(t+timedelta(minutes=4), open_="101", high="102",
            low="94" if break_second else "98", close="101"),
    )
    at = t+timedelta(minutes=5)
    src = replace(_source(), m1_trigger_confirmed_at=at.isoformat())
    return src, (*older, *extension)


def test_second_pivot_intact_replaces_breached_first_as_context_only() -> None:
    source, bars = _second_pivot_bars()
    first = review_source_m1(source=source, m1=bars)
    assert first.protection_class is M1ProtectionClass.PRIOR_CONFIRMED_BREACHED
    second = review_second_pivot(source=source, first=first, m1=bars)
    assert second.finding is SecondaryPivotClass.LATER_CONFIRMED_INTACT
    assert second.later_intact
    assert second.distinct_pivots >= 2
    assert second.protected_price == "95"
    assert second.confirmed_at == "2026-01-05T01:08:00+00:00"
    assert second.swing_at == "2026-01-05T01:05:00+00:00"
    assert not second.entry_veto_added
    assert not second.author_certified
    assert not second.outcome_used


def test_later_pivot_can_also_be_breached_before_original_entry() -> None:
    source, bars = _second_pivot_bars(break_second=True)
    first = review_source_m1(source=source, m1=bars)
    result = review_second_pivot(source=source, first=first, m1=bars)
    assert not result.later_intact
    assert result.finding is SecondaryPivotClass.NO_LATER_INTACT_WITH_BREACHES
    assert result.protected_price is None


def test_already_intact_v2_source_is_not_downgraded() -> None:
    bars, _, _ = _fixtures()
    first = review_source_m1(source=_source(), m1=bars)
    second = review_second_pivot(source=_source(), first=first, m1=bars)
    assert second.finding is SecondaryPivotClass.PREVIOUS_V2_PROOF
    assert not second.later_intact
    assert not second.source_signals_changed


def test_strict_source_identity_future_candle_and_false_authority() -> None:
    src, bars = _second_pivot_bars()
    first = review_source_m1(source=src, m1=bars)
    with pytest.raises(ValueError, match="frozen original source"):
        review_second_pivot(
            source=src,
            first=replace(first, source_opportunity_id="INVENTED"),
            m1=bars,
        )
    with pytest.raises(ValueError, match="native closed"):
        review_second_pivot(
            source=src, first=first,
            m1=(*bars, _m1(
                datetime.fromisoformat(src.m1_trigger_confirmed_at),
                open_="101", high="102", low="98", close="101",
            )),
        )
    good = review_second_pivot(source=src, first=first, m1=bars)
    with pytest.raises(ValueError, match="future or invalid"):
        replace(
            good,
            confirmed_at=(datetime.fromisoformat(src.m1_trigger_confirmed_at)
                          + timedelta(minutes=1)).isoformat(),
        )
    with pytest.raises(ValueError, match="no economic"):
        replace(good, entry_veto_added=True)
