#!/usr/bin/env python3
"""Build the Architect-2 certification evidence-readiness gate.

Functional completeness and certification evidence are deliberately separate.
A working research runtime must never make burned/reused evidence certifying.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FAMILY_DISPOSITIONS: dict[str, dict[str, Any]] = {
    "FRESH_FORWARD_CAUSAL": {
        "status": "BLOCKED_EXTERNAL_FRESH_FORWARD_EVIDENCE",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "Current Trader-Lab/Capital-Science bridge is explicitly "
            "NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH and creates no Fresh-OOS claim."
        ),
    },
    "PROVIDER_EXECUTION_ECONOMICS": {
        "status": "PARTIAL_EMPIRICAL_CLOSURE",
        "certification_ready": False,
        "partial": True,
        "reason": (
            "Provider execution/slippage is partially proven for T11, while Fresh-OOS "
            "gross-edge and provider-bound market-impact evidence remain required."
        ),
    },
    "SCARCITY_CONCENTRATION": {
        "status": "BLOCKED_REAL_SCARCITY_POPULATION",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "Research replay can exercise the mechanism, but certification still "
            "requires real simultaneous scarcity and non-worse concentration evidence."
        ),
    },
    "PATH_STRESS_TEMPORAL_MC": {
        "status": "RESEARCH_ONLY_NOT_CERTIFYING",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "Current path/MC/stress surfaces explicitly prohibit certification claims "
            "and still require real/fresh temporal populations."
        ),
    },
    "COMPOUND_PORTFOLIO_CAPITAL": {
        "status": "RESEARCH_ONLY_NOT_CERTIFYING",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "The reused-holdout compound population binding is BURNED_RESEARCH and "
            "explicitly cannot claim certification readiness."
        ),
    },
    "POST_OUTCOME_MEMORY_GOVERNANCE": {
        "status": "BLOCKED_POST_OUTCOME_AND_EXTERNAL_GOVERNANCE",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "GEN-C13 remains post-outcome research/shadow and GEN-C14 includes external "
            "Owner review/promotion evidence that cannot be fabricated."
        ),
    },
    "EXAM_GOVERNANCE": {
        "status": "BLOCKED_EXAMS_NOT_RUN",
        "certification_ready": False,
        "partial": False,
        "reason": (
            "Pre-exam prerequisites and the actual governed Final/World-Cup exams remain "
            "unexecuted; software-gate readiness is not exam PASS."
        ),
    },
}

EVIDENCE_REFS = (
    "src/qore/infrastructure/cibo_capital_science_runtime_bridge.py",
    "src/qore/infrastructure/cibo_compound_real_population_binding.py",
    "src/qore/infrastructure/cibo_compound_path_monte_carlo.py",
    "src/qore/infrastructure/cibo_meta_capital_memory.py",
    "artifacts/arch2/CIBO_ARCH2_EXTERNAL_DEPENDENCY_COLLAPSE_V1.json",
    "artifacts/arch2/CIBO_ARCH2_CERTIFICATION_BLOCKER_RECONCILIATION_V1.json",
)


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_readiness(
    collapse: dict[str, Any],
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    actual_families = {
        name
        for name in collapse.get("dependency_families", {})
        if name != "UNCLASSIFIED_EXTERNAL"
    }
    expected_families = set(FAMILY_DISPOSITIONS)
    missing = sorted(expected_families - actual_families)
    unexpected = sorted(actual_families - expected_families)
    if missing or unexpected:
        raise ValueError(
            f"dependency family drift: missing={missing}, unexpected={unexpected}"
        )

    family_rows = collapse["dependency_families"]
    families = []
    for name in sorted(expected_families):
        policy = FAMILY_DISPOSITIONS[name]
        families.append(
            {
                "family": name,
                "row_count": int(family_rows[name]["row_count"]),
                "status": policy["status"],
                "certification_ready": policy["certification_ready"],
                "partial": policy["partial"],
                "reason": policy["reason"],
            }
        )

    ready_count = sum(1 for item in families if item["certification_ready"])
    partial_count = sum(1 for item in families if item["partial"])
    blocked_count = len(families) - ready_count - partial_count

    phase22 = reconciliation.get("phase22_v4_preexecution", {})
    owner_authorization = bool(phase22.get("owner_authorization_present"))
    fresh_executed = bool(phase22.get("fresh_outcomes_executed"))

    return {
        "schema": "qore.cibo.arch2-certification-evidence-readiness.v1",
        "source_collapse_schema": collapse.get("schema"),
        "family_count": len(families),
        "certification_ready_family_count": ready_count,
        "partial_family_count": partial_count,
        "blocked_family_count": blocked_count,
        "external_dependency_blocked_row_count": int(
            collapse["external_dependency_blocked_row_count"]
        ),
        "architect2_internal_repair_count": collapse.get(
            "actionable_architect2_internal_repair_count"
        ),
        "fresh_oos_owner_authorization_present": owner_authorization,
        "fresh_outcomes_executed": fresh_executed,
        "certification_execution_ready": (
            ready_count == len(families)
            and int(collapse["external_dependency_blocked_row_count"]) == 0
            and owner_authorization
            and fresh_executed
        ),
        "families": families,
        "evidence_refs": list(EVIDENCE_REFS),
        "disposition": (
            "EXTERNAL_EVIDENCE_NOT_READY__DO_NOT_OPEN_CERTIFICATION_EXECUTION"
        ),
        "governance": {
            "functional_completeness_is_not_certification": True,
            "burned_research_is_not_fresh_oos": True,
            "research_runtime_may_not_self_promote": True,
            "merge_performed": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collapse",
        type=Path,
        default=Path(
            "artifacts/arch2/CIBO_ARCH2_EXTERNAL_DEPENDENCY_COLLAPSE_V1.json"
        ),
    )
    parser.add_argument(
        "--reconciliation",
        type=Path,
        default=Path(
            "artifacts/arch2/CIBO_ARCH2_CERTIFICATION_BLOCKER_RECONCILIATION_V1.json"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_readiness(_load(args.collapse), _load(args.reconciliation))
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
