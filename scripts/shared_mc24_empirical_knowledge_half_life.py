#!/usr/bin/env python3
"""MC24 empirical half-life and validated MC23 binding in native Shared Lab."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np

import shared_mc23_real_novelty_detection as novelty_source
import shared_mc23_validated_novel_regime_adaptation as mc23_runner
import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.mc23_validated_novel_regime_adaptation import (
    ADAPTIVE_INTERACTION_NAMES,
    BASELINE_FEATURE_NAMES,
    build_adaptive_design,
    evaluate_adaptation,
    fit_frozen_ridge_projection,
)
from qore.infrastructure.core_stack_v2.mc24_empirical_half_life import (
    KnowledgeHalfLifeBin,
    measure_empirical_half_life,
)
from qore.infrastructure.core_stack_v2.meta_learning_regime_adaptation import (
    NoveltyState,
    assess_regime_novelty,
)

IDENTITY = "QORE_SHARED_MC24_VALIDATED_ADAPTATION_HALF_LIFE_001"
PREREGISTRATION = (
    "QORE_SHARED_MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_PREREGISTRATION_001"
)
BIN_DAYS = 90


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _selected_partition(
    root: Path,
    partition: str,
) -> tuple[np.ndarray, np.ndarray, tuple[Any, ...]]:
    rows = source._aligned_source_rows(
        mc23_runner._paths(root, partition),
        partition=f"mc24_half_life_{partition}",
        require_future=True,
    )
    features: list[tuple[float, ...]] = []
    targets: list[tuple[float, ...]] = []
    source_times: list[Any] = []
    for observation, _states, pre, future in rows:
        if future is None:
            raise AssertionError("MC24 half-life requires attached future evidence")
        novelty = assess_regime_novelty(
            novelty_source._uncertainty(observation),
            closest_known_structures=(
                "MC16_REGIME_MEMORY",
                "WP04_LATENT_REPRESENTATION",
            ),
        )
        if novelty.state not in {NoveltyState.NOVEL, NoveltyState.NEAR_KNOWN}:
            continue
        features.append(mc23_runner._baseline_features(observation))
        targets.append(mc23_runner._future_targets(pre=pre, future=future))
        source_times.append(observation.as_of)

    expected = mc23_runner.EXPECTED_COUNTS[partition]["novel_or_near"]
    if len(features) != expected:
        raise ValueError(
            f"{partition} selected population drift: {len(features)} != {expected}"
        )
    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(targets, dtype=np.float64),
        tuple(source_times),
    )


def _evaluate(
    *,
    root: Path,
    mc23_result: dict[str, Any],
    prior_mc24: dict[str, Any],
) -> dict[str, object]:
    if mc23_result.get("status") != (
        "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_PASS"
    ):
        raise ValueError("MC24 cannot bind an unvalidated MC23 adaptation")
    if mc23_result.get("real_novel_regime_validated_adaptation") is not True:
        raise ValueError("MC23 validated adaptation flag missing")
    if prior_mc24.get("status") != "MC24_REAL_REGRESSION_SUITE_BOUND_PASS":
        raise ValueError("prior MC24 real regression suite evidence missing")
    if prior_mc24.get("catastrophic_forgetting_detected") is not False:
        raise ValueError("prior MC24 regression evidence detected forgetting")

    r6_x, r6_y, _r6_times = _selected_partition(root, "r6")
    r5_x, r5_y, r5_times = _selected_partition(root, "r5")
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
    if baseline.fingerprint() != mc23_result.get("baseline_model_fingerprint"):
        raise ValueError("MC23 baseline model fingerprint drift")
    if adaptive.fingerprint() != mc23_result.get("adaptive_model_fingerprint"):
        raise ValueError("MC23 adaptive model fingerprint drift")

    origin = min(r5_times)
    grouped: dict[int, list[int]] = {}
    for index, observed_at in enumerate(r5_times):
        age_days = int((observed_at - origin).total_seconds() // 86_400)
        grouped.setdefault(age_days // BIN_DAYS, []).append(index)

    bins: list[KnowledgeHalfLifeBin] = []
    bin_payloads: list[dict[str, object]] = []
    for bin_index in sorted(grouped):
        indexes = np.asarray(grouped[bin_index], dtype=np.int64)
        validation = evaluate_adaptation(
            baseline_model=baseline,
            adaptive_model=adaptive,
            baseline_features=r5_x[indexes],
            adaptive_features=r5_adaptive[indexes],
            targets=r5_y[indexes],
        )
        start_age = bin_index * BIN_DAYS
        end_age = (bin_index + 1) * BIN_DAYS
        row = KnowledgeHalfLifeBin(
            bin_index=bin_index,
            start_age_days=start_age,
            end_age_days=end_age,
            sample_count=validation.sample_count,
            pooled_incremental_information_bps=(
                validation.pooled_incremental_information_bps
            ),
            maximum_target_regression_bps=(
                validation.maximum_target_regression_bps
            ),
        )
        bins.append(row)
        bin_payloads.append(
            {
                **asdict(row),
                "source_start": (origin + timedelta(days=start_age)).isoformat(),
                "source_end_exclusive": (
                    origin + timedelta(days=end_age)
                ).isoformat(),
                "positive_target_count": validation.positive_target_count,
                "incremental_information_bps": (
                    validation.incremental_information_bps
                ),
            }
        )

    assessment = measure_empirical_half_life(tuple(bins))
    completed = (
        assessment.empirical_half_life_validated
        and assessment.retained_knowledge_non_degradation_pass
    )
    return {
        "identity": IDENTITY,
        "preregistration": PREREGISTRATION,
        "status": (
            "MC24_VALIDATED_ADAPTATION_HALF_LIFE_PASS"
            if completed
            else "MC24_VALIDATED_ADAPTATION_HALF_LIFE_NOT_CLOSED"
        ),
        "mc23_identity": mc23_result.get("identity"),
        "mc23_baseline_model_fingerprint": baseline.fingerprint(),
        "mc23_adaptive_model_fingerprint": adaptive.fingerprint(),
        "mc23_real_regime_adaptation_bound": True,
        "prior_real_regression_suite_bound": True,
        "half_life_bins": bin_payloads,
        "half_life_assessment": asdict(assessment),
        "empirical_half_life_validated": (
            assessment.empirical_half_life_validated
        ),
        "catastrophic_forgetting_detected": (
            assessment.catastrophic_forgetting_detected
        ),
        "retained_knowledge_non_degradation_pass": (
            assessment.retained_knowledge_non_degradation_pass
        ),
        "stable_certified_knowledge_overwritten": False,
        "r5_refit": False,
        "threshold_retuning_after_r5": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "mc24_completed_and_proven": completed,
        "next_gate": (
            "MC25_SAME_LINEAGE_PERFORMANCE_STRESS"
            if completed
            else "MC24_REMAINS_OPEN"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--mc23-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not zipfile.is_zipfile(args.dataset):
        raise SystemExit("MC24 Shared Lab dataset must be a ZIP")
    mc23_result = _load(args.mc23_result)
    with tempfile.TemporaryDirectory(prefix="qore-mc24-half-life-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(args.dataset) as archive:
            archive.extractall(root)
        prior_mc24 = _load(root / "sealed" / "mc24-real-regression-suite.json")
        payload = _evaluate(
            root=root,
            mc23_result=mc23_result,
            prior_mc24=prior_mc24,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if payload["mc24_completed_and_proven"] else 2)


if __name__ == "__main__":
    main()
