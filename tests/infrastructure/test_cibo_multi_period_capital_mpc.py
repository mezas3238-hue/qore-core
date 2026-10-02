from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10EconomicBucket,
    Genc10KnownCapitalOption,
    Genc10ObservedCapitalTwin,
    Genc10WorldKind,
    Genc10WorldScenario,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboRegimePosture
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    GENC11_POLICY_SHA256,
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
    Genc11WorldStep,
    plan_genc11_multi_period_capital,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 8, 10, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="genc11-mpc",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _twin() -> Genc10ObservedCapitalTwin:
    buckets = tuple(
        (
            bucket,
            Decimal("100")
            if bucket is Genc10EconomicBucket.ORIGINAL_BASE
            else Decimal(0),
        )
        for bucket in Genc10EconomicBucket
    )
    return Genc10ObservedCapitalTwin(
        twin_id="genc11-twin",
        account_identity=_identity(),
        captured_at=T0,
        capital_truth_sha256="sha256:" + "1" * 64,
        compound_cycle_sha256="sha256:" + "2" * 64,
        source_ledger_sha256="sha256:" + "3" * 64,
        provider_registry_sha256="sha256:" + "4" * 64,
        total_realized_capital_usd=Decimal("100"),
        original_base_usd=Decimal("100"),
        compound_economic_value_usd=Decimal("0"),
        protected_floor_usd=Decimal("0"),
        policy_protected_floor_usd=Decimal("0"),
        broker_guaranteed_floor_usd=Decimal("0"),
        economic_buckets=buckets,
        generation_balances=(),
        source_capacities=(),
        total_stop_risk_capacity_usd=Decimal("10"),
        used_stop_risk_usd=Decimal("0"),
        stop_risk_headroom_usd=Decimal("10"),
        total_margin_capacity_usd=Decimal("100"),
        used_margin_usd=Decimal("0"),
        margin_headroom_usd=Decimal("100"),
        active_deployment_count=0,
        provider_capability_counts=(),
        known_options=(
            Genc10KnownCapitalOption(
                option_id="known-a",
                known_at=T0,
                earliest_action_at=T0 + timedelta(minutes=5),
                expires_at=T0 + timedelta(minutes=40),
                requested_capital_usd=Decimal("5"),
                stop_risk_usd=Decimal("1"),
                margin_usd=Decimal("2"),
                evidence_sha256="sha256:" + "5" * 64,
            ),
        ),
    )


def _scenario(
    *,
    scenario_id: str,
    kind: Genc10WorldKind,
    declared_at: datetime,
    surviving: tuple[str, ...],
    risk_delta: str = "0",
    margin_delta: str = "0",
    hypothetical: int = 0,
) -> Genc10WorldScenario:
    return Genc10WorldScenario(
        scenario_id=scenario_id,
        kind=kind,
        declared_at=declared_at,
        scenario_evidence_sha256="sha256:" + "6" * 64,
        transition_uncertainty_evidence_sha256="sha256:" + "7" * 64,
        stop_risk_capacity_delta_usd=Decimal(risk_delta),
        margin_capacity_delta_usd=Decimal(margin_delta),
        surviving_known_option_ids=surviving,
        hypothetical_new_option_count=hypothetical,
    )


def _path(
    *,
    path_id: str,
    kind: Genc10WorldKind,
    risk_deltas: tuple[str, str, str],
    margin_deltas: tuple[str, str, str],
    hypothetical: int = 0,
) -> Genc11WorldPath:
    steps = tuple(
        Genc11WorldStep(
            step_index=index,
            projected_at=T0 + timedelta(minutes=5 * index),
            posture=CiboRegimePosture.STABLE,
            scenario=_scenario(
                scenario_id=f"{path_id}-{index}",
                kind=kind,
                declared_at=T0,
                surviving=("known-a",),
                risk_delta=risk_deltas[index - 1],
                margin_delta=margin_deltas[index - 1],
                hypothetical=hypothetical if index == 1 else 0,
            ),
        )
        for index in range(1, 4)
    )
    return Genc11WorldPath(
        path_id=path_id,
        world_kind=kind,
        steps=steps,
        factor_interaction_evidence_sha256="sha256:" + "8" * 64,
        optionality_evidence_sha256="sha256:" + "9" * 64,
        reserve_need_evidence_sha256="sha256:" + "a" * 64,
    )


def _schedule() -> tuple[Genc11KnownOptionSchedule, ...]:
    return (
        Genc11KnownOptionSchedule(
            option_id="known-a",
            decision_step=1,
            schedule_evidence_sha256="sha256:" + "b" * 64,
        ),
    )


def test_genc11_policy_digest_is_frozen() -> None:
    assert GENC11_POLICY_SHA256 == (
        "sha256:a919f08abd0dbf4496a9bac553fc9e5c7ca32d4d9a564431f928ba9e4038d7f4"
    )


def test_genc11_builds_robust_multi_world_receding_horizon_plan() -> None:
    plan = plan_genc11_multi_period_capital(
        plan_id="plan-1",
        twin=_twin(),
        world_paths=(
            _path(
                path_id="balanced",
                kind=Genc10WorldKind.BALANCED,
                risk_deltas=("0", "0", "0"),
                margin_deltas=("0", "0", "0"),
            ),
            _path(
                path_id="crisis",
                kind=Genc10WorldKind.CRISIS,
                risk_deltas=("-2", "0", "0"),
                margin_deltas=("-20", "0", "0"),
            ),
        ),
        option_schedules=_schedule(),
    )

    assert plan.horizon_steps == 3
    assert plan.known_option_ids == ("known-a",)
    assert len(plan.world_step_plans) == 6
    first = plan.robust_step_envelopes[0]
    assert first.common_stop_risk_headroom_usd == Decimal("8")
    assert first.common_margin_headroom_usd == Decimal("80")
    assert first.maximum_required_reserve_stop_risk_usd == Decimal("1")
    assert first.maximum_required_reserve_margin_usd == Decimal("2")
    assert first.minimum_deployable_stop_risk_usd == Decimal("7")
    assert first.minimum_deployable_margin_usd == Decimal("78")
    assert first.all_worlds_horizon_coverable is True
    assert plan.oracle_arrivals_used is False
    assert plan.production_policy_selected is False
    assert plan.certification_ready is False


def test_genc11_anonymous_future_arrivals_never_gain_geometry() -> None:
    plan = plan_genc11_multi_period_capital(
        plan_id="plan-hypothetical",
        twin=_twin(),
        world_paths=(
            _path(
                path_id="abundance",
                kind=Genc10WorldKind.OPPORTUNITY_ABUNDANCE,
                risk_deltas=("0", "0", "0"),
                margin_deltas=("0", "0", "0"),
                hypothetical=10,
            ),
            _path(
                path_id="balanced",
                kind=Genc10WorldKind.BALANCED,
                risk_deltas=("0", "0", "0"),
                margin_deltas=("0", "0", "0"),
            ),
        ),
        option_schedules=_schedule(),
    )

    abundance_first = next(
        item
        for item in plan.world_step_plans
        if item.path_id == "abundance" and item.step_index == 1
    )
    assert abundance_first.anonymous_hypothetical_option_count == 10
    assert abundance_first.geometry_option_ids == ("known-a",)
    assert "hypothetical" not in abundance_first.geometry_option_ids


def test_genc11_requires_schedule_for_every_known_in_horizon_option() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cover every known in-horizon option",
    ):
        plan_genc11_multi_period_capital(
            plan_id="missing-option",
            twin=_twin(),
            world_paths=(
                _path(
                    path_id="balanced",
                    kind=Genc10WorldKind.BALANCED,
                    risk_deltas=("0", "0", "0"),
                    margin_deltas=("0", "0", "0"),
                ),
                _path(
                    path_id="defensive",
                    kind=Genc10WorldKind.DEFENSIVE,
                    risk_deltas=("0", "0", "0"),
                    margin_deltas=("0", "0", "0"),
                ),
            ),
            option_schedules=(),
        )


def test_genc11_rejects_manually_delayed_option_schedule() -> None:
    delayed = (
        Genc11KnownOptionSchedule(
            option_id="known-a",
            decision_step=2,
            schedule_evidence_sha256="sha256:" + "c" * 64,
        ),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="does not match known action time",
    ):
        plan_genc11_multi_period_capital(
            plan_id="delayed-option",
            twin=_twin(),
            world_paths=(
                _path(
                    path_id="balanced",
                    kind=Genc10WorldKind.BALANCED,
                    risk_deltas=("0", "0", "0"),
                    margin_deltas=("0", "0", "0"),
                ),
                _path(
                    path_id="defensive",
                    kind=Genc10WorldKind.DEFENSIVE,
                    risk_deltas=("0", "0", "0"),
                    margin_deltas=("0", "0", "0"),
                ),
            ),
            option_schedules=delayed,
        )


def test_genc11_world_paths_must_share_synchronized_clock() -> None:
    normal = _path(
        path_id="balanced",
        kind=Genc10WorldKind.BALANCED,
        risk_deltas=("0", "0", "0"),
        margin_deltas=("0", "0", "0"),
    )
    shifted_steps = tuple(
        Genc11WorldStep(
            step_index=item.step_index,
            projected_at=item.projected_at + timedelta(minutes=1),
            posture=item.posture,
            scenario=item.scenario,
        )
        for item in normal.steps
    )
    shifted = Genc11WorldPath(
        path_id="shifted",
        world_kind=Genc10WorldKind.BALANCED,
        steps=shifted_steps,
        factor_interaction_evidence_sha256="sha256:" + "d" * 64,
        optionality_evidence_sha256="sha256:" + "e" * 64,
        reserve_need_evidence_sha256="sha256:" + "f" * 64,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="synchronized step times",
    ):
        plan_genc11_multi_period_capital(
            plan_id="clock-drift",
            twin=_twin(),
            world_paths=(normal, shifted),
            option_schedules=_schedule(),
        )


def test_genc11_plan_rejects_incomplete_world_step_matrix() -> None:
    plan = plan_genc11_multi_period_capital(
        plan_id="plan-complete-matrix",
        twin=_twin(),
        world_paths=(
            _path(
                path_id="balanced",
                kind=Genc10WorldKind.BALANCED,
                risk_deltas=("0", "0", "0"),
                margin_deltas=("0", "0", "0"),
            ),
            _path(
                path_id="crisis",
                kind=Genc10WorldKind.CRISIS,
                risk_deltas=("-2", "0", "0"),
                margin_deltas=("-20", "0", "0"),
            ),
        ),
        option_schedules=_schedule(),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="world-step coverage drift",
    ):
        replace(plan, world_step_plans=plan.world_step_plans[:-1])


def test_genc11_plan_rejects_duplicate_path_ids_and_bad_envelope_steps() -> None:
    plan = plan_genc11_multi_period_capital(
        plan_id="plan-identity-check",
        twin=_twin(),
        world_paths=(
            _path(
                path_id="balanced",
                kind=Genc10WorldKind.BALANCED,
                risk_deltas=("0", "0", "0"),
                margin_deltas=("0", "0", "0"),
            ),
            _path(
                path_id="crisis",
                kind=Genc10WorldKind.CRISIS,
                risk_deltas=("-2", "0", "0"),
                margin_deltas=("-20", "0", "0"),
            ),
        ),
        option_schedules=_schedule(),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="path ids must be unique",
    ):
        replace(plan, path_ids=("balanced", "balanced"))

    with pytest.raises(
        CiboCapitalManagementError,
        match="robust-envelope step identity drift",
    ):
        replace(
            plan,
            robust_step_envelopes=(
                replace(plan.robust_step_envelopes[0], step_index=2),
                *plan.robust_step_envelopes[1:],
            ),
        )


def test_genc11_rejects_ambiguous_bool_and_counter_types() -> None:
    path = _path(
        path_id="balanced",
        kind=Genc10WorldKind.BALANCED,
        risk_deltas=("0", "0", "0"),
        margin_deltas=("0", "0", "0"),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="future_outcome_used must be bool",
    ):
        replace(path, future_outcome_used=0)

    plan = plan_genc11_multi_period_capital(
        plan_id="plan-bool-check",
        twin=_twin(),
        world_paths=(
            path,
            _path(
                path_id="crisis",
                kind=Genc10WorldKind.CRISIS,
                risk_deltas=("-2", "0", "0"),
                margin_deltas=("-20", "0", "0"),
            ),
        ),
        option_schedules=_schedule(),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="plan oos_pass must be bool",
    ):
        replace(plan, oos_pass=0)
