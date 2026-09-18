from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    cibo_xauusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_cognitive_memory_v2 as v2,
)


def _row(*, target: bool, protect_target: bool | None = None) -> dict[str, object]:
    protect_target = target if protect_target is None else protect_target
    return {
        "strategy_entry_at": "2020-01-02T00:00:00+00:00",
        "STATIC_target_reached": target,
        "STATIC_protected_exit": False,
        "STATIC_stop_exit": not target,
        "LET_RUN_target_reached": target,
        "LET_RUN_protected_exit": False,
        "LET_RUN_stop_exit": not target,
        "PROTECT_target_reached": protect_target,
        "PROTECT_protected_exit": not protect_target,
        "PROTECT_stop_exit": False,
        "STATIC_net_010_r": "-999",
        "PROTECT_net_010_r": "999",
    }


def test_ratio_state_is_fixed_and_not_learned_from_pnl() -> None:
    assert v2._ratio_state(Decimal("0.70")) == "compressed"
    assert v2._ratio_state(Decimal("1.00")) == "balanced"
    assert v2._ratio_state(Decimal("1.50")) == "expanded"
    assert v2._ratio_state(Decimal("2.50")) == "extreme"


def test_management_requires_structural_non_inferiority() -> None:
    rows = [_row(target=True, protect_target=False) for _ in range(10)]
    posture, _ = v2._structural_posture(rows)
    assert posture in {native.POSTURE_STATIC, native.POSTURE_LET_RUN}
    assert posture != native.POSTURE_PROTECT


def test_target_profile_ignores_economic_labels() -> None:
    rows = []
    for quarter in range(8):
        year = 2020 + quarter // 4
        month = 1 + (quarter % 4) * 3
        for _ in range(3):
            row = _row(target=True)
            row["strategy_entry_at"] = f"{year}-{month:02d}-02T00:00:00+00:00"
            row["STATIC_net_010_r"] = "-1000000"
            row["PROTECT_net_010_r"] = "1000000"
            rows.append(row)
    profile = v2._target_profile(rows)
    assert profile["structurally_supported"] is True
    assert profile["decision_uses_economic_fields"] is False
    assert Decimal(str(profile["static_protected_swing_reach_rate"])) == Decimal("1")


def test_context_only_level_cannot_authorize() -> None:
    hierarchy = {
        "exact_regime": {"signatures": {}},
        "causal_core_regime": {"signatures": {}},
        "anatomy_regime": {"signatures": {}},
        "regime_journey": {
            "signatures": {
                "H1|balanced|balanced|balanced|medium": {
                    "decision_authority": "CONTEXT_ONLY",
                    "targets": {
                        "1|ROUTE": {
                            "structurally_supported": True,
                        }
                    },
                }
            }
        },
    }
    row = {
        "timeframe": "H1",
        "side": "long",
        "session": "london",
        "prior_body_alignment": "opposed",
        "fvg_before_entry": "yes",
        "exact_equal_liquidity": "no",
        "raid_depth_range_bucket": "q1",
        "reclaim_latency_bucket": "<=5m",
        "cisd_progress_bucket": "q1",
        "protected_risk_range_bucket": "q1",
        "source_range_state_bucket": "q1",
        "body_fraction_bucket": "q1",
        "rejection_wick_bucket": "q1",
        "close_location_bucket": "q1",
        "h1_range_state": "balanced",
        "h4_range_state": "balanced",
        "d1_range_state": "balanced",
        "h1_body_alignment": "with",
        "h4_body_alignment": "with",
        "d1_body_alignment": "with",
        "m5_volatility_state": "balanced",
        "m5_efficiency_state": "medium",
        "m5_displacement_alignment": "with",
        "target_rank": 1,
        "target_route": "ROUTE",
    }
    profile, level, signature = v2.resolve_authoritative(hierarchy, row)
    assert profile is None
    assert level is None
    assert signature is None
