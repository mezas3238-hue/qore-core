from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.secret_resolution import (
    SecretMaterial,
    SecretMaterialResolution,
    SecretMaterialResolverBoundary,
    resolve_supervised_secret_material,
)
from qore.infrastructure.secrets import (
    SecretBoundaryError,
    SecretRef,
)
from qore.kernel.result import Failure, Result, Success

_EXPECTED_SECRET_NAME = "oanda-personal-access-token"
_EXPECTED_REFERENCE_PREFIX = "oanda/practice/"


class OandaPracticeCredentialActivationError(SecretBoundaryError):
    """Base error for OANDA Practice credential activation."""

    __slots__ = ()


class OandaPracticeCredentialActivationValidationError(
    OandaPracticeCredentialActivationError
):
    """Violation of an OANDA Practice credential activation invariant."""

    __slots__ = ()


def _validate_activation_timestamp(value: datetime) -> None:
    if not isinstance(value, datetime):
        raise OandaPracticeCredentialActivationValidationError(
            "credential activated_at must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise OandaPracticeCredentialActivationValidationError(
            "credential activated_at must be timezone-aware"
        )


def _validate_practice_secret_ref(
    configuration: OandaPracticeRuntimeConfiguration,
    ref: SecretRef,
) -> None:
    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        raise OandaPracticeCredentialActivationValidationError(
            "credential activation requires OandaPracticeRuntimeConfiguration"
        )
    if not isinstance(ref, SecretRef):
        raise OandaPracticeCredentialActivationValidationError(
            "credential activation requires SecretRef"
        )
    if ref.name.value != _EXPECTED_SECRET_NAME:
        raise OandaPracticeCredentialActivationValidationError(
            "credential reference must use the OANDA personal access token name"
        )
    if not ref.external_reference.value.startswith(_EXPECTED_REFERENCE_PREFIX):
        raise OandaPracticeCredentialActivationValidationError(
            "credential external reference must be scoped to oanda/practice"
        )
    if ref.metadata.get("provider") != configuration.provider_key:
        raise OandaPracticeCredentialActivationValidationError(
            "credential reference provider metadata must match configuration"
        )
    if ref.metadata.get("environment") != configuration.environment.value:
        raise OandaPracticeCredentialActivationValidationError(
            "credential reference environment metadata must be demo"
        )
    if ref.metadata.get("account-ref") != configuration.account.account_ref:
        raise OandaPracticeCredentialActivationValidationError(
            "credential reference account metadata must match configuration"
        )


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class OandaPracticeCredentialActivation:
    """Activated Practice credential with opaque material kept out of evidence."""

    configuration: OandaPracticeRuntimeConfiguration
    ref: SecretRef
    _resolution: SecretMaterialResolution = field(
        repr=False,
        compare=False,
        hash=False,
    )
    activated_at: datetime

    def __post_init__(self) -> None:
        _validate_practice_secret_ref(self.configuration, self.ref)
        if not isinstance(self._resolution, SecretMaterialResolution):
            raise OandaPracticeCredentialActivationValidationError(
                "credential activation requires SecretMaterialResolution"
            )
        _validate_activation_timestamp(self.activated_at)
        if self._resolution.ref != self.ref:
            raise OandaPracticeCredentialActivationValidationError(
                "credential resolution ref must match activation ref"
            )
        if self._resolution.resolved_at != self.activated_at:
            raise OandaPracticeCredentialActivationValidationError(
                "credential resolution timestamp must match activation timestamp"
            )

    def __repr__(self) -> str:
        return (
            "OandaPracticeCredentialActivation("
            f"provider_key={self.configuration.provider_key!r}, "
            f"account_ref={self.configuration.account.account_ref!r}, "
            f"ref={self.ref}, activated_at={self.activated_at.isoformat()}, "
            "material=<redacted>)"
        )

    @property
    def material(self) -> SecretMaterial:
        """Expose opaque material only to the next secret-aware external boundary."""
        return self._resolution.material

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.configuration.provider_key,
            self.configuration.environment.value,
            self.configuration.account.logical_values(),
            self.ref.logical_values(),
            self.activated_at.isoformat(),
        )


def activate_oanda_practice_credentials(
    configuration: OandaPracticeRuntimeConfiguration,
    ref: SecretRef,
    *,
    resolver: SecretMaterialResolverBoundary,
    metadata: ExternalRequestMetadata,
    activated_at: datetime,
) -> Result[OandaPracticeCredentialActivation, SecretBoundaryError]:
    """Resolve only an explicitly Practice-bound credential reference."""
    try:
        _validate_practice_secret_ref(configuration, ref)
        _validate_activation_timestamp(activated_at)
    except OandaPracticeCredentialActivationError as error:
        return Failure(error)

    resolution_result = resolve_supervised_secret_material(
        resolver,
        ref,
        metadata=metadata,
        resolved_at=activated_at,
    )
    if isinstance(resolution_result, Failure):
        return Failure(resolution_result.error)
    resolution = resolution_result.value
    if not isinstance(resolution, SecretMaterialResolution):
        return Failure(
            OandaPracticeCredentialActivationValidationError(
                "credential resolver returned an invalid resolution"
            )
        )
    try:
        activation = OandaPracticeCredentialActivation(
            configuration=configuration,
            ref=ref,
            _resolution=resolution,
            activated_at=activated_at,
        )
    except OandaPracticeCredentialActivationError as error:
        return Failure(error)
    return Success(activation)
