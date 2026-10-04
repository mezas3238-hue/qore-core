"""MC-28 explicit model/runtime instability diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RuntimeInstabilityState(StrEnum):
    STABLE = "STABLE"
    INSTABILITY = "INSTABILITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuntimeStabilityEvidence:
    core_runtime_executed: bool
    deterministic_rebuild: bool
    core_system_state: str
    error_count: int
    snapshot_fingerprint_sha256: str
    checkpoint_fingerprint_sha256: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.error_count) is not int or self.error_count < 0:
            raise ValueError("runtime error_count must be non-negative int")
        for value in (
            self.snapshot_fingerprint_sha256,
            self.checkpoint_fingerprint_sha256,
        ):
            if len(value) != 64:
                raise ValueError("runtime evidence requires sha256 fingerprints")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("runtime evidence refs must be canonical")


@dataclass(frozen=True, slots=True)
class RuntimeInstabilityDiagnostic:
    state: RuntimeInstabilityState
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    restart_authority: bool = False
    mutation_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reason_codes:
            raise ValueError("runtime diagnostic requires reason codes")
        if (
            self.restart_authority
            or self.mutation_authority
            or self.execution_authority
            or self.risk_authority
        ):
            raise ValueError("runtime instability diagnostic is observational only")


def diagnose_runtime_instability(
    evidence: RuntimeStabilityEvidence,
) -> RuntimeInstabilityDiagnostic:
    if not evidence.core_runtime_executed or evidence.core_system_state == "UNKNOWN":
        return RuntimeInstabilityDiagnostic(
            state=RuntimeInstabilityState.UNKNOWN,
            reason_codes=("RUNTIME_OBSERVABILITY_INSUFFICIENT",),
            evidence_refs=evidence.evidence_refs,
        )

    reasons: list[str] = []
    if not evidence.deterministic_rebuild:
        reasons.append("DETERMINISTIC_REBUILD_DRIFT")
    if evidence.error_count > 0:
        reasons.append("RUNTIME_ERROR_COUNT_NONZERO")
    if evidence.core_system_state != "HEALTHY":
        reasons.append("CORE_SYSTEM_STATE_NOT_HEALTHY")

    if reasons:
        return RuntimeInstabilityDiagnostic(
            state=RuntimeInstabilityState.INSTABILITY,
            reason_codes=tuple(sorted(reasons)),
            evidence_refs=evidence.evidence_refs,
        )
    return RuntimeInstabilityDiagnostic(
        state=RuntimeInstabilityState.STABLE,
        reason_codes=("DETERMINISTIC_REBUILD_AND_HEALTHY_RUNTIME",),
        evidence_refs=evidence.evidence_refs,
    )
