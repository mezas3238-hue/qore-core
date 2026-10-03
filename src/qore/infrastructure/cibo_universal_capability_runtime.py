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
    CapitalAction,
    CapitalSource,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    CiboCapabilityCognitiveCoverageReceipt,
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
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_t11_runtime_guard import (
    evaluate_t11_runtime_exposure_guard,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicEnvelope,
)

CAPABILITY_LAB = "CIBO_UNIVERSAL_CAPABILITY_LAB_V1"


@dataclass(frozen=True, slots=True)
class CapabilityLabRuntimeInputs:
    realized_profit_state: CiboCapitalState
    protected_capacity_state: CiboCapitalState
    provider_envelopes: tuple[tuple[str, ProviderEconomicEnvelope], ...]
    derisk_inputs: tuple[tuple[str, CiboDeRiskingInput], ...]

    def __post_init__(self) -> None:
        provider_symbols = tuple(symbol for symbol, _ in self.provider_envelopes)
        derisk_signals = tuple(signal for signal, _ in self.derisk_inputs)
        if len(provider_symbols) != len(set(provider_symbols)):
            raise ValueError("capability lab provider symbols must be unique")
        if len(derisk_signals) != len(set(derisk_signals)):
            raise ValueError("capability lab derisk signals must be unique")
        if any(
            not isinstance(envelope, ProviderEconomicEnvelope)
            for _, envelope in self.provider_envelopes
        ):
            raise ValueError("capability lab provider envelope invalid")
        if any(
            not isinstance(item, CiboDeRiskingInput)
            for _, item in self.derisk_inputs
        ):
            raise ValueError("capability lab derisk input invalid")


@dataclass(frozen=True, slots=True)
class CapabilityLabToolReceipt:
    tool_code: str
    applied_count: int
    fail_closed_count: int
    detail: str

    def __post_init__(self) -> None:
        if self.tool_code not in {"T06", "T07", "T11", "T14"}:
            raise ValueError("capability lab runtime tool code invalid")
        if self.applied_count < 0 or self.fail_closed_count < 0:
            raise ValueError("capability lab runtime tool counts invalid")
        if not self.detail:
            raise ValueError("capability lab runtime tool detail required")

    @property
    def functional_pass(self) -> bool:
        return self.applied_count > 0


@dataclass(frozen=True, slots=True)
class UniversalCapabilityLabResult:
    cognitive_coverage: CiboCapabilityCognitiveCoverageReceipt
    surface: FullCe2iSurfaceAssessment
    advanced_actions: tuple[AdvancedCapitalActionProposal, ...]
    portfolio_budget_adjustment: AdvancedCapitalBudgetAdjustment
    runtime_tool_receipts: tuple[CapabilityLabToolReceipt, ...]
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
        if (
            not isinstance(
                self.cognitive_coverage,
                CiboCapabilityCognitiveCoverageReceipt,
            )
            or not self.cognitive_coverage.complete
        ):
            raise ValueError("capability lab requires complete CF01..CF19 coverage")
        expected_runtime_codes = ("T06", "T07", "T11", "T14")
        if tuple(
            item.tool_code for item in self.runtime_tool_receipts
        ) != expected_runtime_codes:
            raise ValueError(
                "capability lab requires exact T06/T07/T11/T14 receipts"
            )
        if any(not item.functional_pass for item in self.runtime_tool_receipts):
            raise ValueError(
                "capability lab runtime tool functional probe failed"
            )
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
    cognitive_coverage: CiboCapabilityCognitiveCoverageReceipt,
    runtime_inputs: CapabilityLabRuntimeInputs,
) -> UniversalCapabilityLabResult:
    """Exercise the complete advanced CE2I surface outside certification gates."""

    if (
        not isinstance(
            cognitive_coverage,
            CiboCapabilityCognitiveCoverageReceipt,
        )
        or not cognitive_coverage.complete
    ):
        raise ValueError("capability lab requires complete cognitive coverage")

    if not isinstance(runtime_inputs, CapabilityLabRuntimeInputs):
        raise ValueError("capability lab requires runtime tool inputs")

    provider_by_symbol = dict(runtime_inputs.provider_envelopes)
    derisk_by_signal = dict(runtime_inputs.derisk_inputs)

    t06_applied = t06_failed = 0
    t07_applied = t07_failed = 0
    t11_applied = t11_failed = 0
    t14_applied = t14_failed = 0

    for opportunity in opportunities:
        t06 = plan_self_financing_expansion(
            opportunity,
            runtime_inputs.realized_profit_state,
        )
        if (
            t06.action is CapitalAction.EXPAND
            and t06.capital_source is CapitalSource.REALIZED_PROFIT
        ):
            t06_applied += 1
        else:
            t06_failed += 1

        t07 = plan_self_financing_expansion(
            opportunity,
            runtime_inputs.protected_capacity_state,
        )
        if (
            t07.action is CapitalAction.EXPAND
            and t07.capital_source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
        ):
            t07_applied += 1
        else:
            t07_failed += 1

        envelope = provider_by_symbol.get(opportunity.qore_symbol)
        if envelope is None:
            t11_failed += 1
        else:
            t11 = evaluate_t11_runtime_exposure_guard(
                qore_symbol=opportunity.qore_symbol,
                requested_volume=opportunity.minimum_volume,
                provider_envelope=envelope,
                gross_edge_model_ready=True,
                market_impact_model_ready=True,
            )
            if t11.advanced_exposure_authorized:
                t11_applied += 1
            else:
                t11_failed += 1

        derisk = derisk_by_signal.get(opportunity.signal_fingerprint)
        if derisk is None:
            t14_failed += 1
        else:
            t14 = plan_dynamic_derisking(derisk)
            if t14.action in {
                CiboDeRiskAction.REDUCE,
                CiboDeRiskAction.RELEASE_ALL,
            }:
                t14_applied += 1
            else:
                t14_failed += 1

    runtime_tool_receipts = (
        CapabilityLabToolReceipt(
            tool_code="T06",
            applied_count=t06_applied,
            fail_closed_count=t06_failed,
            detail="realized-profit expansion functional probe",
        ),
        CapabilityLabToolReceipt(
            tool_code="T07",
            applied_count=t07_applied,
            fail_closed_count=t07_failed,
            detail="protected-capacity expansion functional probe",
        ),
        CapabilityLabToolReceipt(
            tool_code="T11",
            applied_count=t11_applied,
            fail_closed_count=t11_failed,
            detail="execution-efficient exposure functional probe",
        ),
        CapabilityLabToolReceipt(
            tool_code="T14",
            applied_count=t14_applied,
            fail_closed_count=t14_failed,
            detail="dynamic de-risking functional probe",
        ),
    )

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
        cognitive_coverage=cognitive_coverage,
        surface=surface,
        advanced_actions=actions,
        portfolio_budget_adjustment=adjustment,
        runtime_tool_receipts=runtime_tool_receipts,
        productive_authority=False,
    )
