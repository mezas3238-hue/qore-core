#!/usr/bin/env python3
"""Preregistered consumed-development calibration for MC18 failure mass."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import shared_sti2_real_opportunity_discovery as source
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from qore.infrastructure.core_stack_v2.counterfactual_world_calibration import (
    CounterfactualFailureCalibration,
    raw_failure_probability_bps,
)
from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    build_counterfactual_world_distribution,
)
from qore.infrastructure.core_stack_v2.dynamic_causal_graph import CausalConcept

IDENTITY = "QORE_SHARED_MC18_COUNTERFACTUAL_FAILURE_CALIBRATION_001"
TARGET_BPS = 6_500
RANDOM_STATE = 1818
TARGET_DEFINITION = (
    "MAX_REVERSAL_STRUCTURAL_FAILURE_ANOMALY_GTE_6500_BPS_AT_30M"
)


def _rows(paths: dict[str, Path], partition: str) -> tuple[np.ndarray, np.ndarray]:
    aligned = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=True,
    )
    x: list[list[float]] = []
    y: list[int] = []
    for observation, _states, pre, future in aligned:
        if future is None:
            raise AssertionError("MC18 calibration requires offline development target")
        distribution = build_counterfactual_world_distribution(observation)
        raw_bps = raw_failure_probability_bps(distribution)
        # The source-only prediction is sealed before the consumed future label.
        target = source._target_state(pre, future)
        realized = int(
            max(
                target[CausalConcept.REVERSAL],
                target[CausalConcept.STRUCTURAL_FAILURE],
                target[CausalConcept.ANOMALY],
            )
            >= TARGET_BPS
        )
        x.append([raw_bps / 10_000.0])
        y.append(realized)
    if not x:
        raise ValueError(f"{partition}: no aligned development rows")
    labels = np.asarray(y, dtype=np.int8)
    if len(set(int(item) for item in labels)) != 2:
        raise ValueError(f"{partition}: binary target lacks both classes")
    return np.asarray(x, dtype=np.float64), labels


def _clip(probability: np.ndarray) -> np.ndarray:
    return np.clip(probability, 1e-6, 1.0 - 1e-6)


def _metrics(probability: np.ndarray, labels: np.ndarray) -> dict[str, float | int]:
    p = _clip(probability)
    brier = float(np.mean((p - labels) ** 2))
    return {
        "sample_count": int(len(labels)),
        "event_count": int(labels.sum()),
        "event_rate": float(labels.mean()),
        "brier": brier,
        "log_loss": float(log_loss(labels, p, labels=[0, 1])),
    }


def run(
    *,
    r6_paths: dict[str, Path],
    r5_paths: dict[str, Path],
) -> dict[str, Any]:
    x_train, y_train = _rows(r6_paths, "mc18_calibration_r6_consumed")
    x_validation, y_validation = _rows(
        r5_paths,
        "mc18_calibration_r5_consumed_validation",
    )

    model = LogisticRegression(
        C=1.0,
        max_iter=500,
        random_state=RANDOM_STATE,
        solver="lbfgs",
    )
    model.fit(x_train, y_train)
    coefficient = float(model.coef_[0][0])
    intercept = float(model.intercept_[0])
    if not math.isfinite(coefficient) or not math.isfinite(intercept):
        raise ValueError("MC18 calibration fit produced non-finite coefficients")

    raw = x_validation[:, 0]
    calibrated = model.predict_proba(x_validation)[:, 1]
    baseline = _metrics(raw, y_validation)
    treatment = _metrics(calibrated, y_validation)
    gates = {
        "coefficient_positive": coefficient > 0.0,
        "calibrated_brier_lt_raw": (
            float(treatment["brier"]) < float(baseline["brier"])
        ),
        "calibrated_log_loss_lt_raw": (
            float(treatment["log_loss"]) < float(baseline["log_loss"])
        ),
    }
    passed = all(gates.values())

    frozen_calibration = None
    if passed:
        calibration = CounterfactualFailureCalibration(
            calibration_id="MC18_FAILURE_CALIBRATION_R6_TO_R5_V1",
            intercept=intercept,
            coefficient=coefficient,
            fitted_on="R6_CONSUMED_ONLY",
            target_definition=TARGET_DEFINITION,
        )
        frozen_calibration = {
            "calibration_id": calibration.calibration_id,
            "intercept": calibration.intercept,
            "coefficient": calibration.coefficient,
            "fitted_on": calibration.fitted_on,
            "target_definition": calibration.target_definition,
            "fingerprint": calibration.fingerprint(),
        }

    return {
        "identity": IDENTITY,
        "status": (
            "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_PASS"
            if passed
            else "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_FALSIFIED"
        ),
        "target_definition": TARGET_DEFINITION,
        "fit_partition": "R6_CONSUMED_ONLY",
        "validation_partition": "R5_CONSUMED_ONLY",
        "raw_validation": baseline,
        "calibrated_validation": treatment,
        "gates": gates,
        "frozen_calibration": frozen_calibration,
        "engine_changed": False,
        "future_oos_used_for_fit": False,
        "future_oos_used_for_validation": False,
        "protected_final_holdout_opened": False,
        "independent_value_proven": False,
        "mc18_completed_and_proven": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        for market in ("nas", "sp", "us"):
            parser.add_argument(f"--{partition}-{market}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(partition: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }

    payload = run(r6_paths=paths("r6"), r5_paths=paths("r5"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
