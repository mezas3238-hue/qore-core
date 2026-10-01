"""MC-28 explicit broker/provider mismatch diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BrokerProviderMismatchState(StrEnum):
    CONSISTENT = "CONSISTENT"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class BrokerProviderEvidence:
    provider_state: str
    broker_state: str
    provider_catalog_matches_frozen: bool | None
    provider_error_count: int | None
    broker_error_count: int | None
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("provider_error_count", "broker_error_count"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not int or value < 0
            ):
                raise ValueError(f"{name} must be non-negative int or None")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("broker/provider evidence refs must be canonical")


@dataclass(frozen=True, slots=True)
class BrokerProviderMismatchDiagnostic:
    state: BrokerProviderMismatchState
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    broker_mutation_authority: bool = False
    restart_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reason_codes:
            raise ValueError("broker/provider diagnostic requires reasons")
        if (
            self.broker_mutation_authority
            or self.restart_authority
            or self.order_authority
            or self.risk_authority
        ):
            raise ValueError("broker/provider diagnostic is observational only")


def diagnose_broker_provider_mismatch(
    evidence: BrokerProviderEvidence,
) -> BrokerProviderMismatchDiagnostic:
    known_states = {"HEALTHY", "DEGRADED", "UNAVAILABLE"}
    if (
        evidence.provider_state not in known_states
        or evidence.broker_state not in known_states
        or evidence.provider_catalog_matches_frozen is None
        or evidence.provider_error_count is None
        or evidence.broker_error_count is None
    ):
        return BrokerProviderMismatchDiagnostic(
            state=BrokerProviderMismatchState.UNKNOWN,
            reason_codes=("BROKER_PROVIDER_EVIDENCE_INCOMPLETE",),
            evidence_refs=evidence.evidence_refs,
        )

    reasons: list[str] = []
    if evidence.provider_state != evidence.broker_state:
        reasons.append("PROVIDER_BROKER_STATE_DIVERGENCE")
    if not evidence.provider_catalog_matches_frozen:
        reasons.append("PROVIDER_CATALOG_FROZEN_BINDING_MISMATCH")
    if (evidence.provider_error_count > 0) != (
        evidence.broker_error_count > 0
    ):
        reasons.append("PROVIDER_BROKER_ERROR_ASYMMETRY")

    if reasons:
        return BrokerProviderMismatchDiagnostic(
            state=BrokerProviderMismatchState.MISMATCH,
            reason_codes=tuple(sorted(reasons)),
            evidence_refs=evidence.evidence_refs,
        )
    return BrokerProviderMismatchDiagnostic(
        state=BrokerProviderMismatchState.CONSISTENT,
        reason_codes=("PROVIDER_BROKER_OBSERVATIONS_CONSISTENT",),
        evidence_refs=evidence.evidence_refs,
    )
