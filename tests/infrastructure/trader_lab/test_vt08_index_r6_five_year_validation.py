from __future__ import annotations

from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as mod
from qore.infrastructure.trader_lab import vt08_index_r6_governed_candidate_freeze as freeze


def test_five_year_window_and_density_contract_are_fixed() -> None:
    assert mod.START_DATE == date(2018, 9, 15)
    assert mod.END_DATE_EXCLUSIVE == date(2023, 9, 15)
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600


def test_five_year_replay_uses_exact_frozen_r6_candidate() -> None:
    assert freeze.CANDIDATE_ID == "VT08_INDEX_R6_GOVERNED_657_001"
    governor = mod._frozen_governor()
    assert governor.nas100_weight == Decimal("1.0")
    assert governor.sp500_weight == Decimal("0.75")
    assert governor.us30_weight == Decimal("1.0")
    assert governor.warn_dd_r == Decimal("2.5")
    assert governor.hard_dd_r == Decimal("3.5")
    assert governor.loss_streak_trigger == 3


def test_frozen_policy_map_contains_all_six_market_side_cells() -> None:
    policy_map = mod._frozen_policy_map()
    assert set(policy_map) == {
        "NAS100:long",
        "NAS100:short",
        "SP500:long",
        "SP500:short",
        "US30:long",
        "US30:short",
    }


def test_performance_contract_matches_frozen_r6_goal() -> None:
    assert mod.PRIMARY_PF_MIN == Decimal("1.50")
    assert mod.PRIMARY_DD_MAX == Decimal("6")
    assert mod.SECONDARY_PF_MIN == Decimal("1.30")
    assert mod.SECONDARY_DD_MAX == Decimal("8")
