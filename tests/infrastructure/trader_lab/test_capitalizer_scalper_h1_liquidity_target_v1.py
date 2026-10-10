"""H1 target hierarchy: never mistake future M1 or incomplete H1 for liquidity."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_liquidity_target_v1 import (
    TargetKind,
    discover_h1_liquidity_targets,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)

BASE = datetime(2026, 5, 4, 8, tzinfo=UTC)
HIGHS = ("103", "106", "104", "103", "103", "103")
LOWS = ("95", "96", "97", "98", "99", "99")


def _source(*, direction: str = "BULLISH", target: str = "103") -> V49Opportunity:
    return V49Opportunity(
        symbol="EURUSD", session="LONDON", operating_date="2026-05-04",
        h1_state_direction=direction,
        h1_state_from=(BASE - timedelta(hours=1)).isoformat(),
        h1_state_until=(BASE + timedelta(hours=8)).isoformat(),
        h1_state_basis="H1_C2",
        m15_setup_confirmed_at=(BASE + timedelta(hours=5, minutes=30)).isoformat(),
        m15_protected_swing_price="99" if direction == "BULLISH" else "101",
        m1_trigger_confirmed_at=(BASE + timedelta(hours=6)).isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price=target,
    )


def _bars(
    highs: tuple[str, ...] = HIGHS,
    lows: tuple[str, ...] = LOWS,
) -> tuple[tuple[V48AggregatedBar, ...], tuple[CapitalizerM1Bar, ...]]:
    h1: list[V48AggregatedBar] = []
    m1: list[CapitalizerM1Bar] = []
    for i, (hi, lo) in enumerate(zip(highs, lows, strict=True)):
        opened = BASE + timedelta(hours=i)
        src = CapitalizerSourceBar(
            open=Decimal("100"), high=Decimal(hi),
            low=Decimal(lo), close=Decimal("100"),
        )
        h1.append(V48AggregatedBar(
            opened_at=opened, closed_at=opened + timedelta(hours=1),
            source=src, minute_count=60,
        ))
        for minute in range(60):
            now = opened + timedelta(minutes=minute)
            m1.append(CapitalizerM1Bar(
                symbol="EURUSD", opened_at=now,
                closed_at=now + timedelta(minutes=1),
                open=Decimal("100"), high=Decimal(hi),
                low=Decimal(lo), close=Decimal("100"),
                volume=100, digits=5,
            ))
    return tuple(h1), tuple(m1)


def test_confirmed_external_swing_outweighs_recent_candle_extreme() -> None:
    h1, m1 = _bars()
    result = discover_h1_liquidity_targets(_source(), h1, m1)
    assert result.source_witness_reconciled is True
    assert result.prior_h1_candle_extreme is not None
    assert result.prior_h1_candle_extreme.price == Decimal("103")
    assert result.selected is not None
    assert result.selected.kind is TargetKind.EXTERNAL_CONFIRMED_H1_SWING
    assert result.selected.price == Decimal("106")
    assert result.selected.target_r_vs_m15_stop == 6
    assert result.selected.confirmed_at == BASE + timedelta(hours=3)
    assert result.selected_policy == "EXTERNAL_CONFIRMED_H1_SWING_FIRST"
    assert not result.live_authorized


def test_missing_confirmed_external_falls_back_without_dropping_entry() -> None:
    h1, m1 = _bars(
        highs=("101", "102", "103", "104", "105", "106"),
        lows=LOWS,
    )
    result = discover_h1_liquidity_targets(
        _source(target="106"), h1, m1
    )
    assert result.selected is not None
    assert result.selected.kind is TargetKind.RECENT_H1_CANDLE_EXTREME
    assert result.selected.price == 106
    assert result.available_external_swings == ()
    assert result.selected_policy == "SOURCE_WITNESS_FALLBACK"


def test_future_m1_inflight_high_does_not_consume_prior_swing() -> None:
    h1, m1 = _bars()
    before = discover_h1_liquidity_targets(_source(), h1, m1)
    at = BASE + timedelta(hours=6)
    future = CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("100"), high=Decimal("110"), low=Decimal("99"),
        close=Decimal("100"), volume=100, digits=5,
    )
    after = discover_h1_liquidity_targets(_source(), h1, m1 + (future,))
    assert after == before


def test_future_right_h1_confirmation_must_not_create_pivot() -> None:
    h1, m1 = _bars()
    source = replace(
        _source(), m1_trigger_confirmed_at=(BASE + timedelta(hours=2)).isoformat(),
        structural_target_witness_price="106",
        m15_setup_confirmed_at=(BASE + timedelta(hours=1)).isoformat(),
    )
    result = discover_h1_liquidity_targets(source, h1, m1)
    assert result.available_external_swings == ()
    assert result.selected is not None
    assert result.selected.kind is TargetKind.RECENT_H1_CANDLE_EXTREME


def test_original_witness_mismatch_is_invalid_evidence() -> None:
    h1, m1 = _bars()
    with pytest.raises(ValueError, match="witness mismatch"):
        discover_h1_liquidity_targets(
            _source(target="107"), h1, m1
        )


def test_invalid_or_unordered_source_fails_closed() -> None:
    h1, m1 = _bars()
    with pytest.raises(ValueError, match="strictly chronological"):
        discover_h1_liquidity_targets(_source(), tuple(reversed(h1)), m1)
    with pytest.raises(ValueError, match="symbol mismatch"):
        discover_h1_liquidity_targets(
            _source(), h1, (replace(m1[0], symbol="GBPUSD"),) + m1[1:]
        )


def test_confirmed_swing_previously_swept_is_not_eligible() -> None:
    h1, m1 = _bars(
        highs=("103", "106", "104", "107", "103", "103"),
        lows=LOWS,
    )
    # The original H1 bar #3 has a more recent untouched witness #5
    # at 103, but previous high 106 has been traded through.
    decision = discover_h1_liquidity_targets(_source(), h1, m1)
    assert all(row.price != 106 for row in decision.available_external_swings)
    assert decision.selected is not None
    assert decision.selected.price != 106
