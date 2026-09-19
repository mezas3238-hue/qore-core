from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)


def test_r58_binds_exact_r47_before_overlay() -> None:
    assert r58.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert r58._fingerprint_payload()["r42_r43_static_priors_inherited"] is False
    assert len(r58.RULE_FINGERPRINT) == 64


def test_r58_overlay_rules_remain_frozen() -> None:
    assert r58.RULES["signals_suppressed"] is False
    assert r58.RULES["calendar_or_year_runtime_feature"] is False
