from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from uuid import UUID

from qore.domain.commands import CommandMetadata
from qore.domain.events import CausationId, CorrelationId
from qore.functional.decisions import (
    DecisionMetadata,
    DecisionReason,
    FunctionalDecision,
)
from qore.infrastructure.historical_dataset import (
    HistoricalCoverageGap,
    HistoricalDatasetManifest,
    HistoricalOhlcDatasetScope,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.replay_availability import ReplayMarketDataObservation
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageCanonicalValueError,
)
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyConfigurationManifest,
    ResearchStrategyParameter,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistMetadata,
    SpecialistReason,
)


_STATE_CONTENT_SCHEMA = "qore.research-state-content-tagged.v1"


def _require_aware_dt(value: datetime, *, field_name: str = "datetime") -> datetime:
    if not isinstance(value, datetime):
        raise ResearchLineageCanonicalValueError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchLineageCanonicalValueError(
            f"{field_name} must be timezone-aware"
        )
    return value


def _utc_iso(value: datetime, *, field_name: str = "datetime") -> str:
    return _require_aware_dt(
        value,
        field_name=field_name,
    ).astimezone(UTC).isoformat(timespec="microseconds")


def _scalar(value: object) -> object:
    """Canonicalize values only where their type is already structurally known."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if type(value) is int:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ResearchLineageCanonicalValueError(
                f"non-finite float is not canonical: {value!r}"
            )
        return value.hex()
    if isinstance(value, str):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _utc_iso(value)
    if isinstance(value, Enum):
        return _scalar(value.value)
    if isinstance(value, tuple):
        return [_scalar(item) for item in value]
    if isinstance(value, list):
        return [_scalar(item) for item in value]
    if isinstance(value, Mapping):
        keys = tuple(value.keys())
        if any(not isinstance(key, str) for key in keys):
            raise ResearchLineageCanonicalValueError(
                "canonical Mapping keys must be strings"
            )
        return {
            key: _scalar(value[key])
            for key in sorted(keys)
        }
    raise ResearchLineageCanonicalValueError(
        f"unsupported canonical scalar type: {type(value).__name__!r}"
    )


def _tagged_metadata_value(value: object) -> dict[str, object]:
    """Type-preserving projection for DomainMetadataValue."""

    if value is None:
        return {"type": "none", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ResearchLineageCanonicalValueError(
                f"non-finite metadata float: {value!r}"
            )
        return {"type": "float", "value": value.hex()}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, UUID):
        return {"type": "uuid", "value": str(value)}
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "items": [_tagged_metadata_value(item) for item in value],
        }
    raise ResearchLineageCanonicalValueError(
        f"unsupported metadata value type: {type(value).__name__!r}"
    )


def _canonical_attrs(
    attrs: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    if not isinstance(attrs, Mapping):
        raise ResearchLineageCanonicalValueError(
            "attributes must be a Mapping"
        )
    keys = tuple(attrs.keys())
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ResearchLineageCanonicalValueError(
                "attribute keys must be non-empty strings"
            )
    return {
        key: _tagged_metadata_value(attrs[key])
        for key in sorted(keys)
    }


def _state_tagged(value: object) -> dict[str, object]:
    """Closed type-preserving algebra for producer-defined state evidence."""

    if value is None:
        return {"type": "none", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if type(value) is int:
        return {"type": "int", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ResearchLineageCanonicalValueError(
                f"non-finite state float: {value!r}"
            )
        return {"type": "float", "value": value.hex()}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, UUID):
        return {"type": "uuid", "value": str(value)}
    if isinstance(value, datetime):
        return {"type": "datetime", "value": _utc_iso(value)}
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "items": [_state_tagged(item) for item in value],
        }
    if isinstance(value, Mapping):
        keys = tuple(value.keys())
        if any(not isinstance(key, str) for key in keys):
            raise ResearchLineageCanonicalValueError(
                "state-content Mapping keys must be strings"
            )
        return {
            "type": "mapping",
            "items": {
                key: _state_tagged(value[key])
                for key in sorted(keys)
            },
        }
    raise ResearchLineageCanonicalValueError(
        f"unsupported state-content type: {type(value).__name__!r}"
    )


def _canonical_state_content(
    logical_values: Mapping[str, object],
) -> dict[str, object]:
    if not isinstance(logical_values, Mapping):
        raise ResearchLineageCanonicalValueError(
            "state logical_values() must return Mapping[str, object]"
        )
    keys = tuple(logical_values.keys())
    if any(not isinstance(key, str) for key in keys):
        raise ResearchLineageCanonicalValueError(
            "state logical_values() keys must be strings"
        )
    return {
        "schema": _STATE_CONTENT_SCHEMA,
        "content": {
            key: _state_tagged(logical_values[key])
            for key in sorted(keys)
        },
    }


def _cjson(value: Mapping[str, object]) -> bytes:
    normalized = _scalar(value)
    return json.dumps(
        normalized,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_external_source(
    source: ExternalSourceDescriptor,
) -> dict[str, object]:
    if not isinstance(source, ExternalSourceDescriptor):
        raise ResearchLineageCanonicalValueError(
            "source must be ExternalSourceDescriptor"
        )
    return {
        "adapter_id": str(source.adapter_id.value),
        "source_id": str(source.source_id.value),
        "port_name": source.port_name.value,
    }


def canonical_historical_window(
    window: HistoricalOhlcWindow,
) -> dict[str, object]:
    if not isinstance(window, HistoricalOhlcWindow):
        raise ResearchLineageCanonicalValueError(
            "window must be HistoricalOhlcWindow"
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


def canonical_dataset_scope(
    scope: HistoricalOhlcDatasetScope,
) -> dict[str, object]:
    if not isinstance(scope, HistoricalOhlcDatasetScope):
        raise ResearchLineageCanonicalValueError(
            "scope must be HistoricalOhlcDatasetScope"
        )
    return {
        "source": canonical_external_source(scope.source),
        "window": canonical_historical_window(scope.window),
    }


def canonical_coverage_gap(
    gap: HistoricalCoverageGap,
) -> dict[str, object]:
    if not isinstance(gap, HistoricalCoverageGap):
        raise ResearchLineageCanonicalValueError(
            "gap must be HistoricalCoverageGap"
        )
    return {
        "opened_at": _utc_iso(gap.opened_at, field_name="gap opened_at"),
        "closed_at": _utc_iso(gap.closed_at, field_name="gap closed_at"),
    }


def canonical_dataset_manifest(
    manifest: HistoricalDatasetManifest,
) -> dict[str, object]:
    if not isinstance(manifest, HistoricalDatasetManifest):
        raise ResearchLineageCanonicalValueError(
            "manifest must be HistoricalDatasetManifest"
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
        "scope": canonical_dataset_scope(manifest.scope),
        "assembled_at": _utc_iso(
            manifest.assembled_at,
            field_name="manifest assembled_at",
        ),
        "schema_version": manifest.schema_version.value,
        "normalization_version": manifest.normalization_version.value,
        "observation_count": manifest.observation_count,
        "actual_opened_at": _utc_iso(
            manifest.actual_opened_at,
            field_name="manifest actual_opened_at",
        ),
        "actual_closed_at": _utc_iso(
            manifest.actual_closed_at,
            field_name="manifest actual_closed_at",
        ),
        "gaps": [canonical_coverage_gap(gap) for gap in manifest.gaps],
        "digest_algorithm": manifest.digest_algorithm.value,
        "evidence_digest": manifest.evidence_digest.value,
    }


def canonical_research_run_evidence(
    run: ResearchRunEvidence,
) -> dict[str, object]:
    if not isinstance(run, ResearchRunEvidence):
        raise ResearchLineageCanonicalValueError(
            "run must be ResearchRunEvidence"
        )
    return {
        "run_id": str(run.run_id.value),
        "created_at": _utc_iso(
            run.created_at,
            field_name="run created_at",
        ),
        "datasets": [
            canonical_dataset_manifest(manifest)
            for manifest in run.datasets
        ],
        "replay_policy_version": run.replay_policy_version.value,
        "simulated_start": _utc_iso(
            run.simulated_start,
            field_name="run simulated_start",
        ),
        "simulated_end": _utc_iso(
            run.simulated_end,
            field_name="run simulated_end",
        ),
        "strategy_configuration_id": str(
            run.strategy_configuration_id.value
        ),
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


def _canonical_strategy_parameter(
    parameter: ResearchStrategyParameter,
) -> dict[str, object]:
    if not isinstance(parameter, ResearchStrategyParameter):
        raise ResearchLineageCanonicalValueError(
            "strategy parameter must be ResearchStrategyParameter"
        )
    canonical = parameter.canonical_value()
    if (
        not isinstance(canonical, dict)
        or set(canonical) != {"type", "value"}
    ):
        raise ResearchLineageCanonicalValueError(
            "strategy parameter canonical_value() contract mismatch"
        )
    return {"name": parameter.name, **canonical}


def canonical_strategy_configuration_manifest(
    manifest: ResearchStrategyConfigurationManifest,
) -> dict[str, object]:
    if not isinstance(manifest, ResearchStrategyConfigurationManifest):
        raise ResearchLineageCanonicalValueError(
            "strategy manifest must be ResearchStrategyConfigurationManifest"
        )
    return {
        "configuration_id": str(manifest.configuration_id.value),
        "schema_version": manifest.schema_version.value,
        "parameters": [
            _canonical_strategy_parameter(parameter)
            for parameter in manifest.parameters
        ],
        "content_digest": manifest.content_digest.value,
        "frozen_at": _utc_iso(
            manifest.frozen_at,
            field_name="strategy manifest frozen_at",
        ),
        "evidence_ref": str(manifest.evidence_ref.value),
    }


def canonical_research_run_strategy_binding(
    binding: ResearchRunStrategyBinding,
) -> dict[str, object]:
    if not isinstance(binding, ResearchRunStrategyBinding):
        raise ResearchLineageCanonicalValueError(
            "binding must be ResearchRunStrategyBinding"
        )
    return {
        "run": canonical_research_run_evidence(binding.run),
        "manifest": canonical_strategy_configuration_manifest(binding.manifest),
        "binding_fingerprint": binding.binding_fingerprint.value,
    }


def canonical_replay_observation(
    observation: ReplayMarketDataObservation,
) -> dict[str, object]:
    if not isinstance(observation, ReplayMarketDataObservation):
        raise ResearchLineageCanonicalValueError(
            "observation must be ReplayMarketDataObservation"
        )
    if not isinstance(observation.payload, OhlcSnapshot):
        raise ResearchLineageCanonicalValueError(
            "research lineage requires OhlcSnapshot replay payload"
        )
    snapshot = observation.payload
    return {
        "observation_id": str(observation.observation_id.value),
        "snapshot_id": str(snapshot.snapshot_id.value),
        "source": canonical_external_source(snapshot.source),
        "instrument": snapshot.instrument.symbol,
        "timeframe_seconds": snapshot.timeframe.seconds,
        "opened_at": _utc_iso(
            snapshot.opened_at,
            field_name="replay snapshot opened_at",
        ),
        "closed_at": _utc_iso(
            snapshot.closed_at,
            field_name="replay snapshot closed_at",
        ),
        "open": snapshot.open.hex(),
        "high": snapshot.high.hex(),
        "low": snapshot.low.hex(),
        "close": snapshot.close.hex(),
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


def canonical_decision_metadata(
    metadata: DecisionMetadata,
) -> dict[str, object]:
    if not isinstance(metadata, DecisionMetadata):
        raise ResearchLineageCanonicalValueError(
            "decision metadata must be DecisionMetadata"
        )
    if not isinstance(metadata.correlation_id, CorrelationId):
        raise ResearchLineageCanonicalValueError(
            "decision correlation_id must be CorrelationId"
        )
    if metadata.causation_id is not None and not isinstance(
        metadata.causation_id,
        CausationId,
    ):
        raise ResearchLineageCanonicalValueError(
            "decision causation_id must be CausationId or None"
        )
    return {
        "correlation_id": str(metadata.correlation_id.value),
        "causation_id": (
            str(metadata.causation_id.value)
            if metadata.causation_id is not None
            else None
        ),
        "attributes": _canonical_attrs(metadata.attributes),
    }


def canonical_decision_reason(
    reason: DecisionReason,
) -> dict[str, object]:
    if not isinstance(reason, DecisionReason):
        raise ResearchLineageCanonicalValueError(
            "decision reason must be DecisionReason"
        )
    return {
        "code": reason.code.value,
        "summary": reason.summary,
        "attributes": _canonical_attrs(reason.attributes),
    }


def canonical_functional_decision(
    decision: FunctionalDecision,
) -> dict[str, object]:
    if not isinstance(decision, FunctionalDecision):
        raise ResearchLineageCanonicalValueError(
            "decision must be FunctionalDecision"
        )
    if not isinstance(decision.decision_id.value, UUID):
        raise ResearchLineageCanonicalValueError(
            "decision_id.value must be UUID"
        )
    return {
        "decision_id": str(decision.decision_id.value),
        "timestamp": _utc_iso(
            decision.timestamp,
            field_name="decision timestamp",
        ),
        "decision_type": decision.decision_type.value,
        "status": decision.status.value,
        "priority": decision.priority.value,
        "metadata": canonical_decision_metadata(decision.metadata),
        "reasons": [
            canonical_decision_reason(reason)
            for reason in decision.reasons
        ],
        "outcome": (
            decision.outcome.value
            if decision.outcome is not None
            else None
        ),
    }


def canonical_specialist_metadata(
    metadata: SpecialistMetadata,
) -> dict[str, object]:
    if not isinstance(metadata, SpecialistMetadata):
        raise ResearchLineageCanonicalValueError(
            "specialist metadata must be SpecialistMetadata"
        )
    return {
        "correlation_id": str(metadata.correlation_id.value),
        "causation_id": (
            str(metadata.causation_id.value)
            if metadata.causation_id is not None
            else None
        ),
        "attributes": _canonical_attrs(metadata.attributes),
    }


def canonical_specialist_reason(
    reason: SpecialistReason,
) -> dict[str, object]:
    if not isinstance(reason, SpecialistReason):
        raise ResearchLineageCanonicalValueError(
            "specialist reason must be SpecialistReason"
        )
    return {
        "code": reason.code.value,
        "summary": reason.summary,
        "attributes": _canonical_attrs(reason.attributes),
    }


def canonical_specialist_analysis(
    analysis: SpecialistAnalysis,
) -> dict[str, object]:
    if not isinstance(analysis, SpecialistAnalysis):
        raise ResearchLineageCanonicalValueError(
            "analysis must be SpecialistAnalysis"
        )
    return {
        "analysis_id": str(analysis.analysis_id.value),
        "timestamp": _utc_iso(
            analysis.timestamp,
            field_name="specialist timestamp",
        ),
        "kind": analysis.kind.value,
        "status": analysis.status.value,
        "metadata": canonical_specialist_metadata(analysis.metadata),
        "confidence": (
            analysis.confidence.value.hex()
            if analysis.confidence is not None
            else None
        ),
        "reasons": [
            canonical_specialist_reason(reason)
            for reason in analysis.reasons
        ],
    }


def canonical_command_metadata(
    metadata: CommandMetadata,
) -> dict[str, object]:
    if not isinstance(metadata, CommandMetadata):
        raise ResearchLineageCanonicalValueError(
            "command metadata must be CommandMetadata"
        )
    if not isinstance(metadata.correlation_id, CorrelationId):
        raise ResearchLineageCanonicalValueError(
            "command correlation_id must be CorrelationId"
        )
    if metadata.causation_id is not None and not isinstance(
        metadata.causation_id,
        CausationId,
    ):
        raise ResearchLineageCanonicalValueError(
            "command causation_id must be CausationId or None"
        )
    return {
        "correlation_id": str(metadata.correlation_id.value),
        "causation_id": (
            str(metadata.causation_id.value)
            if metadata.causation_id is not None
            else None
        ),
        "idempotency_key": (
            metadata.idempotency_key.value
            if metadata.idempotency_key is not None
            else None
        ),
        "attributes": _canonical_attrs(metadata.attributes),
    }
