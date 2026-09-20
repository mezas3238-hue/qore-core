from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r83_ps_qualification_r58_transport as r83,
)


def test_r83_qualified_union_is_source_defined_not_pnl_selected() -> None:
    assert r83.QUALIFIED_FAMILIES == (
        r82.FAMILY_LIQUIDITY,
        r82.FAMILY_FVG,
        r82.FAMILY_BOTH,
    )
    assert r82.FAMILY_UNQUALIFIED not in r83.QUALIFIED_FAMILIES


def test_r83_empty_weight_stats_are_deterministic() -> None:
    assert r83._weight_stats((), ()) == {
        "sample": 0,
        "base_total_weight": "0",
        "base_mean_weight": "0",
        "r58_total_weight": "0",
        "r58_mean_weight": "0",
        "r58_minus_r47_total_weight": "0",
        "risk_increase_count": 0,
        "risk_decrease_count": 0,
        "risk_unchanged_count": 0,
        "floor_weight_count": 0,
        "cap_weight_count": 0,
    }


def test_r83_source_r82_evidence_is_pinned() -> None:
    assert r83.SOURCE_R82_RUN_ID == 35519594414
    assert r83.SOURCE_R82_ARTIFACT_ID == 10607673530
    assert r83.SOURCE_R82_ARTIFACT_DIGEST.startswith("sha256:")


def test_r83_stress_contract_matches_frozen_economic_tests() -> None:
    assert str(r83.PRIMARY_STRESS) == "0.05"
    assert str(r83.SECONDARY_STRESS) == "0.10"
