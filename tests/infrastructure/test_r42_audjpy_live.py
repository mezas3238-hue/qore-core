from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.r42_audjpy_live import (
    BASE_RISK_FRACTION,
    BOUNDARY_ARM_LEAD,
    BOUNDARY_RETRY_SECONDS,
    CERTIFICATION_ARTIFACT_ID,
    CERTIFICATION_IDENTITY,
    CERTIFICATION_RUN_ID,
    ENTRY_SLA,
    IDENTITY,
    MAX_BROKER_TICK_AGE,
    MEMORY_FULL_PROFILE_COUNTS,
    MEMORY_PROFILE_COUNTS,
    MEMORY_SHA256,
    NORMAL_FEED_REFRESH_SECONDS,
    SECOND_LAYER_POLICY,
    SELECTED_ENSEMBLE,
    SELECTED_POLICY,
    R42AudJpyDol,
    R42AudJpyLiveSignal,
    R42AudJpyLiveState,
    R42AudJpyM5Cache,
    R42AudJpyOpenTrade,
    _risk_scale_for,
    build_r42_audjpy_risk_request,
    certified_stop_for_open_trade,
    current_anchor,
    load_memory,
)
from qore.infrastructure.trader_lab import (
    cibo_audjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r38_structural_fragility_risk_correction as r38,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _spec(*, ask: str = "110.120", bid: str = "110.118") -> Mt5SymbolSpecification:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    return Mt5SymbolSpecification(
        provider_symbol="AUDJPY",
        bid=Decimal(bid),
        ask=Decimal(ask),
        spread_points=Decimal("2"),
        digits=3,
        point=Decimal("0.001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.001"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("40"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("1000"),
        trade_enabled=True,
        session_open=True,
        observed_at=now,
    )


def _signal(
    *,
    side: str = "long",
    base: Decimal = Decimal("1"),
    first: Decimal = Decimal("1"),
    second: Decimal = Decimal("1"),
) -> R42AudJpyLiveSignal:
    if side == "long":
        entry, stop, target = "110.120", "109.920", "110.620"
    else:
        entry, stop, target = "110.118", "110.318", "109.618"
    return R42AudJpyLiveSignal(
        signal_fingerprint="a" * 64,
        entry_at=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        boundary_tick_at=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        timeframe="H1",
        side=side,
        certified_entry=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        source_scheme="R32_CORE_ROUTE_TYPES",
        authority_tier="CORE",
        classification=r38.MAJORITY,
        posture=native.POSTURE_STATIC,
        base_risk_scale=base,
        first_layer_fragility_flags=(),
        first_layer_overlay_scale=first,
        second_layer_fragility_flags=(),
        second_layer_overlay_scale=second,
        risk_scale=base * first * second,
        ladder=(
            R42AudJpyDol(
                1,
                target,
                "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
            ),
        ),
    )


def test_r42_audjpy_certified_identity_and_lineage() -> None:
    assert IDENTITY == "TURTLE_SOUP_AUDJPY_R42"
    assert CERTIFICATION_IDENTITY == "TURTLE_SOUP_AUDJPY_R43_FINAL_CERTIFICATION_SUITE_V1"
    assert CERTIFICATION_RUN_ID == 35400542409
    assert CERTIFICATION_ARTIFACT_ID == 10570670638
    assert SELECTED_ENSEMBLE == "R38_FROZEN_SIGNAL_BASELINE"
    assert SELECTED_POLICY == "AUDJPY_CONFIDENCE_100_075_025"
    assert BASE_RISK_FRACTION == Decimal("0.002")
    assert TraderLineage.R42_AUDJPY.value == "R42_AUDJPY"


def test_r42_audjpy_committed_memory_is_exactly_bound() -> None:
    memories = load_memory(
        Path("runtime_data/audjpy/r42-causal-authority-memory.json")
    )
    assert MEMORY_SHA256 == "22cc9fbccb8d88fe5e5027c93d93412b3cee3f9e724dae034ff9f56a0e82cfe6"
    assert {
        scheme: len(bundle[2])
        for scheme, bundle in memories.items()
    } == MEMORY_PROFILE_COUNTS
    assert MEMORY_FULL_PROFILE_COUNTS == {
        "R32_CORE_ROUTE_TYPES": 8092,
        "R34_DIRECTION_REGIME_ROUTE_TYPES": 3535,
        "R34_TIMEFRAME_REGIME_ROUTE_TYPES": 449,
    }


def test_r42_audjpy_memory_hash_is_cross_platform_line_ending_stable(
    tmp_path: Path,
) -> None:
    source = Path(
        "runtime_data/audjpy/r42-causal-authority-memory.json"
    ).read_bytes()
    target = tmp_path / "r42-audjpy-memory.json"
    normalized = source.replace(b"\r\n", b"\n")
    target.write_bytes(normalized.replace(b"\n", b"\r\n"))
    assert set(load_memory(target)) == set(MEMORY_PROFILE_COUNTS)


def test_r42_audjpy_request_maps_certified_risk_into_sovereign_risk() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    request, base_risk = build_r42_audjpy_risk_request(
        request_id="r42-audjpy-test",
        signal=_signal(),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.trader_id is TraderLineage.R42_AUDJPY
    assert request.qore_symbol == "AUDJPY"
    assert request.requested_stop_risk <= base_risk
    assert request.requested_volume >= Decimal("0.01")


def test_r42_audjpy_tiny_certified_risk_requests_minimum_lot() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    request, _ = build_r42_audjpy_risk_request(
        request_id="r42-audjpy-min",
        signal=_signal(first=Decimal("0.01"), second=Decimal("0.10")),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert request.requested_volume == Decimal("0.01")
    assert request.minimum_volume_uplifted is True
    assert request.requested_stop_risk > request.strategy_requested_risk_usd


def test_r42_audjpy_source_open_drift_fails_closed() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="entry drift"):
        build_r42_audjpy_risk_request(
            request_id="r42-audjpy-drift",
            signal=_signal(),
            provider_spec=_spec(ask="110.141"),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r42_audjpy_broker_stop_level_fails_closed() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    strict = replace(_spec(), minimum_stop_distance_points=Decimal("250"))
    with pytest.raises(ValueError, match="stops level"):
        build_r42_audjpy_risk_request(
            request_id="r42-audjpy-stops",
            signal=_signal(),
            provider_spec=strict,
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r42_audjpy_risk_request_rejects_after_m5_deadline() -> None:
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    fresh = replace(_spec(), observed_at=anchor + timedelta(seconds=2, milliseconds=1))
    with pytest.raises(ValueError, match="M5 order-send deadline expired"):
        build_r42_audjpy_risk_request(
            request_id="r42-audjpy-late",
            signal=_signal(),
            provider_spec=fresh,
            account_equity=Decimal("2000"),
            now=anchor + timedelta(seconds=2, milliseconds=1),
        )


def test_r42_audjpy_risk_request_rejects_stale_broker_tick() -> None:
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    stale_spec = replace(
        _spec(),
        observed_at=anchor - timedelta(seconds=2, milliseconds=1),
    )
    with pytest.raises(ValueError, match="broker executable snapshot older than 2s"):
        build_r42_audjpy_risk_request(
            request_id="r42-audjpy-stale-tick",
            signal=_signal(),
            provider_spec=stale_spec,
            account_equity=Decimal("2000"),
            now=anchor,
        )


class _FakeM5Api:
    TIMEFRAME_M5 = 5

    def __init__(self, rows: list[dict[str, object]], *, tick_at: datetime) -> None:
        self.rows = rows
        self.tick_at = tick_at
        self.copy_counts: list[int] = []

    def copy_rates_from_pos(
        self,
        _symbol: str,
        _timeframe: int,
        _start: int,
        count: int,
    ) -> list[dict[str, object]]:
        self.copy_counts.append(count)
        return self.rows[-count:]

    def symbol_info(self, _symbol: str) -> SimpleNamespace:
        return SimpleNamespace(digits=3)

    def symbol_info_tick(self, _symbol: str) -> SimpleNamespace:
        return SimpleNamespace(
            time=int(self.tick_at.timestamp()),
            time_msc=int(self.tick_at.timestamp() * 1000),
        )


def _m5_row(at: datetime, price: Decimal) -> dict[str, object]:
    return {
        "time": int(at.timestamp()),
        "open": float(price),
        "high": float(price + Decimal("0.010")),
        "low": float(price - Decimal("0.010")),
        "close": float(price),
    }


def test_r42_audjpy_cache_preloads_once_then_reads_recent_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r42_audjpy_live as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    start = anchor - timedelta(minutes=5 * 2000)
    rows = [
        _m5_row(start + timedelta(minutes=5 * index), Decimal("110"))
        for index in range(2000)
    ]
    api = _FakeM5Api(rows, tick_at=anchor)
    cache = R42AudJpyM5Cache()
    cache.preload(api, now=anchor - timedelta(seconds=10))
    assert cache.preload_calls == 1
    assert api.copy_counts == [15000]
    with pytest.raises(RuntimeError, match="preload may run only once"):
        cache.preload(api, now=anchor - timedelta(seconds=9))

    api.rows.append(_m5_row(anchor, Decimal("110.120")))
    cache.refresh_incremental(api, now=anchor, count=4)
    assert cache.incremental_calls == 1
    assert api.copy_counts[-1] == 4
    snapshot = cache.boundary_snapshot(
        api,
        anchor=anchor,
        observed_at=anchor + timedelta(milliseconds=200),
    )
    assert snapshot.anchor == anchor
    assert snapshot.current_open == Decimal("110.12")


def test_r42_audjpy_boundary_snapshot_requires_exact_new_and_closed_m5(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r42_audjpy_live as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    start = anchor - timedelta(minutes=5 * 2000)
    rows = [
        _m5_row(start + timedelta(minutes=5 * index), Decimal("110"))
        for index in range(2000)
    ]
    api = _FakeM5Api(rows, tick_at=anchor)
    cache = R42AudJpyM5Cache()
    cache.preload(api, now=anchor - timedelta(seconds=10))
    with pytest.raises(RuntimeError, match="exact new M5 unavailable"):
        cache.boundary_snapshot(
            api,
            anchor=anchor,
            observed_at=anchor + timedelta(milliseconds=100),
        )


def test_r42_audjpy_boundary_snapshot_rejects_tick_older_than_two_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r42_audjpy_live as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    start = anchor - timedelta(minutes=5 * 2000)
    rows = [
        _m5_row(start + timedelta(minutes=5 * index), Decimal("110"))
        for index in range(2000)
    ]
    rows.append(_m5_row(anchor, Decimal("110.120")))
    api = _FakeM5Api(
        rows,
        tick_at=anchor - timedelta(seconds=2, milliseconds=1),
    )
    cache = R42AudJpyM5Cache()
    cache.preload(api, now=anchor - timedelta(seconds=10))
    with pytest.raises(RuntimeError, match="broker tick older than 2s"):
        cache.boundary_snapshot(
            api,
            anchor=anchor,
            observed_at=anchor,
        )


def test_r42_audjpy_anchor_uses_m5_two_second_decision_window() -> None:
    anchor = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    assert current_anchor(anchor + timedelta(seconds=1, milliseconds=999)) == anchor
    assert current_anchor(anchor + timedelta(seconds=2, milliseconds=1)) is None
    assert ENTRY_SLA == timedelta(seconds=2)
    assert BOUNDARY_ARM_LEAD == timedelta(seconds=10)
    assert BOUNDARY_RETRY_SECONDS == pytest.approx(0.075)
    assert NORMAL_FEED_REFRESH_SECONDS == pytest.approx(1.0)
    assert MAX_BROKER_TICK_AGE == timedelta(seconds=2)


def test_r42_audjpy_dual_fragility_overlay_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r42_audjpy_live as live

    monkeypatch.setattr(
        live.v1,
        "_setup_context",
        lambda _setup: {
            "strategy_projected_r_bucket": "q2:<=1.0",
            "raid_depth_range_bucket": "q4:<=0.50",
            "source_range_state_bucket": "q2:<=1.0",
        },
    )
    decision = r38.Decision(
        target=native.NativeTarget(
            rank=1,
            level=Decimal("110.60"),
            route="SOURCE_OPPOSITE_BOUNDARY:H1",
            distance_ticks=Decimal("480"),
            touched=False,
            touch_at=None,
        ),
        posture=native.POSTURE_STATIC,
        classification=r38.MAJORITY,
        observations=50,
        source_scheme="R34_DIRECTION_REGIME_ROUTE_TYPES",
        authority_tier="EXPANSION",
        fragility_flags=(
            "M5_EFFICIENCY_MEDIUM",
            "D1_RANGE_EXPANDED",
            "PROJECTED_R_Q2_LE_1",
        ),
    )
    setup = type("Setup", (), {})()
    base, first_flags, first, second_flags, second, final = _risk_scale_for(
        setup=setup,  # type: ignore[arg-type]
        regime={"d1_body_alignment": "opposed"},
        decision=decision,
    )
    assert base == Decimal("0.25")
    assert len(first_flags) == 3
    assert first == Decimal("0.01")
    assert len(second_flags) == 3
    assert second == Decimal("0.10")
    assert final == Decimal("0.00025")
    assert min(SECOND_LAYER_POLICY) > Decimal("0")


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_r42_audjpy_static_posture_never_uses_swing_trailing() -> None:
    at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    evidence = Evidence(
        symbol="AUDJPY",
        digits=3,
        bars=(
            _bar(at, "110.100", "110.300", "110.000", "110.200"),
            _bar(at + timedelta(minutes=5), "110.200", "110.250", "110.050", "110.180"),
            _bar(at + timedelta(minutes=10), "110.180", "110.350", "110.100", "110.300"),
        ),
    )
    opened = R42AudJpyOpenTrade(
        client_order_id="qore-r42-audjpy-test",
        signal_fingerprint="f" * 64,
        entry_at=at.isoformat(),
        side="long",
        entry_price="110.100",
        initial_stop="109.900",
        current_stop="109.900",
        take_profit="110.600",
        posture=native.POSTURE_STATIC,
        target_rank=1,
        target_route="TEST:H1",
        ladder=(R42AudJpyDol(1, "110.600", "TEST:H1"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    assert certified_stop_for_open_trade(
        opened,
        evidence,
        now=at + timedelta(minutes=15),
    ) == Decimal("109.900")


def test_r42_audjpy_state_drawdown_is_diagnostic_not_risk_input() -> None:
    state = R42AudJpyLiveState(strategy_equity_r="-3", strategy_peak_r="0")
    assert state.drawdown_r == Decimal("3")
