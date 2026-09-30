"""Adapter from V50 high-frequency cognition into the existing Master Cognitive Frame.

V50 does not replace the Capitalizer Master Brain. It enriches the candidate context consumed by
the already-governed master frame.

The adapter maps one V50 snapshot into CapitalizerCandidateCognitiveContext:
- freshness comes from H1 + M15/M1 freshness;
- destination availability comes from causal target ladder / geometry;
- failure-state fingerprint is the V50 state-family identity;
- provenance is explicit;
- observation tokens preserve V50 reasoning for audit.

The Master Frame remains responsible for regime, session journey, cross-market causality,
metacognition, adversarial reasoning and opportunity competition.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    V50GeometryProposal,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50ExecutionFreshness,
    V50H1Freshness,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    V50CognitiveOpportunitySnapshot,
)

IDENTITY = "QORE_CAPITALIZER_V50_MASTER_COGNITIVE_ADAPTER"


@dataclass(frozen=True, slots=True)
class V50MasterCognitiveAdapterResult:
    identity: str
    context: CapitalizerCandidateCognitiveContext
    geometry_decision: V50GeometryDecision
    master_frame_required: bool = True
    source_strategy_bypassed: bool = False
    outcome_visible: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50 Master Cognitive adapter identity")
        if not self.master_frame_required:
            raise ValueError("V50 cannot bypass Master Cognitive Frame")
        if self.source_strategy_bypassed:
            raise ValueError("V50 cognition cannot bypass source strategy")
        if self.outcome_visible:
            raise ValueError("V50 Master adapter cannot see future outcome")
        if self.grants_entry_authority or self.grants_capital_authority:
            raise ValueError("V50 Master adapter is advisory only")


def adapt_v50_to_master_context(
    snapshot: V50CognitiveOpportunitySnapshot,
    geometry: V50GeometryProposal,
) -> V50MasterCognitiveAdapterResult:
    """Create the candidate context consumed by the existing Master Cognitive Frame."""

    state = snapshot.cognitive.state
    event_is_fresh = (
        state.h1_freshness is not V50H1Freshness.STALE
        and state.execution_freshness is not V50ExecutionFreshness.LATE
    )
    destination_context_known = bool(snapshot.target_ladder.candidates)
    destination_available = (
        geometry.decision is V50GeometryDecision.READY
        and geometry.t1 is not None
    )
    genuinely_new = any(
        token == "NEW_CAUSAL_EVENT=YES"
        for token in state.observation_tokens
    )

    tokens = (
        *state.observation_tokens,
        f"V50_GEOMETRY={geometry.decision.value}",
        f"V50_TARGET_COUNT={len(snapshot.target_ladder.candidates)}",
        f"V50_EXEC_STOP_AVAILABLE={snapshot.dual_invalidation.execution_anchor_available}",
        "V50_MASTER_FRAME_REQUIRED=YES",
    )
    context = CapitalizerCandidateCognitiveContext(
        symbol=snapshot.symbol,
        observed_at=snapshot.observed_at,
        failure_state_fingerprint=state.state_family_id,
        evidence_provenance_complete=True,
        destination_context_known=destination_context_known,
        destination_available=destination_available,
        event_is_fresh=event_is_fresh,
        genuinely_new_causal_event=genuinely_new,
        observation_tokens=tokens,
    )
    return V50MasterCognitiveAdapterResult(
        identity=IDENTITY,
        context=context,
        geometry_decision=geometry.decision,
    )
