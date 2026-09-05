from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboHealthState(StrEnum):
    """Coarse operational health of a capability or the whole core."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboCapabilityHealth:
    """Per-capability operational health, bound to explicit evidence refs only.

    The refs record *why* inputs are stale/missing or reconciliation is gaped;
    they never encode a silent repair of certified code/config.
    """

    capability_code: str
    availability: CiboHealthState
    stale_inputs: tuple[CiboEvidenceRef, ...]
    missing_inputs: tuple[CiboEvidenceRef, ...]
    reconciliation_gaps: tuple[CiboEvidenceRef, ...]
    evidence_pipeline_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_code",
            _validate_code(self.capability_code, field_name="capability code"),
        )
        if type(self.availability) is not CiboHealthState:
            raise CiboFunctionalValidationError(
                "capability health requires CiboHealthState"
            )
        object.__setattr__(
            self,
            "stale_inputs",
            _validate_evidence_refs(self.stale_inputs, field_name="stale inputs"),
        )
        object.__setattr__(
            self,
            "missing_inputs",
            _validate_evidence_refs(self.missing_inputs, field_name="missing inputs"),
        )
        object.__setattr__(
            self,
            "reconciliation_gaps",
            _validate_evidence_refs(
                self.reconciliation_gaps,
                field_name="reconciliation gaps",
            ),
        )
        object.__setattr__(
            self,
            "evidence_pipeline_code",
            _validate_code(
                self.evidence_pipeline_code,
                field_name="evidence pipeline code",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.capability_code,
            self.availability.value,
            tuple(item.logical_values() for item in self.stale_inputs),
            tuple(item.logical_values() for item in self.missing_inputs),
            tuple(item.logical_values() for item in self.reconciliation_gaps),
            self.evidence_pipeline_code,
        )


def _derive_overall(
    capabilities: tuple[CiboCapabilityHealth, ...],
    evidence: CiboFunctionalEvidence,
) -> CiboHealthState:
    """Derive the coarse overall health state from capabilities and evidence.

    A BLOCKED capability dominates; then any degraded/stale/missing/gapped
    capability; only fully sufficient evidence over healthy capabilities yields
    HEALTHY. This is the single deterministic derivation shared by the builder and
    the constructor, so a stronger semantic state cannot be admitted by direct
    construction.
    """
    if any(
        item.availability is CiboHealthState.BLOCKED for item in capabilities
    ):
        return CiboHealthState.BLOCKED
    if any(
        item.availability is CiboHealthState.DEGRADED
        or item.stale_inputs
        or item.missing_inputs
        or item.reconciliation_gaps
        for item in capabilities
    ):
        return CiboHealthState.DEGRADED
    if evidence.status is CiboEvidenceStatus.SUFFICIENT:
        return CiboHealthState.HEALTHY
    return CiboHealthState.DEGRADED


@dataclass(frozen=True, slots=True)
class CiboHealthSnapshot:
    """An operational health snapshot. It escalates/requests, never repairs."""

    capabilities: tuple[CiboCapabilityHealth, ...]
    overall: CiboHealthState
    evidence: CiboFunctionalEvidence
    blockers: tuple[str, ...]
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.capabilities, tuple) or not self.capabilities or any(
            not isinstance(item, CiboCapabilityHealth) for item in self.capabilities
        ):
            raise CiboFunctionalValidationError(
                "health snapshot requires a non-empty tuple of CiboCapabilityHealth"
            )
        for item in self.capabilities:
            CiboCapabilityHealth.__post_init__(item)
        codes = tuple(item.capability_code for item in self.capabilities)
        if len(set(codes)) != len(codes):
            raise CiboFunctionalValidationError(
                "health snapshot capability codes must be unique"
            )
        object.__setattr__(
            self,
            "capabilities",
            tuple(sorted(self.capabilities, key=lambda item: item.capability_code)),
        )
        if type(self.overall) is not CiboHealthState:
            raise CiboFunctionalValidationError(
                "health snapshot requires CiboHealthState"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "health snapshot requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        object.__setattr__(
            self,
            "blockers",
            _validate_codes(self.blockers, field_name="health snapshot blockers"),
        )
        _validate_timestamp(self.assessed_at, field_name="health snapshot assessed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "health snapshot requires CiboFunctionalAuthority"
            )
        if self.overall is CiboHealthState.HEALTHY:
            if self.authority is not CiboFunctionalAuthority.OBSERVATION:
                raise CiboFunctionalValidationError(
                    "healthy health snapshot requires OBSERVATION authority"
                )
        elif self.authority is not CiboFunctionalAuthority.ESCALATION:
            raise CiboFunctionalValidationError(
                "degraded/blocked health snapshot requires ESCALATION authority"
            )
        if self.overall is CiboHealthState.BLOCKED and not self.blockers:
            raise CiboFunctionalValidationError(
                "blocked health snapshot requires non-empty blockers"
            )
        # Constructor/deriver parity: direct construction must not admit a stronger
        # overall state than the deterministic capability/evidence derivation.
        expected = _derive_overall(self.capabilities, self.evidence)
        if self.overall is not expected:
            raise CiboFunctionalValidationError(
                "health snapshot overall must equal the capability-derived state"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.capabilities),
            self.overall.value,
            self.evidence.logical_values(),
            self.blockers,
            self.assessed_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboCoreHealth:
    """Deterministic, stateless operational health assessment policy.

    It computes a coarse overall state and an authority ceiling. A non-HEALTHY
    snapshot is an ESCALATION and a BLOCKED snapshot must carry blockers; it never
    silently repairs certified code/config (no such field exists).
    """

    def assess(
        self,
        capabilities: tuple[CiboCapabilityHealth, ...],
        *,
        evidence: CiboFunctionalEvidence,
        blockers: tuple[str, ...],
        assessed_at: datetime,
    ) -> Result[CiboHealthSnapshot, CiboFunctionalError]:
        if not isinstance(capabilities, tuple) or not capabilities or any(
            not isinstance(item, CiboCapabilityHealth) for item in capabilities
        ):
            return Failure(
                CiboFunctionalValidationError(
                    "assess requires a non-empty tuple of CiboCapabilityHealth"
                )
            )
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError(
                    "assess requires CiboFunctionalEvidence"
                )
            )
        try:
            for item in capabilities:
                CiboCapabilityHealth.__post_init__(item)
            CiboFunctionalEvidence.__post_init__(evidence)
            _validate_timestamp(assessed_at, field_name="assessed_at")
            normalized_blockers = _validate_codes(blockers, field_name="blockers")
        except CiboFunctionalError as error:
            return Failure(error)
        codes = tuple(item.capability_code for item in capabilities)
        if len(set(codes)) != len(codes):
            return Failure(
                CiboFunctionalValidationError(
                    "health assessment capability codes must be unique"
                )
            )

        overall = _derive_overall(capabilities, evidence)

        authority = (
            CiboFunctionalAuthority.OBSERVATION
            if overall is CiboHealthState.HEALTHY
            else CiboFunctionalAuthority.ESCALATION
        )

        try:
            return Success(
                CiboHealthSnapshot(
                    capabilities=capabilities,
                    overall=overall,
                    evidence=evidence,
                    blockers=normalized_blockers,
                    assessed_at=assessed_at,
                    authority=authority,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
