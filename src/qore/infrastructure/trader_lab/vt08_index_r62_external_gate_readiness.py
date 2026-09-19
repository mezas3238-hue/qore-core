"""VT08 Index R62 — external-gate certification readiness bundle.

R62 binds the immutable R59/R58 candidate to the official successful R60 Core
robustness evidence, successful R61 independent stability evidence, and current
QORE CI. It prepares exact request payloads for the three externally owned
Trader-Lab gates:

- RISK_REVIEW
- CIBO_REVIEW
- INDEPENDENT_VALIDATION

R62 does NOT mint TraderLabGovernedAuthenticityProof values. Core explicitly
forbids the Trader Lab from self-issuing those proofs. Therefore R62 can mark
the candidate certification-ready for external review while remaining
DEMO_ELIGIBLE=False / TRADER_CERTIFIED=False until authentic external proofs
are supplied and verified.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)

SCHEMA = "qore.trader_lab.vt08_index_r62_external_gate_readiness.v1"
IDENTITY = "VT08_INDEX_R62_EXTERNAL_GATE_READINESS_001"

CANDIDATE_ID = freeze.CANDIDATE_ID
CANDIDATE_RULE_FINGERPRINT = freeze.CANDIDATE_RULE_FINGERPRINT

R59 = {
    "run_id": 35460187018,
    "artifact_id": 10589633213,
    "artifact_digest": (
        "sha256:bab6cb1dacf7d331aca68f97fa8227905ef35cc2492a6e9f4fee6ff6ae365e8d"
    ),
    "head_sha": "02c20f78ad8177ea8256f090bd9382775568bcab",
}

R60 = {
    "run_id": 35460660236,
    "artifact_id": 10589738798,
    "artifact_digest": (
        "sha256:14339ddd43fb3ca374a20294d7ed3ed2a310a2c52d33da0627c2217fc6226911"
    ),
    "head_sha": "dc9cac7fef30318b667aa6cc29612f2518922838",
    "decision": "PASS_R60_CORE_ROBUSTNESS_CONTINUE_CERTIFICATION",
}

R61 = {
    "run_id": 35462392609,
    "artifact_id": 10590286548,
    "artifact_digest": (
        "sha256:6f976b8fc80075ca2241a3877a4e5ba3973ff440395395c3a6dd39ad9d24c4e9"
    ),
    "head_sha": "1ebd584f29c823cf62ed1f6ac9ba08e31b9a4ae8",
    "decision": "PASS_R61_INDEPENDENT_STABILITY_AUDIT",
}

QORE_CI = {
    "run_id": 35462395297,
    "head_sha": "1ebd584f29c823cf62ed1f6ac9ba08e31b9a4ae8",
    "conclusion": "success",
}

ECONOMIC_SUMMARY = {
    "five_year": {
        "sample": 2448,
        "secondary_pf": "1.629558488030606209556849234",
        "secondary_total_r": "19.57012376284302190781598390",
        "secondary_mtm_dd_r": "2.503917047184170471841704718",
        "hard_stress_0_20_pf": "1.431543704562873065286109115",
        "hard_stress_0_20_total_r": "14.63395828915881138298682560",
        "monte_carlo_positive_terminal_fraction": "0.9998",
        "monte_carlo_p95_dd_r": "3.73",
        "wfo_folds_passed": "3/3",
    },
    "recent_two_year": {
        "sample": 1017,
        "secondary_pf": "1.523139762832498209330322819",
        "secondary_total_r": "6.066902720396949835979068450",
        "secondary_mtm_dd_r": "1.409409624846977228815435268",
        "hard_stress_0_20_pf": "1.338409582735828342824503214",
        "hard_stress_0_20_total_r": "4.280152720396949835979068450",
        "monte_carlo_positive_terminal_fraction": "0.9832",
        "monte_carlo_p95_dd_r": "2.78",
        "wfo_folds_passed": "3/3",
    },
}

KNOWN_LIMITATIONS = (
    "All 5Y and recent 2Y windows are consumed evidence; neither is a fresh holdout.",
    (
        "Most recent WFO fold remains positive at -0.10R/trade but is slightly "
        "negative at the extreme -0.20R/trade stress."
    ),
    (
        "Trader Lab external governed authenticity proofs cannot be minted by "
        "the Trader Lab or this module."
    ),
)


def _request_payload(authority: str) -> dict[str, object]:
    payload = {
        "schema": "qore.trader_lab.external_gate_request.v1",
        "candidate_id": CANDIDATE_ID,
        "candidate_rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
        "freeze_id": freeze.FREEZE_ID,
        "authority": authority,
        "source_evidence": {
            "r59": R59,
            "r60": R60,
            "r61": R61,
            "qore_ci": QORE_CI,
        },
        "economic_summary": ECONOMIC_SUMMARY,
        "known_limitations": list(KNOWN_LIMITATIONS),
        "requested_disposition": "APPROVED_OR_EXPLICITLY_REJECTED",
        "self_issued_proof": False,
    }
    request_fingerprint = sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    return {
        **payload,
        "request_fingerprint": request_fingerprint,
    }


def build_report() -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R62 frozen R59/R58 dependency drift")

    requests = {
        "risk_review": _request_payload("RISK"),
        "cibo_review": _request_payload("CIBO"),
        "independent_validation": _request_payload(
            "INDEPENDENT_VALIDATION"
        ),
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "candidate_modified": False,
        },
        "source_evidence": {
            "r59": R59,
            "r60": R60,
            "r61": R61,
            "qore_ci": QORE_CI,
        },
        "economic_summary": ECONOMIC_SUMMARY,
        "known_limitations": list(KNOWN_LIMITATIONS),
        "external_gate_requests": requests,
        "quantitative_certification_ready": True,
        "external_governed_gates_satisfied": False,
        "demo_eligible": False,
        "trader_certified": False,
        "decision": "READY_FOR_EXTERNAL_GOVERNED_GATE_REVIEW",
        "governance": {
            "self_certification_forbidden": True,
            "external_proofs_fabricated": False,
            "fresh_holdout_claim": False,
            "candidate_retuned": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "decision": report["decision"],
                "quantitative_certification_ready": report[
                    "quantitative_certification_ready"
                ],
                "external_governed_gates_satisfied": report[
                    "external_governed_gates_satisfied"
                ],
                "demo_eligible": report["demo_eligible"],
                "trader_certified": report["trader_certified"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
