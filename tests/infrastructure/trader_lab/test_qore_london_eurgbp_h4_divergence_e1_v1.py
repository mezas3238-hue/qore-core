"""E1: causal H4, paired dates, frozen outcome interaction, controls."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.qore_london_eurgbp_h4_divergence_e1_v1 import (
    REGIMES, common_regimes, draw_date_blocks, h4_prior, interaction, rates,
    standardized_interaction,
)


def bar(at: datetime, close: str) -> CapitalizerM1Bar:
    p = Decimal(close)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at, closed_at=at+timedelta(minutes=1),
        open=p, high=p+Decimal(".0002"),
        low=p-Decimal(".0002"), close=p, volume=1, digits=5,
    )


RAID = datetime(2026, 7, 15, 10, 20, tzinfo=UTC)


def h4_fixture() -> dict[datetime, CapitalizerM1Bar]:
    start = datetime(2026, 7, 14, 20, tzinfo=UTC)
    return {
        start+timedelta(minutes=i): bar(
            start+timedelta(minutes=i), str(Decimal("1.10000") + Decimal(i)/Decimal(1000000))
        )
        for i in range(720)
    }


def test_h4_strict_720_and_last_completed_before_raid() -> None:
    src = h4_fixture()
    r = h4_prior(src, RAID, "HIGH")
    assert r["status"] == REGIMES[0]
    assert r["h4_m1_count"] == 720
    assert r["latest_completed_h4_end"] == "2026-07-15T08:00:00+00:00"
    assert r["last_observed_m1_closed_at"] == "2026-07-15T08:00:00+00:00"
    assert h4_prior(src, RAID, "LOW")["status"] == REGIMES[1]
    # Pre-raid H4 cannot see a newer H4 that is still forming.
    extra=dict(src)
    extra[RAID+timedelta(minutes=1)] = bar(RAID+timedelta(minutes=1), "9.00000")
    assert h4_prior(extra, RAID, "HIGH") == r


def test_h4_weekend_or_gap_unknown_instead_of_ffill() -> None:
    src = h4_fixture()
    del src[datetime(2026, 7, 15, 3, 19, tzinfo=UTC)]
    result = h4_prior(src, RAID, "HIGH")
    assert result["status"] == "H4_UNKNOWN_GAP"


def test_raw_cross_pair_interaction_with_known_frozen_counts() -> None:
    rows=[]
    for symbol, state, n, reversals in [
        ("EURUSD","RECLAIM_INSIDE",94,38),
        ("EURUSD","ACCEPTED_OUTSIDE",115,40),
        ("GBPUSD","RECLAIM_INSIDE",92,22),
        ("GBPUSD","ACCEPTED_OUTSIDE",123,50),
    ]:
        for i in range(n):
            rows.append({
                "symbol":symbol,"checkpoint_state":state,
                "source_status":"CHECKPOINT_VALID",
                "terminal_60":"REVERSAL" if i<reversals else "NEUTRAL",
            })
    x=interaction(rows)
    assert x is not None
    assert x["effect_interaction_EUR_minus_GBP"] == pytest.approx(
        (38/94-40/115) - (22/92-50/123)
    )
    assert x["simple_reclaim_rate_EUR_minus_GBP"] == pytest.approx(38/94-22/92)


def test_paired_date_bootstrap_keeps_two_symbols_together() -> None:
    base=[
        {"symbol": sym, "ny_day":f"2026-07-{day:02d}",
         "checkpoint_state":"RECLAIM_INSIDE",
         "source_status":"CHECKPOINT_VALID",
         "terminal_60":"REVERSAL"}
        for day in range(1,21) for sym in ("EURUSD","GBPUSD")
    ]
    from random import Random
    draw=draw_date_blocks(base,[f"2026-07-{d:02d}" for d in range(1,21)],Random(100))
    eur=[r["ny_day"] for r in draw if r["symbol"]=="EURUSD"]
    gbp=[r["ny_day"] for r in draw if r["symbol"]=="GBPUSD"]
    assert eur==gbp
    assert len(eur)==20


def test_h4_regime_requires_both_states_both_pairs_support() -> None:
    rows = [
        {"symbol": s, "checkpoint_state": st,
         "terminal_60": "REVERSAL", "source_status":"CHECKPOINT_VALID",
         "h4_prior":{"status":REGIMES[0]}}
        for s in ("EURUSD","GBPUSD") for st in ("RECLAIM_INSIDE","ACCEPTED_OUTSIDE")
        for _ in range(12)
    ]
    regimes,weights,counts=common_regimes(rows)
    assert regimes==(REGIMES[0],)
    assert weights[REGIMES[0]]==pytest.approx(1)
    assert counts[REGIMES[0]]["EURUSD|RECLAIM_INSIDE"]==12
    a=standardized_interaction(rows,regimes,weights,min_cell=10)
    assert a is not None
    assert a["interaction_EUR_minus_GBP"]==0
    assert rates([])["p_reversal"] is None
