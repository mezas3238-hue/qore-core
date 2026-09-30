"""MC-12 QORE Market Foundation Model evidence contract.

The ceiling standard does not require an LLM. It requires a QORE-owned
financial-sequence representation layer whose learned representations survive
causal/OOS governance. This contract records exactly which objectives,
modalities and market families are proven and which remain absent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class FoundationLearningObjective(StrEnum):
    NEXT_STATE_PREDICTION = "NEXT_STATE_PREDICTION"
    CROSS_MARKET_REPRESENTATION = "CROSS_MARKET_REPRESENTATION"
    MASKED_RECONSTRUCTION = "MASKED_RECONSTRUCTION"
    CONTRASTIVE_STATE_LEARNING = "CONTRASTIVE_STATE_LEARNING"
    ANOMALY_DISCOVERY = "ANOMALY_DISCOVERY"


class FoundationModality(StrEnum):
    M1_OHLC_DERIVED_SEQUENCE = "M1_OHLC_DERIVED_SEQUENCE"
    BID_ASK = "BID_ASK"
    TICKS = "TICKS"
    SPREAD = "SPREAD"
    ORDER_FLOW = "ORDER_FLOW"
    MARKET_DEPTH = "MARKET_DEPTH"
    VOLATILITY = "VOLATILITY"
    EVENTS = "EVENTS"
    TRAJECTORIES = "TRAJECTORIES"


@dataclass(frozen=True, slots=True)
class MarketFoundationEvidence:
    representation_fingerprint: str
    concept_count: int
    probe_count: int
    horizon_minutes: int
    markets: tuple[str, ...]
    market_families: tuple[str, ...]
    objectives_proven: tuple[FoundationLearningObjective, ...]
    modalities_proven: tuple[FoundationModality, ...]
    fresh_holdout_incremental_bps: int
    fresh_holdout_positive_targets: int
    temporal_replication_incremental_bps: int
    temporal_replication_positive_targets: int
    identity_shortcut_used: bool = False
    runtime_future_market_used: bool = False
    representation_refit_on_holdout: bool = False
    representation_refit_on_replication: bool = False
    global_multi_family_world_bound: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.representation_fingerprint) != 64:
            raise ValueError("representation fingerprint must be sha256")
        int(self.representation_fingerprint, 16)
        if self.concept_count < 1 or self.probe_count < 1:
            raise ValueError("foundation evidence requires concepts and probes")
        if self.horizon_minutes < 1:
            raise ValueError("foundation horizon must be positive")
        if self.markets != tuple(sorted(set(self.markets))):
            raise ValueError("foundation markets must be canonical")
        if self.market_families != tuple(sorted(set(self.market_families))):
            raise ValueError("foundation market families must be canonical")
        if self.objectives_proven != tuple(
            sorted(set(self.objectives_proven), key=lambda item: item.value)
        ):
            raise ValueError("foundation objectives must be canonical")
        if self.modalities_proven != tuple(
            sorted(set(self.modalities_proven), key=lambda item: item.value)
        ):
            raise ValueError("foundation modalities must be canonical")
        for value in (
            self.fresh_holdout_incremental_bps,
            self.temporal_replication_incremental_bps,
        ):
            if value < -10_000 or value > 10_000:
                raise ValueError("incremental information bps out of range")
        for value in (
            self.fresh_holdout_positive_targets,
            self.temporal_replication_positive_targets,
        ):
            if value < 0:
                raise ValueError("positive target count cannot be negative")
        if (
            self.identity_shortcut_used
            or self.runtime_future_market_used
            or self.representation_refit_on_holdout
            or self.representation_refit_on_replication
            or self.productive_authority
        ):
            raise ValueError("foundation evidence violates research governance")

    @property
    def sequence_representation_scientifically_proven(self) -> bool:
        required = {
            FoundationLearningObjective.NEXT_STATE_PREDICTION,
            FoundationLearningObjective.CROSS_MARKET_REPRESENTATION,
        }
        return (
            required.issubset(set(self.objectives_proven))
            and self.fresh_holdout_incremental_bps > 0
            and self.temporal_replication_incremental_bps > 0
            and self.fresh_holdout_positive_targets > 0
            and self.temporal_replication_positive_targets > 0
        )

    @property
    def ceiling_complete(self) -> bool:
        return (
            self.sequence_representation_scientifically_proven
            and self.global_multi_family_world_bound
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["objectives_proven"] = tuple(
            item.value for item in self.objectives_proven
        )
        payload["modalities_proven"] = tuple(
            item.value for item in self.modalities_proven
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
