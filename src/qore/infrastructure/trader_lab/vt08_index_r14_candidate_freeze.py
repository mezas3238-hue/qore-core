"""Frozen VT08 Index R14 governed candidate.

This file freezes the only R14 scheme that passed the five-year development
contract. It is immutable evidence for subsequent no-retuning replays.

No live, real-capital or production authority is granted here.
"""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_r14_rolling_refinement as r14

CANDIDATE_ID = "VT08_INDEX_R14_ROLLING_1574_001"
SOURCE_RUN_ID = 35356898995
SOURCE_ARTIFACT_ID = 10552381706
SOURCE_ARTIFACT_DIGEST = (
    "sha256:d40a5bdae7b5c89a54ab9c9f6fc1275f629df5b6e7234d53c0d7b6f84816f8c3"
)
SOURCE_HEAD_SHA = "fe786be932e6998a475b9860cc8ac3b9e64d5daa"

FIVE_YEAR_SAMPLE = 1574
FIVE_YEAR_PRIMARY_PF = "1.522470915576582435504401155"
FIVE_YEAR_PRIMARY_DD_R = "5.396620098039215686274509804"
FIVE_YEAR_PRIMARY_TOTAL_R = "72.05431950566482647157373413"
FIVE_YEAR_SECONDARY_PF = "1.316158221647938784106714952"
FIVE_YEAR_SECONDARY_DD_R = "7.201995098039215686274509804"
FIVE_YEAR_SECONDARY_TOTAL_R = "40.61231950566482647157373413"
FIVE_YEAR_POSITIVE_YEAR_BUCKETS = 5

TARGET_R = "2.5"
SCHEME = {
    "aligned_weight": "0.25",
    "rolling_trades": 60,
    "c2_cap": "0.50",
    "short_cap": "0.50",
    "warn_dd_r": "1.75",
    "warn_multiplier": "0.15",
    "hard_dd_r": "2.50",
    "hard_multiplier": "0.10",
    "loss_trigger": 2,
    "loss_multiplier": "0.20",
    "minimum_effective_weight": "0.005",
}
SCHEME_ID = "R14-A0.25-D1.75x0.15-H2.50x0.10-L2x0.20"


def frozen_refined_scheme() -> r14.RefinedScheme:
    return r14.RefinedScheme(
        aligned_weight=r14.Decimal(SCHEME["aligned_weight"]),
        warn_dd_r=r14.Decimal(SCHEME["warn_dd_r"]),
        warn_multiplier=r14.Decimal(SCHEME["warn_multiplier"]),
        hard_dd_r=r14.Decimal(SCHEME["hard_dd_r"]),
        hard_multiplier=r14.Decimal(SCHEME["hard_multiplier"]),
        loss_multiplier=r14.Decimal(SCHEME["loss_multiplier"]),
    )


def _fingerprint_payload() -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_head_sha": SOURCE_HEAD_SHA,
        "target_r": TARGET_R,
        "scheme_id": SCHEME_ID,
        "scheme": SCHEME,
        "five_year_sample": FIVE_YEAR_SAMPLE,
        "five_year_primary_pf": FIVE_YEAR_PRIMARY_PF,
        "five_year_primary_dd_r": FIVE_YEAR_PRIMARY_DD_R,
        "five_year_secondary_pf": FIVE_YEAR_SECONDARY_PF,
        "five_year_secondary_dd_r": FIVE_YEAR_SECONDARY_DD_R,
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
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}
