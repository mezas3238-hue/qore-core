"""Audit written bullish M30→M3 stop rule without promoting C-geometry."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1 import (
    ClosedExternalPivot,
    ExternalPivotKind,
)
from qore.infrastructure.trader_lab.vt08_5m_a_ttrades_m30m3_stop_authority_contract_v1 import (
    POI_AUTHOR_ADDITIONAL_CONTEXT,
    POI_AUTHOR_CONTINUATION_HIERARCHY,
    AuthorCheckStatus,
    inspect_bullish_m30_example,
    observed_bullish_breaker_shapes,
    stop_below_eq_and_breaker,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T0 = datetime(2026, 7, 14, 9, tzinfo=UTC)
LONG = DemoTradingSetupSide.LONG


def bar(start, op: str, hi: str, lo: str, cl: str, period: int):
    return Vt08B01Bar(
        opened_at=start, closed_at=start + timedelta(minutes=period),
        open=Decimal(op), high=Decimal(hi), low=Decimal(lo),
        close=Decimal(cl),
    )


def c2():
    return bar(T0, "100", "110", "95", "98", 30)


def pivot(confirmed_at=None):
    t = confirmed_at or T0
    return ClosedExternalPivot(
        kind=ExternalPivotKind.LOW, extreme=Decimal("94"),
        pivot_candle_opened_at=t - timedelta(hours=1),
        confirmed_at=t,
    )


def m3_breaker_proxy():
    return (
        bar(T0, "100", "102", "99", "101", 3),
        bar(T0 + timedelta(minutes=3), "101", "108", "100", "107", 3),
        bar(T0 + timedelta(minutes=6), "107", "107", "97", "99", 3),
        bar(T0 + timedelta(minutes=9), "99", "109", "99", "108", 3),
    )


def inspect(*, p=None, m3=None, decision=None, side=LONG):
    return inspect_bullish_m30_example(
        c2=c2(), decision_at=decision or c2().closed_at,
        side=side, candidate_reference_pivots=p if p is not None else (pivot(),),
        preceding_m3=m3 if m3 is not None else m3_breaker_proxy(),
    )


def test_author_stop_below_both_strictly_not_equality():
    assert stop_below_eq_and_breaker(
        stop=Decimal("94"), eq=Decimal("100"),
        breaker_low=Decimal("96"),
    )
    assert not stop_below_eq_and_breaker(
        stop=Decimal("96"), eq=Decimal("100"),
        breaker_low=Decimal("96"),
    )
    assert not stop_below_eq_and_breaker(
        stop=Decimal("100"), eq=Decimal("100"),
        breaker_low=Decimal("96"),
    )
    assert not stop_below_eq_and_breaker(
        stop=Decimal("98"), eq=Decimal("100"),
        breaker_low=Decimal("96"),
    )


def test_author_stop_relation_cannot_invent_nonpositive_quote():
    with pytest.raises(ValueError, match="positive"):
        stop_below_eq_and_breaker(
            stop=Decimal("0"), eq=Decimal("99"),
            breaker_low=Decimal("96"),
        )


def test_written_rule_a_still_requires_d_swing_reference():
    result = inspect()
    assert result.stop_condition_written_a is True
    assert result.pre_c2_external_pivot_known is True
    assert result.source_eq_reference_swing_valid is False
    assert result.source_breaker_low_adjudicated is False
    assert result.source_entry_complete is False
    assert result.cognitive_ready is False
    assert result.authorized_orders == 0
    assert result.research_breaker_proxy_count == 1
    # EQ candidate not author-valid selector:
    assert result.candidate_eq_full_c2 == Decimal("102.5")
    assert result.candidate_eq_close_to_low_c2 == Decimal("96.5")
    assert result.as_json()["stop_rule_author_source"].endswith(
        "precision-entries/"
    )


def test_right_pivot_after_c2_opens_rejected_not_backdated():
    with pytest.raises(ValueError, match="not known before"):
        inspect(p=(pivot(T0 + timedelta(minutes=3)),))


def test_wait_for_complete_m30_before_eq_geometry():
    result = inspect(decision=T0 + timedelta(minutes=24))
    assert result.status is AuthorCheckStatus.WAIT_M30_CLOSE
    assert result.candidate_eq_full_c2 is None
    assert result.authorized_orders == 0


def test_bearish_requires_separate_author_source_example():
    result = inspect(side=DemoTradingSetupSide.SHORT)
    assert result.status is AuthorCheckStatus.WRONG_FAMILY
    assert result.authorized_orders == 0


def test_four_bar_breaker_proxy_not_author_identity():
    shapes = observed_bullish_breaker_shapes(
        m3_breaker_proxy(), decision_at=T0 + timedelta(minutes=30),
    )
    assert len(shapes) == 1
    assert shapes[0].low_1 == Decimal("99")
    assert shapes[0].higher_high_4 == Decimal("109")
    assert shapes[0].author_breaker_identity_verified is False
    assert shapes[0].usable_as_trade_stop_level is False


def test_breaker_proxy_rejects_future_m3_fourth_bar():
    with pytest.raises(ValueError, match="future"):
        observed_bullish_breaker_shapes(
            m3_breaker_proxy(), decision_at=T0 + timedelta(minutes=9),
        )


def test_breaker_proxy_rejects_missing_reordered_m3():
    data = list(m3_breaker_proxy())
    data[1] = replace(
        data[1], opened_at=data[1].opened_at + timedelta(minutes=3),
        closed_at=data[1].closed_at + timedelta(minutes=3),
    )
    with pytest.raises(ValueError, match="contiguous"):
        observed_bullish_breaker_shapes(
            tuple(data), decision_at=T0 + timedelta(minutes=30),
        )


def test_no_pivot_still_refuses_eq_swings():
    status = inspect(p=())
    assert status.status is AuthorCheckStatus.BOTH_EQ_AND_BREAKER_UNADJUDICATED
    assert status.source_eq_reference_swing_valid is False


def test_poi_hierarchy_source_written_ob_not_ignored():
    assert POI_AUTHOR_CONTINUATION_HIERARCHY == (
        "FVG", "SWING_HIGH_LOW", "CISD_RETEST",
    )
    assert "ORDER_BLOCK" in POI_AUTHOR_ADDITIONAL_CONTEXT


def test_no_hidden_auto_source_complete_on_c2_without_breaker():
    status = inspect(m3=())
    assert status.research_breaker_proxy_count == 0
    assert status.source_entry_complete is False
    assert status.authorized_orders == 0
