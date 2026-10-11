"""P0 source contract: independent M15 geometry/clock adversarial tests."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_5m_ttrades_source_swing_asof_contract_v1 import (
    Family,
    PoiReceipt,
    PoiType,
    ProofStatus,
    evaluate_source_swing_asof,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

LONG = DemoTradingSetupSide.LONG
SHORT = DemoTradingSetupSide.SHORT
T0 = datetime(2026, 3, 12, 8, tzinfo=UTC)


def bar(start: datetime, o: str, high: str, low: str, close: str, minutes=15):
    return Vt08B01Bar(
        opened_at=start, closed_at=start + timedelta(minutes=minutes),
        open=Decimal(o), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def fvg(formed_at: datetime) -> PoiReceipt:
    t = formed_at - timedelta(minutes=45)
    a = bar(t, "97", "98", "96", "97")
    b = bar(t + timedelta(minutes=15), "98", "100", "97", "99")
    c = bar(t + timedelta(minutes=30), "100", "101", "99", "100")
    return PoiReceipt(
        kind=PoiType.FVG, side=LONG,
        lower=Decimal("98"), upper=Decimal("99"),
        formed_at=formed_at, sources=(a, b, c),
    )


def prefix(start: datetime) -> tuple[Vt08B01Bar, ...]:
    return (
        bar(start, "100", "102", "94", "96"),
        bar(start + timedelta(minutes=15), "96", "106", "95", "105"),
    )


def candles():
    c1 = bar(T0 - timedelta(hours=4), "100", "110", "95", "101", 240)
    c2 = bar(T0, "100", "106", "94", "102", 240)
    c3 = bar(T0 + timedelta(hours=4), "102", "108", "97", "107", 240)
    return c1, c2, c3


def evaluate(
    family=Family.C2_CLOSURE_TO_C3, *,
    side=LONG, c1=None, c2=None, c3=None, ltf=None, poi=None, at=None,
):
    a, b, c = candles()
    a, b, c = c1 or a, c2 or b, c3 or c
    if ltf is None:
        ltf = prefix(b.opened_at)
    return evaluate_source_swing_asof(
        market="EURJPY", family=family, side=side,
        c1=a, c2=b, c3=c if family is Family.C3_CLOSURE_TO_C4 else None,
        ltf_bars=ltf, poi=poi or fvg(b.opened_at),
        decision_at=at or b.closed_at,
    )


def test_c2_confirmed_swing_not_backdated_to_cisd() -> None:
    s = evaluate()
    assert s.status is ProofStatus.CONFIRMED_STRUCTURE_ONLY
    assert s.cisd_confirmed_at == T0 + timedelta(minutes=30)
    assert s.swing_point_confirmed_at == T0 + timedelta(hours=4)
    assert s.poi_first_touched_at == T0 + timedelta(minutes=15)
    assert s.protected_swing_price == Decimal("94")
    assert s.payload()["orders_authorized"] is False
    assert s.payload()["cognitive_ready"] is False


def test_c2_swing_waits_for_h4_candle_close() -> None:
    s = evaluate(at=T0 + timedelta(hours=3))
    assert s.status is ProofStatus.WAIT_H4_CLOSURE
    assert s.swing_point_confirmed_at is None


def test_c3_continuation_proven_in_c3_without_reading_c3_future_h4() -> None:
    _, b, _ = candles()
    ltf = prefix(b.closed_at)
    s = evaluate(
        Family.C3_CONTINUATION_INTRAC3,
        ltf=ltf, poi=fvg(b.closed_at),
        at=b.closed_at + timedelta(minutes=30),
    )
    assert s.status is ProofStatus.CONFIRMED_STRUCTURE_ONLY
    assert s.cisd_confirmed_at == b.closed_at + timedelta(minutes=30)
    assert s.swing_point_confirmed_at == s.cisd_confirmed_at
    assert s.htf_closure_known_at == b.closed_at


def test_c3_continuation_cannot_use_fvg_created_after_c3_entry() -> None:
    _, b, _ = candles()
    poi = fvg(b.closed_at + timedelta(minutes=45))
    s = evaluate(
        Family.C3_CONTINUATION_INTRAC3,
        ltf=prefix(b.closed_at), poi=poi,
        at=b.closed_at + timedelta(minutes=30),
    )
    assert s.status is ProofStatus.POI_NOT_ATTESTED


def test_c3_continuation_cannot_use_future_m15_confirmation() -> None:
    _, b, _ = candles()
    with pytest.raises(ValueError, match="future M15"):
        evaluate(
            Family.C3_CONTINUATION_INTRAC3,
            ltf=prefix(b.closed_at), poi=fvg(b.closed_at),
            at=b.closed_at + timedelta(minutes=15),
        )


def test_c2_dual_sweep_is_d_not_resolved_by_last_cisd() -> None:
    _, b, _ = candles()
    s = evaluate(c2=replace(b, high=Decimal("111")))
    assert s.status is ProofStatus.DUAL_SWEEP_UNADJUDICATED
    assert s.cisd_confirmed_at is None
    assert s.orders_authorized is False


def test_poi_missing_or_invalid_source_triple_is_not_attested() -> None:
    _, b, _ = candles()
    missing = evaluate(poi=PoiReceipt(
        kind=PoiType.SWING_HIGH_LOW, side=LONG,
        lower=Decimal("98"), upper=Decimal("99"),
        formed_at=b.opened_at, sources=(),
    ))
    assert missing.status is ProofStatus.POI_NOT_ATTESTED
    poi = fvg(b.opened_at)
    future = replace(poi.sources[-1], closed_at=b.opened_at + timedelta(minutes=15))
    bad = replace(poi, sources=poi.sources[:2] + (future,))
    assert evaluate(poi=bad).status is ProofStatus.POI_NOT_ATTESTED


def test_no_swing_confirmed_without_cisd_close() -> None:
    _, b, _ = candles()
    one = prefix(b.opened_at)[:1]
    s = evaluate(ltf=one)
    assert s.status is ProofStatus.WAIT_LTF_CISD


def test_closed_m15_cannot_hide_gap_or_out_of_order() -> None:
    _, b, _ = candles()
    data = prefix(b.opened_at)
    with pytest.raises(ValueError, match="missing or reordered"):
        evaluate(ltf=(data[0], replace(data[1], opened_at=data[1].opened_at + timedelta(minutes=15),
                                          closed_at=data[1].closed_at + timedelta(minutes=15)))


def test_c3_closure_never_uses_c4_full_h4_to_confirm_early() -> None:
    a, b, _ = candles()
    a = replace(a, low=Decimal("95"), high=Decimal("110"))
    b = replace(b, low=Decimal("94"), close=Decimal("94.5"))
    c3 = bar(b.closed_at, "95", "104", "94.2", "101", 240)
    data = prefix(c3.closed_at)
    at = c3.closed_at + timedelta(minutes=30)
    poi = fvg(c3.closed_at)
    s = evaluate(
        Family.C3_CLOSURE_TO_C4, c1=a, c2=b, c3=c3,
        ltf=data, poi=poi, at=at,
    )
    assert s.status is ProofStatus.CONFIRMED_STRUCTURE_ONLY
    assert s.htf_closure_known_at == c3.closed_at
    assert s.cisd_confirmed_at == at
    assert s.swing_point_confirmed_at == at


def test_c3_closure_cannot_confirm_before_c3_h4_close() -> None:
    a, b, _ = candles()
    b = replace(b, close=Decimal("94.5"))
    c3 = bar(b.closed_at, "95", "104", "94.2", "101", 240)
    s = evaluate(
        Family.C3_CLOSURE_TO_C4, c1=a, c2=b, c3=c3,
        ltf=(), at=c3.closed_at - timedelta(minutes=15),
    )
    assert s.status is ProofStatus.WAIT_H4_CLOSURE


def test_c3_closure_requires_prior_sweep_failed_not_any_no_sweep() -> None:
    a, b, _ = candles()
    b = replace(b, low=Decimal("96"), close=Decimal("98"))
    c3 = bar(b.closed_at, "97", "104", "96", "103", 240)
    s = evaluate(
        Family.C3_CLOSURE_TO_C4, c1=a, c2=b, c3=c3,
        ltf=(), at=c3.closed_at,
    )
    assert s.status is ProofStatus.NOT_FAMILY_CLOSURE


def test_stable_swing_origin_across_wait_then_confirm() -> None:
    early = evaluate(at=T0 + timedelta(hours=3))
    late = evaluate(at=T0 + timedelta(hours=4))
    assert early.origin_id == late.origin_id
    assert early.status is not late.status


def test_no_unvalidated_ps_released_as_source_complete() -> None:
    s = evaluate()
    assert s.payload()["source_status"] == "STRUCTURE_RESEARCH_NOT_SOURCE_COMPLETE"
    assert s.orders_authorized is False and s.cognitive_ready is False
