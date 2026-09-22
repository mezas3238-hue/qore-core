from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.r38_eurusd_live import (
    BASE_RISK_FRACTION,
    COGNITIVE_SHA256,
    FAMILY_SET,
    GOVERNOR,
    IDENTITY,
    R38Dol,
    R38LiveSignal,
    R38OpenTrade,
    _risk_scale_for,
    build_r38_risk_request,
    certified_stop_for_open_trade,
    current_anchor,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)


def _spec(*, ask: str = "1.10000", bid: str = "1.09998") -> Mt5SymbolSpecification:
    now = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    return Mt5SymbolSpecification(
        provider_symbol="EURUSD",
        bid=Decimal(bid),
        ask=Decimal(ask),
        spread_points=Decimal("2"),
        digits=5,
        point=Decimal("0.00001"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.00001"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("1000"),
        trade_enabled=True,
        session_open=True,
        observed_at=now,
    )


def _signal(*, scale: str = "0.50") -> R38LiveSignal:
    return R38LiveSignal(
        signal_fingerprint="b" * 64,
        entry_at=datetime(2026, 9, 18, 6, 0, tzinfo=UTC),
        timeframe="H1",
        side="long",
        certified_entry=Decimal("1.10000"),
        stop_loss=Decimal("1.09950"),
        take_profit=Decimal("1.10400"),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        decision_source="R30_CORE",
        family=None,
        posture="STATIC",
        fragility_flags=("BALANCED_M5_VOLATILITY",),
        base_fragility_scale=Decimal("0.50"),
        structural_overlay_scale=Decimal("1"),
        risk_scale=Decimal(scale),
        ladder=(R38Dol(1, "1.10400", "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1"),),
    )


def test_r38_certified_identity_and_lineage() -> None:
    assert IDENTITY == "TURTLE_SOUP_EURUSD_R38"
    assert FAMILY_SET == "R36_F235_FROZEN"
    assert GOVERNOR == "FRAGILITY_050_025_010"
    assert BASE_RISK_FRACTION == Decimal("0.002")
    assert len(COGNITIVE_SHA256) == 64
    assert TraderLineage.R38_EURUSD.value == "R38_EURUSD"


def test_r38_request_maps_certified_scale_into_sovereign_risk() -> None:
    now = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    request, base_risk = build_r38_risk_request(
        request_id="r38-test",
        signal=_signal(),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.trader_id is TraderLineage.R38_EURUSD
    assert request.qore_symbol == "EURUSD"
    assert request.requested_stop_risk <= base_risk * Decimal("0.50")
    assert request.stop_loss == Decimal("1.09950")
    assert request.take_profit == Decimal("1.10400")


def test_r38_minimum_broker_volume_uses_shared_risk_headroom() -> None:
    now = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    request, base_risk = build_r38_risk_request(
        request_id="r38-minimum-volume",
        signal=_signal(scale="0.01"),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.requested_volume == Decimal("0.01")
    assert request.minimum_volume == Decimal("0.01")
    assert request.minimum_volume_uplifted is True
    assert request.strategy_requested_risk_usd == Decimal("0.04000")
    assert request.requested_stop_risk > request.strategy_requested_risk_usd


def test_r38_source_open_drift_over_certified_stress_fails_closed() -> None:
    now = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="entry drift"):
        build_r38_risk_request(
            request_id="r38-drift",
            signal=_signal(),
            provider_spec=_spec(ask="1.10006"),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r38_new_york_anchor_is_hourly_and_short_grace_only() -> None:
    assert current_anchor(datetime(2026, 9, 18, 6, 0, 1, tzinfo=UTC)) == datetime(
        2026, 9, 18, 6, 0, tzinfo=UTC
    )
    assert current_anchor(datetime(2026, 9, 18, 6, 0, 2, 1_000, tzinfo=UTC)) is None


def test_r38_structural_overlays_are_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    from qore.infrastructure import r38_eurusd_live as live

    monkeypatch.setattr(live.v1, "_setup_context", lambda _setup: {})
    monkeypatch.setattr(
        live.r36,
        "_fragility_flags",
        lambda _item: ("A", "B"),
    )
    monkeypatch.setattr(
        live.r36,
        "_fragility_scale",
        lambda count, _rule: Decimal("0.25") if count == 2 else Decimal("1"),
    )
    flags, base, overlay, scale = _risk_scale_for(
        setup=object(),  # type: ignore[arg-type]
        regime={},
        family=live.r36.F5,
        side="short",
        target_route="ANY",
    )
    assert flags == ("A", "B")
    assert base == Decimal("0.25")
    assert overlay == Decimal("0.10")
    assert scale == Decimal("0.025")

    _, _, overlay2, scale2 = _risk_scale_for(
        setup=object(),  # type: ignore[arg-type]
        regime={},
        family=None,
        side="long",
        target_route=live.UNSTABLE_LONG_ROUTE,
    )
    assert overlay2 == Decimal("0.50")
    assert scale2 == Decimal("0.125")


def _bar(at: datetime, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_r38_protect_posture_advances_only_after_confirmed_swing() -> None:
    at = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    evidence = Evidence(
        symbol="EURUSD",
        digits=5,
        bars=(
            _bar(at, "1.1005", "1.1030", "1.1020", "1.1025"),
            _bar(at + timedelta(minutes=5), "1.1025", "1.1030", "1.1010", "1.1020"),
            _bar(at + timedelta(minutes=10), "1.1020", "1.1032", "1.1025", "1.1030"),
        ),
    )
    opened = R38OpenTrade(
        client_order_id="qore-test",
        signal_fingerprint="c" * 64,
        entry_at=at.isoformat(),
        side="long",
        entry_price="1.1000",
        initial_stop="1.0980",
        current_stop="1.0980",
        take_profit="1.1050",
        posture="PROTECT",
        target_rank=1,
        target_route="TEST",
        ladder=(R38Dol(1, "1.1050", "TEST"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    assert certified_stop_for_open_trade(
        opened,
        evidence,
        now=at + timedelta(minutes=15),
    ) == Decimal("1.1010")


def test_r38_static_posture_never_uses_swing_trailing() -> None:
    at = datetime(2026, 9, 18, 6, 0, tzinfo=UTC)
    evidence = Evidence(
        symbol="EURUSD",
        digits=5,
        bars=(
            _bar(at, "1.1005", "1.1030", "1.1020", "1.1025"),
            _bar(at + timedelta(minutes=5), "1.1025", "1.1030", "1.1010", "1.1020"),
            _bar(at + timedelta(minutes=10), "1.1020", "1.1032", "1.1025", "1.1030"),
        ),
    )
    opened = R38OpenTrade(
        client_order_id="qore-test",
        signal_fingerprint="d" * 64,
        entry_at=at.isoformat(),
        side="long",
        entry_price="1.1000",
        initial_stop="1.0980",
        current_stop="1.0980",
        take_profit="1.1050",
        posture="STATIC",
        target_rank=1,
        target_route="TEST",
        ladder=(R38Dol(1, "1.1050", "TEST"),),
        base_risk_usd="4",
        risk_scale="1",
    )
    assert certified_stop_for_open_trade(
        opened,
        evidence,
        now=at + timedelta(minutes=15),
    ) == Decimal("1.0980")
