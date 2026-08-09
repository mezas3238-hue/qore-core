from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.infrastructure.research_multiplicity import (
    ResearchHolmFamilyId,
    ResearchHolmFamilywiseEvidence,
    ResearchHolmPolicy,
    build_research_holm_familywise_evidence,
)
from qore.infrastructure.research_preoutcome_hypothesis import (
    ResearchPreOutcomeBootstrapEvidence,
    ResearchPreOutcomeBootstrapHypothesisSpec,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchPreOutcomeFamilyError(InfrastructureError):
    """Base error for pre-outcome hypothesis-family evidence."""

    __slots__ = ()


class ResearchPreOutcomeFamilyValidationError(ResearchPreOutcomeFamilyError):
    """Violation of a pre-outcome hypothesis-family invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchPreOutcomeFamilyValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchPreOutcomeFamilyValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeFamilyId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPreOutcomeFamilyValidationError(
                "pre-outcome family id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _canonical_members(
    members: tuple[ResearchPreOutcomeBootstrapHypothesisSpec, ...],
) -> tuple[ResearchPreOutcomeBootstrapHypothesisSpec, ...]:
    if not isinstance(members, tuple) or len(members) < 2:
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family requires at least two immutable hypothesis specs"
        )
    if any(
        not isinstance(member, ResearchPreOutcomeBootstrapHypothesisSpec)
        for member in members
    ):
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family members must be bootstrap hypothesis specs"
        )
    test_ids = tuple(member.test_id for member in members)
    if len(set(test_ids)) != len(test_ids):
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family test ids must be unique"
        )
    spec_ids = tuple(member.spec_id for member in members)
    if len(set(spec_ids)) != len(spec_ids):
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family spec ids must be unique"
        )
    return tuple(sorted(members, key=lambda member: str(member.test_id.value)))


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeHypothesisFamilySpec:
    """Result-free family membership frozen before later recorded observations."""

    family_id: ResearchPreOutcomeFamilyId
    members: tuple[ResearchPreOutcomeBootstrapHypothesisSpec, ...]
    frozen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.family_id, ResearchPreOutcomeFamilyId):
            raise ResearchPreOutcomeFamilyValidationError(
                "family_id must be ResearchPreOutcomeFamilyId"
            )
        canonical = _canonical_members(self.members)
        if self.members != canonical:
            raise ResearchPreOutcomeFamilyValidationError(
                "pre-outcome family members must use canonical test-id order"
            )
        _validate_timestamp(self.frozen_at, field_name="family frozen_at")
        if any(member.frozen_at > self.frozen_at for member in self.members):
            raise ResearchPreOutcomeFamilyValidationError(
                "family freeze must not predate any member specification freeze"
            )

    @property
    def family_size(self) -> int:
        return len(self.members)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family_id.logical_values(),
            tuple(member.logical_values() for member in self.members),
            self.frozen_at.isoformat(),
        )


def _canonical_results(
    results: tuple[ResearchPreOutcomeBootstrapEvidence, ...],
) -> tuple[ResearchPreOutcomeBootstrapEvidence, ...]:
    if not isinstance(results, tuple) or len(results) < 2:
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family evidence requires at least two immutable results"
        )
    if any(not isinstance(result, ResearchPreOutcomeBootstrapEvidence) for result in results):
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family results must be ResearchPreOutcomeBootstrapEvidence"
        )
    test_ids = tuple(result.spec.test_id for result in results)
    if len(set(test_ids)) != len(test_ids):
        raise ResearchPreOutcomeFamilyValidationError(
            "pre-outcome family result test ids must be unique"
        )
    return tuple(sorted(results, key=lambda result: str(result.spec.test_id.value)))


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeHypothesisFamilyEvidence:
    """Exact pre-observation family membership bound to later bootstrap results."""

    family_spec: ResearchPreOutcomeHypothesisFamilySpec
    results: tuple[ResearchPreOutcomeBootstrapEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.family_spec, ResearchPreOutcomeHypothesisFamilySpec):
            raise ResearchPreOutcomeFamilyValidationError(
                "family evidence requires ResearchPreOutcomeHypothesisFamilySpec"
            )
        canonical = _canonical_results(self.results)
        if self.results != canonical:
            raise ResearchPreOutcomeFamilyValidationError(
                "pre-outcome family results must use canonical test-id order"
            )
        if len(self.results) != len(self.family_spec.members):
            raise ResearchPreOutcomeFamilyValidationError(
                "pre-outcome family results must cover every frozen member exactly once"
            )
        for member, result in zip(
            self.family_spec.members,
            self.results,
            strict=True,
        ):
            if result.spec != member:
                raise ResearchPreOutcomeFamilyValidationError(
                    "family result must match the exact frozen member specification"
                )
            if result.earliest_observation_recorded_at < self.family_spec.frozen_at:
                raise ResearchPreOutcomeFamilyValidationError(
                    "family membership freeze must not postdate any member observation"
                )

    @property
    def family_size(self) -> int:
        return len(self.results)

    @property
    def tests(self) -> tuple[object, ...]:
        return tuple(result.test for result in self.results)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family_spec.logical_values(),
            tuple(result.logical_values() for result in self.results),
        )


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeFamilyHolmEvidence:
    """Holm correction bound to one pre-observation frozen hypothesis family."""

    family: ResearchPreOutcomeHypothesisFamilyEvidence
    holm: ResearchHolmFamilywiseEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.family, ResearchPreOutcomeHypothesisFamilyEvidence):
            raise ResearchPreOutcomeFamilyValidationError(
                "Holm binding requires ResearchPreOutcomeHypothesisFamilyEvidence"
            )
        if not isinstance(self.holm, ResearchHolmFamilywiseEvidence):
            raise ResearchPreOutcomeFamilyValidationError(
                "Holm binding requires ResearchHolmFamilywiseEvidence"
            )
        expected_tests = tuple(result.test for result in self.family.results)
        if self.holm.tests != expected_tests:
            raise ResearchPreOutcomeFamilyValidationError(
                "Holm tests must exactly match the pre-outcome frozen family results"
            )

    @property
    def rejection_count(self) -> int:
        return self.holm.rejection_count

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family.logical_values(),
            self.holm.logical_values(),
        )


def build_research_preoutcome_family_spec(
    *,
    family_id: ResearchPreOutcomeFamilyId,
    members: tuple[ResearchPreOutcomeBootstrapHypothesisSpec, ...],
    frozen_at: datetime,
) -> Result[ResearchPreOutcomeHypothesisFamilySpec, ResearchPreOutcomeFamilyError]:
    """Build a canonical result-free family membership freeze."""

    try:
        canonical = _canonical_members(members)
        return Success(
            ResearchPreOutcomeHypothesisFamilySpec(
                family_id=family_id,
                members=canonical,
                frozen_at=frozen_at,
            )
        )
    except ResearchPreOutcomeFamilyError as error:
        return Failure(error)


def build_research_preoutcome_family_evidence(
    *,
    family_spec: ResearchPreOutcomeHypothesisFamilySpec,
    results: tuple[ResearchPreOutcomeBootstrapEvidence, ...],
) -> Result[ResearchPreOutcomeHypothesisFamilyEvidence, ResearchPreOutcomeFamilyError]:
    """Bind later results to every frozen family member exactly once."""

    try:
        canonical = _canonical_results(results)
        return Success(
            ResearchPreOutcomeHypothesisFamilyEvidence(
                family_spec=family_spec,
                results=canonical,
            )
        )
    except ResearchPreOutcomeFamilyError as error:
        return Failure(error)


def build_research_preoutcome_family_holm_evidence(
    *,
    family: ResearchPreOutcomeHypothesisFamilyEvidence,
    holm_family_id: ResearchHolmFamilyId,
    policy: ResearchHolmPolicy,
) -> Result[ResearchPreOutcomeFamilyHolmEvidence, InfrastructureError]:
    """Apply Holm only to the exact pre-observation frozen family results."""

    if not isinstance(family, ResearchPreOutcomeHypothesisFamilyEvidence):
        return Failure(
            ResearchPreOutcomeFamilyValidationError(
                "family must be ResearchPreOutcomeHypothesisFamilyEvidence"
            )
        )
    tests = tuple(result.test for result in family.results)
    built = build_research_holm_familywise_evidence(
        family_id=holm_family_id,
        policy=policy,
        tests=tests,
    )
    if isinstance(built, Failure):
        return Failure(built.error)
    try:
        return Success(
            ResearchPreOutcomeFamilyHolmEvidence(
                family=family,
                holm=built.value,
            )
        )
    except ResearchPreOutcomeFamilyError as error:
        return Failure(error)
