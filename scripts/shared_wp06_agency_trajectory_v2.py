#!/usr/bin/env python3
"""WP-06 Market Agency V2 temporal trajectory OOS experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as target
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

IDENTITY = "QORE_SHARED_WP06_MARKET_AGENCY_TRAJECTORY_V2_001"
TARGET_BPS = 6_500
ALL_CLASSES = (
    "CONTINUATION",
    "EXPANSION",
    "NO_MATERIAL",
    "RELATIONSHIP_TRANSITION",
    "REVERSAL",
)


def _raw(observation: SharedOpportunitySourceObservation) -> list[float]:
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


def _target(pre, future) -> str:
    state = source._target_state(pre, future)
    scores = target._target_mechanism_scores(state)
    mechanism, score = max(
        scores.items(),
        key=lambda item: (item[1], item[0].value),
    )
    return "NO_MATERIAL" if score < TARGET_BPS else mechanism.value


def _agency_margin(assessment) -> tuple[SharedAgencyMechanism | None, int]:
    dominant = assessment.dominant_mechanism
    if dominant is None:
        return None, 0
    row = next(item for item in assessment.hypotheses if item.mechanism is dominant)
    return dominant, row.support_bps - row.contradiction_bps


def _rows(
    paths: dict[str, Path],
    partition: str,
) -> list[tuple[list[float], list[float], str]]:
    aligned = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    previous: dict[
        str,
        tuple[SharedOpportunitySourceObservation, object, SharedAgencyMechanism | None, int, int],
    ] = {}
    rows: list[tuple[list[float], list[float], str]] = []

    for observation, _states, pre, future in aligned:
        if future is None:
            raise AssertionError("WP06 V2 requires offline future target")
        assessment = assess_market_agency(observation)
        dominant, margin = _agency_margin(assessment)
        prior = previous.get(observation.asset)
        if prior is not None:
            prior_observation, prior_assessment, prior_dominant, prior_margin, run = prior
            baseline = _raw(prior_observation) + _raw(observation)

            trajectory: list[float] = []
            for mechanism in SharedAgencyMechanism:
                trajectory.append(1.0 if prior_dominant is mechanism else 0.0)
            for mechanism in SharedAgencyMechanism:
                trajectory.append(1.0 if dominant is mechanism else 0.0)
            changed = float(prior_dominant is not dominant)
            trajectory.extend(
                [
                    changed,
                    prior_margin / 10_000.0,
                    margin / 10_000.0,
                    (margin - prior_margin) / 10_000.0,
                    min(20, run) / 20.0,
                    float(assessment.insufficient),
                    float(prior_assessment.insufficient),
                ]
            )
            treatment = baseline + trajectory
            # Both feature vectors are sealed before target attachment.
            label = _target(pre, future)
            rows.append((baseline, treatment, label))
            next_run = run + 1 if prior_dominant is dominant else 1
        else:
            next_run = 1

        previous[observation.asset] = (
            observation,
            assessment,
            dominant,
            margin,
            next_run,
        )

    if not rows:
        raise ValueError(f"{partition}: no agency trajectory rows")
    return rows


def _xy(rows, *, treatment: bool):
    return (
        np.asarray([row[1] if treatment else row[0] for row in rows], dtype=float),
        np.asarray([row[2] for row in rows], dtype=object),
    )


def _model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            solver="lbfgs",
            max_iter=500,
            random_state=638,
        ),
    )


def _brier(probabilities, classes, labels) -> float:
    index = {name: i for i, name in enumerate(classes)}
    total = 0.0
    for probability, label in zip(probabilities, labels, strict=True):
        for name in ALL_CLASSES:
            target_value = 1.0 if str(label) == name else 0.0
            total += (float(probability[index[name]]) - target_value) ** 2
    return total / len(labels)


def _metrics(model, x, y) -> dict[str, float | int]:
    probability = model.predict_proba(x)
    predicted = model.predict(x)
    classes = tuple(str(item) for item in model.classes_)
    if set(classes) != set(ALL_CLASSES):
        raise ValueError(f"incomplete model classes: {classes}")
    return {
        "sample_count": int(len(y)),
        "log_loss": float(log_loss(y, probability, labels=list(classes))),
        "multiclass_brier": float(_brier(probability, classes, y)),
        "accuracy": float(accuracy_score(y, predicted)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5", "oos"):
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

    development = _rows(paths("r6"), "wp06_v2_fit_r6")
    development.extend(_rows(paths("r5"), "wp06_v2_fit_r5"))
    oos = _rows(paths("oos"), "wp06_v2_temporal_oos")

    xb_train, yb_train = _xy(development, treatment=False)
    xt_train, yt_train = _xy(development, treatment=True)
    if not np.array_equal(yb_train, yt_train):
        raise AssertionError("V2 baseline/treatment fit labels diverged")

    baseline_model = _model()
    treatment_model = _model()
    baseline_model.fit(xb_train, yb_train)
    treatment_model.fit(xt_train, yt_train)

    xb_oos, yb_oos = _xy(oos, treatment=False)
    xt_oos, yt_oos = _xy(oos, treatment=True)
    if not np.array_equal(yb_oos, yt_oos):
        raise AssertionError("V2 baseline/treatment OOS labels diverged")

    baseline = _metrics(baseline_model, xb_oos, yb_oos)
    treatment_metrics = _metrics(treatment_model, xt_oos, yt_oos)
    gates = {
        "treatment_log_loss_lt_baseline": (
            float(treatment_metrics["log_loss"]) < float(baseline["log_loss"])
        ),
        "treatment_multiclass_brier_lt_baseline": (
            float(treatment_metrics["multiclass_brier"])
            < float(baseline["multiclass_brier"])
        ),
        "treatment_accuracy_gte_baseline": (
            float(treatment_metrics["accuracy"]) >= float(baseline["accuracy"])
        ),
    }
    passed = all(gates.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "WP06_AGENCY_TRAJECTORY_V2_TEMPORAL_OOS_PASS"
            if passed
            else "WP06_AGENCY_TRAJECTORY_V2_TEMPORAL_OOS_FALSIFIED"
        ),
        "development_row_count": len(development),
        "oos_row_count": len(oos),
        "baseline": baseline,
        "treatment": treatment_metrics,
        "improvements": {
            "log_loss": float(baseline["log_loss"]) - float(treatment_metrics["log_loss"]),
            "multiclass_brier": (
                float(baseline["multiclass_brier"])
                - float(treatment_metrics["multiclass_brier"])
            ),
            "accuracy": float(treatment_metrics["accuracy"]) - float(baseline["accuracy"]),
        },
        "gates": gates,
        "agency_trajectory_scientific_value_pass": passed,
        "oos_used_for_fit": False,
        "hyperparameter_search_used": False,
        "outcome_used_for_agency_inference": False,
        "future_market_used_for_agency_inference": False,
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
