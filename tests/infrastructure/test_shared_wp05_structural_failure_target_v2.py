from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_target_module():
    path = Path("scripts/shared_wp05_structural_failure_target_v2.py")
    spec = importlib.util.spec_from_file_location("shared_wp05_target_v2_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load WP05 target V2 builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


target_v2 = _load_target_module()


def test_bullish_anchor_requires_downside_breach_and_close_acceptance() -> None:
    assert target_v2.higher_timeframe_structural_failure_target(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=112.0,
        future_low=98.0,
        future_final_close=99.0,
    ) is True
    assert target_v2.higher_timeframe_structural_failure_target(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=112.0,
        future_low=98.0,
        future_final_close=101.0,
    ) is False


def test_bearish_anchor_requires_upside_breach_and_close_acceptance() -> None:
    assert target_v2.higher_timeframe_structural_failure_target(
        anchor_direction=-1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=112.0,
        future_low=99.0,
        future_final_close=111.0,
    ) is True
    assert target_v2.higher_timeframe_structural_failure_target(
        anchor_direction=-1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=112.0,
        future_low=99.0,
        future_final_close=109.0,
    ) is False


def test_unidentifiable_anchor_cannot_fabricate_failure() -> None:
    assert target_v2.higher_timeframe_structural_failure_target(
        anchor_direction=0,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=120.0,
        future_low=90.0,
        future_final_close=90.0,
    ) is False


def test_invalid_structural_frontier_fails_closed() -> None:
    with pytest.raises(ValueError, match="prior structural frontier"):
        target_v2.higher_timeframe_structural_failure_target(
            anchor_direction=1,
            prior_peak=99.0,
            prior_floor=100.0,
            future_high=101.0,
            future_low=98.0,
            future_final_close=98.0,
        )


def test_invalid_anchor_fails_closed() -> None:
    with pytest.raises(ValueError, match="anchor_direction"):
        target_v2.higher_timeframe_structural_failure_target(
            anchor_direction=2,
            prior_peak=110.0,
            prior_floor=100.0,
            future_high=112.0,
            future_low=98.0,
            future_final_close=99.0,
        )
