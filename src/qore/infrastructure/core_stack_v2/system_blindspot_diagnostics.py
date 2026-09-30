"""MC-28 Standard 006 diagnostic taxonomy.

This module is deliberately fail-closed. A diagnostic category is not complete
because a neighboring health signal looks normal; each required category needs
its own explicit evidence binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SystemDiagnosticKind(StrEnum):
    FEED_DEGRADATION = "FEED_DEGRADATION"
    DATA_HOLES = "DATA_HOLES"
    CLOCK_DRIFT = "CLOCK_DRIFT"
    LATENCY_ANOMALIES = "LATENCY_ANOMALIES"
    MAPPING_ERRORS = "MAPPING_ERRORS"
    BROKER_PROVIDER_MISMATCH = "BROKER_PROVIDER_MISMATCH"
    EXECUTION_QUALITY_DETERIORATION = "EXECUTION_QUALITY_DETERIORATION"
    MODEL_RUNTIME_INSTABILITY = "MODEL_RUNTIME_INSTABILITY"


class SystemDiagnosticState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SystemDiagnosticEvidence:
    kind: SystemDiagnosticKind
    state: SystemDiagnosticState
    severity_bps: int
    observed_at: datetime
    evidence_cutoff_at: datetime
    evidence_refs: tuple[str, ...]
    diagnostic_evidence_bound: bool
    mutation_authority: bool = False
    restart_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("diagnostic observed_at must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("diagnostic evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future diagnostic evidence is forbidden")
        if type(self.severity_bps) is not int or not 0 <= self.severity_bps <= 10_000:
            raise ValueError("diagnostic severity must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("diagnostic evidence refs must be canonical")
        if not self.diagnostic_evidence_bound:
            if self.state is not SystemDiagnosticState.UNKNOWN:
                raise ValueError("unbound diagnostic must remain UNKNOWN")
            if self.severity_bps != 0:
                raise ValueError("unbound diagnostic cannot invent severity")
        if (
            self.mutation_authority
            or self.restart_authority
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("MC28 diagnostics are observational only")


@dataclass(frozen=True, slots=True)
class SecondOrderSystemDiagnosticSnapshot:
    diagnostics: tuple[SystemDiagnosticEvidence, ...]
    open_diagnostics: tuple[SystemDiagnosticKind, ...]
    complete: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.diagnostics, key=lambda item: item.kind.value))
        if self.diagnostics != ordered:
            raise ValueError("MC28 diagnostics must be canonical")
        kinds = {item.kind for item in self.diagnostics}
        if kinds != set(SystemDiagnosticKind):
            raise ValueError("MC28 requires all Standard 006 diagnostic kinds")
        expected_open = tuple(
            item.kind
            for item in self.diagnostics
            if not item.diagnostic_evidence_bound
            or item.state is SystemDiagnosticState.UNKNOWN
        )
        if self.open_diagnostics != expected_open:
            raise ValueError("MC28 open diagnostic inventory drift")
        if self.complete != (not self.open_diagnostics):
            raise ValueError("MC28 completion must equal zero open diagnostics")
        if self.productive_authority:
            raise ValueError("MC28 cannot acquire productive authority")


def build_second_order_system_diagnostics(
    diagnostics: tuple[SystemDiagnosticEvidence, ...],
) -> SecondOrderSystemDiagnosticSnapshot:
    ordered = tuple(sorted(diagnostics, key=lambda item: item.kind.value))
    open_diagnostics = tuple(
        item.kind
        for item in ordered
        if not item.diagnostic_evidence_bound
        or item.state is SystemDiagnosticState.UNKNOWN
    )
    return SecondOrderSystemDiagnosticSnapshot(
        diagnostics=ordered,
        open_diagnostics=open_diagnostics,
        complete=not open_diagnostics,
    )
