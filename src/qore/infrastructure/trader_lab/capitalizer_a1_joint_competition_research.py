"""A1 simultaneous multi-hypothesis collision ledger, *not* execution arbitration.

The legacy nine-market Master Frame evaluates one hypothesis per market.
An A1 multi-M1 census preserves all hypotheses through independent as-of
projections. This module then restores *simultaneous* cross-candidate visibility
without secretly choosing or discarding a source opportunity. Any source-policy
ranking, order allocation and broker sizing remains outside this research layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from itertools import combinations

from qore.infrastructure.trader_lab.capitalizer_a1_multi_hypothesis_research import (
    A1MultiHypothesisBarrier,
    A1MultiHypothesisEvidence,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketRelation,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerFactorExposure,
    CapitalizerSide,
    factor_exposures,
)

IDENTITY = "QORE_SCALPER_A1_JOINT_CONSTRAINTS_RESEARCH_ONLY"


@dataclass(frozen=True, slots=True)
class A1ProspectiveSourceExposure:
    """Evidenced hypothetical side and risk; NOT authorized by QORE RISK."""

    source_opportunity_id: str
    symbol: str
    side: CapitalizerSide
    assumed_risk_r: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.source_opportunity_id:
            raise ValueError("exposure evidence requires source identity")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("exposure evidence must be timezone-aware")
        CapitalizerExposurePosition(
            symbol=self.symbol, side=self.side, risk_r=self.assumed_risk_r
        )


@dataclass(frozen=True, slots=True)
class A1JointPairEvidence:
    """Observed relation, not a score or decision to remove either candidate."""

    left_source_id: str
    right_source_id: str
    left_symbol: str
    right_symbol: str
    relation: str
    evidence_tokens: tuple[str, ...]
    requires_joint_review: bool
    missing_causal_relation: bool
    factor_overlap: tuple[str, ...]
    hypothetical_joint_exposure: tuple[CapitalizerFactorExposure, ...] | None
    selects_winner: bool = False

    def __post_init__(self) -> None:
        if self.left_source_id >= self.right_source_id or self.selects_winner:
            raise ValueError("joint pair identities must be ordered; no winner allowed")
        if not self.evidence_tokens:
            raise ValueError("joint pair requires explicit causal provenance or uncertainty")


@dataclass(frozen=True, slots=True)
class A1JointCandidateEvidence:
    source_opportunity_id: str
    symbol: str
    cognitive_gate: str
    all_pair_source_ids: tuple[str, ...]
    potential_collision_source_ids: tuple[str, ...]
    unknown_relation_source_ids: tuple[str, ...]
    missing_exposure_intent: bool
    why_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class A1JointCompetitionEvidence:
    identity: str
    decision_at: str
    candidate_rows: tuple[A1JointCandidateEvidence, ...]
    pair_rows: tuple[A1JointPairEvidence, ...]
    source_ids: tuple[str, ...]
    pass_source_ids: tuple[str, ...]
    remaining_session_slots: int
    capacity_competition_required: bool
    source_policy_arbitration_required: bool
    all_pass_candidates_accounted_for: bool
    provisional_projection_only: bool = True
    selected_source_ids: tuple[str, ...] = ()
    changes_source_eligibility: bool = False
    changes_economic_admission: bool = False
    grants_capital_authority: bool = False
    uses_future_outcomes: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("joint census identity mismatch")
        if self.source_ids != tuple(x.source_opportunity_id for x in self.candidate_rows):
            raise ValueError("joint census lost original source identities")
        if self.pass_source_ids != tuple(
            x.source_opportunity_id
            for x in self.candidate_rows
            if x.cognitive_gate == "PASS_TO_STRATEGY"
        ):
            raise ValueError("PASS candidate denominator is inconsistent")
        if not self.all_pass_candidates_accounted_for:
            raise ValueError("cannot certify incomplete simultaneous census")
        if self.capacity_competition_required != (
            len(self.pass_source_ids) > self.remaining_session_slots
        ):
            raise ValueError("capacity competition must count source IDs, not symbols")
        if (
            not self.provisional_projection_only
            or self.selected_source_ids
            or self.changes_source_eligibility
            or self.changes_economic_admission
            or self.grants_capital_authority
            or self.uses_future_outcomes
        ):
            raise ValueError("joint research must never select trades or grant capital")


def assess_joint_competition_barrier(
    *,
    barrier: A1MultiHypothesisBarrier,
    census: A1MultiHypothesisEvidence,
    exposure_intents: tuple[A1ProspectiveSourceExposure, ...] = (),
) -> A1JointCompetitionEvidence:
    """Build one simultaneous pairwise evidence map without introducing selection.

    No causal edge means UNKNOWN, not INDEPENDENT; mere factor overlap is not a
    hard strategy rejection. Conflicts are observations for later approved
    source-author arbitration. An absent hypothetical side/risk is reported as
    missing instead of inventing a zero-risk or a broker lot.
    """
    at = barrier.observed_at
    if census.barriers_evaluated != 1 or len(census.competition_demand) != 1:
        raise ValueError("joint research needs exactly one synchronized barrier")
    if census.competition_demand[0].decision_at != at.isoformat():
        raise ValueError("joint assessment and census time barriers differ")
    source_map = {
        alt.binding.source_opportunity_id: alt for alt in barrier.alternatives
    }
    ids = tuple(sorted(source_map))
    if (
        len(source_map) != len(barrier.alternatives)
        or set(ids) != set(barrier.expected_source_ids)
        or set(ids) != set(census.source_ids)
        or census.evaluated_alternatives != len(ids)
    ):
        raise ValueError("joint evidence missing or duplicating source candidates")
    if any(alt.binding.confirmed_at != at for alt in barrier.alternatives):
        raise ValueError("joint source candidate crosses time frontier")
    if barrier.cross_market_graph.observed_at > at:
        raise ValueError("future causal graph cannot enter joint competition")
    if (
        census.competition_demand[0].available_session_slots
        != barrier.world.execution_slots_remaining
    ):
        raise ValueError("competition demand slots differ from immutable session ledger")

    decisions = {row.source_opportunity_id: row for row in census.decisions}
    if len(decisions) != len(ids):
        raise ValueError("joint cognitive decision identity collision")
    intents: dict[str, A1ProspectiveSourceExposure] = {}
    for intent in exposure_intents:
        if intent.source_opportunity_id in intents or intent.source_opportunity_id not in source_map:
            raise ValueError("duplicate or unrecognized source exposure intent")
        if (
            intent.symbol != source_map[intent.source_opportunity_id].binding.symbol
            or intent.observed_at > at
        ):
            raise ValueError("exposure intent symbol or time frontier mismatch")
        intents[intent.source_opportunity_id] = intent

    pass_ids = tuple(
        id_ for id_ in ids if decisions[id_].cognitive_gate == "PASS_TO_STRATEGY"
    )
    pairs: list[A1JointPairEvidence] = []
    conflicts: dict[str, list[str]] = {id_: [] for id_ in ids}
    unknowns: dict[str, list[str]] = {id_: [] for id_ in ids}
    peers: dict[str, list[str]] = {id_: [] for id_ in ids}

    for left_id, right_id in combinations(pass_ids, 2):
        a, b = source_map[left_id], source_map[right_id]
        left_symbol, right_symbol = a.binding.symbol, b.binding.symbol
        unknown = False
        if left_symbol == right_symbol:
            relation = "SAME_MARKET_OVERLAPPING_HYPOTHESES"
            tokens = ("SIMULTANEOUS_SAME_MARKET_SOURCE_CANDIDATES",)
            conflict = True
        else:
            edge = barrier.cross_market_graph.relation_for(
                left_symbol, right_symbol
            )
            if edge is None or edge.relation is CapitalizerCrossMarketRelation.UNKNOWN:
                relation = "CAUSAL_RELATION_UNKNOWN"
                tokens = ("NO_EVIDENCED_CAUSAL_RELATION",)
                unknown = True
                conflict = False
            else:
                relation = edge.relation.value
                tokens = edge.causal_tokens
                # A causal relation does not automatically veto either entry.
                conflict = edge.relation is not CapitalizerCrossMarketRelation.INDEPENDENT

        left_intent, right_intent = intents.get(left_id), intents.get(right_id)
        exposure: tuple[CapitalizerFactorExposure, ...] | None = None
        overlap: tuple[str, ...] = ()
        if left_intent is not None and right_intent is not None:
            left_pos = CapitalizerExposurePosition(
                symbol=left_symbol,
                side=left_intent.side,
                risk_r=left_intent.assumed_risk_r,
            )
            right_pos = CapitalizerExposurePosition(
                symbol=right_symbol,
                side=right_intent.side,
                risk_r=right_intent.assumed_risk_r,
            )
            first_factors = {row.factor for row in factor_exposures((left_pos,))}
            other_factors = {row.factor for row in factor_exposures((right_pos,))}
            overlap = tuple(sorted(first_factors & other_factors))
            exposure = factor_exposures(
                (
                    *(position.exposure_position for position in barrier.world.open_positions),
                    left_pos,
                    right_pos,
                )
            )

        pairs.append(
            A1JointPairEvidence(
                left_source_id=left_id,
                right_source_id=right_id,
                left_symbol=left_symbol,
                right_symbol=right_symbol,
                relation=relation,
                evidence_tokens=tokens,
                requires_joint_review=conflict or unknown or bool(overlap),
                missing_causal_relation=unknown,
                factor_overlap=overlap,
                hypothetical_joint_exposure=exposure,
            )
        )
        for id_, peer in ((left_id, right_id), (right_id, left_id)):
            peers[id_].append(peer)
            if conflict or overlap:
                conflicts[id_].append(peer)
            if unknown:
                unknowns[id_].append(peer)

    candidates = tuple(
        A1JointCandidateEvidence(
            source_opportunity_id=id_,
            symbol=source_map[id_].binding.symbol,
            cognitive_gate=decisions[id_].cognitive_gate,
            all_pair_source_ids=tuple(sorted(peers[id_])),
            potential_collision_source_ids=tuple(sorted(conflicts[id_])),
            unknown_relation_source_ids=tuple(sorted(unknowns[id_])),
            missing_exposure_intent=id_ not in intents,
            why_tokens=(
                *decisions[id_].why_tokens,
                "JOINT_REVIEW_PENDING_NOT_A_TRADE_SELECTION",
                *(f"JOINT_COLLISION:{peer}" for peer in sorted(conflicts[id_])),
                *(f"JOINT_CAUSAL_UNKNOWN:{peer}" for peer in sorted(unknowns[id_])),
                *(() if id_ in intents else ("PROSPECTIVE_EXPOSURE_UNAVAILABLE",)),
            ),
        )
        for id_ in ids
    )
    return A1JointCompetitionEvidence(
        identity=IDENTITY,
        decision_at=at.isoformat(),
        candidate_rows=candidates,
        pair_rows=tuple(pairs),
        source_ids=ids,
        pass_source_ids=pass_ids,
        remaining_session_slots=barrier.world.execution_slots_remaining,
        capacity_competition_required=(
            len(pass_ids) > barrier.world.execution_slots_remaining
        ),
        source_policy_arbitration_required=(
            len(pass_ids) > barrier.world.execution_slots_remaining
            or any(p.requires_joint_review for p in pairs)
            or any(id_ not in intents for id_ in pass_ids)
        ),
        all_pass_candidates_accounted_for=True,
    )
