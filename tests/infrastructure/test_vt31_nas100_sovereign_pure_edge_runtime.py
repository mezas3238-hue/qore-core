from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)


ROOT = Path(__file__).resolve().parents[2]
SPECIALIST = ROOT / "scripts" / "vt31_nas100_specialist_r1_candidate.py"
REASONING = (
    ROOT
    / "src"
    / "qore"
    / "infrastructure"
    / "traders"
    / "vt31_nas100_reasoning_engine.py"
)


def _situation(*, ref_ratio: str = "0.68") -> Nas100SituationModel:
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
        planned_target_r=None,
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


def test_runtime_reasoning_has_no_r_target_plan() -> None:
    compressed = reason(_situation(ref_ratio="0.68"))
    normal = reason(_situation(ref_ratio="1.05"))

    assert compressed.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"
    assert normal.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"
    assert "R" not in compressed.target_plan
    assert "PARTIAL" not in compressed.target_plan


def test_runtime_situation_rejects_planned_target_r() -> None:
    base = _situation()
    payload = {
        name: getattr(base, name)
        for name in base.__dataclass_fields__
    }
    payload["planned_target_r"] = Decimal("3")

    with pytest.raises(
        ValueError,
        match="R is post-trade evaluation only",
    ):
        Nas100SituationModel(**payload)


def test_certifiable_simulator_does_not_use_r_exit_triggers() -> None:
    text = SPECIALIST.read_text(encoding="utf-8")
    block = text.split(
        "def _simulate_structural_boundary_only",
        1,
    )[1].split(
        "def _simulate_selected_plan",
        1,
    )[0]

    assert "three_r_price" not in block
    assert "touched_three_r" not in block
    assert "PARTIAL_TARGET_R" not in block
    assert "_simulate_partial_runner" not in block
    assert "current_stop = entry" not in block
    assert 'exit_reason = "structural-invalidation"' in block
    assert 'exit_reason = "structural-target"' in block


def test_certifiable_target_selection_has_no_legacy_r_plan() -> None:
    reasoning = REASONING.read_text(encoding="utf-8")

    assert "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER" not in reasoning
    assert "PRIMARY_STRUCTURAL_BOUNDARY" in reasoning


def test_specialist_contract_declares_r_evaluation_only() -> None:
    text = SPECIALIST.read_text(encoding="utf-8")

    assert '"r_is_evaluation_metric_only": True' in text
    assert '"runtime_r_target_allowed": False' in text
    assert '"runtime_r_breakeven_allowed": False' in text
    assert '"runtime_r_trailing_allowed": False' in text
    assert '"sizing_used": False' in text
    assert '"leverage_used": False' in text
    assert '"compounding_used": False' in text
