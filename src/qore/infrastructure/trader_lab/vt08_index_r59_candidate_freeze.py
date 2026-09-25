"""VT08 Index R59 — immutable freeze of the exact-lineage R58 candidate.

R58 is the first post-R47 candidate that preserves exact frozen R47 lineage,
passes the consumed 5Y and recent 2Y development gates, survives extra stress,
and remains positive after removal of the three largest winning contributions.

R59 freezes that exact identity before any new robustness or reproduction work.
No DEMO, LIVE, production, or real-capital authority is granted.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)

SCHEMA = "qore.trader_lab.vt08_index_r59_candidate_freeze.v1"
FREEZE_ID = "VT08_INDEX_R59_R58_CANDIDATE_FREEZE_001"
CANDIDATE_ID = "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
CANDIDATE_RULE_FINGERPRINT = (
    "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
)

SOURCE_RUN_ID = 35457127324
SOURCE_ARTIFACT_ID = 10588014348
SOURCE_ARTIFACT_DIGEST = (
    "sha256:d77bc9079e72240f0e8ffe8e6c15a7d6a9697b19e5da18c6a0f35bd463276f74"
)
SOURCE_HEAD_SHA = "34dfeb9ef9220191c5e4847ab13d3be20f9cd53c"

FIVE_YEAR = {
    "sample": 2448,
    "primary_pf": "1.742706111321657525772404513",
    "primary_total_r": "22.03820599968512717097387863",
    "primary_mtm_dd_r": "2.319917047184170471841704718",
    "secondary_pf": "1.629558488030606209556849234",
    "secondary_total_r": "19.57012376284302190781598390",
    "secondary_mtm_dd_r": "2.503917047184170471841704718",
    "leave_top_3_out_secondary_pf": "1.571653627939396117414131028",
    "leave_top_3_out_secondary_total_r": "17.77012376284302190781598390",
    "stress_015_pf": "1.526247450152837317054716672",
    "stress_020_pf": "1.431543704562873065286109115",
}

RECENT_TWO_YEAR = {
    "sample": 1017,
    "primary_pf": "1.628653568489481093349699162",
    "primary_total_r": "6.960277720396949835979068450",
    "primary_mtm_dd_r": "1.328909624846977228815435268",
    "secondary_pf": "1.523139762832498209330322819",
    "secondary_total_r": "6.066902720396949835979068450",
    "secondary_mtm_dd_r": "1.409409624846977228815435268",
    "leave_top_3_out_secondary_pf": "1.367928509826469179846933945",
    "leave_top_3_out_secondary_total_r": "4.266902720396949835979068450",
    "stress_015_pf": "1.426771668441081127369446869",
    "stress_020_pf": "1.338409582735828342824503214",
}

GOVERNANCE = {
    "candidate_frozen": True,
    "development_pass": True,
    "five_year_window_consumed": True,
    "two_year_window_consumed": True,
    "fresh_holdout_claim": False,
    "robustness_retuning_permitted": False,
    "walk_forward_retuning_permitted": False,
    "stress_retuning_permitted": False,
    "bootstrap_retuning_permitted": False,
    "concentration_retuning_permitted": False,
    "calendar_or_year_runtime_feature": False,
    "post_entry_outcome_runtime_feature": False,
    "all_source_complete_signals_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "certified": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}


def dependency_contract_matches() -> bool:
    return (
        r58.CANDIDATE_ID == CANDIDATE_ID
        and r58.RULE_FINGERPRINT == CANDIDATE_RULE_FINGERPRINT
        and r58.RULES["signals_suppressed"] is False
        and r58.RULES["calendar_or_year_runtime_feature"] is False
        and str(r58.RULES["minimum_effective_weight_r"]) == "0.005"
        and str(r58.RULES["max_requested_weight_r"]) == "0.25"
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
        "rules": r58.RULES,
        "five_year": FIVE_YEAR,
        "recent_two_year": RECENT_TWO_YEAR,
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
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
