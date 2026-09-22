from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_stop_protection import (
    STOP_POLICIES,
    Bar,
    R1Trade,
    replay_trade,
)


def _trade(*, side: str = "long") -> R1Trade:
    opened = datetime(2025, 1, 2, 7, 0, tzinfo=UTC)
    if side == "long":
        entry = Decimal("100")
        stop = Decimal("90")
        target = Decimal("120")
    else:
        entry = Decimal("100")
        stop = Decimal("110")
        target = Decimal("80")
    return R1Trade(
        symbol="NAS100",
        signal_at=opened,
        baseline_exited_at=opened + timedelta(minutes=15),
        anchor_hour_ny=2,
        side=side,
        entry=entry,
        stop=stop,
        target=target,
        baseline_exit_price=stop,
        baseline_exit_reason="stop",
        baseline_r=Decimal("-1"),
    )


def _bars(
    rows: list[tuple[str, str, str]],
    *,
    start: datetime | None = None,
) -> dict[datetime, Bar]:
    cursor = start or datetime(2025, 1, 2, 7, 0, tzinfo=UTC)
    result: dict[datetime, Bar] = {}
    for high, low, close in rows:
        result[cursor] = Bar(
            opened_at=cursor,
            closed_at=cursor + timedelta(minutes=15),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        )
        cursor += timedelta(minutes=15)
    while len(result) < 16:
        result[cursor] = Bar(
            opened_at=cursor,
            closed_at=cursor + timedelta(minutes=15),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
        )
        cursor += timedelta(minutes=15)
    return result


def test_frozen_policies_match_preexisting_r316_contract() -> None:
    assert tuple(policy.name for policy in STOP_POLICIES) == (
        "off",
        "soft",
        "be050-lock050-at100",
        "aggressive",
    )
    assert STOP_POLICIES[1].ratchets == (
        (Decimal("0.75"), Decimal("-0.50")),
        (Decimal("1.25"), Decimal("0.00")),
        (Decimal("1.60"), Decimal("0.50")),
    )
    assert STOP_POLICIES[2].ratchets == (
        (Decimal("0.50"), Decimal("0.00")),
        (Decimal("1.00"), Decimal("0.50")),
    )
    assert STOP_POLICIES[3].ratchets == (
        (Decimal("0.50"), Decimal("0.00")),
        (Decimal("1.00"), Decimal("0.50")),
        (Decimal("1.50"), Decimal("1.00")),
    )


def test_active_stop_is_checked_before_same_bar_target() -> None:
    trade = _trade()
    bars = _bars([("121", "89", "110")])
    outcome = replay_trade(trade, bars, STOP_POLICIES[0])
    assert outcome.exit_reason == "stop"
    assert outcome.r_multiple == Decimal("-1")
    assert outcome.exit_price == Decimal("90")


def test_ratchet_observed_in_bar_protects_only_later_bar() -> None:
    trade = _trade()
    bars = _bars(
        [
            ("106", "95", "105"),
            ("106", "99", "100"),
        ]
    )
    outcome = replay_trade(trade, bars, STOP_POLICIES[2])
    assert outcome.exit_reason == "cibo_protected_stop"
    assert outcome.r_multiple == Decimal("0.00")
    assert outcome.exit_price == Decimal("100.00")


def test_aggressive_can_lock_one_r_on_later_bar_without_changing_target() -> None:
    trade = _trade()
    bars = _bars(
        [
            ("116", "95", "114"),
            ("115", "109", "110"),
        ]
    )
    outcome = replay_trade(trade, bars, STOP_POLICIES[3])
    assert outcome.exit_reason == "cibo_protected_stop"
    assert outcome.r_multiple == Decimal("1.00")
    assert outcome.exit_price == Decimal("110.00")


def test_short_side_uses_symmetric_stop_ratchet() -> None:
    trade = _trade(side="short")
    bars = _bars(
        [
            ("105", "94", "95"),
            ("101", "94", "100"),
        ]
    )
    outcome = replay_trade(trade, bars, STOP_POLICIES[2])
    assert outcome.exit_reason == "cibo_protected_stop"
    assert outcome.r_multiple == Decimal("0.00")
    assert outcome.exit_price == Decimal("100.00")
