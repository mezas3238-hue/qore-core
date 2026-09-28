"""Burned/contract causal calibration for T06 profit-funded expansion.

This freezes only funding-source eligibility and lifecycle causality. It does
not calibrate an expansion multiplier or claim incremental economic benefit.
"""

from __future__ import annotations

import hashlib
import json

SOURCE_PHASE19_ARTIFACT_ID = 10972948493
SOURCE_PHASE19_ARTIFACT_SHA256 = (
    "e2fcf03ac78e278a22ec53f4f4d6b419ae4d9f5f7a9c674c23fd18c3a4e95527"
)

T06_PROFIT_FUNDED_RULES = (
    "ONLY_RECONCILED_REALIZED_PROFIT_IS_EXPANSION_FUNDING",
    "POSITIVE_FLOATING_PNL_IS_NOT_SPENDABLE_CAPITAL",
    "ORIGINAL_BASE_CAPITAL_IS_NOT_SELF_FINANCING_EXPANSION_SOURCE",
    "RESERVATION_PRECEDES_RISK_HANDOFF",
    "DUPLICATE_CAPITAL_SPEND_FORBIDDEN",
    "REJECTED_OR_UNUSED_RESERVATION_MUST_BE_RELEASED",
)


def burned_t06_source_calibration_payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.ce2i.burned_t06_source_calibration.v1",
        "source": {
            "phase19_artifact_id": SOURCE_PHASE19_ARTIFACT_ID,
            "phase19_artifact_sha256": SOURCE_PHASE19_ARTIFACT_SHA256,
            "phase20_contract_evidence": (
                "settlement-ledger-and-expansion-reservation-contracts"
            ),
            "evidence_status": "BURNED_PLUS_FAIL_CLOSED_CONTRACT",
        },
        "tool": "T06",
        "classification": "CALIBRATED_CAUSAL",
        "calibration_space": "REALIZED_CAPITAL_SOURCE_ELIGIBILITY",
        "rules": list(T06_PROFIT_FUNDED_RULES),
        "expansion_multiplier_calibrated": False,
        "incremental_economic_utility_calibrated": False,
        "governance": {
            "holdout_2017h1_used": False,
            "floating_pnl_as_cash": False,
            "historical_usd_execution_economics_claimed": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_t06_source_calibration_sha256() -> str:
    raw = json.dumps(
        burned_t06_source_calibration_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()
