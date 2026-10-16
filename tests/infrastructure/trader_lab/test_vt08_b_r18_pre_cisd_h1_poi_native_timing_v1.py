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
    x[2] = (datetime(2026, 1, 5, 12, 6), x[2][1])
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
