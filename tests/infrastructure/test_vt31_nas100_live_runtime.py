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
    Vt31Nas100M1Cache,
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
    assert M1_PROFILE.decision_deadline_seconds == Decimal("2.0")
    assert M1_PROFILE.order_send_deadline_seconds == Decimal("2.0")
    assert M1_PROFILE.tick_max_age_seconds == Decimal("2.0")
    assert M5_PROFILE.timeframe == "M5"
    assert M5_PROFILE.decision_deadline_seconds == Decimal("2.0")
    assert M5_PROFILE.order_send_deadline_seconds == Decimal("2.0")
    assert M5_PROFILE.tick_max_age_seconds == Decimal("2.0")
    assert DECISION_DEADLINE == timedelta(seconds=2)
    assert MAX_BROKER_TICK_AGE == timedelta(seconds=2)


def test_m1_deadline_accepts_exact_two_seconds_and_rejects_late() -> None:
    anchor = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    assert_deadline(
        anchor=anchor,
        now=anchor + timedelta(seconds=2),
        stage="test",
    )
    with pytest.raises(Vt31Nas100SlaExpired):
        assert_deadline(
            anchor=anchor,
            now=anchor + timedelta(seconds=2, milliseconds=1),
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


def test_m1_replay_fails_under_old_seal_rule_and_reconciles_late_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    opened = datetime(2026, 9, 20, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda _raw: opened,
    )
    cache = Vt31Nas100M1Cache()

    open_row = {
        "time": 1,
        "open": 20000.0,
        "high": 20002.0,
        "low": 19999.0,
        "close": 20001.0,
        "tick_volume": 10,
        "real_volume": 0,
        "spread": 2,
    }
    final_row = {
        **open_row,
        "high": 20003.0,
        "close": 20002.0,
        "tick_volume": 20,
    }
    rewritten_row = {
        **final_row,
        "close": 20002.5,
        "tick_volume": 21,
    }
    late_rewrite = {
        **rewritten_row,
        "close": 20002.75,
        "tick_volume": 22,
    }

    cache._ingest([open_row], observed_at=opened + timedelta(seconds=30))
    cache._ingest(
        [final_row],
        observed_at=opened + timedelta(minutes=1, milliseconds=100),
    )
    cache._ingest(
        [rewritten_row],
        observed_at=opened + timedelta(minutes=1, seconds=1),
    )
    cache._ingest(
        [rewritten_row],
        observed_at=opened + timedelta(minutes=1, seconds=2, milliseconds=1),
    )

    cache._ingest(
        [late_rewrite],
        observed_at=opened + timedelta(minutes=1, seconds=2, milliseconds=3),
    )
    receipts = cache.drain_reconciliation_receipts()
    assert any(item.result == "LATE_TICK_RECONCILED" for item in receipts)
    assert cache.closed_m1(through=opened + timedelta(minutes=1))[-1].close == 20002.8


def test_m1_true_contradiction_after_seal_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    opened = datetime(2026, 10, 5, 10, 24, tzinfo=UTC)
    monkeypatch.setattr(live, "normalise_fundednext_server_epoch", lambda _raw: opened)
    cache = Vt31Nas100M1Cache()
    original = {
        "time": 1,
        "open": 20000.0,
        "high": 20005.0,
        "low": 19998.0,
        "close": 20003.0,
        "tick_volume": 30,
        "real_volume": 0,
        "spread": 2,
    }
    contradiction = {
        **original,
        "high": 20004.0,
        "close": 20003.5,
        "tick_volume": 31,
    }
    cache._ingest(
        [original],
        observed_at=opened + timedelta(minutes=1, seconds=3),
    )
    with pytest.raises(Vt31Nas100LiveError, match="changed_fields.*high") as captured:
        cache._ingest(
            [contradiction],
            observed_at=opened + timedelta(minutes=1, seconds=4),
        )
    assert captured.value.receipt is not None
    assert captured.value.receipt.result == "TRUE_CONTRADICTION"
    assert captured.value.receipt.decision_state == "FAIL_CLOSED"
    assert captured.value.receipt.bar_open_time == opened
    assert captured.value.receipt.differences == (
        ("high", "20005.0", "20004.0", "-1.0"),
        ("close", "20003.0", "20003.5", "0.5"),
    )


def test_m1_precision_only_difference_normalizes_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    opened = datetime(2026, 10, 5, 9, 52, tzinfo=UTC)
    monkeypatch.setattr(live, "normalise_fundednext_server_epoch", lambda _raw: opened)
    cache = Vt31Nas100M1Cache(price_digits=1)
    row = {
        "time": 1,
        "open": 20000.0,
        "high": 20002.0,
        "low": 19999.0,
        "close": 20001.0,
        "tick_volume": 10,
        "real_volume": 0,
        "spread": 2,
    }
    precision_only = {**row, "close": 20001.04}
    cache._ingest([row], observed_at=opened + timedelta(minutes=1, seconds=3))
    cache.drain_reconciliation_receipts()
    cache._ingest(
        [precision_only],
        observed_at=opened + timedelta(minutes=1, seconds=4),
    )
    receipts = cache.drain_reconciliation_receipts()
    assert len(receipts) == 1
    assert receipts[0].result == "PRECISION_NORMALIZED"
    assert receipts[0].changed_fields == ("close_precision",)


def test_m1_duplicate_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    opened = datetime(2026, 10, 5, 9, 53, tzinfo=UTC)
    monkeypatch.setattr(live, "normalise_fundednext_server_epoch", lambda _raw: opened)
    cache = Vt31Nas100M1Cache()
    row = {
        "time": 1,
        "open": 20000.0,
        "high": 20002.0,
        "low": 19999.0,
        "close": 20001.0,
        "tick_volume": 10,
        "real_volume": 0,
        "spread": 2,
    }
    observed = opened + timedelta(minutes=1, seconds=3)
    cache._ingest([row], observed_at=observed)
    version = cache.cache_version
    cache.drain_reconciliation_receipts()
    cache._ingest([row], observed_at=observed + timedelta(seconds=1))
    assert cache.cache_version == version
    assert cache.drain_reconciliation_receipts() == ()


def test_m1_in_progress_revision_is_legitimate_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    opened = datetime(2026, 10, 5, 8, 56, tzinfo=UTC)
    monkeypatch.setattr(live, "normalise_fundednext_server_epoch", lambda _raw: opened)
    cache = Vt31Nas100M1Cache()
    first = {
        "time": 1,
        "open": 20000.0,
        "high": 20001.0,
        "low": 19999.0,
        "close": 20000.0,
        "tick_volume": 3,
        "real_volume": 0,
        "spread": 2,
    }
    second = {**first, "high": 20002.0, "close": 20001.0, "tick_volume": 4}
    cache._ingest([first], observed_at=opened + timedelta(seconds=10))
    cache.drain_reconciliation_receipts()
    cache._ingest([second], observed_at=opened + timedelta(seconds=20))
    receipt = cache.drain_reconciliation_receipts()[0]
    assert receipt.result == "LEGITIMATE_UPDATE"
    assert receipt.bar_state == "OPEN"
    assert receipt.decision_state == "WAIT"


def test_m1_restart_rebuilds_cache_without_artificial_contradiction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import vt31_nas100_live as live

    base = datetime(2026, 10, 5, 10, 20, tzinfo=UTC)
    monkeypatch.setattr(live, "MIN_PRELOAD_M1_BARS", 2)
    monkeypatch.setattr(live, "HISTORY_M1_BARS", 3)
    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: base + timedelta(minutes=raw),
    )
    rows = [
        {
            "time": index,
            "open": 20000.0 + index,
            "high": 20001.0 + index,
            "low": 19999.0 + index,
            "close": 20000.5 + index,
            "tick_volume": 10 + index,
            "real_volume": 0,
            "spread": 2,
        }
        for index in range(3)
    ]

    class Api:
        TIMEFRAME_M1 = 1

        def copy_rates_from_pos(
            self, _symbol: str, _timeframe: int, _start: int, _count: int
        ) -> list[dict[str, float | int]]:
            return rows

    now = base + timedelta(minutes=4)
    first = Vt31Nas100M1Cache(max_bars=3)
    first.preload(Api(), now=now)
    restarted = Vt31Nas100M1Cache(max_bars=3)
    restarted.preload(Api(), now=now)
    restarted.refresh_incremental(Api(), now=now + timedelta(seconds=1), count=3)
    assert restarted.drain_reconciliation_receipts() == ()
    assert restarted.closed_m1(through=now) == first.closed_m1(through=now)
