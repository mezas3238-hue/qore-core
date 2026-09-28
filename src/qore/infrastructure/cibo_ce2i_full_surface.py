"""Complete 20-tool CE2I portfolio coordinator.

This is the single research entry point that binds account mission, causal regime
selection, per-opportunity advanced engines and portfolio-level advanced engines.
It performs no broker mutation and grants no Risk/execution authority.
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
    CapitalVelocityEvidence,
    ConvexExposureEvidence,
    HedgedExposureEvidence,
    MarginEfficiencyEvidence,
    PortfolioNettingEvidence,
    RiskEfficiencyEvidence,
    StructuralLeverageEvidence,
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

_OPPORTUNITY_ADVANCED = ("T02", "T03", "T04", "T17")
_PORTFOLIO_ADVANCED = ("T08", "T10", "T16")


@dataclass(frozen=True, slots=True)
class AdvancedOpportunityEvidence:
    signal_fingerprint: str
    current_volume: Decimal = Decimal(0)
    maximum_additional_volume: Decimal = Decimal(0)
    structural_leverage: StructuralLeverageEvidence | None = None
    margin_efficiency: MarginEfficiencyEvidence | None = None
    risk_efficiency: RiskEfficiencyEvidence | None = None
    convex_exposure: ConvexExposureEvidence | None = None

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "advanced opportunity signal fingerprint required"
            )
        for name in ("current_volume", "maximum_additional_volume"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )


@dataclass(frozen=True, slots=True)
class AdvancedPortfolioEvidence:
    opportunities: tuple[AdvancedOpportunityEvidence, ...] = ()
    portfolio_netting: PortfolioNettingEvidence | None = None
    capital_velocity: CapitalVelocityEvidence | None = None
    hedged_exposure: HedgedExposureEvidence | None = None

    def __post_init__(self) -> None:
        ids = tuple(item.signal_fingerprint for item in self.opportunities)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "advanced opportunity evidence fingerprints must be unique"
            )


@dataclass(frozen=True, slots=True)
class AdvancedOpportunityAssessment:
    signal_fingerprint: str
    decisions: tuple[AdvancedToolDecision, ...]

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "advanced opportunity assessment fingerprint required"
            )
        if any(item.tool_code not in _OPPORTUNITY_ADVANCED for item in self.decisions):
            raise CiboCapitalManagementError(
                "opportunity assessment contains portfolio-level tool"
            )


@dataclass(frozen=True, slots=True)
class FullCe2iSurfaceAssessment:
    mission_tools: tuple[str, ...]
    regime: CiboRegimeToolSelection
    opportunity_assessments: tuple[AdvancedOpportunityAssessment, ...]
    portfolio_decisions: tuple[AdvancedToolDecision, ...]
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
        if any(
            item.tool_code not in _PORTFOLIO_ADVANCED
            for item in self.portfolio_decisions
        ):
            raise CiboCapitalManagementError(
                "portfolio assessment contains opportunity-level tool"
            )

    @property
    def advanced_decisions(self) -> tuple[AdvancedToolDecision, ...]:
        return tuple(
            decision
            for assessment in self.opportunity_assessments
            for decision in assessment.decisions
        ) + self.portfolio_decisions


def evaluate_full_ce2i_surface(
    *,
    mission: CiboCapitalMissionPolicy,
    regime_state: CiboCapitalRegimeState,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    advanced_evidence: AdvancedPortfolioEvidence,
) -> FullCe2iSurfaceAssessment:
    """Bind all 20 tool contracts and evaluate enabled advanced engines."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "regime_state must be CiboCapitalRegimeState"
        )
    if not isinstance(advanced_evidence, AdvancedPortfolioEvidence):
        raise CiboCapitalManagementError(
            "advanced_evidence must be AdvancedPortfolioEvidence"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "regime opportunity_count must match opportunity set"
        )
    fingerprints = tuple(item.signal_fingerprint for item in opportunities)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "full CE2I opportunity fingerprints must be unique"
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
    evidence_by_signal = {
        item.signal_fingerprint: item
        for item in advanced_evidence.opportunities
    }
    opportunity_tools = tuple(
        code for code in _OPPORTUNITY_ADVANCED
        if code in regime.enabled_tools
    )
    assessments: list[AdvancedOpportunityAssessment] = []
    for opportunity in sorted(
        opportunities,
        key=lambda item: (
            item.trader_id.value,
            item.qore_symbol,
            item.signal_fingerprint,
        ),
    ):
        row = evidence_by_signal.get(opportunity.signal_fingerprint)
        bundle = AdvancedCe2iEvidenceBundle(
            structural_leverage=(
                row.structural_leverage if row is not None else None
            ),
            margin_efficiency=(
                row.margin_efficiency if row is not None else None
            ),
            risk_efficiency=(
                row.risk_efficiency if row is not None else None
            ),
            convex_exposure=(
                row.convex_exposure if row is not None else None
            ),
        )
        decisions = evaluate_advanced_ce2i_surface(
            enabled_tools=opportunity_tools,
            opportunity=opportunity,
            evidence=bundle,
            current_volume=(
                row.current_volume if row is not None else Decimal(0)
            ),
            maximum_additional_volume=(
                row.maximum_additional_volume
                if row is not None
                else Decimal(0)
            ),
        )
        assessments.append(
            AdvancedOpportunityAssessment(
                signal_fingerprint=opportunity.signal_fingerprint,
                decisions=decisions,
            )
        )

    portfolio_tools = tuple(
        code for code in _PORTFOLIO_ADVANCED
        if code in regime.enabled_tools
    )
    portfolio_decisions = evaluate_advanced_ce2i_surface(
        enabled_tools=portfolio_tools,
        opportunity=None,
        evidence=AdvancedCe2iEvidenceBundle(
            portfolio_netting=advanced_evidence.portfolio_netting,
            capital_velocity=advanced_evidence.capital_velocity,
            hedged_exposure=advanced_evidence.hedged_exposure,
        ),
    )
    return FullCe2iSurfaceAssessment(
        mission_tools=mission_tools,
        regime=regime,
        opportunity_assessments=tuple(assessments),
        portfolio_decisions=portfolio_decisions,
        registry_codes=registry_codes,
        complete_registry=True,
    )
