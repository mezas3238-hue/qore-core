"""V49 high-frequency Scalper decision graph.

The graph is deliberately compact:
H1 persistent context state
-> M15 setup formation
-> M1 execution trigger
-> structural invalidation + intraday target.

No Daily/H4 layer may be inserted. A new H1 signal is not required for every trade.
M15 and M1 techniques are route alternatives, never a global superintersection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V49_HIGH_FREQUENCY_DECISION_GRAPH"


class V49GateRelation(StrEnum):
    REQUIRED = "REQUIRED"
    ALTERNATIVE = "ALTERNATIVE"
    CONTEXT = "CONTEXT"


@dataclass(frozen=True, slots=True)
class V49DecisionStage:
    stage_id: str
    timeframe: str
    relation: V49GateRelation
    description: str

    def __post_init__(self) -> None:
        if self.stage_id != self.stage_id.upper():
            raise ValueError("stage id must be uppercase")
        if self.timeframe not in {"H1", "M15", "M1"}:
            raise ValueError("V49 decision graph only allows H1, M15 and M1")
        if not self.description:
            raise ValueError("decision stage requires description")


STAGES: tuple[V49DecisionStage, ...] = (
    V49DecisionStage(
        "H1_CONTEXT_STATE",
        "H1",
        V49GateRelation.REQUIRED,
        "Persistent directional/liquidity context; reusable until invalidated.",
    ),
    V49DecisionStage(
        "M15_SETUP",
        "M15",
        V49GateRelation.REQUIRED,
        "A fresh intraday setup forms inside the valid H1 state.",
    ),
    V49DecisionStage(
        "M1_TRIGGER",
        "M1",
        V49GateRelation.REQUIRED,
        "One valid execution trigger confirms the specific M15 setup.",
    ),
    V49DecisionStage(
        "M1_TRIGGER_ALTERNATIVES",
        "M1",
        V49GateRelation.ALTERNATIVE,
        (
            "CISD, liquidity-sweep+CISD, FVG-retrace+CISD, or another explicitly "
            "source/QORE-approved trigger may compete; they are not simultaneous AND gates."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V49HighFrequencyDecisionGraph:
    identity: str = IDENTITY
    stages: tuple[V49DecisionStage, ...] = STAGES
    fresh_h1_event_required_per_trade: bool = False
    daily_allowed: bool = False
    h4_allowed: bool = False
    m15_setup_consumed_by_unrelated_trade: bool = False
    m1_superintersection_required: bool = False
    max3_session_ceiling_preserved: bool = True
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 decision graph identity is frozen")
        if self.fresh_h1_event_required_per_trade:
            raise ValueError("high-frequency topology reuses H1 state")
        if self.daily_allowed or self.h4_allowed:
            raise ValueError("Daily/H4 cannot enter the V49 decision graph")
        if self.m15_setup_consumed_by_unrelated_trade:
            raise ValueError("M15 setup identity must remain causal")
        if self.m1_superintersection_required:
            raise ValueError("V49 forbids universal M1 superintersection")
        if not self.max3_session_ceiling_preserved:
            raise ValueError("MAX3/session governance must remain intact")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("V49 graph is pre-economic")


V49_HIGH_FREQUENCY_DECISION_GRAPH = V49HighFrequencyDecisionGraph()
