from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from re import fullmatch

from qore.infrastructure.historical_dataset import (
    HistoricalCoverageGap,
    HistoricalDatasetManifest,
    HistoricalOhlcDatasetScope,
    HistoricalOhlcReplayDataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.market_data_integrity import (
    MarketDataIngressRecord,
    MarketDataIntegrityAssessment,
    MarketDataIntegrityCertificate,
    MarketDataIntegrityCertificateStatus,
    MarketDataIntegrityPolicy,
    MarketDataIntegrityState,
    evaluate_market_data_integrity,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.replay_availability import ReplayMarketDataObservation
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DATASET_QUALIFICATION_SCHEMA = "qore.dataset-integrity-qualification.v1"
_TEMPORAL_SEMANTICS = "core-ingress-safe.v1"
_RUN_QUALIFICATION_SCHEMA = "qore.integrity-qualified-research-run.v1"


class DatasetIntegrityQualificationError(InfrastructureError):
    """Base error for integrity-qualified historical replay evidence."""

    __slots__ = ()


class DatasetIntegrityQualificationValidationError(DatasetIntegrityQualificationError):
    """Violation of a dataset-integrity qualification invariant."""

    __slots__ = ()


def _require_aware_datetime(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise DatasetIntegrityQualificationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise DatasetIntegrityQualificationValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value


def _utc_iso(value: datetime, *, field_name: str) -> str:
    return _require_aware_datetime(
        value,
        field_name=field_name,
    ).astimezone(UTC).isoformat(timespec="microseconds")


def _canonical_json(value: dict[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_hex(value: dict[str, object]) -> str:
    return sha256(_canonical_json(value)).hexdigest()


def _canonical_external_source(source: ExternalSourceDescriptor) -> dict[str, object]:
    if not isinstance(source, ExternalSourceDescriptor):
        raise DatasetIntegrityQualificationValidationError(
            "external source must be ExternalSourceDescriptor"
        )
    return {
        "adapter_id": str(source.adapter_id.value),
        "source_id": str(source.source_id.value),
        "port_name": source.port_name.value,
    }


def _canonical_historical_window(window: HistoricalOhlcWindow) -> dict[str, object]:
    if not isinstance(window, HistoricalOhlcWindow):
        raise DatasetIntegrityQualificationValidationError(
            "historical window must be HistoricalOhlcWindow"
        )
    return {
        "instrument": window.instrument.symbol,
        "timeframe_seconds": window.timeframe.seconds,
        "opened_at": _utc_iso(
            window.opened_at,
            field_name="historical window opened_at",
        ),
        "closed_at": _utc_iso(
            window.closed_at,
            field_name="historical window closed_at",
        ),
        "interval_count": window.interval_count,
    }


def _canonical_dataset_scope(scope: HistoricalOhlcDatasetScope) -> dict[str, object]:
    if not isinstance(scope, HistoricalOhlcDatasetScope):
        raise DatasetIntegrityQualificationValidationError(
            "dataset scope must be HistoricalOhlcDatasetScope"
        )
    return {
        "source": _canonical_external_source(scope.source),
        "window": _canonical_historical_window(scope.window),
    }


def _canonical_coverage_gap(gap: HistoricalCoverageGap) -> dict[str, object]:
    if not isinstance(gap, HistoricalCoverageGap):
        raise DatasetIntegrityQualificationValidationError(
            "coverage gap must be HistoricalCoverageGap"
        )
    return {
        "opened_at": _utc_iso(
            gap.opened_at,
            field_name="coverage gap opened_at",
        ),
        "closed_at": _utc_iso(
            gap.closed_at,
            field_name="coverage gap closed_at",
        ),
    }


def _canonical_dataset_manifest(
    manifest: HistoricalDatasetManifest,
) -> dict[str, object]:
    if not isinstance(manifest, HistoricalDatasetManifest):
        raise DatasetIntegrityQualificationValidationError(
            "dataset manifest must be HistoricalDatasetManifest"
        )
    return {
        "dataset_id": str(manifest.dataset_id.value),
        "revision_id": str(manifest.revision_id.value),
        "parent_revision_id": (
            str(manifest.parent_revision_id.value)
            if manifest.parent_revision_id is not None
            else None
        ),
        "revision_reason": manifest.revision_reason,
        "scope": _canonical_dataset_scope(manifest.scope),
        "assembled_at": _utc_iso(
            manifest.assembled_at,
            field_name="dataset assembled_at",
        ),
        "schema_version": manifest.schema_version.value,
        "normalization_version": manifest.normalization_version.value,
        "observation_count": manifest.observation_count,
        "actual_opened_at": _utc_iso(
            manifest.actual_opened_at,
            field_name="dataset actual_opened_at",
        ),
        "actual_closed_at": _utc_iso(
            manifest.actual_closed_at,
            field_name="dataset actual_closed_at",
        ),
        "gaps": [_canonical_coverage_gap(gap) for gap in manifest.gaps],
        "digest_algorithm": manifest.digest_algorithm.value,
        "evidence_digest": manifest.evidence_digest.value,
    }


def _canonical_ohlc_snapshot(snapshot: OhlcSnapshot) -> dict[str, object]:
    if not isinstance(snapshot, OhlcSnapshot):
        raise DatasetIntegrityQualificationValidationError(
            "snapshot must be OhlcSnapshot"
        )
    return {
        "snapshot_id": str(snapshot.snapshot_id.value),
        "instrument": snapshot.instrument.symbol,
        "source": _canonical_external_source(snapshot.source),
        "timeframe_seconds": snapshot.timeframe.seconds,
        "opened_at": _utc_iso(
            snapshot.opened_at,
            field_name="OHLC opened_at",
        ),
        "closed_at": _utc_iso(
            snapshot.closed_at,
            field_name="OHLC closed_at",
        ),
        "open": snapshot.open.hex(),
        "high": snapshot.high.hex(),
        "low": snapshot.low.hex(),
        "close": snapshot.close.hex(),
    }


def _canonical_replay_observation(
    observation: ReplayMarketDataObservation,
) -> dict[str, object]:
    if not isinstance(observation, ReplayMarketDataObservation):
        raise DatasetIntegrityQualificationValidationError(
            "replay observation must be ReplayMarketDataObservation"
        )
    if not isinstance(observation.payload, OhlcSnapshot):
        raise DatasetIntegrityQualificationValidationError(
            "dataset integrity qualification requires OhlcSnapshot replay payloads"
        )
    return {
        "observation_id": str(observation.observation_id.value),
        "payload": _canonical_ohlc_snapshot(observation.payload),
        "availability_evidence_at": _utc_iso(
            observation.availability_evidence_at,
            field_name="availability_evidence_at",
        ),
        "available_at": _utc_iso(
            observation.available_at,
            field_name="available_at",
        ),
        "availability_basis": observation.availability_basis.value,
        "availability_evidence_ref": str(
            observation.availability_evidence_ref.value
        ),
    }


def _canonical_integrity_policy(
    policy: MarketDataIntegrityPolicy,
) -> dict[str, object]:
    if not isinstance(policy, MarketDataIntegrityPolicy):
        raise DatasetIntegrityQualificationValidationError(
            "qualification_policy must be MarketDataIntegrityPolicy"
        )
    return {
        "max_delivery_delay_microseconds": policy.max_delivery_delay.microseconds,
    }


def _canonical_ingress_record(record: MarketDataIngressRecord) -> dict[str, object]:
    if not isinstance(record, MarketDataIngressRecord):
        raise DatasetIntegrityQualificationValidationError(
            "integrity record must be MarketDataIngressRecord"
        )
    return {
        "snapshot": _canonical_ohlc_snapshot(record.snapshot),
        "hosting_received_at": _utc_iso(
            record.hosting_received_at,
            field_name="hosting_received_at",
        ),
        "core_ingress_at": _utc_iso(
            record.core_ingress_at,
            field_name="core_ingress_at",
        ),
        "delivery_delay_microseconds": record.delivery_delay.microseconds,
        "normalization_evidence_ref": str(
            record.normalization_evidence_ref.value
        ),
    }


def _canonical_integrity_assessment(
    assessment: MarketDataIntegrityAssessment,
) -> dict[str, object]:
    if not isinstance(assessment, MarketDataIntegrityAssessment):
        raise DatasetIntegrityQualificationValidationError(
            "integrity assessment must be MarketDataIntegrityAssessment"
        )
    return {
        "assessment_id": str(assessment.assessment_id.value),
        "state": assessment.state.value,
        "disposition": assessment.disposition.value,
        "record": _canonical_ingress_record(assessment.record),
        "previous_snapshot_id": (
            str(assessment.previous_snapshot_id.value)
            if assessment.previous_snapshot_id is not None
            else None
        ),
        "expected_opened_at": (
            _utc_iso(
                assessment.expected_opened_at,
                field_name="expected_opened_at",
            )
            if assessment.expected_opened_at is not None
            else None
        ),
        "rationale_code": assessment.rationale_code.value,
        "evidence_refs": [str(ref.value) for ref in assessment.evidence_refs],
        "assessed_at": _utc_iso(
            assessment.assessed_at,
            field_name="assessed_at",
        ),
    }


def _canonical_integrity_certificate(
    certificate: MarketDataIntegrityCertificate,
) -> dict[str, object]:
    if not isinstance(certificate, MarketDataIntegrityCertificate):
        raise DatasetIntegrityQualificationValidationError(
            "integrity certificate must be MarketDataIntegrityCertificate"
        )
    return {
        "certificate_id": str(certificate.certificate_id.value),
        "status": certificate.status.value,
        "assessment": _canonical_integrity_assessment(certificate.assessment),
        "issued_at": _utc_iso(
            certificate.issued_at,
            field_name="certificate issued_at",
        ),
        "evidence_ref": str(certificate.evidence_ref.value),
    }


def _canonical_research_run(run: ResearchRunEvidence) -> dict[str, object]:
    if not isinstance(run, ResearchRunEvidence):
        raise DatasetIntegrityQualificationValidationError(
            "run must be ResearchRunEvidence"
        )
    return {
        "run_id": str(run.run_id.value),
        "created_at": _utc_iso(
            run.created_at,
            field_name="research run created_at",
        ),
        "datasets": [
            _canonical_dataset_manifest(manifest) for manifest in run.datasets
        ],
        "replay_policy_version": run.replay_policy_version.value,
        "simulated_start": _utc_iso(
            run.simulated_start,
            field_name="research run simulated_start",
        ),
        "simulated_end": _utc_iso(
            run.simulated_end,
            field_name="research run simulated_end",
        ),
        "strategy_configuration_id": str(run.strategy_configuration_id.value),
        "software_revision": run.software_revision.value,
        "execution_model_id": (
            str(run.execution_model_id.value)
            if run.execution_model_id is not None
            else None
        ),
        "transaction_cost_model_id": (
            str(run.transaction_cost_model_id.value)
            if run.transaction_cost_model_id is not None
            else None
        ),
        "randomness_mode": run.randomness_mode.value,
        "random_seed": run.random_seed,
        "input_fingerprint": run.input_fingerprint.value,
    }


@dataclass(frozen=True, slots=True)
class DatasetIntegrityQualificationFingerprint:
    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or fullmatch(r"[0-9a-f]{64}", self.value) is None
        ):
            raise DatasetIntegrityQualificationValidationError(
                "dataset integrity qualification fingerprint must be "
                "64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class IntegrityQualifiedResearchRunFingerprint:
    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or fullmatch(r"[0-9a-f]{64}", self.value) is None
        ):
            raise DatasetIntegrityQualificationValidationError(
                "integrity-qualified research run fingerprint must be "
                "64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _ohlc_payload(
    observation: ReplayMarketDataObservation,
) -> OhlcSnapshot:
    if not isinstance(observation, ReplayMarketDataObservation):
        raise DatasetIntegrityQualificationValidationError(
            "chronological replay item must be ReplayMarketDataObservation"
        )
    if not isinstance(observation.payload, OhlcSnapshot):
        raise DatasetIntegrityQualificationValidationError(
            "chronological replay item payload must be OhlcSnapshot"
        )
    return observation.payload


def _chronological_observations(
    dataset: HistoricalOhlcReplayDataset,
) -> tuple[ReplayMarketDataObservation, ...]:
    return tuple(
        sorted(
            dataset.observations,
            key=lambda observation: (
                _ohlc_payload(observation).opened_at,
                _ohlc_payload(observation).closed_at,
                str(observation.snapshot_id.value),
            ),
        )
    )


def _validate_predecessor(
    predecessor: MarketDataIntegrityCertificate | None,
    first_observation: ReplayMarketDataObservation,
) -> tuple[MarketDataIngressRecord, ...]:
    if predecessor is None:
        return ()
    if not isinstance(predecessor, MarketDataIntegrityCertificate):
        raise DatasetIntegrityQualificationValidationError(
            "predecessor_certificate must be MarketDataIntegrityCertificate or None"
        )
    if predecessor.status is not MarketDataIntegrityCertificateStatus.CERTIFIED:
        raise DatasetIntegrityQualificationValidationError(
            "predecessor_certificate must be CERTIFIED"
        )
    if predecessor.assessment.state is not MarketDataIntegrityState.VALID:
        raise DatasetIntegrityQualificationValidationError(
            "predecessor_certificate assessment must be VALID"
        )
    if not isinstance(first_observation.payload, OhlcSnapshot):
        raise DatasetIntegrityQualificationValidationError(
            "first replay observation payload must be OhlcSnapshot"
        )
    previous = predecessor.assessment.record.snapshot
    current = first_observation.payload
    if (
        previous.source != current.source
        or previous.instrument != current.instrument
        or previous.timeframe != current.timeframe
    ):
        raise DatasetIntegrityQualificationValidationError(
            "predecessor_certificate scope must match first chronological observation"
        )
    if previous.closed_at != current.opened_at:
        raise DatasetIntegrityQualificationValidationError(
            "predecessor_certificate must be contiguous with first chronological observation"
        )
    return (predecessor.assessment.record,)


def _qualified_pairs(
    dataset: HistoricalOhlcReplayDataset,
    certificates: tuple[MarketDataIntegrityCertificate, ...],
) -> tuple[
    tuple[ReplayMarketDataObservation, MarketDataIntegrityCertificate],
    ...,
]:
    chronological = _chronological_observations(dataset)
    if len(certificates) != len(chronological):
        raise DatasetIntegrityQualificationValidationError(
            "certificates must cover every replay observation exactly once"
        )
    pairs = tuple(zip(chronological, certificates, strict=True))
    seen_observation_ids: set[object] = set()
    seen_certificate_ids: set[object] = set()
    for observation, certificate in pairs:
        if certificate.status is not MarketDataIntegrityCertificateStatus.CERTIFIED:
            raise DatasetIntegrityQualificationValidationError(
                "every qualification certificate must be CERTIFIED"
            )
        if certificate.assessment.state is not MarketDataIntegrityState.VALID:
            raise DatasetIntegrityQualificationValidationError(
                "every qualification certificate assessment must be VALID"
            )
        if not isinstance(observation.payload, OhlcSnapshot):
            raise DatasetIntegrityQualificationValidationError(
                "qualification observation payload must be OhlcSnapshot"
            )
        if certificate.assessment.record.snapshot != observation.payload:
            raise DatasetIntegrityQualificationValidationError(
                "certificate snapshot must equal the exact chronological replay snapshot"
            )
        if observation.observation_id in seen_observation_ids:
            raise DatasetIntegrityQualificationValidationError(
                "replay observation paired more than once"
            )
        if certificate.certificate_id in seen_certificate_ids:
            raise DatasetIntegrityQualificationValidationError(
                "integrity certificate paired more than once"
            )
        seen_observation_ids.add(observation.observation_id)
        seen_certificate_ids.add(certificate.certificate_id)
    return pairs


def _reproduce_assessments(
    pairs: tuple[
        tuple[ReplayMarketDataObservation, MarketDataIntegrityCertificate],
        ...,
    ],
    *,
    qualification_policy: MarketDataIntegrityPolicy,
    predecessor_certificate: MarketDataIntegrityCertificate | None,
) -> None:
    if not pairs:
        raise DatasetIntegrityQualificationValidationError(
            "dataset integrity qualification requires at least one pair"
        )
    accepted_history = _validate_predecessor(
        predecessor_certificate,
        pairs[0][0],
    )
    for _, certificate in pairs:
        result = evaluate_market_data_integrity(
            record=certificate.assessment.record,
            accepted_history=accepted_history,
            policy=qualification_policy,
            assessment_id=certificate.assessment.assessment_id,
            assessed_at=certificate.assessment.assessed_at,
        )
        if isinstance(result, Failure):
            raise DatasetIntegrityQualificationValidationError(
                "integrity assessment reproduction failed under qualification policy"
            )
        if not isinstance(result, Success):
            raise DatasetIntegrityQualificationValidationError(
                "integrity assessment reproduction returned malformed Result"
            )
        if result.value != certificate.assessment:
            raise DatasetIntegrityQualificationValidationError(
                "integrity assessment reproduction did not equal retained assessment"
            )
        accepted_history = (*accepted_history, certificate.assessment.record)


def _enforce_t2(
    dataset: HistoricalOhlcReplayDataset,
    pairs: tuple[
        tuple[ReplayMarketDataObservation, MarketDataIntegrityCertificate],
        ...,
    ],
) -> None:
    certificate_by_snapshot_id = {
        observation.snapshot_id: certificate for observation, certificate in pairs
    }
    if len(certificate_by_snapshot_id) != len(pairs):
        raise DatasetIntegrityQualificationValidationError(
            "snapshot identities must remain unique across validated pairs"
        )
    for observation in dataset.observations:
        certificate = certificate_by_snapshot_id.get(observation.snapshot_id)
        if certificate is None:
            raise DatasetIntegrityQualificationValidationError(
                "replay observation missing exact paired certificate"
            )
        if observation.available_at < certificate.assessment.record.core_ingress_at:
            raise DatasetIntegrityQualificationValidationError(
                "T2 violation: replay available_at predates exact paired core_ingress_at"
            )


def _canonical_dataset_qualification(
    *,
    dataset: HistoricalOhlcReplayDataset,
    qualification_policy: MarketDataIntegrityPolicy,
    predecessor_certificate: MarketDataIntegrityCertificate | None,
    pairs: tuple[
        tuple[ReplayMarketDataObservation, MarketDataIntegrityCertificate],
        ...,
    ],
) -> dict[str, object]:
    return {
        "schema": _DATASET_QUALIFICATION_SCHEMA,
        "temporal_semantics": _TEMPORAL_SEMANTICS,
        "dataset_manifest": _canonical_dataset_manifest(dataset.manifest),
        "qualification_policy": _canonical_integrity_policy(qualification_policy),
        "anchor": {
            "mode": (
                "predecessor-certificate"
                if predecessor_certificate is not None
                else "empty-history-root"
            ),
            "predecessor_certificate": (
                _canonical_integrity_certificate(predecessor_certificate)
                if predecessor_certificate is not None
                else None
            ),
        },
        "qualified_items": [
            {
                "observation": _canonical_replay_observation(observation),
                "certificate": _canonical_integrity_certificate(certificate),
            }
            for observation, certificate in pairs
        ],
    }


def _compute_dataset_qualification_fingerprint(
    *,
    dataset: HistoricalOhlcReplayDataset,
    qualification_policy: MarketDataIntegrityPolicy,
    predecessor_certificate: MarketDataIntegrityCertificate | None,
    certificates: tuple[MarketDataIntegrityCertificate, ...],
) -> DatasetIntegrityQualificationFingerprint:
    pairs = _qualified_pairs(dataset, certificates)
    canonical = _canonical_dataset_qualification(
        dataset=dataset,
        qualification_policy=qualification_policy,
        predecessor_certificate=predecessor_certificate,
        pairs=pairs,
    )
    return DatasetIntegrityQualificationFingerprint(_sha256_hex(canonical))


@dataclass(frozen=True, slots=True)
class DatasetIntegrityQualification:
    """Exact revalidation evidence for one complete historical replay dataset."""

    dataset: HistoricalOhlcReplayDataset
    qualification_policy: MarketDataIntegrityPolicy
    predecessor_certificate: MarketDataIntegrityCertificate | None
    certificates: tuple[MarketDataIntegrityCertificate, ...]
    fingerprint: DatasetIntegrityQualificationFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, HistoricalOhlcReplayDataset):
            raise DatasetIntegrityQualificationValidationError(
                "dataset must be HistoricalOhlcReplayDataset"
            )
        if not isinstance(self.qualification_policy, MarketDataIntegrityPolicy):
            raise DatasetIntegrityQualificationValidationError(
                "qualification_policy must be MarketDataIntegrityPolicy"
            )
        if self.predecessor_certificate is not None and not isinstance(
            self.predecessor_certificate,
            MarketDataIntegrityCertificate,
        ):
            raise DatasetIntegrityQualificationValidationError(
                "predecessor_certificate must be MarketDataIntegrityCertificate or None"
            )
        if not isinstance(self.certificates, tuple) or any(
            not isinstance(item, MarketDataIntegrityCertificate)
            for item in self.certificates
        ):
            raise DatasetIntegrityQualificationValidationError(
                "certificates must be an immutable MarketDataIntegrityCertificate tuple"
            )
        if not isinstance(
            self.fingerprint,
            DatasetIntegrityQualificationFingerprint,
        ):
            raise DatasetIntegrityQualificationValidationError(
                "fingerprint must be DatasetIntegrityQualificationFingerprint"
            )
        if self.dataset.manifest.gaps != ():
            raise DatasetIntegrityQualificationValidationError(
                "dataset integrity qualification requires complete coverage with no gaps"
            )
        if len(self.certificates) != len(self.dataset.observations):
            raise DatasetIntegrityQualificationValidationError(
                "certificates must match replay observation count"
            )
        pairs = _qualified_pairs(self.dataset, self.certificates)
        _reproduce_assessments(
            pairs,
            qualification_policy=self.qualification_policy,
            predecessor_certificate=self.predecessor_certificate,
        )
        _enforce_t2(self.dataset, pairs)
        expected = _compute_dataset_qualification_fingerprint(
            dataset=self.dataset,
            qualification_policy=self.qualification_policy,
            predecessor_certificate=self.predecessor_certificate,
            certificates=self.certificates,
        )
        if self.fingerprint != expected:
            raise DatasetIntegrityQualificationValidationError(
                "dataset integrity qualification fingerprint mismatch"
            )


def build_dataset_integrity_qualification(
    *,
    dataset: HistoricalOhlcReplayDataset,
    qualification_policy: MarketDataIntegrityPolicy,
    predecessor_certificate: MarketDataIntegrityCertificate | None,
    certificates: tuple[MarketDataIntegrityCertificate, ...],
) -> Result[DatasetIntegrityQualification, DatasetIntegrityQualificationError]:
    """Build deterministic CERTIFIED-only integrity qualification evidence."""

    try:
        if not isinstance(dataset, HistoricalOhlcReplayDataset):
            raise DatasetIntegrityQualificationValidationError(
                "dataset must be HistoricalOhlcReplayDataset"
            )
        if not isinstance(qualification_policy, MarketDataIntegrityPolicy):
            raise DatasetIntegrityQualificationValidationError(
                "qualification_policy must be MarketDataIntegrityPolicy"
            )
        if predecessor_certificate is not None and not isinstance(
            predecessor_certificate,
            MarketDataIntegrityCertificate,
        ):
            raise DatasetIntegrityQualificationValidationError(
                "predecessor_certificate must be MarketDataIntegrityCertificate or None"
            )
        if not isinstance(certificates, tuple) or any(
            not isinstance(item, MarketDataIntegrityCertificate) for item in certificates
        ):
            raise DatasetIntegrityQualificationValidationError(
                "certificates must be an immutable MarketDataIntegrityCertificate tuple"
            )
        fingerprint = _compute_dataset_qualification_fingerprint(
            dataset=dataset,
            qualification_policy=qualification_policy,
            predecessor_certificate=predecessor_certificate,
            certificates=certificates,
        )
        return Success(
            DatasetIntegrityQualification(
                dataset=dataset,
                qualification_policy=qualification_policy,
                predecessor_certificate=predecessor_certificate,
                certificates=certificates,
                fingerprint=fingerprint,
            )
        )
    except DatasetIntegrityQualificationError as error:
        return Failure(error)


def _canonical_integrity_qualified_research_run(
    *,
    run: ResearchRunEvidence,
    qualifications: tuple[DatasetIntegrityQualification, ...],
) -> dict[str, object]:
    return {
        "schema": _RUN_QUALIFICATION_SCHEMA,
        "run": _canonical_research_run(run),
        "qualifications": [
            {
                "dataset_id": str(
                    qualification.dataset.manifest.dataset_id.value
                ),
                "qualification_fingerprint": qualification.fingerprint.value,
            }
            for qualification in qualifications
        ],
    }


def _compute_integrity_qualified_research_run_fingerprint(
    *,
    run: ResearchRunEvidence,
    qualifications: tuple[DatasetIntegrityQualification, ...],
) -> IntegrityQualifiedResearchRunFingerprint:
    return IntegrityQualifiedResearchRunFingerprint(
        _sha256_hex(
            _canonical_integrity_qualified_research_run(
                run=run,
                qualifications=qualifications,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class IntegrityQualifiedResearchRun:
    """Exact research run whose retained datasets each have one integrity qualification."""

    run: ResearchRunEvidence
    qualifications: tuple[DatasetIntegrityQualification, ...]
    fingerprint: IntegrityQualifiedResearchRunFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.run, ResearchRunEvidence):
            raise DatasetIntegrityQualificationValidationError(
                "run must be ResearchRunEvidence"
            )
        if not isinstance(self.qualifications, tuple) or any(
            not isinstance(item, DatasetIntegrityQualification)
            for item in self.qualifications
        ):
            raise DatasetIntegrityQualificationValidationError(
                "qualifications must be an immutable DatasetIntegrityQualification tuple"
            )
        if not isinstance(
            self.fingerprint,
            IntegrityQualifiedResearchRunFingerprint,
        ):
            raise DatasetIntegrityQualificationValidationError(
                "fingerprint must be IntegrityQualifiedResearchRunFingerprint"
            )
        if len(self.run.datasets) != len(self.qualifications):
            raise DatasetIntegrityQualificationValidationError(
                "run datasets and qualifications must have identical cardinality"
            )
        seen_dataset_ids: set[object] = set()
        for index, (manifest, qualification) in enumerate(
            zip(self.run.datasets, self.qualifications, strict=True)
        ):
            if qualification.dataset.manifest != manifest:
                raise DatasetIntegrityQualificationValidationError(
                    f"qualification {index} manifest does not equal run dataset manifest"
                )
            dataset_id = qualification.dataset.manifest.dataset_id
            if dataset_id in seen_dataset_ids:
                raise DatasetIntegrityQualificationValidationError(
                    "dataset qualification identities must be unique"
                )
            seen_dataset_ids.add(dataset_id)
        expected = _compute_integrity_qualified_research_run_fingerprint(
            run=self.run,
            qualifications=self.qualifications,
        )
        if self.fingerprint != expected:
            raise DatasetIntegrityQualificationValidationError(
                "integrity-qualified research run fingerprint mismatch"
            )


def build_integrity_qualified_research_run(
    *,
    run: ResearchRunEvidence,
    qualifications: tuple[DatasetIntegrityQualification, ...],
) -> Result[IntegrityQualifiedResearchRun, DatasetIntegrityQualificationError]:
    """Bind exact run evidence to one qualification for each retained dataset."""

    try:
        if not isinstance(run, ResearchRunEvidence):
            raise DatasetIntegrityQualificationValidationError(
                "run must be ResearchRunEvidence"
            )
        if not isinstance(qualifications, tuple) or any(
            not isinstance(item, DatasetIntegrityQualification)
            for item in qualifications
        ):
            raise DatasetIntegrityQualificationValidationError(
                "qualifications must be an immutable DatasetIntegrityQualification tuple"
            )
        fingerprint = _compute_integrity_qualified_research_run_fingerprint(
            run=run,
            qualifications=qualifications,
        )
        return Success(
            IntegrityQualifiedResearchRun(
                run=run,
                qualifications=qualifications,
                fingerprint=fingerprint,
            )
        )
    except DatasetIntegrityQualificationError as error:
        return Failure(error)
