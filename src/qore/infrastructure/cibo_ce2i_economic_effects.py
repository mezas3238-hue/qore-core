"""Apply authorized advanced CE2I decisions to the economic allocation inputs.

This module is the causal seam that was missing from the historical replay:
advanced CE2I decisions were previously recorded but did not modify the
candidate/budget actually seen by MPC/T09/T18. Only decisions already marked
APPLIED by their evidence contracts and with a safe economic binding are allowed
to change economics here.

No Trader logic, QORE Risk authority, broker state, or outcome-aware tuning is
introduced.  Capacity releases are conservatively non-additive across portfolio
mechanisms to avoid double counting overlapping risk-transfer claims.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    FullCe2iSurfaceAssessment,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)


@dataclass(frozen=True, slots=True)
class AdvancedCe2iCandidateEconomicEffect:
    signal_fingerprint: str
    tool_code: str
    field_name: str
    before_usd: Decimal
    after_usd: Decimal
    reason: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.tool_code or not self.field_name:
            raise CiboCapitalManagementError(
                "advanced CE2I candidate economic effect identity required"
            )
        for name in ("before_usd", "after_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"advanced CE2I effect {name} must be finite non-negative Decimal"
                )
        if not self.reason:
            raise CiboCapitalManagementError(
                "advanced CE2I candidate economic effect reason required"
            )


@dataclass(frozen=True, slots=True)
class AdvancedCe2iPortfolioEconomicEffect:
    tool_code: str
    released_risk_capacity_usd: Decimal
    reason: str

    def __post_init__(self) -> None:
        if not self.tool_code or not self.reason:
            raise CiboCapitalManagementError(
                "advanced CE2I portfolio economic effect identity required"
            )
        if (
            not isinstance(self.released_risk_capacity_usd, Decimal)
            or not self.released_risk_capacity_usd.is_finite()
            or self.released_risk_capacity_usd < 0
        ):
            raise CiboCapitalManagementError(
                "advanced CE2I released risk capacity must be finite non-negative"
            )


@dataclass(frozen=True, slots=True)
class AdvancedCe2iEconomicApplication:
    candidates: tuple[CapitalOpportunityCandidate, ...]
    effective_hard_risk_headroom_usd: Decimal
    effective_margin_headroom_usd: Decimal
    candidate_effects: tuple[AdvancedCe2iCandidateEconomicEffect, ...]
    portfolio_effects: tuple[AdvancedCe2iPortfolioEconomicEffect, ...]
    conservative_portfolio_credit_usd: Decimal

    def __post_init__(self) -> None:
        for name in (
            "effective_hard_risk_headroom_usd",
            "effective_margin_headroom_usd",
            "conservative_portfolio_credit_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"advanced CE2I economic application {name} invalid"
                )


def apply_advanced_ce2i_economic_effects(
    *,
    candidates: tuple[CapitalOpportunityCandidate, ...],
    full_surface: FullCe2iSurfaceAssessment,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
) -> AdvancedCe2iEconomicApplication:
    """Bind authorized T03/T08/T16 effects into allocation economics.

    T04 remains observational here because changing true stop risk without
    rebuilding the causal expectation would create an internally inconsistent
    candidate.  It may be promoted only with an explicit expectation-repricing
    contract.
    """

    if not isinstance(full_surface, FullCe2iSurfaceAssessment):
        raise CiboCapitalManagementError(
            "advanced CE2I economic application requires full surface"
        )
    for name, value in (
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise CiboCapitalManagementError(f"{name} invalid")

    by_signal = {item.signal_fingerprint: item for item in candidates}
    if len(by_signal) != len(candidates):
        raise CiboCapitalManagementError(
            "advanced CE2I economic application duplicate candidate fingerprint"
        )

    effects: list[AdvancedCe2iCandidateEconomicEffect] = []
    adjusted: dict[str, CapitalOpportunityCandidate] = dict(by_signal)

    for assessment in full_surface.opportunity_assessments:
        candidate = adjusted.get(assessment.signal_fingerprint)
        if candidate is None:
            raise CiboCapitalManagementError(
                "advanced CE2I assessment/candidate lineage drift"
            )
        for decision in assessment.decisions:
            if decision.disposition is not AdvancedToolDisposition.APPLIED:
                continue
            if decision.tool_code == "T03":
                target = decision.target_margin_usd
                if target is None:
                    raise CiboCapitalManagementError(
                        "applied T03 must carry target_margin_usd"
                    )
                if target > candidate.margin_usd:
                    raise CiboCapitalManagementError(
                        "T03 cannot increase candidate margin in economic reducer"
                    )
                if target < candidate.margin_usd:
                    effects.append(
                        AdvancedCe2iCandidateEconomicEffect(
                            signal_fingerprint=candidate.signal_fingerprint,
                            tool_code="T03",
                            field_name="margin_usd",
                            before_usd=candidate.margin_usd,
                            after_usd=target,
                            reason=decision.reason,
                        )
                    )
                    candidate = replace(candidate, margin_usd=target)
        adjusted[candidate.signal_fingerprint] = candidate

    portfolio_effects: list[AdvancedCe2iPortfolioEconomicEffect] = []
    credits: list[Decimal] = []
    for decision in full_surface.portfolio_decisions:
        if decision.disposition is not AdvancedToolDisposition.APPLIED:
            continue
        if decision.tool_code not in {"T08", "T16"}:
            continue
        if decision.released_capacity_usd <= 0:
            continue
        credits.append(decision.released_capacity_usd)
        portfolio_effects.append(
            AdvancedCe2iPortfolioEconomicEffect(
                tool_code=decision.tool_code,
                released_risk_capacity_usd=decision.released_capacity_usd,
                reason=decision.reason,
            )
        )

    # T08 true netting and T16 hedge transfer may describe overlapping economic
    # risk.  Until an independence proof exists, consume only the largest single
    # verified credit rather than summing them.
    credit = max(credits, default=Decimal(0))
    ordered_candidates = tuple(
        adjusted[item.signal_fingerprint] for item in candidates
    )
    return AdvancedCe2iEconomicApplication(
        candidates=ordered_candidates,
        effective_hard_risk_headroom_usd=hard_risk_headroom_usd + credit,
        effective_margin_headroom_usd=margin_headroom_usd,
        candidate_effects=tuple(effects),
        portfolio_effects=tuple(portfolio_effects),
        conservative_portfolio_credit_usd=credit,
    )
