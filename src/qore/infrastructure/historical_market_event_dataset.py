from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetDigest,
    HistoricalDatasetDigestAlgorithm,
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketEventReplayError,
    RetainedMarketEventObservation,
    order_market_event_observations,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HistoricalMarketEventDatasetError(InfrastructureError):
    """Base error for immutable mixed market-event dataset evidence."""

    __slots__ = ()


class HistoricalMarketEventDatasetValidationError(HistoricalMarketEventDatasetError):
    """Violation of a historical mixed market-event dataset invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HistoricalMarketEventDatasetValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalMarketEventDatasetValidationError(
            f"{field_name} must be timezone-aware"
        )


def _utc_iso(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class HistoricalMarketEventDatasetScope:
    """One source/instrument/capture-lineage ingestion window."""

    source: ExternalSourceDescriptor
    instrument: Instrument
    capture_lineage_id: MarketCaptureLineageId
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise HistoricalMarketEventDatasetValidationError(
                "market event dataset source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.instrument, Instrument):
            raise HistoricalMarketEventDatasetValidationError(
                "market event dataset instrument must be Instrument"
            )
        if not isinstance(self.capture_lineage_id, MarketCaptureLineageId):
            raise HistoricalMarketEventDatasetValidationError(
                "market event dataset lineage must be MarketCaptureLineageId"
            )
        _validate_timestamp(self.opened_at, field_name="dataset scope opened_at")
        _validate_timestamp(self.closed_at, field_name="dataset scope closed_at")
        if self.closed_at <= self.opened_at:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset scope closed_at must be after opened_at"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source.logical_values(),
            self.instrument.symbol,
            self.capture_lineage_id.logical_values(),
            _utc_iso(self.opened_at, field_name="dataset scope opened_at"),
            _utc_iso(self.closed_at, field_name="dataset scope closed_at"),
        )


@dataclass(frozen=True, slots=True)
class HistoricalMarketEventDatasetManifest:
    """Administrative revision identity plus derived mixed-event evidence."""

    dataset_id: HistoricalDatasetId
    revision_id: HistoricalDatasetRevisionId
    parent_revision_id: HistoricalDatasetRevisionId | None
    revision_reason: str | None
    scope: HistoricalMarketEventDatasetScope
    assembled_at: datetime
    schema_version: HistoricalDatasetSchemaVersion
    normalization_version: HistoricalDatasetNormalizationVersion
    observation_count: int
    first_core_ingress_at: datetime
    last_core_ingress_at: datetime
    digest_algorithm: HistoricalDatasetDigestAlgorithm
    evidence_digest: HistoricalDatasetDigest

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_id, HistoricalDatasetId):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest dataset_id must be HistoricalDatasetId"
            )
        if not isinstance(self.revision_id, HistoricalDatasetRevisionId):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest revision_id must be HistoricalDatasetRevisionId"
            )
        if self.parent_revision_id is not None and not isinstance(
            self.parent_revision_id,
            HistoricalDatasetRevisionId,
        ):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest parent revision must be HistoricalDatasetRevisionId or None"
            )
        if self.parent_revision_id == self.revision_id:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest revision cannot be its own parent"
            )
        if (self.parent_revision_id is None) != (self.revision_reason is None):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest parent revision and reason must be present together"
            )
        if self.revision_reason is not None and (
            not isinstance(self.revision_reason, str)
            or not self.revision_reason.strip()
            or self.revision_reason != self.revision_reason.strip()
        ):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest revision reason must be a non-empty trimmed string"
            )
        if not isinstance(self.scope, HistoricalMarketEventDatasetScope):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest scope must be HistoricalMarketEventDatasetScope"
            )
        _validate_timestamp(self.assembled_at, field_name="manifest assembled_at")
        if self.assembled_at < self.scope.closed_at:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest cannot be assembled before capture window closes"
            )
        if not isinstance(self.schema_version, HistoricalDatasetSchemaVersion):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest schema_version must be HistoricalDatasetSchemaVersion"
            )
        if not isinstance(
            self.normalization_version,
            HistoricalDatasetNormalizationVersion,
        ):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest normalization_version must be "
                "HistoricalDatasetNormalizationVersion"
            )
        if type(self.observation_count) is not int or self.observation_count <= 0:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest observation_count must be a positive int"
            )
        _validate_timestamp(
            self.first_core_ingress_at,
            field_name="manifest first_core_ingress_at",
        )
        _validate_timestamp(
            self.last_core_ingress_at,
            field_name="manifest last_core_ingress_at",
        )
        if self.last_core_ingress_at < self.first_core_ingress_at:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest ingress coverage cannot move backwards"
            )
        if self.assembled_at < self.last_core_ingress_at:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest cannot predate retained core ingress"
            )
        if not isinstance(self.digest_algorithm, HistoricalDatasetDigestAlgorithm):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest digest_algorithm must be HistoricalDatasetDigestAlgorithm"
            )
        if not isinstance(self.evidence_digest, HistoricalDatasetDigest):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest evidence_digest must be HistoricalDatasetDigest"
            )

    def logical_values(self) -> tuple[object, ...]:
        parent = (
            self.parent_revision_id.logical_values()
            if self.parent_revision_id is not None
            else None
        )
        return (
            self.dataset_id.logical_values(),
            self.revision_id.logical_values(),
            parent,
            self.revision_reason,
            self.scope.logical_values(),
            _utc_iso(self.assembled_at, field_name="manifest assembled_at"),
            self.schema_version.logical_values(),
            self.normalization_version.logical_values(),
            self.observation_count,
            _utc_iso(
                self.first_core_ingress_at,
                field_name="manifest first_core_ingress_at",
            ),
            _utc_iso(
                self.last_core_ingress_at,
                field_name="manifest last_core_ingress_at",
            ),
            self.digest_algorithm.value,
            self.evidence_digest.logical_values(),
        )


def _validate_observations(
    scope: HistoricalMarketEventDatasetScope,
    observations: tuple[RetainedMarketEventObservation, ...],
) -> tuple[
    tuple[RetainedMarketEventObservation, ...],
    datetime,
    datetime,
]:
    if not isinstance(scope, HistoricalMarketEventDatasetScope):
        raise HistoricalMarketEventDatasetValidationError(
            "market event dataset scope must be HistoricalMarketEventDatasetScope"
        )
    if not isinstance(observations, tuple) or not observations or any(
        not isinstance(item, RetainedMarketEventObservation)
        for item in observations
    ):
        raise HistoricalMarketEventDatasetValidationError(
            "market event dataset observations must be a non-empty immutable tuple"
        )
    try:
        ordered = order_market_event_observations(observations)
    except MarketEventReplayError as error:
        raise HistoricalMarketEventDatasetValidationError(
            "market event dataset arrival provenance is invalid"
        ) from error

    for item in ordered:
        if item.capture_lineage_id != scope.capture_lineage_id:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset observation capture lineage must match scope"
            )
        if item.source != scope.source:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset observation source must match scope"
            )
        if item.instrument != scope.instrument:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset observation instrument must match scope"
            )
        if not scope.opened_at <= item.core_ingress_at < scope.closed_at:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset observation core ingress must remain inside capture window"
            )

    return ordered, ordered[0].core_ingress_at, ordered[-1].core_ingress_at


def compute_historical_market_event_evidence_digest(
    scope: HistoricalMarketEventDatasetScope,
    observations: tuple[RetainedMarketEventObservation, ...],
    *,
    schema_version: HistoricalDatasetSchemaVersion,
    normalization_version: HistoricalDatasetNormalizationVersion,
) -> HistoricalDatasetDigest:
    """Hash exact mixed evidence, excluding administrative dataset identity."""

    if not isinstance(schema_version, HistoricalDatasetSchemaVersion):
        raise HistoricalMarketEventDatasetValidationError(
            "digest schema_version must be HistoricalDatasetSchemaVersion"
        )
    if not isinstance(
        normalization_version,
        HistoricalDatasetNormalizationVersion,
    ):
        raise HistoricalMarketEventDatasetValidationError(
            "digest normalization_version must be "
            "HistoricalDatasetNormalizationVersion"
        )
    ordered, _, _ = _validate_observations(scope, observations)
    canonical: dict[str, object] = {
        "schema_version": schema_version.value,
        "normalization_version": normalization_version.value,
        "scope": scope.logical_values(),
        "observation_count": len(ordered),
        "observations": [item.logical_values() for item in ordered],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return HistoricalDatasetDigest(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class HistoricalMarketEventDataset:
    """Immutable mixed event dataset bound to exact retained evidence."""

    manifest: HistoricalMarketEventDatasetManifest
    observations: tuple[RetainedMarketEventObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, HistoricalMarketEventDatasetManifest):
            raise HistoricalMarketEventDatasetValidationError(
                "dataset manifest must be HistoricalMarketEventDatasetManifest"
            )
        ordered, first_ingress, last_ingress = _validate_observations(
            self.manifest.scope,
            self.observations,
        )
        if self.observations != ordered:
            raise HistoricalMarketEventDatasetValidationError(
                "dataset observations must use canonical arrival order"
            )
        if self.manifest.observation_count != len(self.observations):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest observation_count must match observations"
            )
        if (
            self.manifest.first_core_ingress_at != first_ingress
            or self.manifest.last_core_ingress_at != last_ingress
        ):
            raise HistoricalMarketEventDatasetValidationError(
                "manifest ingress coverage must match retained observations"
            )
        if (
            self.manifest.digest_algorithm
            is not HistoricalDatasetDigestAlgorithm.SHA256
        ):
            raise HistoricalMarketEventDatasetValidationError(
                "market event dataset supports only SHA256 evidence digest"
            )
        expected = compute_historical_market_event_evidence_digest(
            self.manifest.scope,
            self.observations,
            schema_version=self.manifest.schema_version,
            normalization_version=self.manifest.normalization_version,
        )
        if self.manifest.evidence_digest != expected:
            raise HistoricalMarketEventDatasetValidationError(
                "manifest evidence digest must match canonical mixed evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.manifest.logical_values(),
            tuple(item.logical_values() for item in self.observations),
        )


def build_historical_market_event_dataset(
    *,
    dataset_id: HistoricalDatasetId,
    revision_id: HistoricalDatasetRevisionId,
    parent_revision_id: HistoricalDatasetRevisionId | None,
    revision_reason: str | None,
    scope: HistoricalMarketEventDatasetScope,
    assembled_at: datetime,
    schema_version: HistoricalDatasetSchemaVersion,
    normalization_version: HistoricalDatasetNormalizationVersion,
    observations: tuple[RetainedMarketEventObservation, ...],
) -> Result[HistoricalMarketEventDataset, HistoricalMarketEventDatasetError]:
    """Build a canonical mixed replay dataset without IO or hidden clocks."""

    try:
        if not isinstance(dataset_id, HistoricalDatasetId):
            raise HistoricalMarketEventDatasetValidationError(
                "dataset_id must be HistoricalDatasetId"
            )
        if not isinstance(revision_id, HistoricalDatasetRevisionId):
            raise HistoricalMarketEventDatasetValidationError(
                "revision_id must be HistoricalDatasetRevisionId"
            )
        _validate_timestamp(assembled_at, field_name="dataset assembled_at")
        ordered, first_ingress, last_ingress = _validate_observations(
            scope,
            observations,
        )
        digest = compute_historical_market_event_evidence_digest(
            scope,
            ordered,
            schema_version=schema_version,
            normalization_version=normalization_version,
        )
        manifest = HistoricalMarketEventDatasetManifest(
            dataset_id=dataset_id,
            revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            revision_reason=revision_reason,
            scope=scope,
            assembled_at=assembled_at,
            schema_version=schema_version,
            normalization_version=normalization_version,
            observation_count=len(ordered),
            first_core_ingress_at=first_ingress,
            last_core_ingress_at=last_ingress,
            digest_algorithm=HistoricalDatasetDigestAlgorithm.SHA256,
            evidence_digest=digest,
        )
        return Success(HistoricalMarketEventDataset(manifest, ordered))
    except HistoricalMarketEventDatasetError as error:
        return Failure(error)
