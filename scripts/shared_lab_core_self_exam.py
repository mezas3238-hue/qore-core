#!/usr/bin/env python3
"""Execute the QORE Shared Lab core-lane self exam and materialize a receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    CapabilityLabRecord,
    EfficiencyReceipt,
    EngineKind,
    InfluenceEdge,
    LabFault,
    NativeEngineReceipt,
    SharedLabLevel,
    TemporalDatumReceipt,
)
from qore.infrastructure.core_stack_v2.shared_lab_authority import (
    AuthorityIsolationReceipt,
    assess_authority_isolation,
)
from qore.infrastructure.core_stack_v2.shared_lab_integrity import (
    FaultScenario,
    run_l10_core_integrity,
)
from qore.infrastructure.core_stack_v2.shared_lab_tools import (
    default_shared_lab_registry,
    registry_fingerprint,
    validate_l10_tool_coverage,
)


def _record(
    *,
    native: bool = True,
    changed: int = 2,
    future: bool = False,
) -> CapabilityLabRecord:
    fingerprint = "a" * 64
    return CapabilityLabRecord(
        capability_id="SELF_EXAM_CAPABILITY",
        engineering_green=True,
        required_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        passed_levels=(SharedLabLevel.L0_STRUCTURAL_REALITY,),
        native_engine=NativeEngineReceipt(
            capability_id="SELF_EXAM_CAPABILITY",
            engine_id="self-exam-engine",
            engine_kind=EngineKind.NATIVE if native else EngineKind.ADAPTER,
            real_input=True,
            native_engine_exists=native,
            native_engine_called=native,
            typed_output_emitted=True,
            adapter_only=not native,
            downstream_native_consumer="SELF_EXAM_CONSUMER" if native else None,
        ),
        cables=(
            CableRealityReceipt(
                "SELF_EXAM_CAPABILITY",
                "SELF_EXAM_CONSUMER",
                fingerprint,
                fingerprint,
                True,
                True,
                changed > 0,
            ),
        ),
        efficiency=EfficiencyReceipt(
            "SELF_EXAM_CAPABILITY",
            10,
            8,
            8,
            changed,
            2,
            0,
            0,
            0.1 if changed else 0.0,
            0.0,
            0.1 if changed else 0.0,
            10,
            100,
        ),
        temporal_data=(
            TemporalDatumReceipt(
                "datum",
                1,
                5 if future else 2,
                3,
                6 if future else 4,
            ),
        ),
        mutation_pass=True,
        metamorphic_pass=True,
        ablation_pass=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    registry = default_shared_lab_registry()
    scenarios = (
        FaultScenario(LabFault.DEAD_NATIVE_ENGINE, record=_record(native=False)),
        FaultScenario(
            LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE,
            record=_record(native=False),
        ),
        FaultScenario(
            LabFault.FAKE_CONSUMER,
            edge=InfluenceEdge(
                producer="SELF_EXAM_PRODUCER",
                consumer="SELF_EXAM_CONSUMER",
                real=True,
                tested=True,
                observed=True,
                consumed=True,
                value_proven=False,
                fingerprint_match=False,
            ),
        ),
        FaultScenario(LabFault.FUTURE_LEAKAGE, record=_record(future=True)),
        FaultScenario(LabFault.DUPLICATED_OUTPUT, duplicate_output_count=2),
        FaultScenario(LabFault.IGNORED_COGNITION, record=_record(changed=0)),
        FaultScenario(
            LabFault.FAKE_PASS,
            record=_record(native=False),
            claimed_pass=True,
        ),
    )
    integrity = run_l10_core_integrity(scenarios)
    authority = assess_authority_isolation(
        (
            AuthorityIsolationReceipt(
                component_id="QORE_SHARED_LAB_CORE",
                requested_authorities=frozenset(),
                granted_authorities=frozenset(),
                read_only=True,
                research_only=True,
            ),
        )
    )
    payload = {
        "identity": "QORE_SHARED_LAB_CORE_SELF_EXAM_001",
        "tool_family_count": len(registry.list_tools()),
        "tool_registry_fingerprint": registry_fingerprint(registry),
        "l10_tool_coverage_missing": [
            fault.value for fault in validate_l10_tool_coverage(registry)
        ],
        "core_faults_injected": [fault.value for fault in integrity.injected_faults],
        "core_faults_detected": [fault.value for fault in integrity.detected_faults],
        "core_l10_pass": integrity.passed,
        "authority_isolation_pass": authority.all_components_authority_free,
        "core_lane_proven": (
            integrity.passed
            and authority.all_components_authority_free
            and not validate_l10_tool_coverage(registry)
        ),
        "global_l10_pass": False,
        "data_sensor_lane_required": True,
        "laboratory_available_for_shared_validation": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }
    if not payload["core_lane_proven"]:
        raise SystemExit("Shared Lab core self-exam failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
