"""Frozen VT08 Index R28 formation-health candidate.

This module freezes the exact R28 development winner after the bounded R23-R28
research chain. It grants no live, demo, production, or real-capital authority.

The five-year source window is consumed development evidence. The frozen
identity exists solely so subsequent 2Y reproduction, walk-forward, Monte
Carlo, and friction validation cannot retune the candidate.
"""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24
from qore.infrastructure.trader_lab import vt08_index_r26_formation_health_governor as r26

CANDIDATE_ID = "VT08_INDEX_R28_FORMATION_HEALTH_1574_001"

SOURCE_RUN_ID = 35403911978
SOURCE_ARTIFACT_ID = 10571751021
SOURCE_ARTIFACT_DIGEST = (
    "sha256:779413592cc54566e6d0d4a12ac2501befe99cb677e603e0d3ad396f3b447026"
)
SOURCE_HEAD_SHA = "57f9d096c3d08e0577f00f7f0f5d0fbeb6e0da3e"

FIVE_YEAR_SAMPLE = 1574
FIVE_YEAR_PRIMARY_PF = "1.873627899552740623154926384"
FIVE_YEAR_PRIMARY_REALIZED_DD_R = "2.49375000000000000000000000"
FIVE_YEAR_PRIMARY_MTM_DD_R = "2.689275087260034904013961606"
FIVE_YEAR_PRIMARY_TOTAL_R = "22.40203964931762719933109964"
FIVE_YEAR_SECONDARY_PF = "1.751968537407924721083268851"
FIVE_YEAR_SECONDARY_REALIZED_DD_R = "2.64625000000000000000000000"
FIVE_YEAR_SECONDARY_MTM_DD_R = "2.874400087260034904013961606"
FIVE_YEAR_SECONDARY_TOTAL_R = "20.20053799368848812648341752"
FIVE_YEAR_POSITIVE_CALENDAR_BUCKETS = 6
FIVE_YEAR_CALENDAR_BUCKET_COUNT = 6
TARGET_R = "2.5"

FORMATION_HEALTH: dict[str, str | int] = {
    "rolling_tier_trades": 6,
    "min_observations": 5,
    "cold_multiplier": "0.005",
    "weak_multiplier": "0.05",
    "healthy_mean_threshold_r": "0.00",
}
FORMATION_HEALTH_PROFILE_ID = "FH-W6-N5-C0.005-WEAK0.05-T0.00"

QUALITY: dict[str, str] = {
    "base_weight": "0.005",
    "tier_a_weight": "1.50",
    "tier_b_weight": "0.75",
    "tier_c_weight": "0.10",
}
GLOBAL_RISK: dict[str, str | int] = {
    "rolling_trades": 60,
    "warn_dd_r": "1.25",
    "warn_multiplier": "0.05",
    "hard_dd_r": "1.50",
    "hard_multiplier": "0.025",
    "loss_trigger": 2,
    "loss_multiplier": "0.05",
    "portfolio_risk_budget_r": "0.75",
    "minimum_effective_weight": "0.005",
}


def frozen_formation_health_profile() -> r26.FormationHealthProfile:
    return r26.FormationHealthProfile(
        rolling_tier_trades=int(FORMATION_HEALTH["rolling_tier_trades"]),
        min_observations=int(FORMATION_HEALTH["min_observations"]),
        cold_multiplier=Decimal(str(FORMATION_HEALTH["cold_multiplier"])),
        weak_multiplier=Decimal(str(FORMATION_HEALTH["weak_multiplier"])),
        healthy_mean_threshold_r=Decimal(
            str(FORMATION_HEALTH["healthy_mean_threshold_r"])
        ),
    )


def dependency_contract_matches() -> bool:
    quality = r24.BASE_QUALITY
    risk = r24.BASE_RISK
    return (
        str(quality.base_weight) == QUALITY["base_weight"]
        and str(quality.tier_a_weight) == QUALITY["tier_a_weight"]
        and str(quality.tier_b_weight) == QUALITY["tier_b_weight"]
        and str(quality.tier_c_weight) == QUALITY["tier_c_weight"]
        and risk.rolling_trades == GLOBAL_RISK["rolling_trades"]
        and str(risk.warn_dd_r) == GLOBAL_RISK["warn_dd_r"]
        and str(risk.warn_multiplier) == GLOBAL_RISK["warn_multiplier"]
        and str(risk.hard_dd_r) == GLOBAL_RISK["hard_dd_r"]
        and str(risk.hard_multiplier) == GLOBAL_RISK["hard_multiplier"]
        and str(risk.loss_multiplier) == GLOBAL_RISK["loss_multiplier"]
        and str(risk.portfolio_risk_budget_r)
        == GLOBAL_RISK["portfolio_risk_budget_r"]
    )


def _fingerprint_payload() -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_head_sha": SOURCE_HEAD_SHA,
        "target_r": TARGET_R,
        "formation_health_profile_id": FORMATION_HEALTH_PROFILE_ID,
        "formation_health": FORMATION_HEALTH,
        "quality": QUALITY,
        "global_risk": GLOBAL_RISK,
        "five_year_sample": FIVE_YEAR_SAMPLE,
        "five_year_primary_pf": FIVE_YEAR_PRIMARY_PF,
        "five_year_primary_mtm_dd_r": FIVE_YEAR_PRIMARY_MTM_DD_R,
        "five_year_secondary_pf": FIVE_YEAR_SECONDARY_PF,
        "five_year_secondary_mtm_dd_r": FIVE_YEAR_SECONDARY_MTM_DD_R,
        "five_year_positive_calendar_buckets": FIVE_YEAR_POSITIVE_CALENDAR_BUCKETS,
    }


RULE_FINGERPRINT = sha256(
    json.dumps(
        _fingerprint_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()

GOVERNANCE = {
    "candidate_frozen": True,
    "five_year_window_consumed": True,
    "fresh_holdout_claim": False,
    "all_trades_preserved": True,
    "cross_market_concurrency_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}
