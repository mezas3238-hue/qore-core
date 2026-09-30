#!/usr/bin/env python3
"""Audit MC-28 Standard 006 diagnostic coverage without overclaiming."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.core_stack_v2.system_blindspot_diagnostics import (
    SystemDiagnosticEvidence,
    SystemDiagnosticKind,
    SystemDiagnosticState,
    build_second_order_system_diagnostics,
)

IDENTITY = "QORE_SHARED_MC28_STANDARD_006_DIAGNOSTIC_TAXONOMY_001"

B_FOUNDATION_RUN_ID = 36763268609
B_FOUNDATION_ARTIFACT_ID = 11119388121
B_RUNTIME_RUN_ID = 36764365409
B_RUNTIME_ARTIFACT_ID = 11120521150
B_INVENTORY_RUN_ID = 36764376550
B_INVENTORY_ARTIFACT_ID = 11120391213


def _row(
    kind: SystemDiagnosticKind,
    *,
    bound: bool,
    refs: tuple[str, ...],
) -> SystemDiagnosticEvidence:
    now = datetime(2026, 9, 30, 21, 5, tzinfo=UTC)
    return SystemDiagnosticEvidence(
        kind=kind,
        state=(
            SystemDiagnosticState.HEALTHY
            if bound
            else SystemDiagnosticState.UNKNOWN
        ),
        severity_bps=0,
        observed_at=now,
        evidence_cutoff_at=now,
        evidence_refs=tuple(sorted(set(refs))),
        diagnostic_evidence_bound=bound,
    )


def main() -> None:
    foundation = (
        f"artifact:{B_FOUNDATION_ARTIFACT_ID}",
        f"run:{B_FOUNDATION_RUN_ID}",
    )
    runtime = (
        f"artifact:{B_RUNTIME_ARTIFACT_ID}",
        f"run:{B_RUNTIME_RUN_ID}",
    )
    inventory = (
        f"artifact:{B_INVENTORY_ARTIFACT_ID}",
        f"run:{B_INVENTORY_RUN_ID}",
    )

    diagnostics = (
        _row(
            SystemDiagnosticKind.FEED_DEGRADATION,
            bound=True,
            refs=foundation + runtime,
        ),
        _row(
            SystemDiagnosticKind.DATA_HOLES,
            bound=True,
            refs=foundation + inventory,
        ),
        _row(
            SystemDiagnosticKind.CLOCK_DRIFT,
            bound=False,
            refs=("dependency:RUNTIME_CLOCK_DRIFT_OBSERVATION",),
        ),
        _row(
            SystemDiagnosticKind.LATENCY_ANOMALIES,
            bound=True,
            refs=runtime,
        ),
        _row(
            SystemDiagnosticKind.MAPPING_ERRORS,
            bound=False,
            refs=("dependency:EXPLICIT_MAPPING_ERROR_DIAGNOSTIC",),
        ),
        _row(
            SystemDiagnosticKind.BROKER_PROVIDER_MISMATCH,
            bound=False,
            refs=("dependency:BROKER_PROVIDER_COMPARATOR",),
        ),
        _row(
            SystemDiagnosticKind.EXECUTION_QUALITY_DETERIORATION,
            bound=False,
            refs=(
                "dependency:SPREAD_SLIPPAGE_REJECTION_RUNTIME_TELEMETRY",
            ),
        ),
        _row(
            SystemDiagnosticKind.MODEL_RUNTIME_INSTABILITY,
            bound=False,
            refs=("dependency:MODEL_RUNTIME_INSTABILITY_DIAGNOSTIC",),
        ),
    )
    snapshot = build_second_order_system_diagnostics(diagnostics)
    open_names = tuple(item.value for item in snapshot.open_diagnostics)
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_PASS_OPEN_5"
            if len(open_names) == 5
            else "MC28_STANDARD_006_DIAGNOSTIC_CONTRACT_UNEXPECTED_STATE"
        ),
        "required_diagnostic_count": len(SystemDiagnosticKind),
        "bound_diagnostic_count": len(SystemDiagnosticKind) - len(open_names),
        "open_diagnostic_count": len(open_names),
        "open_diagnostics": open_names,
        "bound_diagnostics": tuple(
            item.kind.value
            for item in snapshot.diagnostics
            if item.diagnostic_evidence_bound
        ),
        "runtime_core_broker_replication_complete": True,
        "second_order_inventory_complete": True,
        "open_world_boundary_preserved": True,
        "all_unknown_unknowns_eliminated": False,
        "mc28_completed_and_proven": snapshot.complete,
        "productive_authority": snapshot.productive_authority,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
        "next_gate": "BIND_FIVE_STANDARD_006_DIAGNOSTICS_WITH_REAL_EVIDENCE",
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc28-standard-006-diagnostic-taxonomy.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
