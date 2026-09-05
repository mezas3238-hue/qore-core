"""CF-09 — Stop-Loss / Failure Intelligence.

CIBO diagnoses a failure as a research hypothesis. The output is always an
``OPINION``: it never auto-mutates parameters, stop methodology, config or code.
Certainty requires sufficient evidence; ``INSUFFICIENT_EVIDENCE`` may never be
asserted with post-hoc certainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_timestamp,
)
from qore.kernel.result import Failure, Result, Success


class CiboFailureClass(StrEnum):
    """Deterministic failure classification vocabulary."""

    RISK_CONTAINMENT = "risk-containment"
    ENTRY_QUALITY = "entry-quality"
    NOISE = "noise"
    REGIME_CHANGE = "regime-change"
    VOLATILITY_EXPANSION = "volatility-expansion"
    LATE_SIGNAL = "late-signal"
    LIFECYCLE_MISMATCH = "lifecycle-mismatch"
    INSTRUMENT_MISMATCH = "instrument-mismatch"
    STOP_METHODOLOGY = "stop-methodology"
    CONCENTRATION_CORRELATION = "concentration-correlation"
    EXECUTION_COST_DEGRADATION = "execution-cost-degradation"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


def _revalidate_evidence(evidence: CiboFunctionalEvidence) -> None:
    try:
        CiboFunctionalEvidence.__post_init__(evidence)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "evidence must be a valid CiboFunctionalEvidence"
        ) from None


@dataclass(frozen=True, slots=True)
class CiboFailureDiagnosis:
    """A failure hypothesis; an opinion, never an automatic parameter mutation."""

    classification: CiboFailureClass
    hypothesis_code: str
    evidence: CiboFunctionalEvidence
    diagnosed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if type(self.classification) is not CiboFailureClass:
            raise CiboFunctionalValidationError(
                "failure diagnosis requires CiboFailureClass"
            )
        object.__setattr__(
            self,
            "hypothesis_code",
            _validate_code(self.hypothesis_code, field_name="hypothesis code"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "failure diagnosis requires CiboFunctionalEvidence"
            )
        _revalidate_evidence(self.evidence)
        _validate_timestamp(self.diagnosed_at, field_name="failure diagnosed_at")
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "failure diagnosis authority must be opinion"
            )
        if self.classification is CiboFailureClass.INSUFFICIENT_EVIDENCE:
            if self.evidence.status is CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "insufficient-evidence failure cannot assert post-hoc certainty"
                )
            return
        if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            raise CiboFunctionalValidationError(
                "failure classification requires sufficient evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.classification.value,
            self.hypothesis_code,
            self.evidence.logical_values(),
            self.diagnosed_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboFailureIntelligence:
    """Deterministic, stateless stop-loss / failure intelligence."""

    def diagnose(
        self,
        classification: CiboFailureClass,
        *,
        evidence: CiboFunctionalEvidence,
        hypothesis_code: str,
        diagnosed_at: datetime,
    ) -> Result[CiboFailureDiagnosis, CiboFunctionalError]:
        """Diagnose a failure as an opinionated research hypothesis."""
        if type(classification) is not CiboFailureClass:
            return Failure(
                CiboFunctionalValidationError("classification must be CiboFailureClass")
            )
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            return Success(
                CiboFailureDiagnosis(
                    classification=classification,
                    hypothesis_code=hypothesis_code,
                    evidence=evidence,
                    diagnosed_at=diagnosed_at,
                    authority=CiboFunctionalAuthority.OPINION,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
