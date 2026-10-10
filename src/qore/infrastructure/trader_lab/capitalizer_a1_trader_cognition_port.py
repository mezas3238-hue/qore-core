"""A1 research handoff contract: source M1 -> full cognition -> Trader review.

This port *actually invokes* the nine-market Master Cognitive Frame per
source-identifiable hypothesis, joins causal memory and simultaneous candidate
relations, and returns a complete keyed decision envelope to a future Trader.

It NEVER selects a trade, overrides source rules, allocates MAX3, grants QORE
Risk authority, constructs artificial data or executes broker operations.
It cannot replace a true global strategy arbitration or economic replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_a1_full_frame_research_adapter import (
    A1CausalSettledMemory,
    A1SettledChosenTrade,
)
from qore.infrastructure.trader_lab.capitalizer_a1_joint_competition_research import (
    A1JointCompetitionEvidence,
    A1ProspectiveSourceExposure,
    assess_joint_competition_barrier,
)
from qore.infrastructure.trader_lab.capitalizer_a1_multi_hypothesis_research import (
    A1MultiHypothesisBarrier,
    replay_multi_hypothesis_evidence,
)
from qore.infrastructure.trader_lab.capitalizer_memory import CapitalizerLossCause

IDENTITY = "QORE_SCALPER_A1_TRADER_COGNITION_PORT_RESEARCH_V1"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Trader cognitive port requires timezone-aware evidence")
    return value


@dataclass(frozen=True, slots=True)
class A1TraderCognitiveCandidate:
    """One ORIGINAL source opportunity and one real cognitive WHY."""

    source_opportunity_id: str
    symbol: str
    decision_at: datetime
    source_rule_id: str
    hypothesis_id: str
    source_event_id: str
    h1_confirmed_at: datetime
    m15_confirmed_at: datetime
    m1_confirmed_at: datetime
    cognitive_gate: str
    why_tokens: tuple[str, ...]
    uncertainty_tokens: tuple[str, ...]
    joint_review_peer_ids: tuple[str, ...]
    unknown_relation_peer_ids: tuple[str, ...]
    closed_chosen_history_count: int
    closed_chosen_failure_count: int
    trader_review_status: str
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.source_opportunity_id or not self.source_rule_id:
            raise ValueError("Trader port cannot omit source identity or author ledger rule")
        if not self.why_tokens:
            raise ValueError("Trader port cannot omit complete causal WHY")
        if not (
            _aware(self.h1_confirmed_at)
            <= _aware(self.m15_confirmed_at)
            <= _aware(self.m1_confirmed_at)
            == _aware(self.decision_at)
        ):
            raise ValueError("Trader port H1/M15/M1 frontier invalid")
        expected = {
            "PASS_TO_STRATEGY": "SOURCE_METHOD_ARBITRATION_REQUIRED",
            "WAIT": "COGNITIVE_WAIT_RESEARCH",
            "ABSTAIN": "COGNITIVE_ABSTAIN_RESEARCH",
        }
        if (
            self.cognitive_gate not in expected
            or self.trader_review_status != expected[self.cognitive_gate]
            or self.execution_authorized
        ):
            raise ValueError("a cognitive pass never implies a real trade authorization")


@dataclass(frozen=True, slots=True)
class A1TraderCognitionPacket:
    """Immutable, one-barrier, lossless pre-execution handoff to Trader."""

    identity: str
    observed_at: datetime
    candidates: tuple[A1TraderCognitiveCandidate, ...]
    joint: A1JointCompetitionEvidence
    source_opportunity_ids: tuple[str, ...]
    remaining_session_slots: int
    nine_market_frame_called_for_each_source: bool
    original_source_denominator_preserved: bool
    settlement_history_reconciled: bool
    global_arbitration_complete: bool = False
    physical_risk_checked: bool = False
    economic_trades_executed: bool = False
    live_integration_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected Trader cognition integration port identity")
        ids = tuple(row.source_opportunity_id for row in self.candidates)
        if (
            ids != self.source_opportunity_ids
            or ids != self.joint.source_ids
            or len(ids) != len(set(ids))
            or self.remaining_session_slots != self.joint.remaining_session_slots
        ):
            raise ValueError("Trader handoff drops or duplicates source opportunities")
        if any(row.decision_at != self.observed_at for row in self.candidates):
            raise ValueError("Trader packet mixes incompatible time barriers")
        if not (
            self.nine_market_frame_called_for_each_source
            and self.original_source_denominator_preserved
            and self.settlement_history_reconciled
        ):
            raise ValueError("Trader packet requires full cognitive provenance")
        if (
            self.global_arbitration_complete
            or self.physical_risk_checked
            or self.economic_trades_executed
            or self.live_integration_authorized
        ):
            raise ValueError("pre-execution research is not deployment certification")


@dataclass(frozen=True, slots=True)
class A1ExternallySettledExecution:
    """Caller-supplied execution receipt; NOT broker-authenticated by this port.

    Its chosen status and QORE Risk authorization must be verified externally.
    The port validates temporal/source continuity but cannot attest that IDs
    correspond to real broker fills. A negative settled R requires causal
    explanation before it may influence future decisions.
    """

    execution_id: str
    source_opportunity_id: str
    risk_authority_receipt_id: str
    execution_provenance_id: str
    entry_at: datetime
    exit_at: datetime
    settlement_known_at: datetime
    realized_r: Decimal
    loss_cause: CapitalizerLossCause | None

    def __post_init__(self) -> None:
        if not all((
            self.execution_id,
            self.source_opportunity_id,
            self.risk_authority_receipt_id,
            self.execution_provenance_id,
        )):
            raise ValueError("external settlement requires source/risk/execution provenance")
        if not (
            _aware(self.entry_at)
            <= _aware(self.exit_at)
            <= _aware(self.settlement_known_at)
        ):
            raise ValueError("settlement receipt time order invalid")
        if not isinstance(self.realized_r, Decimal) or not self.realized_r.is_finite():
            raise ValueError("external realized R must be finite Decimal")
        if (self.realized_r < 0) != (self.loss_cause is not None):
            raise ValueError("negative settled R needs causal loss; nonloss cannot teach loss")
        if self.loss_cause is not None:
            if (
                self.loss_cause.loss_id != self.execution_id
                or self.loss_cause.realized_r != self.realized_r
            ):
                raise ValueError("settled loss receipt does not reconcile R and execution")


@dataclass(frozen=True, slots=True)
class A1TraderCognitionState:
    """Immutable chronological cursor and independently sourced chosen receipts."""

    latest_decision_at: datetime | None = None
    prior_candidates: tuple[A1TraderCognitiveCandidate, ...] = ()
    externally_settled_executions: tuple[A1ExternallySettledExecution, ...] = ()
    processed_barrier_count: int = 0

    def __post_init__(self) -> None:
        ids = tuple(x.source_opportunity_id for x in self.prior_candidates)
        receipts = tuple(x.execution_id for x in self.externally_settled_executions)
        if len(ids) != len(set(ids)) or len(receipts) != len(set(receipts)):
            raise ValueError("duplicate prior source or settled execution")
        if (self.latest_decision_at is None) != (self.processed_barrier_count == 0):
            raise ValueError("invalid chronological Trader cursor")
        if self.latest_decision_at is not None:
            _aware(self.latest_decision_at)


def prepare_trader_cognition_packet(
    *,
    barrier: A1MultiHypothesisBarrier,
    settled_memory: A1CausalSettledMemory,
    exposure_intents: tuple[A1ProspectiveSourceExposure, ...] = (),
) -> A1TraderCognitionPacket:
    """Invoke original Master Frame with genuine caller-provided nine-market data."""
    assessed = replay_multi_hypothesis_evidence(
        barriers=(barrier,), chosen_settlements=settled_memory
    )
    joint = assess_joint_competition_barrier(
        barrier=barrier, census=assessed, exposure_intents=exposure_intents
    )
    ancestry = {
        row.binding.source_opportunity_id: row for row in assessed.source_ancestry
    }
    by_decision = {row.source_opportunity_id: row for row in assessed.decisions}
    candidates: list[A1TraderCognitiveCandidate] = []
    for item in joint.candidate_rows:
        id_ = item.source_opportunity_id
        row, source = by_decision[id_], ancestry[id_]
        status = {
            "PASS_TO_STRATEGY": "SOURCE_METHOD_ARBITRATION_REQUIRED",
            "WAIT": "COGNITIVE_WAIT_RESEARCH",
            "ABSTAIN": "COGNITIVE_ABSTAIN_RESEARCH",
        }[row.cognitive_gate]
        candidates.append(A1TraderCognitiveCandidate(
            source_opportunity_id=id_,
            symbol=source.binding.symbol,
            decision_at=barrier.observed_at,
            source_rule_id=source.source_rule_id,
            hypothesis_id=source.hypothesis_id,
            source_event_id=source.source_event_id,
            h1_confirmed_at=source.h1_confirmed_at,
            m15_confirmed_at=source.m15_confirmed_at,
            m1_confirmed_at=source.m1_confirmed_at,
            cognitive_gate=row.cognitive_gate,
            why_tokens=item.why_tokens,
            uncertainty_tokens=row.uncertainty_tokens,
            joint_review_peer_ids=item.potential_collision_source_ids,
            unknown_relation_peer_ids=item.unknown_relation_source_ids,
            closed_chosen_history_count=row.closed_chosen_history_count,
            closed_chosen_failure_count=row.closed_chosen_failure_count,
            trader_review_status=status,
        ))
    return A1TraderCognitionPacket(
        identity=IDENTITY,
        observed_at=barrier.observed_at,
        candidates=tuple(candidates),
        joint=joint,
        source_opportunity_ids=joint.source_ids,
        remaining_session_slots=joint.remaining_session_slots,
        nine_market_frame_called_for_each_source=all(
            row.nine_market_frame_invoked for row in assessed.decisions
        ),
        original_source_denominator_preserved=(
            set(assessed.source_ids) == set(barrier.expected_source_ids)
        ),
        settlement_history_reconciled=all(
            row.closed_chosen_history_count == len(
                settled_memory.as_of(barrier.observed_at)
            )
            for row in assessed.decisions
        ),
    )


def advance_trader_cognition(
    *,
    state: A1TraderCognitionState,
    barrier: A1MultiHypothesisBarrier,
    newly_settled: tuple[A1ExternallySettledExecution, ...] = (),
    exposure_intents: tuple[A1ProspectiveSourceExposure, ...] = (),
) -> tuple[A1TraderCognitionState, A1TraderCognitionPacket]:
    """Prepare the next research handoff; only prior source-known receipts teach.

    Same-clock settlement ACKs are excluded, and future ACKs are rejected.
    No synthesized fills, discretionary ranking, or economic admission.
    """
    at = _aware(barrier.observed_at)
    if state.latest_decision_at is not None and at <= state.latest_decision_at:
        raise ValueError("Trader cognition barriers must advance strictly in time")
    ids = tuple(item.binding.source_opportunity_id for item in barrier.alternatives)
    if set(ids) & {item.source_opportunity_id for item in state.prior_candidates}:
        raise ValueError("Trader cognition source ID reused across barriers")
    previously_seen = {row.source_opportunity_id: row for row in state.prior_candidates}
    existing = state.externally_settled_executions
    known_exec_ids = {row.execution_id for row in existing}
    known_source_ids = {row.source_opportunity_id for row in existing}
    proven: list[A1ExternallySettledExecution] = []
    for receipt in newly_settled:
        if (
            receipt.execution_id in known_exec_ids
            or receipt.execution_id in {item.execution_id for item in proven}
            or receipt.source_opportunity_id in known_source_ids
            or receipt.source_opportunity_id in {
                item.source_opportunity_id for item in proven
            }
        ):
            raise ValueError("duplicate externally settled source or execution")
        prior = previously_seen.get(receipt.source_opportunity_id)
        if prior is None or prior.cognitive_gate != "PASS_TO_STRATEGY":
            raise ValueError("external settlement lacks prior observed PASS source")
        if receipt.entry_at < prior.decision_at or receipt.settlement_known_at >= at:
            raise ValueError("external settlement crosses entry or knowledge frontier")
        if receipt.loss_cause is not None and (
            receipt.loss_cause.symbol != prior.symbol
            or receipt.loss_cause.hypothesis_id != prior.hypothesis_id
        ):
            raise ValueError("settled loss source/hypothesis identity inconsistent")
        proven.append(receipt)
    all_receipts = (*existing, *proven)
    # Receipt knowledge, not only broker exit clock, is the visibility frontier.
    chosen_memory = A1CausalSettledMemory(tuple(
        A1SettledChosenTrade(
            execution_id=row.execution_id,
            entry_at=row.entry_at,
            exit_at=row.settlement_known_at,
            loss_cause=row.loss_cause,
        )
        for row in all_receipts
    ))
    packet = prepare_trader_cognition_packet(
        barrier=barrier, settled_memory=chosen_memory,
        exposure_intents=exposure_intents,
    )
    return (
        A1TraderCognitionState(
            latest_decision_at=at,
            prior_candidates=(*state.prior_candidates, *packet.candidates),
            externally_settled_executions=all_receipts,
            processed_barrier_count=state.processed_barrier_count + 1,
        ),
        packet,
    )
