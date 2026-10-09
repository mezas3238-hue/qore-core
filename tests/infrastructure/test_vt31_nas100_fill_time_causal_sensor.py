"""VT31 fill-time sensor: no intrabar fill leak or future regime mutation."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.vt31_nas100_fill_time_causal_sensor import (
    build_prospective_fill_observation,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

T = datetime(2026, 1, 5, 15, 20, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("78730000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("78730000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-fill-shadow-test"),
)


def bar(i: int, price: float, top: float, bottom: float) -> OhlcSnapshot:
    opened_at = T + timedelta(minutes=i)
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"78730000-0000-0000-0000-{i + 200:012d}")
        ),
        source=_SOURCE,
        instrument=Instrument("NAS100"),
        timeframe=Timeframe(60),
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=float(price),
        high=float(top),
        low=float(bottom),
        close=float(price),
    )


def entry() -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of=T.isoformat(),
        weekday="Monday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=10 * 60 + 20,
        side="long",
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state="bullish",
        m15_state="mixed",
        premarket_state="bullish",
        cash_open_state="bullish",
        position_in_prior_day_range="middle-third",
        range_state="compressed",
        volatility_state="compressed",
        current_path_vs_previous=Decimal("0.7"),
        reference_width_vs_prior5=Decimal("0.70"),
        raid_depth_ref=Decimal("0.2"),
        recent_path_efficiency=Decimal("0.6"),
        recent_overlap_rate=Decimal("0.2"),
        first_breach_side="low",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=2,
        last_structure_event_family="reference-liquidity-sweep",
        last_structure_event_age_minutes=1,
        recent_liquidity_event_count_10m=1,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family="fair-value-gap",
        confirmation_latency_minutes=2,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.1"),
        planned_target_r=Decimal("3"),
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.9"),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="CALIBRATED_DEPTH_ECONOMICS_PENDING",
        dol3_state="CALIBRATED_DEPTH_ECONOMICS_PENDING",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
    )


def source():
    candidate = SimpleNamespace(
        family=SimpleNamespace(value="fair-value-gap"),
        formed_at=T - timedelta(minutes=2),
        zone_lower=Decimal("100"),
        zone_upper=Decimal("102"),
    )
    return SimpleNamespace(
        pending_expires_at=T + timedelta(minutes=40),
        side=SimpleNamespace(value="long"),
        structure=SimpleNamespace(raid_at=T - timedelta(minutes=4)),
        candidates=(candidate,),
        reference=SimpleNamespace(
            low=Decimal("100"), high=Decimal("110"),
        ),
    )


def test_fill_candle_and_future_bars_cannot_change_pending_cognition() -> None:
    # At prospective open 15:21, bar(0) is closed; bar(1) is not.
    first = bar(0, 101, 102, 100)
    fill_candle = bar(1, 108, 112, 99)
    args = dict(
        entry_situation=entry(),
        source=source(),
        selected_family="fair-value-gap",
        prospective_fill_open_at=T + timedelta(minutes=1),
        previous_admitted_path_range=Decimal("20"),
    )
    before = build_prospective_fill_observation(
        day_bars=(first,), **args,
    )
    after = build_prospective_fill_observation(
        day_bars=(first, fill_candle), **args,
    )
    assert before == after
    assert before.as_of == (T + timedelta(minutes=1)).isoformat()
    assert before.current_open_r is None
    assert before.double_sided_before_decision is False
    assert before.entry_evidence_freshness == "fresh-0-5m"


def test_later_closed_m1_can_confirm_other_side_and_staleness() -> None:
    candles = [
        bar(i, 101, 102, 100)
        for i in range(7)
    ]
    candles[5] = bar(5, 105, 111, 101)
    kwargs = dict(
        entry_situation=entry(),
        source=source(),
        selected_family="fair-value-gap",
        previous_admitted_path_range=Decimal("20"),
        day_bars=tuple(candles),
    )
    before = build_prospective_fill_observation(
        prospective_fill_open_at=T + timedelta(minutes=5),
        **kwargs,
    )
    after = build_prospective_fill_observation(
        prospective_fill_open_at=T + timedelta(minutes=7),
        **kwargs,
    )
    assert before.double_sided_before_decision is False
    assert after.double_sided_before_decision is True
    assert after.entry_evidence_freshness == "older-than-5m"


def test_fail_closed_on_noncausal_timestamp_and_wrong_session() -> None:
    kwargs = dict(
        entry_situation=entry(),
        source=source(),
        selected_family="fair-value-gap",
        previous_admitted_path_range=Decimal("20"),
        day_bars=(bar(0, 101, 102, 100),),
    )
    with pytest.raises(ValueError, match="outside frozen pending"):
        build_prospective_fill_observation(
            prospective_fill_open_at=T - timedelta(minutes=1),
            **kwargs,
        )
    with pytest.raises(ValueError, match="missing causal completed M1"):
        build_prospective_fill_observation(
            prospective_fill_open_at=T, **kwargs,
        )
    with pytest.raises(ValueError, match="unknown session"):
        build_prospective_fill_observation(
            prospective_fill_open_at=T + timedelta(minutes=1),
            **{**kwargs, "entry_situation": replace(
                entry(), session="LONDON_SILVER_BULLET",
            )},
        )


def test_no_sizing_authority_in_fill_causal_sensor() -> None:
    import inspect
    names = set(inspect.signature(build_prospective_fill_observation).parameters)
    assert not names & {"size", "lot", "leverage", "equity", "capital", "pnl"}
