from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r29_candidate_freeze as freeze


def test_r29_freezes_exact_r28_winner() -> None:
    profile = freeze.frozen_formation_health_profile()
    assert freeze.CANDIDATE_ID == "VT08_INDEX_R28_FORMATION_HEALTH_1574_001"
    assert profile.rolling_tier_trades == 6
    assert profile.min_observations == 5
    assert profile.cold_multiplier == Decimal("0.005")
    assert profile.weak_multiplier == Decimal("0.05")
    assert profile.healthy_mean_threshold_r == Decimal("0.00")


def test_r29_dependency_contract_has_not_drifted() -> None:
    assert freeze.dependency_contract_matches() is True


def test_r29_freeze_has_no_operational_authority() -> None:
    assert freeze.GOVERNANCE["candidate_frozen"] is True
    assert freeze.GOVERNANCE["fresh_holdout_claim"] is False
    assert freeze.GOVERNANCE["demo_eligible"] is False
    assert freeze.GOVERNANCE["live_authorized"] is False
    assert freeze.GOVERNANCE["real_capital_authorized"] is False
    assert freeze.GOVERNANCE["production_authorized"] is False
    assert len(freeze.RULE_FINGERPRINT) == 64
