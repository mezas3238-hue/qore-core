from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r14_recent_2y_replay as mod


def test_r14_recent_2y_window_and_stress_contract() -> None:
    assert mod.START_DATE == date(2024, 9, 15)
    assert mod.END_DATE_EXCLUSIVE == date(2026, 9, 15)
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
    assert mod.REFERENCE_DENSITY_MIN == 600
    assert mod.REFERENCE_DENSITY_MAX == 700


def test_r14_recent_2y_is_no_retuning_reproduction() -> None:
    assert mod.freeze.CANDIDATE_ID == "VT08_INDEX_R14_ROLLING_1574_001"
    assert mod.freeze.TARGET_R == "2.5"
