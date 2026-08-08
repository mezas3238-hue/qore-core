from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.adapter_lifecycle as adapter_lifecycle
import qore.infrastructure.adapter_observability as adapter_observability
import qore.infrastructure.adapter_resilience as adapter_resilience
import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.infrastructure.secrets as secrets
import qore.kernel.result as result_contract
from qore.domain.events import DomainMetadataValue

_RESERVED_ACTIVATION_METADATA_KEYS = frozenset(
    {
        "adapter_id",
        "causation_id",
        "correlation_id",
        "decision",
        "mode",
        "provider_id",
        "reason",
        "reasons",
        "secret",
        "secret_value",
        "source_id",
        "token",
        "value",
    }
)
_SENSITIVE_ACTIVATION_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SENSITIVE_ACTIVATION_TEXT_PARTS = frozenset(
    {
        "-----begin",
        "api_key=",
        "authorization:",
        "bearer ",
        "client_secret=",
        "ghp_",
        "github_pat_",
        "password=",
        "secret=",
        "sk-",
        "token=",
        "xox",
    }
)


class ProviderActivationPolicyError(ports.ExternalPortError):
    """Base error for provider activation policy contracts."""

    __slots__ = ()


class ProviderActivationPolicyValidationError(ProviderActivationPolicyError):
    """Violation of a provider activation policy invariant."""

    __slots__ = ()


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ProviderActivationPolicyValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderActivationPolicyValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProviderActivationPolicyValidationError(f"{field_name} must be non-empty")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_ACTIVATION_TEXT_PARTS):
        raise ProviderActivationPolicyValidationError(
            f"{field_name} must not contain sensitive payloads"
        )


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, str):
        _validate_public_text(value, field_name="provider activation metadata value")
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ProviderActivationPolicyValidationError(
                "provider activation metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise ProviderActivationPolicyValidationError(
        "provider activation metadata values must be immutable scalars or tuples"
    )


def _validate_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise ProviderActivationPolicyValidationError(
            "provider activation metadata must be a mapping"
        )
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise ProviderActivationPolicyValidationError(
                "provider activation metadata keys must use lowercase letters, "
                "digits, dots, underscores, or hyphens"
            )
        if key in _RESERVED_ACTIVATION_METADATA_KEYS:
            raise ProviderActivationPolicyValidationError(
                f"reserved provider activation metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_ACTIVATION_KEY_PARTS):
            raise ProviderActivationPolicyValidationError(
                "provider activation metadata must not contain secret-like keys"
            )
        _validate_metadata_value(value)
    return MappingProxyType({key: values[key] for key in sorted(values)})


class ProviderActivationMode(StrEnum):
    """Closed fail-closed activation modes for supervised provider adapters."""

    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    SIMULATION = "simulation"
    READ_ONLY = "read_only"


class ProviderActivationDecision(StrEnum):
    """Closed result of a provider activation policy evaluation."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    DEGRADED = "degraded"


class ProviderActivationDecisionReason(StrEnum):
    """Closed sanitized reasons for activation policy decisions."""

    POLICY_DISABLED = "policy_disabled"
    CONFIGURATION_DISABLED = "configuration_disabled"
    MODE_EXCEEDS_CONFIGURATION = "mode_exceeds_configuration"
    MISSING_CAPABILITY = "missing_capability"
    MISSING_SECRET_REFERENCE = "missing_secret_reference"
    UNKNOWN_SECRET_REFERENCE = "unknown_secret_reference"
    LIFECYCLE_NOT_READY = "lifecycle_not_ready"
    OBSERVABILITY_DEGRADED = "observability_degraded"
    OBSERVABILITY_UNAVAILABLE = "observability_unavailable"
    RESILIENCE_UNAVAILABLE = "resilience_unavailable"
    IDENTITY_MISMATCH = "identity_mismatch"


_ACTIVATION_MODE_RANK = MappingProxyType(
    {
        ProviderActivationMode.DISABLED: 0,
        ProviderActivationMode.DRY_RUN: 1,
        ProviderActivationMode.SIMULATION: 2,
        ProviderActivationMode.READ_ONLY: 3,
    }
)
_CONFIGURATION_MODE_LIMIT = MappingProxyType(
    {
        adapter_configuration.AdapterConfigurationMode.DISABLED: ProviderActivationMode.DISABLED,
        adapter_configuration.AdapterConfigurationMode.SIMULATION: (
            ProviderActivationMode.SIMULATION
        ),
        adapter_configuration.AdapterConfigurationMode.READ_ONLY: ProviderActivationMode.READ_ONLY,
    }
)
_ALLOWED_LIFECYCLE_STATES = frozenset(
    {
        adapter_lifecycle.AdapterLifecycleState.INITIALIZED,
        adapter_lifecycle.AdapterLifecycleState.STARTED,
    }
)


@dataclass(frozen=True, slots=True)
class ProviderActivationPolicy:
    """Immutable fail-closed activation policy for one provider/source boundary."""

    provider: providers.ProviderDescriptor
    source: ports.ExternalSourceDescriptor
    mode: ProviderActivationMode = ProviderActivationMode.DISABLED
    required_capabilities: tuple[providers.ProviderCapability, ...] = ()
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.provider, providers.ProviderDescriptor):
            raise ProviderActivationPolicyValidationError(
                "provider activation policy provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ports.ExternalSourceDescriptor):
            raise ProviderActivationPolicyValidationError(
                "provider activation policy source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.mode, ProviderActivationMode):
            raise ProviderActivationPolicyValidationError(
                "provider activation policy mode must be ProviderActivationMode"
            )
        if not isinstance(self.required_capabilities, tuple):
            raise ProviderActivationPolicyValidationError(
                "provider activation required_capabilities must be a tuple"
            )
        seen: set[providers.ProviderCapability] = set()
        for capability in self.required_capabilities:
            if not isinstance(capability, providers.ProviderCapability):
                raise ProviderActivationPolicyValidationError(
                    "provider activation required_capabilities entries must be "
                    "ProviderCapability"
                )
            if capability in seen:
                raise ProviderActivationPolicyValidationError(
                    "provider activation required_capabilities must not contain "
                    "duplicates"
                )
            seen.add(capability)
        object.__setattr__(
            self,
            "required_capabilities",
            tuple(sorted(self.required_capabilities, key=lambda item: item.value)),
        )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    @property
    def is_enabled(self) -> bool:
        """Return whether this policy can ever allow activation."""
        return self.mode is not ProviderActivationMode.DISABLED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.source.logical_values(),
            self.mode.value,
            tuple(capability.value for capability in self.required_capabilities),
            tuple(self.metadata.items()),
        )


@dataclass(frozen=True, slots=True)
class ProviderActivationSecretReferences:
    """Canonical secret references supplied for activation, never secret values."""

    refs: tuple[secrets.SecretRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.refs, tuple):
            raise ProviderActivationPolicyValidationError(
                "provider activation secret refs must be a tuple"
            )
        seen: set[str] = set()
        for ref in self.refs:
            if not isinstance(ref, secrets.SecretRef):
                raise ProviderActivationPolicyValidationError(
                    "provider activation secret refs entries must be SecretRef"
                )
            if ref.name.value in seen:
                raise ProviderActivationPolicyValidationError(
                    "provider activation secret refs must not contain duplicates"
                )
            seen.add(ref.name.value)
        object.__setattr__(
            self,
            "refs",
            tuple(sorted(self.refs, key=lambda item: item.name.value)),
        )

    def contains(self, name: adapter_configuration.AdapterSecretName) -> bool:
        """Return whether a secret reference exists for a requirement name."""
        if not isinstance(name, adapter_configuration.AdapterSecretName):
            raise ProviderActivationPolicyValidationError(
                "provider activation secret check name must be AdapterSecretName"
            )
        return any(ref.name == name for ref in self.refs)

    def names(self) -> tuple[str, ...]:
        """Return canonical secret names only, never secret values."""
        return tuple(ref.name.value for ref in self.refs)

    def logical_values(self) -> tuple[tuple[object, ...], ...]:
        return tuple(ref.logical_values() for ref in self.refs)


@dataclass(frozen=True, slots=True)
class ProviderActivationEvaluation:
    """Explicit inputs for a pure activation policy evaluation."""

    policy: ProviderActivationPolicy
    configuration: adapter_configuration.ExternalAdapterConfiguration
    lifecycle: adapter_lifecycle.AdapterLifecycleSnapshot
    observability: adapter_observability.AdapterObservabilitySnapshot | None = None
    resilience: adapter_resilience.AdapterResilienceSnapshot | None = None
    secrets: ProviderActivationSecretReferences = field(
        default_factory=ProviderActivationSecretReferences
    )
    evaluated_at: datetime | None = None
    metadata: ports.ExternalRequestMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProviderActivationPolicy):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation policy must be ProviderActivationPolicy"
            )
        if not isinstance(
            self.configuration,
            adapter_configuration.ExternalAdapterConfiguration,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation configuration must be "
                "ExternalAdapterConfiguration"
            )
        if not isinstance(self.lifecycle, adapter_lifecycle.AdapterLifecycleSnapshot):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation lifecycle must be AdapterLifecycleSnapshot"
            )
        if self.observability is not None and not isinstance(
            self.observability,
            adapter_observability.AdapterObservabilitySnapshot,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation observability must be "
                "AdapterObservabilitySnapshot or None"
            )
        if self.resilience is not None and not isinstance(
            self.resilience,
            adapter_resilience.AdapterResilienceSnapshot,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation resilience must be "
                "AdapterResilienceSnapshot or None"
            )
        if not isinstance(self.secrets, ProviderActivationSecretReferences):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation secrets must be "
                "ProviderActivationSecretReferences"
            )
        if self.evaluated_at is not None:
            _validate_explicit_datetime(self.evaluated_at, field_name="evaluated_at")
        if self.metadata is not None and not isinstance(
            self.metadata,
            ports.ExternalRequestMetadata,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation evaluation metadata must be ExternalRequestMetadata or None"
            )


@dataclass(frozen=True, slots=True)
class ProviderActivationDecisionSnapshot:
    """Immutable sanitized activation policy decision."""

    policy: ProviderActivationPolicy
    configuration: adapter_configuration.ExternalAdapterConfiguration
    decision: ProviderActivationDecision
    reasons: tuple[ProviderActivationDecisionReason, ...]
    evaluated_at: datetime
    lifecycle: adapter_lifecycle.AdapterLifecycleSnapshot
    observability: adapter_observability.AdapterObservabilitySnapshot | None = None
    resilience: adapter_resilience.AdapterResilienceSnapshot | None = None
    secret_references: ProviderActivationSecretReferences = field(
        default_factory=ProviderActivationSecretReferences
    )
    metadata: ports.ExternalRequestMetadata | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, ProviderActivationPolicy):
            raise ProviderActivationPolicyValidationError(
                "activation decision policy must be ProviderActivationPolicy"
            )
        if not isinstance(
            self.configuration,
            adapter_configuration.ExternalAdapterConfiguration,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation decision configuration must be ExternalAdapterConfiguration"
            )
        if not isinstance(self.decision, ProviderActivationDecision):
            raise ProviderActivationPolicyValidationError(
                "activation decision must be ProviderActivationDecision"
            )
        if not isinstance(self.reasons, tuple):
            raise ProviderActivationPolicyValidationError(
                "activation decision reasons must be a tuple"
            )
        for reason in self.reasons:
            if not isinstance(reason, ProviderActivationDecisionReason):
                raise ProviderActivationPolicyValidationError(
                    "activation decision reasons entries must be "
                    "ProviderActivationDecisionReason"
                )
        if self.decision is ProviderActivationDecision.ALLOWED and self.reasons:
            raise ProviderActivationPolicyValidationError(
                "allowed activation decisions must not carry reasons"
            )
        if self.decision is not ProviderActivationDecision.ALLOWED and not self.reasons:
            raise ProviderActivationPolicyValidationError(
                "blocked or degraded activation decisions require reasons"
            )
        _validate_explicit_datetime(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.lifecycle, adapter_lifecycle.AdapterLifecycleSnapshot):
            raise ProviderActivationPolicyValidationError(
                "activation decision lifecycle must be AdapterLifecycleSnapshot"
            )
        if self.observability is not None and not isinstance(
            self.observability,
            adapter_observability.AdapterObservabilitySnapshot,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation decision observability must be "
                "AdapterObservabilitySnapshot or None"
            )
        if self.resilience is not None and not isinstance(
            self.resilience,
            adapter_resilience.AdapterResilienceSnapshot,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation decision resilience must be "
                "AdapterResilienceSnapshot or None"
            )
        if not isinstance(self.secret_references, ProviderActivationSecretReferences):
            raise ProviderActivationPolicyValidationError(
                "activation decision secret_references must be "
                "ProviderActivationSecretReferences"
            )
        if self.metadata is not None and not isinstance(
            self.metadata,
            ports.ExternalRequestMetadata,
        ):
            raise ProviderActivationPolicyValidationError(
                "activation decision metadata must be ExternalRequestMetadata or None"
            )
        if self.message is not None:
            _validate_public_text(self.message, field_name="activation decision message")
        object.__setattr__(
            self,
            "reasons",
            tuple(sorted(set(self.reasons), key=lambda item: item.value)),
        )

    @property
    def can_activate(self) -> bool:
        """Return whether the policy permits exposing the adapter boundary."""
        return self.decision is ProviderActivationDecision.ALLOWED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy.logical_values(),
            self.configuration.logical_values(),
            self.decision.value,
            tuple(reason.value for reason in self.reasons),
            self.evaluated_at.isoformat(),
            self.lifecycle.logical_values(),
            self.observability.logical_values()
            if self.observability is not None
            else None,
            self.resilience.logical_values() if self.resilience is not None else None,
            self.secret_references.logical_values(),
            self.metadata.logical_values() if self.metadata is not None else None,
            self.message,
        )


class ProviderActivationPolicyBoundary(Protocol):
    """Structural boundary exposing a fail-closed activation decision."""

    @property
    def activation_policy(self) -> ProviderActivationPolicy:
        """Return immutable activation policy."""
        ...

    def evaluate_activation(
        self,
        evaluation: ProviderActivationEvaluation,
    ) -> result_contract.Result[
        ProviderActivationDecisionSnapshot,
        ProviderActivationPolicyError,
    ]:
        """Evaluate activation without mutating runtime or resolving secrets."""
        ...


def _failure(
    message: str,
) -> result_contract.Failure[ProviderActivationPolicyError]:
    return result_contract.Failure(ProviderActivationPolicyValidationError(message))


def _mode_exceeds_configuration(
    *,
    policy_mode: ProviderActivationMode,
    configuration_mode: adapter_configuration.AdapterConfigurationMode,
) -> bool:
    max_mode = _CONFIGURATION_MODE_LIMIT[configuration_mode]
    return _ACTIVATION_MODE_RANK[policy_mode] > _ACTIVATION_MODE_RANK[max_mode]


def _matching_identity(
    evaluation: ProviderActivationEvaluation,
) -> bool:
    expected_provider = evaluation.configuration.provider
    expected_source = evaluation.configuration.source
    if evaluation.policy.provider != expected_provider:
        return False
    if evaluation.policy.source != expected_source:
        return False
    if evaluation.lifecycle.provider != expected_provider:
        return False
    if evaluation.lifecycle.descriptor != expected_source:
        return False
    if evaluation.observability is not None:
        if evaluation.observability.provider != expected_provider:
            return False
        if evaluation.observability.source != expected_source:
            return False
    if evaluation.resilience is not None:
        if evaluation.resilience.policy.provider != expected_provider:
            return False
        if evaluation.resilience.policy.source != expected_source:
            return False
    return True


def _secret_decision_reasons(
    evaluation: ProviderActivationEvaluation,
) -> list[ProviderActivationDecisionReason]:
    reasons: list[ProviderActivationDecisionReason] = []
    requirements = evaluation.configuration.secret_requirements.requirements
    requirement_names = {requirement.name.value for requirement in requirements}
    for requirement in requirements:
        if requirement.required and not evaluation.secrets.contains(requirement.name):
            reasons.append(ProviderActivationDecisionReason.MISSING_SECRET_REFERENCE)
    for supplied_name in evaluation.secrets.names():
        if supplied_name not in requirement_names:
            reasons.append(ProviderActivationDecisionReason.UNKNOWN_SECRET_REFERENCE)
    return reasons


def _decision_message(
    decision: ProviderActivationDecision,
    reasons: tuple[ProviderActivationDecisionReason, ...],
) -> str | None:
    if decision is ProviderActivationDecision.ALLOWED:
        return None
    joined = ",".join(reason.value for reason in reasons)
    return f"activation {decision.value}: {joined}"


def evaluate_provider_activation_policy(
    evaluation: ProviderActivationEvaluation,
) -> result_contract.Result[
    ProviderActivationDecisionSnapshot,
    ProviderActivationPolicyError,
]:
    """Evaluate activation policy with explicit inputs and no side effects."""
    if not isinstance(evaluation, ProviderActivationEvaluation):
        return _failure("evaluation must be ProviderActivationEvaluation")
    if evaluation.evaluated_at is None:
        return _failure("activation evaluation evaluated_at is required")
    if evaluation.metadata is None:
        return _failure("activation evaluation metadata is required")
    if not _matching_identity(evaluation):
        return _failure("activation evaluation identities must match")

    blocking_reasons: list[ProviderActivationDecisionReason] = []
    degraded_reasons: list[ProviderActivationDecisionReason] = []

    if evaluation.policy.mode is ProviderActivationMode.DISABLED:
        blocking_reasons.append(ProviderActivationDecisionReason.POLICY_DISABLED)
    if not evaluation.configuration.is_enabled:
        blocking_reasons.append(ProviderActivationDecisionReason.CONFIGURATION_DISABLED)
    if _mode_exceeds_configuration(
        policy_mode=evaluation.policy.mode,
        configuration_mode=evaluation.configuration.mode,
    ):
        blocking_reasons.append(ProviderActivationDecisionReason.MODE_EXCEEDS_CONFIGURATION)

    for capability in evaluation.policy.required_capabilities:
        if not evaluation.configuration.provider.capabilities.supports(capability):
            blocking_reasons.append(ProviderActivationDecisionReason.MISSING_CAPABILITY)

    blocking_reasons.extend(_secret_decision_reasons(evaluation))

    if evaluation.lifecycle.state not in _ALLOWED_LIFECYCLE_STATES:
        blocking_reasons.append(ProviderActivationDecisionReason.LIFECYCLE_NOT_READY)

    if evaluation.observability is not None:
        if evaluation.observability.readiness is adapter_observability.AdapterReadiness.DEGRADED:
            degraded_reasons.append(
                ProviderActivationDecisionReason.OBSERVABILITY_DEGRADED
            )
        if evaluation.observability.readiness is adapter_observability.AdapterReadiness.UNAVAILABLE:
            blocking_reasons.append(
                ProviderActivationDecisionReason.OBSERVABILITY_UNAVAILABLE
            )

    if evaluation.resilience is not None and evaluation.resilience.circuit_breaker is not None:
        if (
            evaluation.resilience.circuit_breaker.state
            is adapter_resilience.AdapterCircuitBreakerState.OPEN
        ):
            blocking_reasons.append(
                ProviderActivationDecisionReason.RESILIENCE_UNAVAILABLE
            )

    if blocking_reasons:
        decision = ProviderActivationDecision.BLOCKED
        reasons = tuple(blocking_reasons)
    elif degraded_reasons:
        decision = ProviderActivationDecision.DEGRADED
        reasons = tuple(degraded_reasons)
    else:
        decision = ProviderActivationDecision.ALLOWED
        reasons = ()

    try:
        snapshot = ProviderActivationDecisionSnapshot(
            policy=evaluation.policy,
            configuration=evaluation.configuration,
            decision=decision,
            reasons=reasons,
            evaluated_at=evaluation.evaluated_at,
            lifecycle=evaluation.lifecycle,
            observability=evaluation.observability,
            resilience=evaluation.resilience,
            secret_references=evaluation.secrets,
            metadata=evaluation.metadata,
            message=_decision_message(decision, reasons),
        )
    except ProviderActivationPolicyError as error:
        return result_contract.Failure(error)
    return result_contract.Success(snapshot)
