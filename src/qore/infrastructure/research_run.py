from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetManifest,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchRunError(InfrastructureError):
    """Base error for immutable historical research-run evidence."""

    __slots__ = ()


class ResearchRunValidationError(ResearchRunError):
    """Violation of a reproducible research-run identity invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ResearchRunValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchRunValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchRunValidationError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime) -> str:
    _validate_timestamp(value, field_name="research fingerprint timestamp")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_canonical_token(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._/+:-]*",
        value,
    ) is None:
        raise ResearchRunValidationError(
            f"{field_name} must use canonical token syntax"
        )


@dataclass(frozen=True, slots=True)
class ResearchRunId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research run id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchStrategyConfigurationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research strategy configuration id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchExecutionModelId:
    """Opaque identity of replay execution assumptions; it defines no fill behavior."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research execution model id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchTransactionCostModelId:
    """Opaque identity of replay cost assumptions; it defines no cost semantics."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="research transaction cost model id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchReplayPolicyVersion:
    value: str

    def __post_init__(self) -> None:
        _validate_canonical_token(self.value, field_name="research replay policy version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ResearchSoftwareRevision:
    value: str

    def __post_init__(self) -> None:
        _validate_canonical_token(self.value, field_name="research software revision")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ResearchRandomnessMode(StrEnum):
    DETERMINISTIC = "deterministic"
    SEEDED = "seeded"


@dataclass(frozen=True, slots=True)
class ResearchRunInputFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchRunValidationError(
                "research run input fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _validate_randomness(
    mode: ResearchRandomnessMode,
    seed: int | None,
) -> None:
    if not isinstance(mode, ResearchRandomnessMode):
        raise ResearchRunValidationError(
            "research randomness_mode must be ResearchRandomnessMode"
        )
    if mode is ResearchRandomnessMode.DETERMINISTIC:
        if seed is not None:
            raise ResearchRunValidationError(
                "deterministic research run must not declare random_seed"
            )
        return
    if type(seed) is not int or seed < 0:
        raise ResearchRunValidationError(
            "seeded research run requires a non-negative integer random_seed"
        )


def _validate_datasets(
    datasets: tuple[HistoricalDatasetManifest, ...],
    *,
    simulated_start: datetime,
    simulated_end: datetime,
) -> tuple[HistoricalDatasetManifest, ...]:
    if not isinstance(datasets, tuple) or not datasets or any(
        not isinstance(item, HistoricalDatasetManifest) for item in datasets
    ):
        raise ResearchRunValidationError(
            "research datasets must be a non-empty immutable manifest tuple"
        )
    dataset_ids = tuple(item.dataset_id for item in datasets)
    if len(set(dataset_ids)) != len(dataset_ids):
        raise ResearchRunValidationError(
            "research run must reference each dataset_id exactly once"
        )
    for manifest in datasets:
        window = manifest.scope.window
        if simulated_start < window.opened_at or simulated_end > window.closed_at:
            raise ResearchRunValidationError(
                "every research dataset requested window must cover the simulated run window"
            )
    return tuple(
        sorted(
            datasets,
            key=lambda item: (
                str(item.dataset_id.value),
                str(item.revision_id.value),
                item.evidence_digest.value,
            ),
        )
    )


def _canonical_dataset_reference(manifest: HistoricalDatasetManifest) -> dict[str, object]:
    scope = manifest.scope
    source = scope.source
    window = scope.window
    return {
        "dataset_id": str(manifest.dataset_id.value),
        "revision_id": str(manifest.revision_id.value),
        "evidence_digest": manifest.evidence_digest.value,
        "digest_algorithm": manifest.digest_algorithm.value,
        "schema_version": manifest.schema_version.value,
        "normalization_version": manifest.normalization_version.value,
        "scope": {
            "source": {
                "adapter_id": str(source.adapter_id.value),
                "source_id": str(source.source_id.value),
                "port_name": source.port_name.value,
            },
            "instrument": window.instrument.symbol,
            "timeframe_seconds": window.timeframe.seconds,
            "requested_opened_at": _utc_iso(window.opened_at),
            "requested_closed_at": _utc_iso(window.closed_at),
        },
    }


def compute_research_run_input_fingerprint(
    *,
    datasets: tuple[HistoricalDatasetManifest, ...],
    replay_policy_version: ResearchReplayPolicyVersion,
    simulated_start: datetime,
    simulated_end: datetime,
    strategy_configuration_id: ResearchStrategyConfigurationId,
    software_revision: ResearchSoftwareRevision,
    execution_model_id: ResearchExecutionModelId | None,
    transaction_cost_model_id: ResearchTransactionCostModelId | None,
    randomness_mode: ResearchRandomnessMode,
    random_seed: int | None,
) -> ResearchRunInputFingerprint:
    """Hash canonical run inputs while excluding administrative run identity/time."""

    _validate_timestamp(simulated_start, field_name="research simulated_start")
    _validate_timestamp(simulated_end, field_name="research simulated_end")
    if simulated_end <= simulated_start:
        raise ResearchRunValidationError(
            "research simulated_end must be after simulated_start"
        )
    if not isinstance(replay_policy_version, ResearchReplayPolicyVersion):
        raise ResearchRunValidationError(
            "replay_policy_version must be ResearchReplayPolicyVersion"
        )
    if not isinstance(strategy_configuration_id, ResearchStrategyConfigurationId):
        raise ResearchRunValidationError(
            "strategy_configuration_id must be ResearchStrategyConfigurationId"
        )
    if not isinstance(software_revision, ResearchSoftwareRevision):
        raise ResearchRunValidationError(
            "software_revision must be ResearchSoftwareRevision"
        )
    if execution_model_id is not None and not isinstance(
        execution_model_id,
        ResearchExecutionModelId,
    ):
        raise ResearchRunValidationError(
            "execution_model_id must be ResearchExecutionModelId or None"
        )
    if transaction_cost_model_id is not None and not isinstance(
        transaction_cost_model_id,
        ResearchTransactionCostModelId,
    ):
        raise ResearchRunValidationError(
            "transaction_cost_model_id must be ResearchTransactionCostModelId or None"
        )
    _validate_randomness(randomness_mode, random_seed)
    ordered_datasets = _validate_datasets(
        datasets,
        simulated_start=simulated_start,
        simulated_end=simulated_end,
    )
    canonical: dict[str, object] = {
        "datasets": [
            _canonical_dataset_reference(manifest) for manifest in ordered_datasets
        ],
        "replay_policy_version": replay_policy_version.value,
        "simulated_start": _utc_iso(simulated_start),
        "simulated_end": _utc_iso(simulated_end),
        "strategy_configuration_id": str(strategy_configuration_id.value),
        "software_revision": software_revision.value,
        "execution_model_id": (
            str(execution_model_id.value) if execution_model_id is not None else None
        ),
        "transaction_cost_model_id": (
            str(transaction_cost_model_id.value)
            if transaction_cost_model_id is not None
            else None
        ),
        "randomness_mode": randomness_mode.value,
        "random_seed": random_seed,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchRunInputFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchRunEvidence:
    """Immutable identity binding one research run to its exact evidence inputs."""

    run_id: ResearchRunId
    created_at: datetime
    datasets: tuple[HistoricalDatasetManifest, ...]
    replay_policy_version: ResearchReplayPolicyVersion
    simulated_start: datetime
    simulated_end: datetime
    strategy_configuration_id: ResearchStrategyConfigurationId
    software_revision: ResearchSoftwareRevision
    execution_model_id: ResearchExecutionModelId | None
    transaction_cost_model_id: ResearchTransactionCostModelId | None
    randomness_mode: ResearchRandomnessMode
    random_seed: int | None
    input_fingerprint: ResearchRunInputFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, ResearchRunId):
            raise ResearchRunValidationError("run_id must be ResearchRunId")
        _validate_timestamp(self.created_at, field_name="research created_at")
        expected = compute_research_run_input_fingerprint(
            datasets=self.datasets,
            replay_policy_version=self.replay_policy_version,
            simulated_start=self.simulated_start,
            simulated_end=self.simulated_end,
            strategy_configuration_id=self.strategy_configuration_id,
            software_revision=self.software_revision,
            execution_model_id=self.execution_model_id,
            transaction_cost_model_id=self.transaction_cost_model_id,
            randomness_mode=self.randomness_mode,
            random_seed=self.random_seed,
        )
        ordered = _validate_datasets(
            self.datasets,
            simulated_start=self.simulated_start,
            simulated_end=self.simulated_end,
        )
        if self.datasets != ordered:
            raise ResearchRunValidationError(
                "research datasets must be retained in canonical dataset order"
            )
        if not isinstance(self.input_fingerprint, ResearchRunInputFingerprint):
            raise ResearchRunValidationError(
                "input_fingerprint must be ResearchRunInputFingerprint"
            )
        if self.input_fingerprint != expected:
            raise ResearchRunValidationError(
                "research input fingerprint must match canonical run inputs"
            )

    @property
    def binds_execution_model(self) -> bool:
        return self.execution_model_id is not None

    @property
    def binds_transaction_cost_model(self) -> bool:
        return self.transaction_cost_model_id is not None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.run_id.logical_values(),
            self.created_at.isoformat(),
            tuple(item.logical_values() for item in self.datasets),
            self.replay_policy_version.logical_values(),
            self.simulated_start.isoformat(),
            self.simulated_end.isoformat(),
            self.strategy_configuration_id.logical_values(),
            self.software_revision.logical_values(),
            (
                self.execution_model_id.logical_values()
                if self.execution_model_id is not None
                else None
            ),
            (
                self.transaction_cost_model_id.logical_values()
                if self.transaction_cost_model_id is not None
                else None
            ),
            self.randomness_mode.value,
            self.random_seed,
            self.input_fingerprint.logical_values(),
        )


def build_research_run_evidence(
    *,
    run_id: ResearchRunId,
    created_at: datetime,
    datasets: tuple[HistoricalDatasetManifest, ...],
    replay_policy_version: ResearchReplayPolicyVersion,
    simulated_start: datetime,
    simulated_end: datetime,
    strategy_configuration_id: ResearchStrategyConfigurationId,
    software_revision: ResearchSoftwareRevision,
    execution_model_id: ResearchExecutionModelId | None,
    transaction_cost_model_id: ResearchTransactionCostModelId | None,
    randomness_mode: ResearchRandomnessMode,
    random_seed: int | None,
) -> Result[ResearchRunEvidence, ResearchRunError]:
    """Build research input evidence without executing replay or trading logic."""

    try:
        if not isinstance(run_id, ResearchRunId):
            raise ResearchRunValidationError("run_id must be ResearchRunId")
        _validate_timestamp(created_at, field_name="research created_at")
        ordered_datasets = _validate_datasets(
            datasets,
            simulated_start=simulated_start,
            simulated_end=simulated_end,
        )
        fingerprint = compute_research_run_input_fingerprint(
            datasets=ordered_datasets,
            replay_policy_version=replay_policy_version,
            simulated_start=simulated_start,
            simulated_end=simulated_end,
            strategy_configuration_id=strategy_configuration_id,
            software_revision=software_revision,
            execution_model_id=execution_model_id,
            transaction_cost_model_id=transaction_cost_model_id,
            randomness_mode=randomness_mode,
            random_seed=random_seed,
        )
        return Success(
            ResearchRunEvidence(
                run_id=run_id,
                created_at=created_at,
                datasets=ordered_datasets,
                replay_policy_version=replay_policy_version,
                simulated_start=simulated_start,
                simulated_end=simulated_end,
                strategy_configuration_id=strategy_configuration_id,
                software_revision=software_revision,
                execution_model_id=execution_model_id,
                transaction_cost_model_id=transaction_cost_model_id,
                randomness_mode=randomness_mode,
                random_seed=random_seed,
                input_fingerprint=fingerprint,
            )
        )
    except ResearchRunError as error:
        return Failure(error)
