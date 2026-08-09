from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
)
from qore.infrastructure.research_periodic_equity import ResearchPeriodicEquityReturnSeries
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchHypothesisFamilyError(InfrastructureError):
    """Base error for structural research hypothesis-family evidence."""

    __slots__ = ()


class ResearchHypothesisFamilyValidationError(ResearchHypothesisFamilyError):
    """Violation of a structural hypothesis-family invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchHypothesisFamilyManifestId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis family manifest id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchBootstrapHypothesisPlan:
    """Exact bootstrap test specification for one family member."""

    test_id: ResearchPeriodicBootstrapTestId
    series: ResearchPeriodicEquityReturnSeries
    policy: ResearchPeriodicBootstrapTestPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.test_id, ResearchPeriodicBootstrapTestId):
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis plan test_id must be ResearchPeriodicBootstrapTestId"
            )
        if not isinstance(self.series, ResearchPeriodicEquityReturnSeries):
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis plan series must be ResearchPeriodicEquityReturnSeries"
            )
        if not isinstance(self.policy, ResearchPeriodicBootstrapTestPolicy):
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis plan policy must be ResearchPeriodicBootstrapTestPolicy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.test_id.logical_values(),
            self.series.logical_values(),
            self.policy.logical_values(),
        )


def _canonical_plans(
    plans: tuple[ResearchBootstrapHypothesisPlan, ...],
) -> tuple[ResearchBootstrapHypothesisPlan, ...]:
    if not isinstance(plans, tuple) or len(plans) < 2:
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family manifest requires at least two immutable plans"
        )
    if any(not isinstance(plan, ResearchBootstrapHypothesisPlan) for plan in plans):
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family members must be ResearchBootstrapHypothesisPlan"
        )
    test_ids = tuple(plan.test_id for plan in plans)
    if len(set(test_ids)) != len(test_ids):
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family plan test ids must be unique"
        )
    return tuple(sorted(plans, key=lambda plan: str(plan.test_id.value)))


@dataclass(frozen=True, slots=True)
class ResearchBootstrapHypothesisFamilyManifest:
    """Canonical structural declaration of one bootstrap hypothesis family.

    The manifest fixes family membership and each test's exact source series and
    bootstrap policy. It is structural evidence only: without independent timing
    evidence it does not prove that this family was preregistered before outcomes
    or p-values were observed.
    """

    manifest_id: ResearchHypothesisFamilyManifestId
    plans: tuple[ResearchBootstrapHypothesisPlan, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest_id, ResearchHypothesisFamilyManifestId):
            raise ResearchHypothesisFamilyValidationError(
                "manifest_id must be ResearchHypothesisFamilyManifestId"
            )
        canonical = _canonical_plans(self.plans)
        if self.plans != canonical:
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis family plans must use canonical test-id order"
            )

    @property
    def family_size(self) -> int:
        return len(self.plans)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.manifest_id.logical_values(),
            tuple(plan.logical_values() for plan in self.plans),
        )


def _canonical_tests(
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
) -> tuple[ResearchPeriodicBootstrapTestEvidence, ...]:
    if not isinstance(tests, tuple) or len(tests) < 2:
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family evidence requires at least two bootstrap tests"
        )
    if any(not isinstance(test, ResearchPeriodicBootstrapTestEvidence) for test in tests):
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family results must be ResearchPeriodicBootstrapTestEvidence"
        )
    test_ids = tuple(test.test_id for test in tests)
    if len(set(test_ids)) != len(test_ids):
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family result test ids must be unique"
        )
    return tuple(sorted(tests, key=lambda test: str(test.test_id.value)))


def _validate_binding(
    manifest: ResearchBootstrapHypothesisFamilyManifest,
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
) -> None:
    if not isinstance(manifest, ResearchBootstrapHypothesisFamilyManifest):
        raise ResearchHypothesisFamilyValidationError(
            "family binding requires ResearchBootstrapHypothesisFamilyManifest"
        )
    canonical_tests = _canonical_tests(tests)
    if tests != canonical_tests:
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family results must use canonical test-id order"
        )
    if len(tests) != len(manifest.plans):
        raise ResearchHypothesisFamilyValidationError(
            "hypothesis family results must cover every manifest plan exactly once"
        )
    for plan, test in zip(manifest.plans, tests, strict=True):
        if test.test_id != plan.test_id:
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis result test id must match manifest plan"
            )
        if test.series != plan.series:
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis result series must match manifest plan"
            )
        if test.policy != plan.policy:
            raise ResearchHypothesisFamilyValidationError(
                "hypothesis result policy must match manifest plan"
            )


@dataclass(frozen=True, slots=True)
class ResearchBootstrapHypothesisFamilyEvidence:
    """Exact result binding for a structural bootstrap hypothesis-family manifest."""

    manifest: ResearchBootstrapHypothesisFamilyManifest
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...]

    def __post_init__(self) -> None:
        _validate_binding(self.manifest, self.tests)

    @property
    def family_size(self) -> int:
        return len(self.tests)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.manifest.logical_values(),
            tuple(test.logical_values() for test in self.tests),
        )


def build_research_bootstrap_hypothesis_family_manifest(
    *,
    manifest_id: ResearchHypothesisFamilyManifestId,
    plans: tuple[ResearchBootstrapHypothesisPlan, ...],
) -> Result[
    ResearchBootstrapHypothesisFamilyManifest,
    ResearchHypothesisFamilyError,
]:
    """Build a canonical structural bootstrap hypothesis-family manifest."""

    try:
        canonical = _canonical_plans(plans)
        return Success(
            ResearchBootstrapHypothesisFamilyManifest(
                manifest_id=manifest_id,
                plans=canonical,
            )
        )
    except ResearchHypothesisFamilyError as error:
        return Failure(error)


def build_research_bootstrap_hypothesis_family_evidence(
    *,
    manifest: ResearchBootstrapHypothesisFamilyManifest,
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
) -> Result[
    ResearchBootstrapHypothesisFamilyEvidence,
    ResearchHypothesisFamilyError,
]:
    """Bind exact bootstrap results to every structural family plan."""

    try:
        canonical = _canonical_tests(tests)
        return Success(
            ResearchBootstrapHypothesisFamilyEvidence(
                manifest=manifest,
                tests=canonical,
            )
        )
    except ResearchHypothesisFamilyError as error:
        return Failure(error)
