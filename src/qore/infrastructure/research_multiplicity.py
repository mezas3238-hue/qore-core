from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from uuid import UUID

from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapTestEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchMultiplicityError(InfrastructureError):
    """Base error for research multiple-testing evidence."""

    __slots__ = ()


class ResearchMultiplicityValidationError(ResearchMultiplicityError):
    """Violation of a research multiplicity invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchHolmFamilyId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchMultiplicityValidationError(
                "Holm family id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchHolmPolicy:
    """Explicit family-wise alpha for Holm's step-down procedure."""

    familywise_alpha: Decimal

    def __post_init__(self) -> None:
        if (
            not isinstance(self.familywise_alpha, Decimal)
            or not self.familywise_alpha.is_finite()
            or not Decimal(0) < self.familywise_alpha < Decimal(1)
        ):
            raise ResearchMultiplicityValidationError(
                "familywise_alpha must be a finite Decimal strictly between zero and one"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.familywise_alpha, "f"),)


@dataclass(frozen=True, slots=True)
class ResearchHolmDecision:
    """One ordered Holm decision for one bootstrap-test p-value."""

    test: ResearchPeriodicBootstrapTestEvidence
    rank: int
    raw_p_value: Decimal
    holm_threshold: Decimal
    rejected: bool

    def __post_init__(self) -> None:
        if not isinstance(self.test, ResearchPeriodicBootstrapTestEvidence):
            raise ResearchMultiplicityValidationError(
                "Holm decision requires ResearchPeriodicBootstrapTestEvidence"
            )
        if type(self.rank) is not int or self.rank <= 0:
            raise ResearchMultiplicityValidationError(
                "Holm decision rank must be a positive integer"
            )
        if self.raw_p_value != self.test.bootstrap_p_value:
            raise ResearchMultiplicityValidationError(
                "Holm decision raw p-value must match source bootstrap evidence"
            )
        if (
            not isinstance(self.raw_p_value, Decimal)
            or not self.raw_p_value.is_finite()
            or not Decimal(0) < self.raw_p_value <= Decimal(1)
        ):
            raise ResearchMultiplicityValidationError(
                "Holm decision raw p-value must be in (0, 1]"
            )
        if (
            not isinstance(self.holm_threshold, Decimal)
            or not self.holm_threshold.is_finite()
            or not Decimal(0) < self.holm_threshold < Decimal(1)
        ):
            raise ResearchMultiplicityValidationError(
                "Holm decision threshold must be in (0, 1)"
            )
        if type(self.rejected) is not bool:
            raise ResearchMultiplicityValidationError(
                "Holm decision rejected must be bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.test.logical_values(),
            self.rank,
            format(self.raw_p_value, "f"),
            format(self.holm_threshold, "f"),
            self.rejected,
        )


def _validate_tests(
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
) -> None:
    if not isinstance(tests, tuple) or len(tests) < 2:
        raise ResearchMultiplicityValidationError(
            "Holm family requires at least two immutable bootstrap tests"
        )
    if any(not isinstance(test, ResearchPeriodicBootstrapTestEvidence) for test in tests):
        raise ResearchMultiplicityValidationError(
            "Holm family members must be ResearchPeriodicBootstrapTestEvidence"
        )
    test_ids = tuple(test.test_id for test in tests)
    if len(set(test_ids)) != len(test_ids):
        raise ResearchMultiplicityValidationError(
            "Holm family bootstrap test ids must be unique"
        )


def _derive_decisions(
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
    policy: ResearchHolmPolicy,
) -> tuple[ResearchHolmDecision, ...]:
    _validate_tests(tests)
    if not isinstance(policy, ResearchHolmPolicy):
        raise ResearchMultiplicityValidationError(
            "Holm correction requires ResearchHolmPolicy"
        )
    ordered = tuple(
        sorted(
            tests,
            key=lambda test: (
                test.bootstrap_p_value,
                str(test.test_id.value),
            ),
        )
    )
    family_size = len(ordered)
    keep_rejecting = True
    decisions: list[ResearchHolmDecision] = []
    for rank, test in enumerate(ordered, start=1):
        with localcontext(_DECIMAL128):
            threshold = policy.familywise_alpha / Decimal(family_size - rank + 1)
        rejected = keep_rejecting and test.bootstrap_p_value <= threshold
        if not rejected:
            keep_rejecting = False
        decisions.append(
            ResearchHolmDecision(
                test=test,
                rank=rank,
                raw_p_value=test.bootstrap_p_value,
                holm_threshold=threshold,
                rejected=rejected,
            )
        )
    return tuple(decisions)


@dataclass(frozen=True, slots=True)
class ResearchHolmFamilywiseEvidence:
    """Holm step-down family-wise rejection evidence for an explicit test family.

    The family and alpha are explicit. Tests are ordered deterministically by raw
    bootstrap p-value and then test UUID. Rejection stops at the first hypothesis
    that fails its Holm threshold, controlling family-wise error under the usual
    Holm assumptions for the supplied valid p-values.

    This evidence does not approve a strategy, prove predictive validity, choose
    the hypothesis family, correct undisclosed searches, or authorize production.
    """

    family_id: ResearchHolmFamilyId
    policy: ResearchHolmPolicy
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...]
    decisions: tuple[ResearchHolmDecision, ...]
    rejection_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.family_id, ResearchHolmFamilyId):
            raise ResearchMultiplicityValidationError(
                "family_id must be ResearchHolmFamilyId"
            )
        if not isinstance(self.policy, ResearchHolmPolicy):
            raise ResearchMultiplicityValidationError(
                "policy must be ResearchHolmPolicy"
            )
        _validate_tests(self.tests)
        expected_decisions = _derive_decisions(self.tests, self.policy)
        if self.decisions != expected_decisions:
            raise ResearchMultiplicityValidationError(
                "Holm decisions must match the exact test family and alpha"
            )
        expected_rejection_count = sum(decision.rejected for decision in expected_decisions)
        if self.rejection_count != expected_rejection_count:
            raise ResearchMultiplicityValidationError(
                "Holm rejection_count must match derived decisions"
            )

    @property
    def family_size(self) -> int:
        return len(self.tests)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family_id.logical_values(),
            self.policy.logical_values(),
            tuple(test.logical_values() for test in self.tests),
            tuple(decision.logical_values() for decision in self.decisions),
            self.rejection_count,
        )


def build_research_holm_familywise_evidence(
    *,
    family_id: ResearchHolmFamilyId,
    policy: ResearchHolmPolicy,
    tests: tuple[ResearchPeriodicBootstrapTestEvidence, ...],
) -> Result[ResearchHolmFamilywiseEvidence, ResearchMultiplicityError]:
    """Build deterministic Holm family-wise rejection evidence."""

    try:
        decisions = _derive_decisions(tests, policy)
        return Success(
            ResearchHolmFamilywiseEvidence(
                family_id=family_id,
                policy=policy,
                tests=tests,
                decisions=decisions,
                rejection_count=sum(decision.rejected for decision in decisions),
            )
        )
    except ResearchMultiplicityError as error:
        return Failure(error)
