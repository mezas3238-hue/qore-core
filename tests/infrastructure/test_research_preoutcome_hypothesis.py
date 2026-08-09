from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapAlternative,
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityFlowStatus,
    ResearchEquityValuationBasis,
    ResearchEquityValuationObservation,
    ResearchPeriodicEquityPolicy,
    ResearchPeriodicEquityReturnSeries,
    ResearchValuationModelBinding,
    ResearchValuationModelId,
)
from qore.infrastructure.research_preoutcome_hypothesis import (
    ResearchPreOutcomeBootstrapHypothesisSpec,
    ResearchPreOutcomeHypothesisSpecId,
    ResearchPreOutcomeHypothesisValidationError,
    build_research_preoutcome_bootstrap_evidence,
)
from qore.infrastructure.research_run import (
    ResearchRunEvidence,
    ResearchRunInputFingerprint,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"91000000-0000-0000-0000-{suffix:012d}")


def _bootstrap_policy(seed: int = 1) -> ResearchPeriodicBootstrapTestPolicy:
    return ResearchPeriodicBootstrapTestPolicy(
        null_mean_per_period=Decimal("0"),
        alternative=ResearchPeriodicBootstrapAlternative.GREATER,
        block_length=2,
        resample_count=12,
        seed=seed,
    )


def _run(fingerprint: str = "a" * 64) -> ResearchRunEvidence:
    run = object.__new__(ResearchRunEvidence)
    object.__setattr__(run, "input_fingerprint", ResearchRunInputFingerprint(fingerprint))
    return run


def _binding(
    *,
    fingerprint: str = "a" * 64,
    model_suffix: int = 1,
    version: str = "valuation.v1",
    basis: ResearchEquityValuationBasis = ResearchEquityValuationBasis.GROSS,
) -> ResearchValuationModelBinding:
    binding = object.__new__(ResearchValuationModelBinding)
    object.__setattr__(binding, "run", _run(fingerprint))
    object.__setattr__(binding, "model_id", ResearchValuationModelId(_uuid(model_suffix)))
    object.__setattr__(binding, "model_version", version)
    object.__setattr__(binding, "basis", basis)
    return binding


def _observation(recorded_at: datetime) -> ResearchEquityValuationObservation:
    observation = object.__new__(ResearchEquityValuationObservation)
    object.__setattr__(observation, "recorded_at", recorded_at)
    object.__setattr__(
        observation,
        "flow_status_since_prior",
        ResearchEquityFlowStatus.NO_EXTERNAL_FLOW,
    )
    return observation


def _test_evidence(
    *,
    test_suffix: int = 10,
    fingerprint: str = "a" * 64,
    model_suffix: int = 1,
    model_version: str = "valuation.v1",
    basis: ResearchEquityValuationBasis = ResearchEquityValuationBasis.GROSS,
    periodic_policy: ResearchPeriodicEquityPolicy | None = None,
    bootstrap_policy: ResearchPeriodicBootstrapTestPolicy | None = None,
    observation_times: tuple[datetime, ...] = (_BASE, _BASE + timedelta(hours=1)),
) -> ResearchPeriodicBootstrapTestEvidence:
    periodic = periodic_policy or ResearchPeriodicEquityPolicy(interval_seconds=3_600)
    bootstrap = bootstrap_policy or _bootstrap_policy()
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(
        series,
        "binding",
        _binding(
            fingerprint=fingerprint,
            model_suffix=model_suffix,
            version=model_version,
            basis=basis,
        ),
    )
    object.__setattr__(series, "policy", periodic)
    object.__setattr__(
        series,
        "observations",
        tuple(_observation(value) for value in observation_times),
    )
    evidence = object.__new__(ResearchPeriodicBootstrapTestEvidence)
    object.__setattr__(
        evidence,
        "test_id",
        ResearchPeriodicBootstrapTestId(_uuid(test_suffix)),
    )
    object.__setattr__(evidence, "series", series)
    object.__setattr__(evidence, "policy", bootstrap)
    return evidence


def _spec(
    *,
    frozen_at: datetime = _BASE,
    test_suffix: int = 10,
    fingerprint: str = "a" * 64,
    model_suffix: int = 1,
    model_version: str = "valuation.v1",
    basis: ResearchEquityValuationBasis = ResearchEquityValuationBasis.GROSS,
    periodic_policy: ResearchPeriodicEquityPolicy | None = None,
    bootstrap_policy: ResearchPeriodicBootstrapTestPolicy | None = None,
) -> ResearchPreOutcomeBootstrapHypothesisSpec:
    return ResearchPreOutcomeBootstrapHypothesisSpec(
        spec_id=ResearchPreOutcomeHypothesisSpecId(_uuid(100)),
        test_id=ResearchPeriodicBootstrapTestId(_uuid(test_suffix)),
        run_input_fingerprint=ResearchRunInputFingerprint(fingerprint),
        valuation_model_id=ResearchValuationModelId(_uuid(model_suffix)),
        valuation_model_version=model_version,
        valuation_basis=basis,
        periodic_policy=periodic_policy
        or ResearchPeriodicEquityPolicy(interval_seconds=3_600),
        bootstrap_policy=bootstrap_policy or _bootstrap_policy(),
        frozen_at=frozen_at,
    )


def test_preoutcome_evidence_binds_exact_spec_before_recorded_observations() -> None:
    spec = _spec(frozen_at=_BASE)
    test = _test_evidence(
        observation_times=(_BASE, _BASE + timedelta(hours=1)),
    )

    built = build_research_preoutcome_bootstrap_evidence(spec=spec, test=test)

    assert isinstance(built, Success)
    assert built.value.spec is spec
    assert built.value.test is test
    assert built.value.earliest_observation_recorded_at == _BASE


def test_preoutcome_evidence_rejects_freeze_after_any_recorded_observation() -> None:
    spec = _spec(frozen_at=_BASE + timedelta(minutes=1))
    test = _test_evidence(
        observation_times=(_BASE, _BASE + timedelta(hours=1)),
    )

    built = build_research_preoutcome_bootstrap_evidence(spec=spec, test=test)

    assert isinstance(built, Failure)
    assert "must not postdate" in str(built.error)


def test_preoutcome_evidence_rejects_run_or_valuation_mismatch() -> None:
    base_test = _test_evidence()

    wrong_run = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(fingerprint="b" * 64),
        test=base_test,
    )
    wrong_model = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(model_suffix=2),
        test=base_test,
    )
    wrong_version = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(model_version="valuation.v2"),
        test=base_test,
    )

    assert isinstance(wrong_run, Failure)
    assert isinstance(wrong_model, Failure)
    assert isinstance(wrong_version, Failure)


def test_preoutcome_evidence_rejects_periodic_or_bootstrap_policy_mismatch() -> None:
    test = _test_evidence()
    wrong_periodic = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(periodic_policy=ResearchPeriodicEquityPolicy(interval_seconds=1_800)),
        test=test,
    )
    wrong_bootstrap = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(bootstrap_policy=_bootstrap_policy(seed=2)),
        test=test,
    )

    assert isinstance(wrong_periodic, Failure)
    assert isinstance(wrong_bootstrap, Failure)


def test_preoutcome_evidence_rejects_test_id_mismatch() -> None:
    built = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(test_suffix=20),
        test=_test_evidence(test_suffix=21),
    )

    assert isinstance(built, Failure)
    assert "test id" in str(built.error)


def test_preoutcome_spec_requires_aware_process_timestamp() -> None:
    with pytest.raises(ResearchPreOutcomeHypothesisValidationError):
        _spec(frozen_at=datetime(2026, 8, 9, 20, 0))


def test_preoutcome_spec_rejects_noncanonical_valuation_version() -> None:
    with pytest.raises(ResearchPreOutcomeHypothesisValidationError):
        _spec(model_version="valuation version")


def test_preoutcome_evidence_rejects_derived_spec_tampering() -> None:
    spec = _spec()
    test = _test_evidence()
    built = build_research_preoutcome_bootstrap_evidence(spec=spec, test=test)
    assert isinstance(built, Success)

    with pytest.raises(ResearchPreOutcomeHypothesisValidationError):
        replace(
            built.value,
            spec=replace(spec, run_input_fingerprint=ResearchRunInputFingerprint("c" * 64)),
        )


def test_preoutcome_evidence_makes_no_broad_preregistration_or_production_claims() -> None:
    built = build_research_preoutcome_bootstrap_evidence(
        spec=_spec(),
        test=_test_evidence(),
    )
    assert isinstance(built, Success)
    evidence = built.value

    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "no_prior_data_access")
    assert not hasattr(evidence, "no_prior_experimentation")
    assert not hasattr(evidence, "preregistered")
    assert not hasattr(evidence, "predictive_validity")
    assert not hasattr(evidence, "production_ready")
