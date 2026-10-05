#!/usr/bin/env python3
"""MC23 candidate 002 — novelty-routed symmetric second-order specialists.

This is a native QORE Shared Lab scientific capsule. It is frozen by
QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_002.

Development: consumed R8/R6/R5 only.
Validation: consumed TEMPORAL_REPLICATION_D, one shot.
Replication: consumed HOLDOUT_E, evaluated only if D passes.
No protected final holdout, P/L, Trader methodology, broker mutation or
productive authority is available here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

from a2_lab_capsule import capsule as base

IDENTITY: Final = "QORE_SHARED_MC23_CANDIDATE_002_ROUTED_SECOND_ORDER_001"
PREREGISTRATION: Final = (
    "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_002"
)
DATASET_SHA256: Final = (
    "d6eed594ae467a0776031c6b65d1f04887a9a4020111f508df7c5223bf057b9f"
)
DEVELOPMENT_PARTITIONS: Final = ("r8", "r6", "r5")
VALIDATION_PARTITION: Final = "replication_d"
REPLICATION_PARTITION: Final = "holdout_e"
ROUTES: Final = ("NEAR_KNOWN", "NOVEL")
RIDGE_LAMBDA: Final = 1.0
MINIMUM_DEVELOPMENT_ROWS_PER_ROUTE: Final = 1_000
D_MINIMUM_ROWS: Final = 3_000
E_MINIMUM_ROWS: Final = 500
MINIMUM_POOLED_INCREMENTAL_BPS: Final = 100
MINIMUM_POSITIVE_TARGETS: Final = 3
MAXIMUM_TARGET_REGRESSION_BPS: Final = 500
D_START: Final = datetime.fromisoformat("2025-07-14T00:00:00+00:00")
D_END: Final = datetime.fromisoformat("2026-07-13T00:00:00+00:00")
E_START: Final = datetime.fromisoformat("2026-07-13T00:00:00+00:00")
E_END: Final = datetime.fromisoformat("2026-09-25T00:00:00+00:00")


@dataclass(frozen=True, slots=True)
class FrozenCandidate:
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    baseline_coefficients: np.ndarray
    specialist_coefficients: tuple[tuple[str, np.ndarray], ...]
    development_route_counts: tuple[tuple[str, int], ...]

    def fingerprint(self) -> str:
        payload = {
            "identity": IDENTITY,
            "preregistration": PREREGISTRATION,
            "ridge_lambda": RIDGE_LAMBDA,
            "x_mean": np.round(self.x_mean, 12).tolist(),
            "x_scale": np.round(self.x_scale, 12).tolist(),
            "y_mean": np.round(self.y_mean, 12).tolist(),
            "y_scale": np.round(self.y_scale, 12).tolist(),
            "baseline_coefficients": np.round(
                self.baseline_coefficients, 12
            ).tolist(),
            "specialist_coefficients": {
                route: np.round(coefficients, 12).tolist()
                for route, coefficients in self.specialist_coefficients
            },
            "development_route_counts": dict(self.development_route_counts),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Validation:
    partition: str
    sample_count: int
    route_counts: tuple[tuple[str, int], ...]
    baseline_mse: tuple[float, ...]
    adaptive_mse: tuple[float, ...]
    incremental_information_bps: tuple[int, ...]
    pooled_incremental_information_bps: int
    positive_target_count: int
    maximum_target_regression_bps: int
    minimum_required_rows: int
    pass_gate: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_dataset(dataset: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    if _sha256_file(dataset) != DATASET_SHA256:
        raise ValueError("MC23 candidate 002 dataset hash mismatch")
    if not zipfile.is_zipfile(dataset):
        raise ValueError("candidate 002 dataset must be ZIP")
    temp = tempfile.TemporaryDirectory(prefix="qore-a2-mc23-002-")
    root = Path(temp.name)
    with zipfile.ZipFile(dataset) as archive:
        archive.extractall(root)
    manifest = json.loads(
        (root / "DATASET-MANIFEST.json").read_text(encoding="utf-8")
    )
    if manifest.get("schema") != "QORE_SHARED_A2_MC23_002_DATASET_001":
        raise ValueError("candidate 002 embedded dataset schema drift")
    return temp, root


def _safe_scale(values: np.ndarray) -> np.ndarray:
    scale = np.asarray(values.std(axis=0), dtype=np.float64)
    return np.where(scale > 1e-12, scale, 1.0)


def _route_rows(features: np.ndarray) -> tuple[str, ...]:
    return tuple(
        base._novelty_state(tuple(float(value) for value in row))
        for row in features
    )


def _second_order_from_standardized(z: np.ndarray) -> np.ndarray:
    if z.ndim != 2 or z.shape[1] != len(base.BASELINE_FEATURE_NAMES):
        raise ValueError("candidate 002 base feature shape drift")
    columns: list[np.ndarray] = [z]
    columns.append(z * z)
    pairs = [
        (z[:, left] * z[:, right])[:, None]
        for left in range(z.shape[1])
        for right in range(left + 1, z.shape[1])
    ]
    if pairs:
        columns.append(np.hstack(pairs))
    design = np.hstack(columns)
    expected = 14 + 14 + 91
    if design.shape[1] != expected:
        raise AssertionError("candidate 002 second-order basis cardinality drift")
    return np.asarray(design, dtype=np.float64)


def _ridge(design: np.ndarray, target_z: np.ndarray) -> np.ndarray:
    if design.ndim != 2 or target_z.ndim != 2:
        raise ValueError("candidate 002 ridge requires matrices")
    if design.shape[0] != target_z.shape[0]:
        raise ValueError("candidate 002 ridge row mismatch")
    matrix = np.column_stack((np.ones(design.shape[0]), design))
    gram = matrix.T @ matrix
    penalty = np.eye(gram.shape[0], dtype=np.float64) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(gram + penalty, matrix.T @ target_z)
    coefficients.setflags(write=False)
    return coefficients


def _fit_candidate(
    features: np.ndarray,
    targets: np.ndarray,
    routes: tuple[str, ...],
) -> FrozenCandidate:
    if features.shape[0] != targets.shape[0] or features.shape[0] != len(routes):
        raise ValueError("candidate 002 development cardinality mismatch")
    if any(route not in ROUTES for route in routes):
        raise ValueError("development contains non-adaptive novelty route")

    x_mean = np.asarray(features.mean(axis=0), dtype=np.float64)
    x_scale = _safe_scale(features)
    y_mean = np.asarray(targets.mean(axis=0), dtype=np.float64)
    y_scale = _safe_scale(targets)
    z = (features - x_mean) / x_scale
    target_z = (targets - y_mean) / y_scale

    baseline_coefficients = _ridge(z, target_z)
    second_order = _second_order_from_standardized(z)

    route_array = np.asarray(routes)
    specialists: list[tuple[str, np.ndarray]] = []
    route_counts: list[tuple[str, int]] = []
    for route in ROUTES:
        mask = route_array == route
        count = int(np.sum(mask))
        if count < MINIMUM_DEVELOPMENT_ROWS_PER_ROUTE:
            raise ValueError(
                f"candidate 002 insufficient development rows for {route}: {count}"
            )
        specialists.append((route, _ridge(second_order[mask], target_z[mask])))
        route_counts.append((route, count))

    for array in (x_mean, x_scale, y_mean, y_scale):
        array.setflags(write=False)
    return FrozenCandidate(
        x_mean=x_mean,
        x_scale=x_scale,
        y_mean=y_mean,
        y_scale=y_scale,
        baseline_coefficients=baseline_coefficients,
        specialist_coefficients=tuple(specialists),
        development_route_counts=tuple(route_counts),
    )


def _predict(coefficients: np.ndarray, design: np.ndarray) -> np.ndarray:
    matrix = np.column_stack((np.ones(design.shape[0]), design))
    return np.asarray(matrix @ coefficients, dtype=np.float64)


def _incremental_bps(baseline: float, adaptive: float) -> int:
    if baseline <= 0:
        return 0
    return int(round((baseline - adaptive) / baseline * 10_000))


def _evaluate_partition(
    *,
    candidate: FrozenCandidate,
    partition: str,
    features: np.ndarray,
    targets: np.ndarray,
    routes: tuple[str, ...],
    minimum_rows: int,
) -> Validation:
    if features.shape[0] != targets.shape[0] or features.shape[0] != len(routes):
        raise ValueError("candidate 002 validation cardinality mismatch")
    if any(route not in ROUTES for route in routes):
        raise ValueError("validation contains non-adaptive novelty route")

    z = (features - candidate.x_mean) / candidate.x_scale
    truth_z = (targets - candidate.y_mean) / candidate.y_scale
    baseline_pred = _predict(candidate.baseline_coefficients, z)
    second_order = _second_order_from_standardized(z)
    route_array = np.asarray(routes)
    adaptive_pred = np.empty_like(truth_z)
    specialists = dict(candidate.specialist_coefficients)
    route_counts: list[tuple[str, int]] = []
    for route in ROUTES:
        mask = route_array == route
        count = int(np.sum(mask))
        route_counts.append((route, count))
        if count:
            adaptive_pred[mask] = _predict(
                specialists[route],
                second_order[mask],
            )

    baseline_mse_array = np.mean((truth_z - baseline_pred) ** 2, axis=0)
    adaptive_mse_array = np.mean((truth_z - adaptive_pred) ** 2, axis=0)
    increments = tuple(
        _incremental_bps(float(base_mse), float(adaptive_mse))
        for base_mse, adaptive_mse in zip(
            baseline_mse_array,
            adaptive_mse_array,
            strict=True,
        )
    )
    pooled_baseline = float(np.mean(baseline_mse_array))
    pooled_adaptive = float(np.mean(adaptive_mse_array))
    pooled_incremental = _incremental_bps(
        pooled_baseline,
        pooled_adaptive,
    )
    positive = sum(value >= 1 for value in increments)
    max_regression = max((max(0, -value) for value in increments), default=0)
    passed = (
        features.shape[0] >= minimum_rows
        and pooled_incremental >= MINIMUM_POOLED_INCREMENTAL_BPS
        and positive >= MINIMUM_POSITIVE_TARGETS
        and max_regression <= MAXIMUM_TARGET_REGRESSION_BPS
    )
    return Validation(
        partition=partition,
        sample_count=features.shape[0],
        route_counts=tuple(route_counts),
        baseline_mse=tuple(float(value) for value in baseline_mse_array),
        adaptive_mse=tuple(float(value) for value in adaptive_mse_array),
        incremental_information_bps=increments,
        pooled_incremental_information_bps=pooled_incremental,
        positive_target_count=positive,
        maximum_target_regression_bps=max_regression,
        minimum_required_rows=minimum_rows,
        pass_gate=passed,
    )


def _check_window(
    metadata: dict[str, Any],
    *,
    start: datetime,
    end: datetime,
) -> None:
    source_min = datetime.fromisoformat(str(metadata["source_min"]))
    source_max = datetime.fromisoformat(str(metadata["source_max"]))
    if source_min < start:
        raise ValueError("candidate 002 partition starts before frozen boundary")
    if source_max >= end:
        raise ValueError("candidate 002 partition crosses frozen boundary")


def _load_selected(
    root: Path,
    partition: str,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], dict[str, Any]]:
    features, targets, _times, metadata = base._partition(root, partition)
    routes = _route_rows(features)
    if any(route not in ROUTES for route in routes):
        raise AssertionError(
            "base capsule selected population contains unexpected novelty state"
        )
    return features, targets, routes, metadata


def _development(
    root: Path,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], dict[str, Any]]:
    feature_rows: list[np.ndarray] = []
    target_rows: list[np.ndarray] = []
    routes: list[str] = []
    metadata: dict[str, Any] = {}
    for partition in DEVELOPMENT_PARTITIONS:
        features, targets, partition_routes, meta = _load_selected(root, partition)
        feature_rows.append(features)
        target_rows.append(targets)
        routes.extend(partition_routes)
        metadata[partition] = meta
    return (
        np.vstack(feature_rows),
        np.vstack(target_rows),
        tuple(routes),
        metadata,
    )


def _run(dataset: Path, output: Path) -> dict[str, Any]:
    temp, root = _extract_dataset(dataset)
    try:
        development_x, development_y, development_routes, development_meta = (
            _development(root)
        )
        candidate = _fit_candidate(
            development_x,
            development_y,
            development_routes,
        )
        repeated = _fit_candidate(
            development_x,
            development_y,
            development_routes,
        )
        deterministic_fit = candidate.fingerprint() == repeated.fingerprint()
        if not deterministic_fit:
            raise AssertionError("candidate 002 deterministic freeze failed")

        d_x, d_y, d_routes, d_meta = _load_selected(
            root,
            VALIDATION_PARTITION,
        )
        _check_window(d_meta, start=D_START, end=D_END)
        d_validation = _evaluate_partition(
            candidate=candidate,
            partition="TEMPORAL_REPLICATION_D",
            features=d_x,
            targets=d_y,
            routes=d_routes,
            minimum_rows=D_MINIMUM_ROWS,
        )

        e_validation: Validation | None = None
        e_meta: dict[str, Any] | None = None
        if d_validation.pass_gate:
            e_x, e_y, e_routes, e_meta = _load_selected(
                root,
                REPLICATION_PARTITION,
            )
            _check_window(e_meta, start=E_START, end=E_END)
            e_validation = _evaluate_partition(
                candidate=candidate,
                partition="REPLACEMENT_ONE_SHOT_HOLDOUT_E",
                features=e_x,
                targets=e_y,
                routes=e_routes,
                minimum_rows=E_MINIMUM_ROWS,
            )

        if not d_validation.pass_gate:
            status = "MC23_CANDIDATE_002_FALSIFIED_ON_REPLICATION_D"
            completed = False
        elif e_validation is None:
            status = "MC23_CANDIDATE_002_INSUFFICIENT_EVIDENCE"
            completed = False
        elif not e_validation.pass_gate:
            status = "MC23_CANDIDATE_002_FALSIFIED_ON_HOLDOUT_E"
            completed = False
        else:
            status = (
                "MC23_CANDIDATE_002_VALIDATED_AND_"
                "INDEPENDENTLY_REPLICATED_PASS"
            )
            completed = True

        payload = {
            "identity": IDENTITY,
            "preregistration": PREREGISTRATION,
            "dataset_sha256": DATASET_SHA256,
            "status": status,
            "candidate_fingerprint": candidate.fingerprint(),
            "deterministic_fit_repeat_pass": deterministic_fit,
            "development": {
                "partitions": DEVELOPMENT_PARTITIONS,
                "metadata": development_meta,
                "sample_count": int(development_x.shape[0]),
                "route_counts": dict(candidate.development_route_counts),
                "target_count": int(development_y.shape[1]),
            },
            "validation_d": asdict(d_validation),
            "validation_d_metadata": d_meta,
            "holdout_e_evaluated": e_validation is not None,
            "replication_e": (
                None if e_validation is None else asdict(e_validation)
            ),
            "replication_e_metadata": e_meta,
            "basis": {
                "baseline": "INTERCEPT_PLUS_14_LINEAR",
                "adaptive": (
                    "ROUTED_INTERCEPT_PLUS_14_LINEAR_PLUS_14_SQUARES_"
                    "PLUS_91_UNIQUE_PAIRS"
                ),
                "routes": ROUTES,
                "ridge_lambda": RIDGE_LAMBDA,
                "global_target_normalization": True,
            },
            "candidate_001_reused": False,
            "r5_used_as_candidate_002_validation": False,
            "validation_d_refit": False,
            "replication_e_refit": False,
            "gate_retuning": False,
            "outcome_aware_tuning": False,
            "future_market_used_for_source_features": False,
            "future_market_used_offline_for_validation": True,
            "pnl_used": False,
            "trader_methodology_used": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
            "real_novel_regime_validated_adaptation": completed,
            "mc23_completed_and_proven": completed,
            "next_gate": (
                "BIND_VALIDATED_MC23_ADAPTATION_INTO_MC24"
                if completed
                else "NEW_PREREGISTERED_MECHANISM_REQUIRED"
            ),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload
    finally:
        temp.cleanup()


def _self_test() -> dict[str, Any]:
    rng = np.random.default_rng(23)
    n = 8_000
    x = rng.normal(size=(n, len(base.BASELINE_FEATURE_NAMES)))
    routes = tuple(
        "NOVEL" if index % 2 else "NEAR_KNOWN"
        for index in range(n)
    )
    z = (x - x.mean(axis=0)) / _safe_scale(x)
    second = _second_order_from_standardized(z)
    signal_near = (
        0.7 * second[:, 14]
        - 0.5 * second[:, 31]
        + 0.4 * second[:, 55]
    )
    signal_novel = (
        -0.8 * second[:, 18]
        + 0.6 * second[:, 44]
        + 0.5 * second[:, 90]
    )
    route_array = np.asarray(routes)
    signal = np.where(
        route_array == "NOVEL",
        signal_novel,
        signal_near,
    )
    y = np.column_stack(
        [
            signal + rng.normal(0.0, 0.1, n),
            0.8 * signal + rng.normal(0.0, 0.1, n),
            0.6 * signal + rng.normal(0.0, 0.1, n),
            0.5 * signal + rng.normal(0.0, 0.1, n),
        ]
    )
    split = 6_000
    candidate = _fit_candidate(x[:split], y[:split], routes[:split])
    result = _evaluate_partition(
        candidate=candidate,
        partition="SYNTHETIC",
        features=x[split:],
        targets=y[split:],
        routes=routes[split:],
        minimum_rows=500,
    )
    if not result.pass_gate:
        raise AssertionError("candidate 002 synthetic routed-signal self-test failed")
    repeat = _fit_candidate(x[:split], y[:split], routes[:split])
    if candidate.fingerprint() != repeat.fingerprint():
        raise AssertionError("candidate 002 deterministic freeze self-test failed")
    return {
        "identity": IDENTITY,
        "status": "PASS",
        "synthetic_mechanics_only": True,
        "scientific_D_or_E_opened": False,
        "candidate_fingerprint": candidate.fingerprint(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("self-test", "evaluate"), required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.mode == "self-test":
        print(json.dumps(_self_test(), sort_keys=True))
        return

    if args.dataset is None or args.output is None:
        raise SystemExit("evaluate requires --dataset and --output")
    payload = _run(args.dataset, args.output)
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if payload["mc23_completed_and_proven"] else 2)


if __name__ == "__main__":
    main()
