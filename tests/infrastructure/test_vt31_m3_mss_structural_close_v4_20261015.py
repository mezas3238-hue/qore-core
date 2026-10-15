"""Adversarial TTrades MSS structural close: swing geometry != displacement."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_mss_structural_close_v4_20261015 import (
    TTradesSourceSwingCOGV4,
    structural_close_component,
)


def bar(t, *, high="106", low="90", close="99"):
    return M1Bar(
        t, t+timedelta(minutes=1), Decimal("100"),
        Decimal(high), Decimal(low), Decimal(close),
    )


def bullish():
    t = datetime(2025, 7, 1, 14, tzinfo=UTC)
    highs = ("103", "105", "110", "103", "114", "113")
    closes = ("99", "98", "98", "100", "112", "111")
    return tuple(
        bar(t+timedelta(minutes=i), high=h, close=c)
        for i, (h, c) in enumerate(zip(highs, closes, strict=True))
    )


def test_bullish_exact_one_preconfirmed_swing_close_is_only_component():
    rows = bullish()
    x = structural_close_component(
        rows[:5], side=Side.LONG,
        first_return_at=rows[0].closed_at,
        as_of=rows[4].closed_at,
    )
    assert x.state == "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED"
    assert (x.eligible_swings, x.crossed_swings) == (1, 1)
    assert x.reference_pivot_confirmed_at == rows[3].closed_at
    assert x.reference_pivot_confirmed_at < x.as_of


def test_bearish_symmetry_swing_low_confirmed_before_close():
    t = datetime(2025, 1, 15, 15, tzinfo=UTC)
    lows = ("92", "89", "85", "88", "82")
    closes = ("99", "99", "98", "96", "83")
    rows = tuple(
        bar(t+timedelta(minutes=i), low=lo, close=c)
        for i, (lo, c) in enumerate(zip(lows, closes, strict=True))
    )
    x = structural_close_component(
        rows, side=Side.SHORT,
        first_return_at=rows[0].closed_at,
        as_of=rows[-1].closed_at,
    )
    assert x.state == "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED"
    assert x.reference_pivot_confirmed_at == rows[3].closed_at


def test_no_lookahead_right_m1_confirmation_required():
    rows = bullish()
    x = structural_close_component(
        rows[:4], side=Side.LONG,
        first_return_at=rows[0].closed_at,
        as_of=rows[3].closed_at,
    )
    assert x.state == "WAIT_FOR_NEW_STRUCTURAL_CLOSE"
    assert x.crossed_swings == 0


def test_past_break_not_reused_as_new_break_without_crossing_again():
    rows = bullish()
    x = structural_close_component(
        rows, side=Side.LONG,
        first_return_at=rows[0].closed_at,
        as_of=rows[5].closed_at,
    )
    assert x.state == "WAIT_FOR_NEW_STRUCTURAL_CLOSE"
    assert x.crossed_swings == 0


def test_multiple_pivots_not_resolved_by_cherry_picking():
    t = datetime(2025, 7, 1, 14, tzinfo=UTC)
    highs = ("103", "105", "110", "104", "105", "112", "104", "116")
    closes = ("99", "99", "99", "99", "99", "99", "99", "115")
    rows = tuple(
        bar(t+timedelta(minutes=i), high=h, close=c)
        for i, (h, c) in enumerate(zip(highs, closes, strict=True))
    )
    x = structural_close_component(
        rows, side=Side.LONG,
        first_return_at=rows[0].closed_at,
        as_of=rows[-1].closed_at,
    )
    assert x.state == "MULTIPLE_SWINGS_MSS_REFERENCE_UNKNOWN"
    assert x.eligible_swings >= 2 and x.crossed_swings >= 2
    assert x.reference_pivot_confirmed_at is None


def test_equal_neighbour_highs_not_confirmed_swing():
    t = datetime(2025, 7, 1, 14, tzinfo=UTC)
    highs = ("105", "110", "110", "102", "114")
    rows = tuple(
        bar(t+timedelta(minutes=i), high=h, close="99")
        for i, h in enumerate(highs)
    )
    x = structural_close_component(
        rows, side=Side.LONG, first_return_at=rows[0].closed_at,
        as_of=rows[-1].closed_at,
    )
    assert x.state == "WAIT_FOR_NEW_STRUCTURAL_CLOSE"
    assert x.eligible_swings == 0


def test_timestamp_gap_overlap_future_and_naive_rejected():
    rows = bullish()
    with pytest.raises(ValueError, match="ASOF"):
        structural_close_component(
            rows, side=Side.LONG,
            first_return_at=rows[0].closed_at, as_of=rows[4].closed_at,
        )
    with pytest.raises(ValueError, match="AWARE"):
        structural_close_component(
            rows[:5], side=Side.LONG,
            first_return_at=datetime(2025, 7, 1, 14),
            as_of=rows[4].closed_at,
        )
    gapped = rows[:2] + rows[3:5]
    with pytest.raises(ValueError, match="GAPPED"):
        structural_close_component(
            gapped, side=Side.LONG,
            first_return_at=gapped[0].closed_at,
            as_of=gapped[-1].closed_at,
        )


class ControlledV3:
    """Causal adversarial controller; real GitHub replay uses UNMODIFIED V3."""

    def __init__(self):
        self.seen = 0
        self.invalidate_at = None
        self.target_at = None
        self.first = None

    def observe_closed_m1(self, current):
        local = current.opened_at.hour
        if local not in (14, 15):  # test fixture 14 UTC NY 10 summer
            return SimpleNamespace(
                state="WAIT_FOR_09H_CONTEXT", as_of=current.closed_at,
                first_author_cisd_at=None, first_return_at=None, bias=None,
            )
        self.seen += 1
        if self.first is None:
            self.first = current.closed_at
        state = "AUTHOR_FIRST_OPEN_CISD_COMPONENT_MSS_UNVERIFIED"
        if current.closed_at == self.invalidate_at:
            state = "INVALIDATED_OPPOSITE_RAID"
        elif current.closed_at == self.target_at:
            state = "TARGET_CONSUMED_NO_FRESH_INTENT"
        return SimpleNamespace(
            state=state, as_of=current.closed_at,
            first_author_cisd_at=self.first,
            first_return_at=self.first, bias="LONG",
        )


@pytest.mark.parametrize("terminal", ["INVALIDATED_OPPOSITE_RAID",
                                     "TARGET_CONSUMED_NO_FRESH_INTENT"])
def test_source_revocation_overrides_previous_close_evidence(terminal):
    b = bullish()
    engine = TTradesSourceSwingCOGV4()
    control = ControlledV3()
    engine._v3 = control
    for current in b[:5]:
        snap = engine.observe_closed_m1(current)
    assert snap.first_structural_close_component_at == b[4].closed_at
    assert snap.state == "SOURCE_SWING_CLOSE_COMPONENT_DISPLACEMENT_UNVERIFIED"
    if terminal == "INVALIDATED_OPPOSITE_RAID":
        control.invalidate_at = b[5].closed_at
    else:
        control.target_at = b[5].closed_at
    ended = engine.observe_closed_m1(b[5])
    assert ended.state == terminal
    assert ended.first_structural_close_component_at == snap.first_structural_close_component_at
    assert not ended.method_certified
    assert not ended.mss_author_certified
    assert not ended.trader_certified
    assert ended.orders_fills_sizing == 0


def test_cog_rejects_empty_snapshot_and_no_author_ready_claim():
    engine = TTradesSourceSwingCOGV4()
    with pytest.raises(ValueError, match="NEEDS_A_CLOSED"):
        engine.snapshot()
