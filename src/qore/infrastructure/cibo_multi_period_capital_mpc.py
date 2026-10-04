"""GEN-C11 robust multi-period capital MPC.

GEN-C11 composes the existing Phase20I forecastless receding-horizon planner
with GEN-C10 causal Digital Twin worlds. It never forecasts actual future
opportunity arrivals or outcomes. Only options known in the observed twin may
carry executable geometry.

Research/shadow only. No allocation, sizing, Risk, execution, LIVE or
real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10CapitalFlow,
    Genc10KnownCapitalOption,
    Genc10ObservedCapitalTwin,
    Genc10ProjectedTwinState,
    Genc10WorldKind,
    Genc10WorldScenario,
    project_genc10_world,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import (
    Phase20MpcCapacityPlan,
    Phase20MpcKnownOption,
    plan_phase20i_receding_horizon_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture

GENC11_POLICY_ID = "CIBO_GENC11_ROBUST_MULTI_PERIOD_CAPITAL_MPC_V1"
GENC11_FROZEN_AT = datetime(2026, 9, 30, 7, 40, tzinfo=UTC)
GENC11_POLICY_SHA256 = (
    "sha256:a919f08abd0dbf4496a9bac553fc9e5c7ca32d4d9a564431f928ba9e4038d7f4"
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"GEN-C11 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"GEN-C11 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc11KnownOptionSchedule:
    option_id: str
    decision_step: int
    schedule_evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.option_id:
            raise CiboCapitalManagementError(
                "GEN-C11 option schedule identity is required"
            )
        if (
            not isinstance(self.decision_step, int)
            or isinstance(self.decision_step, bool)
            or self.decision_step <= 0
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 option decision step must be positive int"
            )
        _sha(
            self.schedule_evidence_sha256,
            "schedule_evidence_sha256",
        )


@dataclass(frozen=True, slots=True)
class Genc11WorldStep:
    step_index: int
    projected_at: datetime
    posture: CiboRegimePosture
    scenario: Genc10WorldScenario

    def __post_init__(self) -> None:
        if (
            not isinstance(self.step_index, int)
            or isinstance(self.step_index, bool)
            or self.step_index <= 0
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 step index must be positive int"
            )
        _aware(self.projected_at, "step projected_at")
        if type(self.posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "GEN-C11 step posture must be canonical"
            )
        if not isinstance(self.scenario, Genc10WorldScenario):
            raise CiboCapitalManagementError(
                "GEN-C11 step scenario must be GEN-C10 world"
            )
        if self.scenario.declared_at > self.projected_at:
            raise CiboCapitalManagementError(
                "GEN-C11 scenario cannot be declared after its step"
            )


@dataclass(frozen=True, slots=True)
class Genc11WorldPath:
    path_id: str
    world_kind: Genc10WorldKind
    steps: tuple[Genc11WorldStep, ...]
    factor_interaction_evidence_sha256: str
    optionality_evidence_sha256: str
    reserve_need_evidence_sha256: str
    market_probability_claimed: bool = False
    future_outcome_used: bool = False

    def __post_init__(self) -> None:
        if not self.path_id:
            raise CiboCapitalManagementError(
                "GEN-C11 world path identity is required"
            )
        if type(self.world_kind) is not Genc10WorldKind:
            raise CiboCapitalManagementError(
                "GEN-C11 world kind is invalid"
            )
        if not self.steps:
            raise CiboCapitalManagementError(
                "GEN-C11 world path requires steps"
            )
        expected = tuple(range(1, len(self.steps) + 1))
        observed = tuple(item.step_index for item in self.steps)
        if observed != expected:
            raise CiboCapitalManagementError(
                "GEN-C11 world path steps must be contiguous"
            )
        if any(
            item.scenario.kind is not self.world_kind
            for item in self.steps
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 world path cannot change world kind"
            )
        projected = tuple(item.projected_at for item in self.steps)
        if tuple(sorted(projected)) != projected or len(set(projected)) != len(
            projected
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 world path time must increase strictly"
            )
        for name in (
            "factor_interaction_evidence_sha256",
            "optionality_evidence_sha256",
            "reserve_need_evidence_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "market_probability_claimed",
            "future_outcome_used",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"GEN-C11 world path {name} must be bool"
                )
        if self.market_probability_claimed or self.future_outcome_used:
            raise CiboCapitalManagementError(
                "GEN-C11 world path cannot use probability/outcome oracle"
            )


@dataclass(frozen=True, slots=True)
class Genc11WorldStepPlan:
    path_id: str
    world_kind: Genc10WorldKind
    step_index: int
    projected_state: Genc10ProjectedTwinState
    capacity_plan: Phase20MpcCapacityPlan
    geometry_option_ids: tuple[str, ...]
    anonymous_hypothetical_option_count: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path_id, str)
            or not self.path_id
            or not isinstance(self.step_index, int)
            or isinstance(self.step_index, bool)
            or self.step_index <= 0
            or type(self.world_kind) is not Genc10WorldKind
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 world step plan identity is invalid"
            )
        if not isinstance(
            self.projected_state,
            Genc10ProjectedTwinState,
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 step plan projected state is invalid"
            )
        if not isinstance(self.capacity_plan, Phase20MpcCapacityPlan):
            raise CiboCapitalManagementError(
                "GEN-C11 step plan capacity plan is invalid"
            )
        if (
            not isinstance(self.anonymous_hypothetical_option_count, int)
            or isinstance(self.anonymous_hypothetical_option_count, bool)
            or self.anonymous_hypothetical_option_count < 0
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 hypothetical option count must be non-negative int"
            )
        if (
            not isinstance(self.geometry_option_ids, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.geometry_option_ids
            )
            or len(self.geometry_option_ids)
            != len(set(self.geometry_option_ids))
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 geometry option ids must be unique non-empty strings"
            )
        if any(
            item not in self.projected_state.surviving_known_option_ids
            for item in self.geometry_option_ids
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 geometry can only use surviving known options"
            )


@dataclass(frozen=True, slots=True)
class Genc11RobustStepEnvelope:
    step_index: int
    common_stop_risk_headroom_usd: Decimal
    common_margin_headroom_usd: Decimal
    maximum_required_reserve_stop_risk_usd: Decimal
    maximum_required_reserve_margin_usd: Decimal
    minimum_deployable_stop_risk_usd: Decimal
    minimum_deployable_margin_usd: Decimal
    minimum_projected_realized_capital_usd: Decimal
    all_worlds_horizon_coverable: bool

    def __post_init__(self) -> None:
        if self.step_index <= 0:
            raise CiboCapitalManagementError(
                "GEN-C11 robust step index must be positive"
            )
        for name in (
            "common_stop_risk_headroom_usd",
            "common_margin_headroom_usd",
            "maximum_required_reserve_stop_risk_usd",
            "maximum_required_reserve_margin_usd",
            "minimum_deployable_stop_risk_usd",
            "minimum_deployable_margin_usd",
            "minimum_projected_realized_capital_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"GEN-C11 {name} must be finite non-negative Decimal"
                )
        if type(self.all_worlds_horizon_coverable) is not bool:
            raise CiboCapitalManagementError(
                "GEN-C11 coverable flag must be bool"
            )


@dataclass(frozen=True, slots=True)
class Genc11MultiPeriodPlan:
    plan_id: str
    twin_id: str
    horizon_steps: int
    step_times: tuple[datetime, ...]
    path_ids: tuple[str, ...]
    known_option_ids: tuple[str, ...]
    world_step_plans: tuple[Genc11WorldStepPlan, ...]
    robust_step_envelopes: tuple[Genc11RobustStepEnvelope, ...]
    policy_id: str = GENC11_POLICY_ID
    policy_sha256: str = GENC11_POLICY_SHA256
    frozen_at: datetime = GENC11_FROZEN_AT
    weighted_score_used: bool = False
    oracle_arrivals_used: bool = False
    market_probability_claimed: bool = False
    production_policy_selected: bool = False
    value_demonstrated: bool = False
    oos_pass: bool = False
    stress_pass: bool = False
    temporal_replication_pass: bool = False
    certification_ready: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.plan_id or not self.twin_id:
            raise CiboCapitalManagementError(
                "GEN-C11 plan identity is required"
            )
        if self.horizon_steps < 2:
            raise CiboCapitalManagementError(
                "GEN-C11 horizon must contain at least two steps"
            )
        if len(self.step_times) != self.horizon_steps:
            raise CiboCapitalManagementError(
                "GEN-C11 plan step-time count drift"
            )
        if len(self.robust_step_envelopes) != self.horizon_steps:
            raise CiboCapitalManagementError(
                "GEN-C11 robust-envelope count drift"
            )
        if (
            not isinstance(self.path_ids, tuple)
            or not self.path_ids
            or any(not isinstance(item, str) or not item for item in self.path_ids)
            or len(self.path_ids) != len(set(self.path_ids))
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 plan path ids must be unique non-empty strings"
            )
        if (
            not isinstance(self.known_option_ids, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.known_option_ids
            )
            or len(self.known_option_ids) != len(set(self.known_option_ids))
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 plan known option ids must be unique non-empty strings"
            )
        for at in self.step_times:
            _aware(at, "plan step time")
        if (
            tuple(sorted(self.step_times)) != self.step_times
            or len(set(self.step_times)) != len(self.step_times)
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 plan step times must increase strictly"
            )
        if (
            not isinstance(self.world_step_plans, tuple)
            or any(
                not isinstance(item, Genc11WorldStepPlan)
                for item in self.world_step_plans
            )
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 plan world-step rows must be canonical"
            )
        expected_world_steps = {
            (path_id, step_index)
            for path_id in self.path_ids
            for step_index in range(1, self.horizon_steps + 1)
        }
        observed_world_steps = {
            (item.path_id, item.step_index)
            for item in self.world_step_plans
        }
        if (
            len(self.world_step_plans) != len(expected_world_steps)
            or observed_world_steps != expected_world_steps
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 plan world-step coverage drift"
            )
        if tuple(
            item.step_index for item in self.robust_step_envelopes
        ) != tuple(range(1, self.horizon_steps + 1)):
            raise CiboCapitalManagementError(
                "GEN-C11 robust-envelope step identity drift"
            )
        if self.policy_id != GENC11_POLICY_ID:
            raise CiboCapitalManagementError(
                "GEN-C11 policy identity drift"
            )
        if self.policy_sha256 != GENC11_POLICY_SHA256:
            raise CiboCapitalManagementError(
                "GEN-C11 policy digest drift"
            )
        _aware(self.frozen_at, "frozen_at")
        for name in (
            "weighted_score_used",
            "oracle_arrivals_used",
            "market_probability_claimed",
            "production_policy_selected",
            "value_demonstrated",
            "oos_pass",
            "stress_pass",
            "temporal_replication_pass",
            "certification_ready",
            "allocation_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"GEN-C11 plan {name} must be bool"
                )
        if any(
            (
                self.weighted_score_used,
                self.oracle_arrivals_used,
                self.market_probability_claimed,
                self.production_policy_selected,
                self.value_demonstrated,
                self.oos_pass,
                self.stress_pass,
                self.temporal_replication_pass,
                self.certification_ready,
                self.allocation_authority,
                self.risk_authority,
                self.execution_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "GEN-C11 V1 cannot claim value, oracle or authority"
            )


def plan_genc11_multi_period_capital(
    *,
    plan_id: str,
    twin: Genc10ObservedCapitalTwin,
    world_paths: tuple[Genc11WorldPath, ...],
    option_schedules: tuple[Genc11KnownOptionSchedule, ...],
) -> Genc11MultiPeriodPlan:
    """Build a robust, forecastless multi-world capacity envelope."""

    if not plan_id:
        raise CiboCapitalManagementError("GEN-C11 plan_id is required")
    if not isinstance(twin, Genc10ObservedCapitalTwin):
        raise CiboCapitalManagementError(
            "GEN-C11 requires canonical GEN-C10 observed twin"
        )
    # The GEN-C11 freeze locks the planning policy. A canonical GEN-C10
    # twin may represent historical market time without disabling this engine.
    if len(world_paths) < 2:
        raise CiboCapitalManagementError(
            "GEN-C11 robust planning requires at least two worlds"
        )
    path_ids = tuple(item.path_id for item in world_paths)
    if len(path_ids) != len(set(path_ids)):
        raise CiboCapitalManagementError(
            "GEN-C11 world path ids must be unique"
        )

    horizon = len(world_paths[0].steps)
    if horizon < 2 or any(len(item.steps) != horizon for item in world_paths):
        raise CiboCapitalManagementError(
            "GEN-C11 world paths must share a multi-step horizon"
        )
    step_times = tuple(item.projected_at for item in world_paths[0].steps)
    if any(
        tuple(step.projected_at for step in path.steps) != step_times
        for path in world_paths
    ):
        raise CiboCapitalManagementError(
            "GEN-C11 world paths must share synchronized step times"
        )

    scheduled = _validate_option_schedules(
        twin=twin,
        step_times=step_times,
        schedules=option_schedules,
    )

    plans: list[Genc11WorldStepPlan] = []
    for path in world_paths:
        cumulative: list[Genc10WorldScenario] = []
        for step in path.steps:
            cumulative.append(step.scenario)
            aggregate = _aggregate_scenarios(
                path=path,
                scenarios=tuple(cumulative),
                through_step=step.step_index,
            )
            projected = project_genc10_world(
                twin=twin,
                scenario=aggregate,
                projected_at=step.projected_at,
            )
            surviving = set(projected.surviving_known_option_ids)
            options = tuple(
                Phase20MpcKnownOption(
                    opportunity_id=item.option_id,
                    decision_step=item.decision_step,
                    minimum_stop_risk_usd=_known_option(
                        twin,
                        item.option_id,
                    ).stop_risk_usd,
                    minimum_margin_usd=_known_option(
                        twin,
                        item.option_id,
                    ).margin_usd,
                )
                for item in scheduled
                if item.option_id in surviving
                and _known_option(twin, item.option_id).expires_at
                > step.projected_at
            )
            capacity_plan = plan_phase20i_receding_horizon_capacity(
                current_step=step.step_index - 1,
                horizon_steps=horizon - step.step_index + 1,
                posture=step.posture,
                hard_risk_headroom_usd=(
                    projected.stop_risk_headroom_usd
                ),
                margin_headroom_usd=projected.margin_headroom_usd,
                known_options=options,
            )
            plans.append(
                Genc11WorldStepPlan(
                    path_id=path.path_id,
                    world_kind=path.world_kind,
                    step_index=step.step_index,
                    projected_state=projected,
                    capacity_plan=capacity_plan,
                    geometry_option_ids=tuple(
                        item.opportunity_id for item in options
                    ),
                    anonymous_hypothetical_option_count=(
                        projected.hypothetical_new_option_count
                    ),
                )
            )

    envelopes = tuple(
        _robust_envelope(step_index, tuple(plans))
        for step_index in range(1, horizon + 1)
    )
    return Genc11MultiPeriodPlan(
        plan_id=plan_id,
        twin_id=twin.twin_id,
        horizon_steps=horizon,
        step_times=step_times,
        path_ids=path_ids,
        known_option_ids=tuple(
            sorted(item.option_id for item in scheduled)
        ),
        world_step_plans=tuple(plans),
        robust_step_envelopes=envelopes,
        weighted_score_used=False,
        oracle_arrivals_used=False,
        market_probability_claimed=False,
        production_policy_selected=False,
        value_demonstrated=False,
        oos_pass=False,
        stress_pass=False,
        temporal_replication_pass=False,
        certification_ready=False,
        allocation_authority=False,
        risk_authority=False,
        execution_authority=False,
    )


def _validate_option_schedules(
    *,
    twin: Genc10ObservedCapitalTwin,
    step_times: tuple[datetime, ...],
    schedules: tuple[Genc11KnownOptionSchedule, ...],
) -> tuple[Genc11KnownOptionSchedule, ...]:
    ids = tuple(item.option_id for item in schedules)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "GEN-C11 option schedules must be unique"
        )
    horizon_end = step_times[-1]
    relevant = tuple(
        item
        for item in twin.known_options
        if item.earliest_action_at <= horizon_end
        and item.expires_at > twin.captured_at
    )
    relevant_ids = {item.option_id for item in relevant}
    if set(ids) != relevant_ids:
        raise CiboCapitalManagementError(
            "GEN-C11 schedule must cover every known in-horizon option"
        )
    for schedule in schedules:
        option = _known_option(twin, schedule.option_id)
        expected_step = next(
            (
                index
                for index, at in enumerate(step_times, start=1)
                if at >= option.earliest_action_at
            ),
            None,
        )
        if expected_step is None or schedule.decision_step != expected_step:
            raise CiboCapitalManagementError(
                "GEN-C11 option schedule does not match known action time"
            )
    return tuple(sorted(schedules, key=lambda item: item.option_id))


def _known_option(
    twin: Genc10ObservedCapitalTwin,
    option_id: str,
) -> Genc10KnownCapitalOption:
    rows = tuple(
        item for item in twin.known_options if item.option_id == option_id
    )
    if len(rows) != 1:
        raise CiboCapitalManagementError(
            "GEN-C11 known option is not unique"
        )
    return rows[0]


def _aggregate_scenarios(
    *,
    path: Genc11WorldPath,
    scenarios: tuple[Genc10WorldScenario, ...],
    through_step: int,
) -> Genc10WorldScenario:
    flows: list[Genc10CapitalFlow] = []
    for index, scenario in enumerate(scenarios, start=1):
        for flow in scenario.flows:
            flows.append(
                Genc10CapitalFlow(
                    flow_id=f"s{index}:{flow.flow_id}",
                    kind=flow.kind,
                    amount_usd=flow.amount_usd,
                    evidence_sha256=flow.evidence_sha256,
                    source_bucket=flow.source_bucket,
                    target_bucket=flow.target_bucket,
                )
            )
    latest = scenarios[-1]
    provider_changed = any(
        item.provider_constraints_changed for item in scenarios
    )
    provider_sha = (
        _derived_sha(
            "provider-change",
            tuple(
                item.provider_change_evidence_sha256
                for item in scenarios
                if item.provider_change_evidence_sha256 is not None
            ),
        )
        if provider_changed
        else None
    )
    return Genc10WorldScenario(
        scenario_id=f"{path.path_id}:through:{through_step}",
        kind=path.world_kind,
        declared_at=max(item.declared_at for item in scenarios),
        scenario_evidence_sha256=_derived_sha(
            "scenario",
            tuple(item.scenario_evidence_sha256 for item in scenarios),
        ),
        transition_uncertainty_evidence_sha256=_derived_sha(
            "uncertainty",
            tuple(
                item.transition_uncertainty_evidence_sha256
                for item in scenarios
            ),
        ),
        flows=tuple(flows),
        stop_risk_capacity_delta_usd=sum(
            (item.stop_risk_capacity_delta_usd for item in scenarios),
            Decimal(0),
        ),
        stop_risk_usage_delta_usd=sum(
            (item.stop_risk_usage_delta_usd for item in scenarios),
            Decimal(0),
        ),
        margin_capacity_delta_usd=sum(
            (item.margin_capacity_delta_usd for item in scenarios),
            Decimal(0),
        ),
        margin_usage_delta_usd=sum(
            (item.margin_usage_delta_usd for item in scenarios),
            Decimal(0),
        ),
        surviving_known_option_ids=latest.surviving_known_option_ids,
        hypothetical_new_option_count=sum(
            (item.hypothetical_new_option_count for item in scenarios),
            0,
        ),
        provider_constraints_changed=provider_changed,
        provider_change_evidence_sha256=provider_sha,
        uncertainty_calibrated=False,
        market_probability_claimed=False,
        actual_future_outcome_used=False,
        productive_authority=False,
    )


def _robust_envelope(
    step_index: int,
    plans: tuple[Genc11WorldStepPlan, ...],
) -> Genc11RobustStepEnvelope:
    rows = tuple(
        item for item in plans if item.step_index == step_index
    )
    if not rows:
        raise CiboCapitalManagementError(
            "GEN-C11 robust envelope has no world rows"
        )
    return Genc11RobustStepEnvelope(
        step_index=step_index,
        common_stop_risk_headroom_usd=min(
            item.projected_state.stop_risk_headroom_usd for item in rows
        ),
        common_margin_headroom_usd=min(
            item.projected_state.margin_headroom_usd for item in rows
        ),
        maximum_required_reserve_stop_risk_usd=max(
            item.capacity_plan.reserve_stop_risk_usd for item in rows
        ),
        maximum_required_reserve_margin_usd=max(
            item.capacity_plan.reserve_margin_usd for item in rows
        ),
        minimum_deployable_stop_risk_usd=min(
            item.capacity_plan.deployable_stop_risk_usd for item in rows
        ),
        minimum_deployable_margin_usd=min(
            item.capacity_plan.deployable_margin_usd for item in rows
        ),
        minimum_projected_realized_capital_usd=min(
            item.projected_state.total_realized_capital_usd for item in rows
        ),
        all_worlds_horizon_coverable=all(
            item.capacity_plan.horizon_fully_coverable for item in rows
        ),
    )


def _derived_sha(label: str, values: tuple[str, ...]) -> str:
    payload = {"label": label, "values": list(values)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()



def plan_genc11_from_full_economic_twin(
    *,
    plan_id: str,
    twin: CiboObservedEconomicTwin,
    world_paths: tuple[Genc11WorldPath, ...],
    option_schedules: tuple[Genc11KnownOptionSchedule, ...],
) -> Genc11MultiPeriodPlan:
    """Run GEN-C11 from the canonical Full Economic Twin opportunity surface.

    GEN-C10 remains capital truth. The wrapper only replaces its known-option
    view with the complete causal opportunity set already present in the Full
    Economic Twin, preserving evidence lineage and all existing GEN-C11 world
    mechanics.
    """

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "GEN-C11 Full Twin adapter requires canonical observed twin"
        )
    options = tuple(
        Genc10KnownCapitalOption(
            option_id=item.option_id,
            known_at=item.known_at,
            earliest_action_at=item.earliest_action_at,
            expires_at=item.expires_at,
            requested_capital_usd=item.requested_capital_usd,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            evidence_sha256=item.evidence_sha256,
        )
        for item in twin.opportunities
    )
    augmented_capital_twin = replace(
        twin.capital_twin,
        known_options=options,
    )
    return plan_genc11_multi_period_capital(
        plan_id=plan_id,
        twin=augmented_capital_twin,
        world_paths=world_paths,
        option_schedules=option_schedules,
    )
