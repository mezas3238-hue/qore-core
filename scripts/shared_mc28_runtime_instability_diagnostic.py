#!/usr/bin/env python3
"""MC-28 model/runtime instability diagnostic bound to B18 real replay."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.runtime_instability_diagnostic import (
    RuntimeInstabilityState,
    RuntimeStabilityEvidence,
    diagnose_runtime_instability,
)

IDENTITY = "QORE_SHARED_MC28_MODEL_RUNTIME_INSTABILITY_DIAGNOSTIC_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b18", type=Path, required=True)
    parser.add_argument("--prior-mc28", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    b18 = _load(args.b18)
    prior = _load(args.prior_mc28)

    if b18.get("status") != "REAL_READ_ONLY_CORE_BROKER_REPLICATION_PASS":
        raise AssertionError("B18 real Core/Broker replication missing")
    if b18.get("core_runtime_executed") is not True:
        raise AssertionError("B18 did not execute Core runtime")
    if b18.get("core_runtime_deterministic_rebuild") is not True:
        raise AssertionError("B18 deterministic rebuild evidence missing")
    if b18.get("productive_authority") is not False:
        raise AssertionError("B18 unexpectedly carries productive authority")

    assessments = b18.get("system_assessments")
    if not isinstance(assessments, list):
        raise AssertionError("B18 system assessments missing")
    core_rows = [
        row
        for row in assessments
        if isinstance(row, dict) and row.get("system_kind") == "CORE_COMPONENT"
    ]
    if len(core_rows) != 1:
        raise AssertionError("B18 must contain exactly one Core assessment")
    core = core_rows[0]

    evidence = RuntimeStabilityEvidence(
        core_runtime_executed=True,
        deterministic_rebuild=True,
        core_system_state=str(core["state"]),
        error_count=int(core["error_count"]),
        snapshot_fingerprint_sha256=str(
            b18["core_snapshot_fingerprint_sha256"]
        ),
        checkpoint_fingerprint_sha256=str(
            b18["core_checkpoint_fingerprint_sha256"]
        ),
        evidence_refs=(
            "artifact:11120521150",
            "run:36764365409",
        ),
    )
    baseline = diagnose_runtime_instability(evidence)
    deterministic_fault = diagnose_runtime_instability(
        replace(evidence, deterministic_rebuild=False)
    )
    error_fault = diagnose_runtime_instability(
        replace(evidence, error_count=1)
    )
    degraded_fault = diagnose_runtime_instability(
        replace(evidence, core_system_state="DEGRADED")
    )

    diagnostic_pass = (
        baseline.state is RuntimeInstabilityState.STABLE
        and deterministic_fault.state is RuntimeInstabilityState.INSTABILITY
        and error_fault.state is RuntimeInstabilityState.INSTABILITY
        and degraded_fault.state is RuntimeInstabilityState.INSTABILITY
    )

    if prior.get("status") != "MC28_MAPPING_ERROR_DIAGNOSTIC_REAL_BOUND_PASS_OPEN_4":
        raise AssertionError("prior MC28 mapping diagnostic evidence missing")
    prior_open = tuple(sorted(str(x) for x in prior["open_diagnostics"]))
    if "MODEL_RUNTIME_INSTABILITY" not in prior_open:
        raise AssertionError("runtime instability gap unexpectedly absent")
    open_after = tuple(
        item for item in prior_open if item != "MODEL_RUNTIME_INSTABILITY"
    )
    expected_after = (
        "BROKER_PROVIDER_MISMATCH",
        "CLOCK_DRIFT",
        "EXECUTION_QUALITY_DETERIORATION",
    )
    if open_after != expected_after:
        raise AssertionError(f"unexpected post-runtime gaps: {open_after}")

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC28_MODEL_RUNTIME_INSTABILITY_REAL_BOUND_PASS_OPEN_3"
            if diagnostic_pass
            else "MC28_MODEL_RUNTIME_INSTABILITY_DIAGNOSTIC_FAILED"
        ),
        "real_core_runtime_executed": True,
        "real_deterministic_rebuild_verified": True,
        "real_core_state": core["state"],
        "real_core_error_count": core["error_count"],
        "baseline_diagnostic_state": baseline.state.value,
        "deterministic_drift_fault_state": deterministic_fault.state.value,
        "runtime_error_fault_state": error_fault.state.value,
        "degraded_runtime_fault_state": degraded_fault.state.value,
        "model_runtime_instability_diagnostic_bound": diagnostic_pass,
        "open_diagnostic_count": len(open_after),
        "open_diagnostics": open_after,
        "model_runtime_instability_open": False,
        "restart_authority": False,
        "mutation_authority": False,
        "execution_authority": False,
        "risk_authority": False,
        "productive_authority": False,
        "mc28_completed_and_proven": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
