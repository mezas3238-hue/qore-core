"""Causal regime-adaptive CE2I tool selection for CIBO CMA.

The selector narrows the account-mission tool surface using only contemporaneous
account/market/provider state. It never sizes a Trader and never uses future
outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboRegimePosture(StrEnum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEFENSIVE = "DEFENSIVE"
    RECOVERY = "RECOVERY"
    HALT_NEW_CAPITAL = "HALT_NEW_CAPITAL"


class LiquidityState(StrEnum):
    NORMAL = "NORMAL"
    THIN = "THIN"
    STRESSED = "STRESSED"


class VolatilityState(StrEnum):
    COMPRESSED = "COMPRESSED"
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    DISLOCATED = "DISLOCATED"


class CorrelationState(StrEnum):
    NORMAL = "NORMAL"
    CONCENTRATED = "CONCENTRATED"
    BREAK = "BREAK"


class ProviderCondition(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class CiboCapitalRegimeState:
    liquidity: LiquidityState
    volatility: VolatilityState
    correlation: CorrelationState
    provider_condition: ProviderCondition
    risk_utilization: Decimal
    margin_utilization: Decimal
    drawdown_utilization: Decimal
    opportunity_count: int
    position_path_adverse: bool = False
    evidence_stale: bool = False

    def __post_init__(self) -> None:
        for name, enum_type in (
            ("liquidity", LiquidityState),
            ("volatility", VolatilityState),
            ("correlation", CorrelationState),
            ("provider_condition", ProviderCondition),
        ):
            if type(getattr(self, name)) is not enum_type:
                raise CiboCapitalManagementError(
                    f"{name} must use canonical enum"
                )
        for name in (
            "risk_utilization",
            "margin_utilization",
            "drawdown_utilization",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite Decimal in [0, 1]"
                )
        if (
            not isinstance(self.opportunity_count, int)
            or isinstance(self.opportunity_count, bool)
            or self.opportunity_count < 0
        ):
            raise CiboCapitalManagementError(
                "opportunity_count must be non-negative int"
            )
        for name in ("position_path_adverse", "evidence_stale"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")


@dataclass(frozen=True, slots=True)
class CiboRegimeToolSelection:
    posture: CiboRegimePosture
    enabled_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "posture must be CiboRegimePosture"
            )
        if set(self.enabled_tools) & set(self.blocked_tools):
            raise CiboCapitalManagementError(
                "tool cannot be enabled and blocked simultaneously"
            )
        if not self.reason:
            raise CiboCapitalManagementError("selection reason required")


_NEW_CAPITAL_TOOLS = frozenset({"T01", "T06", "T07", "T09", "T18"})
_EXPANSION_TOOLS = frozenset({"T06", "T07", "T09", "T18"})
_RECOVERY_SAFE_TOOLS = frozenset({"T11", "T13", "T14", "T15", "T20"})


def select_ce2i_tools_for_regime(
    *,
    mission: CiboCapitalMissionPolicy,
    state: CiboCapitalRegimeState,
) -> CiboRegimeToolSelection:
    """Narrow mission-eligible CE2I tools from current causal regime evidence."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "state must be CiboCapitalRegimeState"
        )

    mission_tools = eligible_ce2i_tool_codes_for_mission(mission)
    posture, reason = _posture(state)
    enabled = set(mission_tools)

    if posture is CiboRegimePosture.HALT_NEW_CAPITAL:
        enabled &= {"T20"}
    elif posture is CiboRegimePosture.RECOVERY:
        enabled &= _RECOVERY_SAFE_TOOLS
    elif posture is CiboRegimePosture.DEFENSIVE:
        enabled -= _EXPANSION_TOOLS

    if (
        state.provider_condition is not ProviderCondition.HEALTHY
        or state.liquidity is LiquidityState.STRESSED
    ):
        enabled -= _NEW_CAPITAL_TOOLS

    if state.correlation is CorrelationState.BREAK:
        enabled -= {"T08", "T09", "T16", "T18"}

    if state.opportunity_count < 2:
        enabled -= {"T09", "T18"}

    ordered_enabled = tuple(
        code for code in mission_tools if code in enabled
    )
    ordered_blocked = tuple(
        code for code in mission_tools if code not in enabled
    )
    return CiboRegimeToolSelection(
        posture=posture,
        enabled_tools=ordered_enabled,
        blocked_tools=ordered_blocked,
        reason=reason,
    )


def _posture(
    state: CiboCapitalRegimeState,
) -> tuple[CiboRegimePosture, str]:
    if state.evidence_stale:
        return (
            CiboRegimePosture.HALT_NEW_CAPITAL,
            "regime evidence stale; new capital fails closed",
        )
    if state.provider_condition is ProviderCondition.UNAVAILABLE:
        return (
            CiboRegimePosture.HALT_NEW_CAPITAL,
            "provider unavailable; only capital release remains eligible",
        )
    if (
        state.drawdown_utilization >= Decimal("0.75")
        or state.risk_utilization >= Decimal("0.85")
        or state.volatility is VolatilityState.DISLOCATED
        or state.correlation is CorrelationState.BREAK
    ):
        return (
            CiboRegimePosture.RECOVERY,
            "account/market state requires recovery-first capital posture",
        )
    if (
        state.provider_condition is ProviderCondition.DEGRADED
        or state.liquidity is LiquidityState.STRESSED
        or state.drawdown_utilization >= Decimal("0.50")
        or state.risk_utilization >= Decimal("0.70")
        or state.margin_utilization >= Decimal("0.80")
        or state.position_path_adverse
    ):
        return (
            CiboRegimePosture.DEFENSIVE,
            "current state requires defensive capital posture",
        )
    if (
        state.liquidity is LiquidityState.THIN
        or state.volatility is VolatilityState.ELEVATED
        or state.correlation is CorrelationState.CONCENTRATED
        or state.opportunity_count >= 3
    ):
        return (
            CiboRegimePosture.WATCH,
            "current state requires heightened capital observation",
        )
    return (
        CiboRegimePosture.STABLE,
        "current state supports normal mission-eligible CE2I surface",
    )
