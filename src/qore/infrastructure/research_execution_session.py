from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetManifest,
    HistoricalOhlcReplayDataset,
)
from qore.infrastructure.replay_availability import ReplayMarketDataObservation
from qore.infrastructure.replay_clock import replay_observation_order_key
from qore.infrastructure.research_lineage_canonical import (
    _cjson,
    _sha256,
    canonical_dataset_manifest,
    canonical_replay_observation,
    canonical_research_run_strategy_binding,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchExecutionSessionValidationError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchExecutionSessionFingerprint,
)
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding


@dataclass(frozen=True, slots=True)
class QualifiedReplayObservation:
    """One exact replay observation bound to its retained dataset provenance."""

    source_manifest: HistoricalDatasetManifest
    observation: ReplayMarketDataObservation

    def __post_init__(self) -> None:
        if not isinstance(self.source_manifest, HistoricalDatasetManifest):
            raise ResearchLineageValidationError(
                "source_manifest must be HistoricalDatasetManifest"
            )
        if not isinstance(self.observation, ReplayMarketDataObservation):
            raise ResearchLineageValidationError(
                "observation must be ReplayMarketDataObservation"
            )

    @property
    def qualified_id(self) -> tuple[str, str]:
        return (
            str(self.source_manifest.dataset_id.value),
            str(self.observation.observation_id.value),
        )

    def canonical_projection(self) -> dict[str, object]:
        return {
            "source_dataset_id": str(self.source_manifest.dataset_id.value),
            "source_revision_id": str(self.source_manifest.revision_id.value),
            "source_evidence_digest": self.source_manifest.evidence_digest.value,
            "observation": canonical_replay_observation(self.observation),
        }


def _qualified_sort_key(
    qualified: QualifiedReplayObservation,
) -> tuple[object, ...]:
    if not isinstance(qualified, QualifiedReplayObservation):
        raise ResearchLineageValidationError(
            "qualified replay ordering requires QualifiedReplayObservation"
        )
    return (
        *replay_observation_order_key(qualified.observation),
        str(qualified.source_manifest.dataset_id.value),
    )


def order_qualified_replay_observations(
    observations: tuple[QualifiedReplayObservation, ...],
) -> tuple[QualifiedReplayObservation, ...]:
    if not isinstance(observations, tuple) or any(
        not isinstance(item, QualifiedReplayObservation)
        for item in observations
    ):
        raise ResearchLineageValidationError(
            "qualified observations must be an immutable QualifiedReplayObservation tuple"
        )
    return tuple(sorted(observations, key=_qualified_sort_key))


def _bijection_sort_key(
    manifest: HistoricalDatasetManifest,
) -> tuple[str, str]:
    if not isinstance(manifest, HistoricalDatasetManifest):
        raise ResearchExecutionSessionValidationError(
            "dataset bijection manifest has wrong type"
        )
    return (
        str(manifest.dataset_id.value),
        str(manifest.revision_id.value),
    )


def _validate_dataset_bijection(
    strategy_binding: ResearchRunStrategyBinding,
    replay_datasets: tuple[HistoricalOhlcReplayDataset, ...],
) -> tuple[HistoricalOhlcReplayDataset, ...]:
    if not isinstance(strategy_binding, ResearchRunStrategyBinding):
        raise ResearchExecutionSessionValidationError(
            "strategy_binding must be ResearchRunStrategyBinding"
        )
    if not isinstance(replay_datasets, tuple) or any(
        not isinstance(item, HistoricalOhlcReplayDataset)
        for item in replay_datasets
    ):
        raise ResearchExecutionSessionValidationError(
            "replay_datasets must be an immutable HistoricalOhlcReplayDataset tuple"
        )
    run_manifests = strategy_binding.run.datasets
    if len(replay_datasets) != len(run_manifests):
        raise ResearchExecutionSessionValidationError(
            "replay dataset count must equal retained run manifest count"
        )
    canonical_run = tuple(sorted(run_manifests, key=_bijection_sort_key))
    canonical_datasets = tuple(
        sorted(
            replay_datasets,
            key=lambda dataset: _bijection_sort_key(dataset.manifest),
        )
    )
    seen: set[tuple[str, str]] = set()
    for run_manifest, dataset in zip(
        canonical_run,
        canonical_datasets,
        strict=True,
    ):
        key = _bijection_sort_key(dataset.manifest)
        if key in seen:
            raise ResearchExecutionSessionValidationError(
                f"duplicate dataset manifest identity: {key!r}"
            )
        seen.add(key)
        if dataset.manifest != run_manifest:
            raise ResearchExecutionSessionValidationError(
                "replay dataset manifest does not exactly equal retained run manifest"
            )
    return canonical_datasets


@dataclass(frozen=True, slots=True)
class ResearchExecutionSession:
    strategy_binding: ResearchRunStrategyBinding
    replay_datasets: tuple[HistoricalOhlcReplayDataset, ...]
    qualified_observations: tuple[QualifiedReplayObservation, ...] = field(
        init=False
    )
    session_fingerprint: ResearchExecutionSessionFingerprint = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_binding, ResearchRunStrategyBinding):
            raise ResearchExecutionSessionValidationError(
                "strategy_binding must be ResearchRunStrategyBinding"
            )
        if not isinstance(self.replay_datasets, tuple):
            raise ResearchExecutionSessionValidationError(
                "replay_datasets must be tuple"
            )
        if any(
            not isinstance(dataset, HistoricalOhlcReplayDataset)
            for dataset in self.replay_datasets
        ):
            raise ResearchExecutionSessionValidationError(
                "every replay_datasets item must be HistoricalOhlcReplayDataset"
            )
        canonical_datasets = _validate_dataset_bijection(
            self.strategy_binding,
            self.replay_datasets,
        )
        object.__setattr__(self, "replay_datasets", canonical_datasets)
        qualified = tuple(
            QualifiedReplayObservation(
                source_manifest=dataset.manifest,
                observation=observation,
            )
            for dataset in canonical_datasets
            for observation in dataset.observations
        )
        object.__setattr__(self, "qualified_observations", qualified)
        object.__setattr__(
            self,
            "session_fingerprint",
            _compute_session_fingerprint(self),
        )


def derive_schedule_a_instants(
    session: ResearchExecutionSession,
) -> tuple[datetime, ...]:
    if not isinstance(session, ResearchExecutionSession):
        raise ResearchExecutionSessionValidationError(
            "schedule derivation requires ResearchExecutionSession"
        )
    run = session.strategy_binding.run
    instants = {
        qualified.observation.available_at
        for qualified in session.qualified_observations
        if (
            run.simulated_start
            <= qualified.observation.available_at
            < run.simulated_end
        )
    }
    return tuple(sorted(instants))


def _compute_session_fingerprint(
    session: ResearchExecutionSession,
) -> ResearchExecutionSessionFingerprint:
    if not isinstance(session, ResearchExecutionSession):
        raise ResearchExecutionSessionValidationError(
            "session fingerprint requires ResearchExecutionSession"
        )
    return ResearchExecutionSessionFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-execution-session.v1",
                    "strategy_binding": (
                        canonical_research_run_strategy_binding(
                            session.strategy_binding
                        )
                    ),
                    "datasets": [
                        canonical_dataset_manifest(dataset.manifest)
                        for dataset in session.replay_datasets
                    ],
                }
            )
        )
    )
