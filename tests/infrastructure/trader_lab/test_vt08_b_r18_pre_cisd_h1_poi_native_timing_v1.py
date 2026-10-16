"""Adversarial VT08 B R18 pre-CISD H1 POI temporal provenance."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    M3,
    first_touch_phase,
    h1_causal_context,
)

START = datetime(2026, 1, 5, 12, tzinfo=UTC)


def candles(
    *, touched_at: int | None,
) -> list[tuple[datetime, tuple[Decimal, Decimal, Decimal, Decimal]]]:
    result = []
    for i in range(10):
        low = Decimal("99") if i == touched_at else Decimal("105")
        result.append((START + i * M3, (
            Decimal("106"), Decimal("107"), low, Decimal("106"),
        )))
    return result


def phase(touched_at: int | None, cisd_index: int = 4) -> str:
    return str(first_touch_phase(
        candles(touched_at=touched_at),
        lower=Decimal("99"), upper=Decimal("100"),
        cisd_closed_at=START + cisd_index * M3,
    )["first_touch_phase"])


def test_touch_earlier_complete_m3_is_pre_cisd() -> None:
    assert phase(1) == "TOUCHED_BEFORE_CISD_BAR"


def test_touch_in_closing_cisd_m3_is_not_proven_prior() -> None:
    assert phase(3) == "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"


def test_touch_after_cisd_close_is_not_poi_pre_cisd() -> None:
    assert phase(4) == "TOUCHED_AFTER_CISD_CLOSE"


def test_absent_h1_poi_touch_remains_absent() -> None:
    assert phase(None) == "NOT_TOUCHED_DURING_C2"


def test_touched_multiple_bars_uses_earliest_not_best_future() -> None:
    source = candles(touched_at=1)
    later = list(source)
    later[6] = (
        later[6][0], (Decimal("106"), Decimal("107"),
                      Decimal("99"), Decimal("106")),
    )
    r = first_touch_phase(
        later, lower=Decimal("99"), upper=Decimal("100"),
        cisd_closed_at=START + 4 * M3,
    )
    assert r["first_touch_bar_opened_at_utc"] == (START+M3).isoformat()


def test_no_invented_touch_for_gapped_data() -> None:
    source = candles(touched_at=2)
    source.pop(1)
    with pytest.raises(ValueError, match="gaps"):
        first_touch_phase(
            source, lower=Decimal("99"), upper=Decimal("100"),
            cisd_closed_at=START + 4 * M3,
        )


def test_inverted_fvg_range_rejected() -> None:
    with pytest.raises(ValueError, match="zone"):
        first_touch_phase(
            candles(touched_at=1),
            lower=Decimal("101"), upper=Decimal("100"),
            cisd_closed_at=START + 4 * M3,
        )


def test_naive_cisd_time_rejected() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        first_touch_phase(
            candles(touched_at=1),
            lower=Decimal("99"), upper=Decimal("100"),
            cisd_closed_at=datetime(2026, 1, 5, 12),
        )


def test_naive_m3_time_rejected() -> None:
    x = candles(touched_at=1)
    x[0] = (datetime(2026, 1, 5, 12), x[0][1])
    with pytest.raises(ValueError, match="clock naive"):
        first_touch_phase(
            x, lower=Decimal("99"), upper=Decimal("100"),
            cisd_closed_at=START + 4 * M3,
        )


def test_h1_missing_all_bars_quarantined() -> None:
    out = h1_causal_context({}, "f"*64, c2_open=START)
    assert out["status"] == "UPSTREAM_H1_SOURCE_GAP"
    assert out["h1_candles"] == []


def test_h1_c2_wrong_alignment_rejected() -> None:
    with pytest.raises(ValueError, match="alignment"):
        h1_causal_context({}, "f"*64, c2_open=START+timedelta(minutes=17))


def test_h1_naive_time_rejected() -> None:
    with pytest.raises(ValueError, match="alignment"):
        h1_causal_context({}, "f"*64, c2_open=datetime(2026, 1, 5, 12))


def test_preceding_m3_touch_with_gap_is_never_accepted() -> None:
    x = candles(touched_at=1)
    x[5] = (START+timedelta(minutes=21),x[5][1])
    with pytest.raises(ValueError, match="gaps"):
        first_touch_phase(
            x, lower=Decimal("99"), upper=Decimal("100"),
            cisd_closed_at=START + 4*M3,
        )


def synthetic_prior_h1_m15():
    """Causal 3 fully closed H1 M15 input with a bullish FVG."""
    bars = {}
    origin = START-timedelta(hours=3)
    for i in range(12):
        at = origin + i*timedelta(minutes=15)
        if i < 4:
            op, hi, lo, cl = "100", "101", "99", "100"
        elif i < 8:
            op, hi, lo, cl = "102", "103", "101", "102"
        else:
            op, hi, lo, cl = "106", "108", "105", "106"
        bars[at] = {
            "opened_at":at.isoformat(),
            "closed_at":(at+timedelta(minutes=15)).isoformat(),
            "open":op, "high":hi, "low":lo, "close":cl,
        }
    return bars


def test_bullish_fvg_precedes_c2_and_has_m15_source_ids() -> None:
    ctx=h1_causal_context(
        synthetic_prior_h1_m15(),"f"*64,c2_open=START,
    )
    assert ctx["status"]=="THREE_PRIOR_H1_CLOSED"
    assert len(ctx["h1_candles"])==3
    assert ctx["fvg"]["type"]=="BULLISH_H1_3BAR_FVG_GEOMETRY"
    assert ctx["fvg"]["lower"]=="101"
    assert ctx["fvg"]["upper"]=="105"
    assert ctx["fvg"]["available_at_utc"]==START.isoformat()
    assert len(ctx["fvg"]["source_bar_ids"])==8


def test_h1_fvg_is_not_computed_from_incomplete_last_h1() -> None:
    raw=synthetic_prior_h1_m15()
    raw.pop(START-timedelta(minutes=15))
    ctx=h1_causal_context(raw,"f"*64,c2_open=START)
    assert ctx["status"]=="UPSTREAM_H1_SOURCE_GAP"
    assert ctx["h1_candles"]==[]


def test_h1_prior_fvg_invariant_at_c2_halfhour_open() -> None:
    raw=synthetic_prior_h1_m15()
    early=h1_causal_context(raw,"f"*64,c2_open=START)
    later=h1_causal_context(
        raw,"f"*64,c2_open=START+timedelta(minutes=30),
    )
    assert early["fvg"]==later["fvg"]
