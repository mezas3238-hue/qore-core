"""Architect-2 terminal recommendation for the PROVIDER_ECONOMICS workstream.

The legacy ledger asks for exact historical provider USD economics even though
the active Phase22 scientific contract explicitly separates two evidence planes:
historical market replay and real current cTrader DEMO execution calibration.

This module does not edit the canonical ledger and does not consume Phase22 V2.
It only makes the supersession lineage machine-readable for Integrator review.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    STATUS as PROVIDER_CALIBRATION_STATUS,
)

RECOMMENDATION = "SUPERSEDED_WITH_PROVEN_LINEAGE"
LEGACY_REQUIREMENT = "HISTORICAL_2017_PROVIDER_USD_ECONOMICS_UNAVAILABLE"
SUPERSEDING_CONTRACT = "CIBO_PHASE22_DUAL_EVIDENCE_QUALIFICATION_PLAN_V2"


@dataclass(frozen=True, slots=True)
class ProviderEconomicsTerminalRecommendation:
    workstream_id: str
    recommendation: str
    legacy_requirement: str
    superseding_contract: str
    current_empirical_provider_plane_ready: bool
    historical_market_plane_required: bool
    predeclared_provider_cost_application_required: bool
    historical_provider_fill_claims_forbidden: bool
    historical_provider_order_refs_forbidden: bool
    historical_provider_deal_refs_forbidden: bool
    historical_provider_settlement_claims_forbidden: bool
    exact_historical_provider_economics_claimed: bool
    holdout_outcomes_used: bool
    terminal_disposition_assigned: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id != "PROVIDER_ECONOMICS":
            raise CiboCapitalManagementError(
                "provider economics terminal recommendation identity drift"
            )
        if self.recommendation != RECOMMENDATION:
            raise CiboCapitalManagementError(
                "provider economics recommendation drift"
            )
        if self.legacy_requirement != LEGACY_REQUIREMENT:
            raise CiboCapitalManagementError(
                "provider economics legacy requirement drift"
            )
        if self.superseding_contract != SUPERSEDING_CONTRACT:
            raise CiboCapitalManagementError(
                "provider economics superseding contract drift"
            )
        required_true = (
            self.current_empirical_provider_plane_ready,
            self.historical_market_plane_required,
            self.predeclared_provider_cost_application_required,
            self.historical_provider_fill_claims_forbidden,
            self.historical_provider_order_refs_forbidden,
            self.historical_provider_deal_refs_forbidden,
            self.historical_provider_settlement_claims_forbidden,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "provider economics supersession cannot weaken evidence planes"
            )
        if (
            self.exact_historical_provider_economics_claimed
            or self.holdout_outcomes_used
            or self.terminal_disposition_assigned
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "provider economics supersession governance contamination"
            )


def build_provider_economics_terminal_recommendation(
) -> ProviderEconomicsTerminalRecommendation:
    receipt = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT
    plan = PHASE22_DUAL_EVIDENCE_PLAN

    current_ready = (
        PROVIDER_CALIBRATION_STATUS == "READY"
        and receipt.execution_population_ready
        and receipt.empirical_slippage_calibrated
        and receipt.execution_model_ready
        and receipt.created_positions_closed
        and receipt.minimum_volume_only
        and not receipt.blockers
        and not receipt.historical_provider_economics_claimed
        and not receipt.historical_holdout_execution_claimed
        and not receipt.holdout_outcomes_used
        and not receipt.productive_authority
        and plan.activation_ready
        and plan.empirical_provider_calibration_ready
    )

    return ProviderEconomicsTerminalRecommendation(
        workstream_id="PROVIDER_ECONOMICS",
        recommendation=RECOMMENDATION,
        legacy_requirement=LEGACY_REQUIREMENT,
        superseding_contract=SUPERSEDING_CONTRACT,
        current_empirical_provider_plane_ready=current_ready,
        historical_market_plane_required=plan.require_historical_holdout_market_plane,
        predeclared_provider_cost_application_required=(
            plan.require_predeclared_provider_cost_application
        ),
        historical_provider_fill_claims_forbidden=(
            plan.forbid_historical_provider_fill_claims
        ),
        historical_provider_order_refs_forbidden=(
            plan.forbid_historical_provider_order_refs
        ),
        historical_provider_deal_refs_forbidden=(
            plan.forbid_historical_provider_deal_refs
        ),
        historical_provider_settlement_claims_forbidden=(
            plan.forbid_historical_provider_settlement_claims
        ),
        exact_historical_provider_economics_claimed=False,
        holdout_outcomes_used=False,
        terminal_disposition_assigned=False,
        productive_authority=False,
    )
