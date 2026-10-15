"""VT31 V6: source literal intermediate triples vs QORE V5 strict, fail closed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_intermediate_literal_source_v6_20261015 import (
    LiteralIntermediateEvidence,
    literal_intermediate_source_geometry,
)


def bar(at, *, high="101", low="80", close="100"):
    return M1Bar(
        at,
        at + timedelta(minutes=1),
        Decimal("100"),
        Decimal(high),
        Decimal(low),
        Decimal(close),
    )


def highs(*, middle="112", end_close="115"):
    t = datetime(2025, 7, 1, 14, tzinfo=UTC)
    top = ("101", "102", "108", "101", "103", middle,
           "102", "103", "109", "101", "116")
    closes = ("100",) * 10 + (end_close,)
    return tuple(
        bar(t + timedelta(minutes=i), high=h, close=c)
        for i, (h, c) in enumerate(zip(top, closes, strict=True))
    )


def lows(*, middle="88"):
    t = datetime(2025, 1, 15, 15, tzinfo=UTC)
    bottom = ("98", "97", "92", "99", "97", middle,
              "99", "97", "94", "99", "84")
    closes = ("100",) * 10 + ("85",)
    return tuple(
        bar(t + timedelta(minutes=i), low=lo, close=c)
        for i, (lo, c) in enumerate(zip(bottom, closes, strict=True))
    )


def witness(candles, side):
    return literal_intermediate_source_geometry(
        candles, side=side, first_return_at=candles[0].closed_at,
        as_of=candles[-1].closed_at,
    )


def test_one_source_literal_same_kind_long_not_mss_or_order():
    candles = highs()
    a = witness(candles, Side.LONG)
    assert a.state == "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY"
    assert a.short_term_same_kind == 3
    assert a.eligible_literal_triples == 1
    assert a.freshly_crossed_literal_triples == 1
    assert a.single_center_pivot_closed_at == candles[5].closed_at
    assert a.single_right_confirmed_at == candles[9].closed_at
    assert a.single_right_confirmed_at < a.as_of
    assert isinstance(a, LiteralIntermediateEvidence)
    assert not (
        a.author_displacement_certified or a.causative_protected_swing_certified
        or a.methodology_certified or a.cognition_certified
        or a.trader_certified or a.orders_or_sizing
    )


def test_one_source_literal_same_kind_short_not_mss():
    a = witness(lows(), Side.SHORT)
    assert a.state == "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY"
    assert a.freshly_crossed_literal_triples == 1
    assert not a.author_displacement_certified


def test_nonstrict_center_is_a_literal_triple_but_v5_rejects_as_strict():
    from scripts.vt31_m3_intermediate_swing_hierarchy_v5_20261015 import (
        intermediate_swing_source_geometry,
    )

    candles = highs(middle="107")
    literal = witness(candles, Side.LONG)
    strict = intermediate_swing_source_geometry(
        candles, side=Side.LONG, first_return_at=candles[0].closed_at,
        as_of=candles[-1].closed_at,
    )
    assert literal.state == "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY"
    assert strict.state == "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"
    assert not literal.methodology_certified


def test_equal_short_term_neighbors_different_from_qore_strict_center():
    from scripts.vt31_m3_intermediate_swing_hierarchy_v5_20261015 import (
        intermediate_swing_source_geometry,
    )

    candles = highs(middle="112")
    changed = list(candles)
    changed[2] = bar(changed[2].opened_at, high="112")
    literal = witness(tuple(changed), Side.LONG)
    strict = intermediate_swing_source_geometry(
        tuple(changed), side=Side.LONG,
        first_return_at=candles[0].closed_at, as_of=candles[-1].closed_at,
    )
    assert literal.state == "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY"
    assert strict.state == "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"


def test_multi_literal_reference_abstains_without_tie_break():
    t = datetime(2025, 7, 1, 14, tzinfo=UTC)
    candles = [
        bar(t + timedelta(minutes=i), high="101") for i in range(17)
    ]
    for i, high in ((2, "105"), (5, "113"), (8, "109"),
                    (11, "114"), (14, "106")):
        candles[i] = bar(candles[i].opened_at, high=high)
    candles[16] = bar(candles[16].opened_at, high="120", close="119")
    a = witness(tuple(candles), Side.LONG)
    assert a.state == "MULTIPLE_LITERAL_INTERMEDIATES_UNKNOWN"
    assert a.freshly_crossed_literal_triples >= 2
    assert a.single_center_pivot_closed_at is None
    assert a.single_right_confirmed_at is None
    assert not a.trader_certified


def test_no_future_right_confirmation_at_break_close():
    x = highs()[:10]
    a = witness(x, Side.LONG)
    assert a.state == "NO_LITERAL_INTERMEDIATE_BREAK"
    assert a.freshly_crossed_literal_triples == 0


def test_wick_only_is_not_fresh_close_and_duplicate_break_is_not_counted():
    original = highs()
    changed = list(original)
    changed[-1] = bar(changed[-1].opened_at, high="120", close="100")
    a = witness(tuple(changed), Side.LONG)
    assert a.state == "NO_LITERAL_INTERMEDIATE_BREAK"
    assert a.freshly_crossed_literal_triples == 0
    last = original[-1]
    extra = bar(last.closed_at, high="117", close="115")
    later = witness(original + (extra,), Side.LONG)
    assert later.state == "NO_LITERAL_INTERMEDIATE_BREAK"


def test_nonstrict_short_literal_component_without_falsifying_v5():
    from scripts.vt31_m3_intermediate_swing_hierarchy_v5_20261015 import (
        intermediate_swing_source_geometry,
    )

    candles = lows(middle="94")
    literal = witness(candles, Side.SHORT)
    strict = intermediate_swing_source_geometry(
        candles, side=Side.SHORT,
        first_return_at=candles[0].closed_at,
        as_of=candles[-1].closed_at,
    )
    assert literal.state == "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY"
    assert strict.state == "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF"


def test_missing_data_naive_first_return_and_future_clock_fail_closed():
    x = highs()
    with pytest.raises(ValueError, match="SOURCE_GAP"):
        witness(x[:4] + x[5:], Side.LONG)
    with pytest.raises(ValueError, match="AWARE_TIME"):
        literal_intermediate_source_geometry(
            x, side=Side.LONG,
            first_return_at=datetime(2025, 7, 1, 14),
            as_of=x[-1].closed_at,
        )
    with pytest.raises(ValueError, match="ASOF_NOT_CLOSED"):
        literal_intermediate_source_geometry(
            x, side=Side.LONG, first_return_at=x[0].closed_at,
            as_of=x[-1].closed_at + timedelta(minutes=1),
        )


def test_first_return_after_center_cannot_create_retrospective_literal():
    x = highs()
    a = literal_intermediate_source_geometry(
        x, side=Side.LONG, first_return_at=x[6].closed_at,
        as_of=x[-1].closed_at,
    )
    assert a.state == "NO_LITERAL_INTERMEDIATE_BREAK"
    assert a.freshly_crossed_literal_triples == 0
