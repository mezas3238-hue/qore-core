#!/usr/bin/env python3
"""Real source-only binding for MC-05 hierarchical temporal world reasoning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept
from qore.infrastructure.core_stack_v2.hierarchical_world_model import (
    DirectionalState,
    WorldLevelState,
    WorldScale,
    reconcile_world_levels,
)

IDENTITY = "QORE_SHARED_MC05_HIERARCHICAL_WORLD_REAL_REPLAY_001"
REQUIRED_SCALES = {
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.CROSS_MARKET_REGIME,
}


def _clamp(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _direction(value: float) -> DirectionalState:
    sign = _sign(value)
    if sign > 0:
        return DirectionalState.BULLISH
    if sign < 0:
        return DirectionalState.BEARISH
    return DirectionalState.NEUTRAL


def _persistence_bps(bars: tuple[Any, ...]) -> int:
    metric = source._metric(bars)
    direction = _sign(metric.net_bps)
    if direction == 0:
        return 0
    moves = [
        _sign(bars[index].close - bars[index - 1].close)
        for index in range(1, len(bars))
    ]
    nonzero = sum(move != 0 for move in moves)
    if nonzero == 0:
        return 0
    aligned = sum(move == direction for move in moves)
    return aligned * 10_000 // nonzero


def _level(
    bars: tuple[Any, ...],
    scale: WorldScale,
    states: dict[CausalConcept, int],
) -> WorldLevelState:
    metric = source._metric(bars)
    persistence = _persistence_bps(bars)
    confidence = _clamp(round(metric.efficiency * 10_000))
    fragility = _clamp(
        (
            states[CausalConcept.STRUCTURAL_FRAGILITY]
            + (10_000 - persistence)
        )
        // 2
    )
    transition = _clamp(
        (
            states[CausalConcept.REGIME_TRANSITION]
            + (10_000 - confidence)
        )
        // 2
    )
    return WorldLevelState(
        scale=scale,
        directional_state=_direction(metric.net_bps),
        confidence_bps=confidence,
        persistence_bps=persistence,
        fragility_bps=fragility,
        transition_probability_bps=transition,
    )


def _cross_market_level(
    pre: dict[str, tuple[Any, ...]],
    states: dict[CausalConcept, int],
) -> WorldLevelState:
    metrics = {
        market: source._metric(pre[market][-60:])
        for market in ("NAS100", "SP500", "US30")
    }
    signs = [_sign(metric.net_bps) for metric in metrics.values()]
    signed = sum(signs)
    if signed == len(signs):
        direction = DirectionalState.BULLISH
    elif signed == -len(signs):
        direction = DirectionalState.BEARISH
    else:
        direction = DirectionalState.CONTESTED
    persistence = sum(
        _persistence_bps(pre[market][-60:])
        for market in ("NAS100", "SP500", "US30")
    ) // 3
    confidence = abs(signed) * 10_000 // len(signs)
    return WorldLevelState(
        scale=WorldScale.CROSS_MARKET_REGIME,
        directional_state=direction,
        confidence_bps=confidence,
        persistence_bps=persistence,
        fragility_bps=states[CausalConcept.STRUCTURAL_FRAGILITY],
        transition_probability_bps=states[CausalConcept.REGIME_TRANSITION],
    )


def _levels(
    pre: dict[str, tuple[Any, ...]],
    states: dict[CausalConcept, int],
) -> tuple[WorldLevelState, ...]:
    nas = pre["NAS100"]
    return (
        _level(nas[-2:], WorldScale.M1, states),
        _level(nas[-3:], WorldScale.M3, states),
        _level(nas[-5:], WorldScale.M5, states),
        _level(nas[-15:], WorldScale.M15, states),
        _level(nas[-60:], WorldScale.H1, states),
        _cross_market_level(pre, states),
    )


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    deterministic = 0
    authority_violations = 0
    pullback_only = 0
    structural_reversal = 0
    covered_scales: set[WorldScale] = set()

    for _observation, states, pre, future in rows:
        if future is not None:
            raise AssertionError("MC05 source replay cannot attach future evidence")
        levels = _levels(pre, states)
        first = reconcile_world_levels(levels)
        second = reconcile_world_levels(levels)
        deterministic += int(first == second)
        covered_scales.update(level.scale for level in first.levels)
        authority_violations += int(
            first.outcome_used
            or first.pnl_used
            or first.future_market_used
            or first.execution_authority
            or first.risk_authority
            or first.sizing_authority
        )
        pullback_only += int(first.lower_timeframe_pullback_only)
        structural_reversal += int(first.structural_reversal_confirmed)

    opposed_cases = pullback_only + structural_reversal
    passed = (
        bool(rows)
        and deterministic == len(rows)
        and authority_violations == 0
        and REQUIRED_SCALES.issubset(covered_scales)
        and opposed_cases > 0
        and pullback_only > 0
    )
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_count": deterministic,
        "authority_violation_count": authority_violations,
        "covered_scales": sorted(scale.value for scale in covered_scales),
        "opposed_cross_level_case_count": opposed_cases,
        "lower_timeframe_pullback_only_count": pullback_only,
        "structural_reversal_confirmed_count": structural_reversal,
        "bottom_up_reasoning_observed": opposed_cases > 0,
        "top_down_context_preserved": pullback_only > 0,
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    results = {
        name: _partition(paths(name), f"mc05_{name}")
        for name in ("r6", "r5")
    }
    passed = all(bool(item["pass"]) for item in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC05_HIERARCHICAL_WORLD_REAL_DATA_BOUND_PASS"
            if passed
            else "MC05_HIERARCHICAL_WORLD_REAL_DATA_BOUND_FAIL"
        ),
        "results": results,
        "bottom_up_reasoning": True,
        "top_down_reasoning": True,
        "source_time_only": True,
        "future_market_used": False,
        "outcome_used": False,
        "productive_authority": False,
        "bound_scales": sorted(scale.value for scale in REQUIRED_SCALES),
        "unbound_scales": [
            "MICROSTRUCTURE",
            "SECONDS",
            "H4",
            "DAILY",
            "WEEKLY",
            "MACRO_REGIME",
        ],
        "external_dependency": "B_GLOBAL_WORLD_MULTISCALE_BINDING",
        "mc05_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
