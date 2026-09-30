#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_integrator_b_provenance_coverage import (
    assess_b_provenance_coverage,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text())
    result = assess_b_provenance_coverage(payload["capability_scopes"])
    out = {
        "identity": "SHARED_INTEGRATOR_B_PROVENANCE_COVERAGE_001",
        "covered_count": len(result.covered_ids),
        "required_count": 24,
        "covered_ids": result.covered_ids,
        "missing_ids": result.missing_ids,
        "missing_terminal_ids": result.missing_terminal_ids,
        "missing_external_blocked_ids": result.missing_external_blocked_ids,
        "missing_nonterminal_ids": result.missing_nonterminal_ids,
        "coverage_complete": result.coverage_complete,
        "b_status_mutated": False,
        "holdout_authority": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
