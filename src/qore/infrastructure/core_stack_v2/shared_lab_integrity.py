"""Executable L10 fault detector for QORE Shared Lab core/cognitive lane."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab import (
    CapabilityLabRecord,
    InfluenceEdge,
    LabFault,
    LabIntegrityReceipt,
)


@dataclass(frozen=True, slots=True)
class FaultScenario:
    fault: LabFault
    record: CapabilityLabRecord | None = None
    edge: InfluenceEdge | None = None
    claimed_pass: bool = False
    duplicate_output_count: int = 1


def detect_fault(scenario: FaultScenario) -> bool:
    record = scenario.record
    edge = scenario.edge

    if scenario.fault is LabFault.DEAD_NATIVE_ENGINE:
        return record is not None and (
            not record.native_engine.native_engine_exists
            or not record.native_engine.native_engine_called
        )
    if scenario.fault is LabFault.ADAPTER_SUBSTITUTED_FOR_ENGINE:
        return record is not None and (
            record.native_engine.adapter_only
            or record.native_engine.engine_kind.value == "ADAPTER"
        )
    if scenario.fault is LabFault.FAKE_CONSUMER:
        return edge is not None and (not edge.observed or not edge.consumed or not edge.fingerprint_match)
    if scenario.fault is LabFault.FUTURE_LEAKAGE:
        return record is not None and not record.leakage_free
    if scenario.fault is LabFault.DUPLICATED_OUTPUT:
        return scenario.duplicate_output_count > 1
    if scenario.fault is LabFault.IGNORED_COGNITION:
        return record is not None and (
            record.efficiency.invocation_count > 0
            and record.efficiency.downstream_changed_count == 0
            and not record.efficiency.cognitively_live
        )
    if scenario.fault is LabFault.FAKE_PASS:
        return record is not None and scenario.claimed_pass and not record.phase_proven

    # Data/sensor-lane faults are intentionally delegated to Architect 2's
    # dedicated harness. Core L10 must not fake detection it cannot perform.
    return False


def run_l10_core_integrity(
    scenarios: tuple[FaultScenario, ...],
) -> LabIntegrityReceipt:
    if not scenarios:
        raise ValueError("L10 integrity requires deliberate fault scenarios")
    injected = tuple(item.fault for item in scenarios)
    detected = tuple(item.fault for item in scenarios if detect_fault(item))
    return LabIntegrityReceipt(injected_faults=injected, detected_faults=detected)
