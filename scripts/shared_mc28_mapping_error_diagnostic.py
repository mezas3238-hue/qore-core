#!/usr/bin/env python3
"""MC-28 mapping-error diagnostic bound to B identity frontier V3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.mapping_error_diagnostic import (
    KNOWN_MAPPING_STAGES,
    MappingDiagnosticState,
    MappingExpectation,
    MappingObservation,
    diagnose_mapping,
)

IDENTITY = "QORE_SHARED_MC28_MAPPING_ERROR_DIAGNOSTIC_001"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier-v3", type=Path, required=True)
    parser.add_argument("--prior-mc28", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frontier = _load(args.frontier_v3)
    prior = _load(args.prior_mc28)

    if frontier.get("identity") != "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001":
        raise AssertionError("unexpected B identity frontier")
    if frontier.get("status") != "EXACT_177_SENSOR_IDENTITY_FRONTIER_V3_MATERIALIZED":
        raise AssertionError("B identity frontier V3 not materialized")
    if frontier.get("sensor_count") != 177:
        raise AssertionError("B identity frontier is not exact 177")
    if frontier.get("automatic_identity_inference") is not False:
        raise AssertionError("B identity frontier used automatic inference")
    if frontier.get("b06_complete") is not False:
        raise AssertionError("B06 must remain open")

    if prior.get("status") != "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_PASS_OPEN_5":
        raise AssertionError("prior MC28 diagnostic inventory missing")
    prior_open = tuple(sorted(str(x) for x in prior["open_diagnostics"]))
    if "MAPPING_ERRORS" not in prior_open:
        raise AssertionError("prior MC28 mapping gap already absent unexpectedly")

    records = frontier.get("records")
    if not isinstance(records, list) or len(records) != 177:
        raise AssertionError("B identity records missing")

    match_count = 0
    unknown_count = 0
    baseline_mismatch_count = 0
    injected_mismatch_detected = 0

    for raw in records:
        if not isinstance(raw, dict):
            raise AssertionError("identity record is not an object")
        provider = str(raw["provider"])
        symbol_id = int(raw["provider_symbol_id"])
        symbol = str(raw["provider_symbol"])
        description = str(raw["provider_description"])
        stage = str(raw["resolution_stage"])
        expectation = MappingExpectation(
            provider=provider,
            provider_symbol_id=symbol_id,
            provider_symbol=symbol,
            provider_description=description,
            resolution_stage=stage,
            evidence_refs=(
                "artifact:11125412870",
                "run:36775635034",
            ),
        )
        baseline = diagnose_mapping(
            expectation,
            MappingObservation(
                provider=provider,
                provider_symbol_id=symbol_id,
                provider_symbol=symbol,
                provider_description=description,
            ),
        )

        if stage in KNOWN_MAPPING_STAGES:
            if baseline.state is not MappingDiagnosticState.MATCH:
                baseline_mismatch_count += 1
            else:
                match_count += 1
            injected = diagnose_mapping(
                expectation,
                MappingObservation(
                    provider=provider,
                    provider_symbol_id=symbol_id,
                    provider_symbol=f"{symbol}__INJECTED_DRIFT",
                    provider_description=description,
                ),
            )
            injected_mismatch_detected += int(
                injected.state is MappingDiagnosticState.MISMATCH
                and "PROVIDER_SYMBOL_MISMATCH" in injected.reason_codes
            )
        else:
            if baseline.state is not MappingDiagnosticState.UNKNOWN:
                raise AssertionError("unresolved identity became false mapping claim")
            unknown_count += 1

    if (match_count, unknown_count) != (90, 87):
        raise AssertionError(
            f"unexpected known/unknown identity partition: {match_count}/{unknown_count}"
        )
    diagnostic_pass = (
        baseline_mismatch_count == 0
        and injected_mismatch_detected == match_count
    )
    open_after = tuple(
        item for item in prior_open if item != "MAPPING_ERRORS"
    )
    expected_after = (
        "BROKER_PROVIDER_MISMATCH",
        "CLOCK_DRIFT",
        "EXECUTION_QUALITY_DETERIORATION",
        "MODEL_RUNTIME_INSTABILITY",
    )
    if open_after != expected_after:
        raise AssertionError(f"unexpected post-mapping gaps: {open_after}")

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC28_MAPPING_ERROR_DIAGNOSTIC_REAL_BOUND_PASS_OPEN_4"
            if diagnostic_pass
            else "MC28_MAPPING_ERROR_DIAGNOSTIC_FAILED"
        ),
        "b06_identity_frontier_complete": False,
        "sensor_count": 177,
        "known_mapping_count": match_count,
        "identity_unknown_count": unknown_count,
        "baseline_mapping_mismatch_count": baseline_mismatch_count,
        "injected_mapping_error_count": match_count,
        "injected_mapping_error_detected_count": injected_mismatch_detected,
        "mapping_error_diagnostic_bound": diagnostic_pass,
        "unknown_identity_preserved_as_unknown": True,
        "automatic_identity_inference_used": False,
        "prior_open_diagnostic_count": len(prior_open),
        "open_diagnostic_count": len(open_after),
        "open_diagnostics": open_after,
        "mapping_errors_open": False,
        "mc28_completed_and_proven": False,
        "broker_mutation_authority": False,
        "execution_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
