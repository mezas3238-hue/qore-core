"""PIT C2 eligibility, three-M5 timing, N1 reconciliation guards."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_n3_c2_m5_causal_clock import (
    c2_purge_return,
    census_c2_to_m5,
    first_m5_observation,
    new_early_m5_prefix_state,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

T = datetime(2026, 1, 14, 12, tzinfo=UTC)


def m15(i: int, op: int, hi: int, lo: int, cl: int) -> M15Bar:
    return M15Bar(
        opened_at=T + timedelta(minutes=15 * i),
        open_price=op, high_price=hi, low_price=lo, close_price=cl,
    )


def m5(i: int, op: int, hi: int, lo: int, cl: int) -> ReplayBar:
    return ReplayBar(
        opened_at=T + timedelta(minutes=30 + 5 * i),
        open_price=op, high_price=hi, low_price=lo, close_price=cl,
    )


def test_c2_sweep_return_admitted_as_event_at_close_without_c3() -> None:
    assert c2_purge_return(
        m15(0, 100, 110, 90, 100),
        m15(1, 100, 105, 85, 95),
    ) is CrtPureCandidateDirection.BULLISH
    assert c2_purge_return(
        m15(0, 100, 110, 90, 100),
        m15(1, 100, 115, 95, 105),
    ) is CrtPureCandidateDirection.BEARISH


def test_c2_two_sided_sweep_or_close_outside_rejected() -> None:
    c1 = m15(0, 100, 110, 90, 100)
    assert c2_purge_return(c1, m15(1, 100, 115, 85, 100)) is None
    assert c2_purge_return(c1, m15(1, 100, 105, 85, 80)) is None
    assert c2_purge_return(c1, m15(1, 100, 115, 95, 112)) is None
    assert c2_purge_return(c1, m15(1, 100, 105, 95, 102)) is None


def test_c2_requires_contiguous_complete_reference() -> None:
    assert c2_purge_return(
        m15(0, 100, 110, 90, 100),
        m15(2, 100, 105, 85, 95),
    ) is None


def test_m5_midpoint_first_cross_slot_one_before_far_touch_slot_three() -> None:
    c3_m5 = (
        m5(0, 95, 102, 94, 101),
        m5(1, 101, 107, 99, 105),
        m5(2, 105, 112, 103, 108),
    )
    result = first_m5_observation(
        micro_c1=m15(0, 100, 110, 90, 100),
        micro_c3=m15(2, 95, 112, 94, 108),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_bars=c3_m5,
    )
    assert result["first_m5_close_crossing_micro_c1_midpoint_slot"] == 1
    assert result["first_m5_wick_touching_far_boundary_slot"] == 3
    assert result["midpoint_slot_precedes_far_slot"] is True
    assert result["measurement_only_not_M5_entry_signal"] is True


def test_m5_same_bar_wick_close_order_is_explicitly_unknown() -> None:
    b = (
        m5(0, 95, 112, 94, 101),
        m5(1, 101, 107, 99, 102),
        m5(2, 102, 106, 98, 104),
    )
    result = first_m5_observation(
        micro_c1=m15(0, 100, 110, 90, 100),
        micro_c3=m15(2, 95, 112, 94, 104),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_bars=b,
    )
    assert result["first_m5_close_crossing_micro_c1_midpoint_slot"] == 1
    assert result["first_m5_wick_touching_far_boundary_slot"] == 1
    assert result["same_M5_bar_order_if_both_occur"] == "UNKNOWN_INTRABAR_SEQUENCE"


def test_bearish_m5_close_crossing_without_far_touch() -> None:
    b = (
        m5(0, 105, 108, 99, 101),
        m5(1, 101, 104, 95, 97),
        m5(2, 97, 100, 93, 94),
    )
    result = first_m5_observation(
        micro_c1=m15(0, 100, 110, 90, 100),
        micro_c3=m15(2, 105, 108, 93, 94),
        direction=CrtPureCandidateDirection.BEARISH,
        m5_bars=b,
    )
    assert result["first_m5_close_crossing_micro_c1_midpoint_slot"] == 2
    assert result["first_m5_wick_touching_far_boundary_slot"] is None


def test_no_m5_close_crossing_is_recorded_not_dropped() -> None:
    b = (
        m5(0, 95, 98, 92, 93),
        m5(1, 93, 99, 90, 94),
        m5(2, 94, 99, 91, 96),
    )
    result = first_m5_observation(
        micro_c1=m15(0, 100, 110, 90, 100),
        micro_c3=m15(2, 95, 99, 90, 96),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_bars=b,
    )
    assert result["first_m5_close_crossing_micro_c1_midpoint_slot"] is None
    assert result["first_m5_wick_touching_far_boundary_slot"] is None


def test_noncontiguous_m5_rejected() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        first_m5_observation(
            micro_c1=m15(0, 100, 110, 90, 100),
            micro_c3=m15(2, 95, 107, 90, 104),
            direction=CrtPureCandidateDirection.BULLISH,
            m5_bars=(m5(0, 95, 100, 93, 98), m5(2, 98, 107, 90, 104), m5(3, 104, 107, 99, 102)),
        )


def test_m5_aggregation_mismatch_rejected() -> None:
    b = (
        m5(0, 95, 103, 94, 101),
        m5(1, 101, 105, 99, 103),
        m5(2, 103, 107, 100, 105),
    )
    with pytest.raises(ValueError, match="aggregation"):
        first_m5_observation(
            micro_c1=m15(0, 100, 110, 90, 100),
            micro_c3=m15(2, 95, 107, 94, 109),
            direction=CrtPureCandidateDirection.BULLISH,
            m5_bars=b,
        )


def test_btcusd_is_frozen() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        census_c2_to_m5(CrtPureMarket.BTCUSD, ())


def test_n3b_new_m5_evidence_can_precede_far_wick_in_later_M5() -> None:
    # The third M5 makes the far target later, which MUST NOT invalidate
    # information demonstrably known at the first M5 close.
    bars = (
        m5(0, 95, 102, 94, 101),
        m5(1, 101, 105, 98, 104),
        m5(2, 104, 112, 103, 109),
    )
    assert new_early_m5_prefix_state(
        c2_midpoint_already_closed_beyond=False,
        first_m5_midpoint_close_slot=1,
        micro_c1=m15(0, 100, 110, 90, 100),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_c3=bars,
    ) == (True, True)


def test_n3b_same_M5_wick_far_prevents_clean_prefix_even_if_close_confirms() -> None:
    bars = (
        m5(0, 95, 112, 94, 101),
        m5(1, 101, 105, 98, 104),
        m5(2, 104, 108, 103, 105),
    )
    assert new_early_m5_prefix_state(
        c2_midpoint_already_closed_beyond=False,
        first_m5_midpoint_close_slot=1,
        micro_c1=m15(0, 100, 110, 90, 100),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_c3=bars,
    ) == (True, False)


def test_n3b_C2_midpoint_already_beyond_does_not_claim_new_M5_evidence() -> None:
    bars = (
        m5(0, 101, 106, 100, 104),
        m5(1, 104, 108, 102, 105),
        m5(2, 105, 112, 103, 110),
    )
    assert new_early_m5_prefix_state(
        c2_midpoint_already_closed_beyond=True,
        first_m5_midpoint_close_slot=1,
        micro_c1=m15(0, 100, 110, 90, 100),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_c3=bars,
    ) == (False, False)


def test_n3b_slot_three_not_early_even_if_it_closes_beyond() -> None:
    bars = (
        m5(0, 95, 99, 93, 96),
        m5(1, 96, 100, 94, 99),
        m5(2, 99, 109, 97, 105),
    )
    assert new_early_m5_prefix_state(
        c2_midpoint_already_closed_beyond=False,
        first_m5_midpoint_close_slot=3,
        micro_c1=m15(0, 100, 110, 90, 100),
        direction=CrtPureCandidateDirection.BULLISH,
        m5_c3=bars,
    ) == (False, False)


def test_n3b_bearish_far_low_untouched_through_slot_two() -> None:
    bars = (
        m5(0, 105, 108, 101, 102),
        m5(1, 102, 104, 93, 96),
        m5(2, 96, 99, 85, 88),
    )
    assert new_early_m5_prefix_state(
        c2_midpoint_already_closed_beyond=False,
        first_m5_midpoint_close_slot=2,
        micro_c1=m15(0, 100, 110, 90, 100),
        direction=CrtPureCandidateDirection.BEARISH,
        m5_c3=bars,
    ) == (True, True)
