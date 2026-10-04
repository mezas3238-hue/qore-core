#!/usr/bin/env python3
"""WP-06 / MC-17 agency-state incremental calibration experiment."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import shared_sti2_real_opportunity_discovery as v1
import shared_sti2_v2_trajectory_heads as v2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from qore.infrastructure.core_stack_v2.market_agency_model import (
    SharedAgencyMechanism,
    assess_market_agency,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)

IDENTITY = "QORE_SHARED_WP06_MARKET_AGENCY_CALIBRATION_001"
TARGET_BPS = 6_500
TRAIN_FRACTION = 0.70
ALL_CLASSES = (
    "CONTINUATION",
    "EXPANSION",
    "NO_MATERIAL",
    "RELATIONSHIP_TRANSITION",
    "REVERSAL",
)


def _baseline_features(observation: SharedOpportunitySourceObservation) -> list[float]:
    values = [
        observation.direction_sign * 10_000,
        observation.data_integrity_bps,
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
    ]
    return [value / 10_000.0 for value in values]


def _treatment_features(observation: SharedOpportunitySourceObservation) -> list[float]:
    assessment = assess_market_agency(observation)
    features = _baseline_features(observation)
    dominant = assessment.dominant_mechanism
    for hypothesis in assessment.hypotheses:
        features.extend(
            [
                hypothesis.support_bps / 10_000.0,
                hypothesis.contradiction_bps / 10_000.0,
                hypothesis.uncertainty_bps / 10_000.0,
            ]
        )
    for mechanism in SharedAgencyMechanism:
        features.append(1.0 if dominant is mechanism else 0.0)
    features.append(1.0 if assessment.insufficient else 0.0)
    return features


def _label(pre: dict[str, tuple[object, ...]], future: dict[str, tuple[object, ...]]) -> str:
    target = v1._target_state(pre, future)
    scores = v2._target_mechanism_scores(target)
    mechanism, score = max(
        scores.items(),
        key=lambda item: (item[1], item[0].value),
    )
    if score < TARGET_BPS:
        return "NO_MATERIAL"
    return mechanism.value


def _rows(paths: dict[str, Path], partition: str) -> list[tuple[list[float], list[float], str]]:
    aligned = v1._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    rows: list[tuple[list[float], list[float], str]] = []
    for observation, _states, pre, future in aligned:
        if future is None:
            raise AssertionError("WP-06 calibration requires offline future target")
        baseline = _baseline_features(observation)
        treatment = _treatment_features(observation)
        # Both inference feature vectors are sealed before attaching the label.
        label = _label(pre, future)
        rows.append((baseline, treatment, label))
    if not rows:
        raise ValueError(f"{partition}: no aligned rows")
    return rows


def _xy(
    rows: Iterable[tuple[list[float], list[float], str]],
    *,
    treatment: bool,
) -> tuple[np.ndarray, np.ndarray]:
    materialized = list(rows)
    x = np.asarray(
        [row[1] if treatment else row[0] for row in materialized],
        dtype=np.float64,
    )
    y = np.asarray([row[2] for row in materialized], dtype=object)
    return x, y


def _model() -> object:
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            max_iter=500,
            random_state=638,
            solver="lbfgs",
        ),
    )


def _multiclass_brier(
    *,
    probabilities: np.ndarray,
    classes: tuple[str, ...],
    labels: np.ndarray,
) -> float:
    class_index = {name: index for index, name in enumerate(classes)}
    total = 0.0
    for row, label in zip(probabilities, labels, strict=True):
        for name, index in class_index.items():
            target = 1.0 if str(label) == name else 0.0
            total += (float(row[index]) - target) ** 2
    return total / len(labels)


def _evaluate(model: object, x: np.ndarray, y: np.ndarray) -> dict[str, float | int]:
    probabilities = model.predict_proba(x)  # type: ignore[attr-defined]
    predicted = model.predict(x)  # type: ignore[attr-defined]
    classes = tuple(str(item) for item in model.classes_)  # type: ignore[attr-defined]
    if set(classes) != set(ALL_CLASSES):
        raise ValueError(f"model classes incomplete: {classes}")
    order = [classes.index(name) for name in ALL_CLASSES]
    ordered_probabilities = probabilities[:, order]
    return {
        "sample_count": int(len(y)),
        "log_loss": float(log_loss(y, ordered_probabilities, labels=list(ALL_CLASSES))),
        "multiclass_brier": float(
            _multiclass_brier(
                probabilities=ordered_probabilities,
                classes=ALL_CLASSES,
                labels=y,
            )
        ),
        "accuracy": float(accuracy_score(y, predicted)),
    }


def _comparison(
    baseline: dict[str, float | int],
    treatment: dict[str, float | int],
) -> dict[str, object]:
    gates = {
        "treatment_log_loss_lt_baseline": (
            float(treatment["log_loss"]) < float(baseline["log_loss"])
        ),
        "treatment_multiclass_brier_lt_baseline": (
            float(treatment["multiclass_brier"])
            < float(baseline["multiclass_brier"])
        ),
        "treatment_accuracy_gte_baseline": (
            float(treatment["accuracy"]) >= float(baseline["accuracy"])
        ),
    }
    return {
        "baseline": baseline,
        "treatment": treatment,
        "log_loss_improvement": (
            float(baseline["log_loss"]) - float(treatment["log_loss"])
        ),
        "brier_improvement": (
            float(baseline["multiclass_brier"])
            - float(treatment["multiclass_brier"])
        ),
        "accuracy_delta": (
            float(treatment["accuracy"]) - float(baseline["accuracy"])
        ),
        "gates": gates,
        "pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    r6 = _rows(
        {
            "NAS100": args.r6_nas,
            "SP500": args.r6_sp,
            "US30": args.r6_us,
        },
        "r6",
    )
    r5 = _rows(
        {
            "NAS100": args.r5_nas,
            "SP500": args.r5_sp,
            "US30": args.r5_us,
        },
        "r5",
    )

    split = int(len(r6) * TRAIN_FRACTION)
    if split <= 0 or split >= len(r6):
        raise ValueError("invalid R6 chronological split")
    train = r6[:split]
    r6_validation = r6[split:]

    xb_train, y_train = _xy(train, treatment=False)
    xt_train, yt_train = _xy(train, treatment=True)
    if not np.array_equal(y_train, yt_train):
        raise AssertionError("baseline/treatment training labels diverged")
    if set(str(item) for item in y_train) != set(ALL_CLASSES):
        raise ValueError("R6 training prefix does not contain all frozen classes")

    baseline_model = _model()
    treatment_model = _model()
    baseline_model.fit(xb_train, y_train)  # type: ignore[attr-defined]
    treatment_model.fit(xt_train, yt_train)  # type: ignore[attr-defined]

    results: dict[str, object] = {}
    for name, rows in (("r6_tail", r6_validation), ("r5", r5)):
        xb, yb = _xy(rows, treatment=False)
        xt, yt = _xy(rows, treatment=True)
        if not np.array_equal(yb, yt):
            raise AssertionError("baseline/treatment validation labels diverged")
        results[name] = _comparison(
            _evaluate(baseline_model, xb, yb),
            _evaluate(treatment_model, xt, yt),
        )

    passed = all(bool(result["pass"]) for result in results.values())  # type: ignore[index]
    payload = {
        "identity": IDENTITY,
        "status": (
            "WP06_MARKET_AGENCY_CALIBRATION_OOS_PASS"
            if passed
            else "WP06_MARKET_AGENCY_CALIBRATION_OOS_FALSIFIED"
        ),
        "r6_train_count": len(train),
        "results": results,
        "scenario_discrimination_improved": passed,
        "calibration_improved": passed,
        "wp06_exit_gate_science_pass": passed,
        "agency_engine_changed": False,
        "hyperparameter_search_used": False,
        "r5_used_for_fit": False,
        "future_market_used_for_inference": False,
        "outcome_used_for_agency_inference": False,
        "wp05_dependency_closed": False,
        "wp06_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
