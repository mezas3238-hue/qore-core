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
    _canonical_decimal,
    _validate_sha256,
    _validate_token,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    _canonical_bytes,
    _make_self_authenticating_reference,
)
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
    THRESHOLD_VIOLATION = "threshold_violation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


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
            _canonical_decimal(self.lower) if self.lower is not None else None,
            _canonical_decimal(self.upper) if self.upper is not None else None,
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


def _canonical_thresholds(
    thresholds: tuple[TraderLabThreshold, ...],
) -> tuple[TraderLabThreshold, ...]:
    """Validate and return thresholds in canonical name order (unique names)."""

    if not isinstance(thresholds, tuple) or any(
        not isinstance(item, TraderLabThreshold) for item in thresholds
    ):
        raise TraderLabValidationError(
            "thresholds must be an immutable TraderLabThreshold tuple"
        )
    names = [item.name for item in thresholds]
    if len(set(names)) != len(names):
        raise TraderLabValidationError("threshold names must be unique")
    return tuple(sorted(thresholds, key=lambda item: item.name))


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
    if block_length is not None and (
        type(block_length) is not int or block_length < 2
    ):
        raise TraderLabValidationError(
            "block_length must be an integer of at least two or None"
        )
    if seed is not None and (type(seed) is not int or seed < 0):
        raise TraderLabValidationError(
            "seed must be a non-negative integer or None"
        )
    if type(simulation_count) is not int or simulation_count <= 0:
        raise TraderLabValidationError(
            "simulation_count must be a positive integer"
        )
    if type(min_sample_size) is not int or min_sample_size < 2:
        raise TraderLabValidationError(
            "min_sample_size must be an integer of at least two"
        )
    _validate_timestamp(registered_at, field_name="registration registered_at")
    ordered_thresholds = _canonical_thresholds(thresholds)
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
        if self.thresholds != _canonical_thresholds(self.thresholds):
            raise TraderLabValidationError(
                "thresholds must use canonical name order with unique names"
            )
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
            tuple(
                item.logical_values()
                for item in _canonical_thresholds(self.thresholds)
            ),
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
        canonical_thresholds = _canonical_thresholds(thresholds)
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
            thresholds=canonical_thresholds,
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
                thresholds=canonical_thresholds,
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


def _threshold_metric_value(
    name: str,
    distribution: ResearchBlockBootstrapDistribution,
    envelope: ResearchResamplingEnvelope,
) -> Decimal | None:
    """Resolve a registered acceptance-threshold metric to authoritative evidence.

    Only these four deterministic mean-return magnitudes are evaluable; any other
    name (profitability, edge, significance, etc.) is unsupported and fails closed.
    """

    if name == "distribution.source_mean":
        return distribution.source_mean
    if name == "envelope.lower_mean":
        return envelope.lower_mean
    if name == "envelope.median_mean":
        return envelope.median_mean
    if name == "envelope.upper_mean":
        return envelope.upper_mean
    return None


def _derive_monte_carlo_status(
    registration: TraderLabExperimentRegistration,
    distribution: ResearchBlockBootstrapDistribution,
    envelope: ResearchResamplingEnvelope,
) -> TraderLabMonteCarloStatus:
    if not isinstance(registration, TraderLabExperimentRegistration):
        raise TraderLabValidationError(
            "Monte Carlo status derivation requires TraderLabExperimentRegistration"
        )
    if not isinstance(distribution, ResearchBlockBootstrapDistribution):
        raise TraderLabValidationError(
            "Monte Carlo status derivation requires ResearchBlockBootstrapDistribution"
        )
    if not isinstance(envelope, ResearchResamplingEnvelope):
        raise TraderLabValidationError(
            "Monte Carlo status derivation requires ResearchResamplingEnvelope"
        )
    if envelope.distribution != distribution:
        raise TraderLabValidationError(
            "envelope distribution must equal the supplied distribution exactly"
        )
    if distribution.sample_size < registration.min_sample_size:
        return TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE
    diagnostic_status = distribution.diagnostic.status
    if diagnostic_status is ResearchLagOneCorrelationStatus.UNDEFINED_ZERO_VARIANCE:
        return TraderLabMonteCarloStatus.UNSUPPORTED_DEPENDENCE
    if diagnostic_status is ResearchLagOneCorrelationStatus.INSUFFICIENT_SAMPLE:
        return TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE
    if not registration.thresholds:
        return TraderLabMonteCarloStatus.INSUFFICIENT_EVIDENCE
    for threshold in registration.thresholds:
        value = _threshold_metric_value(threshold.name, distribution, envelope)
        if value is None:
            return TraderLabMonteCarloStatus.INSUFFICIENT_EVIDENCE
        if threshold.lower is not None and value < threshold.lower:
            return TraderLabMonteCarloStatus.THRESHOLD_VIOLATION
        if threshold.upper is not None and value > threshold.upper:
            return TraderLabMonteCarloStatus.THRESHOLD_VIOLATION
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
        "schema": "qore.trader_lab.monte_carlo.v2",
        "registration_fingerprint": registration.fingerprint.value,
        "policy": list(policy.logical_values()),
        "distribution_id": str(distribution.distribution_id.value),
        "sample_size": distribution.sample_size,
        "source_mean": _canonical_decimal(distribution.source_mean),
        "resampled_means": [
            _canonical_decimal(value) for value in distribution.resampled_means
        ],
        "envelope_id": str(envelope.envelope_id.value),
        "empirical_sample_size": envelope.empirical_sample_size,
        "lower_mean": _canonical_decimal(envelope.lower_mean),
        "median_mean": _canonical_decimal(envelope.median_mean),
        "upper_mean": _canonical_decimal(envelope.upper_mean),
        "status": status.value,
    }
    return TraderLabMonteCarloFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


def validate_trader_lab_monte_carlo_experiment_evidence(
    evidence: TraderLabMonteCarloExperimentEvidence,
) -> None:
    """Re-validate Monte Carlo experiment evidence at a trust boundary."""

    if not isinstance(evidence, TraderLabMonteCarloExperimentEvidence):
        raise TraderLabValidationError(
            "evidence must be TraderLabMonteCarloExperimentEvidence"
        )
    if not isinstance(evidence.evidence_id, TraderLabMonteCarloEvidenceId):
        raise TraderLabValidationError(
            "evidence_id must be TraderLabMonteCarloEvidenceId"
        )
    if not isinstance(evidence.registration, TraderLabExperimentRegistration):
        raise TraderLabValidationError(
            "registration must be TraderLabExperimentRegistration"
        )
    if evidence.registration.family is not TraderLabRobustnessFamily.BLOCK_BOOTSTRAP:
        raise TraderLabValidationError(
            "Monte Carlo evidence requires a block bootstrap registration"
        )
    if not isinstance(evidence.policy, ResearchBlockBootstrapPolicy):
        raise TraderLabValidationError("policy must be ResearchBlockBootstrapPolicy")
    if not isinstance(evidence.distribution, ResearchBlockBootstrapDistribution):
        raise TraderLabValidationError(
            "distribution must be ResearchBlockBootstrapDistribution"
        )
    if not isinstance(evidence.envelope, ResearchResamplingEnvelope):
        raise TraderLabValidationError("envelope must be ResearchResamplingEnvelope")
    if not isinstance(evidence.status, TraderLabMonteCarloStatus):
        raise TraderLabValidationError("status must be TraderLabMonteCarloStatus")
    if evidence.registration.block_length != evidence.policy.block_length:
        raise TraderLabValidationError(
            "policy block_length must match the frozen registration"
        )
    if evidence.registration.simulation_count != evidence.policy.resample_count:
        raise TraderLabValidationError(
            "policy resample_count must match the frozen simulation_count"
        )
    if evidence.registration.seed != evidence.policy.seed:
        raise TraderLabValidationError(
            "policy seed must match the frozen registration seed"
        )
    if evidence.distribution.policy != evidence.policy:
        raise TraderLabValidationError(
            "distribution policy must equal the supplied policy exactly"
        )
    if evidence.envelope.distribution != evidence.distribution:
        raise TraderLabValidationError(
            "envelope distribution must equal the supplied distribution exactly"
        )
    expected_status = _derive_monte_carlo_status(
        evidence.registration,
        evidence.distribution,
        evidence.envelope,
    )
    if evidence.status is not expected_status:
        raise TraderLabValidationError(
            "Monte Carlo status must match the derived fail-closed status"
        )
    if not isinstance(evidence.fingerprint, TraderLabMonteCarloFingerprint):
        raise TraderLabValidationError(
            "fingerprint must be TraderLabMonteCarloFingerprint"
        )
    expected = compute_trader_lab_monte_carlo_fingerprint(
        registration=evidence.registration,
        policy=evidence.policy,
        distribution=evidence.distribution,
        envelope=evidence.envelope,
        status=evidence.status,
    )
    if evidence.fingerprint != expected:
        raise TraderLabValidationError(
            "Monte Carlo fingerprint must match the exact evidence"
        )


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
        validate_trader_lab_monte_carlo_experiment_evidence(self)

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
        status = _derive_monte_carlo_status(registration, distribution, envelope)
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


def reference_trader_lab_monte_carlo(
    candidate: TraderLabCandidateBinding,
    evidence: TraderLabMonteCarloExperimentEvidence,
) -> TraderLabEvidenceReference:
    """Reference exact Monte Carlo qualification evidence bound to the candidate.

    The MONTE_CARLO stage requires a ``TraderLabMonteCarloExperimentEvidence``
    whose frozen thresholds actually participated in a ``QUALIFIED`` derivation:
    any other status (threshold violation, insufficient sample/evidence,
    unsupported dependence) fails closed. This is the only promotion-path entry
    point for the MONTE_CARLO stage, so the raw resampling envelope alone can
    never satisfy it.
    """

    validate_trader_lab_monte_carlo_experiment_evidence(evidence)
    if evidence.registration.candidate != candidate:
        raise TraderLabValidationError(
            "Monte Carlo evidence must bind the exact candidate registration"
        )
    if evidence.status is not TraderLabMonteCarloStatus.QUALIFIED:
        raise TraderLabValidationError(
            "only a qualified Monte Carlo status may satisfy the MONTE_CARLO stage"
        )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.MONTE_CARLO_QUALIFICATION,
        reference_id=evidence.evidence_id.value,
        content_digest=TraderLabEvidenceDigest(evidence.fingerprint.value),
        schema_version="trader_lab.monte-carlo.v1",
        strategy_binding_fingerprint=candidate.strategy_binding.binding_fingerprint.value,
    )


_STRESS_FAMILIES: frozenset[TraderLabRobustnessFamily] = frozenset(
    {
        TraderLabRobustnessFamily.START_SUBWINDOW,
        TraderLabRobustnessFamily.COST_PERTURBATION,
        TraderLabRobustnessFamily.PARAMETER_NEIGHBORHOOD,
    }
)


class TraderLabStressStatus(StrEnum):
    """Fail-closed verdict of an adversarial stress scenario."""

    QUALIFIED = "qualified"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class TraderLabStressEvidenceId:
    """Immutable identity of one stress-evidence record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError("stress evidence id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabStressFingerprint:
    """Canonical SHA-256 digest of the stress-evidence record."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="stress fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _canonical_bounds(bounds: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
    if not isinstance(bounds, tuple) or any(
        not isinstance(item, Decimal) or not item.is_finite() for item in bounds
    ):
        raise TraderLabValidationError(
            "stress bounds must be an immutable finite Decimal tuple"
        )
    ordered = tuple(sorted(bounds, key=lambda item: _canonical_decimal(item)))
    if len(set(ordered)) != len(ordered):
        raise TraderLabValidationError("stress bounds must be unique")
    return ordered


def compute_trader_lab_stress_fingerprint(
    *,
    evidence_id: TraderLabStressEvidenceId,
    candidate: TraderLabCandidateBinding,
    family: TraderLabRobustnessFamily,
    scenario: str,
    bounds: tuple[Decimal, ...],
    status: TraderLabStressStatus,
    certified_at: datetime,
) -> TraderLabStressFingerprint:
    """Hash the exact stress-evidence content, distinct from Monte Carlo evidence."""

    if not isinstance(evidence_id, TraderLabStressEvidenceId):
        raise TraderLabValidationError("evidence_id must be TraderLabStressEvidenceId")
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(family, TraderLabRobustnessFamily):
        raise TraderLabValidationError("family must be TraderLabRobustnessFamily")
    if family not in _STRESS_FAMILIES:
        raise TraderLabValidationError(
            "stress evidence requires a stress family, never block bootstrap"
        )
    _validate_token(scenario, field_name="stress scenario")
    canonical_bounds = _canonical_bounds(bounds)
    if not isinstance(status, TraderLabStressStatus):
        raise TraderLabValidationError("status must be TraderLabStressStatus")
    _validate_timestamp(certified_at, field_name="stress certified_at")
    canonical = {
        "schema": "qore.trader_lab.stress.v1",
        "evidence_id": str(evidence_id.value),
        "candidate_fingerprint": candidate.fingerprint.value,
        "family": family.value,
        "scenario": scenario,
        "bounds": [_canonical_decimal(item) for item in canonical_bounds],
        "status": status.value,
        "certified_at": certified_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
    }
    return TraderLabStressFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


def validate_trader_lab_stress_evidence(evidence: TraderLabStressEvidence) -> None:
    """Re-validate typed stress evidence at a trust boundary."""

    if not isinstance(evidence, TraderLabStressEvidence):
        raise TraderLabValidationError("evidence must be TraderLabStressEvidence")
    if not isinstance(evidence.evidence_id, TraderLabStressEvidenceId):
        raise TraderLabValidationError(
            "evidence_id must be TraderLabStressEvidenceId"
        )
    if not isinstance(evidence.candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(evidence.family, TraderLabRobustnessFamily):
        raise TraderLabValidationError("family must be TraderLabRobustnessFamily")
    if evidence.family not in _STRESS_FAMILIES:
        raise TraderLabValidationError(
            "stress evidence requires a stress family, never block bootstrap"
        )
    _validate_token(evidence.scenario, field_name="stress scenario")
    canonical_bounds = _canonical_bounds(evidence.bounds)
    if evidence.bounds != canonical_bounds:
        raise TraderLabValidationError("stress bounds must use canonical order")
    if not isinstance(evidence.status, TraderLabStressStatus):
        raise TraderLabValidationError("status must be TraderLabStressStatus")
    _validate_timestamp(evidence.certified_at, field_name="stress certified_at")
    if not isinstance(evidence.fingerprint, TraderLabStressFingerprint):
        raise TraderLabValidationError(
            "fingerprint must be TraderLabStressFingerprint"
        )
    expected = compute_trader_lab_stress_fingerprint(
        evidence_id=evidence.evidence_id,
        candidate=evidence.candidate,
        family=evidence.family,
        scenario=evidence.scenario,
        bounds=evidence.bounds,
        status=evidence.status,
        certified_at=evidence.certified_at,
    )
    if evidence.fingerprint != expected:
        raise TraderLabValidationError(
            "stress fingerprint must match the exact evidence"
        )


@dataclass(frozen=True, slots=True)
class TraderLabStressEvidence:
    """Typed, self-authenticating adversarial stress evidence.

    This is a semantically distinct seam from Monte Carlo evidence: it carries a
    declared adversarial scenario (start subwindow, cost perturbation, or
    parameter neighborhood) with a fail-closed verdict, never a resampling
    envelope. The scenario/verdict content is produced by an external stress
    evaluator; the Lab only validates structure, candidate binding, and identity.
    """

    evidence_id: TraderLabStressEvidenceId
    candidate: TraderLabCandidateBinding
    family: TraderLabRobustnessFamily
    scenario: str
    bounds: tuple[Decimal, ...]
    status: TraderLabStressStatus
    certified_at: datetime
    fingerprint: TraderLabStressFingerprint

    def __post_init__(self) -> None:
        validate_trader_lab_stress_evidence(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.candidate.fingerprint.logical_values(),
            self.family.value,
            self.scenario,
            tuple(_canonical_decimal(item) for item in self.bounds),
            self.status.value,
            self.certified_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.fingerprint.logical_values(),
        )


def build_trader_lab_stress_evidence(
    *,
    evidence_id: TraderLabStressEvidenceId,
    candidate: TraderLabCandidateBinding,
    family: TraderLabRobustnessFamily,
    scenario: str,
    bounds: tuple[Decimal, ...],
    status: TraderLabStressStatus,
    certified_at: datetime,
) -> Result[TraderLabStressEvidence, TraderLabError]:
    """Build typed stress evidence without executing any stress evaluation."""

    try:
        canonical_bounds = _canonical_bounds(bounds)
        fingerprint = compute_trader_lab_stress_fingerprint(
            evidence_id=evidence_id,
            candidate=candidate,
            family=family,
            scenario=scenario,
            bounds=canonical_bounds,
            status=status,
            certified_at=certified_at,
        )
        return Success(
            TraderLabStressEvidence(
                evidence_id=evidence_id,
                candidate=candidate,
                family=family,
                scenario=scenario,
                bounds=canonical_bounds,
                status=status,
                certified_at=certified_at,
                fingerprint=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)


def reference_trader_lab_stress(
    candidate: TraderLabCandidateBinding,
    evidence: TraderLabStressEvidence,
) -> TraderLabEvidenceReference:
    """Reference exact typed stress evidence bound to the candidate.

    Only a ``QUALIFIED`` stress verdict may satisfy the STRESS stage; a FAILED or
    INSUFFICIENT_EVIDENCE verdict fails closed.
    """

    validate_trader_lab_stress_evidence(evidence)
    if evidence.candidate != candidate:
        raise TraderLabValidationError(
            "stress evidence must bind the exact candidate"
        )
    if evidence.status is not TraderLabStressStatus.QUALIFIED:
        raise TraderLabValidationError(
            "only a qualified stress verdict may satisfy the STRESS stage"
        )
    raise TraderLabValidationError(
        "qualified stress evidence is an external-governance dependency: use "
        "TraderLabGovernedGate.STRESS_REVIEW with an externally issued "
        "robustness-authority authenticity proof"
    )
