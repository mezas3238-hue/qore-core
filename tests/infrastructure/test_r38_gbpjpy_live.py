from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.r38_gbpjpy_live import (
    BASE_RISK_FRACTION,
    CERTIFICATION_ARTIFACT_ID,
    CERTIFICATION_IDENTITY,
    CERTIFICATION_RUN_ID,
    IDENTITY,
    MEMORY_PROFILE_COUNTS,
    MEMORY_SHA256,
    R38GbpJpyDol,
    R38GbpJpyLiveSignal,
    R38GbpJpyLiveState,
    R38GbpJpyOpenTrade,
    SELECTED_ENSEMBLE,
    SELECTED_POLICY,
    _risk_scale_for,
    build_r38_gbpjpy_risk_request,
    certified_stop_for_open_trade,
    current_anchor,
    load_memory,
)
from qore.infrastructure.trader_lab import (
    cibo_gbpjpy_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r35_confidence_tier_ensemble as r35,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _spec(*, ask: str = "205.120", bid: str = "205.118") -> Mt5SymbolSpecification:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    return Mt5SymbolSpecification(
        provider_symbol="GBPJPY",
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


def _signal(*, scale: str = "1", side: str = "long") -> R38GbpJpyLiveSignal:
    if side == "long":
        entry, stop, target = "205.120", "204.920", "205.620"
    else:
        entry, stop, target = "205.118", "205.318", "204.618"
    requested = Decimal(scale)
    if requested == Decimal("0.05"):
        base = Decimal("1")
        overlay = Decimal("0.05")
        flags = (
            "CORE_SOURCE_OPPOSITE_BOUNDARY_H1",
            "CORE_CLOSE_LOCATION_Q4",
            "CORE_H4_BODY_WITH",
        )
    else:
        base = requested
        overlay = Decimal("1")
        flags = ()
    return R38GbpJpyLiveSignal(
        signal_fingerprint="a" * 64,
        entry_at=datetime(2026, 9, 18, 15, 0, tzinfo=UTC),
        timeframe="H1",
        side=side,
        certified_entry=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        source_scheme="R34_RANGE_ROUTE_TYPES",
        authority_tier="CORE",
        classification=r35.MAJORITY,
        posture=native.POSTURE_STATIC,
        base_risk_scale=base,
        fragility_flags=flags,
        structural_overlay_scale=overlay,
        risk_scale=base * overlay,
        ladder=(
            R38GbpJpyDol(
                1,
                target,
                "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
            ),
        ),
    )


def test_r38_gbpjpy_certified_identity_and_lineage() -> None:
    assert IDENTITY == "TURTLE_SOUP_GBPJPY_R38"
    assert CERTIFICATION_IDENTITY == "TURTLE_SOUP_GBPJPY_R39_FINAL_CERTIFICATION_SUITE_V1"
    assert CERTIFICATION_RUN_ID == 35374273254
    assert CERTIFICATION_ARTIFACT_ID == 10559463231
    assert SELECTED_ENSEMBLE == "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
    assert SELECTED_POLICY == "CONFIDENCE_100_050_010"
    assert BASE_RISK_FRACTION == Decimal("0.002")
    assert TraderLineage.R38_GBPJPY.value == "R38_GBPJPY"


def test_r38_gbpjpy_committed_memory_is_exactly_bound() -> None:
    memories = load_memory(
        Path("runtime_data/gbpjpy/r38-confidence-tier-memory.json")
    )
    assert len(MEMORY_SHA256) == 64
    assert set(memories) == set(MEMORY_PROFILE_COUNTS)
    assert {
        scheme: len(bundle[2])
        for scheme, bundle in memories.items()
    } == MEMORY_PROFILE_COUNTS


def test_r38_gbpjpy_memory_hash_is_cross_platform_line_ending_stable(
    tmp_path: Path,
) -> None:
    source = Path(
        "runtime_data/gbpjpy/r38-confidence-tier-memory.json"
    ).read_bytes()
    target = tmp_path / "r38-gbpjpy-memory.json"
    target.write_bytes(source.replace(b"\n", b"\r\n"))
    memories = load_memory(target)
    assert set(memories) == set(MEMORY_PROFILE_COUNTS)


def test_r38_gbpjpy_long_request_maps_certified_risk_into_sovereign_risk() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    request, base_risk = build_r38_gbpjpy_risk_request(
        request_id="r38-gbpjpy-test",
        signal=_signal(),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.trader_id is TraderLineage.R38_GBPJPY
    assert request.qore_symbol == "GBPJPY"
    assert request.requested_stop_risk <= base_risk
    assert request.requested_volume >= Decimal("0.01")


def test_r38_gbpjpy_tiny_certified_risk_never_rounds_up_to_minimum_lot() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="below broker minimum"):
        build_r38_gbpjpy_risk_request(
            request_id="r38-gbpjpy-min",
            signal=_signal(scale="0.05"),
            provider_spec=_spec(),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r38_gbpjpy_source_open_drift_over_certified_stress_fails_closed() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="entry drift"):
        build_r38_gbpjpy_risk_request(
            request_id="r38-gbpjpy-drift",
            signal=_signal(),
            provider_spec=_spec(ask="205.141"),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r38_gbpjpy_broker_minimum_stop_level_fails_closed() -> None:
    now = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    spec = _spec()
    strict = replace(
        spec,
        minimum_stop_distance_points=Decimal("250"),
    )
    with pytest.raises(ValueError, match="stops level"):
        build_r38_gbpjpy_risk_request(
            request_id="r38-gbpjpy-stops",
            signal=_signal(),
            provider_spec=strict,
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r38_gbpjpy_anchor_has_hard_two_second_grace() -> None:
    assert current_anchor(
        datetime(2026, 9, 18, 15, 0, 1, 900_000, tzinfo=UTC)
    ) == datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    assert current_anchor(
        datetime(2026, 9, 18, 15, 0, 2, 1_000, tzinfo=UTC)
    ) is None


def test_r38_gbpjpy_core_three_flag_overlay_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import r38_gbpjpy_live as live

    monkeypatch.setattr(
        live.v1,
        "_setup_context",
        lambda _setup: {"close_location_bucket": "q4:>0.75"},
    )
    decision = r35.Decision(
        target=native.NativeTarget(
            rank=1,
            level=Decimal("205.60"),
            route="SOURCE_OPPOSITE_BOUNDARY:H1",
            distance_ticks=Decimal("480"),
            touched=False,
            touch_at=None,
        ),
        posture=native.POSTURE_STATIC,
        classification=r35.MAJORITY,
        observations=50,
        source_scheme="R34_RANGE_ROUTE_TYPES",
        authority_tier="CORE",
    )
    setup = type("Setup", (), {})()
    base, flags, overlay, final = _risk_scale_for(
        setup=setup,  # type: ignore[arg-type]
        regime={"h4_body_alignment": "with"},
        decision=decision,
    )
    assert base == Decimal("1")
    assert len(flags) == 3
    assert overlay == Decimal("0.05")
    assert final == Decimal("0.05")


def test_r38_gbpjpy_expansion_fragility_flags_do_not_suppress_or_rescale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision = r35.Decision(
        target=native.NativeTarget(
            rank=1,
            level=Decimal("205.60"),
            route="SOURCE_OPPOSITE_BOUNDARY:H1",
            distance_ticks=Decimal("480"),
            touched=False,
            touch_at=None,
        ),
        posture=native.POSTURE_STATIC,
        classification=r35.ROBUST,
        observations=50,
        source_scheme="R34_DIRECTION_REGIME_ROUTE_TYPES",
        authority_tier="EXPANSION",
    )
    setup = type("Setup", (), {})()
    setup.context = type("Context", (), {})()
    setup.context.signal = type("Signal", (), {})()
    from qore.infrastructure import r38_gbpjpy_live as live

    monkeypatch.setattr(
        live.v1,
        "_setup_context",
        lambda _setup: {"close_location_bucket": "q4:>0.75"},
    )
    base, flags, overlay, final = _risk_scale_for(
        setup=setup,  # type: ignore[arg-type]
        regime={"h4_body_alignment": "with"},
        decision=decision,
    )
    assert base == Decimal("0.50")
    assert flags == ()
    assert overlay == Decimal("1")
    assert final == Decimal("0.50")


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_r38_gbpjpy_static_posture_never_uses_swing_trailing() -> None:
    at = datetime(2026, 9, 18, 15, 0, tzinfo=UTC)
    evidence = Evidence(
        symbol="GBPJPY",
        digits=3,
        bars=(
            _bar(at, "205.100", "205.300", "205.000", "205.200"),
            _bar(at + timedelta(minutes=5), "205.200", "205.250", "205.050", "205.180"),
            _bar(at + timedelta(minutes=10), "205.180", "205.350", "205.100", "205.300"),
        ),
    )
    opened = R38GbpJpyOpenTrade(
        client_order_id="qore-r38-gbpjpy-test",
        signal_fingerprint="f" * 64,
        entry_at=at.isoformat(),
        side="long",
        entry_price="205.100",
        initial_stop="204.900",
        current_stop="204.900",
        take_profit="205.600",
        posture=native.POSTURE_STATIC,
        target_rank=1,
        target_route="TEST:H1",
        ladder=(R38GbpJpyDol(1, "205.600", "TEST:H1"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    assert certified_stop_for_open_trade(
        opened,
        evidence,
        now=at + timedelta(minutes=15),
    ) == Decimal("204.900")


def test_r38_gbpjpy_state_drawdown_is_diagnostic_not_risk_input() -> None:
    state = R38GbpJpyLiveState(strategy_equity_r="-3", strategy_peak_r="0")
    assert state.drawdown_r == Decimal("3")
