"""Non-certifying universal CIBO capability-lab orchestration.

This surface exists only to prove that the CE2I engines can be exercised
independently of certification scientific eligibility.  It never grants
broker, LIVE, real-capital, production, or merge authority and it never makes
fresh-OOS/generalization claims.

Certification policy remains unchanged.  CAPABILITY_LAB deliberately passes
scientific_eligibility=None so a reused/synthetic functional scenario can
exercise engine mechanics that certification correctly keeps SHADOW_ONLY or
terminal-disabled.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_actions import (
    AdvancedCapitalActionProposal,
    AdvancedCapitalBudgetAdjustment,
    advanced_portfolio_budget_adjustment,
    build_advanced_capital_actions,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedPortfolioEvidence,
    FullCe2iSurfaceAssessment,
    evaluate_full_ce2i_surface,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)

CAPABILITY_LAB = "CIBO_UNIVERSAL_CAPABILITY_LAB_V1"


@dataclass(frozen=True, slots=True)
class UniversalCapabilityLabResult:
    surface: FullCe2iSurfaceAssessment
    advanced_actions: tuple[AdvancedCapitalActionProposal, ...]
    portfolio_budget_adjustment: AdvancedCapitalBudgetAdjustment
    capability_lab_id: str = CAPABILITY_LAB
    scientific_certification_claimed: bool = False
    fresh_oos_generalization_claimed: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    productive_authority: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if self.capability_lab_id != CAPABILITY_LAB:
            raise ValueError("capability lab identity drift")
        if any(
            (
                self.scientific_certification_claimed,
                self.fresh_oos_generalization_claimed,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.productive_authority,
                self.production_authorized,
                self.merge_authorized,
            )
        ):
            raise ValueError("capability lab cannot grant productive authority")


def evaluate_universal_capability_lab(
    *,
    mission: CiboCapitalMissionPolicy,
    regime_state: CiboCapitalRegimeState,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    advanced_evidence: AdvancedPortfolioEvidence,
) -> UniversalCapabilityLabResult:
    """Exercise the complete advanced CE2I surface outside certification gates."""

    surface = evaluate_full_ce2i_surface(
        mission=mission,
        regime_state=regime_state,
        opportunities=opportunities,
        advanced_evidence=advanced_evidence,
        scientific_eligibility=None,
    )
    actions = build_advanced_capital_actions(surface)
    adjustment = advanced_portfolio_budget_adjustment(actions)
    return UniversalCapabilityLabResult(
        surface=surface,
        advanced_actions=actions,
        portfolio_budget_adjustment=adjustment,
        productive_authority=False,
    )
