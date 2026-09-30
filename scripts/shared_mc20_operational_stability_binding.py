#!/usr/bin/env python3
"""Close MC-20 by composing sealed A foundation with sealed B telemetry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.stability_engine import (
    StabilityDomain,
    StabilityState,
    assess_stability_channel,
)
from qore.infrastructure.core_stack_v2.stability_operational_binding import (
    OperationalSystemKind,
    OperationalSystemObservation,
    OperationalSystemState,
    operational_stability_evidence,
)

IDENTITY = "QORE_SHARED_MC20_OPERATIONAL_STABILITY_BINDING_001"
A_FOUNDATION_RUN_ID = 36764891693
A_FOUNDATION_ARTIFACT_ID = 11120781116
B_RUNTIME_RUN_ID = 36764365409
B_RUNTIME_ARTIFACT_ID = 11120521150


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, Any], payload)


def _observation(row: dict[str, Any]) -> OperationalSystemObservation:
    return OperationalSystemObservation(
        system_id=str(row["system_id"]),
        system_kind=OperationalSystemKind(str(row["system_kind"])),
        state=OperationalSystemState(str(row["state"])),
        fingerprint_sha256=str(row["fingerprint_sha256"]),
        mutation_authority=bool(row["mutation_authority"]),
        restart_authority=bool(row["restart_authority"]),
        order_authority=bool(row["order_authority"]),
        risk_authority=bool(row["risk_authority"]),
        sizing_authority=bool(row["sizing_authority"]),
        capital_authority=bool(row["capital_authority"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-foundation", type=Path, required=True)
    parser.add_argument("--b-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    foundation = _load(args.a_foundation)
    runtime = _load(args.b_runtime)

    if foundation.get("status") != (
        "MC20_STABILITY_ENGINE_MARKET_COGNITION_SYSTEMIC_REAL_BOUND_PASS"
    ):
        raise AssertionError("sealed A MC20 foundation did not pass")
    if foundation.get("domains_distinct") is not True:
        raise AssertionError("A MC20 domains were not distinct")
    if foundation.get("market_price_used_as_core_health_proxy") is not False:
        raise AssertionError("Core health proxy law violated")
    if foundation.get("market_price_used_as_provider_health_proxy") is not False:
        raise AssertionError("Provider health proxy law violated")

    if runtime.get("status") != "REAL_READ_ONLY_CORE_BROKER_REPLICATION_PASS":
        raise AssertionError("sealed B operational replication did not pass")
    if runtime.get("core_runtime_deterministic_rebuild") is not True:
        raise AssertionError("B Core runtime replay was not deterministic")
    if runtime.get("read_only_message_firewall") is not True:
        raise AssertionError("B operational evidence was not read-only")
    if runtime.get("productive_authority") is not False:
        raise AssertionError("B operational evidence carried authority")

    raw = runtime.get("system_assessments")
    if not isinstance(raw, list):
        raise AssertionError("B system assessments missing")
    rows = tuple(
        _observation(cast(dict[str, Any], row))
        for row in raw
        if isinstance(row, dict)
    )
    evidence = operational_stability_evidence(
        rows,
        evidence_refs=(
            f"artifact:{B_RUNTIME_ARTIFACT_ID}",
            f"run:{B_RUNTIME_RUN_ID}",
        ),
    )
    channels = tuple(assess_stability_channel(item) for item in evidence)
    by_domain = {item.domain: item for item in channels}

    operational_bound = (
        by_domain[StabilityDomain.QORE_CORE].state is not StabilityState.UNKNOWN
        and by_domain[StabilityDomain.PROVIDER_BROKER].state
        is not StabilityState.UNKNOWN
    )
    authority_free = all(
        not item.trading_command
        and not item.execution_authority
        and not item.risk_authority
        and not item.sizing_authority
        for item in channels
    )
    completed = operational_bound and authority_free

    payload = {
        "identity": IDENTITY,
        "status": (
            "MC20_STABILITY_ENGINE_COMPLETED_AND_PROVEN"
            if completed
            else "MC20_OPERATIONAL_BINDING_FAILED"
        ),
        "a_foundation_run_id": A_FOUNDATION_RUN_ID,
        "a_foundation_artifact_id": A_FOUNDATION_ARTIFACT_ID,
        "b_runtime_run_id": B_RUNTIME_RUN_ID,
        "b_runtime_artifact_id": B_RUNTIME_ARTIFACT_ID,
        "market_cognition_systemic_real_bound": True,
        "qore_core_operational_telemetry_bound": operational_bound,
        "provider_broker_operational_telemetry_bound": operational_bound,
        "qore_core_state": by_domain[
            StabilityDomain.QORE_CORE
        ].state.value,
        "provider_broker_state": by_domain[
            StabilityDomain.PROVIDER_BROKER
        ].state.value,
        "domains_distinct": True,
        "market_price_used_as_core_health_proxy": False,
        "market_price_used_as_provider_health_proxy": False,
        "same_timestamp_cross_domain_fusion_claimed": False,
        "evidence_composition": (
            "SEALED_CAPABILITY_PROOF_WITHOUT_SYNTHETIC_TEMPORAL_FUSION"
        ),
        "states_are_trading_commands": False,
        "productive_authority": False,
        "mc20_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
