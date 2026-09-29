"""Instrument-level global market relational graph for Shared cognition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class GlobalRelationKind(StrEnum):
    CORRELATION = "CORRELATION"
    CONDITIONAL_CORRELATION = "CONDITIONAL_CORRELATION"
    ROLLING_CORRELATION = "ROLLING_CORRELATION"
    NONLINEAR_DEPENDENCE = "NONLINEAR_DEPENDENCE"
    LEAD_LAG = "LEAD_LAG"
    INFORMATION_FLOW = "INFORMATION_FLOW"
    CONVERGENCE = "CONVERGENCE"
    DIVERGENCE = "DIVERGENCE"
    CROSS_MARKET_STRUCTURAL_DIVERGENCE = "CROSS_MARKET_STRUCTURAL_DIVERGENCE"
    RELATIVE_STRENGTH = "RELATIVE_STRENGTH"
    VOLATILITY_COUPLING = "VOLATILITY_COUPLING"
    LIQUIDITY_COUPLING = "LIQUIDITY_COUPLING"
    MOMENTUM_COUPLING = "MOMENTUM_COUPLING"
    REGIME_DEPENDENCE = "REGIME_DEPENDENCE"
    CAUSAL_INFLUENCE = "CAUSAL_INFLUENCE"
    TEMPORAL_PRECEDENCE = "TEMPORAL_PRECEDENCE"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"
    RELATIONSHIP_STABILITY = "RELATIONSHIP_STABILITY"
    RELATIONSHIP_DECAY = "RELATIONSHIP_DECAY"
    RELATIONSHIP_RECOVERY = "RELATIONSHIP_RECOVERY"
    CROSS_ASSET_CONTAGION = "CROSS_ASSET_CONTAGION"
    SYSTEMIC_STRESS = "SYSTEMIC_STRESS"


class GlobalRelationState(StrEnum):
    CONVERGING = "CONVERGING"
    DIVERGING = "DIVERGING"
    DECOUPLING = "DECOUPLING"
    RECOUPLING = "RECOUPLING"
    LEADER_CHANGE = "LEADER_CHANGE"
    ANOMALOUS_RELATION = "ANOMALOUS_RELATION"
    SYSTEMIC_CONSENSUS = "SYSTEMIC_CONSENSUS"
    SYSTEMIC_DISAGREEMENT = "SYSTEMIC_DISAGREEMENT"
    STABLE = "STABLE"
    DECAYING = "DECAYING"
    BROKEN = "BROKEN"
    UNKNOWN = "UNKNOWN"


class GlobalRelationHorizon(StrEnum):
    TICK = "TICK"
    SUB_SECOND = "SUB_SECOND"
    SECONDS = "SECONDS"
    M1 = "M1"
    M3 = "M3"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    DAILY = "DAILY"
    SESSION = "SESSION"
    MULTI_DAY = "MULTI_DAY"
    WEEKLY = "WEEKLY"
    MACRO = "MACRO"


class RelationEpistemicGrade(StrEnum):
    OBSERVED = "OBSERVED"
    ASSOCIATION = "ASSOCIATION"
    TEMPORAL_DEPENDENCY = "TEMPORAL_DEPENDENCY"
    CAUSAL_CANDIDATE = "CAUSAL_CANDIDATE"
    FALSIFICATION_SURVIVED = "FALSIFICATION_SURVIVED"
    REPLICATED = "REPLICATED"
    TRANSPORTABLE = "TRANSPORTABLE"
    CERTIFIED = "CERTIFIED"


class RelationDirection(StrEnum):
    BIDIRECTIONAL = "BIDIRECTIONAL"
    SOURCE_TO_TARGET = "SOURCE_TO_TARGET"
    TARGET_TO_SOURCE = "TARGET_TO_SOURCE"
    UNRESOLVED = "UNRESOLVED"


_DIVERGENCE_STATES = {
    GlobalRelationState.DIVERGING,
    GlobalRelationState.DECOUPLING,
    GlobalRelationState.LEADER_CHANGE,
    GlobalRelationState.ANOMALOUS_RELATION,
    GlobalRelationState.SYSTEMIC_DISAGREEMENT,
    GlobalRelationState.BROKEN,
}


@dataclass(frozen=True, slots=True)
class GlobalMarketNode:
    instrument_key: str
    family: str
    observation_status: str
    data_quality_bps: int
    uncertainty_bps: int
    freshness_ms: int | None
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instrument_key.strip() or not self.family.strip():
            raise ValueError("market node identity must be explicit")
        if not self.observation_status.strip():
            raise ValueError("observation_status must be explicit")
        for name in ("data_quality_bps", "uncertainty_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.freshness_ms is not None and self.freshness_ms < 0:
            raise ValueError("freshness_ms cannot be negative")
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise ValueError("node provenance must be unique and canonical")


@dataclass(frozen=True, slots=True)
class GlobalMarketRelationEdge:
    relation_id: str
    source_instrument_key: str
    target_instrument_key: str
    relation_kind: GlobalRelationKind
    relation_state: GlobalRelationState
    horizon: GlobalRelationHorizon
    direction: RelationDirection
    epistemic_grade: RelationEpistemicGrade
    as_of: datetime
    evidence_cutoff_at: datetime
    last_transition_at: datetime
    strength_bps: int
    confidence_bps: int
    uncertainty_bps: int
    stability_bps: int
    persistence_bps: int
    historical_validity_bps: int
    current_validity_bps: int
    timestamp_alignment_bps: int
    market_hours_comparable: bool
    lag_ms: int | None
    regime_context: tuple[str, ...]
    multiple_testing_control: str
    sample_count: int
    provenance_refs: tuple[str, ...]
    outcome_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if not self.relation_id.strip():
            raise ValueError("relation_id must be non-empty")
        if (
            not self.source_instrument_key.strip()
            or not self.target_instrument_key.strip()
        ):
            raise ValueError("relation endpoints must be explicit")
        if self.source_instrument_key == self.target_instrument_key:
            raise ValueError("market relation cannot self-reference")
        for value in (self.as_of, self.evidence_cutoff_at, self.last_transition_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("relation timestamps must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future relation evidence is forbidden")
        if self.last_transition_at > self.as_of:
            raise ValueError("future relation transition is forbidden")
        for name in (
            "strength_bps",
            "confidence_bps",
            "uncertainty_bps",
            "stability_bps",
            "persistence_bps",
            "historical_validity_bps",
            "current_validity_bps",
            "timestamp_alignment_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if type(self.market_hours_comparable) is not bool:
            raise ValueError("market_hours_comparable must be bool")
        if self.relation_state in _DIVERGENCE_STATES:
            if not self.market_hours_comparable:
                raise ValueError(
                    "divergence/break claims require comparable market hours"
                )
        if self.lag_ms is not None and self.lag_ms < 0:
            raise ValueError("lag_ms cannot be negative")
        if self.sample_count < 0:
            raise ValueError("sample_count cannot be negative")
        if not self.multiple_testing_control.strip():
            raise ValueError("multiple_testing_control must be explicit")
        if self.regime_context != tuple(sorted(set(self.regime_context))):
            raise ValueError("regime_context must be unique and canonical")
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise ValueError("edge provenance must be unique and canonical")
        if (
            self.outcome_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError("global market relation cannot carry forbidden authority")


@dataclass(frozen=True, slots=True)
class QoreGlobalMarketRelationalGraph:
    as_of: datetime
    nodes: tuple[GlobalMarketNode, ...]
    edges: tuple[GlobalMarketRelationEdge, ...]
    current_trader_universe_defines_graph_ceiling: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("graph as_of must be timezone-aware")
        node_keys = tuple(item.instrument_key for item in self.nodes)
        if node_keys != tuple(sorted(node_keys)) or len(node_keys) != len(set(node_keys)):
            raise ValueError("graph nodes must be unique and canonical")
        relation_ids = tuple(item.relation_id for item in self.edges)
        if relation_ids != tuple(sorted(relation_ids)) or len(relation_ids) != len(
            set(relation_ids)
        ):
            raise ValueError("graph relation ids must be unique and canonical")
        known = set(node_keys)
        for edge in self.edges:
            if edge.source_instrument_key not in known:
                raise ValueError("relation source is not a retained graph node")
            if edge.target_instrument_key not in known:
                raise ValueError("relation target is not a retained graph node")
            if edge.as_of > self.as_of:
                raise ValueError("future graph edge is forbidden")
        if (
            self.current_trader_universe_defines_graph_ceiling
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("global relational graph is cognition-only")

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def fingerprint(self) -> str:
        payload = {
            "as_of": self.as_of.astimezone(UTC).isoformat(),
            "nodes": [asdict(item) for item in self.nodes],
            "edges": [
                {
                    **asdict(item),
                    "relation_kind": item.relation_kind.value,
                    "relation_state": item.relation_state.value,
                    "horizon": item.horizon.value,
                    "direction": item.direction.value,
                    "epistemic_grade": item.epistemic_grade.value,
                    "as_of": item.as_of.astimezone(UTC).isoformat(),
                    "evidence_cutoff_at": item.evidence_cutoff_at.astimezone(
                        UTC
                    ).isoformat(),
                    "last_transition_at": item.last_transition_at.astimezone(
                        UTC
                    ).isoformat(),
                }
                for item in self.edges
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()
