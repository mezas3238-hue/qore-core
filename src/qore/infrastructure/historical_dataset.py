from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
from re import fullmatch
from uuid import UUID

from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.replay_availability import ReplayMarketDataObservation
from qore.infrastructure.replay_clock import order_replay_observations
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HistoricalDatasetError(InfrastructureError):
    """Base error for immutable historical replay dataset evidence."""

    __slots__ = ()


class HistoricalDatasetValidationError(HistoricalDatasetError):
    """Violation of an immutable historical replay dataset invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HistoricalDatasetValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HistoricalDatasetValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalDatasetValidationError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime) -> str:
    _validate_timestamp(value, field_name="canonical digest timestamp")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class HistoricalDatasetId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="historical dataset id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HistoricalDatasetRevisionId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="historical dataset revision id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HistoricalDatasetSchemaVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z0-9][a-z0-9._-]*", self.value
        ) is None:
            raise HistoricalDatasetValidationError(
                "historical dataset schema version must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class HistoricalDatasetNormalizationVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z0-9][a-z0-9._-]*", self.value
        ) is None:
            raise HistoricalDatasetValidationError(
                "historical dataset normalization version must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class HistoricalDatasetDigestAlgorithm(StrEnum):
    SHA256 = "sha256"


@dataclass(frozen=True, slots=True)
class HistoricalDatasetDigest:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise HistoricalDatasetValidationError(
                "historical dataset digest must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class HistoricalCoverageGap:
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        _validate_timestamp(self.opened_at, field_name="historical gap opened_at")
        _validate_timestamp(self.closed_at, field_name="historical gap closed_at")
        if self.closed_at <= self.opened_at:
            raise HistoricalDatasetValidationError(
                "historical coverage gap closed_at must be after opened_at"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.opened_at.isoformat(), self.closed_at.isoformat())


@dataclass(frozen=True, slots=True)
class HistoricalOhlcDatasetScope:
    """One exact source/instrument/timeframe historical request scope."""

    source: ExternalSourceDescriptor
    window: HistoricalOhlcWindow

    def __post_init__(self) -> None:
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise HistoricalDatasetValidationError(
                "historical dataset source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.window, HistoricalOhlcWindow):
            raise HistoricalDatasetValidationError(
                "historical dataset window must be HistoricalOhlcWindow"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.source.logical_values(), self.window.logical_values())


@dataclass(frozen=True, slots=True)
class HistoricalDatasetManifest:
    """Immutable administrative identity plus derived dataset evidence summary."""

    dataset_id: HistoricalDatasetId
    revision_id: HistoricalDatasetRevisionId
    parent_revision_id: HistoricalDatasetRevisionId | None
    revision_reason: str | None
    scope: HistoricalOhlcDatasetScope
    assembled_at: datetime
    schema_version: HistoricalDatasetSchemaVersion
    normalization_version: HistoricalDatasetNormalizationVersion
    observation_count: int
    actual_opened_at: datetime
    actual_closed_at: datetime
    gaps: tuple[HistoricalCoverageGap, ...]
    digest_algorithm: HistoricalDatasetDigestAlgorithm
    evidence_digest: HistoricalDatasetDigest

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_id, HistoricalDatasetId):
            raise HistoricalDatasetValidationError(
                "manifest dataset_id must be HistoricalDatasetId"
            )
        if not isinstance(self.revision_id, HistoricalDatasetRevisionId):
            raise HistoricalDatasetValidationError(
                "manifest revision_id must be HistoricalDatasetRevisionId"
            )
        if self.parent_revision_id is not None and not isinstance(
            self.parent_revision_id, HistoricalDatasetRevisionId
        ):
            raise HistoricalDatasetValidationError(
                "manifest parent_revision_id must be HistoricalDatasetRevisionId or None"
            )
        if self.parent_revision_id == self.revision_id:
            raise HistoricalDatasetValidationError(
                "manifest revision cannot be its own parent"
            )
        if (self.parent_revision_id is None) != (self.revision_reason is None):
            raise HistoricalDatasetValidationError(
                "manifest parent revision and revision reason must be present together"
            )
        if self.revision_reason is not None and (
            not isinstance(self.revision_reason, str)
            or not self.revision_reason.strip()
            or self.revision_reason != self.revision_reason.strip()
        ):
            raise HistoricalDatasetValidationError(
                "manifest revision reason must be a non-empty trimmed string"
            )
        if not isinstance(self.scope, HistoricalOhlcDatasetScope):
            raise HistoricalDatasetValidationError(
                "manifest scope must be HistoricalOhlcDatasetScope"
            )
        _validate_timestamp(self.assembled_at, field_name="manifest assembled_at")
        if not isinstance(self.schema_version, HistoricalDatasetSchemaVersion):
            raise HistoricalDatasetValidationError(
                "manifest schema_version must be HistoricalDatasetSchemaVersion"
            )
        if not isinstance(
            self.normalization_version,
            HistoricalDatasetNormalizationVersion,
        ):
            raise HistoricalDatasetValidationError(
                "manifest normalization_version must be HistoricalDatasetNormalizationVersion"
            )
        if type(self.observation_count) is not int or self.observation_count <= 0:
            raise HistoricalDatasetValidationError(
                "manifest observation_count must be a positive int"
            )
        _validate_timestamp(self.actual_opened_at, field_name="manifest actual_opened_at")
        _validate_timestamp(self.actual_closed_at, field_name="manifest actual_closed_at")
        if self.actual_closed_at <= self.actual_opened_at:
            raise HistoricalDatasetValidationError(
                "manifest actual coverage must have positive duration"
            )
        if not isinstance(self.gaps, tuple) or any(
            not isinstance(gap, HistoricalCoverageGap) for gap in self.gaps
        ):
            raise HistoricalDatasetValidationError(
                "manifest gaps must be an immutable HistoricalCoverageGap tuple"
            )
        if not isinstance(self.digest_algorithm, HistoricalDatasetDigestAlgorithm):
            raise HistoricalDatasetValidationError(
                "manifest digest_algorithm must be HistoricalDatasetDigestAlgorithm"
            )
        if not isinstance(self.evidence_digest, HistoricalDatasetDigest):
            raise HistoricalDatasetValidationError(
                "manifest evidence_digest must be HistoricalDatasetDigest"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.dataset_id.logical_values(),
            self.revision_id.logical_values(),
            (
                self.parent_revision_id.logical_values()
                if self.parent_revision_id is not None
                else None
            ),
            self.revision_reason,
            self.scope.logical_values(),
            self.assembled_at.isoformat(),
            self.schema_version.logical_values(),
            self.normalization_version.logical_values(),
            self.observation_count,
            self.actual_opened_at.isoformat(),
            self.actual_closed_at.isoformat(),
            tuple(gap.logical_values() for gap in self.gaps),
            self.digest_algorithm.value,
            self.evidence_digest.logical_values(),
        )


def _validate_observations(
    scope: HistoricalOhlcDatasetScope,
    observations: tuple[ReplayMarketDataObservation, ...],
) -> tuple[
    tuple[ReplayMarketDataObservation, ...],
    datetime,
    datetime,
    tuple[HistoricalCoverageGap, ...],
]:
    if not isinstance(observations, tuple) or not observations or any(
        not isinstance(item, ReplayMarketDataObservation) for item in observations
    ):
        raise HistoricalDatasetValidationError(
            "historical dataset observations must be a non-empty immutable replay tuple"
        )
    replay_ids = tuple(item.observation_id for item in observations)
    if len(set(replay_ids)) != len(replay_ids):
        raise HistoricalDatasetValidationError(
            "historical dataset replay observation identities must be unique"
        )
    snapshot_ids = tuple(item.snapshot_id for item in observations)
    if len(set(snapshot_ids)) != len(snapshot_ids):
        raise HistoricalDatasetValidationError(
            "historical dataset snapshot identities must be unique"
        )

    requested = scope.window
    for observation in observations:
        if not isinstance(observation.payload, OhlcSnapshot):
            raise HistoricalDatasetValidationError(
                "historical OHLC dataset requires OhlcSnapshot replay payloads"
            )
        payload = observation.payload
        if payload.source != scope.source:
            raise HistoricalDatasetValidationError(
                "historical dataset observation source must match scope source"
            )
        if payload.instrument != requested.instrument:
            raise HistoricalDatasetValidationError(
                "historical dataset observation instrument must match scope window"
            )
        if payload.timeframe != requested.timeframe:
            raise HistoricalDatasetValidationError(
                "historical dataset observation timeframe must match scope window"
            )
        if (
            payload.opened_at < requested.opened_at
            or payload.closed_at > requested.closed_at
        ):
            raise HistoricalDatasetValidationError(
                "historical dataset observation must remain inside requested window"
            )

    replay_ordered = order_replay_observations(observations)
    chronological = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.payload.opened_at,
                item.payload.closed_at,
                str(item.snapshot_id.value),
            ),
        )
    )

    gaps: list[HistoricalCoverageGap] = []
    first = chronological[0].payload
    if first.opened_at > requested.opened_at:
        gaps.append(HistoricalCoverageGap(requested.opened_at, first.opened_at))

    previous = first
    for observation in chronological[1:]:
        current = observation.payload
        if current.opened_at < previous.closed_at:
            raise HistoricalDatasetValidationError(
                "historical dataset observations must not overlap"
            )
        if current.opened_at > previous.closed_at:
            gaps.append(HistoricalCoverageGap(previous.closed_at, current.opened_at))
        previous = current

    if previous.closed_at < requested.closed_at:
        gaps.append(HistoricalCoverageGap(previous.closed_at, requested.closed_at))

    return (
        replay_ordered,
        chronological[0].payload.opened_at,
        chronological[-1].payload.closed_at,
        tuple(gaps),
    )


def _canonical_observation(observation: ReplayMarketDataObservation) -> dict[str, object]:
    payload = observation.payload
    if not isinstance(payload, OhlcSnapshot):
        raise HistoricalDatasetValidationError(
            "canonical historical dataset digest requires OhlcSnapshot payload"
        )
    source = payload.source
    return {
        "observation_id": str(observation.observation_id.value),
        "snapshot_id": str(payload.snapshot_id.value),
        "source": {
            "adapter_id": str(source.adapter_id.value),
            "source_id": str(source.source_id.value),
            "port_name": source.port_name.value,
        },
        "instrument": payload.instrument.symbol,
        "timeframe_seconds": payload.timeframe.seconds,
        "opened_at": _utc_iso(payload.opened_at),
        "closed_at": _utc_iso(payload.closed_at),
        "open": payload.open.hex(),
        "high": payload.high.hex(),
        "low": payload.low.hex(),
        "close": payload.close.hex(),
        "availability_evidence_at": _utc_iso(observation.availability_evidence_at),
        "available_at": _utc_iso(observation.available_at),
        "availability_basis": observation.availability_basis.value,
        "availability_evidence_ref": str(observation.availability_evidence_ref.value),
    }


def compute_historical_dataset_evidence_digest(
    scope: HistoricalOhlcDatasetScope,
    observations: tuple[ReplayMarketDataObservation, ...],
    *,
    schema_version: HistoricalDatasetSchemaVersion,
    normalization_version: HistoricalDatasetNormalizationVersion,
) -> HistoricalDatasetDigest:
    """Hash canonical semantic/evidence content, excluding administrative identity."""

    if not isinstance(scope, HistoricalOhlcDatasetScope):
        raise HistoricalDatasetValidationError(
            "digest scope must be HistoricalOhlcDatasetScope"
        )
    if not isinstance(schema_version, HistoricalDatasetSchemaVersion):
        raise HistoricalDatasetValidationError(
            "digest schema_version must be HistoricalDatasetSchemaVersion"
        )
    if not isinstance(
        normalization_version,
        HistoricalDatasetNormalizationVersion,
    ):
        raise HistoricalDatasetValidationError(
            "digest normalization_version must be HistoricalDatasetNormalizationVersion"
        )
    ordered, actual_opened_at, actual_closed_at, gaps = _validate_observations(
        scope,
        observations,
    )
    source = scope.source
    canonical: dict[str, object] = {
        "schema_version": schema_version.value,
        "normalization_version": normalization_version.value,
        "scope": {
            "source": {
                "adapter_id": str(source.adapter_id.value),
                "source_id": str(source.source_id.value),
                "port_name": source.port_name.value,
            },
            "instrument": scope.window.instrument.symbol,
            "timeframe_seconds": scope.window.timeframe.seconds,
            "requested_opened_at": _utc_iso(scope.window.opened_at),
            "requested_closed_at": _utc_iso(scope.window.closed_at),
        },
        "actual_coverage": {
            "opened_at": _utc_iso(actual_opened_at),
            "closed_at": _utc_iso(actual_closed_at),
        },
        "observation_count": len(ordered),
        "gaps": [
            {"opened_at": _utc_iso(gap.opened_at), "closed_at": _utc_iso(gap.closed_at)}
            for gap in gaps
        ],
        "observations": [_canonical_observation(item) for item in ordered],
    }
    payload = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return HistoricalDatasetDigest(sha256(payload).hexdigest())


@dataclass(frozen=True, slots=True)
class HistoricalOhlcReplayDataset:
    """Immutable historical OHLC replay evidence bound to its manifest digest."""

    manifest: HistoricalDatasetManifest
    observations: tuple[ReplayMarketDataObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, HistoricalDatasetManifest):
            raise HistoricalDatasetValidationError(
                "historical dataset manifest must be HistoricalDatasetManifest"
            )
        ordered, actual_opened_at, actual_closed_at, gaps = _validate_observations(
            self.manifest.scope,
            self.observations,
        )
        if self.observations != ordered:
            raise HistoricalDatasetValidationError(
                "historical dataset observations must use canonical replay order"
            )
        if self.manifest.observation_count != len(self.observations):
            raise HistoricalDatasetValidationError(
                "manifest observation_count must match retained observations"
            )
        if (
            self.manifest.actual_opened_at != actual_opened_at
            or self.manifest.actual_closed_at != actual_closed_at
        ):
            raise HistoricalDatasetValidationError(
                "manifest actual coverage must match retained observations"
            )
        if self.manifest.gaps != gaps:
            raise HistoricalDatasetValidationError(
                "manifest gaps must match retained observation coverage"
            )
        expected_digest = compute_historical_dataset_evidence_digest(
            self.manifest.scope,
            self.observations,
            schema_version=self.manifest.schema_version,
            normalization_version=self.manifest.normalization_version,
        )
        if self.manifest.digest_algorithm is not HistoricalDatasetDigestAlgorithm.SHA256:
            raise HistoricalDatasetValidationError(
                "historical dataset supports only SHA256 evidence digest"
            )
        if self.manifest.evidence_digest != expected_digest:
            raise HistoricalDatasetValidationError(
                "manifest evidence digest must match canonical dataset evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.manifest.logical_values(),
            tuple(item.logical_values() for item in self.observations),
        )


def build_historical_ohlc_replay_dataset(
    *,
    dataset_id: HistoricalDatasetId,
    revision_id: HistoricalDatasetRevisionId,
    parent_revision_id: HistoricalDatasetRevisionId | None,
    revision_reason: str | None,
    scope: HistoricalOhlcDatasetScope,
    assembled_at: datetime,
    schema_version: HistoricalDatasetSchemaVersion,
    normalization_version: HistoricalDatasetNormalizationVersion,
    observations: tuple[ReplayMarketDataObservation, ...],
) -> Result[HistoricalOhlcReplayDataset, HistoricalDatasetError]:
    """Build immutable replay evidence without storage or network side effects."""

    try:
        if not isinstance(dataset_id, HistoricalDatasetId):
            raise HistoricalDatasetValidationError(
                "dataset_id must be HistoricalDatasetId"
            )
        if not isinstance(revision_id, HistoricalDatasetRevisionId):
            raise HistoricalDatasetValidationError(
                "revision_id must be HistoricalDatasetRevisionId"
            )
        _validate_timestamp(assembled_at, field_name="historical dataset assembled_at")
        ordered, actual_opened_at, actual_closed_at, gaps = _validate_observations(
            scope,
            observations,
        )
        digest = compute_historical_dataset_evidence_digest(
            scope,
            ordered,
            schema_version=schema_version,
            normalization_version=normalization_version,
        )
        manifest = HistoricalDatasetManifest(
            dataset_id=dataset_id,
            revision_id=revision_id,
            parent_revision_id=parent_revision_id,
            revision_reason=revision_reason,
            scope=scope,
            assembled_at=assembled_at,
            schema_version=schema_version,
            normalization_version=normalization_version,
            observation_count=len(ordered),
            actual_opened_at=actual_opened_at,
            actual_closed_at=actual_closed_at,
            gaps=gaps,
            digest_algorithm=HistoricalDatasetDigestAlgorithm.SHA256,
            evidence_digest=digest,
        )
        return Success(HistoricalOhlcReplayDataset(manifest, ordered))
    except HistoricalDatasetError as error:
        return Failure(error)
