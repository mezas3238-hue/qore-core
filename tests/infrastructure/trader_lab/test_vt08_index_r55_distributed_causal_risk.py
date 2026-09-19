from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)


def test_r55_uses_existing_core_risk_ladder() -> None:
    assert r55.MAX_REQUESTED_WEIGHT == Decimal("0.25")
    assert r55.REARM_MIN_WEIGHT == Decimal("0.10")
    assert r55.SUPPORTED_FVG_MIN_WEIGHT == Decimal("0.25")
    assert r55.LATE_REVALIDATION_MIN_WEIGHT == Decimal("0.25")
    assert r55.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert r55.PORTFOLIO_BUDGET_R == Decimal("0.75")


def test_r55_governance_rules_preserve_surface() -> None:
    assert r55.RULES["preserve_r47_demotions"] is True
    assert r55.RULES["signals_suppressed"] is False
    assert r55.RULES["freed_risk_opportunistically_reallocated"] is False
    assert r55.RULES["calendar_or_year_runtime_feature"] is False


def test_r55_fingerprint_is_stable_shape() -> None:
    assert len(r55.RULE_FINGERPRINT) == 64
    assert r55.CANDIDATE_ID == (
        "VT08_INDEX_R55_DISTRIBUTED_CAUSAL_RISK_001"
    )
