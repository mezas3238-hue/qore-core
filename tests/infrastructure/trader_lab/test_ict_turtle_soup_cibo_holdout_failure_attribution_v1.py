from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_cibo_holdout_failure_attribution_v1 import (
    _enumerate_daily_targets,
    _failure_zone,
    _side,
    _stop_behavior,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
)


def _bar(at: datetime, o: str, h: str, l: str, c: str) -> Bar:
    return Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=5),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(l),
        close=Decimal(c),
    )


def _candle(day: int, o: str, h: str, l: str, c: str) -> SourceCandle:
    opened = datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day)
    return SourceCandle(
        opened_at=opened,
        closed_at=opened + timedelta(days=1),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(l),
        close=Decimal(c),
        m5=(),
    )


def test_side_accepts_r5_lowercase_values() -> None:
    assert _side("long") is Side.LONG
    assert _side("short") is Side.SHORT
    assert _side("LONG") is Side.LONG


def test_daily_target_enumeration_uses_nearest_untouched_swing() -> None:
    daily = (
        _candle(0, "1.00", "1.10", "0.90", "1.00"),
        _candle(1, "1.00", "1.30", "0.95", "1.10"),
        _candle(2, "1.10", "1.15", "1.00", "1.05"),
        _candle(3, "1.05", "1.40", "1.00", "1.20"),
        _candle(4, "1.20", "1.20", "1.05", "1.10"),
    )
    entry_at = daily[-1].closed_at
    candidates = _enumerate_daily_targets(
        daily,
        (),
        side=Side.LONG,
        entry=Decimal("1.00"),
        entry_at=entry_at,
    )
    assert [item.level for item in candidates] == [Decimal("1.30"), Decimal("1.40")]


def test_stop_behavior_detects_post_stop_target_recovery() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    evidence = Evidence(
        symbol="TEST",
        digits=2,
        bars=(
            _bar(start, "100", "100.4", "99.8", "100.1"),
            _bar(start + timedelta(minutes=5), "100.1", "100.2", "98.9", "99.0"),
            _bar(start + timedelta(minutes=10), "99.0", "100.5", "98.8", "100.2"),
            _bar(start + timedelta(minutes=15), "100.2", "102.2", "100.0", "102.0"),
        ),
    )
    assessment, metrics = _stop_behavior(
        trade={
            "exit_reason": "stop",
            "entry_at": start.isoformat(),
            "exit_at": (start + timedelta(minutes=10)).isoformat(),
        },
        evidence=evidence,
        daily_close=start + timedelta(hours=1),
        side=Side.LONG,
        entry=Decimal("100"),
        stop=Decimal("99"),
        target=Decimal("102"),
        risk=Decimal("1"),
        tick=Decimal("0.01"),
    )
    assert assessment == "POST_STOP_TARGET_REACHED"
    assert metrics["entry_recovered_after_stop"] is True
    assert metrics["target_reached_after_stop"] is True


def test_stop_behavior_supports_invalidation_when_entry_never_recovers() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    evidence = Evidence(
        symbol="TEST",
        digits=2,
        bars=(
            _bar(start, "100", "100.1", "99.2", "99.5"),
            _bar(start + timedelta(minutes=5), "99.5", "99.6", "98.8", "99.0"),
            _bar(start + timedelta(minutes=10), "99.0", "99.4", "98.0", "98.4"),
        ),
    )
    assessment, metrics = _stop_behavior(
        trade={
            "exit_reason": "stop",
            "entry_at": start.isoformat(),
            "exit_at": (start + timedelta(minutes=10)).isoformat(),
        },
        evidence=evidence,
        daily_close=start + timedelta(hours=1),
        side=Side.LONG,
        entry=Decimal("100"),
        stop=Decimal("99"),
        target=Decimal("102"),
        risk=Decimal("1"),
        tick=Decimal("0.01"),
    )
    assert assessment == "POST_STOP_NO_ENTRY_RECOVERY"
    assert metrics["entry_recovered_after_stop"] is False
    assert metrics["target_reached_after_stop"] is False


def test_failure_zone_prefers_stop_invalidation_when_price_recovers() -> None:
    zone, tier = _failure_zone(
        exit_reason="stop",
        gross_r=-1.0,
        d1_full=False,
        entry_contract_ok=True,
        stop_contract_ok=True,
        target_contract_ok=True,
        stop_behavior="POST_STOP_ENTRY_RECOVERED_ONLY",
    )
    assert zone == "STOP_INVALIDATION"
    assert tier == "E1_DIAGNOSTIC_TRAJECTORY"


def test_failure_zone_marks_entry_state_only_after_contracts_hold() -> None:
    zone, tier = _failure_zone(
        exit_reason="daily-c3-close",
        gross_r=-0.4,
        d1_full=False,
        entry_contract_ok=True,
        stop_contract_ok=True,
        target_contract_ok=True,
        stop_behavior="STOP_NOT_TESTED",
    )
    assert zone == "ENTRY_STATE"
    assert tier == "E1_ASSOCIATION"
