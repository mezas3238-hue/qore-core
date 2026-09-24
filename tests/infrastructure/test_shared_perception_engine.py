from decimal import Decimal

from qore.infrastructure.core_stack_v2.perception_engine import (
    PerceptionBar,
    infer_situation,
    perceive_market,
)


def _bar(i: int, opened: str, closed: str, high: str, low: str, close: str) -> PerceptionBar:
    return PerceptionBar(
        opened_at=f"2026-01-01T{opened}",
        closed_at=f"2026-01-01T{closed}",
        open=Decimal(str(i)),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_perception_is_fail_closed_to_future_bars() -> None:
    bars = [
        _bar(100, "10:00:00", "10:01:00", "101", "99", "100.8"),
        _bar(101, "10:01:00", "10:02:00", "102", "100", "101.8"),
        _bar(102, "10:02:00", "10:03:00", "103", "101", "102.8"),
        _bar(103, "10:03:00", "10:04:00", "104", "102", "103.8"),
        _bar(104, "10:04:00", "10:05:00", "105", "103", "104.8"),
        _bar(105, "10:05:00", "10:06:00", "999", "1", "500"),
    ]
    as_of = "2026-01-01T10:05:00"
    with_future = perceive_market(bars, as_of=as_of)
    without_future = perceive_market(bars[:-1], as_of=as_of)
    assert with_future == without_future


def test_perception_has_no_outcome_or_authority_fields() -> None:
    bars = [
        _bar(100 + i, f"10:0{i}:00", f"10:0{i + 1}:00", str(102 + i), str(99 + i), str(101.8 + i))
        for i in range(5)
    ]
    perception = perceive_market(bars, as_of="2026-01-01T10:05:00")
    situation = infer_situation(perception)
    forbidden = {
        "pnl", "profit", "loss", "winner", "loser", "order",
        "risk_authority", "execution_authority", "target_result",
    }
    assert not forbidden.intersection(perception.__dataclass_fields__)
    assert not forbidden.intersection(situation.__dataclass_fields__)


def test_directional_expansion_is_perceived_from_present_market() -> None:
    bars = []
    price = Decimal("100")
    for i in range(20):
        width = Decimal("0.2") if i < 15 else Decimal("1.2")
        opened = price
        close = opened + width * Decimal("0.8")
        bars.append(
            PerceptionBar(
                opened_at=f"2026-01-01T10:{i:02d}:00",
                closed_at=f"2026-01-01T10:{i + 1:02d}:00",
                open=opened,
                high=opened + width,
                low=opened - width * Decimal("0.05"),
                close=close,
            )
        )
        price = close
    perception = perceive_market(bars, as_of="2026-01-01T10:20:00")
    situation = infer_situation(perception)
    assert perception.volatility_state == "EXPANDING"
    assert "RANGE_EXPANSION" in perception.anomaly_flags
    assert situation.regime == "TREND_EXPANSION"


def test_fingerprint_is_deterministic() -> None:
    bars = [
        _bar(100, "10:00:00", "10:01:00", "101", "99", "100.8"),
        _bar(101, "10:01:00", "10:02:00", "102", "100", "101.8"),
    ]
    one = perceive_market(bars, as_of="2026-01-01T10:02:00")
    two = perceive_market(tuple(reversed(bars)), as_of="2026-01-01T10:02:00")
    assert one.fingerprint == two.fingerprint
