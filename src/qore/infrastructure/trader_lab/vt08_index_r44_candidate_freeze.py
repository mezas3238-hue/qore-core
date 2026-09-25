"""Frozen VT08 Index R43 source-complete candidate.

R43 is the first source-complete 2,448-trade identity to satisfy the Owner's
exact five-year development contract under both -0.05R and -0.10R friction
surfaces. This module freezes that exact identity before any recent-2Y replay.

No parameter may be retuned from the 2Y reproduction. This freeze grants no
LIVE, real-capital, demo, deployment, or production authority.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r29_candidate_freeze as r29,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r42_hierarchical_nas100_prior as r42,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r43_sp500_long_stability_prior as r43,
)

SCHEMA = "qore.trader_lab.vt08_index_r44_candidate_freeze.v1"
CANDIDATE_ID = "VT08_INDEX_R43_SOURCE_COMPLETE_2448_001"

SOURCE_RUN_ID = 35418460354
SOURCE_ARTIFACT_ID = 10576224564
SOURCE_ARTIFACT_DIGEST = (
    "sha256:8a517c5d4af176db54634d1ea4779607afaa9d16e924d1876d6e4cf22159906b"
)
SOURCE_HEAD_SHA = "b5bdc447dc48ed45433dad985d0e4a0a9d1de307"

TARGET_R = "2.5"
FIVE_YEAR_SAMPLE = 2448
FIVE_YEAR_PRIMARY_PF = "1.769639342624740541144278005"
FIVE_YEAR_PRIMARY_TOTAL_R = "15.73981375375935285531409927"
FIVE_YEAR_PRIMARY_MTM_DD_R = "2.73278323050218031949020759"
FIVE_YEAR_SECONDARY_PF = "1.654750054785311462947327222"
FIVE_YEAR_SECONDARY_TOTAL_R = "14.02761388418103890472068983"
FIVE_YEAR_SECONDARY_MTM_DD_R = "3.06844279176045846518557183"

FIVE_YEAR_PRIMARY_BLOCK_TOTALS_R = {
    "Y1": "0.1381703881552621048419367747",
    "Y2": "1.053828125000000000000000000",
    "Y3": "6.702520348837209302325581395",
    "Y4": "6.814415771831682416600615142",
    "Y5": "1.024979119935199031545965962",
}
FIVE_YEAR_SECONDARY_BLOCK_TOTALS_R = {
    "Y1": "0.0200453881552621048419367747",
    "Y2": "0.8037500000000000000000000000",
    "Y3": "6.295644933554817275747508306",
    "Y4": "6.382704003794038638280643026",
    "Y5": "0.519819558676920885850601724",
}

FORMATION_HEALTH_PROFILE_ID = r29.FORMATION_HEALTH_PROFILE_ID
FORMATION_HEALTH = dict(r29.FORMATION_HEALTH)
STRUCTURAL_QUALITY = dict(r29.QUALITY)
GLOBAL_RISK = dict(r29.GLOBAL_RISK)

POI_OVERLAY = {
    "profile_id": r43.BASE_POI_OVERLAY.profile_id,
    "rolling_family_trades": r43.BASE_POI_OVERLAY.rolling_family_trades,
    "min_observations": r43.BASE_POI_OVERLAY.min_observations,
    "cold_multiplier": str(r43.BASE_POI_OVERLAY.cold_multiplier),
    "weak_multiplier": str(r43.BASE_POI_OVERLAY.weak_multiplier),
    "healthy_mean_threshold_r": str(
        r43.BASE_POI_OVERLAY.healthy_mean_threshold_r
    ),
}

STRUCTURAL_PRIORS = {
    "nas100_market_multiplier": str(r42.NAS100_MARKET_MULTIPLIER),
    "nas100_short_extra_multiplier": str(
        r42.NAS100_SHORT_EXTRA_MULTIPLIER
    ),
    "nas100_short_total_multiplier": str(
        r42.NAS100_SHORT_TOTAL_MULTIPLIER
    ),
    "sp500_long_multiplier": str(r43.SP500_LONG_MULTIPLIER),
    "minimum_effective_weight": str(r43.MIN_EFFECTIVE_WEIGHT),
    "released_risk_reallocated": False,
}

EXECUTION_ARCHITECTURE = {
    "markets": ["NAS100", "SP500", "US30"],
    "poi_set": ["fvg", "relevant-swing", "cisd"],
    "structural_rearm_enabled": True,
    "same_symbol_distinct_structural_concurrency": True,
    "duplicate_structural_identity_allowed": False,
    "target_r": TARGET_R,
    "all_source_complete_signals_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
}


def dependency_contract_matches() -> bool:
    return (
        r29.dependency_contract_matches()
        and r43.BASE_POI_OVERLAY.profile_id
        == "PO-W10-N5-C0.50-WEAK0.50-T0.05"
        and str(r42.NAS100_MARKET_MULTIPLIER) == "0.50"
        and str(r42.NAS100_SHORT_EXTRA_MULTIPLIER) == "0.50"
        and str(r42.NAS100_SHORT_TOTAL_MULTIPLIER) == "0.2500"
        and str(r43.SP500_LONG_MULTIPLIER) == "0.75"
        and str(r43.MIN_EFFECTIVE_WEIGHT) == "0.005"
    )


def _fingerprint_payload() -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_head_sha": SOURCE_HEAD_SHA,
        "target_r": TARGET_R,
        "five_year_sample": FIVE_YEAR_SAMPLE,
        "five_year_primary_pf": FIVE_YEAR_PRIMARY_PF,
        "five_year_primary_total_r": FIVE_YEAR_PRIMARY_TOTAL_R,
        "five_year_primary_mtm_dd_r": FIVE_YEAR_PRIMARY_MTM_DD_R,
        "five_year_secondary_pf": FIVE_YEAR_SECONDARY_PF,
        "five_year_secondary_total_r": FIVE_YEAR_SECONDARY_TOTAL_R,
        "five_year_secondary_mtm_dd_r": FIVE_YEAR_SECONDARY_MTM_DD_R,
        "five_year_primary_block_totals_r": FIVE_YEAR_PRIMARY_BLOCK_TOTALS_R,
        "five_year_secondary_block_totals_r": FIVE_YEAR_SECONDARY_BLOCK_TOTALS_R,
        "formation_health_profile_id": FORMATION_HEALTH_PROFILE_ID,
        "formation_health": FORMATION_HEALTH,
        "structural_quality": STRUCTURAL_QUALITY,
        "global_risk": GLOBAL_RISK,
        "poi_overlay": POI_OVERLAY,
        "structural_priors": STRUCTURAL_PRIORS,
        "execution_architecture": EXECUTION_ARCHITECTURE,
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
    "two_year_retuning_permitted": False,
    "walk_forward_retuning_permitted": False,
    "all_source_complete_signals_preserved": True,
    "same_symbol_structural_concurrency_frozen": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}


def payload() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "head_sha": SOURCE_HEAD_SHA,
        },
        "five_year": {
            "sample": FIVE_YEAR_SAMPLE,
            "primary_pf": FIVE_YEAR_PRIMARY_PF,
            "primary_total_r": FIVE_YEAR_PRIMARY_TOTAL_R,
            "primary_mtm_dd_r": FIVE_YEAR_PRIMARY_MTM_DD_R,
            "secondary_pf": FIVE_YEAR_SECONDARY_PF,
            "secondary_total_r": FIVE_YEAR_SECONDARY_TOTAL_R,
            "secondary_mtm_dd_r": FIVE_YEAR_SECONDARY_MTM_DD_R,
            "primary_block_totals_r": FIVE_YEAR_PRIMARY_BLOCK_TOTALS_R,
            "secondary_block_totals_r": FIVE_YEAR_SECONDARY_BLOCK_TOTALS_R,
        },
        "formation_health_profile_id": FORMATION_HEALTH_PROFILE_ID,
        "formation_health": FORMATION_HEALTH,
        "structural_quality": STRUCTURAL_QUALITY,
        "global_risk": GLOBAL_RISK,
        "poi_overlay": POI_OVERLAY,
        "structural_priors": STRUCTURAL_PRIORS,
        "execution_architecture": EXECUTION_ARCHITECTURE,
        "dependency_contract_matches": dependency_contract_matches(),
        "governance": GOVERNANCE,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = payload()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "rule_fingerprint": RULE_FINGERPRINT,
                "dependency_contract_matches": report[
                    "dependency_contract_matches"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
