from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import (
    ClosurePolicy,
    SwingPolicy,
    TargetPolicy,
    _closure,
    _select_swing,
    variants,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    Vt08IndexC2R1ProtectedSwing,
)


def _bar(hour: int, open_: str, high: str, low: str, close: str) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, 2, hour, tzinfo=UTC)
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _expand_h4(
    start: datetime, values: tuple[str, str, str, str]
) -> dict[datetime, Vt08IndexC2R1Bar]:
    open_, high, low, close = map(Decimal, values)
    rows = {}
    for index in range(16):
        opened = start + timedelta(minutes=15 * index)
        row_open = open_ if index == 0 else open_
        row_close = close if index == 15 else open_
        row_high = max(row_open, row_close, high if index == 7 else row_open)
        row_low = min(row_open, row_close, low if index == 8 else row_open)
        rows[opened] = Vt08IndexC2R1Bar(
            opened_at=opened,
            closed_at=opened + timedelta(minutes=15),
            open=row_open,
            high=row_high,
            low=row_low,
            close=row_close,
        )
    return rows


def test_frozen_grid_has_512_unique_variants() -> None:
    grid = variants()
    assert len(grid) == 512
    assert len({item.variant_id for item in grid}) == 512


def test_completed_c2_math_is_directional() -> None:
    decision = datetime(2026, 1, 2, 10, tzinfo=UTC)
    indexed = {}
    indexed.update(_expand_h4(decision - timedelta(hours=8), ("100", "101", "99", "100")))
    indexed.update(_expand_h4(decision - timedelta(hours=4), ("100", "100.5", "98", "99.5")))
    resolved = _closure(
        policy=ClosurePolicy.C2_ONLY,
        bars_by_open=indexed,
        decision_at=decision,
        side=DemoTradingSetupSide.LONG,
    )
    assert resolved is not None
    assert resolved[2] == "c2"


def test_unique_swing_fails_closed_and_explicit_policies_resolve() -> None:
    first = Vt08IndexC2R1ProtectedSwing(
        DemoTradingSetupSide.LONG,
        Decimal("99"),
        Decimal("100"),
        datetime(2026, 1, 2, 2, 30, tzinfo=UTC),
        datetime(2026, 1, 2, 2, tzinfo=UTC),
    )
    last = Vt08IndexC2R1ProtectedSwing(
        DemoTradingSetupSide.LONG,
        Decimal("98"),
        Decimal("99"),
        datetime(2026, 1, 2, 3, 30, tzinfo=UTC),
        datetime(2026, 1, 2, 3, tzinfo=UTC),
    )
    assert (
        _select_swing((first, last), policy=SwingPolicy.UNIQUE_ONLY, side=DemoTradingSetupSide.LONG)
        is None
    )
    assert (
        _select_swing(
            (first, last), policy=SwingPolicy.FIRST_CAUSAL, side=DemoTradingSetupSide.LONG
        )
        is first
    )
    assert (
        _select_swing(
            (first, last), policy=SwingPolicy.LATEST_CAUSAL, side=DemoTradingSetupSide.LONG
        )
        is last
    )
    assert (
        _select_swing(
            (first, last), policy=SwingPolicy.FARTHEST_STRUCTURAL, side=DemoTradingSetupSide.LONG
        )
        is last
    )


def test_target_multiples_are_frozen() -> None:
    assert tuple(item.multiple for item in TargetPolicy) == (
        Decimal("1.5"),
        Decimal("2"),
        Decimal("2.5"),
        Decimal("3"),
    )
