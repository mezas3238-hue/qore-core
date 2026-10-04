#!/usr/bin/env python3
"""Materialize Architect-B final handoff readiness without emitting B-24."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b_world_perception_freeze import (
    assess_final_b_handoff,
)
from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    assess_b_provenance_coverage,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--covered-scope", action="append", required=True)
    parser.add_argument("--world-perception-freeze-present", action="store_true")
    parser.add_argument("--deterministic-replay-verified", action="store_true")
    parser.add_argument("--explicit-unknowns-preserved", action="store_true")
    parser.add_argument("--authority-free-outputs", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    coverage = assess_b_provenance_coverage(tuple(args.covered_scope))
    assessment = assess_final_b_handoff(
        provenance_coverage=coverage,
        world_perception_freeze_present=args.world_perception_freeze_present,
        deterministic_replay_verified=args.deterministic_replay_verified,
        explicit_unknowns_preserved=args.explicit_unknowns_preserved,
        authority_free_outputs=args.authority_free_outputs,
    )
    payload = {
        "identity": "SHARED_B_FINAL_HANDOFF_READINESS_001",
        "status": (
            "READY_TO_EMIT_B24"
            if assessment.handoff_authorized
            else "BLOCKED_DO_NOT_EMIT_B24"
        ),
        "pre_handoff_required_ids": assessment.pre_handoff_required_ids,
        "pre_handoff_nonterminal_ids": assessment.pre_handoff_nonterminal_ids,
        "provenance_missing_ids": assessment.provenance_missing_ids,
        "pre_handoff_provenance_complete": (
            assessment.pre_handoff_provenance_complete
        ),
        "world_perception_freeze_present": (
            assessment.world_perception_freeze_present
        ),
        "deterministic_replay_verified": (
            assessment.deterministic_replay_verified
        ),
        "explicit_unknowns_preserved": assessment.explicit_unknowns_preserved,
        "authority_free_outputs": assessment.authority_free_outputs,
        "handoff_authorized": assessment.handoff_authorized,
        "handoff_assessment_fingerprint_sha256": assessment.fingerprint(),
        "b24_handoff_emitted": False,
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
