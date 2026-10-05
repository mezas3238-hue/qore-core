"""Phase 20I forecastless receding-horizon capital optionality contract.

The planner preserves enough current capacity to keep one deterministic,
currently-known executable option reachable at each future decision step inside
a finite horizon. It does not forecast market outcomes, prices or probabilities.

At every call the horizon is rebuilt from current headroom and currently-known
options. There is no hidden state, no outcome fitting and no Phase-19J reuse.
This is research-only MPC machinery, not an allocator or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture


@dataclass(frozen=True, slots=True)
class Phase20MpcKnownOption:
    opportunity_id: str
    decision_step: int
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal

    def __post_init__(self) -> None:
        if not self.opportunity_id:
            raise CiboCapitalManagementError(
                "Phase20I option opportunity_id is required"
            )
        if (
            type(self.decision_step) is not int
            or self.decision_step < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20I decision_step must be non-negative int"
            )
        for name in ("minimum_stop_risk_usd", "minimum_margin_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20I {name} must be finite non-negative Decimal"
                )


@dataclass(frozen=True, slots=True)
class Phase20MpcCapacityPlan:
    current_step: int
    horizon_steps: int
    horizon_end_step: int
    posture: CiboRegimePosture
    considered_option_ids: tuple[str, ...]
    representative_option_ids: tuple[str, ...]
    reserve_stop_risk_usd: Decimal
    reserve_margin_usd: Decimal
    deployable_stop_risk_usd: Decimal
    deployable_margin_usd: Decimal
    horizon_fully_coverable: bool
    reason: str
    forecast_model_used: bool = False
    outcome_aware: bool = False
    validation_tuned: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if type(self.current_step) is not int or self.current_step < 0:
            raise CiboCapitalManagementError(
                "Phase20I current_step must be non-negative int"
            )
        if type(self.horizon_steps) is not int or self.horizon_steps <= 0:
            raise CiboCapitalManagementError(
                "Phase20I horizon_steps must be positive int"
            )
        if self.horizon_end_step != self.current_step + self.horizon_steps:
            raise CiboCapitalManagementError(
                "Phase20I horizon end drift"
            )
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "Phase20I posture must use canonical enum"
            )
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
                    f"Phase20I {name} must be finite non-negative Decimal"
                )
        if type(self.horizon_fully_coverable) is not bool:
            raise CiboCapitalManagementError(
                "Phase20I horizon_fully_coverable must be bool"
            )
        if not self.reason:
            raise CiboCapitalManagementError("Phase20I reason is required")
        if (
            self.forecast_model_used
            or self.outcome_aware
            or self.validation_tuned
            or self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20I MPC governance drift"
            )


def _finite_headroom(value: Decimal, *, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"Phase20I {name} must be finite non-negative Decimal"
        )


def _capacity_pressure(
    option: Phase20MpcKnownOption,
    *,
    risk_headroom: Decimal,
    margin_headroom: Decimal,
) -> tuple[Decimal, Decimal, str]:
    if risk_headroom == 0:
        risk_pressure = (
            Decimal(0)
            if option.minimum_stop_risk_usd == 0
            else Decimal("Infinity")
        )
    else:
        risk_pressure = option.minimum_stop_risk_usd / risk_headroom

    if margin_headroom == 0:
        margin_pressure = (
            Decimal(0)
            if option.minimum_margin_usd == 0
            else Decimal("Infinity")
        )
    else:
        margin_pressure = option.minimum_margin_usd / margin_headroom

    return (
        max(risk_pressure, margin_pressure),
        risk_pressure + margin_pressure,
        option.opportunity_id,
    )


def plan_phase20i_receding_horizon_capacity(
    *,
    current_step: int,
    horizon_steps: int,
    posture: CiboRegimePosture,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    known_options: tuple[Phase20MpcKnownOption, ...],
    recovery_probe_stop_risk_usd: Decimal = Decimal(0),
    recovery_probe_margin_usd: Decimal = Decimal(0),
) -> Phase20MpcCapacityPlan:
    """Recompute a finite-horizon reserve from currently-known option geometry."""

    if type(current_step) is not int or current_step < 0:
        raise CiboCapitalManagementError(
            "Phase20I current_step must be non-negative int"
        )
    if type(horizon_steps) is not int or horizon_steps <= 0:
        raise CiboCapitalManagementError(
            "Phase20I horizon_steps must be positive int"
        )
    if type(posture) is not CiboRegimePosture:
        raise CiboCapitalManagementError(
            "Phase20I posture must use canonical enum"
        )
    _finite_headroom(
        hard_risk_headroom_usd,
        name="hard_risk_headroom_usd",
    )
    _finite_headroom(
        margin_headroom_usd,
        name="margin_headroom_usd",
    )
    _finite_headroom(
        recovery_probe_stop_risk_usd,
        name="recovery_probe_stop_risk_usd",
    )
    _finite_headroom(
        recovery_probe_margin_usd,
        name="recovery_probe_margin_usd",
    )
    if (
        recovery_probe_stop_risk_usd > hard_risk_headroom_usd
        or recovery_probe_margin_usd > margin_headroom_usd
    ):
        raise CiboCapitalManagementError(
            "Phase20I recovery probe cannot exceed current headroom"
        )
    ids = tuple(item.opportunity_id for item in known_options)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "Phase20I option ids must be unique"
        )

    horizon_end = current_step + horizon_steps
    considered = tuple(
        sorted(
            (
                item
                for item in known_options
                if current_step < item.decision_step <= horizon_end
            ),
            key=lambda item: (item.decision_step, item.opportunity_id),
        )
    )
    considered_ids = tuple(item.opportunity_id for item in considered)

    if posture is CiboRegimePosture.HALT_NEW_CAPITAL:
        fully_coverable = all(
            item.minimum_stop_risk_usd <= hard_risk_headroom_usd
            and item.minimum_margin_usd <= margin_headroom_usd
            for item in considered
        )
        return Phase20MpcCapacityPlan(
            current_step=current_step,
            horizon_steps=horizon_steps,
            horizon_end_step=horizon_end,
            posture=posture,
            considered_option_ids=considered_ids,
            representative_option_ids=considered_ids,
            reserve_stop_risk_usd=hard_risk_headroom_usd,
            reserve_margin_usd=margin_headroom_usd,
            deployable_stop_risk_usd=Decimal(0),
            deployable_margin_usd=Decimal(0),
            horizon_fully_coverable=fully_coverable,
            reason="halt posture preserves the complete horizon capacity",
        )

    if posture is CiboRegimePosture.RECOVERY:
        fully_coverable = all(
            item.minimum_stop_risk_usd <= hard_risk_headroom_usd
            and item.minimum_margin_usd <= margin_headroom_usd
            for item in considered
        )
        probe_enabled = (
            recovery_probe_stop_risk_usd > 0
            and recovery_probe_margin_usd > 0
        )
        deployable_risk = (
            recovery_probe_stop_risk_usd
            if probe_enabled
            else Decimal(0)
        )
        deployable_margin = (
            recovery_probe_margin_usd
            if probe_enabled
            else Decimal(0)
        )
        return Phase20MpcCapacityPlan(
            current_step=current_step,
            horizon_steps=horizon_steps,
            horizon_end_step=horizon_end,
            posture=posture,
            considered_option_ids=considered_ids,
            representative_option_ids=considered_ids,
            reserve_stop_risk_usd=hard_risk_headroom_usd - deployable_risk,
            reserve_margin_usd=margin_headroom_usd - deployable_margin,
            deployable_stop_risk_usd=deployable_risk,
            deployable_margin_usd=deployable_margin,
            horizon_fully_coverable=fully_coverable,
            reason=(
                "recovery preserves the horizon envelope while exposing one "
                "explicit causal capability-measurement probe"
                if probe_enabled
                else "recovery preserves the complete horizon capacity"
            ),
        )

    if not considered:
        return Phase20MpcCapacityPlan(
            current_step=current_step,
            horizon_steps=horizon_steps,
            horizon_end_step=horizon_end,
            posture=posture,
            considered_option_ids=(),
            representative_option_ids=(),
            reserve_stop_risk_usd=Decimal(0),
            reserve_margin_usd=Decimal(0),
            deployable_stop_risk_usd=hard_risk_headroom_usd,
            deployable_margin_usd=margin_headroom_usd,
            horizon_fully_coverable=True,
            reason="no currently-known option falls inside the finite horizon",
        )

    by_step: dict[int, list[Phase20MpcKnownOption]] = {}
    for item in considered:
        by_step.setdefault(item.decision_step, []).append(item)

    representatives = tuple(
        min(
            by_step[step],
            key=lambda item: _capacity_pressure(
                item,
                risk_headroom=hard_risk_headroom_usd,
                margin_headroom=margin_headroom_usd,
            ),
        )
        for step in sorted(by_step)
    )
    required_risk = max(
        item.minimum_stop_risk_usd for item in representatives
    )
    required_margin = max(
        item.minimum_margin_usd for item in representatives
    )
    reserve_risk = min(hard_risk_headroom_usd, required_risk)
    reserve_margin = min(margin_headroom_usd, required_margin)
    fully_coverable = all(
        item.minimum_stop_risk_usd <= hard_risk_headroom_usd
        and item.minimum_margin_usd <= margin_headroom_usd
        for item in representatives
    )
    return Phase20MpcCapacityPlan(
        current_step=current_step,
        horizon_steps=horizon_steps,
        horizon_end_step=horizon_end,
        posture=posture,
        considered_option_ids=considered_ids,
        representative_option_ids=tuple(
            item.opportunity_id for item in representatives
        ),
        reserve_stop_risk_usd=reserve_risk,
        reserve_margin_usd=reserve_margin,
        deployable_stop_risk_usd=hard_risk_headroom_usd - reserve_risk,
        deployable_margin_usd=margin_headroom_usd - reserve_margin,
        horizon_fully_coverable=fully_coverable,
        reason=(
            "reserve the maximum current capacity requirement across one "
            "deterministic representative option per future decision step"
        ),
    )
