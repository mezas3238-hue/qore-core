from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    cibo_xauusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r25_cibo_native_memory_brain as r25,
)


def _setup() -> SimpleNamespace:
    signal = SimpleNamespace(side=SimpleNamespace(value="long"), protected_swing=Decimal("99"))
    context = SimpleNamespace(
        signal=signal,
        timeframe="H1",
        side="long",
        session="london",
        prior_body_alignment="opposed",
        fvg_before_entry="yes",
        exact_equal_liquidity="no",
        reclaim_latency_bucket="6-15m",
        cisd_progress_bucket="q3:<=0.75",
        raid_depth_range_bucket="q3:<=0.25",
        protected_risk_range_bucket="q3:<=1.0",
        body_fraction_bucket="q2:<=0.50",
        rejection_wick_bucket="q2:<=0.25",
        close_location_bucket="q3:<=0.75",
    )
    return SimpleNamespace(context=context)


def test_raid_bucket_mapping_preserves_low_anatomy() -> None:
    assert r25._raid_bucket_to_native("q1:<=0.05") == "q1:<=0.25"
    assert r25._raid_bucket_to_native("q3:<=0.25") == "q1:<=0.25"
    assert r25._raid_bucket_to_native("q4:<=0.50") == "q2:<=0.50"


def test_candidate_decision_accepts_native_robust(monkeypatch) -> None:
    target = native.NativeTarget(
        rank=1,
        level=Decimal("101"),
        route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        distance_ticks=Decimal("100"),
        touched=True,
        touch_at=None,
    )
    monkeypatch.setattr(
        native,
        "resolve_index",
        lambda index, row: (
            {
                "classification": native.ROBUST,
                "preferred_posture": native.POSTURE_LET_RUN,
                "mean_net_010_r": "0.20",
            },
            "destination",
            "sig",
        ),
    )
    result = r25._candidate_decision({}, {}, target)
    assert result is not None
    assert result.classification == native.ROBUST
    assert result.posture == native.POSTURE_LET_RUN


def test_candidate_decision_rejects_negative(monkeypatch) -> None:
    target = native.NativeTarget(
        rank=1,
        level=Decimal("101"),
        route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        distance_ticks=Decimal("100"),
        touched=False,
        touch_at=None,
    )
    monkeypatch.setattr(
        native,
        "resolve_index",
        lambda index, row: (
            {
                "classification": native.NEGATIVE,
                "preferred_posture": None,
                "mean_net_010_r": None,
            },
            "destination",
            "sig",
        ),
    )
    assert r25._candidate_decision({}, {}, target) is None


def test_choose_target_prefers_robust_over_majority(monkeypatch) -> None:
    t1 = native.NativeTarget(1, Decimal("101"), "A:H1", Decimal("100"), True, None)
    t2 = native.NativeTarget(2, Decimal("103"), "B:H4", Decimal("300"), True, None)

    def fake(index, row, target):
        if target.rank == 1:
            return r25.DecisionTarget(
                target, "geometry", native.MAJORITY, native.POSTURE_PROTECT, Decimal("0.50")
            )
        return r25.DecisionTarget(
            target, "destination", native.ROBUST, native.POSTURE_LET_RUN, Decimal("0.10")
        )

    monkeypatch.setattr(r25, "_candidate_decision", fake)
    monkeypatch.setattr(r25, "_query_row", lambda setup, target, entry: {})
    chosen = r25.choose_target({}, _setup(), ladder=[t1, t2], entry=Decimal("100"))
    assert chosen is not None
    assert chosen.native_target.rank == 2
    assert chosen.classification == native.ROBUST
