from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.trader_execution_profile import M1_PROFILE, M5_PROFILE
from qore.infrastructure.vt31_nas100_live import (
    CERTIFICATION_REPORT_SHA256,
    DECISION_DEADLINE,
    EXECUTION_BINDING_FINGERPRINT,
    EXECUTION_BINDING_ID,
    MAX_BROKER_TICK_AGE,
    PROVIDER_SYMBOL,
    TARGET_ARCHITECTURE_ID,
    Vt31Nas100LiveError,
    Vt31Nas100SlaExpired,
    Vt31RiskContext,
    Vt31VirtualCandidate,
    assert_deadline,
    build_risk_request,
    resolve_certified_risk,
    virtual_oco_trigger,
)
from qore.infrastructure.vt31_nas100_state import (
    Vt31Nas100LiveState,
    Vt31Nas100LiveStateStore,
)


def _spec(observed_at: datetime) -> Mt5SymbolSpecification:
    return Mt5SymbolSpecification(
        provider_symbol="NDX100",
        bid=Decimal("20000.0"),
        ask=Decimal("20000.2"),
        spread_points=Decimal("2"),
        digits=1,
        point=Decimal("0.1"),
        contract_size=Decimal("1"),
        tick_size=Decimal("0.1"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("0.1"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("0.1"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("100"),
        trade_enabled=True,
        session_open=True,
        observed_at=observed_at,
    )


def _candidate(*, entry: str, expires_at: datetime) -> Vt31VirtualCandidate:
    return Vt31VirtualCandidate(
        candidate_id=f"c-{entry}",
        signal_fingerprint=f"f-{entry}",
        side="long",
        family="breaker",
        formed_at=expires_at - timedelta(minutes=2),
        decision_at=expires_at - timedelta(minutes=1),
        expires_at=expires_at,
        entry_price=Decimal(entry),
        stop_loss=Decimal(entry) - Decimal("10"),
        take_profit=Decimal(entry) + Decimal("20"),
    )


def test_vt31_provider_symbol_is_frozen_to_fundednext_ndx100() -> None:
    assert PROVIDER_SYMBOL == "NDX100"


def test_certified_v4_execution_binding_is_exact() -> None:
    assert (
        EXECUTION_BINDING_ID
        == "VT31_NAS100_STRUCTURAL_TARGET_EXECUTION_BINDING_V4"
    )
    assert (
        EXECUTION_BINDING_FINGERPRINT
        == "e85ecc5d82f6c59061afd68863b0f641a3512b1cf132f3b8fb01be324ce7e842"
    )
    assert (
        CERTIFICATION_REPORT_SHA256
        == "0d3aaa077cf8e7de27a08fcd84a7b83f62ee45561bd4deba3a19ebe6e13e9018"
    )
    assert TARGET_ARCHITECTURE_ID == "EQ50_COMPRESSED_ACCEPT_RUN25_PHYSICAL_V4"


def test_execution_profiles_are_frozen_per_timeframe() -> None:
    assert M1_PROFILE.timeframe == "M1"
    assert M1_PROFILE.decision_deadline_seconds == Decimal("5.0")
    assert M1_PROFILE.order_send_deadline_seconds == Decimal("5.0")
    assert M1_PROFILE.tick_max_age_seconds == Decimal("2.0")
    assert M5_PROFILE.timeframe == "M5"
    assert M5_PROFILE.decision_deadline_seconds == Decimal("10.0")
    assert M5_PROFILE.order_send_deadline_seconds == Decimal("10.0")
    assert M5_PROFILE.tick_max_age_seconds == Decimal("2.0")
    assert DECISION_DEADLINE == timedelta(seconds=5)
    assert MAX_BROKER_TICK_AGE == timedelta(seconds=2)


def test_m1_deadline_accepts_exact_five_seconds_and_rejects_late() -> None:
    anchor = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    assert_deadline(
        anchor=anchor,
        now=anchor + timedelta(seconds=5),
        stage="test",
    )
    with pytest.raises(Vt31Nas100SlaExpired):
        assert_deadline(
            anchor=anchor,
            now=anchor + timedelta(seconds=5, milliseconds=1),
            stage="test",
        )


def test_virtual_oco_requires_fresh_tick_and_rejects_multi_price_ambiguity() -> None:
    now = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    expiry = now + timedelta(minutes=10)
    one = _candidate(entry="20001", expires_at=expiry)
    selected = virtual_oco_trigger(
        (one,),
        bid=Decimal("20000.8"),
        ask=Decimal("20000.9"),
        tick_at=now - timedelta(seconds=2),
        now=now,
    )
    assert selected == one

    with pytest.raises(Vt31Nas100LiveError):
        virtual_oco_trigger(
            (one,),
            bid=Decimal("20000.8"),
            ask=Decimal("20000.9"),
            tick_at=now - timedelta(seconds=2, milliseconds=1),
            now=now,
        )

    two = _candidate(entry="20002", expires_at=expiry)
    with pytest.raises(Vt31Nas100LiveError):
        virtual_oco_trigger(
            (one, two),
            bid=Decimal("20000.8"),
            ask=Decimal("20000.9"),
            tick_at=now,
            now=now,
        )


def test_certified_risk_stack_and_lineage_are_bound() -> None:
    context = Vt31RiskContext(
        tier="CORE",
        entry_family="breaker",
        side="long",
        nominal_risk_r=Decimal("1.00"),
        h1_state="mixed",
        premarket_state="bearish",
        cash_open_state="rotation",
        confirmation_latency_minutes=4,
        risk_ref=Decimal("0.20"),
        current_path_vs_previous=Decimal("1.00"),
    )
    resolution = resolve_certified_risk(context)
    assert resolution.allocation_multiplier == Decimal("1.20")
    assert resolution.global_scalar == Decimal("0.60")
    assert resolution.breaker_regime_multiplier == Decimal("0.35")
    assert resolution.final_risk_r == Decimal("0.2520000")

    now = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    request, one_r = build_risk_request(
        request_id="vt31-test",
        signal_fingerprint="signal-test",
        side="long",
        entry=Decimal("20000"),
        stop_loss=Decimal("19990"),
        take_profit=Decimal("20020"),
        certified_risk_r=Decimal("1"),
        provider_spec=_spec(now),
        account_equity=Decimal("100000"),
        decision_anchor=now,
        reservation_expires_at=now + timedelta(minutes=30),
        now=now,
    )
    assert request.trader_id is TraderLineage.VT31_NAS100
    assert request.requested_volume == Decimal("1.9")
    assert one_r == Decimal("200")


def test_symbol_snapshot_older_than_two_seconds_fails_closed() -> None:
    now = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    with pytest.raises(Vt31Nas100LiveError, match="older than 2s"):
        build_risk_request(
            request_id="vt31-stale",
            signal_fingerprint="stale",
            side="long",
            entry=Decimal("20000"),
            stop_loss=Decimal("19990"),
            take_profit=Decimal("20020"),
            certified_risk_r=Decimal("1"),
            provider_spec=_spec(now - timedelta(seconds=2, milliseconds=1)),
            account_equity=Decimal("100000"),
            decision_anchor=now,
            reservation_expires_at=now + timedelta(minutes=30),
            now=now,
        )


def test_certified_partial_leg_granularity_fails_closed() -> None:
    now = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    spec = _spec(now)
    tiny = Mt5SymbolSpecification(
        **{
            field: getattr(spec, field)
            for field in spec.__dataclass_fields__
            if field != "minimum_volume"
        },
        minimum_volume=Decimal("0.5"),
    )
    with pytest.raises(Vt31Nas100LiveError, match="partial legs"):
        build_risk_request(
            request_id="vt31-tiny",
            signal_fingerprint="tiny",
            side="long",
            entry=Decimal("20000"),
            stop_loss=Decimal("19990"),
            take_profit=Decimal("20020"),
            certified_risk_r=Decimal("1"),
            provider_spec=tiny,
            account_equity=Decimal("100000"),
            decision_anchor=now,
            reservation_expires_at=now + timedelta(minutes=30),
            now=now,
        )


def test_live_state_store_roundtrips_empty_state(tmp_path: Path) -> None:
    path = tmp_path / "vt31.json"
    store = Vt31Nas100LiveStateStore(path)
    assert store.load() == Vt31Nas100LiveState()
    store.store(Vt31Nas100LiveState())
    assert store.load() == Vt31Nas100LiveState()
