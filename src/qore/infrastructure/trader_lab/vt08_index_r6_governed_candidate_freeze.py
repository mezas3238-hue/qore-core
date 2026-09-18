"""Frozen research contract for VT08 Index R6 governed 657 candidate.

This module freezes a consumed-tuning candidate only. It is not a certification,
promotion, live authorization, or real-capital authorization.
"""

from __future__ import annotations

import json
from hashlib import sha256

CANDIDATE_ID = "VT08_INDEX_R6_GOVERNED_657_001"
SOURCE_RUN_ID = 35334226488
SOURCE_ARTIFACT_ID = 10542845347
SOURCE_ARTIFACT_DIGEST = (
    "sha256:a593340cb76f6a1923620e0a19f132fa3d7731c361f1c346d6c2f2a4b212e207"
)
FIXED_DENSITY = 657
MANAGEMENT_ID = "R6M-1e7063aea1b32ee0"
GOVERNOR_ID = "R6G-2acd920c5653c9a1"

MANAGEMENT_BY_CELL = {
    "NAS100:long": {
        "policy_id": "R5-0762cd2643708e01",
        "target_r": "3.0",
        "soft_close_loss_r": None,
        "soft_close_until_mfe_r": None,
        "deadline_bars": 4,
        "deadline_min_mfe_r": "0.25",
        "trail": "OFF",
    },
    "NAS100:short": {
        "policy_id": "R5-82307432b94c9588",
        "target_r": "3.0",
        "soft_close_loss_r": "0.75",
        "soft_close_until_mfe_r": "1.0",
        "deadline_bars": 12,
        "deadline_min_mfe_r": "0.5",
        "trail": "LOCK025_AT_075",
    },
    "SP500:long": {
        "policy_id": "R5-8b3c6d2c93054eda",
        "target_r": "3.0",
        "soft_close_loss_r": "0.25",
        "soft_close_until_mfe_r": "0.5",
        "deadline_bars": 4,
        "deadline_min_mfe_r": "0.25",
        "trail": "OFF",
    },
    "SP500:short": {
        "policy_id": "R5-2c883c4abdd1cee1",
        "target_r": "3.0",
        "soft_close_loss_r": "0.75",
        "soft_close_until_mfe_r": "1.0",
        "deadline_bars": 4,
        "deadline_min_mfe_r": "0.5",
        "trail": "STAIR_B",
    },
    "US30:long": {
        "policy_id": "R5-112844aa9effb856",
        "target_r": "3.0",
        "soft_close_loss_r": "0.5",
        "soft_close_until_mfe_r": "0.5",
        "deadline_bars": 8,
        "deadline_min_mfe_r": "0.25",
        "trail": "BE050",
    },
    "US30:short": {
        "policy_id": "R5-48e7c15a956154d1",
        "target_r": "2.0",
        "soft_close_loss_r": "0.25",
        "soft_close_until_mfe_r": "1.0",
        "deadline_bars": None,
        "deadline_min_mfe_r": None,
        "trail": "STAIR_C",
    },
}

RISK_GOVERNOR = {
    "market_weights": {"NAS100": "1.0", "SP500": "0.75", "US30": "1.0"},
    "warn_dd_r": "2.5",
    "warn_multiplier": "0.5",
    "hard_dd_r": "3.5",
    "hard_multiplier": "0.10",
    "loss_streak_trigger": 3,
    "loss_streak_multiplier": "0.25",
    "zero_weight_allowed": False,
}

CONSUMED_TUNING_METRICS = {
    "raw_primary": {
        "sample": 657,
        "profit_factor": "1.409261761571496598162018752",
        "max_drawdown_r": "17.93577008091801781387211686",
        "total_r": "111.5435151373628925268177781",
    },
    "governed_primary_minus_0_05r": {
        "sample": 657,
        "profit_factor": "1.798064231484883010036925017",
        "max_drawdown_r": "5.04851671104509791287774421",
        "total_r": "51.13005573192093812003536937",
    },
    "governed_secondary_minus_0_10r": {
        "sample": 657,
        "profit_factor": "1.503745301369286495235203289",
        "max_drawdown_r": "5.25946429169025920320032485",
        "total_r": "32.54448265678566688676514132",
    },
}

GOVERNANCE = {
    "research_only": True,
    "consumed_tuning_window": "2016-09-18..2018-09-15",
    "fresh_holdout_opened": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}

_FINGERPRINT_MATERIAL = {
    "candidate_id": CANDIDATE_ID,
    "fixed_density": FIXED_DENSITY,
    "management_id": MANAGEMENT_ID,
    "management_by_cell": MANAGEMENT_BY_CELL,
    "governor_id": GOVERNOR_ID,
    "risk_governor": RISK_GOVERNOR,
}
RULE_FINGERPRINT = sha256(
    json.dumps(
        _FINGERPRINT_MATERIAL,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()
