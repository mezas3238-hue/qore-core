"""CF-01 Financial World Monitoring.

Deterministic reduction of explicit certified evidence assessments into a single
monitoring signal. The monitor never invents a market fact: SUFFICIENT evidence maps
to NO_MATERIAL_CHANGE, and a material change (MATERIAL_CHANGE / ANOMALY /
REGIME_SHIFT) can only ever be asserted by an explicit typed signal constructed
directly by a caller -- never by this reducer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    synthesize_evidence,
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


class CiboMonitoringSignal(StrEnum):
    """Signals the Financial World Monitor may conclude or a caller may assert."""

    MATERIAL_CHANGE = "material-change"
    ANOMALY = "anomaly"
    CONTRADICTION = "contradiction"
    REGIME_SHIFT = "regime-shift"
    STALE_EVIDENCE = "stale-evidence"
    EVIDENCE_GAP = "evidence-gap"
    NO_MATERIAL_CHANGE = "no-material-change"


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


def _validate_subject_refs(
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


_SIGNALS_REQUIRING_SUBJECTS = frozenset(
    {
        CiboMonitoringSignal.MATERIAL_CHANGE,
        CiboMonitoringSignal.ANOMALY,
        CiboMonitoringSignal.CONTRADICTION,
        CiboMonitoringSignal.REGIME_SHIFT,
    }
)

_MATERIAL_FACT_SIGNALS = frozenset(
    {
        CiboMonitoringSignal.MATERIAL_CHANGE,
        CiboMonitoringSignal.ANOMALY,
        CiboMonitoringSignal.REGIME_SHIFT,
    }
)


@dataclass(frozen=True, slots=True)
class CiboWorldObservation:
    """Immutable reduced world-observation bound to explicit evidence and subjects."""

    signal: CiboMonitoringSignal
    evidence: CiboFunctionalEvidence
    observed_at: datetime
    subject_refs: tuple[CiboEvidenceRef, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.signal) is not CiboMonitoringSignal:
            raise CiboFunctionalValidationError(
                "world observation requires exact CiboMonitoringSignal"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "world observation requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.observed_at, field_name="world observation observed_at")
        object.__setattr__(
            self,
            "subject_refs",
            _validate_subject_refs(self.subject_refs, field_name="subject refs"),
        )
        object.__setattr__(
            self,
            "reasons",
            _validate_codes(self.reasons, field_name="observation reasons"),
        )
        if self.signal in _SIGNALS_REQUIRING_SUBJECTS and not self.subject_refs:
            raise CiboFunctionalValidationError(
                f"{self.signal.value} requires non-empty subject refs"
            )
        # A material market fact (change/anomaly/regime shift) is a stronger
        # conclusion and must be bound to sufficient governed evidence; a
        # self-attested SUFFICIENT built from opaque refs fails closed here.
        if self.signal in _MATERIAL_FACT_SIGNALS and (
            self.evidence.status is not CiboEvidenceStatus.SUFFICIENT
        ):
            raise CiboFunctionalValidationError(
                f"{self.signal.value} requires sufficient governed evidence"
            )
        if self.signal is CiboMonitoringSignal.CONTRADICTION:
            if self.evidence.status is not CiboEvidenceStatus.CONTRADICTORY:
                raise CiboFunctionalValidationError(
                    "contradiction signal requires contradictory evidence"
                )
        if self.signal is CiboMonitoringSignal.STALE_EVIDENCE:
            if self.evidence.status is not CiboEvidenceStatus.STALE:
                raise CiboFunctionalValidationError(
                    "stale-evidence signal requires stale evidence"
                )
        if self.signal is CiboMonitoringSignal.EVIDENCE_GAP:
            if self.evidence.status is not CiboEvidenceStatus.MISSING:
                raise CiboFunctionalValidationError(
                    "evidence-gap signal requires missing evidence"
                )
        # Constructor/deriver parity: NO_MATERIAL_CHANGE is the all-clear conclusion
        # the reducer only emits from SUFFICIENT evidence, so it must not be admitted
        # on insufficient/stale/contradictory/dependent evidence by direct construction.
        if self.signal is CiboMonitoringSignal.NO_MATERIAL_CHANGE:
            if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "no-material-change signal requires sufficient evidence"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.signal.value,
            self.evidence.logical_values(),
            self.observed_at.isoformat(),
            tuple(ref.logical_values() for ref in self.subject_refs),
            self.reasons,
        )


_SIGNAL_BY_STATUS: dict[CiboEvidenceStatus, CiboMonitoringSignal] = {
    CiboEvidenceStatus.CONTRADICTORY: CiboMonitoringSignal.CONTRADICTION,
    CiboEvidenceStatus.STALE: CiboMonitoringSignal.STALE_EVIDENCE,
    CiboEvidenceStatus.MISSING: CiboMonitoringSignal.EVIDENCE_GAP,
    CiboEvidenceStatus.SUFFICIENT: CiboMonitoringSignal.NO_MATERIAL_CHANGE,
}


@dataclass(frozen=True, slots=True)
class CiboWorldMonitor:
    """Stateless, deterministic reducer of evidence assessments to one signal."""

    def observe(
        self,
        assessments: tuple[CiboFunctionalEvidence, ...],
        *,
        observed_at: datetime,
        subject_refs: tuple[CiboEvidenceRef, ...],
    ) -> Result[CiboWorldObservation, CiboFunctionalError]:
        """Reduce assessments to one observation; never fabricate a material change."""
        try:
            _validate_timestamp(observed_at, field_name="observed_at")
            normalized_subjects = _validate_subject_refs(
                subject_refs,
                field_name="subject refs",
            )
            evidence = synthesize_evidence(assessments, as_of=observed_at)
            if evidence.status is CiboEvidenceStatus.INSUFFICIENT:
                raise CiboFunctionalBlockedError(
                    "insufficient evidence; material conclusion fails closed"
                )
            signal = _SIGNAL_BY_STATUS.get(evidence.status)
            if signal is None:
                raise CiboFunctionalBlockedError(
                    "unresolvable evidence status; conclusion fails closed"
                )
            observation = CiboWorldObservation(
                signal=signal,
                evidence=evidence,
                observed_at=observed_at,
                subject_refs=normalized_subjects,
                reasons=evidence.reasons,
            )
            return Success(observation)
        except CiboFunctionalError as error:
            return Failure(error)
