"""CF-14/CF-20 Mission Director (D5).

Turns a high-level objective into a governed mission without duplicating
Cognitive reasoning ownership (#482). A mission binds the objective plus
constraints, the relevant functions/Traders and their readiness, missing evidence
and unresolved uncertainty, research/replay/Lab/evaluation assignments, measurable
hypotheses with success/failure criteria, training/retraining/version-comparison
work, DEMO observation requirements, baseline/counterfactual comparison, a
continue/revise/suspend/abandon disposition, and durable lineage plus unresolved
risks.

A mission is a REQUEST: it asks for governed work, never commands it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo.functional_coordinator import CiboFacultyDomain
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
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


def _validate_faculties(
    values: tuple[CiboFacultyDomain, ...],
    *,
    field_name: str,
) -> tuple[CiboFacultyDomain, ...]:
    if not isinstance(values, tuple) or any(
        type(faculty) is not CiboFacultyDomain for faculty in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of exact CiboFacultyDomain"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda faculty: faculty.value))


def _validate_identities(
    values: tuple[ResearchDecisionEvaluatorIdentity, ...],
    *,
    field_name: str,
) -> tuple[ResearchDecisionEvaluatorIdentity, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ResearchDecisionEvaluatorIdentity) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of ResearchDecisionEvaluatorIdentity"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(
        sorted(
            values,
            key=lambda identity: (
                identity.family.value,
                identity.schema_version.value,
                identity.software_revision.value,
            ),
        )
    )


class CiboMissionDisposition(StrEnum):
    """Governed mission disposition. No execution/promotion member exists."""

    CONTINUE = "continue"
    REVISE = "revise"
    SUSPEND = "suspend"
    ABANDON = "abandon"


@dataclass(frozen=True, slots=True)
class CiboMission:
    """A governed mission representation (REQUEST authority, no Cognitive duplication)."""

    mission_code: str
    objective_code: str
    constraint_codes: tuple[str, ...]
    assigned_functions: tuple[CiboFacultyDomain, ...]
    assigned_traders: tuple[ResearchDecisionEvaluatorIdentity, ...]
    readiness_codes: tuple[str, ...]
    missing_evidence_codes: tuple[str, ...]
    unresolved_uncertainty_codes: tuple[str, ...]
    assignment_codes: tuple[str, ...]
    hypothesis_codes: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    training_codes: tuple[str, ...]
    demo_observation_codes: tuple[str, ...]
    baseline_codes: tuple[str, ...]
    counterfactual_codes: tuple[str, ...]
    disposition: CiboMissionDisposition
    lineage: tuple[str, ...]
    unresolved_risk_codes: tuple[str, ...]
    planned_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mission_code",
            _validate_code(self.mission_code, field_name="mission code"),
        )
        object.__setattr__(
            self,
            "objective_code",
            _validate_code(self.objective_code, field_name="objective code"),
        )
        object.__setattr__(
            self,
            "constraint_codes",
            _validate_codes(self.constraint_codes, field_name="constraint codes"),
        )
        object.__setattr__(
            self,
            "assigned_functions",
            _validate_faculties(self.assigned_functions, field_name="assigned functions"),
        )
        object.__setattr__(
            self,
            "assigned_traders",
            _validate_identities(self.assigned_traders, field_name="assigned traders"),
        )
        object.__setattr__(
            self,
            "readiness_codes",
            _validate_codes(self.readiness_codes, field_name="readiness codes"),
        )
        object.__setattr__(
            self,
            "missing_evidence_codes",
            _validate_codes(self.missing_evidence_codes, field_name="missing evidence"),
        )
        object.__setattr__(
            self,
            "unresolved_uncertainty_codes",
            _validate_codes(
                self.unresolved_uncertainty_codes,
                field_name="unresolved uncertainty",
            ),
        )
        object.__setattr__(
            self,
            "assignment_codes",
            _validate_codes(self.assignment_codes, field_name="assignment codes"),
        )
        object.__setattr__(
            self,
            "hypothesis_codes",
            _validate_codes(self.hypothesis_codes, field_name="hypothesis codes"),
        )
        if not self.hypothesis_codes:
            raise CiboFunctionalValidationError(
                "a mission requires at least one measurable hypothesis"
            )
        object.__setattr__(
            self,
            "success_criteria",
            _validate_codes(self.success_criteria, field_name="success criteria"),
        )
        if not self.success_criteria:
            raise CiboFunctionalValidationError(
                "a mission requires at least one success criterion"
            )
        object.__setattr__(
            self,
            "failure_criteria",
            _validate_codes(self.failure_criteria, field_name="failure criteria"),
        )
        object.__setattr__(
            self,
            "training_codes",
            _validate_codes(self.training_codes, field_name="training codes"),
        )
        object.__setattr__(
            self,
            "demo_observation_codes",
            _validate_codes(
                self.demo_observation_codes,
                field_name="demo observation codes",
            ),
        )
        object.__setattr__(
            self,
            "baseline_codes",
            _validate_codes(self.baseline_codes, field_name="baseline codes"),
        )
        object.__setattr__(
            self,
            "counterfactual_codes",
            _validate_codes(self.counterfactual_codes, field_name="counterfactual codes"),
        )
        if type(self.disposition) is not CiboMissionDisposition:
            raise CiboFunctionalValidationError(
                "mission requires exact CiboMissionDisposition"
            )
        object.__setattr__(
            self,
            "lineage",
            _validate_codes(self.lineage, field_name="mission lineage"),
        )
        object.__setattr__(
            self,
            "unresolved_risk_codes",
            _validate_codes(self.unresolved_risk_codes, field_name="unresolved risks"),
        )
        _validate_timestamp(self.planned_at, field_name="mission planned_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "mission requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.REQUEST:
            raise CiboFunctionalValidationError(
                "mission authority must be REQUEST"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mission_code,
            self.objective_code,
            self.constraint_codes,
            tuple(faculty.value for faculty in self.assigned_functions),
            tuple(item.logical_values() for item in self.assigned_traders),
            self.readiness_codes,
            self.missing_evidence_codes,
            self.unresolved_uncertainty_codes,
            self.assignment_codes,
            self.hypothesis_codes,
            self.success_criteria,
            self.failure_criteria,
            self.training_codes,
            self.demo_observation_codes,
            self.baseline_codes,
            self.counterfactual_codes,
            self.disposition.value,
            self.lineage,
            self.unresolved_risk_codes,
            self.planned_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboMissionDirector:
    """Deterministic, stateless mission director (no Cognitive reasoning duplication)."""

    def direct(
        self,
        *,
        mission_code: str,
        objective_code: str,
        constraint_codes: tuple[str, ...],
        assigned_functions: tuple[CiboFacultyDomain, ...],
        assigned_traders: tuple[ResearchDecisionEvaluatorIdentity, ...],
        readiness_codes: tuple[str, ...],
        missing_evidence_codes: tuple[str, ...],
        unresolved_uncertainty_codes: tuple[str, ...],
        assignment_codes: tuple[str, ...],
        hypothesis_codes: tuple[str, ...],
        success_criteria: tuple[str, ...],
        failure_criteria: tuple[str, ...],
        training_codes: tuple[str, ...],
        demo_observation_codes: tuple[str, ...],
        baseline_codes: tuple[str, ...],
        counterfactual_codes: tuple[str, ...],
        disposition: CiboMissionDisposition,
        lineage: tuple[str, ...],
        unresolved_risk_codes: tuple[str, ...],
        planned_at: datetime,
    ) -> Result[CiboMission, CiboFunctionalError]:
        """Assemble a governed mission; it requests work, never commands it."""
        try:
            return Success(
                CiboMission(
                    mission_code=mission_code,
                    objective_code=objective_code,
                    constraint_codes=constraint_codes,
                    assigned_functions=assigned_functions,
                    assigned_traders=assigned_traders,
                    readiness_codes=readiness_codes,
                    missing_evidence_codes=missing_evidence_codes,
                    unresolved_uncertainty_codes=unresolved_uncertainty_codes,
                    assignment_codes=assignment_codes,
                    hypothesis_codes=hypothesis_codes,
                    success_criteria=success_criteria,
                    failure_criteria=failure_criteria,
                    training_codes=training_codes,
                    demo_observation_codes=demo_observation_codes,
                    baseline_codes=baseline_codes,
                    counterfactual_codes=counterfactual_codes,
                    disposition=disposition,
                    lineage=lineage,
                    unresolved_risk_codes=unresolved_risk_codes,
                    planned_at=planned_at,
                    authority=CiboFunctionalAuthority.REQUEST,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def logical_values(self) -> tuple[object, ...]:
        return ()


__all__ = [
    "CiboMissionDisposition",
    "CiboMission",
    "CiboMissionDirector",
]
