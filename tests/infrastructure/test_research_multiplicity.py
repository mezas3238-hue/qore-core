from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_multiplicity import (
    ResearchHolmFamilyId,
    ResearchHolmPolicy,
    ResearchMultiplicityValidationError,
    build_research_holm_familywise_evidence,
)
from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"88000000-0000-0000-0000-{suffix:012d}")


def _test(suffix: int, p_value: str) -> ResearchPeriodicBootstrapTestEvidence:
    evidence = object.__new__(ResearchPeriodicBootstrapTestEvidence)
    object.__setattr__(
        evidence,
        "test_id",
        ResearchPeriodicBootstrapTestId(_uuid(suffix)),
    )
    object.__setattr__(evidence, "bootstrap_p_value", Decimal(p_value))
    return evidence


def test_holm_rejects_family_members_that_pass_each_step() -> None:
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(100)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(
            _test(3, "0.04"),
            _test(1, "0.001"),
            _test(2, "0.01"),
        ),
    )

    assert isinstance(built, Success)
    evidence = built.value
    assert tuple(decision.raw_p_value for decision in evidence.decisions) == (
        Decimal("0.001"),
        Decimal("0.01"),
        Decimal("0.04"),
    )
    assert evidence.decisions[0].holm_threshold == Decimal(
        "0.01666666666666666666666666666666667"
    )
    assert evidence.decisions[1].holm_threshold == Decimal("0.025")
    assert evidence.decisions[2].holm_threshold == Decimal("0.05")
    assert tuple(decision.rejected for decision in evidence.decisions) == (
        True,
        True,
        True,
    )
    assert evidence.rejection_count == 3
    assert evidence.family_size == 3


def test_holm_step_down_stops_rejection_after_first_failure() -> None:
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(101)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(
            _test(10, "0.01"),
            _test(11, "0.03"),
            _test(12, "0.031"),
        ),
    )

    assert isinstance(built, Success)
    evidence = built.value
    assert tuple(decision.holm_threshold for decision in evidence.decisions) == (
        Decimal("0.01666666666666666666666666666666667"),
        Decimal("0.025"),
        Decimal("0.05"),
    )
    assert tuple(decision.rejected for decision in evidence.decisions) == (
        True,
        False,
        False,
    )
    assert evidence.rejection_count == 1


def test_holm_uses_test_id_as_deterministic_tie_breaker() -> None:
    first = _test(20, "0.01")
    second = _test(21, "0.01")
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(102)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(second, first),
    )

    assert isinstance(built, Success)
    assert tuple(decision.test.test_id for decision in built.value.decisions) == (
        first.test_id,
        second.test_id,
    )


def test_holm_rejects_invalid_alpha_or_too_small_family() -> None:
    for alpha in (
        Decimal("0"),
        Decimal("1"),
        Decimal("-0.1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ):
        with pytest.raises(ResearchMultiplicityValidationError):
            ResearchHolmPolicy(familywise_alpha=alpha)

    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(103)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(_test(30, "0.01"),),
    )
    assert isinstance(built, Failure)


def test_holm_rejects_duplicate_test_ids() -> None:
    first = _test(40, "0.01")
    duplicate = _test(40, "0.02")
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(104)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(first, duplicate),
    )

    assert isinstance(built, Failure)
    assert "unique" in str(built.error)


def test_holm_evidence_rejects_derived_decision_tampering() -> None:
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(105)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(_test(50, "0.01"), _test(51, "0.02")),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchMultiplicityValidationError):
        replace(built.value, rejection_count=99)
    tampered_decision = replace(built.value.decisions[0], rejected=False)
    with pytest.raises(ResearchMultiplicityValidationError):
        replace(
            built.value,
            decisions=(tampered_decision, built.value.decisions[1]),
        )


def test_holm_correction_does_not_authorize_strategy_or_production() -> None:
    built = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(106)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(_test(60, "0.001"), _test(61, "0.01")),
    )
    assert isinstance(built, Success)
    evidence = built.value

    assert not hasattr(evidence, "strategy_approved")
    assert not hasattr(evidence, "predictive_validity")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")
