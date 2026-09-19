from __future__ import annotations

from qore.infrastructure.trader_lab import vt08_index_r59_candidate_freeze as r59


def test_r59_freezes_exact_r58_identity() -> None:
    assert r59.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert r59.CANDIDATE_RULE_FINGERPRINT == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert r59.dependency_contract_matches() is True


def test_r59_preserves_non_operational_governance() -> None:
    assert r59.GOVERNANCE["candidate_frozen"] is True
    assert r59.GOVERNANCE["development_pass"] is True
    assert r59.GOVERNANCE["certified"] is False
    assert r59.GOVERNANCE["demo_eligible"] is False
    assert r59.GOVERNANCE["live_authorized"] is False
    assert r59.GOVERNANCE["real_capital_authorized"] is False
    assert r59.GOVERNANCE["production_authorized"] is False
