#!/usr/bin/env python3
"""MC23 candidate 003 — rich temporal novelty-routed adaptation.

Frozen by QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_003.

Development is consumed R8/R6/R5/TEMPORAL_REPLICATION_D only. HOLDOUT_E is
prepared and scored only after the candidate model and lambda are frozen.
No future values enter source features; no P/L, Trader methodology, broker,
sizing, Risk or productive authority exists here.
"""

from __future__ import annotations

import argparse
import gc
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

IDENTITY: Final = "QORE_SHARED_MC23_CANDIDATE_003_RICH_TEMPORAL_001"
PREREGISTRATION: Final = (
    "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_003"
)
DATASET_SHA256: Final = (
    "d6eed594ae467a0776031c6b65d1f04887a9a4020111f508df7c5223bf057b9f"
)
DEVELOPMENT_PARTITIONS: Final = ("r8", "r6", "r5", "replication_d")
ROUTES: Final = ("NEAR_KNOWN", "NOVEL")
HORIZONS: Final = (5, 15, 30, 60, 90)
RIDGE_GRID: Final = (0.1, 1.0, 10.0, 100.0)
E_START: Final = datetime.fromisoformat("2026-07-13T00:00:00+00:00")
E_END: Final = datetime.fromisoformat("2026-09-25T00:00:00+00:00")
E_MINIMUM_ROWS: Final = 500
MINIMUM_POOLED_INCREMENTAL_BPS: Final = 100
MINIMUM_POSITIVE_TARGETS: Final = 3
MAXIMUM_TARGET_REGRESSION_BPS: Final = 500
RICH_FEATURE_COUNT: Final = 124


@dataclass(frozen=True, slots=True)
class FoldScore:
    partition: str
    sample_count: int
    adaptive_pooled_mse: float
    pooled_incremental_information_bps: int
    incremental_information_bps: tuple[int, ...]
    positive_target_count: int
    maximum_target_regression_bps: int


@dataclass(frozen=True, slots=True)
class FrozenCandidate003:
    selected_lambda: float
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    baseline_coefficients: np.ndarray
    route_coefficients: tuple[tuple[str, np.ndarray], ...]
    development_route_counts: tuple[tuple[str, int], ...]
    cv_scores: tuple[tuple[float, tuple[FoldScore, ...]], ...]

    def fingerprint(self) -> str:
        payload = {
            "identity": IDENTITY,
            "preregistration": PREREGISTRATION,
            "selected_lambda": self.selected_lambda,
            "x_mean": np.round(self.x_mean, 12).tolist(),
            "x_scale": np.round(self.x_scale, 12).tolist(),
            "y_mean": np.round(self.y_mean, 12).tolist(),
            "y_scale": np.round(self.y_scale, 12).tolist(),
            "baseline_coefficients": np.round(
                self.baseline_coefficients, 12
            ).tolist(),
            "route_coefficients": {
                route: np.round(coefficients, 12).tolist()
                for route, coefficients in self.route_coefficients
            },
            "development_route_counts": dict(self.development_route_counts),
            "cv_scores": {
                str(lam): [asdict(score) for score in scores]
                for lam, scores in self.cv_scores
            },
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class Validation003:
    sample_count: int
    route_counts: tuple[tuple[str, int], ...]
    baseline_mse: tuple[float, ...]
    adaptive_mse: tuple[float, ...]
    incremental_information_bps: tuple[int, ...]
    pooled_incremental_information_bps: int
    positive_target_count: int
    maximum_target_regression_bps: int
    pass_gate: bool


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_dataset(dataset: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    if _sha256_file(dataset) != DATASET_SHA256:
        raise ValueError("candidate 003 dataset hash mismatch")
    if not zipfile.is_zipfile(dataset):
        raise ValueError("candidate 003 dataset must be ZIP")
    temp = tempfile.TemporaryDirectory(prefix="qore-a2-mc23-003-")
    root = Path(temp.name)
    with zipfile.ZipFile(dataset) as archive:
        archive.extractall(root)
    return temp, root


def _safe_scale(values: np.ndarray) -> np.ndarray:
    scale = np.asarray(values.std(axis=0), dtype=np.float64)
    return np.where(scale > 1e-12, scale, 1.0)


def _rich_source_features(
    pre: dict[str, tuple[base.Bar, ...]],
) -> tuple[float, ...]:
    values = list(base._source_features(pre))
    metrics: dict[str, dict[int, base.Metric]] = {}
    for market in base.MARKETS:
        metrics[market] = {}
        for horizon in HORIZONS:
            metric = base._metric(pre[market][-horizon:])
            metrics[market][horizon] = metric
            values.extend(
                (
                    metric.net_bps / 100.0,
                    metric.path_bps / 100.0,
                    metric.efficiency,
                    metric.range_mean_bps / 10.0,
                    metric.max_abs_return_bps / 10.0,
                    metric.wick_fraction,
                )
            )

    for horizon in HORIZONS:
        nas = metrics["NAS100"][horizon].net_bps
        sp = metrics["SP500"][horizon].net_bps
        us = metrics["US30"][horizon].net_bps
        signs = (base._sign(nas), base._sign(sp), base._sign(us))
        values.extend(
            (
                abs(sum(signs) / 3.0),
                (nas - sp) / 100.0,
                (nas - us) / 100.0,
                (sp - us) / 100.0,
            )
        )

    if len(values) != RICH_FEATURE_COUNT:
        raise AssertionError(
            f"candidate 003 rich feature count drift: {len(values)}"
        )
    return tuple(float(value) for value in values)


def _partition(
    root: Path,
    partition: str,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], tuple[datetime, ...], dict[str, Any]]:
    bars = {
        market: base._load_bars(
            root / partition / "fresh" / market / "market-evidence.json"
        )
        for market in base.MARKETS
    }
    peer_indexes = {
        market: {
            bar.closed_key: index
            for index, bar in enumerate(bars[market])
        }
        for market in ("SP500", "US30")
    }

    features: list[tuple[float, ...]] = []
    targets: list[tuple[float, ...]] = []
    routes: list[str] = []
    source_times: list[datetime] = []
    total = 0
    nas = bars["NAS100"]

    for nas_index in range(
        base.PRE_WINDOW_MINUTES,
        len(nas) - base.TARGET_HORIZON_MINUTES - 1,
    ):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in base.SAMPLE_MINUTES:
            continue
        indexes = {"NAS100": nas_index}
        missing = False
        for market in ("SP500", "US30"):
            peer_index = peer_indexes[market].get(key)
            if peer_index is None:
                missing = True
                break
            indexes[market] = peer_index
        if missing:
            continue

        pre: dict[str, tuple[base.Bar, ...]] = {}
        future: dict[str, tuple[base.Bar, ...]] = {}
        complete = True
        for market in base.MARKETS:
            index = indexes[market]
            if (
                index < base.PRE_WINDOW_MINUTES
                or index + base.TARGET_HORIZON_MINUTES >= len(bars[market])
            ):
                complete = False
                break
            pre_rows = bars[market][
                index - base.PRE_WINDOW_MINUTES + 1 : index + 1
            ]
            future_rows = bars[market][
                index + 1 : index + 1 + base.TARGET_HORIZON_MINUTES
            ]
            if (
                len(pre_rows) != base.PRE_WINDOW_MINUTES
                or len(future_rows) != base.TARGET_HORIZON_MINUTES
            ):
                complete = False
                break
            pre[market] = pre_rows
            future[market] = future_rows
        if not complete:
            continue

        total += 1
        ontology = base._source_features(pre)
        route = base._novelty_state(ontology)
        if route not in ROUTES:
            continue
        features.append(_rich_source_features(pre))
        targets.append(base._future_targets(pre, future))
        routes.append(route)
        source_times.append(base._parse_key(pre["NAS100"][-1].closed_key))

    del bars
    del peer_indexes
    gc.collect()
    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(targets, dtype=np.float64),
        tuple(routes),
        tuple(source_times),
        {
            "partition": partition,
            "source_observation_count": total,
            "scored_novel_or_near_count": len(features),
            "route_counts": {
                route: routes.count(route)
                for route in ROUTES
            },
            "source_min": min(source_times).isoformat(),
            "source_max": max(source_times).isoformat(),
        },
    )


def _metadata_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _save_prepared(
    path: Path,
    *,
    partition: str,
    features: np.ndarray,
    targets: np.ndarray,
    routes: tuple[str, ...],
    source_times: tuple[datetime, ...],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    route_codes = np.asarray(
        [0 if route == "NEAR_KNOWN" else 1 for route in routes],
        dtype=np.int8,
    )
    source_ns = np.asarray(
        [int(item.timestamp() * 1_000_000_000) for item in source_times],
        dtype=np.int64,
    )
    np.savez(
        path,
        features=features,
        targets=targets,
        route_codes=route_codes,
        source_ns=source_ns,
    )
    payload = {
        "schema": "QORE_SHARED_A2_MC23_003_PREPARED_PARTITION_001",
        "identity": IDENTITY,
        "partition": partition,
        "dataset_sha256": DATASET_SHA256,
        "matrix_sha256": _sha256_file(path),
        "row_count": int(features.shape[0]),
        "feature_count": int(features.shape[1]),
        "metadata": metadata,
        "future_market_used_for_source_features": False,
        "pnl_used": False,
        "protected_certification_holdout_opened": False,
    }
    _metadata_path(path).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _load_prepared(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], tuple[datetime, ...], dict[str, Any]]:
    payload = json.loads(_metadata_path(path).read_text(encoding="utf-8"))
    if payload.get("identity") != IDENTITY:
        raise ValueError("candidate 003 prepared identity drift")
    if payload.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("candidate 003 prepared dataset drift")
    if payload.get("matrix_sha256") != _sha256_file(path):
        raise ValueError("candidate 003 prepared matrix hash mismatch")
    with np.load(path, allow_pickle=False) as data:
        features = np.asarray(data["features"], dtype=np.float64)
        targets = np.asarray(data["targets"], dtype=np.float64)
        codes = np.asarray(data["route_codes"], dtype=np.int8)
        source_ns = np.asarray(data["source_ns"], dtype=np.int64)
    routes = tuple("NEAR_KNOWN" if int(code) == 0 else "NOVEL" for code in codes)
    source_times = tuple(
        datetime.fromtimestamp(int(value) / 1_000_000_000, tz=base.UTC)
        for value in source_ns
    )
    if features.shape[1] != RICH_FEATURE_COUNT:
        raise ValueError("candidate 003 prepared feature count drift")
    return features, targets, routes, source_times, payload


def _ridge(design: np.ndarray, response: np.ndarray, lam: float) -> np.ndarray:
    matrix = np.column_stack((np.ones(design.shape[0]), design))
    gram = matrix.T @ matrix
    penalty = np.eye(gram.shape[0], dtype=np.float64) * lam
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(gram + penalty, matrix.T @ response)
    coefficients.setflags(write=False)
    return coefficients


def _predict(coefficients: np.ndarray, design: np.ndarray) -> np.ndarray:
    return np.column_stack((np.ones(design.shape[0]), design)) @ coefficients


def _incremental_bps(baseline: float, adaptive: float) -> int:
    if baseline <= 0:
        return 0
    return int(round((baseline - adaptive) / baseline * 10_000))


def _fit(
    partitions: tuple[tuple[np.ndarray, np.ndarray, tuple[str, ...]], ...],
    lam: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[tuple[str, np.ndarray], ...], tuple[tuple[str, int], ...]]:
    features = np.vstack([item[0] for item in partitions])
    targets = np.vstack([item[1] for item in partitions])
    routes = np.asarray([route for item in partitions for route in item[2]])
    x_mean = features.mean(axis=0)
    x_scale = _safe_scale(features)
    y_mean = targets.mean(axis=0)
    y_scale = _safe_scale(targets)
    xz = (features - x_mean) / x_scale
    yz = (targets - y_mean) / y_scale
    baseline = _ridge(xz[:, :14], yz, lam)
    route_coefficients: list[tuple[str, np.ndarray]] = []
    route_counts: list[tuple[str, int]] = []
    for route in ROUTES:
        mask = routes == route
        route_coefficients.append((route, _ridge(xz[mask], yz[mask], lam)))
        route_counts.append((route, int(np.sum(mask))))
    return (
        x_mean,
        x_scale,
        y_mean,
        y_scale,
        baseline,
        tuple(route_coefficients),
        tuple(route_counts),
    )


def _evaluate(
    model: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[tuple[str, np.ndarray], ...], tuple[tuple[str, int], ...]],
    *,
    features: np.ndarray,
    targets: np.ndarray,
    routes: tuple[str, ...],
) -> Validation003:
    x_mean, x_scale, y_mean, y_scale, baseline, route_coefficients, _ = model
    xz = (features - x_mean) / x_scale
    yz = (targets - y_mean) / y_scale
    baseline_pred = _predict(baseline, xz[:, :14])
    route_array = np.asarray(routes)
    adaptive_pred = np.empty_like(yz)
    route_counts: list[tuple[str, int]] = []
    for route, coefficients in route_coefficients:
        mask = route_array == route
        route_counts.append((route, int(np.sum(mask))))
        adaptive_pred[mask] = _predict(coefficients, xz[mask])
    baseline_mse = np.mean((yz - baseline_pred) ** 2, axis=0)
    adaptive_mse = np.mean((yz - adaptive_pred) ** 2, axis=0)
    increments = tuple(
        _incremental_bps(float(base_mse), float(adapt_mse))
        for base_mse, adapt_mse in zip(baseline_mse, adaptive_mse, strict=True)
    )
    pooled = _incremental_bps(
        float(np.mean(baseline_mse)),
        float(np.mean(adaptive_mse)),
    )
    positive = sum(value >= 1 for value in increments)
    max_regression = max((max(0, -value) for value in increments), default=0)
    return Validation003(
        sample_count=int(features.shape[0]),
        route_counts=tuple(route_counts),
        baseline_mse=tuple(float(value) for value in baseline_mse),
        adaptive_mse=tuple(float(value) for value in adaptive_mse),
        incremental_information_bps=increments,
        pooled_incremental_information_bps=pooled,
        positive_target_count=positive,
        maximum_target_regression_bps=max_regression,
        pass_gate=(
            features.shape[0] >= E_MINIMUM_ROWS
            and pooled >= MINIMUM_POOLED_INCREMENTAL_BPS
            and positive >= MINIMUM_POSITIVE_TARGETS
            and max_regression <= MAXIMUM_TARGET_REGRESSION_BPS
        ),
    )


def _freeze(
    prepared: dict[str, Path],
    output: Path,
) -> dict[str, Any]:
    loaded = {name: _load_prepared(path) for name, path in prepared.items()}
    cv_rows: list[tuple[float, tuple[FoldScore, ...]]] = []
    lambda_objectives: dict[float, float] = {}

    for lam in RIDGE_GRID:
        fold_scores: list[FoldScore] = []
        weighted_sse = 0.0
        weighted_n = 0
        for holdout in DEVELOPMENT_PARTITIONS:
            train = tuple(
                (
                    loaded[name][0],
                    loaded[name][1],
                    loaded[name][2],
                )
                for name in DEVELOPMENT_PARTITIONS
                if name != holdout
            )
            model = _fit(train, lam)
            features, targets, routes, _times, _payload = loaded[holdout]
            validation = _evaluate(
                model,
                features=features,
                targets=targets,
                routes=routes,
            )
            adaptive_pooled_mse = float(np.mean(validation.adaptive_mse))
            fold_scores.append(
                FoldScore(
                    partition=holdout,
                    sample_count=validation.sample_count,
                    adaptive_pooled_mse=adaptive_pooled_mse,
                    pooled_incremental_information_bps=(
                        validation.pooled_incremental_information_bps
                    ),
                    incremental_information_bps=(
                        validation.incremental_information_bps
                    ),
                    positive_target_count=validation.positive_target_count,
                    maximum_target_regression_bps=(
                        validation.maximum_target_regression_bps
                    ),
                )
            )
            weighted_sse += adaptive_pooled_mse * validation.sample_count
            weighted_n += validation.sample_count
        objective = weighted_sse / weighted_n
        lambda_objectives[lam] = objective
        cv_rows.append((lam, tuple(fold_scores)))

    selected_lambda = sorted(
        RIDGE_GRID,
        key=lambda lam: (lambda_objectives[lam], -lam),
    )[0]
    final_model = _fit(
        tuple(
            (
                loaded[name][0],
                loaded[name][1],
                loaded[name][2],
            )
            for name in DEVELOPMENT_PARTITIONS
        ),
        selected_lambda,
    )
    x_mean, x_scale, y_mean, y_scale, baseline, routes, route_counts = final_model
    frozen = FrozenCandidate003(
        selected_lambda=selected_lambda,
        x_mean=x_mean,
        x_scale=x_scale,
        y_mean=y_mean,
        y_scale=y_scale,
        baseline_coefficients=baseline,
        route_coefficients=routes,
        development_route_counts=route_counts,
        cv_scores=tuple(cv_rows),
    )
    repeat = FrozenCandidate003(
        selected_lambda=selected_lambda,
        x_mean=x_mean.copy(),
        x_scale=x_scale.copy(),
        y_mean=y_mean.copy(),
        y_scale=y_scale.copy(),
        baseline_coefficients=baseline.copy(),
        route_coefficients=tuple((route, coeff.copy()) for route, coeff in routes),
        development_route_counts=route_counts,
        cv_scores=tuple(cv_rows),
    )
    if frozen.fingerprint() != repeat.fingerprint():
        raise AssertionError("candidate 003 deterministic fingerprint failed")

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        selected_lambda=np.asarray([selected_lambda], dtype=np.float64),
        x_mean=x_mean,
        x_scale=x_scale,
        y_mean=y_mean,
        y_scale=y_scale,
        baseline_coefficients=baseline,
        near_coefficients=dict(routes)["NEAR_KNOWN"],
        novel_coefficients=dict(routes)["NOVEL"],
    )
    payload = {
        "schema": "QORE_SHARED_A2_MC23_CANDIDATE_003_FREEZE_001",
        "identity": IDENTITY,
        "preregistration": PREREGISTRATION,
        "selected_lambda": selected_lambda,
        "lambda_objectives": {
            str(lam): lambda_objectives[lam] for lam in RIDGE_GRID
        },
        "cv_scores": {
            str(lam): [asdict(score) for score in scores]
            for lam, scores in cv_rows
        },
        "candidate_fingerprint": frozen.fingerprint(),
        "model_sha256": _sha256_file(output),
        "development_route_counts": dict(route_counts),
        "holdout_e_prepared_or_scored": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    _metadata_path(output).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _load_frozen(path: Path) -> tuple[dict[str, Any], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[tuple[str, np.ndarray], ...], tuple[tuple[str, int], ...]]]:
    payload = json.loads(_metadata_path(path).read_text(encoding="utf-8"))
    if payload.get("identity") != IDENTITY:
        raise ValueError("candidate 003 frozen identity drift")
    if payload.get("model_sha256") != _sha256_file(path):
        raise ValueError("candidate 003 frozen model hash mismatch")
    with np.load(path, allow_pickle=False) as data:
        selected = float(data["selected_lambda"][0])
        model = (
            np.asarray(data["x_mean"], dtype=np.float64),
            np.asarray(data["x_scale"], dtype=np.float64),
            np.asarray(data["y_mean"], dtype=np.float64),
            np.asarray(data["y_scale"], dtype=np.float64),
            np.asarray(data["baseline_coefficients"], dtype=np.float64),
            (
                ("NEAR_KNOWN", np.asarray(data["near_coefficients"], dtype=np.float64)),
                ("NOVEL", np.asarray(data["novel_coefficients"], dtype=np.float64)),
            ),
            tuple(
                (route, int(count))
                for route, count in payload["development_route_counts"].items()
            ),
        )
    if selected != float(payload["selected_lambda"]):
        raise ValueError("candidate 003 selected lambda drift")
    return payload, model


def _validate_e(
    frozen_path: Path,
    e_path: Path,
    output: Path,
) -> dict[str, Any]:
    freeze, model = _load_frozen(frozen_path)
    features, targets, routes, _times, prepared = _load_prepared(e_path)
    meta = dict(prepared["metadata"])
    source_min = datetime.fromisoformat(str(meta["source_min"]))
    source_max = datetime.fromisoformat(str(meta["source_max"]))
    if source_min < E_START or source_max >= E_END:
        raise ValueError("candidate 003 HOLDOUT_E boundary drift")
    validation = _evaluate(
        model,
        features=features,
        targets=targets,
        routes=routes,
    )
    if validation.sample_count < E_MINIMUM_ROWS:
        status = "MC23_CANDIDATE_003_INSUFFICIENT_EVIDENCE"
        passed = False
    elif validation.pass_gate:
        status = "MC23_CANDIDATE_003_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_PASS"
        passed = True
    else:
        status = "MC23_CANDIDATE_003_FALSIFIED_ON_HOLDOUT_E"
        passed = False
    payload = {
        "identity": IDENTITY,
        "preregistration": PREREGISTRATION,
        "dataset_sha256": DATASET_SHA256,
        "status": status,
        "candidate_fingerprint": freeze["candidate_fingerprint"],
        "selected_lambda": freeze["selected_lambda"],
        "validation_e": asdict(validation),
        "validation_e_metadata": meta,
        "holdout_e_refit": False,
        "holdout_e_feature_selection": False,
        "holdout_e_hyperparameter_retuning": False,
        "gate_retuning": False,
        "future_market_used_for_source_features": False,
        "future_market_used_offline_for_validation": True,
        "pnl_used": False,
        "trader_methodology_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
        "real_novel_regime_validated_adaptation": passed,
        "mc23_completed_and_proven": passed,
        "next_gate": (
            "BIND_VALIDATED_MC23_ADAPTATION_INTO_MC24"
            if passed
            else "NEW_PREREGISTERED_MECHANISM_REQUIRED"
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _self_test() -> dict[str, Any]:
    rng = np.random.default_rng(303)
    n = 4000
    features = rng.normal(size=(n, RICH_FEATURE_COUNT))
    targets = np.column_stack(
        (
            0.4 * features[:, 14] + rng.normal(0, 0.5, n),
            0.8 * features[:, 20] + rng.normal(0, 0.4, n),
            0.9 * features[:, 40] + rng.normal(0, 0.4, n),
            0.6 * features[:, 80] + rng.normal(0, 0.5, n),
        )
    )
    routes = tuple("NEAR_KNOWN" if i % 2 == 0 else "NOVEL" for i in range(n))
    model = _fit(((features[:3000], targets[:3000], routes[:3000]),), 100.0)
    validation = _evaluate(
        model,
        features=features[3000:],
        targets=targets[3000:],
        routes=routes[3000:],
    )
    if validation.positive_target_count < 3:
        raise AssertionError("candidate 003 synthetic mechanics failed")
    return {
        "identity": IDENTITY,
        "status": "PASS",
        "synthetic_mechanics_only": True,
        "holdout_e_prepared_or_scored": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("self-test", "prepare", "freeze", "validate-e"),
        required=True,
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--partition")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--r8", type=Path)
    parser.add_argument("--r6", type=Path)
    parser.add_argument("--r5", type=Path)
    parser.add_argument("--d", type=Path)
    parser.add_argument("--e", type=Path)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()

    if args.mode == "self-test":
        print(json.dumps(_self_test(), sort_keys=True))
        return

    if args.mode == "prepare":
        if args.dataset is None or args.partition is None or args.output is None:
            raise SystemExit("prepare requires --dataset --partition --output")
        temp, root = _extract_dataset(args.dataset)
        try:
            features, targets, routes, times, metadata = _partition(
                root, args.partition
            )
            payload = _save_prepared(
                args.output,
                partition=args.partition,
                features=features,
                targets=targets,
                routes=routes,
                source_times=times,
                metadata=metadata,
            )
        finally:
            temp.cleanup()
        print(json.dumps(payload, sort_keys=True))
        return

    if args.mode == "freeze":
        if any(item is None for item in (args.r8,args.r6,args.r5,args.d,args.output)):
            raise SystemExit("freeze requires --r8 --r6 --r5 --d --output")
        payload = _freeze(
            {
                "r8": args.r8,
                "r6": args.r6,
                "r5": args.r5,
                "replication_d": args.d,
            },
            args.output,
        )
        print(json.dumps(payload, sort_keys=True))
        return

    if any(item is None for item in (args.frozen,args.e,args.output)):
        raise SystemExit("validate-e requires --frozen --e --output")
    payload = _validate_e(args.frozen, args.e, args.output)
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if payload["mc23_completed_and_proven"] else 2)


if __name__ == "__main__":
    main()
