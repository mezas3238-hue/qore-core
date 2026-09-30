"""V48 source-faithful human decision graphs for QORE Capitalizer.

The graph is intentionally route-specific. It prevents QORE from collapsing distinct
source-supported session/entry routes into one global AND gate.

This is a source reconstruction artifact, not a production strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_HUMAN_DECISION_GRAPH"


class V48Session(StrEnum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    GENERIC = "GENERIC"


class V48Route(StrEnum):
    ASIA_POSITIONAL = "ASIA_POSITIONAL"
    ASIA_4H_15M_FRACTAL = "ASIA_4H_15M_FRACTAL"
    LONDON_DAILY_4H_15M = "LONDON_DAILY_4H_15M"
    NEW_YORK_MANIPULATION = "NEW_YORK_MANIPULATION"
    GENERIC_SCALP_H1_M15_M1 = "GENERIC_SCALP_H1_M15_M1"
    FAILURE_TO_MANIPULATE = "FAILURE_TO_MANIPULATE"


class V48RouteStageRole(StrEnum):
    NARRATIVE = "NARRATIVE"
    STRUCTURE = "STRUCTURE"
    EXECUTION = "EXECUTION"
    INVALIDATION = "INVALIDATION"
    TARGET = "TARGET"


@dataclass(frozen=True, slots=True)
class V48RouteStage:
    stage_id: str
    role: V48RouteStageRole
    timeframe: str
    required: bool
    description: str

    def __post_init__(self) -> None:
        if not self.stage_id or self.stage_id != self.stage_id.upper():
            raise ValueError("stage_id must be non-empty uppercase")
        if not self.timeframe or not self.description:
            raise ValueError("route stage requires timeframe and description")


@dataclass(frozen=True, slots=True)
class V48ExecutionAlternative:
    alternative_id: str
    description: str
    source_explicit: bool = True

    def __post_init__(self) -> None:
        if not self.alternative_id or self.alternative_id != self.alternative_id.upper():
            raise ValueError("alternative_id must be non-empty uppercase")
        if not self.description:
            raise ValueError("execution alternative requires description")


@dataclass(frozen=True, slots=True)
class V48HumanDecisionRoute:
    route: V48Route
    session: V48Session
    source_url: str
    thesis: str
    stages: tuple[V48RouteStage, ...]
    execution_alternatives: tuple[V48ExecutionAlternative, ...] = ()
    session_binding_explicit: bool = True
    route_is_alternative_not_global_requirement: bool = True

    def __post_init__(self) -> None:
        if not self.source_url.startswith("https://"):
            raise ValueError("decision route requires source URL")
        if not self.thesis or not self.stages:
            raise ValueError("decision route requires thesis and stages")
        stage_ids = tuple(stage.stage_id for stage in self.stages)
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("route stage IDs must be unique inside each route")
        alt_ids = tuple(item.alternative_id for item in self.execution_alternatives)
        if len(alt_ids) != len(set(alt_ids)):
            raise ValueError("execution alternatives must be unique inside each route")


ROUTES: tuple[V48HumanDecisionRoute, ...] = (
    V48HumanDecisionRoute(
        route=V48Route.ASIA_POSITIONAL,
        session=V48Session.ASIA,
        source_url="https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
        thesis=(
            "Use a completed higher-timeframe framework and already-confirmed protected swing "
            "to participate near the new higher-timeframe candle open when immediate expansion "
            "may not offer another retracement."
        ),
        stages=(
            V48RouteStage(
                "ASIA_HTF_BIAS",
                V48RouteStageRole.NARRATIVE,
                "DAILY/HTF",
                True,
                "Higher-timeframe bias/reason for expansion is established first.",
            ),
            V48RouteStage(
                "ASIA_COMPLETED_FRACTAL_FRAMEWORK",
                V48RouteStageRole.STRUCTURE,
                "HTF+LTF",
                True,
                (
                    "Valid HTF Candle-2/3 framework, lower-timeframe CISD and protected swing "
                    "already exist before the new candle."
                ),
            ),
            V48RouteStage(
                "ASIA_POSITIONAL_OPEN",
                V48RouteStageRole.EXECUTION,
                "NEW_HTF_CANDLE_OPEN",
                True,
                "Positional execution near the new higher-timeframe candle open.",
            ),
            V48RouteStage(
                "ASIA_POSITIONAL_PROTECTED_SWING_STOP",
                V48RouteStageRole.INVALIDATION,
                "STRUCTURAL",
                True,
                "Protected swing supplies logical invalidation.",
            ),
            V48RouteStage(
                "ASIA_POSITIONAL_HTF_OBJECTIVE",
                V48RouteStageRole.TARGET,
                "HTF",
                True,
                "Target comes from the existing higher-timeframe framework.",
            ),
        ),
    ),
    V48HumanDecisionRoute(
        route=V48Route.ASIA_4H_15M_FRACTAL,
        session=V48Session.ASIA,
        source_url="https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
        thesis=(
            "When positional conditions are insufficient, wait for 4H Candle-2 confirmation "
            "and use the 15M fractal model to confirm the developing wick/protected swing."
        ),
        stages=(
            V48RouteStage(
                "ASIA_DAILY_BIAS",
                V48RouteStageRole.NARRATIVE,
                "DAILY/HTF",
                True,
                "Higher-timeframe fractal bias/reason for expansion is established.",
            ),
            V48RouteStage(
                "ASIA_4H_C2_CONFIRMATION",
                V48RouteStageRole.STRUCTURE,
                "4H",
                True,
                "4H Candle-2 closure provides additional confirmation.",
            ),
            V48RouteStage(
                "ASIA_15M_CISD_PROTECTED_SWING",
                V48RouteStageRole.EXECUTION,
                "15M",
                True,
                (
                    "15M intra-candle CISD confirms a new protected swing and supplies "
                    "the source-required lower-timeframe execution confirmation."
                ),
            ),
            V48RouteStage(
                "ASIA_15M_PROTECTED_SWING_STOP",
                V48RouteStageRole.INVALIDATION,
                "15M/STRUCTURAL",
                True,
                "Protected swing is the logical invalidation.",
            ),
            V48RouteStage(
                "ASIA_4H15M_HTF_OBJECTIVE",
                V48RouteStageRole.TARGET,
                "HTF",
                True,
                "Trade participates in the higher-timeframe expansion objective.",
            ),
        ),
    ),
    V48HumanDecisionRoute(
        route=V48Route.LONDON_DAILY_4H_15M,
        session=V48Session.LONDON,
        source_url="https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",
        thesis=(
            "Establish daily bias, let the daily and 4H wick form, then use 15M CISD/protected "
            "swing confirmation and continuation to trade the body/expansion."
        ),
        stages=(
            V48RouteStage(
                "LONDON_DAILY_BIAS",
                V48RouteStageRole.NARRATIVE,
                "DAILY",
                True,
                "Daily bias/narrative precedes lower-timeframe execution.",
            ),
            V48RouteStage(
                "LONDON_DAILY_WICK",
                V48RouteStageRole.STRUCTURE,
                "DAILY",
                True,
                (
                    "Allow the daily wick to form before trading the expected daily body; "
                    "this is a semantic stage evidenced by the 4H/15M structure, not an "
                    "extra independent gate."
                ),
            ),
            V48RouteStage(
                "LONDON_4H_WICK_SWING",
                V48RouteStageRole.STRUCTURE,
                "4H",
                True,
                "4H wick/swing structure defines the next expansion layer.",
            ),
            V48RouteStage(
                "LONDON_15M_CISD_PROTECTED_SWING",
                V48RouteStageRole.STRUCTURE,
                "15M",
                True,
                "15M CISD confirms the protected swing.",
            ),
            V48RouteStage(
                "LONDON_15M_CONTINUATION",
                V48RouteStageRole.EXECUTION,
                "15M",
                True,
                "Continuation aligned with daily and 4H provides the entry.",
            ),
            V48RouteStage(
                "LONDON_PROTECTED_SWING_STOP",
                V48RouteStageRole.INVALIDATION,
                "15M/STRUCTURAL",
                True,
                "Protected swing anchors invalidation.",
            ),
            V48RouteStage(
                "LONDON_HTF_DRAW",
                V48RouteStageRole.TARGET,
                "HTF",
                True,
                "Expansion targets the higher-timeframe draw/liquidity objective.",
            ),
        ),
    ),
    V48HumanDecisionRoute(
        route=V48Route.NEW_YORK_MANIPULATION,
        session=V48Session.NEW_YORK,
        source_url="https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/",
        thesis=(
            "When London consolidates, New York can sweep the current range, confirm a CISD, "
            "then expand in the opposite direction toward a structural liquidity objective."
        ),
        stages=(
            V48RouteStage(
                "NY_LONDON_BEHAVIOR",
                V48RouteStageRole.NARRATIVE,
                "SESSION_CONTEXT",
                True,
                (
                    "London behavior/context determines whether the NY manipulation "
                    "profile is plausible."
                ),
            ),
            V48RouteStage(
                "NY_LIQUIDITY_SWEEP",
                V48RouteStageRole.STRUCTURE,
                "INTRADAY",
                True,
                "New York sweeps the relevant range high/low.",
            ),
            V48RouteStage(
                "NY_CISD",
                V48RouteStageRole.STRUCTURE,
                "LTF",
                True,
                "CISD confirms the directional shift after the sweep.",
            ),
            V48RouteStage(
                "NY_ENTRY_MODEL",
                V48RouteStageRole.EXECUTION,
                "LTF",
                True,
                "Execute using one valid entry model rather than requiring all entry models.",
            ),
            V48RouteStage(
                "NY_SWEEP_EXTREME_STOP",
                V48RouteStageRole.INVALIDATION,
                "STRUCTURAL",
                True,
                "Invalidation is beyond the relevant structural sweep/protected extreme.",
            ),
            V48RouteStage(
                "NY_STRUCTURAL_LIQUIDITY_TARGET",
                V48RouteStageRole.TARGET,
                "HTF/DAILY",
                True,
                (
                    "Target is a structural liquidity objective such as PDH/PDL when "
                    "context supports it."
                ),
            ),
        ),
        execution_alternatives=(
            V48ExecutionAlternative("NY_FVG_ENTRY", "Fair value gap entry/refinement."),
            V48ExecutionAlternative("NY_ORDER_BLOCK_ENTRY", "Order block entry/refinement."),
            V48ExecutionAlternative(
                "NY_OTHER_VALID_ENTRY_MODEL",
                "Another source-valid entry model chosen within the established thesis.",
            ),
        ),
    ),
    V48HumanDecisionRoute(
        route=V48Route.GENERIC_SCALP_H1_M15_M1,
        session=V48Session.GENERIC,
        source_url="https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        thesis=(
            "Trade the body of an hourly expansion candle: Daily provides broader context, "
            "H1 defines scalp bias, 15M forms the swing, and M1 executes the already-clear thesis."
        ),
        stages=(
            V48RouteStage(
                "SCALP_DAILY_CONTEXT",
                V48RouteStageRole.NARRATIVE,
                "DAILY",
                False,
                (
                    "Daily gives broader directional context but does not replace "
                    "H1 decision authority."
                ),
            ),
            V48RouteStage(
                "SCALP_H1_BIAS",
                V48RouteStageRole.NARRATIVE,
                "H1",
                True,
                "Hourly candle defines the scalping bias/expected expansion.",
            ),
            V48RouteStage(
                "SCALP_M15_SWING",
                V48RouteStageRole.STRUCTURE,
                "M15",
                True,
                "M15 forms the swing/wick structure aligned with H1.",
            ),
            V48RouteStage(
                "SCALP_M1_CONTINUATION",
                V48RouteStageRole.EXECUTION,
                "M1",
                True,
                (
                    "M1 confirms an executable continuation of the pre-existing thesis. FVG "
                    "interaction, CISD and protected-swing formation are source examples of "
                    "continuation behavior, not individually frozen sufficient conditions."
                ),
            ),
            V48RouteStage(
                "SCALP_PROTECTED_SWING_STOP",
                V48RouteStageRole.INVALIDATION,
                "STRUCTURAL",
                True,
                "A logical route-valid protected swing anchors the stop.",
            ),
            V48RouteStage(
                "SCALP_HTF_OBJECTIVE",
                V48RouteStageRole.TARGET,
                "HTF",
                True,
                "Target is based on higher-timeframe objectives.",
            ),
        ),
        session_binding_explicit=False,
    ),
    V48HumanDecisionRoute(
        route=V48Route.FAILURE_TO_MANIPULATE,
        session=V48Session.GENERIC,
        source_url="https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        thesis=(
            "After a level is taken, do not force the expected reversal. If reversal structure "
            "fails to confirm and continuation structure forms with HTF bias, trade continuation."
        ),
        stages=(
            V48RouteStage(
                "FTM_HTF_REASON",
                V48RouteStageRole.NARRATIVE,
                "HTF",
                True,
                "Higher-timeframe bias supplies the reason; FTM is not standalone.",
            ),
            V48RouteStage(
                "FTM_LEVEL_TAKEN",
                V48RouteStageRole.STRUCTURE,
                "ANY",
                True,
                "Relevant high/low is taken.",
            ),
            V48RouteStage(
                "FTM_EXPECTED_REVERSAL_NOT_CONFIRMED",
                V48RouteStageRole.STRUCTURE,
                "LTF",
                True,
                "Expected reversal fails to form after candle-close confirmation.",
            ),
            V48RouteStage(
                "FTM_CONTINUATION_STRUCTURE",
                V48RouteStageRole.EXECUTION,
                "LTF",
                True,
                "New continuation/protected-swing structure confirms the actionable thesis.",
            ),
            V48RouteStage(
                "FTM_PROTECTED_SWING_STOP",
                V48RouteStageRole.INVALIDATION,
                "LTF/STRUCTURAL",
                True,
                "New continuation protected swing provides invalidation.",
            ),
            V48RouteStage(
                "FTM_HTF_OBJECTIVE",
                V48RouteStageRole.TARGET,
                "HTF",
                True,
                "Continuation participates toward a higher-timeframe objective.",
            ),
        ),
        session_binding_explicit=False,
    ),
)


@dataclass(frozen=True, slots=True)
class V48DecisionGraph:
    identity: str = IDENTITY
    routes: tuple[V48HumanDecisionRoute, ...] = ROUTES
    global_entry_and_gate_allowed: bool = False
    source_route_may_be_forced_into_other_route: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 human decision graph identity is frozen")
        route_ids = tuple(route.route for route in self.routes)
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("each V48 route must be unique")
        if self.global_entry_and_gate_allowed:
            raise ValueError("V48 forbids collapsing alternatives into a global AND gate")
        if self.source_route_may_be_forced_into_other_route:
            raise ValueError("V48 route identity must remain independent")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("V48 human decision graph is pre-economic")


V48_HUMAN_DECISION_GRAPH = V48DecisionGraph()


def shared_required_stage_ids(routes: tuple[V48HumanDecisionRoute, ...] = ROUTES) -> frozenset[str]:
    """Return literal stage IDs shared by every route.

    Empty/near-empty output is useful evidence against one monolithic stage-level AND.
    Semantic invariants should instead be represented by role/meaning, not by forcing
    every route through identical timeframes and entry objects.
    """

    if not routes:
        return frozenset()
    common = {stage.stage_id for stage in routes[0].stages if stage.required}
    for route in routes[1:]:
        common &= {stage.stage_id for stage in route.stages if stage.required}
    return frozenset(common)
