from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_core_stack_v2_adapter import (
    VT31CoreAdapter,
    build_vt31_shadow_snapshot,
    observe_vt31_shadow_ab,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

AS_OF = datetime(2026, 9, 23, 15, 12, tzinfo=UTC)


def _situation() -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of=AS_OF.isoformat(),
        weekday="Wednesday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=11 * 60 + 12,
        side="short",
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state="mixed",
        premarket_state="rotation",
        cash_open_state="bearish",
        position_in_prior_day_range="upper-third",
        range_state="compressed",
        volatility_state="compressed",
        current_path_vs_previous=Decimal("0.62"),
        reference_width_vs_prior5=Decimal("0.68"),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.55"),
        recent_overlap_rate=Decimal("0.71"),
        first_breach_side="high",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=3,
        last_structure_event_family="reference-liquidity-sweep",
        last_structure_event_age_minutes=2,
        recent_liquidity_event_count_10m=1,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family="fair-value-gap",
        confirmation_latency_minutes=4,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.21"),
        planned_target_r=Decimal("3.4"),
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.71"),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="RESEARCH_ONLY_UNCALIBRATED",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
    )


def test_vt31_adapter_lives_on_specialist_boundary_and_preserves_methodology() -> None:
    situation = _situation()
    before = reason(situation)
    observation = observe_vt31_shadow_ab(
        situation,
        generated_at=AS_OF,
    )
    after = reason(situation)

    assert before == after
    assert observation.baseline_decision == before
    assert observation.v2_shadow_action == before.action
    assert observation.methodology_preserved is True
    assert observation.context.core_context_valid is True
    assert observation.context.methodology_mutation_allowed is False
    assert observation.context.order_authority is False
    assert observation.context.risk_authority is False


def test_vt31_shadow_lane_fails_closed_without_changing_current_path() -> None:
    situation = _situation()
    baseline = reason(situation)
    observation = observe_vt31_shadow_ab(
        situation,
        generated_at=AS_OF - timedelta(seconds=1),
    )

    assert observation.context.core_context_valid is False
    assert observation.v2_shadow_action == "ABSTAIN"
    assert reason(situation) == baseline
    assert "FUTURE_SOURCE_TIMESTAMP" in (
        observation.snapshot.perception_integrity.codes
    )


def test_vt31_adapter_rejects_non_nas100_snapshot() -> None:
    situation = _situation()
    snapshot = build_vt31_shadow_snapshot(situation, generated_at=AS_OF)
    assert VT31CoreAdapter().adapt(snapshot).core_context_valid is True
