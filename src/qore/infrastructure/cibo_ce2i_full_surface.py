"""Complete 20-tool CE2I surface coordinator.

This is the single research entry point that binds account mission, causal regime
selection and the formerly-missing advanced CE2I engines. It performs no broker
mutation and grants no Risk/execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedCe2iEvidenceBundle,
    AdvancedToolDecision,
    advanced_ce2i_engine_codes,
    evaluate_advanced_ce2i_surface,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimeToolSelection,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)


@dataclass(frozen=True, slots=True)
class FullCe2iSurfaceAssessment:
    mission_tools: tuple[str, ...]
    regime: CiboRegimeToolSelection
    advanced_decisions: tuple[AdvancedToolDecision, ...]
    registry_codes: tuple[str, ...]
    complete_registry: bool

    def __post_init__(self) -> None:
        if self.registry_codes != tuple(
            f"T{index:02d}" for index in range(1, 21)
        ):
            raise CiboCapitalManagementError(
                "CE2I registry must expose canonical T01..T20 order"
            )
        if not self.complete_registry:
            raise CiboCapitalManagementError(
                "full CE2I coordinator cannot bind incomplete registry"
            )
        if not set(self.regime.enabled_tools).issubset(set(self.mission_tools)):
            raise CiboCapitalManagementError(
                "regime surface cannot exceed account mission"
            )
        expected_advanced = tuple(
            code
            for code in advanced_ce2i_engine_codes()
            if code in self.regime.enabled_tools
        )
        actual_advanced = tuple(
            item.tool_code for item in self.advanced_decisions
        )
        if actual_advanced != expected_advanced:
            raise CiboCapitalManagementError(
                "advanced engine decisions do not match enabled regime surface"
            )


def evaluate_full_ce2i_surface(
    *,
    mission: CiboCapitalMissionPolicy,
    regime_state: CiboCapitalRegimeState,
    opportunity: TraderOpportunityEnvelope,
    advanced_evidence: AdvancedCe2iEvidenceBundle,
    current_volume: Decimal = Decimal(0),
    maximum_additional_volume: Decimal = Decimal(0),
) -> FullCe2iSurfaceAssessment:
    """Bind all 20 tool contracts and evaluate every enabled advanced engine."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "regime_state must be CiboCapitalRegimeState"
        )
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "opportunity must be TraderOpportunityEnvelope"
        )
    registry_codes = tuple(tool.code for tool in CE2I_TOOL_REGISTRY)
    complete_registry = (
        len(registry_codes) == 20
        and registry_codes == tuple(
            f"T{index:02d}" for index in range(1, 21)
        )
        and all(
            tool.maturity
            not in {ToolMaturity.ARCHITECTURE_ONLY, ToolMaturity.REJECTED}
            for tool in CE2I_TOOL_REGISTRY
        )
    )
    if not complete_registry:
        raise CiboCapitalManagementError(
            "CIBO full-surface evaluation requires 20/20 executable contracts"
        )

    mission_tools = eligible_ce2i_tool_codes_for_mission(mission)
    regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=regime_state,
    )
    advanced = evaluate_advanced_ce2i_surface(
        enabled_tools=regime.enabled_tools,
        opportunity=opportunity,
        evidence=advanced_evidence,
        current_volume=current_volume,
        maximum_additional_volume=maximum_additional_volume,
    )
    return FullCe2iSurfaceAssessment(
        mission_tools=mission_tools,
        regime=regime,
        advanced_decisions=advanced,
        registry_codes=registry_codes,
        complete_registry=True,
    )
