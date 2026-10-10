"""Decision-time trace of the V50-G bridge; NEVER a Master Frame certification.

This is a research-only observation contract.  It captures one row for each V49
source opportunity *before* the economics simulator is called.  Missing cognitive
evidence is marked missing instead of silently being represented as GOOD.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
        V49Opportunity,
    )
    from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
        V50GeometryProposal,
    )
    from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
        V50CognitiveOpportunitySnapshot,
    )

TRACE_IDENTITY = "QORE_SCALPER_V50_G_CAUSAL_TRACE_V1"
BRIDGE_ONLY = "PARTIAL_V50_BRIDGE_ONLY"
STATIC_READINESS = "LEGACY_STATIC_WELL_SUPPORTED"
EMPTY_MEMORY = "PER_CANDIDATE_EMPTY_EXPERIENCE"


def _decision_time(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("cognitive trace requires timezone-aware source timestamps")
    return moment


def source_opportunity_id(opportunity: V49Opportunity) -> str:
    """Hash only source information already observed by M1 confirmation."""
    parts = (
        opportunity.symbol,
        opportunity.session,
        opportunity.operating_date,
        opportunity.h1_state_from,
        opportunity.h1_state_direction,
        opportunity.h1_state_basis,
        opportunity.m15_setup_confirmed_at,
        opportunity.m15_protected_swing_price,
        opportunity.m1_trigger_confirmed_at,
        opportunity.m1_trigger_family,
        opportunity.decision_reference_price,
        opportunity.structural_target_witness_price,
    )
    return hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class V50GCausalDecisionTrace:
    identity: str
    source_opportunity_id: str
    symbol: str
    session: str
    observed_at: str
    source_h1_from: str
    source_m15_confirmed_at: str
    source_m1_confirmed_at: str
    source_trigger_family: str
    state_family_id: str
    bridge_disposition: str
    bridge_reasons: tuple[str, ...]
    bridge_knowledge: str
    experience_observations: int
    geometry_decision: str
    geometry_reasons: tuple[str, ...]
    policy_geometry_only_eligible: bool
    policy_cognitive_geometry_eligible: bool
    cognition_coverage: str = BRIDGE_ONLY
    master_frame_evaluated: bool = False
    global_world_model_evaluated: bool = False
    nine_market_competition_evaluated: bool = False
    experience_memory_scope: str = EMPTY_MEMORY
    readiness_origin: str = STATIC_READINESS
    readiness_verified: bool = False
    outcome_visible_to_cognition: bool = False
    capital_authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.identity != TRACE_IDENTITY:
            raise ValueError("unexpected cognitive trace identity")
        if not self.source_opportunity_id or not self.state_family_id:
            raise ValueError("trace requires source/state identities")
        h1 = _decision_time(self.source_h1_from)
        m15 = _decision_time(self.source_m15_confirmed_at)
        m1 = _decision_time(self.source_m1_confirmed_at)
        observed = _decision_time(self.observed_at)
        if not (h1 <= m15 <= m1 == observed):
            raise ValueError("trace contains future or misordered cognitive inputs")
        if self.experience_observations < 0:
            raise ValueError("negative historical observations are invalid")
        if self.cognition_coverage != BRIDGE_ONLY:
            raise ValueError("V50-G cannot claim full cognition without independent wiring")
        if (
            self.master_frame_evaluated
            or self.global_world_model_evaluated
            or self.nine_market_competition_evaluated
            or self.readiness_verified
        ):
            raise ValueError("legacy V50-G did not verify complete Master Frame cognition")
        if self.experience_memory_scope != EMPTY_MEMORY:
            raise ValueError("legacy V50-G creates an empty memory per candidate")
        if self.readiness_origin != STATIC_READINESS:
            raise ValueError("legacy V50-G provides a static readiness constant")
        if self.experience_observations != 0:
            raise ValueError("empty V50-G experience memory cannot have observations")
        if self.outcome_visible_to_cognition or self.capital_authority_granted:
            raise ValueError("cognition must not read future outcomes or grant risk")


def trace_v50_g_bridge(
    opportunity: V49Opportunity,
    snapshot: V50CognitiveOpportunitySnapshot,
    geometry: V50GeometryProposal,
    *,
    cognitive_geometry_allowed: frozenset[str],
) -> V50GCausalDecisionTrace:
    """Trace a current baseline decision, without changing its admissibility."""
    confirmed = _decision_time(opportunity.m1_trigger_confirmed_at)
    if snapshot.symbol != opportunity.symbol or snapshot.observed_at != confirmed:
        raise ValueError("candidate snapshot must match source opportunity and time")
    if snapshot.cognitive.experience_observations != 0:
        raise ValueError("V50-G baseline cannot pretend to have persistent memory")
    return V50GCausalDecisionTrace(
        identity=TRACE_IDENTITY,
        source_opportunity_id=source_opportunity_id(opportunity),
        symbol=opportunity.symbol,
        session=opportunity.session,
        observed_at=confirmed.isoformat(),
        source_h1_from=opportunity.h1_state_from,
        source_m15_confirmed_at=opportunity.m15_setup_confirmed_at,
        source_m1_confirmed_at=opportunity.m1_trigger_confirmed_at,
        source_trigger_family=opportunity.m1_trigger_family,
        state_family_id=snapshot.cognitive.state.state_family_id,
        bridge_disposition=snapshot.cognitive.disposition.value,
        bridge_reasons=snapshot.cognitive.reasons,
        bridge_knowledge=snapshot.cognitive.knowledge.value,
        experience_observations=snapshot.cognitive.experience_observations,
        geometry_decision=geometry.decision.value,
        geometry_reasons=geometry.reasons,
        policy_geometry_only_eligible=geometry.decision.value == "READY",
        policy_cognitive_geometry_eligible=(
            geometry.decision.value == "READY"
            and snapshot.cognitive.disposition.value in cognitive_geometry_allowed
        ),
    )


def trace_json_line(trace: V50GCausalDecisionTrace) -> str:
    """Stable newline-delimited artifact with no terminal P&L or outcomes."""
    return json.dumps(asdict(trace), sort_keys=True, separators=(",", ":")) + "\n"
