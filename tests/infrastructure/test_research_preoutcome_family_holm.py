from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_multiplicity import (
    ResearchHolmFamilyId,
    ResearchHolmPolicy,
    build_research_holm_familywise_evidence,
)
from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapAlternative,
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityValuationBasis,
    ResearchEquityValuationObservation,
    ResearchPeriodicEquityPolicy,
    ResearchPeriodicEquityReturnSeries,
    ResearchValuationModelId,
)
from qore.infrastructure.research_preoutcome_family_holm import (
    ResearchPreOutcomeFamilyHolmEvidence,
    ResearchPreOutcomeFamilyId,
    ResearchPreOutcomeFamilyValidationError,
    build_research_preoutcome_family_evidence,
    build_research_preoutcome_family_holm_evidence,
    build_research_preoutcome_family_spec,
)
from qore.infrastructure.research_preoutcome_hypothesis import (
    ResearchPreOutcomeBootstrapEvidence,
    ResearchPreOutcomeBootstrapHypothesisSpec,
    ResearchPreOutcomeHypothesisSpecId,
)
from qore.infrastructure.research_run import ResearchRunInputFingerprint
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"92000000-0000-0000-0000-{suffix:012d}")


def _bootstrap_policy(seed: int) -> ResearchPeriodicBootstrapTestPolicy:
    return ResearchPeriodicBootstrapTestPolicy(
        null_mean_per_period=Decimal("0"),
        alternative=ResearchPeriodicBootstrapAlternative.GREATER,
        block_length=2,
        resample_count=12,
        seed=seed,
    )


def _spec(
    suffix: int,
    *,
    frozen_at: datetime = _BASE,
) -> ResearchPreOutcomeBootstrapHypothesisSpec:
    return ResearchPreOutcomeBootstrapHypothesisSpec(
        spec_id=ResearchPreOutcomeHypothesisSpecId(_uuid(100 + suffix)),
        test_id=ResearchPeriodicBootstrapTestId(_uuid(suffix)),
        run_input_fingerprint=ResearchRunInputFingerprint("a" * 64),
        valuation_model_id=ResearchValuationModelId(_uuid(500)),
        valuation_model_version="valuation.v1",
        valuation_basis=ResearchEquityValuationBasis.GROSS,
        periodic_policy=ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        bootstrap_policy=_bootstrap_policy(suffix),
        frozen_at=frozen_at,
    )


def _observation(recorded_at: datetime) -> ResearchEquityValuationObservation:
    observation = object.__new__(ResearchEquityValuationObservation)
    object.__setattr__(observation, "recorded_at", recorded_at)
    return observation


def _bootstrap_test(
    spec: ResearchPreOutcomeBootstrapHypothesisSpec,
    *,
    p_value: str,
    first_recorded_at: datetime,
) -> ResearchPeriodicBootstrapTestEvidence:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "binding", None)
    object.__setattr__(series, "policy", spec.periodic_policy)
    object.__setattr__(
        series,
        "observations",
        (
            _observation(first_recorded_at),
            _observation(first_recorded_at + timedelta(hours=1)),
        ),
    )
    object.__setattr__(series, "returns", ())

    evidence = object.__new__(ResearchPeriodicBootstrapTestEvidence)
    object.__setattr__(evidence, "test_id", spec.test_id)
    object.__setattr__(evidence, "series", series)
    object.__setattr__(evidence, "policy", spec.bootstrap_policy)
    object.__setattr__(evidence, "sample_size", 3)
    object.__setattr__(evidence, "observed_mean", Decimal("0"))
    object.__setattr__(evidence, "null_resampled_means", ())
    object.__setattr__(evidence, "extreme_count", 0)
    object.__setattr__(evidence, "bootstrap_p_value", Decimal(p_value))
    return evidence


def _result(
    spec: ResearchPreOutcomeBootstrapHypothesisSpec,
    *,
    p_value: str,
    first_recorded_at: datetime,
) -> ResearchPreOutcomeBootstrapEvidence:
    result = object.__new__(ResearchPreOutcomeBootstrapEvidence)
    object.__setattr__(result, "spec", spec)
    object.__setattr__(
        result,
        "test",
        _bootstrap_test(
            spec,
            p_value=p_value,
            first_recorded_at=first_recorded_at,
        ),
    )
    return result


def test_family_spec_canonicalizes_members_and_freezes_membership() -> None:
    first = _spec(1, frozen_at=_BASE)
    second = _spec(2, frozen_at=_BASE + timedelta(seconds=10))

    built = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(900)),
        members=(second, first),
        frozen_at=_BASE + timedelta(seconds=20),
    )

    assert isinstance(built, Success)
    assert built.value.members == (first, second)
    assert built.value.family_size == 2


def test_family_spec_rejects_duplicate_test_ids_or_early_family_freeze() -> None:
    first = _spec(10, frozen_at=_BASE)
    duplicate = replace(
        _spec(11, frozen_at=_BASE),
        test_id=first.test_id,
    )
    duplicate_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(901)),
        members=(first, duplicate),
        frozen_at=_BASE + timedelta(seconds=20),
    )
    early_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(902)),
        members=(first, _spec(12, frozen_at=_BASE + timedelta(minutes=1))),
        frozen_at=_BASE + timedelta(seconds=30),
    )

    assert isinstance(duplicate_result, Failure)
    assert isinstance(early_result, Failure)


def test_family_evidence_binds_every_frozen_member_before_observations() -> None:
    first = _spec(20)
    second = _spec(21)
    family_spec_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(903)),
        members=(first, second),
        frozen_at=_BASE + timedelta(minutes=1),
    )
    assert isinstance(family_spec_result, Success)
    first_result = _result(
        first,
        p_value="0.001",
        first_recorded_at=_BASE + timedelta(minutes=2),
    )
    second_result = _result(
        second,
        p_value="0.01",
        first_recorded_at=_BASE + timedelta(minutes=3),
    )

    built = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(second_result, first_result),
    )

    assert isinstance(built, Success)
    assert built.value.results == (first_result, second_result)
    assert built.value.family_size == 2


def test_family_evidence_rejects_unfrozen_member_or_post_observation_freeze() -> None:
    first = _spec(30)
    second = _spec(31)
    family_spec_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(904)),
        members=(first, second),
        frozen_at=_BASE + timedelta(minutes=2),
    )
    assert isinstance(family_spec_result, Success)

    substituted = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(
            _result(
                first,
                p_value="0.001",
                first_recorded_at=_BASE + timedelta(minutes=3),
            ),
            _result(
                _spec(32),
                p_value="0.01",
                first_recorded_at=_BASE + timedelta(minutes=3),
            ),
        ),
    )
    too_late = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(
            _result(
                first,
                p_value="0.001",
                first_recorded_at=_BASE + timedelta(minutes=1),
            ),
            _result(
                second,
                p_value="0.01",
                first_recorded_at=_BASE + timedelta(minutes=3),
            ),
        ),
    )

    assert isinstance(substituted, Failure)
    assert isinstance(too_late, Failure)


def test_family_holm_consumes_only_exact_preoutcome_family_tests() -> None:
    first = _spec(40)
    second = _spec(41)
    family_spec_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(905)),
        members=(first, second),
        frozen_at=_BASE + timedelta(minutes=1),
    )
    assert isinstance(family_spec_result, Success)
    family_result = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(
            _result(
                first,
                p_value="0.001",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
            _result(
                second,
                p_value="0.01",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
        ),
    )
    assert isinstance(family_result, Success)

    built = build_research_preoutcome_family_holm_evidence(
        family=family_result.value,
        holm_family_id=ResearchHolmFamilyId(_uuid(906)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
    )

    assert isinstance(built, Success)
    assert built.value.holm.tests == family_result.value.tests
    assert built.value.rejection_count == 2


def test_family_holm_rejects_tampered_holm_test_tuple() -> None:
    first = _spec(50)
    second = _spec(51)
    family_spec_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(907)),
        members=(first, second),
        frozen_at=_BASE + timedelta(minutes=1),
    )
    assert isinstance(family_spec_result, Success)
    family_result = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(
            _result(
                first,
                p_value="0.001",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
            _result(
                second,
                p_value="0.01",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
        ),
    )
    assert isinstance(family_result, Success)
    reversed_holm = build_research_holm_familywise_evidence(
        family_id=ResearchHolmFamilyId(_uuid(908)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
        tests=tuple(reversed(family_result.value.tests)),
    )
    assert isinstance(reversed_holm, Success)

    with pytest.raises(ResearchPreOutcomeFamilyValidationError):
        ResearchPreOutcomeFamilyHolmEvidence(
            family=family_result.value,
            holm=reversed_holm.value,
        )


def test_family_holm_makes_no_broad_preregistration_or_production_claims() -> None:
    first = _spec(60)
    second = _spec(61)
    family_spec_result = build_research_preoutcome_family_spec(
        family_id=ResearchPreOutcomeFamilyId(_uuid(909)),
        members=(first, second),
        frozen_at=_BASE + timedelta(minutes=1),
    )
    assert isinstance(family_spec_result, Success)
    family_result = build_research_preoutcome_family_evidence(
        family_spec=family_spec_result.value,
        results=(
            _result(
                first,
                p_value="0.001",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
            _result(
                second,
                p_value="0.01",
                first_recorded_at=_BASE + timedelta(minutes=2),
            ),
        ),
    )
    assert isinstance(family_result, Success)
    built = build_research_preoutcome_family_holm_evidence(
        family=family_result.value,
        holm_family_id=ResearchHolmFamilyId(_uuid(910)),
        policy=ResearchHolmPolicy(familywise_alpha=Decimal("0.05")),
    )
    assert isinstance(built, Success)
    evidence = built.value

    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "no_prior_data_access")
    assert not hasattr(evidence, "preregistered")
    assert not hasattr(evidence, "strategy_approved")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")
