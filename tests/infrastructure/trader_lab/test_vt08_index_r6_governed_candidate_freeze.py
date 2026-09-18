from qore.infrastructure.trader_lab import (
    vt08_index_r6_governed_candidate_freeze as mod,
)


def test_r6_candidate_freeze_preserves_657_and_authority_boundaries() -> None:
    assert mod.CANDIDATE_ID == "VT08_INDEX_R6_GOVERNED_657_001"
    assert mod.FIXED_DENSITY == 657
    assert mod.MANAGEMENT_ID == "R6M-1e7063aea1b32ee0"
    assert mod.GOVERNOR_ID == "R6G-2acd920c5653c9a1"
    assert len(mod.RULE_FINGERPRINT) == 64
    assert mod.GOVERNANCE["fresh_holdout_opened"] is False
    assert mod.GOVERNANCE["live_authorized"] is False
    assert mod.GOVERNANCE["real_capital_authorized"] is False
    assert mod.GOVERNANCE["production_authorized"] is False


def test_r6_candidate_freeze_keeps_all_three_markets_active() -> None:
    weights = mod.RISK_GOVERNOR["market_weights"]
    assert weights == {"NAS100": "1.0", "SP500": "0.75", "US30": "1.0"}
    assert all(float(value) > 0 for value in weights.values())
