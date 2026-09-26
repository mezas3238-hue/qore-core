"""Deterministic CIBO Capital Management Authority stage machine."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import CapitalStage
from qore.infrastructure.cibo_economic_floor import EconomicFloorResult


class CmaStateMachineError(ValueError):
    """Invalid CMA lifecycle transition."""


@dataclass(frozen=True, slots=True)
class CmaStageDecision:
    stage: CapitalStage
    expansion_eligible: bool
    reason: str


_ALLOWED_TRANSITIONS: dict[CapitalStage, frozenset[CapitalStage]] = {
    CapitalStage.MINIMAL_SEED: frozenset(
        {
            CapitalStage.MINIMAL_SEED,
            CapitalStage.OBSERVE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.OBSERVE: frozenset(
        {
            CapitalStage.OBSERVE,
            CapitalStage.PROTECT_BASE,
            CapitalStage.BASE_RECOVERED,
            CapitalStage.CAPITALIZE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.PROTECT_BASE: frozenset(
        {
            CapitalStage.PROTECT_BASE,
            CapitalStage.BASE_RECOVERED,
            CapitalStage.CAPITALIZE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.BASE_RECOVERED: frozenset(
        {
            CapitalStage.BASE_RECOVERED,
            CapitalStage.CAPITALIZE,
            CapitalStage.COMPOUND_OR_RESERVE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.CAPITALIZE: frozenset(
        {
            CapitalStage.CAPITALIZE,
            CapitalStage.COMPOUND_OR_RESERVE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.COMPOUND_OR_RESERVE: frozenset(
        {
            CapitalStage.COMPOUND_OR_RESERVE,
            CapitalStage.CAPITALIZE,
            CapitalStage.RELEASE,
        }
    ),
    CapitalStage.RELEASE: frozenset({CapitalStage.RELEASE}),
}


def derive_stage(
    *,
    seed_deployed: bool,
    position_open: bool,
    floor: EconomicFloorResult | None,
) -> CmaStageDecision:
    """Derive the capital stage only from current reconciled evidence."""

    if type(seed_deployed) is not bool or type(position_open) is not bool:
        raise CmaStateMachineError("seed_deployed and position_open must be bool")

    if not seed_deployed:
        if position_open:
            raise CmaStateMachineError(
                "position cannot be open before CMA seed deployment evidence"
            )
        return CmaStageDecision(
            stage=CapitalStage.MINIMAL_SEED,
            expansion_eligible=False,
            reason="no CIBO seed deployed",
        )

    if not position_open:
        return CmaStageDecision(
            stage=CapitalStage.RELEASE,
            expansion_eligible=False,
            reason="position no longer open; release/reconcile capital",
        )

    if floor is None or not floor.evidence_sufficient:
        return CmaStageDecision(
            stage=CapitalStage.OBSERVE,
            expansion_eligible=False,
            reason="economic-floor evidence insufficient; expansion fail-closed",
        )

    if (
        floor.base_capital_at_risk_usd is None
        or floor.proven_self_financing_capacity_usd is None
    ):
        raise CmaStateMachineError("sufficient floor missing capital facts")

    if floor.base_capital_at_risk_usd > 0:
        return CmaStageDecision(
            stage=CapitalStage.PROTECT_BASE,
            expansion_eligible=False,
            reason="original/base capital remains exposed",
        )

    if floor.proven_self_financing_capacity_usd <= 0:
        return CmaStageDecision(
            stage=CapitalStage.BASE_RECOVERED,
            expansion_eligible=False,
            reason="base recovered but no proven expansion capacity",
        )

    return CmaStageDecision(
        stage=CapitalStage.CAPITALIZE,
        expansion_eligible=True,
        reason="base recovered and self-financing capacity proven",
    )


def validate_transition(
    current: CapitalStage,
    target: CapitalStage,
) -> None:
    if type(current) is not CapitalStage or type(target) is not CapitalStage:
        raise CmaStateMachineError("current/target must be CapitalStage")
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise CmaStateMachineError(
            f"illegal CMA transition {current.value}->{target.value}"
        )
