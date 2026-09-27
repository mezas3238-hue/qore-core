"""Emit the frozen Phase20 H+I policy candidate pre-registration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)


def build_report() -> dict[str, Any]:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return {
        "schema": "qore.cibo.phase20.policy_candidate_freeze.v1",
        "identity": candidate.candidate_id,
        "status": "FROZEN_FOR_FRESH_FORWARD_RESEARCH",
        "code_sha": candidate.code_sha,
        "frozen_at": candidate.frozen_at.isoformat(),
        "parameter_sha256": candidate.parameter_sha256(),
        "parameters": candidate.parameter_payload(),
        "governance": {
            "outcome_aware": candidate.outcome_aware,
            "validation_tuned": candidate.validation_tuned,
            "phase19j_burned_validation_reused": (
                candidate.phase19j_burned_validation_reused
            ),
            "policy_certified": candidate.policy_certified,
            "allocation_authority": candidate.allocation_authority,
            "risk_authority": candidate.risk_authority,
            "execution_authority": candidate.execution_authority,
            "demo_execution_authorized": candidate.demo_execution_authorized,
            "live_authorized": candidate.live_authorized,
            "real_capital_authorized": candidate.real_capital_authorized,
            "merge_authorized": candidate.merge_authorized,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
