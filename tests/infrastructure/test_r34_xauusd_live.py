from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.r34_xauusd_live import (
    BASE_RISK_FRACTION,
    FAMILY_SET,
    GOVERNOR,
    IDENTITY,
    R34LiveSignal,
    R34LiveState,
    build_r34_risk_request,
    current_anchor,
)


def _spec(*, ask: str = "4300.00", bid: str = "4299.90") -> Mt5SymbolSpecification:
    now = datetime(2026, 9, 18, 5, 0, tzinfo=UTC)
    return Mt5SymbolSpecification(
        provider_symbol="XAUUSD",
        bid=Decimal(bid),
        ask=Decimal(ask),
        spread_points=Decimal("10"),
        digits=2,
        point=Decimal("0.01"),
        contract_size=Decimal("100"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("100"),
        trade_enabled=True,
        session_open=True,
        observed_at=now,
    )


def _signal(*, scale: str = "1") -> R34LiveSignal:
    return R34LiveSignal(
        signal_fingerprint="a" * 64,
        entry_at=datetime(2026, 9, 18, 5, 0, tzinfo=UTC),
        timeframe="H1",
        side="long",
        certified_entry=Decimal("4300.00"),
        stop_loss=Decimal("4297.20"),
        take_profit=Decimal("4320.00"),
        target_rank=1,
        target_route="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        decision_source="R30_CORE",
        family=None,
        risk_scale=Decimal(scale),
    )


def test_r34_frozen_identity_and_governor() -> None:
    assert IDENTITY == "TURTLE_SOUP_XAUUSD_R34"
    assert FAMILY_SET == "R33_FIVE_FAMILY"
    assert GOVERNOR == "DD_2_4_SCALE_075_025"
    assert BASE_RISK_FRACTION == Decimal("0.002")
    assert TraderLineage.R34_XAUUSD.value == "R34_XAUUSD"


@pytest.mark.parametrize(
    ("equity", "peak", "expected"),
    [
        ("0", "0", Decimal("1")),
        ("8", "10", Decimal("0.75")),
        ("6", "10", Decimal("0.25")),
    ],
)
def test_r34_governor_uses_own_strategy_drawdown(
    equity: str,
    peak: str,
    expected: Decimal,
) -> None:
    state = R34LiveState(equity_r=equity, peak_r=peak)
    assert state.risk_scale == expected


def test_r34_request_maps_one_r_to_account_equity_then_risk_scale() -> None:
    now = datetime(2026, 9, 18, 5, 0, tzinfo=UTC)
    request, base_risk = build_r34_risk_request(
        request_id="r34-test",
        signal=_signal(scale="0.75"),
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.trader_id is TraderLineage.R34_XAUUSD
    assert request.qore_symbol == "XAUUSD"
    assert request.requested_stop_risk <= base_risk * Decimal("0.75")
    assert request.stop_loss == Decimal("4297.20")
    assert request.take_profit == Decimal("4320.00")


def test_r34_source_open_drift_over_certified_stress_fails_closed() -> None:
    now = datetime(2026, 9, 18, 5, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="entry drift"):
        build_r34_risk_request(
            request_id="r34-drift",
            signal=_signal(),
            provider_spec=_spec(ask="4300.29"),
            account_equity=Decimal("2000"),
            now=now,
        )


def test_r34_anchor_is_hourly_and_short_grace_only() -> None:
    assert current_anchor(datetime(2026, 9, 18, 5, 0, 1, tzinfo=UTC)) == datetime(
        2026, 9, 18, 5, 0, tzinfo=UTC
    )
    assert current_anchor(datetime(2026, 9, 18, 5, 0, 2, 1_000, tzinfo=UTC)) is None


def test_r34_wide_stop_requests_minimum_lot_for_shared_risk_authority() -> None:
    now = datetime(2026, 9, 18, 5, 0, tzinfo=UTC)
    wide = replace(_signal(), stop_loss=Decimal("4290.00"))
    request, _ = build_r34_risk_request(
        request_id="r34-min-lot",
        signal=wide,
        provider_spec=_spec(),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert request.requested_volume == Decimal("0.01")
    assert request.minimum_volume_uplifted is True
    assert request.requested_stop_risk > request.strategy_requested_risk_usd


def test_r34_live_incident_minimum_lot_is_delegated_to_shared_risk() -> None:
    now = datetime(2026, 9, 22, 5, 0, tzinfo=UTC)
    signal = replace(
        _signal(),
        signal_fingerprint="3e20d162888f51d8cec43b42eb4d83b96ce6a070339ed49964d46c1c9d72887d",
        entry_at=now,
        certified_entry=Decimal("4342.79"),
        stop_loss=Decimal("4335.02"),
        take_profit=Decimal("4349.28"),
    )
    request, base_risk = build_r34_risk_request(
        request_id="r34-live-20260922-0500",
        signal=signal,
        provider_spec=_spec(bid="4342.42", ask="4342.90"),
        account_equity=Decimal("2000"),
        now=now,
    )
    assert base_risk == Decimal("4.000")
    assert request.requested_volume == Decimal("0.01")
    assert request.stop_loss_per_volume == Decimal("810.847612800")
    assert request.requested_stop_risk == Decimal("8.10847612800")
    assert request.minimum_volume_uplifted is True
