from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r101_standard_cisd_wick_routing as r101,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r101_swing_survival_checks_only_after_signal() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(t0, open_="100", high="101", low="98", close="100.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="100.5",
            high="102",
            low="99.5",
            close="101.5",
        ),
        _bar(
            t0 + timedelta(minutes=30),
            open_="101.5",
            high="103",
            low="100",
            close="102.5",
        ),
    )
    assert r101._survives_remainder(
        inside,
        signal_at=t0 + timedelta(minutes=30),
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    )


def test_r101_next_h4_continuation_is_fail_closed_on_invalidation() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(t0, open_="101", high="102", low="98.5", close="101"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="101",
            high="103",
            low="100",
            close="102.5",
        ),
    )
    assert r101._next_h4_continuation(
        inside,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    ) is None


def test_r101_next_h4_continuation_uses_exact_break_close() -> None:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    inside = (
        _bar(t0, open_="101", high="102", low="100", close="101.5"),
        _bar(
            t0 + timedelta(minutes=15),
            open_="101.5",
            high="103",
            low="101",
            close="102.5",
        ),
    )
    result = r101._next_h4_continuation(
        inside,
        side=DemoTradingSetupSide.LONG,
        protected_swing=Decimal("99"),
    )
    assert result is not None
    assert result[0] == 1
    assert result[2] == Decimal("102.5")


def test_r101_routing_identity_is_frozen() -> None:
    assert r101.IDENTITY == (
        "VT08_INDEX_R101_STANDARD_CISD_WICK_ROUTING_DENSITY_001"
    )
