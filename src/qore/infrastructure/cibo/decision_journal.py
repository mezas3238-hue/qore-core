"""CF-17 — Executive / Decision Journal.

Functional decision-episode SEMANTICS only (no persistence): an immutable record
of what was decided, on what evidence, with which hypotheses and consulted
specialists/traders, plus actual results and lessons. No execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalError,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_codes,
    _validate_evidence_refs,
    _validate_timestamp,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchRunValidationError
from qore.kernel.result import Failure, Result, Success


def _revalidate_identity(identity: ResearchDecisionEvaluatorIdentity) -> None:
    try:
        ResearchDecisionEvaluatorIdentity.__post_init__(identity)
        identity.family.__post_init__()
        identity.schema_version.__post_init__()
        identity.software_revision.__post_init__()
    except (
        ResearchLineageValidationError,
        ResearchRunValidationError,
        AttributeError,
        TypeError,
    ):
        raise CiboFunctionalValidationError(
            "consulted trader must be a valid ResearchDecisionEvaluatorIdentity"
        ) from None


def _identity_key(identity: ResearchDecisionEvaluatorIdentity) -> tuple[str, str, str]:
    return (
        identity.family.value,
        identity.schema_version.value,
        identity.software_revision.value,
    )


def _validate_traders(
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
    for item in values:
        _revalidate_identity(item)
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=_identity_key))


def _validate_optional_code(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return _validate_code(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class CiboDecisionEpisode:
    """Immutable decision-episode record semantics; no persistence, no execution."""

    episode_code: str
    world_refs: tuple[CiboEvidenceRef, ...]
    core_refs: tuple[CiboEvidenceRef, ...]
    hypotheses: tuple[str, ...]
    alternatives: tuple[str, ...]
    uncertainty_code: str
    consulted_specialists: tuple[str, ...]
    consulted_traders: tuple[ResearchDecisionEvaluatorIdentity, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    recommendation_code: str
    decision_code: str | None
    expected_result_code: str
    risk_assumption_codes: tuple[str, ...]
    actual_result_code: str | None
    counterfactual_code: str | None
    lesson_codes: tuple[str, ...]
    recorded_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "episode_code",
            _validate_code(self.episode_code, field_name="episode code"),
        )
        object.__setattr__(
            self,
            "world_refs",
            _validate_evidence_refs(self.world_refs, field_name="world refs"),
        )
        object.__setattr__(
            self,
            "core_refs",
            _validate_evidence_refs(self.core_refs, field_name="core refs"),
        )
        object.__setattr__(
            self,
            "hypotheses",
            _validate_codes(self.hypotheses, field_name="hypotheses"),
        )
        object.__setattr__(
            self,
            "alternatives",
            _validate_codes(self.alternatives, field_name="alternatives"),
        )
        object.__setattr__(
            self,
            "uncertainty_code",
            _validate_code(self.uncertainty_code, field_name="uncertainty code"),
        )
        object.__setattr__(
            self,
            "consulted_specialists",
            _validate_codes(
                self.consulted_specialists,
                field_name="consulted specialists",
            ),
        )
        object.__setattr__(
            self,
            "consulted_traders",
            _validate_traders(self.consulted_traders, field_name="consulted traders"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_code(self.recommendation_code, field_name="recommendation code"),
        )
        object.__setattr__(
            self,
            "decision_code",
            _validate_optional_code(self.decision_code, field_name="decision code"),
        )
        object.__setattr__(
            self,
            "expected_result_code",
            _validate_code(self.expected_result_code, field_name="expected result code"),
        )
        object.__setattr__(
            self,
            "risk_assumption_codes",
            _validate_codes(
                self.risk_assumption_codes,
                field_name="risk assumption codes",
            ),
        )
        object.__setattr__(
            self,
            "actual_result_code",
            _validate_optional_code(
                self.actual_result_code,
                field_name="actual result code",
            ),
        )
        object.__setattr__(
            self,
            "counterfactual_code",
            _validate_optional_code(
                self.counterfactual_code,
                field_name="counterfactual code",
            ),
        )
        object.__setattr__(
            self,
            "lesson_codes",
            _validate_codes(self.lesson_codes, field_name="lesson codes"),
        )
        _validate_timestamp(self.recorded_at, field_name="decision recorded_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.episode_code,
            tuple(item.logical_values() for item in self.world_refs),
            tuple(item.logical_values() for item in self.core_refs),
            self.hypotheses,
            self.alternatives,
            self.uncertainty_code,
            self.consulted_specialists,
            tuple(item.logical_values() for item in self.consulted_traders),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.recommendation_code,
            self.decision_code,
            self.expected_result_code,
            self.risk_assumption_codes,
            self.actual_result_code,
            self.counterfactual_code,
            self.lesson_codes,
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboDecisionJournal:
    """Deterministic, stateless executive decision journal (record semantics only)."""

    def record(
        self,
        *,
        episode_code: str,
        world_refs: tuple[CiboEvidenceRef, ...],
        core_refs: tuple[CiboEvidenceRef, ...],
        hypotheses: tuple[str, ...],
        alternatives: tuple[str, ...],
        uncertainty_code: str,
        consulted_specialists: tuple[str, ...],
        consulted_traders: tuple[ResearchDecisionEvaluatorIdentity, ...],
        evidence_refs: tuple[CiboEvidenceRef, ...],
        recommendation_code: str,
        decision_code: str | None,
        expected_result_code: str,
        risk_assumption_codes: tuple[str, ...],
        actual_result_code: str | None,
        counterfactual_code: str | None,
        lesson_codes: tuple[str, ...],
        recorded_at: datetime,
    ) -> Result[CiboDecisionEpisode, CiboFunctionalError]:
        """Record an immutable decision episode."""
        try:
            return Success(
                CiboDecisionEpisode(
                    episode_code=episode_code,
                    world_refs=world_refs,
                    core_refs=core_refs,
                    hypotheses=hypotheses,
                    alternatives=alternatives,
                    uncertainty_code=uncertainty_code,
                    consulted_specialists=consulted_specialists,
                    consulted_traders=consulted_traders,
                    evidence_refs=evidence_refs,
                    recommendation_code=recommendation_code,
                    decision_code=decision_code,
                    expected_result_code=expected_result_code,
                    risk_assumption_codes=risk_assumption_codes,
                    actual_result_code=actual_result_code,
                    counterfactual_code=counterfactual_code,
                    lesson_codes=lesson_codes,
                    recorded_at=recorded_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
