"""Integrated causal replay spine for QORE Capitalizer V1.

This module opens the replay phase without weakening the frozen source contract.

Important evidence boundary:
- the consumed CIBO Atlas corpus is native M5 context;
- the frozen source-faithful trader requires an M1 confirmation path;
- M1 must therefore come from native <=60 second evidence or aggregation from finer data;
- replay must fail closed rather than synthesize M1 from M5.

The coordinator consumes already-causal Cognitive + source-pipeline decisions and a separate
QORE Risk research decision. It can record simulated admissions, but it cannot place broker
orders, size positions, mutate strategy, or claim economic certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_pipeline_v2 import (
    CapitalizerSourcePipelineAssessment,
    CapitalizerSourcePipelineState,
)


class CapitalizerReplayEvidenceProvenance(StrEnum):
    PROVIDER_NATIVE = "PROVIDER_NATIVE"
    AGGREGATED_FROM_FINER = "AGGREGATED_FROM_FINER"
    CONTEXT_ONLY = "CONTEXT_ONLY"


@dataclass(frozen=True, slots=True)
class CapitalizerReplayResolutionEvidence:
    """Auditable resolution provenance used by the integrated replay."""

    resolution_seconds: int
    provenance: CapitalizerReplayEvidenceProvenance
    source_record_id: str
    parent_resolution_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.resolution_seconds <= 0:
            raise ValueError("replay evidence resolution must be positive")
        if not self.source_record_id:
            raise ValueError("replay evidence requires source_record_id")
        if self.provenance is CapitalizerReplayEvidenceProvenance.AGGREGATED_FROM_FINER:
            if (
                self.parent_resolution_seconds is None
                or self.parent_resolution_seconds <= 0
                or self.parent_resolution_seconds >= self.resolution_seconds
            ):
                raise ValueError(
                    "aggregated replay evidence requires a strictly finer parent resolution"
                )
        elif self.parent_resolution_seconds is not None:
            raise ValueError(
                "parent_resolution_seconds is only valid for AGGREGATED_FROM_FINER"
            )

    @property
    def supports_m1_execution(self) -> bool:
        return (
            self.resolution_seconds <= 60
            and self.provenance
            in {
                CapitalizerReplayEvidenceProvenance.PROVIDER_NATIVE,
                CapitalizerReplayEvidenceProvenance.AGGREGATED_FROM_FINER,
            }
        )


class CapitalizerReplayRiskDecision(StrEnum):
    NOT_EVALUATED = "NOT_EVALUATED"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"


class CapitalizerIntegratedReplayState(StrEnum):
    WAIT_COGNITIVE = "WAIT_COGNITIVE"
    ABSTAIN_COGNITIVE = "ABSTAIN_COGNITIVE"
    WAIT_SOURCE = "WAIT_SOURCE"
    PRE_RISK_READY = "PRE_RISK_READY"
    RISK_BLOCKED = "RISK_BLOCKED"
    SESSION_CAP_REACHED = "SESSION_CAP_REACHED"
    SIMULATED_EXECUTION = "SIMULATED_EXECUTION"


@dataclass(frozen=True, slots=True)
class CapitalizerIntegratedReplayFrame:
    """One point-in-time market decision entering the multi-market replay spine."""

    symbol: str
    session: CapitalizerSession
    operating_date: date
    observed_at: datetime
    cognitive_decision: CapitalizerCognitiveGateDecision
    source_pipeline: CapitalizerSourcePipelineAssessment | None
    resolution_evidence: tuple[CapitalizerReplayResolutionEvidence, ...]
    risk_decision: CapitalizerReplayRiskDecision = (
        CapitalizerReplayRiskDecision.NOT_EVALUATED
    )
    risk_decision_id: str | None = None
    risk_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("integrated replay symbol must be uppercase")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("integrated replay symbol must belong to frozen session universe")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("integrated replay observed_at must be timezone-aware")
        if not self.resolution_evidence:
            raise ValueError("integrated replay frame requires auditable resolution evidence")

        if self.cognitive_decision is not CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY:
            if self.source_pipeline is not None:
                raise ValueError(
                    "source strategy cannot run unless cognition emitted PASS_TO_STRATEGY"
                )
            if self.risk_decision is not CapitalizerReplayRiskDecision.NOT_EVALUATED:
                raise ValueError("QORE Risk cannot evaluate a candidate blocked by cognition")
        elif self.source_pipeline is not None:
            if self.source_pipeline.symbol != self.symbol:
                raise ValueError("source pipeline symbol must match replay frame symbol")
            if (
                self.source_pipeline.state
                is CapitalizerSourcePipelineState.PRE_RISK_READY
                and not any(
                    item.supports_m1_execution for item in self.resolution_evidence
                )
            ):
                raise ValueError(
                    "PRE_RISK_READY replay requires <=60s causal evidence; "
                    "consumed CIBO M5 alone is context-only and cannot be promoted to M1"
                )

        if self.risk_decision is CapitalizerReplayRiskDecision.NOT_EVALUATED:
            if self.risk_decision_id is not None or self.risk_reasons:
                raise ValueError("NOT_EVALUATED risk decision cannot carry audit outcome")
        else:
            if self.risk_decision_id is None or not self.risk_decision_id:
                raise ValueError("evaluated QORE Risk decision requires decision id")
            if not self.risk_reasons:
                raise ValueError("evaluated QORE Risk decision requires explicit reasons")
            if (
                self.source_pipeline is None
                or self.source_pipeline.state
                is not CapitalizerSourcePipelineState.PRE_RISK_READY
            ):
                raise ValueError("QORE Risk may evaluate only PRE_RISK_READY source candidates")


@dataclass(frozen=True, slots=True)
class CapitalizerIntegratedReplayEvent:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    observed_at: datetime
    state: CapitalizerIntegratedReplayState
    session_execution_ordinal: int | None
    reasons: tuple[str, ...]
    outcome_aware: bool = False
    broker_order_emitted: bool = False
    capital_sized: bool = False

    def __post_init__(self) -> None:
        if self.outcome_aware:
            raise ValueError("integrated replay admission cannot use future trade outcomes")
        if self.broker_order_emitted or self.capital_sized:
            raise ValueError("integrated replay research cannot emit broker/capital actions")
        if self.state is CapitalizerIntegratedReplayState.SIMULATED_EXECUTION:
            if self.session_execution_ordinal is None:
                raise ValueError("simulated execution requires session ordinal")
            if not 1 <= self.session_execution_ordinal <= MAX_EXECUTIONS_PER_SESSION:
                raise ValueError("simulated execution ordinal exceeds frozen session ceiling")
        elif self.session_execution_ordinal is not None:
            raise ValueError("only simulated execution may carry execution ordinal")


@dataclass(frozen=True, slots=True)
class CapitalizerIntegratedReplayReport:
    events: tuple[CapitalizerIntegratedReplayEvent, ...]
    observed_symbols: tuple[str, ...]
    full_universe_covered: bool
    simulated_executions: int
    max_session_executions_observed: int
    used_future_outcomes: bool = False
    emitted_broker_orders: bool = False
    granted_capital_authority: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if (
            self.used_future_outcomes
            or self.emitted_broker_orders
            or self.granted_capital_authority
            or self.trader_certified
        ):
            raise ValueError("integrated replay report cannot claim forbidden authority/state")
        if self.max_session_executions_observed > MAX_EXECUTIONS_PER_SESSION:
            raise ValueError("replay exceeded frozen MAX3 session ceiling")


_FULL_UNIVERSE = frozenset(
    symbol
    for session in CapitalizerSession
    for symbol in allowed_markets(session)
)


def cibo_m5_context_evidence(*, source_record_id: str) -> CapitalizerReplayResolutionEvidence:
    """Mark consumed CIBO M5 as context-only, never as a synthetic M1 substitute."""

    return CapitalizerReplayResolutionEvidence(
        resolution_seconds=300,
        provenance=CapitalizerReplayEvidenceProvenance.CONTEXT_ONLY,
        source_record_id=source_record_id,
    )


def _state_before_risk(
    frame: CapitalizerIntegratedReplayFrame,
) -> tuple[CapitalizerIntegratedReplayState, tuple[str, ...]]:
    if frame.cognitive_decision is CapitalizerCognitiveGateDecision.WAIT:
        return CapitalizerIntegratedReplayState.WAIT_COGNITIVE, ("COGNITIVE_WAIT",)
    if frame.cognitive_decision is CapitalizerCognitiveGateDecision.ABSTAIN:
        return CapitalizerIntegratedReplayState.ABSTAIN_COGNITIVE, ("COGNITIVE_ABSTAIN",)

    if frame.source_pipeline is None:
        return CapitalizerIntegratedReplayState.WAIT_SOURCE, ("SOURCE_PIPELINE_NOT_READY",)
    if frame.source_pipeline.state is CapitalizerSourcePipelineState.WAIT:
        return (
            CapitalizerIntegratedReplayState.WAIT_SOURCE,
            frame.source_pipeline.reasons,
        )
    if frame.risk_decision is CapitalizerReplayRiskDecision.NOT_EVALUATED:
        return (
            CapitalizerIntegratedReplayState.PRE_RISK_READY,
            ("SOURCE_PRE_RISK_READY",),
        )
    if frame.risk_decision is CapitalizerReplayRiskDecision.REJECTED:
        return CapitalizerIntegratedReplayState.RISK_BLOCKED, frame.risk_reasons
    return (
        CapitalizerIntegratedReplayState.PRE_RISK_READY,
        ("QORE_RISK_AUTHORIZED_PENDING_SESSION_ADMISSION",),
    )


def run_integrated_replay(
    frames: tuple[CapitalizerIntegratedReplayFrame, ...],
    *,
    require_full_universe: bool = True,
) -> CapitalizerIntegratedReplayReport:
    """Replay a globally chronological stream without outcome-aware selection.

    Same-timestamp authorized competition is fail-closed when it exceeds remaining session
    slots. Upstream cognition/opportunity competition must resolve which candidates survive;
    this coordinator will not choose alphabetically or from terminal outcomes.
    """

    if not frames:
        raise ValueError("integrated replay requires at least one frame")

    previous_at: datetime | None = None
    for frame in frames:
        if previous_at is not None and frame.observed_at < previous_at:
            raise ValueError("integrated replay chronology moved backward")
        previous_at = frame.observed_at

    observed_symbols = frozenset(frame.symbol for frame in frames)
    full_universe_covered = observed_symbols == _FULL_UNIVERSE
    if require_full_universe and not full_universe_covered:
        missing = sorted(_FULL_UNIVERSE - observed_symbols)
        extra = sorted(observed_symbols - _FULL_UNIVERSE)
        raise ValueError(
            f"integrated replay universe mismatch missing={missing} extra={extra}"
        )

    execution_counts: dict[tuple[date, CapitalizerSession], int] = {}
    events: list[CapitalizerIntegratedReplayEvent] = []

    index = 0
    while index < len(frames):
        observed_at = frames[index].observed_at
        batch_end = index + 1
        while batch_end < len(frames) and frames[batch_end].observed_at == observed_at:
            batch_end += 1
        batch = frames[index:batch_end]

        authorized_by_bucket: dict[
            tuple[date, CapitalizerSession],
            list[CapitalizerIntegratedReplayFrame],
        ] = {}
        for frame in batch:
            if frame.risk_decision is CapitalizerReplayRiskDecision.AUTHORIZED:
                key = (frame.operating_date, frame.session)
                authorized_by_bucket.setdefault(key, []).append(frame)

        for key, authorized in authorized_by_bucket.items():
            remaining = MAX_EXECUTIONS_PER_SESSION - execution_counts.get(key, 0)
            if len(authorized) > remaining and remaining > 0:
                raise ValueError(
                    "same-timestamp opportunity competition unresolved: "
                    "authorized candidates exceed remaining session slots"
                )

        for frame in batch:
            state, reasons = _state_before_risk(frame)
            ordinal: int | None = None

            if frame.risk_decision is CapitalizerReplayRiskDecision.AUTHORIZED:
                key = (frame.operating_date, frame.session)
                used = execution_counts.get(key, 0)
                if used >= MAX_EXECUTIONS_PER_SESSION:
                    state = CapitalizerIntegratedReplayState.SESSION_CAP_REACHED
                    reasons = ("MAX3_SESSION_CEILING_REACHED",)
                else:
                    used += 1
                    execution_counts[key] = used
                    state = CapitalizerIntegratedReplayState.SIMULATED_EXECUTION
                    ordinal = used
                    reasons = frame.risk_reasons

            events.append(
                CapitalizerIntegratedReplayEvent(
                    symbol=frame.symbol,
                    session=frame.session,
                    operating_date=frame.operating_date,
                    observed_at=frame.observed_at,
                    state=state,
                    session_execution_ordinal=ordinal,
                    reasons=tuple(dict.fromkeys(reasons)),
                )
            )

        index = batch_end

    simulated = sum(
        event.state is CapitalizerIntegratedReplayState.SIMULATED_EXECUTION
        for event in events
    )
    max_observed = max(execution_counts.values(), default=0)
    return CapitalizerIntegratedReplayReport(
        events=tuple(events),
        observed_symbols=tuple(sorted(observed_symbols)),
        full_universe_covered=full_universe_covered,
        simulated_executions=simulated,
        max_session_executions_observed=max_observed,
    )
