#!/usr/bin/env python3
"""One-shot MC23 validated novel-regime adaptation on sealed R6 -> R5 evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

import shared_mc23_real_novelty_detection as novelty_source
import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.mc23_validated_novel_regime_adaptation import (
    ADAPTIVE_INTERACTION_NAMES,
    BASELINE_FEATURE_NAMES,
    TARGET_NAMES,
    build_adaptive_design,
    evaluate_adaptation,
    fit_frozen_ridge_projection,
)
from qore.infrastructure.core_stack_v2.meta_learning_regime_adaptation import (
    NoveltyState,
    assess_regime_novelty,
)

IDENTITY = "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_001"
PREREGISTRATION = (
    "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_001"
)
EXPECTED_COUNTS = {
    "r6": {"total": 21_123, "novel_or_near": 8_011},
    "r5": {"total": 23_363, "novel_or_near": 9_882},
}


def _paths(root: Path, partition: str) -> dict[str, Path]:
    base = root / partition / "fresh"
    return {
        "NAS100": base / "NAS100" / "market-evidence.json",
        "SP500": base / "SP500" / "market-evidence.json",
        "US30": base / "US30" / "market-evidence.json",
    }


def _baseline_features(observation: Any) -> tuple[float, ...]:
    raw = (
        observation.compression_bps,
        observation.liquidity_accumulation_bps,
        observation.failed_auction_bps,
        observation.displacement_bps,
        observation.acceptance_bps,
        observation.absorption_bps,
        observation.leader_confirmation_bps,
        observation.leader_divergence_bps,
        observation.momentum_persistence_bps,
        observation.momentum_decay_bps,
        observation.structural_fragility_bps,
        observation.liquidity_vacuum_bps,
        observation.regime_transition_bps,
        observation.anomaly_bps,
    )
    return tuple(float(value) / 10_000.0 for value in raw)


def _future_targets(
    *,
    pre: dict[str, tuple[Any, ...]],
    future: dict[str, tuple[Any, ...]],
) -> tuple[float, ...]:
    nas_future = future["NAS100"]
    metric = source._metric(nas_future)
    source_close = float(pre["NAS100"][-1].close)
    future_close = float(nas_future[-1].close)
    net_return_bps = (
        0.0
        if source_close == 0.0
        else (future_close / source_close - 1.0) * 10_000.0
    )
    return (
        net_return_bps,
        abs(net_return_bps),
        float(metric.range_mean_bps),
        float(metric.efficiency),
    )


def _partition(
    root: Path,
    partition: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    rows = source._aligned_source_rows(
        _paths(root, partition),
        partition=f"mc23_adaptation_{partition}",
        require_future=True,
    )
    features: list[tuple[float, ...]] = []
    targets: list[tuple[float, ...]] = []
    source_times: list[str] = []
    state_counts = {
        NoveltyState.KNOWN.value: 0,
        NoveltyState.NEAR_KNOWN.value: 0,
        NoveltyState.NOVEL.value: 0,
        NoveltyState.UNRESOLVED.value: 0,
    }

    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("MC23 adaptation validation requires attached future")
        novelty = assess_regime_novelty(
            novelty_source._uncertainty(observation),
            closest_known_structures=(
                "MC16_REGIME_MEMORY",
                "WP04_LATENT_REPRESENTATION",
            ),
        )
        state_counts[novelty.state.value] += 1
        if novelty.state not in {NoveltyState.NOVEL, NoveltyState.NEAR_KNOWN}:
            continue
        features.append(_baseline_features(observation))
        targets.append(_future_targets(pre=pre, future=future))
        source_times.append(observation.as_of.isoformat())

    expected = EXPECTED_COUNTS[partition]
    if len(rows) != expected["total"]:
        raise ValueError(
            f"{partition} total population drift: {len(rows)} != {expected['total']}"
        )
    if len(features) != expected["novel_or_near"]:
        raise ValueError(
            f"{partition} novel population drift: "
            f"{len(features)} != {expected['novel_or_near']}"
        )
    if not features or not targets:
        raise ValueError(f"{partition} adaptation population is empty")

    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(targets, dtype=np.float64),
        {
            "partition": partition,
            "source_observation_count": len(rows),
            "scored_novel_or_near_count": len(features),
            "state_counts": state_counts,
            "source_min": min(source_times),
            "source_max": max(source_times),
        },
    )


def _evaluate(root: Path) -> dict[str, object]:
    r6_x, r6_y, r6_meta = _partition(root, "r6")
    r5_x, r5_y, r5_meta = _partition(root, "r5")
    if str(r6_meta["source_max"]) >= str(r5_meta["source_min"]):
        raise ValueError("R6/R5 temporal order invalid")

    r6_adaptive = build_adaptive_design(r6_x)
    r5_adaptive = build_adaptive_design(r5_x)
    baseline = fit_frozen_ridge_projection(
        features=r6_x,
        targets=r6_y,
        feature_names=BASELINE_FEATURE_NAMES,
    )
    adaptive = fit_frozen_ridge_projection(
        features=r6_adaptive,
        targets=r6_y,
        feature_names=BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    validation = evaluate_adaptation(
        baseline_model=baseline,
        adaptive_model=adaptive,
        baseline_features=r5_x,
        adaptive_features=r5_adaptive,
        targets=r5_y,
    )

    # Exact same frozen computation must repeat deterministically.
    baseline_repeat = fit_frozen_ridge_projection(
        features=r6_x,
        targets=r6_y,
        feature_names=BASELINE_FEATURE_NAMES,
    )
    adaptive_repeat = fit_frozen_ridge_projection(
        features=r6_adaptive,
        targets=r6_y,
        feature_names=BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    validation_repeat = evaluate_adaptation(
        baseline_model=baseline_repeat,
        adaptive_model=adaptive_repeat,
        baseline_features=r5_x,
        adaptive_features=r5_adaptive,
        targets=r5_y,
    )
    deterministic = (
        baseline.fingerprint() == baseline_repeat.fingerprint()
        and adaptive.fingerprint() == adaptive_repeat.fingerprint()
        and validation == validation_repeat
    )
    if not deterministic:
        raise AssertionError("MC23 adaptation repeat is not deterministic")

    if validation.sample_count < 5_000:
        status = (
            "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_INSUFFICIENT_EVIDENCE"
        )
        passed = False
    elif validation.pass_gate:
        status = "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_PASS"
        passed = True
    else:
        status = (
            "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_"
            "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
        )
        passed = False

    metrics = {
        target: {
            "baseline_mse_z": validation.baseline_mse[index],
            "adaptive_mse_z": validation.adaptive_mse[index],
            "incremental_information_bps": (
                validation.incremental_information_bps[index]
            ),
        }
        for index, target in enumerate(TARGET_NAMES)
    }
    return {
        "identity": IDENTITY,
        "preregistration": PREREGISTRATION,
        "status": status,
        "r6": r6_meta,
        "r5": r5_meta,
        "baseline_feature_names": BASELINE_FEATURE_NAMES,
        "adaptive_interaction_names": ADAPTIVE_INTERACTION_NAMES,
        "target_names": TARGET_NAMES,
        "baseline_model_fingerprint": baseline.fingerprint(),
        "adaptive_model_fingerprint": adaptive.fingerprint(),
        "target_metrics": metrics,
        "validation": asdict(validation),
        "temporal_order_pass": True,
        "deterministic_repeat_pass": deterministic,
        "r5_refit": False,
        "r5_feature_selection": False,
        "threshold_retuning_after_r5": False,
        "future_market_used_for_source_features": False,
        "future_market_used_offline_for_validation": True,
        "pnl_used": False,
        "trader_methodology_used": False,
        "protected_certification_holdout_opened": False,
        "certified_knowledge_mutation": False,
        "productive_authority": False,
        "real_novel_regime_validated_adaptation": passed,
        "mc23_completed_and_proven": passed,
        "next_gate": (
            "BIND_VALIDATED_MC23_ADAPTATION_INTO_MC24"
            if passed
            else "NEW_PREREGISTERED_MECHANISM_REQUIRED"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not zipfile.is_zipfile(args.dataset):
        raise SystemExit("MC23 Shared Lab dataset must be a ZIP")
    with tempfile.TemporaryDirectory(prefix="qore-mc23-adaptation-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(args.dataset) as archive:
            archive.extractall(root)
        payload = _evaluate(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    # Shared Lab persists stdout after its isolated worktree is removed, so the
    # full scientific evidence payload is emitted into the native Lab evidence.
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(
        0 if payload["real_novel_regime_validated_adaptation"] else 2
    )


if __name__ == "__main__":
    main()
