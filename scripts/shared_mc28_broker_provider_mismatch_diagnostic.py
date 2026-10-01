#!/usr/bin/env python3
"""MC-28 broker/provider mismatch diagnostic bound to B18 real evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.broker_provider_mismatch_diagnostic import (
    BrokerProviderEvidence,
    BrokerProviderMismatchState,
    diagnose_broker_provider_mismatch,
)

IDENTITY = "QORE_SHARED_MC28_BROKER_PROVIDER_MISMATCH_DIAGNOSTIC_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _system(
    rows: list[object],
    kind: str,
) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("system_kind") == kind
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {kind} assessment")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b18", type=Path, required=True)
    parser.add_argument("--prior-mc28", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    b18 = _load(args.b18)
    prior = _load(args.prior_mc28)

    if b18.get("status") != "REAL_READ_ONLY_CORE_BROKER_REPLICATION_PASS":
        raise AssertionError("B18 real Core/Broker evidence missing")
    if b18.get("provider_catalog_matches_frozen") is not True:
        raise AssertionError("B18 provider catalog did not match frozen digest")
    if b18.get("broker_mutation") is not False:
        raise AssertionError("B18 must remain read-only")

    rows = b18.get("system_assessments")
    if not isinstance(rows, list):
        raise AssertionError("B18 system assessments missing")
    provider = _system(rows, "PROVIDER")
    broker = _system(rows, "BROKER")

    evidence = BrokerProviderEvidence(
        provider_state=str(provider["state"]),
        broker_state=str(broker["state"]),
        provider_catalog_matches_frozen=True,
        provider_error_count=int(provider["error_count"]),
        broker_error_count=int(broker["error_count"]),
        evidence_refs=(
            "artifact:11120521150",
            "run:36764365409",
        ),
    )
    baseline = diagnose_broker_provider_mismatch(evidence)
    state_fault = diagnose_broker_provider_mismatch(
        replace(evidence, provider_state="DEGRADED")
    )
    catalog_fault = diagnose_broker_provider_mismatch(
        replace(evidence, provider_catalog_matches_frozen=False)
    )
    error_fault = diagnose_broker_provider_mismatch(
        replace(evidence, broker_error_count=1)
    )
    unknown_fault = diagnose_broker_provider_mismatch(
        replace(evidence, provider_error_count=None)
    )

    diagnostic_pass = (
        baseline.state is BrokerProviderMismatchState.CONSISTENT
        and state_fault.state is BrokerProviderMismatchState.MISMATCH
        and catalog_fault.state is BrokerProviderMismatchState.MISMATCH
        and error_fault.state is BrokerProviderMismatchState.MISMATCH
        and unknown_fault.state is BrokerProviderMismatchState.UNKNOWN
    )

    expected_prior = (
        "MC28_MODEL_RUNTIME_INSTABILITY_REAL_BOUND_PASS_OPEN_3"
    )
    if prior.get("status") != expected_prior:
        raise AssertionError("prior MC28 runtime diagnostic evidence missing")
    prior_open = tuple(sorted(str(x) for x in prior["open_diagnostics"]))
    if "BROKER_PROVIDER_MISMATCH" not in prior_open:
        raise AssertionError("broker/provider gap unexpectedly absent")
    open_after = tuple(
        item for item in prior_open if item != "BROKER_PROVIDER_MISMATCH"
    )
    expected_after = (
        "CLOCK_DRIFT",
        "EXECUTION_QUALITY_DETERIORATION",
    )
    if open_after != expected_after:
        raise AssertionError(f"unexpected post-comparator gaps: {open_after}")

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC28_BROKER_PROVIDER_MISMATCH_REAL_BOUND_PASS_OPEN_2"
            if diagnostic_pass
            else "MC28_BROKER_PROVIDER_MISMATCH_DIAGNOSTIC_FAILED"
        ),
        "real_provider_state": provider["state"],
        "real_broker_state": broker["state"],
        "real_provider_catalog_matches_frozen": True,
        "baseline_diagnostic_state": baseline.state.value,
        "state_divergence_fault_state": state_fault.state.value,
        "catalog_drift_fault_state": catalog_fault.state.value,
        "error_asymmetry_fault_state": error_fault.state.value,
        "incomplete_evidence_fault_state": unknown_fault.state.value,
        "broker_provider_mismatch_diagnostic_bound": diagnostic_pass,
        "open_diagnostic_count": len(open_after),
        "open_diagnostics": open_after,
        "broker_provider_mismatch_open": False,
        "broker_mutation_authority": False,
        "restart_authority": False,
        "order_authority": False,
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
