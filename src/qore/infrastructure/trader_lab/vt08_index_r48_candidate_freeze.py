"""VT08 Index R48 — immutable freeze of the R47 dual-window candidate.

R47 is the first source-complete VT08 Index identity in this research chain to
pass the Owner's consumed 5Y and recent 2Y development gates simultaneously.
R48 freezes that exact rule identity and its official evidence before any
robustness, walk-forward, stress, bootstrap, or sensitivity work is observed.

This is governance evidence only. It grants no DEMO, LIVE, production, or
real-capital authority.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)

SCHEMA = "qore.trader_lab.vt08_index_r48_candidate_freeze.v1"
FREEZE_ID = "VT08_INDEX_R48_R47_CANDIDATE_FREEZE_001"
CANDIDATE_ID = "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
CANDIDATE_RULE_FINGERPRINT = (
    "013bffb847dff546cdb2a31ac9931bdb1336596c540f6a72c5c729d1762c36c8"
)

SOURCE_RUN_ID = 35439293342
SOURCE_ARTIFACT_ID = 10583234011
SOURCE_ARTIFACT_DIGEST = (
    "sha256:9a88d3b912e0914bf5625fddf0d2584e87fa0e6766692b8a35bf4593cfd658c7"
)
SOURCE_HEAD_SHA = "382c9dfd606af649dca07380a2fe8cacc99f458f"

FIVE_YEAR = {
    "window": ["2018-09-15", "2023-09-15"],
    "sample": 2448,
    "primary_pf": "2.386649334704927017122102215",
    "primary_total_r": "21.19706512074262228717188944",
    "primary_mtm_dd_r": "2.507132233051523477599343040",
    "secondary_pf": "2.231715266927497713808336872",
    "secondary_total_r": "19.72480973857281304205077000",
    "secondary_mtm_dd_r": "2.677507233051523477599343040",
    "primary_block_totals_r": {
        "Y1": "0.1425453881552621048419367747",
        "Y2": "3.866625000000000000000000000",
        "Y3": "2.002457848837209302325581395",
        "Y4": "9.684401513814951848458405314",
        "Y5": "5.495135369935199031545965962",
    },
    "secondary_block_totals_r": {
        "Y1": "0.0269203881552621048419367747",
        "Y2": "3.652625000000000000000000000",
        "Y3": "1.640519933554817275747508306",
        "Y4": "9.256462358185812775610723194",
        "Y5": "5.142632058676920885850601724",
    },
}

RECENT_TWO_YEAR = {
    "window": ["2024-09-15", "2026-09-15"],
    "sample": 1017,
    "primary_pf": "1.900598634355609837892393762",
    "primary_total_r": "4.592939057606252161560463799",
    "primary_mtm_dd_r": "2.292587134561972539856735505",
    "secondary_pf": "1.777798685467245655581477532",
    "secondary_total_r": "4.154125311759076081826244530",
    "secondary_mtm_dd_r": "2.426774634561972539856735505",
    "primary_block_totals_r": {
        "Y1": "1.043449803148129035924958735",
        "Y2": "3.549489254458123125635505064",
    },
    "secondary_block_totals_r": {
        "Y1": "0.8263235573009529561907394656",
        "Y2": "3.327801754458123125635505064",
    },
}

EXECUTION_ARCHITECTURE = {
    "markets": ["NAS100", "SP500", "US30"],
    "poi_set": ["fvg", "relevant-swing", "cisd"],
    "structural_rearm_enabled": True,
    "same_symbol_distinct_structural_concurrency": True,
    "duplicate_structural_identity_allowed": False,
    "all_source_complete_signals_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "freed_risk_reallocated": False,
    "minimum_effective_weight_r": "0.005",
}

GOVERNANCE = {
    "candidate_frozen": True,
    "five_year_window_consumed": True,
    "two_year_window_consumed": True,
    "fresh_holdout_claim": False,
    "robustness_retuning_permitted": False,
    "walk_forward_retuning_permitted": False,
    "stress_retuning_permitted": False,
    "bootstrap_retuning_permitted": False,
    "calendar_or_year_runtime_feature": False,
    "post_entry_outcome_runtime_feature": False,
    "all_source_complete_signals_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "freed_risk_reallocated": False,
    "certified": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}


def dependency_contract_matches() -> bool:
    return (
        r47.CANDIDATE_ID == CANDIDATE_ID
        and r47.RULE_FINGERPRINT == CANDIDATE_RULE_FINGERPRINT
        and r47.RULES["signals_suppressed"] is False
        and r47.RULES["freed_risk_reallocated"] is False
        and r47.RULES["calendar_feature_used"] is False
        and str(r47.MIN_EFFECTIVE_WEIGHT) == "0.005"
    )


def _freeze_payload() -> dict[str, Any]:
    return {
        "freeze_id": FREEZE_ID,
        "candidate_id": CANDIDATE_ID,
        "candidate_rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_head_sha": SOURCE_HEAD_SHA,
        "rules": r47.RULES,
        "five_year": FIVE_YEAR,
        "recent_two_year": RECENT_TWO_YEAR,
        "execution_architecture": EXECUTION_ARCHITECTURE,
        "governance": GOVERNANCE,
    }


FREEZE_EVIDENCE_FINGERPRINT = sha256(
    json.dumps(
        _freeze_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def payload() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        **_freeze_payload(),
        "freeze_evidence_fingerprint": FREEZE_EVIDENCE_FINGERPRINT,
        "dependency_contract_matches": dependency_contract_matches(),
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
                "freeze_id": FREEZE_ID,
                "candidate_id": CANDIDATE_ID,
                "candidate_rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
                "freeze_evidence_fingerprint": FREEZE_EVIDENCE_FINGERPRINT,
                "dependency_contract_matches": report["dependency_contract_matches"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
