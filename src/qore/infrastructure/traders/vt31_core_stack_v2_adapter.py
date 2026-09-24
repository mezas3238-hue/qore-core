"""VT31-specific adapter and shadow A/B bridge for QORE CORE STACK V2.

This module is deliberately specialist-owned. Shared Core never imports VT31
methodology. The bridge translates already-known VT31 causal situation facts
into the shared factual contract, then feeds the resulting context back beside
the unchanged certified VT31 reasoning path.

SHADOW semantics:
- baseline/current VT31 remains untouched;
- valid Core V2 context cannot skip or rewrite VT31 methodology;
- invalid Core V2 context fails the V2 shadow lane closed;
- no order, Risk, deployment, or capital authority exists here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter_ns

from qore.infrastructure.core_stack_v2 import (
    CoreSnapshot,
    MarketEvent,
    TraderCognitiveContext,
    build_shared_context,
    build_snapshot,
    freeze_facts,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    Nas100ReasoningDecision,
    reason,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)


VT31_ADAPTER_VERSION = "1.0.0-research"


@dataclass(frozen=True, slots=True)
class VT31CoreAdapter:
    trader_id: str = "VT31_NAS100"
    adapter_version: str = VT31_ADAPTER_VERSION

    def adapt(self, snapshot: CoreSnapshot) -> TraderCognitiveContext:
        return build_shared_context(
            trader_id=self.trader_id,
            adapter_version=self.adapter_version,
            snapshot=snapshot,
            market_allowed=snapshot.market == "NAS100",
        )


@dataclass(frozen=True, slots=True)
class VT31ShadowABObservation:
    snapshot: CoreSnapshot
    context: TraderCognitiveContext
    baseline_decision: Nas100ReasoningDecision
    v2_shadow_action: str
    methodology_preserved: bool
    core_latency_us: int
    adapter_latency_us: int
    reasoning_latency_us: int

    def __post_init__(self) -> None:
        for value in (
            self.core_latency_us,
            self.adapter_latency_us,
            self.reasoning_latency_us,
        ):
            if value < 0:
                raise ValueError("latency cannot be negative")


def _as_of(situation: Nas100SituationModel) -> datetime:
    value = datetime.fromisoformat(situation.as_of)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("VT31 situation as_of must be timezone-aware")
    return value


def _world_facts(situation: Nas100SituationModel) -> dict[str, str]:
    volatility = situation.volatility_state.upper()
    return {
        "market_state": "VT31_CAUSAL_SITUATION_AVAILABLE",
        "session_state": situation.session,
        "liquidity_state": situation.last_structure_event_family,
        "structure_state": situation.confirmation_state,
        "volatility_state": volatility,
        "expansion_state": (
            "EXPANSION" if volatility == "EXPANDED" else "NOT_EXPANDED"
        ),
        "compression_state": (
            "COMPRESSION" if volatility == "COMPRESSED" else "NOT_COMPRESSED"
        ),
        "directional_state": situation.h1_state,
        "reversal_state": situation.reversal_state
        if hasattr(situation, "reversal_state")
        else "SPECIALIST_UNRESOLVED",
        "continuation_state": "SPECIALIST_UNRESOLVED",
        "liquidity_target_state": situation.dol1_state,
        "opposite_displacement_state": "UNKNOWN",
    }


def vt31_event_from_situation(
    situation: Nas100SituationModel,
    *,
    sequence: int = 0,
) -> MarketEvent:
    """Translate only already-observable VT31 facts into one shared event."""
    as_of = _as_of(situation)
    return MarketEvent(
        event_id=f"VT31_SITUATION:{situation.fingerprint()}",
        market="NAS100",
        event_type="SPECIALIST_SITUATION",
        source_at=as_of,
        observed_at=as_of,
        sequence=sequence,
        complete=True,
        timeframe_seconds=None,
        facts=freeze_facts(_world_facts(situation)),
    )


def build_vt31_shadow_snapshot(
    situation: Nas100SituationModel,
    *,
    generated_at: datetime,
) -> CoreSnapshot:
    """Build a shared snapshot without adding any VT31 strategy authority."""
    return build_snapshot(
        events=(vt31_event_from_situation(situation),),
        generated_at=generated_at,
        cross_market_facts={
            "VT31_CROSS_INDEX_CONTEXT": situation.cross_index_state,
        },
    )


def observe_vt31_shadow_ab(
    situation: Nas100SituationModel,
    *,
    generated_at: datetime,
) -> VT31ShadowABObservation:
    """Compare unchanged VT31 reasoning with Core V2 shadow availability."""
    baseline_started = perf_counter_ns()
    baseline = reason(situation)
    reasoning_latency_us = max(0, (perf_counter_ns() - baseline_started) // 1_000)

    core_started = perf_counter_ns()
    snapshot = build_vt31_shadow_snapshot(
        situation,
        generated_at=generated_at,
    )
    core_latency_us = max(0, (perf_counter_ns() - core_started) // 1_000)

    adapter_started = perf_counter_ns()
    context = VT31CoreAdapter().adapt(snapshot)
    adapter_latency_us = max(0, (perf_counter_ns() - adapter_started) // 1_000)

    # The first A/B is a preservation gate, not a new VT31 policy experiment.
    # Valid shared context leaves the certified specialist decision unchanged.
    # Invalid shared context fails the V2 shadow lane closed without changing
    # the current/live baseline path.
    v2_action = baseline.action if context.core_context_valid else "ABSTAIN"
    methodology_preserved = (
        not context.methodology_mutation_allowed
        and not context.order_authority
        and not context.risk_authority
        and baseline.situation_fingerprint == situation.fingerprint()
    )

    return VT31ShadowABObservation(
        snapshot=snapshot,
        context=context,
        baseline_decision=baseline,
        v2_shadow_action=v2_action,
        methodology_preserved=methodology_preserved,
        core_latency_us=core_latency_us,
        adapter_latency_us=adapter_latency_us,
        reasoning_latency_us=reasoning_latency_us,
    )
