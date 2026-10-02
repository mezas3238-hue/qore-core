"""MC-20 operational telemetry bridge for descriptive stability states.

This bridge consumes normalized read-only system observations from an immutable
upstream evidence artifact. It never infers Core, Provider, or Broker health
from market prices.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.stability_engine import (
    StabilityDomain,
    StabilityEvidence,
)


class OperationalSystemKind(StrEnum):
    CORE_COMPONENT = "CORE_COMPONENT"
    PROVIDER = "PROVIDER"
    BROKER = "BROKER"


class OperationalSystemState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class OperationalSystemObservation:
    system_id: str
    system_kind: OperationalSystemKind
    state: OperationalSystemState
    fingerprint_sha256: str
    mutation_authority: bool = False
    restart_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.system_id.strip():
            raise ValueError("operational observation requires system_id")
        if len(self.fingerprint_sha256) != 64:
            raise ValueError("operational observation requires sha256 fingerprint")
        if (
            self.mutation_authority
            or self.restart_authority
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("Shared operational observation must be read-only")


def _severity_bps(state: OperationalSystemState) -> int:
    if state is OperationalSystemState.HEALTHY:
        return 0
    if state is OperationalSystemState.DEGRADED:
        return 7_000
    return 10_000


def _evidence(
    *,
    domain: StabilityDomain,
    observations: tuple[OperationalSystemObservation, ...],
    evidence_refs: tuple[str, ...],
) -> StabilityEvidence:
    if not observations:
        raise ValueError("operational stability domain requires observations")
    severity = max(_severity_bps(item.state) for item in observations)
    dislocation = 10_000 if severity == 10_000 else 0
    refs = tuple(
        sorted(
            set(evidence_refs)
            | {
                f"system:{item.system_id}:{item.fingerprint_sha256}"
                for item in observations
            }
        )
    )
    return StabilityEvidence(
        domain=domain,
        evidence_available=True,
        stability_bps=10_000 - severity,
        degradation_bps=severity,
        recovery_bps=0,
        dislocation_bps=dislocation,
        evidence_refs=refs,
    )


def operational_stability_evidence(
    observations: tuple[OperationalSystemObservation, ...],
    *,
    evidence_refs: tuple[str, ...],
) -> tuple[StabilityEvidence, StabilityEvidence]:
    """Build separate QORE Core and Provider/Broker stability evidence."""

    kinds = [item.system_kind for item in observations]
    if kinds.count(OperationalSystemKind.CORE_COMPONENT) != 1:
        raise ValueError("exactly one Core component observation is required")
    if kinds.count(OperationalSystemKind.PROVIDER) != 1:
        raise ValueError("exactly one Provider observation is required")
    if kinds.count(OperationalSystemKind.BROKER) != 1:
        raise ValueError("exactly one Broker observation is required")
    if (
        not evidence_refs
        or evidence_refs != tuple(sorted(set(evidence_refs)))
    ):
        raise ValueError("operational evidence refs must be canonical")

    core = tuple(
        item
        for item in observations
        if item.system_kind is OperationalSystemKind.CORE_COMPONENT
    )
    provider_broker = tuple(
        item
        for item in observations
        if item.system_kind
        in {OperationalSystemKind.PROVIDER, OperationalSystemKind.BROKER}
    )
    return (
        _evidence(
            domain=StabilityDomain.QORE_CORE,
            observations=core,
            evidence_refs=evidence_refs,
        ),
        _evidence(
            domain=StabilityDomain.PROVIDER_BROKER,
            observations=provider_broker,
            evidence_refs=evidence_refs,
        ),
    )
