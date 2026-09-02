"""Stress and Monte Carlo robustness orchestration for the Trader Lab.

This module REUSES the existing deterministic research resampling machinery
(``ResearchBlockBootstrapPolicy``, ``ResearchBlockBootstrapDistribution``,
``ResearchResamplingEnvelope``) instead of inventing a new RNG or resampling
engine. It adds pre-registered experiment metadata with frozen
algorithm/family/version/seed/simulation-count/thresholds so that post-hoc
seed hunting, threshold replacement, or unfavorable-simulation deletion always
produces a new identity and cannot reuse a prior qualification.

Monte Carlo evidence here is a descriptive resampling envelope; it never
manufactures edge and never claims a calibrated real-world probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
    ResearchBlockBootstrapPolicy,
)
from qore.infrastructure.research_resampling_envelope import ResearchResamplingEnvelope
from qore.infrastructure.research_serial_dependence import (
    ResearchLagOneCorrelationStatus,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    _validate_sha256,
    _validate_token,
)
from qore.infrastructure.trader_lab.stage_evidence import _canonical_bytes
from qore.kernel.result import Failure, Result, Success


class TraderLabRobustnessFamily(StrEnum):
    """Closed set of supported robustness experiment families."""

    BLOCK_BOOTSTRAP = "block_bootstrap"
    START_SUBWINDOW = "start_subwindow"
    COST_PERTURBATION = "cost_perturbation"
    PARAMETER_NEIGHBORHOOD = "parameter_neighborhood"


class TraderLabMonteCarloStatus(StrEnum):
    """Qualification outcome for Monte Carlo evidence (fail closed by default)."""

    QUALIFIED = "qualified"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    UNSUPPORTED_DEPENDENCE = "unsupported_dependence"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class TraderLabThreshold:
    """A frozen named acceptance threshold (specification data)."""

    name: str
    lower: Decimal | None
    upper: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or fullmatch(
            r"[a-z][a-z0-9._-]{0,79}",
            self.name,
        ) is None:
            raise TraderLabValidationError(
                "threshold name must use canonical lowercase syntax"
            )
        for field_name, value in (("lower", self.lower), ("upper", self.upper)):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise TraderLabValidationError(
                    f"threshold {field_name} must be a finite Decimal or None"
                )
        if self.lower is None and self.upper is None:
            raise TraderLabValidationError(
                "threshold requires at least one bound"
            )
        if (
            self.lower is not None
            and self.upper is not None
            and self.lower > self.upper
        ):
            raise TraderLabValidationError(
                "threshold lower bound must not exceed upper bound"
            )

    def logical_values(self) -> tuple[str, str | None, str | None]:
        return (
            self.name,
            format(self.lower, "f") if self.lower is not None else None,
            format(self.upper, "f") if self.upper is not None else None,
        )


@dataclass(frozen=True, slots=True)
class TraderLabExperimentId:
    """Immutable identity of one pre-registered experiment."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError("experiment id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabExperimentFingerprint:
    """Canonical SHA-256 digest of the pre-registered experiment metadata."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="experiment fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_trader_lab_experiment_fingerprint(
    *,
    experiment_id: TraderLabExperimentId,
    candidate: TraderLabCandidateBinding,
    family: TraderLabRobustnessFamily,
    algorithm: str,
    algorithm_version: str,
    block_length: int | None,
    seed: int | None,
    simulation_count: int,
    min_sample_size: int,
    thresholds: tuple[TraderLabThreshold, ...],
    registered_at: datetime,
) -> TraderLabExperimentFingerprint:
    """Hash the complete frozen experiment metadata (before outcome inspection)."""

    if not isinstance(experiment_id, TraderLabExperimentId):
        raise TraderLabValidationError("experiment_id must be TraderLabExperimentId")
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(family, TraderLabRobustnessFamily):
        raise TraderLabValidationError("family must be TraderLabRobustnessFamily")
    _validate_token(algorithm, field_name="experiment algorithm")
    _validate_token(algorithm_version, field_name="experiment algorithm version")
    ordered_thresholds = tuple(
        sorted(thresholds, key=lambda item: item.name)
    )
    canonical = {
        "schema": "qore.trader_lab.experiment_registration.v1",
        "experiment_id": str(experiment_id.value),
        "candidate_fingerprint": candidate.fingerprint.value,
        "family": family.value,
        "algorithm": algorithm,
        "algorithm_version": algorithm_version,
        "block_length": block_length,
        "seed": seed,
        "simulation_count": simulation_count,
        "min_sample_size": min_sample_size,
        "thresholds": [list(item.logical_values()) for item in ordered_thresholds],
        "registered_at": registered_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
    }
    return TraderLabExperimentFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderLabExperimentRegistration:
    """Pre-registered robustness experiment metadata, frozen before outcomes."""

    experiment_id: TraderLabExperimentId
    candidate: TraderLabCandidateBinding
    family: TraderLabRobustnessFamily
    algorithm: str
    algorithm_version: str
    block_length: int | None
    seed: int | None
    simulation_count: int
    min_sample_size: int
    thresholds: tuple[TraderLabThreshold, ...]
    registered_at: datetime
    fingerprint: TraderLabExperimentFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_id, TraderLabExperimentId):
            raise TraderLabValidationError("experiment_id must be TraderLabExperimentId")
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        if not isinstance(self.family, TraderLabRobustnessFamily):
            raise TraderLabValidationError("family must be TraderLabRobustnessFamily")
        _validate_token(self.algorithm, field_name="experiment algorithm")
        _validate_token(self.algorithm_version, field_name="experiment algorithm version")
        if self.block_length is not None and (
            type(self.block_length) is not int or self.block_length < 2
        ):
            raise TraderLabValidationError(
                "block_length must be an integer of at least two or None"
            )
        if self.seed is not None and (type(self.seed) is not int or self.seed < 0):
            raise TraderLabValidationError(
                "seed must be a non-negative integer or None"
            )
        if type(self.simulation_count) is not int or self.simulation_count <= 0:
            raise TraderLabValidationError(
                "simulation_count must be a positive integer"
            )
        if type(self.min_sample_size) is not int or self.min_sample_size < 2:
            raise TraderLabValidationError(
                "min_sample_size must be an integer of at least two"
            )
        if self.family is TraderLabRobustnessFamily.BLOCK_BOOTSTRAP:
            if self.block_length is None or self.seed is None:
                raise TraderLabValidationError(
                    "block bootstrap registration requires block_length and seed"
                )
        if not isinstance(self.thresholds, tuple) or any(
            not isinstance(item, TraderLabThreshold) for item in self.thresholds
        ):
            raise TraderLabValidationError(
                "thresholds must be an immutable TraderLabThreshold tuple"
            )
        if len({item.name for item in self.thresholds}) != len(self.thresholds):
            raise TraderLabValidationError("threshold names must be unique")
        _validate_timestamp(self.registered_at, field_name="registration registered_at")
        if not isinstance(self.fingerprint, TraderLabExperimentFingerprint):
            raise TraderLabValidationError(
                "fingerprint must be TraderLabExperimentFingerprint"
            )
        expected = compute_trader_lab_experiment_fingerprint(
            experiment_id=self.experiment_id,
            candidate=self.candidate,
            family=self.family,
            algorithm=self.algorithm,
            algorithm_version=self.algorithm_version,
            block_length=self.block_length,
            seed=self.seed,
            simulation_count=self.simulation_count,
            min_sample_size=self.min_sample_size,
            thresholds=self.thresholds,
            registered_at=self.registered_at,
        )
        if self.fingerprint != expected:
            raise TraderLabValidationError(
                "experiment fingerprint must match the exact registration"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.experiment_id.logical_values(),
            self.candidate.fingerprint.logical_values(),
            self.family.value,
            self.algorithm,
            self.algorithm_version,
            self.block_length,
            self.seed,
            self.simulation_count,
            self.min_sample_size,
            tuple(item.logical_values() for item in self.thresholds),
            self.registered_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.fingerprint.logical_values(),
        )


def build_trader_lab_experiment_registration(
    *,
    experiment_id: TraderLabExperimentId,
    candidate: TraderLabCandidateBinding,
    family: TraderLabRobustnessFamily,
    algorithm: str,
    algorithm_version: str,
    block_length: int | None,
    seed: int | None,
    simulation_count: int,
    min_sample_size: int,
    thresholds: tuple[TraderLabThreshold, ...],
    registered_at: datetime,
) -> Result[TraderLabExperimentRegistration, TraderLabError]:
    """Freeze experiment metadata before any outcome is inspected."""

    try:
        fingerprint = compute_trader_lab_experiment_fingerprint(
            experiment_id=experiment_id,
            candidate=candidate,
            family=family,
            algorithm=algorithm,
            algorithm_version=algorithm_version,
            block_length=block_length,
            seed=seed,
            simulation_count=simulation_count,
            min_sample_size=min_sample_size,
            thresholds=thresholds,
            registered_at=registered_at,
        )
        return Success(
            TraderLabExperimentRegistration(
                experiment_id=experiment_id,
                candidate=candidate,
                family=family,
                algorithm=algorithm,
                algorithm_version=algorithm_version,
                block_length=block_length,
                seed=seed,
                simulation_count=simulation_count,
                min_sample_size=min_sample_size,
                thresholds=thresholds,
                registered_at=registered_at,
                fingerprint=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class TraderLabCostPerturbationSpec:
    """Explicit cost/spread/slippage perturbation bounds (specification data).

    These are declared bounds, not hidden assumptions. They do not re-run the
    economic evaluation; actual perturbed evidence is referenced, not fabricated.
    """

    spread_bps: int
    slippage_bps: int
    cost_bps: int

    def __post_init__(self) -> None:
        for field_name, value in (
            ("spread_bps", self.spread_bps),
            ("slippage_bps", self.slippage_bps),
            ("cost_bps", self.cost_bps),
        ):
            if type(value) is not int or value < 0:
                raise TraderLabValidationError(
                    f"{field_name} must be a non-negative integer"
                )

    def logical_values(self) -> tuple[int, int, int]:
        return (self.spread_bps, self.slippage_bps, self.cost_bps)


@dataclass(frozen=True, slots=True)
class TraderLabMonteCarloEvidenceId:
    """Immutable identity of one Monte Carlo experiment evidence record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError(
                "Monte Carlo evidence id must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabMonteCarloFingerprint:
    """Canonical SHA-256 digest of the Monte Carlo experiment evidence."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="Monte Carlo fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _derive_monte_carlo_status(
    registration: TraderLabExperimentRegistration,
    distribution: ResearchBlockBootstrapDistribution,
) -> TraderLabMonteCarloStatus:
    if distribution.sample_size < registration.min_sample_size:
        return TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE
    diagnostic_status = distribution.diagnostic.status
    if diagnostic_status is ResearchLagOneCorrelationStatus.UNDEFINED_ZERO_VARIANCE:
        return TraderLabMonteCarloStatus.UNSUPPORTED_DEPENDENCE
    if diagnostic_status is ResearchLagOneCorrelationStatus.INSUFFICIENT_SAMPLE:
        return TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE
    return TraderLabMonteCarloStatus.QUALIFIED


def compute_trader_lab_monte_carlo_fingerprint(
    *,
    registration: TraderLabExperimentRegistration,
    policy: ResearchBlockBootstrapPolicy,
    distribution: ResearchBlockBootstrapDistribution,
    envelope: ResearchResamplingEnvelope,
    status: TraderLabMonteCarloStatus,
) -> TraderLabMonteCarloFingerprint:
    """Hash the exact orchestration and its fail-closed qualification status."""

    if not isinstance(registration, TraderLabExperimentRegistration):
        raise TraderLabValidationError(
            "registration must be TraderLabExperimentRegistration"
        )
    if not isinstance(policy, ResearchBlockBootstrapPolicy):
        raise TraderLabValidationError("policy must be ResearchBlockBootstrapPolicy")
    if not isinstance(distribution, ResearchBlockBootstrapDistribution):
        raise TraderLabValidationError(
            "distribution must be ResearchBlockBootstrapDistribution"
        )
    if not isinstance(envelope, ResearchResamplingEnvelope):
        raise TraderLabValidationError("envelope must be ResearchResamplingEnvelope")
    if not isinstance(status, TraderLabMonteCarloStatus):
        raise TraderLabValidationError("status must be TraderLabMonteCarloStatus")
    canonical = {
        "schema": "qore.trader_lab.monte_carlo.v1",
        "registration_fingerprint": registration.fingerprint.value,
        "policy": list(policy.logical_values()),
        "distribution_id": str(distribution.distribution_id.value),
        "sample_size": distribution.sample_size,
        "source_mean": format(distribution.source_mean, "f"),
        "resampled_means": [
            format(value, "f") for value in distribution.resampled_means
        ],
        "envelope_id": str(envelope.envelope_id.value),
        "status": status.value,
    }
    return TraderLabMonteCarloFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderLabMonteCarloExperimentEvidence:
    """Monte Carlo evidence reusing the existing block-bootstrap envelope.

    The status is derived fail-closed: insufficient samples or unsupported
    dependence assumptions can never yield ``QUALIFIED``. This is a descriptive
    resampling envelope, not a calibrated probability or edge claim.
    """

    evidence_id: TraderLabMonteCarloEvidenceId
    registration: TraderLabExperimentRegistration
    policy: ResearchBlockBootstrapPolicy
    distribution: ResearchBlockBootstrapDistribution
    envelope: ResearchResamplingEnvelope
    status: TraderLabMonteCarloStatus
    fingerprint: TraderLabMonteCarloFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, TraderLabMonteCarloEvidenceId):
            raise TraderLabValidationError(
                "evidence_id must be TraderLabMonteCarloEvidenceId"
            )
        if not isinstance(self.registration, TraderLabExperimentRegistration):
            raise TraderLabValidationError(
                "registration must be TraderLabExperimentRegistration"
            )
        if self.registration.family is not TraderLabRobustnessFamily.BLOCK_BOOTSTRAP:
            raise TraderLabValidationError(
                "Monte Carlo evidence requires a block bootstrap registration"
            )
        if not isinstance(self.policy, ResearchBlockBootstrapPolicy):
            raise TraderLabValidationError("policy must be ResearchBlockBootstrapPolicy")
        if not isinstance(self.distribution, ResearchBlockBootstrapDistribution):
            raise TraderLabValidationError(
                "distribution must be ResearchBlockBootstrapDistribution"
            )
        if not isinstance(self.envelope, ResearchResamplingEnvelope):
            raise TraderLabValidationError("envelope must be ResearchResamplingEnvelope")
        if not isinstance(self.status, TraderLabMonteCarloStatus):
            raise TraderLabValidationError("status must be TraderLabMonteCarloStatus")
        if self.registration.block_length != self.policy.block_length:
            raise TraderLabValidationError(
                "policy block_length must match the frozen registration"
            )
        if self.registration.simulation_count != self.policy.resample_count:
            raise TraderLabValidationError(
                "policy resample_count must match the frozen simulation_count"
            )
        if self.registration.seed != self.policy.seed:
            raise TraderLabValidationError(
                "policy seed must match the frozen registration seed"
            )
        if self.distribution.policy != self.policy:
            raise TraderLabValidationError(
                "distribution policy must equal the supplied policy exactly"
            )
        if self.envelope.distribution != self.distribution:
            raise TraderLabValidationError(
                "envelope distribution must equal the supplied distribution exactly"
            )
        expected_status = _derive_monte_carlo_status(
            self.registration,
            self.distribution,
        )
        if self.status is not expected_status:
            raise TraderLabValidationError(
                "Monte Carlo status must match the derived fail-closed status"
            )
        if not isinstance(self.fingerprint, TraderLabMonteCarloFingerprint):
            raise TraderLabValidationError(
                "fingerprint must be TraderLabMonteCarloFingerprint"
            )
        expected = compute_trader_lab_monte_carlo_fingerprint(
            registration=self.registration,
            policy=self.policy,
            distribution=self.distribution,
            envelope=self.envelope,
            status=self.status,
        )
        if self.fingerprint != expected:
            raise TraderLabValidationError(
                "Monte Carlo fingerprint must match the exact evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.registration.fingerprint.logical_values(),
            self.policy.logical_values(),
            self.distribution.logical_values(),
            self.envelope.logical_values(),
            self.status.value,
            self.fingerprint.logical_values(),
        )


def build_trader_lab_monte_carlo_experiment_evidence(
    *,
    evidence_id: TraderLabMonteCarloEvidenceId,
    registration: TraderLabExperimentRegistration,
    policy: ResearchBlockBootstrapPolicy,
    distribution: ResearchBlockBootstrapDistribution,
    envelope: ResearchResamplingEnvelope,
) -> Result[TraderLabMonteCarloExperimentEvidence, TraderLabError]:
    """Orchestrate existing resampling evidence into fail-closed Monte Carlo evidence."""

    try:
        if not isinstance(registration, TraderLabExperimentRegistration):
            raise TraderLabValidationError(
                "registration must be TraderLabExperimentRegistration"
            )
        if registration.family is not TraderLabRobustnessFamily.BLOCK_BOOTSTRAP:
            raise TraderLabValidationError(
                "Monte Carlo evidence requires a block bootstrap registration"
            )
        if not isinstance(distribution, ResearchBlockBootstrapDistribution):
            raise TraderLabValidationError(
                "distribution must be ResearchBlockBootstrapDistribution"
            )
        status = _derive_monte_carlo_status(registration, distribution)
        fingerprint = compute_trader_lab_monte_carlo_fingerprint(
            registration=registration,
            policy=policy,
            distribution=distribution,
            envelope=envelope,
            status=status,
        )
        return Success(
            TraderLabMonteCarloExperimentEvidence(
                evidence_id=evidence_id,
                registration=registration,
                policy=policy,
                distribution=distribution,
                envelope=envelope,
                status=status,
                fingerprint=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)
