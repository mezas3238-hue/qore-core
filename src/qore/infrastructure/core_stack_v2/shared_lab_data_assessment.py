"""Strict no-pooled-rescue assessment for the Shared Lab data reality lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DataRealityGate(StrEnum):
    GOLDEN_TRACE = "GOLDEN_TRACE"
    SENSOR_FAILURE_INJECTION = "SENSOR_FAILURE_INJECTION"
    TIMESTAMP_CHRONOLOGY = "TIMESTAMP_CHRONOLOGY"
    PROVIDER_INTEGRITY = "PROVIDER_INTEGRITY"
    CANONICAL_IDENTITY = "CANONICAL_IDENTITY"
    MARKET_HOURS = "MARKET_HOURS"
    DATA_COMPLETENESS = "DATA_COMPLETENESS"
    DATA_QUALITY = "DATA_QUALITY"
    PROVENANCE = "PROVENANCE"
    REDUNDANCY_RESILIENCE = "REDUNDANCY_RESILIENCE"
    FAIL_DEGRADED = "FAIL_DEGRADED"
    LEAKAGE_FIREWALL = "LEAKAGE_FIREWALL"
    DETERMINISTIC_REPLAY = "DETERMINISTIC_REPLAY"
    L10_KNOWN_FAILURE_DETECTION = "L10_KNOWN_FAILURE_DETECTION"


REQUIRED_DATA_REALITY_GATES: tuple[DataRealityGate, ...] = tuple(DataRealityGate)


@dataclass(frozen=True, slots=True)
class GateEvidence:
    gate: DataRealityGate
    passed: bool
    evidence_id: str
    receipt_fingerprint: str

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if len(self.receipt_fingerprint) != 64:
            raise ValueError("receipt_fingerprint must be sha256 hex")


@dataclass(frozen=True, slots=True)
class DataRealityAssessment:
    required_gates: tuple[DataRealityGate, ...]
    passed_gates: tuple[DataRealityGate, ...]
    failed_gates: tuple[DataRealityGate, ...]
    missing_gates: tuple[DataRealityGate, ...]
    evidence_count: int
    functional_complete: bool
    productive_authority: bool = False
    certification_authority: bool = False

    def __post_init__(self) -> None:
        if self.productive_authority or self.certification_authority:
            raise ValueError("data laboratory has no productive or certification authority")


def assess_data_reality(evidence: tuple[GateEvidence, ...]) -> DataRealityAssessment:
    by_gate: dict[DataRealityGate, GateEvidence] = {}
    for item in evidence:
        if item.gate in by_gate:
            raise ValueError(f"duplicate gate evidence: {item.gate}")
        by_gate[item.gate] = item

    missing = tuple(g for g in REQUIRED_DATA_REALITY_GATES if g not in by_gate)
    failed = tuple(
        g for g in REQUIRED_DATA_REALITY_GATES
        if g in by_gate and not by_gate[g].passed
    )
    passed = tuple(
        g for g in REQUIRED_DATA_REALITY_GATES
        if g in by_gate and by_gate[g].passed
    )
    complete = not missing and not failed and len(passed) == len(REQUIRED_DATA_REALITY_GATES)

    return DataRealityAssessment(
        required_gates=REQUIRED_DATA_REALITY_GATES,
        passed_gates=passed,
        failed_gates=failed,
        missing_gates=missing,
        evidence_count=len(evidence),
        functional_complete=complete,
    )
