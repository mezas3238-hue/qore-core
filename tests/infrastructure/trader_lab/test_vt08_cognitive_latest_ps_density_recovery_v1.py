from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    PROFILES,
    SELECTOR_ID,
    latest_confirmed_swing,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01ProtectedSwing


def _swing(minute: int, price: str) -> Vt08B01ProtectedSwing:
    return Vt08B01ProtectedSwing(
        side=DemoTradingSetupSide.LONG,
        price=Decimal(price),
        cisd_level=Decimal("100"),
        confirmed_at=datetime(2026, 1, 1, 0, minute, tzinfo=UTC),
        opposing_series_opened_at=datetime(
            2026, 1, 1, 0, minute - 1, tzinfo=UTC
        ),
    )


def test_latest_confirmed_selector_is_time_based_not_pnl_based() -> None:
    early = _swing(10, "99")
    late = _swing(20, "98")
    assert latest_confirmed_swing((early, late)) is late
    assert latest_confirmed_swing((late, early)) is late


def test_profiles_remain_independent() -> None:
    assert SELECTOR_ID == "LATEST_CONFIRMED_PROTECTED_SWING_V1"
    assert PROFILES == ("M15_STANDARD", "M5_FRACTAL", "M3_FRACTAL")
