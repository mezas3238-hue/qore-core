from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r61_independent_stability_audit as r61,
)


def test_r61_binds_exact_r58_specification() -> None:
    assert r61.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert r61.CANDIDATE_RULE_FINGERPRINT == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert r61.dependency_contract_matches() is True


def test_r61_material_stability_gate_is_fixed() -> None:
    assert r61.MATERIAL_COHORT_MIN_SAMPLE == 30
    assert r61.MATERIAL_COHORT_MIN_MEAN_WEIGHT == Decimal("0.05")
    assert r61.MATERIAL_COHORT_MIN_PF == Decimal("1.00")


def test_r61_pearson_is_descriptive_and_deterministic() -> None:
    correlation = r61._pearson(
        (1.0, 2.0, 3.0),
        (2.0, 4.0, 6.0),
    )
    assert correlation == 1.0


def test_r61_leakage_source_guard_is_clean() -> None:
    audit = r61._source_leakage_audit()
    assert audit["pass"] is True
    assert audit["findings"] == []
