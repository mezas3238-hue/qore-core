from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.r43_gbpusd_live import (
    BASE_RISK_FRACTION,
    CERTIFICATION_ARTIFACT_ID,
    CERTIFICATION_RUN_ID,
    DRAWDOWN_GOVERNOR,
    FAMILY_SET,
    IDENTITY,
    MEMORY_PROFILE_COUNT,
    MEMORY_SHA256,
    RANK2_OVERLAY_SCALE,
    R43Dol,
    R43LiveSignal,
    R43LiveState,
    R43OpenTrade,
    SHORT_OVERLAY_SCALE,
    STRUCTURAL_POLICY,
    _risk_scale_for,
    build_r43_risk_request,
    certified_stop_for_open_trade,
    current_anchor,
    manage_open_position,
    load_memory,
)
from qore.infrastructure.trader_lab import (
    cibo_gbpusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r37_structural_quality_governor as r37,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _spec(*, ask: str = "1.33620", bid: str = "1.33618") -> Mt5SymbolSpecification:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    return Mt5SymbolSpecification(
        provider_symbol="GBPUSD",
        bid=Decimal(bid),
        ask=Decimal(ask),
        spread_points=Decimal("2"),
        digits=5,
        point=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.00001"),
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


def _signal(*, scale: str = "1", side: str = "long") -> R43LiveSignal:
    if side == "long":
        entry, stop, target = "1.33620", "1.33520", "1.34020"
    else:
        entry, stop, target = "1.33618", "1.33718", "1.33218"
    return R43LiveSignal(
        signal_fingerprint="e" * 64,
        entry_at=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        timeframe="H1",
        side=side,
        certified_entry=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        decision_source="R32_REGIME_CORE",
        family=None,
        classification="MAJORITY_VALIDATED_010",
        posture=native.POSTURE_STATIC,
        structural_scale=Decimal("0.25"),
        side_overlay_scale=Decimal("1") if side == "long" else SHORT_OVERLAY_SCALE,
        rank_overlay_scale=Decimal("1"),
        drawdown_scale=Decimal("1"),
        risk_scale=Decimal(scale),
        ladder=(R43Dol(1, target, "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1"),),
    )


def test_r43_certified_identity_and_lineage() -> None:
    assert IDENTITY == "TURTLE_SOUP_GBPUSD_R43"
    assert FAMILY_SET == "R37_G25_FIXED"
    assert STRUCTURAL_POLICY == "SQ3_H1_BALANCED"
    assert DRAWDOWN_GOVERNOR == "DD_1_3_SCALE_075_025"
    assert SHORT_OVERLAY_SCALE == Decimal("0.005")
    assert RANK2_OVERLAY_SCALE == Decimal("0.25")
    assert BASE_RISK_FRACTION == Decimal("0.002")
    assert CERTIFICATION_RUN_ID == 35358106508
    assert CERTIFICATION_ARTIFACT_ID == 10552752028
    assert TraderLineage.R43_GBPUSD.value == "R43_GBPUSD"


def test_r43_committed_memory_is_exactly_bound() -> None:
    fields, route_mode, memory = load_memory(
        Path("runtime_data/gbpusd/r43-r32-regime-memory.json")
    )
    assert len(MEMORY_SHA256) == 64
    assert len(memory) == MEMORY_PROFILE_COUNT == 4246
    assert route_mode == "TYPES_ONLY"
    assert fields == (
        "timeframe",
        "prior_body_alignment",
        "protected_risk_range_bucket",
        "h4_range_state",
        "d1_range_state",
        "m5_volatility_state",
    )


def test_r43_memory_hash_is_cross_platform_line_ending_stable(tmp_path: Path) -> None:
    source = Path("runtime_data/gbpusd/r43-r32-regime-memory.json").read_bytes()
    converted = source.replace(b"\n", b"\r\n")
    target = tmp_path / "r43-memory-windows.json"
    target.write_bytes(converted)
    _fields, _route_mode, memory = load_memory(target)
    assert len(memory) == MEMORY_PROFILE_COUNT


def test_r43_long_request_maps_certified_risk_into_sovereign_risk() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    request, base_risk = build_r43_risk_request(
        request_id="r43-test",
        signal=_signal(scale="1"),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.trader_id is TraderLineage.R43_GBPUSD
    assert request.qore_symbol == "GBPUSD"
    assert request.requested_stop_risk <= base_risk
    assert request.requested_volume >= Decimal("0.01")


def test_r43_tiny_short_risk_never_rounds_up_to_minimum_lot() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="below broker minimum"):
        build_r43_risk_request(
            request_id="r43-short-min",
            signal=_signal(scale="0.005", side="short"),
            provider_spec=_spec(),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r43_source_open_drift_over_certified_stress_fails_closed() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="entry drift"):
        build_r43_risk_request(
            request_id="r43-drift",
            signal=_signal(scale="1"),
            provider_spec=_spec(ask="1.33631"),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r43_anchor_is_hourly_and_has_hard_two_second_grace() -> None:
    assert current_anchor(
        datetime(2026, 9, 18, 15, 0, 1, 900_000, tzinfo=UTC)
    ) == datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    assert current_anchor(
        datetime(2026, 9, 18, 15, 0, 2, 1_000, tzinfo=UTC)
    ) is None


def test_r43_frozen_structural_and_drawdown_scales(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r43_gbpusd_live as live

    monkeypatch.setattr(
        live.v1,
        "_setup_context",
        lambda _setup: {
            "protected_risk_range_bucket": "q3:<=1.0",
            "close_location_bucket": "q4:>0.75",
        },
    )
    decision = r37.Decision(
        target=native.NativeTarget(
            rank=2,
            level=Decimal("1.3400"),
            route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
            distance_ticks=Decimal("380"),
            touched=False,
            touch_at=None,
        ),
        posture=native.POSTURE_STATIC,
        classification="MAJORITY_VALIDATED_010",
        observations=50,
        source="R32_REGIME_CORE",
        family=None,
    )
    setup = type("Setup", (), {})()
    setup.context = type("Context", (), {})()
    setup.context.signal = type("Signal", (), {"side": type("Side", (), {"value": "long"})()})()
    state = R43LiveState(strategy_equity_r="-1.5", strategy_peak_r="0")
    structural, side, rank, dd, scale = _risk_scale_for(
        setup=setup,  # type: ignore[arg-type]
        regime={"h1_range_state": "compressed"},
        decision=decision,
        state=state,
    )
    assert structural == Decimal("0.25")
    assert side == Decimal("1")
    assert rank == Decimal("0.25")
    assert dd == Decimal("0.75")
    assert scale == Decimal("0.046875")


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_r43_static_posture_never_uses_swing_trailing() -> None:
    at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    evidence = Evidence(
        symbol="GBPUSD",
        digits=5,
        bars=(
            _bar(at, "1.3360", "1.3390", "1.3370", "1.3380"),
            _bar(at + timedelta(minutes=5), "1.3380", "1.3390", "1.3360", "1.3375"),
            _bar(at + timedelta(minutes=10), "1.3375", "1.3392", "1.3370", "1.3390"),
        ),
    )
    opened = R43OpenTrade(
        client_order_id="qore-r43-test",
        signal_fingerprint="f" * 64,
        entry_at=at.isoformat(),
        side="long",
        entry_price="1.3350",
        initial_stop="1.3330",
        current_stop="1.3330",
        take_profit="1.3410",
        posture=native.POSTURE_STATIC,
        target_rank=1,
        target_route="TEST",
        ladder=(R43Dol(1, "1.3410", "TEST"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    assert certified_stop_for_open_trade(
        opened,
        evidence,
        now=at + timedelta(minutes=15),
    ) == Decimal("1.3330")


def test_r43_shadow_position_management_never_sends_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r43_gbpusd_live as live

    now = datetime(2026, 9, 18, 20, 5, tzinfo=UTC)
    opened = R43OpenTrade(
        client_order_id="qore-r43-shadow-test",
        signal_fingerprint="d" * 64,
        entry_at=(now - timedelta(hours=1)).isoformat(),
        side="long",
        entry_price="1.3360",
        initial_stop="1.3340",
        current_stop="1.3340",
        take_profit="1.3410",
        posture=native.POSTURE_PROTECT,
        target_rank=1,
        target_route="TEST",
        ladder=(R43Dol(1, "1.3410", "TEST"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    state = R43LiveState(open_trade=opened)
    magic = live._magic(opened.client_order_id)
    sent: list[object] = []

    class Store:
        def reconcile(self, _api: object, *, now: datetime) -> R43LiveState:
            return state

    api = SimpleNamespace(
        TRADE_ACTION_SLTP=6,
        positions_get=lambda: (
            SimpleNamespace(
                magic=magic,
                sl=1.3340,
                type=0,
                ticket=456,
            ),
        ),
        symbol_info=lambda _symbol: SimpleNamespace(trade_tick_size=0.00001),
        order_check=lambda _request: SimpleNamespace(retcode=0),
        order_send=lambda request: sent.append(request),
    )
    monkeypatch.setattr(live, "mt5_management_evidence", lambda *_a, **_k: object())
    monkeypatch.setattr(
        live,
        "certified_stop_for_open_trade",
        lambda *_a, **_k: Decimal("1.3350"),
    )

    _next, reason = manage_open_position(
        api,
        now=now,
        store=Store(),  # type: ignore[arg-type]
        mutations_enabled=False,
    )
    assert reason == "r43-shadow-stop-check-pass:1.3350"
    assert sent == []
