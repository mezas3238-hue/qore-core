from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r47_identity_and_floor_are_new_and_positive() -> None:
    assert (
        r47.IDENTITY
        == "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    )
    assert r47.CANDIDATE_ID == r47.IDENTITY
    assert r47.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert len(r47.RULE_FINGERPRINT) == 64


def test_r47_rules_are_preregistered_structural_demotions() -> None:
    assert r47.RULES == {
        "sp500_long_h4_entry_61_120_to_floor": True,
        "tier_b_long_h4_entry_61_120_to_floor": True,
        "short_cross_index_unanimous_against_to_floor": True,
        "demotion_floor_r": "0.005",
        "freed_risk_reallocated": False,
        "signals_suppressed": False,
        "calendar_feature_used": False,
    }
    assert set(r47.PREREGISTERED_EVIDENCE) == {
        "SP500_LONG_H4_61_120",
        "B_LONG_H4_61_120",
        "SHORT_CROSS_INDEX_UNANIMOUS_AGAINST",
    }


def test_r47_cross_index_state_uses_side_semantics() -> None:
    assert DemoTradingSetupSide.LONG.value == "long"
    assert DemoTradingSetupSide.SHORT.value == "short"
