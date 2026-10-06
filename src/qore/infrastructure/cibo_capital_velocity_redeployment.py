"""Event-driven T14/T20 capital velocity and redeployment research engine.

Consumes causal release events exactly once, classifies why released capacity is
idle, and identifies the best currently eligible alternative without granting
allocation, Risk or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboIdleCapitalClass,
    CiboObservedEconomicTwin,
    CiboObservedOpportunityState,
)


@dataclass(frozen=True, slots=True)
class CiboCapitalReleaseEvent:
    release_id: str
    released_at: datetime
    signal_fingerprint: str
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    source: str

    def __post_init__(self) -> None:
        if not self.release_id or not self.signal_fingerprint or not self.source:
            raise CiboCapitalManagementError(
                "Capital velocity release identity is required"
            )
        if self.released_at.tzinfo is None or self.released_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Capital velocity release time must be timezone-aware"
            )
        for name in ("released_stop_risk_usd", "released_margin_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Capital velocity {name} must be finite positive Decimal"
                )


@dataclass(frozen=True, slots=True)
class CiboCapitalVelocityLedger:
    consumed_release_ids: tuple[str, ...] = ()
    total_released_stop_risk_usd: Decimal = Decimal(0)
    total_released_margin_usd: Decimal = Decimal(0)
    total_redeployed_stop_risk_usd: Decimal = Decimal(0)
    total_redeployed_margin_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if len(self.consumed_release_ids) != len(set(self.consumed_release_ids)):
            raise CiboCapitalManagementError(
                "Capital velocity release ids must be unique"
            )
        for name in (
            "total_released_stop_risk_usd",
            "total_released_margin_usd",
            "total_redeployed_stop_risk_usd",
            "total_redeployed_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Capital velocity {name} must be finite non-negative Decimal"
                )
        if self.total_redeployed_stop_risk_usd > self.total_released_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Capital velocity cannot redeploy more risk than released"
            )
        if self.total_redeployed_margin_usd > self.total_released_margin_usd:
            raise CiboCapitalManagementError(
                "Capital velocity cannot redeploy more margin than released"
            )


@dataclass(frozen=True, slots=True)
class CiboRedeploymentProposal:
    release_id: str
    evaluated_at: datetime
    idle_classification: CiboIdleCapitalClass
    selected_option_id: str | None
    proposed_stop_risk_usd: Decimal
    proposed_margin_usd: Decimal
    expected_net_utility_usd: Decimal
    reason: str
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.release_id or not self.reason:
            raise CiboCapitalManagementError(
                "Redeployment proposal identity/reason required"
            )
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Redeployment evaluated_at must be timezone-aware"
            )
        for name in (
            "proposed_stop_risk_usd",
            "proposed_margin_usd",
            "expected_net_utility_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Redeployment {name} must be finite Decimal"
                )
        if self.proposed_stop_risk_usd < 0 or self.proposed_margin_usd < 0:
            raise CiboCapitalManagementError(
                "Redeployment proposed capacity cannot be negative"
            )
        if (
            self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Redeployment proposal cannot grant productive authority"
            )


def consume_release_once(
    ledger: CiboCapitalVelocityLedger,
    release: CiboCapitalReleaseEvent,
) -> CiboCapitalVelocityLedger:
    """Record one release exactly once; fail closed on double release."""

    if release.release_id in ledger.consumed_release_ids:
        raise CiboCapitalManagementError(
            "Capital velocity double release detected"
        )
    return CiboCapitalVelocityLedger(
        consumed_release_ids=ledger.consumed_release_ids + (release.release_id,),
        total_released_stop_risk_usd=(
            ledger.total_released_stop_risk_usd
            + release.released_stop_risk_usd
        ),
        total_released_margin_usd=(
            ledger.total_released_margin_usd
            + release.released_margin_usd
        ),
        total_redeployed_stop_risk_usd=ledger.total_redeployed_stop_risk_usd,
        total_redeployed_margin_usd=ledger.total_redeployed_margin_usd,
    )


def _eligible(
    item: CiboObservedOpportunityState,
    *,
    at: datetime,
) -> bool:
    return (
        item.known_at <= at
        and item.earliest_action_at <= at
        and item.expires_at > at
        and item.context_allowed
        and item.provider_viable
        and item.capital_source_eligible
        and item.expected_net_value_usd
        - item.provider_cost_usd
        - item.uncertainty_penalty
        > 0
    )


def propose_redeployment(
    *,
    twin: CiboObservedEconomicTwin,
    release: CiboCapitalReleaseEvent,
) -> CiboRedeploymentProposal:
    """Classify released capacity and select a causal superior use if present."""

    if twin.captured_at < release.released_at:
        raise CiboCapitalManagementError(
            "Redeployment Twin predates capital release"
        )

    eligible = tuple(
        item
        for item in twin.opportunities
        if _eligible(item, at=twin.captured_at)
        and item.stop_risk_usd <= release.released_stop_risk_usd
        and item.margin_usd <= release.released_margin_usd
    )
    if not eligible:
        has_future_or_waiting = any(
            item.known_at <= twin.captured_at
            and item.expires_at > twin.captured_at
            and item.earliest_action_at > twin.captured_at
            for item in twin.opportunities
        )
        classification = (
            CiboIdleCapitalClass.WAITING_FOR_BETTER_OPPORTUNITY
            if has_future_or_waiting
            else CiboIdleCapitalClass.NO_VALID_OPPORTUNITY
        )
        return CiboRedeploymentProposal(
            release_id=release.release_id,
            evaluated_at=twin.captured_at,
            idle_classification=classification,
            selected_option_id=None,
            proposed_stop_risk_usd=Decimal(0),
            proposed_margin_usd=Decimal(0),
            expected_net_utility_usd=Decimal(0),
            reason="no currently eligible causal opportunity fits released capacity",
        )

    def utility(item: CiboObservedOpportunityState) -> Decimal:
        return (
            item.expected_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
        ) / item.expected_capital_minutes

    winner = sorted(
        eligible,
        key=lambda item: (
            -utility(item),
            -(
                item.expected_net_value_usd
                - item.provider_cost_usd
                - item.uncertainty_penalty
            ),
            item.stop_risk_usd,
            item.margin_usd,
            item.option_id,
        ),
    )[0]
    return CiboRedeploymentProposal(
        release_id=release.release_id,
        evaluated_at=twin.captured_at,
        idle_classification=CiboIdleCapitalClass.UNNECESSARY_IDLE,
        selected_option_id=winner.option_id,
        proposed_stop_risk_usd=winner.stop_risk_usd,
        proposed_margin_usd=winner.margin_usd,
        expected_net_utility_usd=(
            winner.expected_net_value_usd
            - winner.provider_cost_usd
            - winner.uncertainty_penalty
        ),
        reason="released capacity has a currently eligible positive-utility causal use",
    )


def record_redeployment(
    ledger: CiboCapitalVelocityLedger,
    proposal: CiboRedeploymentProposal,
) -> CiboCapitalVelocityLedger:
    """Record research-attributed reuse without granting execution authority."""

    if proposal.selected_option_id is None:
        return ledger
    return CiboCapitalVelocityLedger(
        consumed_release_ids=ledger.consumed_release_ids,
        total_released_stop_risk_usd=ledger.total_released_stop_risk_usd,
        total_released_margin_usd=ledger.total_released_margin_usd,
        total_redeployed_stop_risk_usd=(
            ledger.total_redeployed_stop_risk_usd
            + proposal.proposed_stop_risk_usd
        ),
        total_redeployed_margin_usd=(
            ledger.total_redeployed_margin_usd
            + proposal.proposed_margin_usd
        ),
    )
