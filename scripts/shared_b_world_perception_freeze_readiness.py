#!/usr/bin/env python3
"""Materialize Architect-B pre-freeze readiness without emitting B-22."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b_world_perception_freeze import (
    assess_world_perception_freeze,
)
from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    assess_b_provenance_coverage,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--covered-scope",
        action="append",
        required=True,
        help="B provenance capability scope; repeat for every covered scope",
    )
    parser.add_argument("--deterministic-replay-verified", action="store_true")
    parser.add_argument("--explicit-unknowns-preserved", action="store_true")
    parser.add_argument("--authority-free-outputs", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    coverage = assess_b_provenance_coverage(tuple(args.covered_scope))
    assessment = assess_world_perception_freeze(
        provenance_coverage=coverage,
        deterministic_replay_verified=args.deterministic_replay_verified,
        explicit_unknowns_preserved=args.explicit_unknowns_preserved,
        authority_free_outputs=args.authority_free_outputs,
    )
    payload = {
        "identity": "SHARED_B_WORLD_PERCEPTION_FREEZE_READINESS_001",
        "status": (
            "READY_TO_EMIT_B22"
            if assessment.freeze_authorized
            else "BLOCKED_DO_NOT_EMIT_B22"
        ),
        "upstream_required_ids": assessment.upstream_required_ids,
        "upstream_nonterminal_ids": assessment.upstream_nonterminal_ids,
        "provenance_covered_ids": assessment.provenance_covered_ids,
        "provenance_missing_ids": assessment.provenance_missing_ids,
        "pre_freeze_provenance_complete": (
            assessment.pre_freeze_provenance_complete
        ),
        "deterministic_replay_verified": (
            assessment.deterministic_replay_verified
        ),
        "explicit_unknowns_preserved": assessment.explicit_unknowns_preserved,
        "authority_free_outputs": assessment.authority_free_outputs,
        "freeze_authorized": assessment.freeze_authorized,
        "freeze_assessment_fingerprint_sha256": assessment.fingerprint(),
        "world_perception_freeze_emitted": False,
        "final_shared_holdout_opened": False,
        "shared_certification_authority": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
