"""Source-faithful raw observation -> pre-Risk trader pipeline for Capitalizer V2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_ftm_observation_engine_v2 import (
    CapitalizerFTMObservationSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_engine_v2 import (
    CapitalizerFractalObservationSnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_engine_v2 import (
    CapitalizerSourceTraderEngineAssessment,
    CapitalizerSourceTraderEngineFacts,
    assess_source_trader_engine,
)


class CapitalizerSourcePipelineState(StrEnum):
    WAIT = "WAIT"
    PRE_RISK_READY = "PRE_RISK_READY"


@dataclass(frozen=True, slots=True)
class CapitalizerSourcePipelineAssessment:
    symbol: str
    route: CapitalizerSourceEntryRoute
    state: CapitalizerSourcePipelineState
    source_engine: CapitalizerSourceTraderEngineAssessment | None
    reasons: tuple[str, ...]
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source pipeline stops before QORE Risk/execution")
        ready = self.state is CapitalizerSourcePipelineState.PRE_RISK_READY
        if ready != (self.source_engine is not None):
            raise ValueError("PRE_RISK_READY requires exactly one source engine assessment")
        if self.source_engine is not None and not self.source_engine.passes_to_qore_risk:
            raise ValueError("PRE_RISK_READY source engine must pass to QORE Risk")


def _side(direction: CapitalizerSourceDirection) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )


def evaluate_fractal_snapshot(
    *,
    snapshot: CapitalizerFractalObservationSnapshot,
    cognitive_gate_decision: CapitalizerCognitiveGateDecision,
) -> CapitalizerSourcePipelineAssessment:
    route = CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION
    if (
        not snapshot.complete
        or snapshot.daily_bias.direction is None
        or snapshot.m1_protected_swing is None
        or snapshot.structural_target is None
        or snapshot.fractal_alignment is None
    ):
        return CapitalizerSourcePipelineAssessment(
            symbol=snapshot.symbol,
            route=route,
            state=CapitalizerSourcePipelineState.WAIT,
            source_engine=None,
            reasons=(*snapshot.reasons, "RAW_FRACTAL_SNAPSHOT_NOT_READY"),
        )

    engine = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol=snapshot.symbol,
            side=_side(snapshot.daily_bias.direction),
            route=route,
            cognitive_gate_decision=cognitive_gate_decision,
            source_session=snapshot.session,
            daily_bias=snapshot.daily_bias,
            entry_price=snapshot.entry_price,
            protected_swing=snapshot.m1_protected_swing,
            structural_target=snapshot.structural_target,
            target_kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
            fractal_alignment=snapshot.fractal_alignment,
        )
    )
    if not engine.passes_to_qore_risk:
        return CapitalizerSourcePipelineAssessment(
            symbol=snapshot.symbol,
            route=route,
            state=CapitalizerSourcePipelineState.WAIT,
            source_engine=None,
            reasons=engine.reasons,
        )

    return CapitalizerSourcePipelineAssessment(
        symbol=snapshot.symbol,
        route=route,
        state=CapitalizerSourcePipelineState.PRE_RISK_READY,
        source_engine=engine,
        reasons=engine.reasons,
    )


def evaluate_ftm_snapshot(
    *,
    snapshot: CapitalizerFTMObservationSnapshot,
    cognitive_gate_decision: CapitalizerCognitiveGateDecision,
) -> CapitalizerSourcePipelineAssessment:
    route = CapitalizerSourceEntryRoute.FAILURE_TO_MANIPULATE_CONTINUATION
    direction = snapshot.failure_to_manipulate.continuation_direction
    if (
        not snapshot.complete
        or snapshot.daily_bias.direction is None
        or snapshot.continuation_protected_swing is None
        or snapshot.structural_target is None
    ):
        return CapitalizerSourcePipelineAssessment(
            symbol=snapshot.symbol,
            route=route,
            state=CapitalizerSourcePipelineState.WAIT,
            source_engine=None,
            reasons=(*snapshot.reasons, "RAW_FTM_SNAPSHOT_NOT_READY"),
        )

    engine = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol=snapshot.symbol,
            side=_side(direction),
            route=route,
            cognitive_gate_decision=cognitive_gate_decision,
            source_session=snapshot.session,
            daily_bias=snapshot.daily_bias,
            entry_price=snapshot.entry_price,
            protected_swing=snapshot.continuation_protected_swing,
            structural_target=snapshot.structural_target,
            target_kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
            failure_to_manipulate=snapshot.failure_to_manipulate,
        )
    )
    if not engine.passes_to_qore_risk:
        return CapitalizerSourcePipelineAssessment(
            symbol=snapshot.symbol,
            route=route,
            state=CapitalizerSourcePipelineState.WAIT,
            source_engine=None,
            reasons=engine.reasons,
        )

    return CapitalizerSourcePipelineAssessment(
        symbol=snapshot.symbol,
        route=route,
        state=CapitalizerSourcePipelineState.PRE_RISK_READY,
        source_engine=engine,
        reasons=engine.reasons,
    )
