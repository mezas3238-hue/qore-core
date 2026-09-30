"""Translate applied advanced CE2I decisions into capital-action proposals.

This layer makes advanced tools operationally consumable without granting broker
mutation authority. It also exposes the safe portfolio credits that may alter
the allocator budget before QORE Risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDecision,
    AdvancedToolDisposition,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    FullCe2iSurfaceAssessment,
)


class AdvancedCapitalActionType(StrEnum):
    SCALE_OPPORTUNITY = "SCALE_OPPORTUNITY"
    SUBSTITUTE_MARGIN_EXPRESSION = "SUBSTITUTE_MARGIN_EXPRESSION"
    SELECT_RISK_EFFICIENT_POLICY = "SELECT_RISK_EFFICIENT_POLICY"
    APPLY_PORTFOLIO_NETTING = "APPLY_PORTFOLIO_NETTING"
    SELECT_CAPITAL_VELOCITY_POLICY = "SELECT_CAPITAL_VELOCITY_POLICY"
    EXECUTE_RISK_TRANSFER = "EXECUTE_RISK_TRANSFER"
    SELECT_CONVEX_EXPRESSION = "SELECT_CONVEX_EXPRESSION"


_ACTION_BY_TOOL = {
    "T02": AdvancedCapitalActionType.SCALE_OPPORTUNITY,
    "T03": AdvancedCapitalActionType.SUBSTITUTE_MARGIN_EXPRESSION,
    "T04": AdvancedCapitalActionType.SELECT_RISK_EFFICIENT_POLICY,
    "T08": AdvancedCapitalActionType.APPLY_PORTFOLIO_NETTING,
    "T10": AdvancedCapitalActionType.SELECT_CAPITAL_VELOCITY_POLICY,
    "T16": AdvancedCapitalActionType.EXECUTE_RISK_TRANSFER,
    "T17": AdvancedCapitalActionType.SELECT_CONVEX_EXPRESSION,
}


@dataclass(frozen=True, slots=True)
class AdvancedCapitalActionProposal:
    tool_code: str
    action_type: AdvancedCapitalActionType
    selected_id: str
    signal_fingerprint: str | None
    approved_volume: Decimal
    target_stop_risk_usd: Decimal | None
    target_margin_usd: Decimal | None
    risk_capacity_credit_usd: Decimal
    margin_capacity_credit_usd: Decimal
    score: Decimal | None
    broker_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if self.tool_code not in _ACTION_BY_TOOL:
            raise CiboCapitalManagementError(
                "advanced capital action tool code is unsupported"
            )
        if self.action_type is not _ACTION_BY_TOOL[self.tool_code]:
            raise CiboCapitalManagementError(
                "advanced capital action type/tool mismatch"
            )
        if not self.selected_id:
            raise CiboCapitalManagementError(
                "advanced capital action selected id is required"
            )
        for name in (
            "approved_volume",
            "risk_capacity_credit_usd",
            "margin_capacity_credit_usd",
        ):
            _nonnegative(getattr(self, name), name)
        for name in ("target_stop_risk_usd", "target_margin_usd"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative(value, name)
        if self.score is not None:
            if not isinstance(self.score, Decimal) or not self.score.is_finite():
                raise CiboCapitalManagementError(
                    "advanced capital action score must be finite Decimal"
                )
        if type(self.broker_mutation_authorized) is not bool:
            raise CiboCapitalManagementError(
                "advanced capital action broker flag must be bool"
            )
        if self.broker_mutation_authorized:
            raise CiboCapitalManagementError(
                "advanced research action cannot authorize broker mutation"
            )


@dataclass(frozen=True, slots=True)
class AdvancedCapitalBudgetAdjustment:
    risk_capacity_credit_usd: Decimal
    margin_capacity_credit_usd: Decimal

    def __post_init__(self) -> None:
        _nonnegative(
            self.risk_capacity_credit_usd,
            "risk_capacity_credit_usd",
        )
        _nonnegative(
            self.margin_capacity_credit_usd,
            "margin_capacity_credit_usd",
        )


def build_advanced_capital_actions(
    surface: FullCe2iSurfaceAssessment,
) -> tuple[AdvancedCapitalActionProposal, ...]:
    if not isinstance(surface, FullCe2iSurfaceAssessment):
        raise CiboCapitalManagementError(
            "advanced capital actions require full CE2I surface"
        )

    proposals: list[AdvancedCapitalActionProposal] = []
    for assessment in surface.opportunity_assessments:
        for decision in assessment.decisions:
            if decision.disposition is not AdvancedToolDisposition.APPLIED:
                continue
            proposals.append(
                _proposal(
                    decision,
                    signal_fingerprint=assessment.signal_fingerprint,
                )
            )
    for decision in surface.portfolio_decisions:
        if decision.disposition is not AdvancedToolDisposition.APPLIED:
            continue
        proposals.append(_proposal(decision, signal_fingerprint=None))

    expected = sum(
        1
        for decision in surface.advanced_decisions
        if decision.disposition is AdvancedToolDisposition.APPLIED
    )
    if len(proposals) != expected:
        raise CiboCapitalManagementError(
            "every applied advanced tool must produce exactly one action"
        )
    return tuple(proposals)


def advanced_portfolio_budget_adjustment(
    actions: tuple[AdvancedCapitalActionProposal, ...],
) -> AdvancedCapitalBudgetAdjustment:
    """Return only credits safe to apply globally before allocation.

    T08 true netting and T16 certified risk transfer may release stop-risk
    capacity at account level. Per-opportunity T03 margin reductions are not
    promoted to global margin headroom because that would double-count capacity
    before the corresponding opportunity is selected.
    """

    risk_credit = sum(
        (
            item.risk_capacity_credit_usd
            for item in actions
            if item.tool_code in {"T08", "T16"}
        ),
        Decimal(0),
    )
    return AdvancedCapitalBudgetAdjustment(
        risk_capacity_credit_usd=risk_credit,
        margin_capacity_credit_usd=Decimal(0),
    )


def _proposal(
    decision: AdvancedToolDecision,
    *,
    signal_fingerprint: str | None,
) -> AdvancedCapitalActionProposal:
    if decision.disposition is not AdvancedToolDisposition.APPLIED:
        raise CiboCapitalManagementError(
            "advanced action proposal requires APPLIED decision"
        )
    assert decision.selected_id is not None

    risk_credit = (
        decision.released_capacity_usd
        if decision.tool_code in {"T08", "T16"}
        else Decimal(0)
    )
    margin_credit = (
        decision.released_capacity_usd
        if decision.tool_code == "T03"
        else Decimal(0)
    )
    return AdvancedCapitalActionProposal(
        tool_code=decision.tool_code,
        action_type=_ACTION_BY_TOOL[decision.tool_code],
        selected_id=decision.selected_id,
        signal_fingerprint=signal_fingerprint,
        approved_volume=decision.approved_volume,
        target_stop_risk_usd=decision.target_stop_risk_usd,
        target_margin_usd=decision.target_margin_usd,
        risk_capacity_credit_usd=risk_credit,
        margin_capacity_credit_usd=margin_credit,
        score=decision.score,
    )


def _nonnegative(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"advanced capital action {name} must be finite non-negative Decimal"
        )
