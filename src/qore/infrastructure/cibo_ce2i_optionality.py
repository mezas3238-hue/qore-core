"""CE2I T13/T15 reserve and capital-optionality intelligence.

The engine values unused capacity from causal, already-known executable seed
requirements. It never predicts trade outcomes and never grants execution
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    CiboRegimeToolSelection,
)


@dataclass(frozen=True, slots=True)
class KnownCapitalOption:
    opportunity_id: str
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal

    def __post_init__(self) -> None:
        if not self.opportunity_id:
            raise CiboCapitalManagementError(
                "known option opportunity_id required"
            )
        for name in ("minimum_stop_risk_usd", "minimum_margin_usd"):
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
class CiboOptionalityDecision:
    reserve_stop_risk_usd: Decimal
    reserve_margin_usd: Decimal
    deployable_stop_risk_usd: Decimal
    deployable_margin_usd: Decimal
    reserved_for_opportunity_ids: tuple[str, ...]
    preserve_new_capital: bool
    reason: str

    def __post_init__(self) -> None:
        for name in (
            "reserve_stop_risk_usd",
            "reserve_margin_usd",
            "deployable_stop_risk_usd",
            "deployable_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if type(self.preserve_new_capital) is not bool:
            raise CiboCapitalManagementError(
                "preserve_new_capital must be bool"
            )
        if not self.reason:
            raise CiboCapitalManagementError(
                "optionality decision reason required"
            )


def plan_capital_optionality(
    *,
    mission: CiboCapitalMissionPolicy,
    regime: CiboRegimeToolSelection,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    known_options: tuple[KnownCapitalOption, ...] = (),
) -> CiboOptionalityDecision:
    """Reserve capacity without inventing future edge or future outcomes."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(regime, CiboRegimeToolSelection):
        raise CiboCapitalManagementError(
            "regime must be CiboRegimeToolSelection"
        )
    for name, value in (
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )
    ids = tuple(item.opportunity_id for item in known_options)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "known optionality opportunity ids must be unique"
        )

    if regime.posture in {
        CiboRegimePosture.RECOVERY,
        CiboRegimePosture.HALT_NEW_CAPITAL,
    }:
        return CiboOptionalityDecision(
            reserve_stop_risk_usd=hard_risk_headroom_usd,
            reserve_margin_usd=margin_headroom_usd,
            deployable_stop_risk_usd=Decimal(0),
            deployable_margin_usd=Decimal(0),
            reserved_for_opportunity_ids=ids,
            preserve_new_capital=True,
            reason="recovery/halt posture preserves all remaining new-capital capacity",
        )

    if not known_options:
        return CiboOptionalityDecision(
            reserve_stop_risk_usd=Decimal(0),
            reserve_margin_usd=Decimal(0),
            deployable_stop_risk_usd=hard_risk_headroom_usd,
            deployable_margin_usd=margin_headroom_usd,
            reserved_for_opportunity_ids=(),
            preserve_new_capital=False,
            reason="no known executable future option requires reserved capacity",
        )

    selected: tuple[KnownCapitalOption, ...]
    if mission.preserve_optionality_priority:
        # Preserve enough capacity to express any one currently known option.
        risk_requirement = max(
            item.minimum_stop_risk_usd for item in known_options
        )
        margin_requirement = max(
            item.minimum_margin_usd for item in known_options
        )
        selected = known_options
        reason = (
            "mission preserves capacity sufficient for any one known "
            "minimum executable opportunity"
        )
    elif regime.posture is CiboRegimePosture.DEFENSIVE:
        # Capability-discovery accounts still preserve one cheapest future option
        # when current conditions have already become defensive.
        selected_item = min(
            known_options,
            key=lambda item: (
                item.minimum_stop_risk_usd,
                item.minimum_margin_usd,
                item.opportunity_id,
            ),
        )
        risk_requirement = selected_item.minimum_stop_risk_usd
        margin_requirement = selected_item.minimum_margin_usd
        selected = (selected_item,)
        reason = (
            "defensive posture preserves the cheapest known future "
            "minimum executable option"
        )
    else:
        return CiboOptionalityDecision(
            reserve_stop_risk_usd=Decimal(0),
            reserve_margin_usd=Decimal(0),
            deployable_stop_risk_usd=hard_risk_headroom_usd,
            deployable_margin_usd=margin_headroom_usd,
            reserved_for_opportunity_ids=(),
            preserve_new_capital=False,
            reason=(
                "capability-discovery posture measures full deployable "
                "capacity instead of reserving known options"
            ),
        )

    reserve_risk = min(hard_risk_headroom_usd, risk_requirement)
    reserve_margin = min(margin_headroom_usd, margin_requirement)
    return CiboOptionalityDecision(
        reserve_stop_risk_usd=reserve_risk,
        reserve_margin_usd=reserve_margin,
        deployable_stop_risk_usd=hard_risk_headroom_usd - reserve_risk,
        deployable_margin_usd=margin_headroom_usd - reserve_margin,
        reserved_for_opportunity_ids=tuple(
            item.opportunity_id for item in selected
        ),
        preserve_new_capital=reserve_risk > 0 or reserve_margin > 0,
        reason=reason,
    )
