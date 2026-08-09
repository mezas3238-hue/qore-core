from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityValuationBasis,
    ResearchPeriodicEquityPolicy,
    ResearchValuationModelBinding,
    ResearchValuationModelId,
)
from qore.infrastructure.research_run import ResearchRunInputFingerprint
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchPreOutcomeHypothesisError(InfrastructureError):
    """Base error for pre-outcome research hypothesis evidence."""

    __slots__ = ()


class ResearchPreOutcomeHypothesisValidationError(ResearchPreOutcomeHypothesisError):
    """Violation of a pre-outcome hypothesis invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchPreOutcomeHypothesisValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchPreOutcomeHypothesisValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._/+:-]*",
        value,
    ) is None:
        raise ResearchPreOutcomeHypothesisValidationError(
            f"{field_name} must use canonical token syntax"
        )


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeHypothesisSpecId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPreOutcomeHypothesisValidationError(
                "pre-outcome hypothesis spec id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeBootstrapHypothesisSpec:
    """Bootstrap hypothesis specification frozen before result observations.

    The specification binds stable run-input identity, valuation semantics,
    fixed-period sampling policy and bootstrap-test policy without embedding any
    realized equity series or p-value.

    `frozen_at` is process/evidence time only. It is never compared with
    historical simulated market time.
    """

    spec_id: ResearchPreOutcomeHypothesisSpecId
    test_id: ResearchPeriodicBootstrapTestId
    run_input_fingerprint: ResearchRunInputFingerprint
    valuation_model_id: ResearchValuationModelId
    valuation_model_version: str
    valuation_basis: ResearchEquityValuationBasis
    periodic_policy: ResearchPeriodicEquityPolicy
    bootstrap_policy: ResearchPeriodicBootstrapTestPolicy
    frozen_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.spec_id, ResearchPreOutcomeHypothesisSpecId):
            raise ResearchPreOutcomeHypothesisValidationError(
                "spec_id must be ResearchPreOutcomeHypothesisSpecId"
            )
        if not isinstance(self.test_id, ResearchPeriodicBootstrapTestId):
            raise ResearchPreOutcomeHypothesisValidationError(
                "test_id must be ResearchPeriodicBootstrapTestId"
            )
        if not isinstance(self.run_input_fingerprint, ResearchRunInputFingerprint):
            raise ResearchPreOutcomeHypothesisValidationError(
                "run_input_fingerprint must be ResearchRunInputFingerprint"
            )
        if not isinstance(self.valuation_model_id, ResearchValuationModelId):
            raise ResearchPreOutcomeHypothesisValidationError(
                "valuation_model_id must be ResearchValuationModelId"
            )
        _validate_token(
            self.valuation_model_version,
            field_name="valuation_model_version",
        )
        if not isinstance(self.valuation_basis, ResearchEquityValuationBasis):
            raise ResearchPreOutcomeHypothesisValidationError(
                "valuation_basis must be ResearchEquityValuationBasis"
            )
        if not isinstance(self.periodic_policy, ResearchPeriodicEquityPolicy):
            raise ResearchPreOutcomeHypothesisValidationError(
                "periodic_policy must be ResearchPeriodicEquityPolicy"
            )
        if not isinstance(
            self.bootstrap_policy,
            ResearchPeriodicBootstrapTestPolicy,
        ):
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap_policy must be ResearchPeriodicBootstrapTestPolicy"
            )
        _validate_timestamp(self.frozen_at, field_name="hypothesis frozen_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.spec_id.logical_values(),
            self.test_id.logical_values(),
            self.run_input_fingerprint.logical_values(),
            self.valuation_model_id.logical_values(),
            self.valuation_model_version,
            self.valuation_basis.value,
            self.periodic_policy.logical_values(),
            self.bootstrap_policy.logical_values(),
            self.frozen_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ResearchPreOutcomeBootstrapEvidence:
    """Bootstrap result proven compatible with one earlier frozen specification.

    Every periodic equity observation must have been recorded at or after the
    specification freeze. This proves a narrow pre-observation chronology on the
    research/process evidence axis and exact specification/result binding.

    It does not prove analyst blindness, absence of prior data access or prior
    experimentation, broad preregistration, predictive validity, or production
    fitness.
    """

    spec: ResearchPreOutcomeBootstrapHypothesisSpec
    test: ResearchPeriodicBootstrapTestEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.spec, ResearchPreOutcomeBootstrapHypothesisSpec):
            raise ResearchPreOutcomeHypothesisValidationError(
                "pre-outcome evidence requires ResearchPreOutcomeBootstrapHypothesisSpec"
            )
        if not isinstance(self.test, ResearchPeriodicBootstrapTestEvidence):
            raise ResearchPreOutcomeHypothesisValidationError(
                "pre-outcome evidence requires ResearchPeriodicBootstrapTestEvidence"
            )
        if self.test.test_id != self.spec.test_id:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap test id must match the frozen hypothesis specification"
            )
        series = self.test.series
        binding = series.binding
        if not isinstance(binding, ResearchValuationModelBinding):
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap series must retain ResearchValuationModelBinding"
            )
        if binding.run.input_fingerprint != self.spec.run_input_fingerprint:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap run input fingerprint must match the frozen specification"
            )
        if binding.model_id != self.spec.valuation_model_id:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap valuation model id must match the frozen specification"
            )
        if binding.model_version != self.spec.valuation_model_version:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap valuation model version must match the frozen specification"
            )
        if binding.basis is not self.spec.valuation_basis:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap valuation basis must match the frozen specification"
            )
        if series.policy != self.spec.periodic_policy:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap periodic policy must match the frozen specification"
            )
        if self.test.policy != self.spec.bootstrap_policy:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap test policy must match the frozen specification"
            )
        observations = series.observations
        if not observations:
            raise ResearchPreOutcomeHypothesisValidationError(
                "bootstrap periodic series must retain valuation observations"
            )
        if any(
            observation.recorded_at < self.spec.frozen_at
            for observation in observations
        ):
            raise ResearchPreOutcomeHypothesisValidationError(
                "hypothesis specification must not postdate any recorded equity observation"
            )

    @property
    def earliest_observation_recorded_at(self) -> datetime:
        return min(observation.recorded_at for observation in self.test.series.observations)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.spec.logical_values(),
            self.test.logical_values(),
        )


def build_research_preoutcome_bootstrap_evidence(
    *,
    spec: ResearchPreOutcomeBootstrapHypothesisSpec,
    test: ResearchPeriodicBootstrapTestEvidence,
) -> Result[ResearchPreOutcomeBootstrapEvidence, ResearchPreOutcomeHypothesisError]:
    """Bind one bootstrap result to an earlier frozen result-free specification."""

    try:
        return Success(
            ResearchPreOutcomeBootstrapEvidence(
                spec=spec,
                test=test,
            )
        )
    except ResearchPreOutcomeHypothesisError as error:
        return Failure(error)
