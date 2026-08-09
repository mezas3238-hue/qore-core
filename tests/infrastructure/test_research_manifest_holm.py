from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_hypothesis_family import (
    ResearchBootstrapHypothesisFamilyEvidence,
)
from qore.infrastructure.research_manifest_holm import (
    ResearchManifestHolmEvidence,
    ResearchManifestHolmValidationError,
    build_research_manifest_holm_evidence,
)
from qore.infrastructure.research_multiplicity import (
    ResearchHolmFamilyId,
    ResearchHolmPolicy,
    build_research_holm_familywise_evidence,
)
from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"90000000-0000-0000-0000-{suffix:012d}")


def _test(suffix: int, p_value: str) -> ResearchPeriodicBootstrapTestEvidence:
    evidence = object.__new__(ResearchPeriodicBootstrapTestEvidence)
    object.__setattr__(
        evidence,
        "test_id",
        ResearchPeriodicBootstrapTestId(_uuid(suffix)),
    )
    object.__setattr__(evidence, "bootstrap_p_value", Decimal(p_value))
    return evidence


def _family(
    *tests: ResearchPeriodicBootstrapTestEvidence,
) -> ResearchBootstrapHypothesisFamilyEvidence:
    family = object.__new__(ResearchBootstrapHypothesisFamilyEvidence)
    object.__setattr__(family, "tests", tuple(tests))
    return family


def test_manifest_holm_consumes_exact_family_test_tuple() -> None:
    family = _family(_test(1, "0.001"), _test(2, "0.01"))
    built = build_research_manifest_holm_evidence(
        family=family,
        family_id=ResearchHolmFamilyId(_uuid(100)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
    )

    assert isinstance(built, Success)
    assert built.value.holm.tests is family.tests
    assert built.value.rejection_count == 2
    assert built.value.holm.family_size == family.family_size


def test_manifest_holm_rejects_reordered_family_results() -> None:
    first = _test(10, "0.001")
    second = _test(11, "0.01")
    family = _family(first, second)
    other_holm = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(101)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(second, first),
    )
    assert isinstance(other_holm, Success)

    with pytest.raises(ResearchManifestHolmValidationError):
        ResearchManifestHolmEvidence(
            family=family,
            holm=other_holm.value,
        )


def test_manifest_holm_rejects_dropped_family_member() -> None:
    first = _test(20, "0.001")
    second = _test(21, "0.01")
    third = _test(22, "0.02")
    family = _family(first, second, third)
    subset_holm = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(102)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=(first, second),
    )
    assert isinstance(subset_holm, Success)

    with pytest.raises(ResearchManifestHolmValidationError):
        ResearchManifestHolmEvidence(
            family=family,
            holm=subset_holm.value,
        )


def test_manifest_holm_propagates_invalid_holm_policy_failure() -> None:
    family = _family(_test(30, "0.001"), _test(31, "0.01"))
    invalid_policy = object.__new__(ResearchHolmPolicy)
    object.__setattr__(invalid_policy, "familywise_alpha", Decimal("0"))

    built = build_research_manifest_holm_evidence(
        family=family,
        family_id=ResearchHolmFamilyId(_uuid(103)),
        policy=invalid_policy,
    )

    assert isinstance(built, Failure)


def test_manifest_holm_rejects_derived_binding_tampering() -> None:
    family = _family(_test(40, "0.001"), _test(41, "0.01"))
    built = build_research_manifest_holm_evidence(
        family=family,
        family_id=ResearchHolmFamilyId(_uuid(104)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
    )
    assert isinstance(built, Success)

    alternate = _family(_test(42, "0.001"), _test(43, "0.01"))
    with pytest.raises(ResearchManifestHolmValidationError):
        replace(built.value, family=alternate)


def test_manifest_holm_makes_no_preregistration_or_production_claims() -> None:
    family = _family(_test(50, "0.001"), _test(51, "0.01"))
    built = build_research_manifest_holm_evidence(
        family=family,
        family_id=ResearchHolmFamilyId(_uuid(105)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
    )
    assert isinstance(built, Success)
    evidence = built.value

    assert not hasattr(evidence, "preregistered")
    assert not hasattr(evidence, "frozen_before_outcomes")
    assert not hasattr(evidence, "strategy_approved")
    assert not hasattr(evidence, "predictive_validity")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")
