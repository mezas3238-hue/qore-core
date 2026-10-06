from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

ROOT = Path(__file__).resolve().parents[2]
SPECIALIST = ROOT / "scripts" / "vt31_nas100_specialist_r1_candidate.py"


def _situation(
    *,
    ref_ratio: str = "0.68",
    planned_target_r: Decimal | None = None,
) -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of="2026-01-05T15:20:00+00:00",
        weekday="Monday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=10 * 60 + 20,
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
        volatility_state=(
            "compressed"
            if Decimal(ref_ratio) < Decimal("0.75")
            else "normal"
        ),
        current_path_vs_previous=Decimal("0.62"),
        reference_width_vs_prior5=Decimal(ref_ratio),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.55"),
        recent_overlap_rate=Decimal("0.42"),
        first_breach_side="high",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=3,
        last_structure_event_family="reference-liquidity-sweep",
        last_structure_event_age_minutes=2,
        recent_liquidity_event_count_10m=2,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family="fair-value-gap",
        confirmation_latency_minutes=4,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.21"),
        planned_target_r=planned_target_r,
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


def test_runtime_situation_allows_strategy_native_r_target() -> None:
    situation = _situation(planned_target_r=Decimal("3"))

    assert situation.planned_target_r == Decimal("3")
    assert situation.payload()["planned_target_r"] == "3"


def test_current_candidate_may_remain_structural_without_banning_r() -> None:
    decision = reason(_situation(ref_ratio="0.68", planned_target_r=Decimal("3")))

    assert decision.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"


def test_specialist_contract_allows_r_but_forbids_sizing_rescue() -> None:
    text = SPECIALIST.read_text(encoding="utf-8")

    assert '"runtime_r_target_allowed": True' in text
    assert '"runtime_r_breakeven_allowed": True' in text
    assert '"runtime_r_trailing_allowed": True' in text
    assert '"r_runtime_allowed_by_sovereign_rule": True' in text
    assert '"sizing_used": False' in text
    assert '"leverage_used": False' in text
    assert '"compounding_used": False' in text
    assert '"capital_weighting_used": False' in text


def test_current_candidate_can_report_no_r_management_without_disabling_capability() -> None:
    text = SPECIALIST.read_text(encoding="utf-8")

    assert '"current_candidate_uses_r_runtime_management": False' in text
    assert '"r_runtime_allowed_by_sovereign_rule": True' in text


def test_volume_does_not_become_trader_decision_authority() -> None:
    text = SPECIALIST.read_text(encoding="utf-8")

    assert '"volume_changes_market_decision": False' in text
    assert '"sizing_used": False' in text
