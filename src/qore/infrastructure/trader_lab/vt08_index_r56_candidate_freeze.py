"""VT08 Index R56 — immutable freeze of the R55 distributed-risk candidate.

R55 is frozen immediately after its official dual-window development replay.
The freeze binds the exact candidate identity, rule fingerprint, source SHA,
workflow evidence, concentration checks, and economic metrics before any new
robustness, bootstrap, sensitivity, or independent reproduction is observed.

This evidence is development-only. It grants no DEMO, LIVE, production, or
real-capital authority.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)

SCHEMA = "qore.trader_lab.vt08_index_r56_candidate_freeze.v1"
FREEZE_ID = "VT08_INDEX_R56_R55_CANDIDATE_FREEZE_001"
CANDIDATE_ID = "VT08_INDEX_R55_DISTRIBUTED_CAUSAL_RISK_001"
CANDIDATE_RULE_FINGERPRINT = (
    "5b7a19b1dace3c1e92f021fdcbde9cc0ff8175633fc1c2a6892ffdf85bee2d13"
)

SOURCE_RUN_ID = 35456567688
SOURCE_ARTIFACT_ID = 10587569792
SOURCE_ARTIFACT_DIGEST = (
    "sha256:d6adc49831c5866e421357c602edb46521fbe1a34fae97869a1d1fec7fceca30"
)
SOURCE_HEAD_SHA = "8cd917654a938478a719cc822f601bd86bcc1ed4"

FIVE_YEAR: dict[str, object] = {
    "window": ["2018-09-15", "2023-09-15"],
    "sample": 2448,
    "primary_pf": "1.758724105897941271230638341",
    "primary_total_r": "22.20006948652723243413177337",
    "primary_mtm_dd_r": "2.201792047184170471841704718",
    "secondary_pf": "1.644536746156170668519278873",
    "secondary_total_r": "19.75678659179039032886861548",
    "secondary_mtm_dd_r": "2.380167047184170471841704718",
    "secondary_annual_totals_r": {
        "Y1": "0.332201638155262104841936775",
        "Y2": "3.762500000000",
        "Y3": "3.3477500000",
        "Y4": "6.941961835355558331553560419",
        "Y5": "5.366723118279569892473118280",
    },
    "stress_015_pf": "1.540276328886768047281881188",
    "stress_015_total_r": "17.31350369705354822360545758",
    "stress_020_pf": "1.444702272894778047821896639",
    "stress_020_total_r": "14.87022080231670611834229968",
    "leave_top_3_total_r": "17.95678659179039032886861547",
    "leave_top_3_pf": "1.585814335115743918304527765",
    "max_requested_weight_r": "0.25",
    "max_committed_structural_risk_r": "0.755",
}

RECENT_TWO_YEAR: dict[str, object] = {
    "window": ["2024-09-15", "2026-09-15"],
    "sample": 1017,
    "primary_pf": "1.627688237501519308016414369",
    "primary_total_r": "6.935996470396949835979068450",
    "primary_mtm_dd_r": "1.328909624846977228815435268",
    "secondary_pf": "1.522237447567218577009203075",
    "secondary_total_r": "6.044590220396949835979068450",
    "secondary_mtm_dd_r": "1.409409624846977228815435268",
    "secondary_annual_totals_r": {
        "Y1": "2.892413465938826710343563386",
        "Y2": "3.152176754458123125635505064",
    },
    "stress_015_pf": "1.425926849223617619138115039",
    "stress_015_total_r": "5.153183970396949835979068450",
    "stress_020_pf": "1.337617434611972428788250989",
    "stress_020_total_r": "4.261777720396949835979068450",
    "leave_top_3_total_r": "4.244590220396949835979068450",
    "leave_top_3_pf": "1.366721958287407382354763803",
    "max_requested_weight_r": "0.25",
    "max_committed_structural_risk_r": "0.505",
}

GOVERNANCE: dict[str, object] = {
    "candidate_frozen": True,
    "five_year_window_consumed": True,
    "two_year_window_consumed": True,
    "fresh_holdout_claim": False,
    "development_pass": True,
    "robustness_retuning_permitted": False,
    "walk_forward_retuning_permitted": False,
    "stress_retuning_permitted": False,
    "bootstrap_retuning_permitted": False,
    "concentration_retuning_permitted": False,
    "all_source_complete_signals_preserved": True,
    "signal_suppression_allowed": False,
    "zero_risk_allowed": False,
    "calendar_or_year_runtime_feature": False,
    "post_entry_outcome_runtime_feature": False,
    "certified": False,
    "demo_eligible": False,
    "live_authorized": False,
    "real_capital_authorized": False,
    "production_authorized": False,
}


def dependency_contract_matches() -> bool:
    return (
        r55.CANDIDATE_ID == CANDIDATE_ID
        and r55.RULE_FINGERPRINT == CANDIDATE_RULE_FINGERPRINT
        and r55.RULES["signals_suppressed"] is False
        and r55.RULES["calendar_or_year_runtime_feature"] is False
        and r55.RULES["freed_risk_opportunistically_reallocated"] is False
        and str(r55.MIN_EFFECTIVE_WEIGHT) == "0.005"
        and str(r55.MAX_REQUESTED_WEIGHT) == "0.25"
        and str(r55.PORTFOLIO_BUDGET_R) == "0.75"
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
        "rules": r55.RULES,
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
    print(
        json.dumps(
            {
                "freeze_id": FREEZE_ID,
                "candidate_id": CANDIDATE_ID,
                "candidate_rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
                "freeze_evidence_fingerprint": FREEZE_EVIDENCE_FINGERPRINT,
                "dependency_contract_matches": report[
                    "dependency_contract_matches"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
