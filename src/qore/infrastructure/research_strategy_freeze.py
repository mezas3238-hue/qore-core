from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_run import (
    ResearchRunEvidence,
    ResearchStrategyConfigurationId,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchStrategyFreezeError(InfrastructureError):
    """Base error for immutable research strategy-configuration evidence."""

    __slots__ = ()


class ResearchStrategyFreezeValidationError(ResearchStrategyFreezeError):
    """Violation of a research strategy freeze invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchStrategyFreezeValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchStrategyFreezeValidationError(
            f"{field_name} must be timezone-aware"
        )


def _utc_iso(value: datetime) -> str:
    _validate_timestamp(value, field_name="strategy freeze timestamp")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._/+:-]*",
        value,
    ) is None:
        raise ResearchStrategyFreezeValidationError(
            f"{field_name} must use canonical token syntax"
        )


def _canonical_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchStrategyFreezeValidationError(
            "strategy decimal parameter must be finite Decimal"
        )
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


ResearchStrategyParameterValue = str | bool | int | Decimal


@dataclass(frozen=True, slots=True)
class ResearchStrategyParameter:
    """One typed immutable strategy parameter with deterministic representation."""

    name: str
    value: ResearchStrategyParameterValue

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or fullmatch(
            r"[a-z][a-z0-9._-]{0,79}",
            self.name,
        ) is None:
            raise ResearchStrategyFreezeValidationError(
                "strategy parameter name must use canonical lowercase syntax"
            )
        if type(self.value) is bool:
            return
        if type(self.value) is int:
            return
        if isinstance(self.value, Decimal):
            _canonical_decimal(self.value)
            return
        if isinstance(self.value, str):
            if not self.value:
                raise ResearchStrategyFreezeValidationError(
                    "strategy string parameter must not be empty"
                )
            return
        raise ResearchStrategyFreezeValidationError(
            "strategy parameter value must be str, bool, int, or Decimal"
        )

    def canonical_value(self) -> dict[str, object]:
        if type(self.value) is bool:
            return {"type": "bool", "value": self.value}
        if type(self.value) is int:
            return {"type": "int", "value": str(self.value)}
        if isinstance(self.value, Decimal):
            return {"type": "decimal", "value": _canonical_decimal(self.value)}
        return {"type": "str", "value": self.value}

    def logical_values(self) -> tuple[object, ...]:
        canonical = self.canonical_value()
        return (self.name, canonical["type"], canonical["value"])


@dataclass(frozen=True, slots=True)
class ResearchStrategySchemaVersion:
    value: str

    def __post_init__(self) -> None:
        _validate_token(self.value, field_name="strategy schema version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ResearchStrategyConfigurationDigest:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchStrategyFreezeValidationError(
                "strategy configuration digest must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ResearchStrategyFreezeEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchStrategyFreezeValidationError(
                "strategy freeze evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _canonical_parameters(
    parameters: tuple[ResearchStrategyParameter, ...],
) -> tuple[ResearchStrategyParameter, ...]:
    if not isinstance(parameters, tuple) or any(
        not isinstance(item, ResearchStrategyParameter) for item in parameters
    ):
        raise ResearchStrategyFreezeValidationError(
            "strategy parameters must be an immutable ResearchStrategyParameter tuple"
        )
    names = tuple(item.name for item in parameters)
    if len(set(names)) != len(names):
        raise ResearchStrategyFreezeValidationError(
            "strategy parameter names must be unique"
        )
    return tuple(sorted(parameters, key=lambda item: item.name))


def compute_research_strategy_configuration_digest(
    *,
    schema_version: ResearchStrategySchemaVersion,
    parameters: tuple[ResearchStrategyParameter, ...],
) -> ResearchStrategyConfigurationDigest:
    """Hash logical configuration content, excluding administrative identity/time."""

    if not isinstance(schema_version, ResearchStrategySchemaVersion):
        raise ResearchStrategyFreezeValidationError(
            "schema_version must be ResearchStrategySchemaVersion"
        )
    ordered = _canonical_parameters(parameters)
    canonical = {
        "schema_version": schema_version.value,
        "parameters": [
            {"name": item.name, **item.canonical_value()} for item in ordered
        ],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchStrategyConfigurationDigest(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchStrategyConfigurationManifest:
    """Exact immutable strategy configuration frozen on the research process axis.

    `frozen_at` is administrative/process evidence time. It is deliberately not
    compared with historical simulated market timestamps.
    """

    configuration_id: ResearchStrategyConfigurationId
    schema_version: ResearchStrategySchemaVersion
    parameters: tuple[ResearchStrategyParameter, ...]
    content_digest: ResearchStrategyConfigurationDigest
    frozen_at: datetime
    evidence_ref: ResearchStrategyFreezeEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.configuration_id, ResearchStrategyConfigurationId):
            raise ResearchStrategyFreezeValidationError(
                "configuration_id must be ResearchStrategyConfigurationId"
            )
        if not isinstance(self.schema_version, ResearchStrategySchemaVersion):
            raise ResearchStrategyFreezeValidationError(
                "schema_version must be ResearchStrategySchemaVersion"
            )
        ordered = _canonical_parameters(self.parameters)
        if self.parameters != ordered:
            raise ResearchStrategyFreezeValidationError(
                "strategy parameters must use canonical name order"
            )
        if not isinstance(self.content_digest, ResearchStrategyConfigurationDigest):
            raise ResearchStrategyFreezeValidationError(
                "content_digest must be ResearchStrategyConfigurationDigest"
            )
        expected = compute_research_strategy_configuration_digest(
            schema_version=self.schema_version,
            parameters=self.parameters,
        )
        if self.content_digest != expected:
            raise ResearchStrategyFreezeValidationError(
                "strategy configuration digest must match canonical configuration content"
            )
        _validate_timestamp(self.frozen_at, field_name="strategy frozen_at")
        if not isinstance(self.evidence_ref, ResearchStrategyFreezeEvidenceReference):
            raise ResearchStrategyFreezeValidationError(
                "evidence_ref must be ResearchStrategyFreezeEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.configuration_id.logical_values(),
            self.schema_version.logical_values(),
            tuple(item.logical_values() for item in self.parameters),
            self.content_digest.logical_values(),
            self.frozen_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def build_research_strategy_configuration_manifest(
    *,
    configuration_id: ResearchStrategyConfigurationId,
    schema_version: ResearchStrategySchemaVersion,
    parameters: tuple[ResearchStrategyParameter, ...],
    frozen_at: datetime,
    evidence_ref: ResearchStrategyFreezeEvidenceReference,
) -> Result[ResearchStrategyConfigurationManifest, ResearchStrategyFreezeError]:
    """Freeze exact strategy content without executing or evaluating a strategy."""

    try:
        ordered = _canonical_parameters(parameters)
        digest = compute_research_strategy_configuration_digest(
            schema_version=schema_version,
            parameters=ordered,
        )
        return Success(
            ResearchStrategyConfigurationManifest(
                configuration_id=configuration_id,
                schema_version=schema_version,
                parameters=ordered,
                content_digest=digest,
                frozen_at=frozen_at,
                evidence_ref=evidence_ref,
            )
        )
    except ResearchStrategyFreezeError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class ResearchRunStrategyBindingFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchStrategyFreezeValidationError(
                "run strategy binding fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_run_strategy_binding_fingerprint(
    *,
    run: ResearchRunEvidence,
    manifest: ResearchStrategyConfigurationManifest,
) -> ResearchRunStrategyBindingFingerprint:
    if not isinstance(run, ResearchRunEvidence):
        raise ResearchStrategyFreezeValidationError(
            "run must be ResearchRunEvidence"
        )
    if not isinstance(manifest, ResearchStrategyConfigurationManifest):
        raise ResearchStrategyFreezeValidationError(
            "manifest must be ResearchStrategyConfigurationManifest"
        )
    canonical = {
        "run_input_fingerprint": run.input_fingerprint.value,
        "strategy_configuration_id": str(manifest.configuration_id.value),
        "strategy_schema_version": manifest.schema_version.value,
        "strategy_content_digest": manifest.content_digest.value,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchRunStrategyBindingFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchRunStrategyBinding:
    """Bind one run to exact frozen strategy content on the process evidence axis.

    The binding proves exact configuration identity/content was frozen no later
    than the research run record creation. It does not prove analyst blindness,
    pre-registration before data inspection, or absence of repeated research.
    """

    run: ResearchRunEvidence
    manifest: ResearchStrategyConfigurationManifest
    binding_fingerprint: ResearchRunStrategyBindingFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchStrategyFreezeValidationError(
                "strategy binding requires ResearchRunEvidence"
            )
        if not isinstance(self.manifest, ResearchStrategyConfigurationManifest):
            raise ResearchStrategyFreezeValidationError(
                "strategy binding requires ResearchStrategyConfigurationManifest"
            )
        if self.run.strategy_configuration_id != self.manifest.configuration_id:
            raise ResearchStrategyFreezeValidationError(
                "strategy manifest configuration id must match research run"
            )
        if self.manifest.frozen_at > self.run.created_at:
            raise ResearchStrategyFreezeValidationError(
                "strategy configuration must be frozen no later than research run creation"
            )
        if not isinstance(
            self.binding_fingerprint,
            ResearchRunStrategyBindingFingerprint,
        ):
            raise ResearchStrategyFreezeValidationError(
                "binding_fingerprint must be ResearchRunStrategyBindingFingerprint"
            )
        expected = compute_research_run_strategy_binding_fingerprint(
            run=self.run,
            manifest=self.manifest,
        )
        if self.binding_fingerprint != expected:
            raise ResearchStrategyFreezeValidationError(
                "strategy binding fingerprint must match run and manifest evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.run.logical_values(),
            self.manifest.logical_values(),
            self.binding_fingerprint.logical_values(),
        )


def build_research_run_strategy_binding(
    *,
    run: ResearchRunEvidence,
    manifest: ResearchStrategyConfigurationManifest,
) -> Result[ResearchRunStrategyBinding, ResearchStrategyFreezeError]:
    """Bind exact strategy content to one research run without executing it."""

    try:
        fingerprint = compute_research_run_strategy_binding_fingerprint(
            run=run,
            manifest=manifest,
        )
        return Success(
            ResearchRunStrategyBinding(
                run=run,
                manifest=manifest,
                binding_fingerprint=fingerprint,
            )
        )
    except ResearchStrategyFreezeError as error:
        return Failure(error)
