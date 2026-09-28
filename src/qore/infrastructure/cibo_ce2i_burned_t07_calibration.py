"""Burned/contract causal calibration for T07 protected-capacity expansion.

This freezes only causal eligibility and lifecycle rules for capacity that is
already proven by a reconciled protected economic floor. It does not calibrate
the historical USD value of that floor, provider execution economics, an
expansion multiplier, or incremental economic utility.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SOURCE_PHASE19_ARTIFACT_ID = 10972948493
SOURCE_PHASE19_ARTIFACT_SHA256 = (
    "e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)

T07_PROTECTED_CAPACITY_RULES = (
    "PROTECTED_CAPACITY_REQUIRES_RECONCILED_POSITION_AND_PROTECTION",
    "POSITIVE_FLOATING_PNL_ALONE_IS_NOT_PROTECTED_CAPACITY",
    "BASE_MUST_BE_RECOVERED_AT_RECONCILED_WORST_CASE_FLOOR",
    "FUTURE_COST_AND_SLIPPAGE_RESERVES_DEDUCT_BEFORE_CAPACITY",
    "RESERVATION_PRECEDES_RISK_HANDOFF",
    "DUPLICATE_CAPITAL_SPEND_FORBIDDEN",
    "DEPLOYED_PROTECTED_CAPACITY_MUST_SETTLE_BEFORE_REUSE",
)


def burned_t07_source_calibration_payload() -> dict[str, Any]:
    return {
        "schema": "qore.cibo.ce2i.burned_t07_source_calibration.v1",
        "source": {
            "phase19_artifact_id": SOURCE_PHASE19_ARTIFACT_ID,
            "phase19_artifact_sha256": SOURCE_PHASE19_ARTIFACT_SHA256,
            "phase20_contract_evidence": (
                "economic-floor-reconciliation-and-capital-ledger-contracts"
            ),
            "evidence_status": "BURNED_NORMALIZED_PLUS_FAIL_CLOSED_CONTRACT",
        },
        "tool": "T07",
        "classification": "CALIBRATED_CAUSAL",
        "calibration_space": (
            "PROTECTED_CAPACITY_SOURCE_ELIGIBILITY_AND_LIFECYCLE"
        ),
        "protected_economic_floor_amount_calibrated": False,
        "expansion_multiplier_calibrated": False,
        "incremental_economic_utility_calibrated": False,
        "governance": {
            "provider_economics_required": True,
            "holdout_2017h1_used": False,
            "floating_pnl_as_cash": False,
            "historical_2017_usd_floor_claimed": False,
            "historical_usd_execution_economics_claimed": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_t07_source_calibration_sha256() -> str:
    raw = json.dumps(
        burned_t07_source_calibration_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()
