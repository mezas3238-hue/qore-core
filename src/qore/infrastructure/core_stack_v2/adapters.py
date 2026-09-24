"""Cognitive adapter boundary for QORE CORE STACK V2.

Adapters contextualize shared facts. They cannot rewrite strategy, authorize risk,
or authorize execution.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Protocol

from qore.infrastructure.core_stack_v2.contracts import CoreSnapshot


@dataclass(frozen=True, slots=True)
class TraderCognitiveContext:
    trader_id: str
    adapter_version: str
    snapshot_id: str
    market: str
    core_context_valid: bool
    invalid_reasons: tuple[str, ...]
    world_facts: tuple[tuple[str, str], ...]
    cross_market_facts: tuple[tuple[str, str], ...]
    attention_event_ids: tuple[str, ...]
    active_hypothesis_ids: tuple[str, ...]
    contradictions: tuple[str, ...]
    knowledge_state: str
    portfolio_warnings: tuple[str, ...]
    position_observations: tuple[tuple[str, str], ...]
    methodology_mutation_allowed: bool = False
    order_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.methodology_mutation_allowed
            or self.order_authority
            or self.risk_authority
        ):
            raise ValueError("adapter context cannot carry methodology/risk/order authority")

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode()).hexdigest()


class CoreAdapter(Protocol):
    trader_id: str
    adapter_version: str

    def adapt(self, snapshot: CoreSnapshot) -> TraderCognitiveContext: ...


def _shared_context(
    *,
    trader_id: str,
    adapter_version: str,
    snapshot: CoreSnapshot,
    market_allowed: bool,
) -> TraderCognitiveContext:
    valid = snapshot.perception_integrity.valid and market_allowed
    reasons = list(snapshot.perception_integrity.codes)
    if not market_allowed:
        reasons.append("ADAPTER_MARKET_MISMATCH")

    world = tuple(
        sorted(
            {
                "market_state": snapshot.world_state.market_state,
                "session_state": snapshot.world_state.session_state,
                "liquidity_state": snapshot.world_state.liquidity_state,
                "structure_state": snapshot.world_state.structure_state,
                "volatility_state": snapshot.world_state.volatility_state,
                "expansion_state": snapshot.world_state.expansion_state,
                "compression_state": snapshot.world_state.compression_state,
                "directional_state": snapshot.world_state.directional_state,
                "reversal_state": snapshot.world_state.reversal_state,
                "continuation_state": snapshot.world_state.continuation_state,
            }.items()
        )
    )
    position = tuple(
        sorted(
            {
                "expansion_state": snapshot.position_context.expansion_state,
                "contradiction_state": snapshot.position_context.contradiction_state,
                "liquidity_target_state": snapshot.position_context.liquidity_target_state,
                "opposite_displacement_state": (
                    snapshot.position_context.opposite_displacement_state
                ),
                "volatility_state": snapshot.position_context.volatility_state,
            }.items()
        )
    )
    warnings = tuple(
        sorted(
            {
                *snapshot.portfolio_state.duplicated_exposures,
                *snapshot.portfolio_state.factor_clusters,
            }
        )
    )
    return TraderCognitiveContext(
        trader_id=trader_id,
        adapter_version=adapter_version,
        snapshot_id=snapshot.snapshot_id,
        market=snapshot.market,
        core_context_valid=valid,
        invalid_reasons=tuple(sorted(set(reasons))),
        world_facts=world,
        cross_market_facts=snapshot.cross_market_state,
        attention_event_ids=snapshot.attention_events,
        active_hypothesis_ids=tuple(
            item.hypothesis_id for item in snapshot.active_hypotheses
        ),
        contradictions=snapshot.contradictions,
        knowledge_state=snapshot.uncertainty.knowledge_state.value,
        portfolio_warnings=warnings,
        position_observations=position,
    )


@dataclass(frozen=True, slots=True)
class VT31CoreAdapter:
    """Shadow adapter only; VT31 methodology remains the existing authority."""

    trader_id: str = "VT31_NAS100"
    adapter_version: str = "1.0.0-research"

    def adapt(self, snapshot: CoreSnapshot) -> TraderCognitiveContext:
        return _shared_context(
            trader_id=self.trader_id,
            adapter_version=self.adapter_version,
            snapshot=snapshot,
            market_allowed=snapshot.market == "NAS100",
        )
