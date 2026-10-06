"""Aggregate efficiency telemetry for native Portfolio shadow decisions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    CompoundPortfolioShadowDecision,
)


@dataclass(frozen=True, slots=True)
class CiboPortfolioShadowEfficiencyReport:
    decision_count: int
    open_position_competition_count: int
    admitted_count: int
    release_proposal_count: int
    fits_without_release_count: int
    cumulative_proposed_released_stop_risk_usd: Decimal
    cumulative_proposed_released_margin_usd: Decimal
    cumulative_net_incremental_utility_usd: Decimal
    positive_net_incremental_count: int
    shadow_actuation_rate: Decimal
    primary_blocker: str
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_count",
            "open_position_competition_count",
            "admitted_count",
            "release_proposal_count",
            "fits_without_release_count",
            "positive_net_incremental_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"portfolio shadow efficiency {name} invalid"
                )
        for name in (
            "cumulative_proposed_released_stop_risk_usd",
            "cumulative_proposed_released_margin_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"portfolio shadow efficiency {name} invalid"
                )
        if (
            not isinstance(self.cumulative_net_incremental_utility_usd, Decimal)
            or not self.cumulative_net_incremental_utility_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "portfolio shadow cumulative utility must be finite Decimal"
            )
        if self.shadow_actuation_rate < 0 or self.shadow_actuation_rate > 1:
            raise CiboCapitalManagementError(
                "portfolio shadow actuation rate outside [0,1]"
            )
        if not self.primary_blocker:
            raise CiboCapitalManagementError(
                "portfolio shadow primary blocker required"
            )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "portfolio shadow sensor cannot use outcomes or authority"
            )


def _ratio(num: int, den: int) -> Decimal:
    if den <= 0:
        return Decimal(0)
    return Decimal(num) / Decimal(den)


def measure_portfolio_shadow_efficiency(
    decisions: tuple[CompoundPortfolioShadowDecision, ...],
) -> CiboPortfolioShadowEfficiencyReport:
    if any(
        not isinstance(item, CompoundPortfolioShadowDecision)
        for item in decisions
    ):
        raise CiboCapitalManagementError(
            "portfolio shadow sensor requires canonical decisions"
        )

    competition = tuple(
        item for item in decisions
        if item.position_competition_observed
        and item.open_position_count > 0
    )
    releases = tuple(
        item for item in competition
        if item.release_proposed
    )
    positive = tuple(
        item for item in competition
        if item.net_incremental_utility_usd > 0
    )

    if not decisions:
        blocker = "NO_PORTFOLIO_DECISIONS"
    elif not competition:
        blocker = "NO_OPEN_POSITION_COMPETITION"
    elif releases:
        blocker = "SHADOW_RELEASE_REQUIRES_EXECUTABLE_SETTLEMENT_EVIDENCE"
    elif positive:
        blocker = "POSITIVE_SHADOW_UTILITY_WITHOUT_RELEASE_REQUIREMENT"
    else:
        blocker = "NO_SUPERIOR_REPLACEMENT_IDENTIFIED"

    return CiboPortfolioShadowEfficiencyReport(
        decision_count=len(decisions),
        open_position_competition_count=len(competition),
        admitted_count=sum(item.admit_opportunity for item in decisions),
        release_proposal_count=len(releases),
        fits_without_release_count=sum(
            item.fits_without_release for item in decisions
        ),
        cumulative_proposed_released_stop_risk_usd=sum(
            (
                item.proposed_released_stop_risk_usd
                for item in releases
            ),
            Decimal(0),
        ),
        cumulative_proposed_released_margin_usd=sum(
            (
                item.proposed_released_margin_usd
                for item in releases
            ),
            Decimal(0),
        ),
        cumulative_net_incremental_utility_usd=sum(
            (
                item.net_incremental_utility_usd
                for item in competition
            ),
            Decimal(0),
        ),
        positive_net_incremental_count=len(positive),
        shadow_actuation_rate=_ratio(len(releases), len(competition)),
        primary_blocker=blocker,
        outcome_used=False,
        productive_authority=False,
    )
