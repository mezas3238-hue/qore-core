"""Emit deterministic Architect-B5 handoff truth for Shared Lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_b5_handoff import build_b5_handoff


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b4-comparability-eligible-count", type=int, required=True)
    parser.add_argument(
        "--b4-relational-comparability-authorized",
        action="store_true",
    )
    parser.add_argument(
        "--b11-empirical-population-complete",
        action="store_true",
    )
    parser.add_argument(
        "--b12-empirical-population-complete",
        action="store_true",
    )
    parser.add_argument(
        "--b13-empirical-population-complete",
        action="store_true",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_b5_handoff(
        b4_comparability_eligible_count=args.b4_comparability_eligible_count,
        b4_relational_comparability_authorized=(
            args.b4_relational_comparability_authorized
        ),
        b11_empirical_population_complete=(
            args.b11_empirical_population_complete
        ),
        b12_empirical_population_complete=(
            args.b12_empirical_population_complete
        ),
        b13_empirical_population_complete=(
            args.b13_empirical_population_complete
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "fingerprint": payload["handoff_fingerprint_sha256"],
                "engineering_open_count": payload["engineering_open_count"],
                "dependency_blocked_count": payload["dependency_blocked_count"],
                "complete_and_proven_count": payload["complete_and_proven_count"],
                "empirical_relational_population_complete": payload[
                    "empirical_relational_population_complete"
                ],
                "handoff_to_integrator_3_ready": payload[
                    "handoff_to_integrator_3_ready"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
