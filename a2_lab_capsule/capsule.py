#!/usr/bin/env python3
"""A2 frozen scientific capsule for native QORE Shared Lab.

This file is deliberately self-contained so Shared Lab can execute an exact-SHA
sparse worktree. It implements only the preregistered A2 MC23 -> MC24 experiment
on the frozen consumed R6/R5 dataset.

It has no broker, Trader, Risk, sizing, capital or productive authority.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import statistics
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Any

import numpy as np

CAPSULE_ID: Final = "QORE_SHARED_A2_LAB_CAPSULE_001"
DATASET_SHA256: Final = (
    "15575cd662b92e736fe53f59fbad50c42d244e29180cfb10fa8b6c7a87c560d0"
)
MC23_PREREG: Final = (
    "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_001"
)
MC24_PREREG: Final = (
    "QORE_SHARED_MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_PREREGISTRATION_001"
)
# The novelty-detection audit used require_future=False. This experiment
# attaches +30m targets, so the final two R6 source observations are not
# target-eligible; one of those two was NOVEL/NEAR_KNOWN.
EXPECTED_COUNTS: Final = {
    "r6": {"total": 21_121, "novel_or_near": 8_010},
}
MARKETS: Final = ("NAS100", "SP500", "US30")
SAMPLE_MINUTES: Final = (0, 30)
PRE_WINDOW_MINUTES: Final = 90
TARGET_HORIZON_MINUTES: Final = 30

BASELINE_FEATURE_NAMES: Final = (
    "compression",
    "liquidity_accumulation",
    "failed_auction",
    "displacement",
    "acceptance",
    "absorption",
    "leader_confirmation",
    "leader_divergence",
    "momentum_persistence",
    "momentum_decay",
    "structural_fragility",
    "liquidity_vacuum",
    "regime_transition",
    "anomaly",
)
ADAPTIVE_INTERACTION_NAMES: Final = (
    "anomaly_x_regime_transition",
    "leader_divergence_x_structural_fragility",
    "liquidity_vacuum_x_anomaly",
    "momentum_persistence_x_inverse_momentum_decay",
    "displacement_x_acceptance",
    "compression_x_liquidity_accumulation",
)
TARGET_NAMES: Final = (
    "NAS100_FUTURE_30M_NET_RETURN_Z",
    "NAS100_FUTURE_30M_ABS_RETURN_Z",
    "NAS100_FUTURE_30M_MEAN_RANGE_Z",
    "NAS100_FUTURE_30M_PATH_EFFICIENCY_Z",
)

RIDGE_LAMBDA: Final = 1.0
MINIMUM_R5_SCORED_OBSERVATIONS: Final = 5_000
MINIMUM_POSITIVE_TARGETS: Final = 3
MINIMUM_POOLED_INCREMENTAL_BPS: Final = 100
MAXIMUM_TARGET_REGRESSION_BPS: Final = 500

HALF_LIFE_BIN_DAYS: Final = 90
HALF_LIFE_MIN_SAMPLES_PER_BIN: Final = 500
HALF_LIFE_MIN_ELIGIBLE_BINS: Final = 4
HALF_LIFE_FRACTION_BPS: Final = 5_000

CANONICAL_SOURCE_BLOBS: Final = {
    "shared_wp03_historical_causal_discovery.py":
        "151cfca3a7566a1a989f104f86aea5305bc44b41",
    "shared_sti2_real_opportunity_discovery.py":
        "cd9fc2b95e925ae5aab58ab9ec35c13cac69bb1c",
    "shared_mc23_real_novelty_detection.py":
        "e7a42c519020ea570b24b95a39493c769220971f",
    "mc23_validated_novel_regime_adaptation.py":
        "b3fe16454cc9c01c041ab11f27ab9e17d0c701f5",
    "mc24_empirical_half_life.py":
        "f4adec6ad1ea6067b6d9239bcae5195db24d3094",
}


@dataclass(frozen=True, slots=True)
class Bar:
    opened_key: str
    closed_key: str
    opened: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class Metric:
    net_bps: float
    path_bps: float
    efficiency: float
    range_mean_bps: float
    max_abs_return_bps: float
    wick_fraction: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class FrozenRidgeProjection:
    feature_names: tuple[str, ...]
    target_names: tuple[str, ...]
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    coefficients: np.ndarray

    def fingerprint(self) -> str:
        payload = {
            "feature_names": self.feature_names,
            "target_names": self.target_names,
            "ridge_lambda": RIDGE_LAMBDA,
            "x_mean": np.round(self.x_mean, 12).tolist(),
            "x_scale": np.round(self.x_scale, 12).tolist(),
            "y_mean": np.round(self.y_mean, 12).tolist(),
            "y_scale": np.round(self.y_scale, 12).tolist(),
            "coefficients": np.round(self.coefficients, 12).tolist(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Validation:
    sample_count: int
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


def _return_bps(last: float, first: float) -> float:
    if first == 0:
        return 0.0
    return (last / first - 1.0) * 10_000.0


def _sign(value: float) -> int:
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _clamp_bps(value: float) -> int:
    return max(0, min(10_000, int(round(value))))


def _parse_key(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _load_bars(path: Path) -> tuple[Bar, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload["periods"]["M1"]
    bars = tuple(
        Bar(
            opened_key=str(row["opened_at"])[:19],
            closed_key=str(row["closed_at"])[:19],
            opened=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
        )
        for row in raw
    )
    del raw
    del payload
    gc.collect()
    return bars


def _metric(bars: tuple[Bar, ...] | list[Bar]) -> Metric:
    if len(bars) < 2:
        raise ValueError("metric requires at least two bars")
    one_minute = [
        _return_bps(bars[index].close, bars[index - 1].close)
        for index in range(1, len(bars))
    ]
    net = _return_bps(bars[-1].close, bars[0].close)
    path = sum(abs(value) for value in one_minute)
    ranges = [
        (bar.high - bar.low) / bar.close * 10_000.0
        if bar.close
        else 0.0
        for bar in bars
    ]
    wick = [
        1.0
        - (
            abs(bar.close - bar.opened) / (bar.high - bar.low)
            if bar.high > bar.low
            else 0.0
        )
        for bar in bars
    ]
    return Metric(
        net_bps=net,
        path_bps=path,
        efficiency=0.0 if path == 0 else abs(net) / path,
        range_mean_bps=statistics.fmean(ranges),
        max_abs_return_bps=max((abs(value) for value in one_minute), default=0.0),
        wick_fraction=statistics.fmean(wick),
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
    )


def _coherence(metrics: dict[str, Metric]) -> tuple[float, float]:
    signs = [_sign(metrics[market].net_bps) for market in MARKETS]
    signed = sum(signs) / len(signs)
    return abs(signed), signed


def _source_features(
    windows: dict[str, tuple[Bar, ...]],
) -> tuple[float, ...]:
    horizon: dict[str, dict[int, Metric]] = {}
    previous: dict[str, dict[int, Metric]] = {}
    sweep: dict[str, float] = {}
    acceptance: dict[str, float] = {}
    edge: dict[str, float] = {}

    for market, bars in windows.items():
        horizon[market] = {
            5: _metric(bars[-5:]),
            15: _metric(bars[-15:]),
            30: _metric(bars[-30:]),
            60: _metric(bars[-60:]),
        }
        previous[market] = {
            5: _metric(bars[-35:-30]),
            15: _metric(bars[-45:-30]),
            60: _metric(bars[-90:-30]),
        }
        prior = bars[-25:-5]
        recent = bars[-5:]
        prior_peak = max(bar.high for bar in prior)
        prior_floor = min(bar.low for bar in prior)
        last_close = recent[-1].close
        sweep[market] = float(
            (
                max(bar.high for bar in recent) > prior_peak
                and last_close < prior_peak
            )
            or (
                min(bar.low for bar in recent) < prior_floor
                and last_close > prior_floor
            )
        )
        outside = sum(
            bar.close > prior_peak or bar.close < prior_floor
            for bar in recent
        )
        acceptance[market] = outside / len(recent)
        width = max(1e-12, prior_peak - prior_floor)
        position = (last_close - prior_floor) / width
        edge[market] = min(1.0, abs(position - 0.5) * 2.0)

    def m(market: str, minutes: int) -> Metric:
        return horizon[market][minutes]

    def p(market: str, minutes: int) -> Metric:
        return previous[market][minutes]

    coh15, _ = _coherence({market: m(market, 15) for market in MARKETS})
    prev_coh15, _ = _coherence({market: p(market, 15) for market in MARKETS})

    nas5 = m("NAS100", 5)
    nas15 = m("NAS100", 15)
    nas30 = m("NAS100", 30)
    nas60 = m("NAS100", 60)
    prev5 = p("NAS100", 5)
    prev60 = p("NAS100", 60)

    vol_ratio = nas5.range_mean_bps / max(1e-9, nas60.range_mean_bps)
    prev_vol_ratio = prev5.range_mean_bps / max(1e-9, prev60.range_mean_bps)
    displacement_scale = abs(nas5.net_bps) / max(
        1e-9, nas60.range_mean_bps * math.sqrt(5.0)
    )
    stretch15 = abs(nas15.net_bps) / max(
        1e-9, nas60.range_mean_bps * math.sqrt(15.0)
    )
    aligned_5_15_30 = float(
        _sign(nas5.net_bps)
        == _sign(nas15.net_bps)
        == _sign(nas30.net_bps)
        != 0
    )
    reverse5_15 = float(nas5.net_bps * nas15.net_bps < 0)
    recent_speed = abs(nas5.net_bps) / 5.0
    medium_speed = abs(nas15.net_bps) / 15.0
    speed_decay = (
        0.0
        if medium_speed <= 1e-9
        else max(0.0, min(1.0, 1.0 - recent_speed / medium_speed))
    )
    peer_direction = _sign(m("SP500", 15).net_bps + m("US30", 15).net_bps)
    leader_alignment = float(
        _sign(nas15.net_bps) != 0
        and _sign(nas15.net_bps) == peer_direction
    )
    vol_transition = min(1.0, abs(vol_ratio - prev_vol_ratio) / 1.5)
    coherence_transition = min(1.0, abs(coh15 - prev_coh15))

    compression = min(
        1.0,
        0.45 * (1.0 - min(1.0, vol_ratio))
        + 0.30 * (1.0 - min(1.0, stretch15))
        + 0.25 * (1.0 - nas15.efficiency),
    )
    liquidity_accumulation = min(
        1.0,
        0.45 * nas30.wick_fraction
        + 0.35 * (1.0 - nas30.efficiency)
        + 0.20 * (1.0 - min(1.0, vol_ratio)),
    )
    failed_auction = min(
        1.0,
        0.65 * sweep["NAS100"]
        + 0.20 * nas5.wick_fraction
        + 0.15 * (1.0 - acceptance["NAS100"]),
    )
    displacement = min(
        1.0,
        0.40 * min(1.0, displacement_scale)
        + 0.35 * nas5.efficiency
        + 0.25 * min(1.0, max(0.0, vol_ratio - 1.0) / 1.5),
    )
    current_acceptance = min(
        1.0, 0.70 * acceptance["NAS100"] + 0.30 * nas5.efficiency
    )
    absorption = min(
        1.0,
        0.50 * nas15.wick_fraction
        + 0.35 * (1.0 - nas15.efficiency)
        + 0.15 * min(1.0, vol_ratio),
    )
    leader_confirmation = min(1.0, 0.60 * coh15 + 0.40 * leader_alignment)
    leader_divergence = 1.0 - leader_confirmation
    momentum_persistence = min(
        1.0,
        0.40 * aligned_5_15_30 + 0.30 * nas15.efficiency + 0.30 * coh15,
    )
    momentum_decay = min(
        1.0,
        0.40 * speed_decay
        + 0.30 * reverse5_15
        + 0.30 * (1.0 - nas5.efficiency),
    )
    structural_fragility = min(
        1.0,
        0.35 * leader_divergence
        + 0.25 * failed_auction
        + 0.20 * min(1.0, max(0.0, vol_ratio - 1.0))
        + 0.20 * edge["NAS100"],
    )
    liquidity_vacuum = min(
        1.0,
        0.45
        * min(
            1.0,
            nas5.max_abs_return_bps
            / max(1e-9, nas60.range_mean_bps * 2.0),
        )
        + 0.35 * nas5.efficiency
        + 0.20 * (1.0 - nas5.wick_fraction),
    )
    regime_transition = min(
        1.0, 0.60 * vol_transition + 0.40 * coherence_transition
    )
    anomaly = min(
        1.0,
        0.60
        * min(
            1.0,
            nas5.max_abs_return_bps
            / max(1e-9, nas60.range_mean_bps * 3.0),
        )
        + 0.40 * min(1.0, max(0.0, vol_ratio - 1.0) / 2.0),
    )
    return (
        compression,
        liquidity_accumulation,
        failed_auction,
        displacement,
        current_acceptance,
        absorption,
        leader_confirmation,
        leader_divergence,
        momentum_persistence,
        momentum_decay,
        structural_fragility,
        liquidity_vacuum,
        regime_transition,
        anomaly,
    )


def _novelty_state(features: tuple[float, ...]) -> str:
    idx = {name: i for i, name in enumerate(BASELINE_FEATURE_NAMES)}
    anomaly = int(round(features[idx["anomaly"]] * 10_000))
    divergence = int(round(features[idx["leader_divergence"]] * 10_000))
    fragility = int(round(features[idx["structural_fragility"]] * 10_000))
    transition = int(round(features[idx["regime_transition"]] * 10_000))
    novelty = max(anomaly, divergence)
    historical_distance = fragility
    regime_unfamiliarity = max(anomaly, transition)
    model_disagreement = divergence
    composite = max(novelty, historical_distance, regime_unfamiliarity)
    if composite >= 7_000:
        return "NOVEL"
    if composite >= 4_000 or model_disagreement >= 5_000:
        return "NEAR_KNOWN"
    return "KNOWN"


def _future_targets(
    pre: dict[str, tuple[Bar, ...]],
    future: dict[str, tuple[Bar, ...]],
) -> tuple[float, ...]:
    nas_future = future["NAS100"]
    metric = _metric(nas_future)
    source_close = pre["NAS100"][-1].close
    future_close = nas_future[-1].close
    net_return_bps = _return_bps(future_close, source_close)
    return (
        net_return_bps,
        abs(net_return_bps),
        metric.range_mean_bps,
        metric.efficiency,
    )


def _partition(
    root: Path,
    partition: str,
) -> tuple[np.ndarray, np.ndarray, tuple[datetime, ...], dict[str, Any]]:
    bars = {
        market: _load_bars(
            root / partition / "fresh" / market / "market-evidence.json"
        )
        for market in MARKETS
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
    source_times: list[datetime] = []
    total = 0
    state_counts = {"KNOWN": 0, "NEAR_KNOWN": 0, "NOVEL": 0}

    nas = bars["NAS100"]
    for nas_index in range(
        PRE_WINDOW_MINUTES,
        len(nas) - TARGET_HORIZON_MINUTES - 1,
    ):
        key = nas[nas_index].closed_key
        if int(key[14:16]) not in SAMPLE_MINUTES:
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

        pre: dict[str, tuple[Bar, ...]] = {}
        future: dict[str, tuple[Bar, ...]] = {}
        complete = True
        for market in MARKETS:
            index = indexes[market]
            if (
                index < PRE_WINDOW_MINUTES
                or index + TARGET_HORIZON_MINUTES >= len(bars[market])
            ):
                complete = False
                break
            pre_rows = bars[market][
                index - PRE_WINDOW_MINUTES + 1 : index + 1
            ]
            future_rows = bars[market][
                index + 1 : index + 1 + TARGET_HORIZON_MINUTES
            ]
            if (
                len(pre_rows) != PRE_WINDOW_MINUTES
                or len(future_rows) != TARGET_HORIZON_MINUTES
            ):
                complete = False
                break
            pre[market] = pre_rows
            future[market] = future_rows
        if not complete:
            continue

        total += 1
        source_features = _source_features(pre)
        state = _novelty_state(source_features)
        state_counts[state] += 1
        if state not in {"NOVEL", "NEAR_KNOWN"}:
            continue
        features.append(source_features)
        targets.append(_future_targets(pre, future))
        source_times.append(_parse_key(pre["NAS100"][-1].closed_key))

    selected = len(features)
    # R6 is consumed construction evidence, so exact target-eligible parity is
    # checked before the one-shot. R5 is not pre-counted; its preregistered
    # scientific sufficiency gate remains MINIMUM_R5_SCORED_OBSERVATIONS.
    if partition == "r6":
        expected = EXPECTED_COUNTS["r6"]
        if total != expected["total"]:
            raise ValueError(
                "r6 target-eligible population drift: "
                f"{total} != {expected['total']}"
            )
        if selected != expected["novel_or_near"]:
            raise ValueError(
                "r6 target-eligible novel population drift: "
                f"{selected} != {expected['novel_or_near']}"
            )
    del bars
    del peer_indexes
    gc.collect()

    return (
        np.asarray(features, dtype=np.float64),
        np.asarray(targets, dtype=np.float64),
        tuple(source_times),
        {
            "partition": partition,
            "source_observation_count": total,
            "scored_novel_or_near_count": selected,
            "state_counts": state_counts,
            "source_min": min(source_times).isoformat(),
            "source_max": max(source_times).isoformat(),
        },
    )


def _adaptive_design(baseline: np.ndarray) -> np.ndarray:
    if baseline.ndim != 2 or baseline.shape[1] != len(BASELINE_FEATURE_NAMES):
        raise ValueError("baseline feature matrix shape drift")
    idx = {name: i for i, name in enumerate(BASELINE_FEATURE_NAMES)}
    x = baseline
    interactions = np.column_stack(
        (
            x[:, idx["anomaly"]] * x[:, idx["regime_transition"]],
            x[:, idx["leader_divergence"]] * x[:, idx["structural_fragility"]],
            x[:, idx["liquidity_vacuum"]] * x[:, idx["anomaly"]],
            x[:, idx["momentum_persistence"]]
            * (1.0 - x[:, idx["momentum_decay"]]),
            x[:, idx["displacement"]] * x[:, idx["acceptance"]],
            x[:, idx["compression"]] * x[:, idx["liquidity_accumulation"]],
        )
    )
    return np.hstack((baseline, interactions))


def _safe_scale(values: np.ndarray) -> np.ndarray:
    scale = np.asarray(values.std(axis=0), dtype=np.float64)
    return np.where(scale > 1e-12, scale, 1.0)


def _fit(
    features: np.ndarray,
    targets: np.ndarray,
    feature_names: tuple[str, ...],
) -> FrozenRidgeProjection:
    x_mean = np.asarray(features.mean(axis=0), dtype=np.float64)
    x_scale = _safe_scale(features)
    y_mean = np.asarray(targets.mean(axis=0), dtype=np.float64)
    y_scale = _safe_scale(targets)
    xz = (features - x_mean) / x_scale
    yz = (targets - y_mean) / y_scale
    design = np.column_stack((np.ones(xz.shape[0]), xz))
    gram = design.T @ design
    penalty = np.eye(gram.shape[0], dtype=np.float64) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(gram + penalty, design.T @ yz)
    return FrozenRidgeProjection(
        feature_names=feature_names,
        target_names=TARGET_NAMES,
        x_mean=x_mean,
        x_scale=x_scale,
        y_mean=y_mean,
        y_scale=y_scale,
        coefficients=coefficients,
    )


def _predict(model: FrozenRidgeProjection, features: np.ndarray) -> np.ndarray:
    xz = (features - model.x_mean) / model.x_scale
    design = np.column_stack((np.ones(xz.shape[0]), xz))
    return design @ model.coefficients


def _target_z(model: FrozenRidgeProjection, targets: np.ndarray) -> np.ndarray:
    return (targets - model.y_mean) / model.y_scale


def _incremental_bps(baseline: float, adaptive: float) -> int:
    if baseline <= 0:
        return 0
    return int(round((baseline - adaptive) / baseline * 10_000))


def _evaluate(
    baseline_model: FrozenRidgeProjection,
    adaptive_model: FrozenRidgeProjection,
    baseline_features: np.ndarray,
    adaptive_features: np.ndarray,
    targets: np.ndarray,
) -> Validation:
    baseline_truth = _target_z(baseline_model, targets)
    adaptive_truth = _target_z(adaptive_model, targets)
    if not np.allclose(baseline_truth, adaptive_truth, rtol=0.0, atol=1e-12):
        raise ValueError("target normalization drift")
    baseline_pred = _predict(baseline_model, baseline_features)
    adaptive_pred = _predict(adaptive_model, adaptive_features)
    baseline_mse = np.mean((baseline_truth - baseline_pred) ** 2, axis=0)
    adaptive_mse = np.mean((adaptive_truth - adaptive_pred) ** 2, axis=0)
    increments = tuple(
        _incremental_bps(float(base), float(adapt))
        for base, adapt in zip(baseline_mse, adaptive_mse, strict=True)
    )
    pooled_base = float(np.mean(baseline_mse))
    pooled_adapt = float(np.mean(adaptive_mse))
    pooled = _incremental_bps(pooled_base, pooled_adapt)
    positive = sum(value >= 1 for value in increments)
    max_regression = max((max(0, -value) for value in increments), default=0)
    passed = (
        baseline_features.shape[0] >= MINIMUM_R5_SCORED_OBSERVATIONS
        and positive >= MINIMUM_POSITIVE_TARGETS
        and pooled >= MINIMUM_POOLED_INCREMENTAL_BPS
        and max_regression <= MAXIMUM_TARGET_REGRESSION_BPS
    )
    return Validation(
        sample_count=baseline_features.shape[0],
        baseline_mse=tuple(float(x) for x in baseline_mse),
        adaptive_mse=tuple(float(x) for x in adaptive_mse),
        incremental_information_bps=increments,
        pooled_incremental_information_bps=pooled,
        positive_target_count=positive,
        maximum_target_regression_bps=max_regression,
        pass_gate=passed,
    )


def _extract_dataset(dataset: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    if _sha256_file(dataset) != DATASET_SHA256:
        raise ValueError("A2 Shared Lab dataset hash mismatch")
    if not zipfile.is_zipfile(dataset):
        raise ValueError("A2 Shared Lab dataset must be ZIP")
    temp = tempfile.TemporaryDirectory(prefix="qore-a2-lab-")
    root = Path(temp.name)
    with zipfile.ZipFile(dataset) as archive:
        archive.extractall(root)
    manifest = json.loads((root / "DATASET-MANIFEST.json").read_text())
    if manifest.get("dataset_sha256") not in {None, DATASET_SHA256}:
        raise ValueError("embedded dataset manifest hash drift")
    return temp, root



def _prepared_metadata_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".json")


def _save_prepared_partition(
    *,
    path: Path,
    partition: str,
    features: np.ndarray,
    targets: np.ndarray,
    source_times: tuple[datetime, ...],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if partition not in {"r6", "r5"}:
        raise ValueError("prepared partition must be r6 or r5")
    if features.ndim != 2 or features.shape[1] != len(BASELINE_FEATURE_NAMES):
        raise ValueError("prepared feature shape drift")
    if targets.ndim != 2 or targets.shape[1] != len(TARGET_NAMES):
        raise ValueError("prepared target shape drift")
    if features.shape[0] != targets.shape[0] or features.shape[0] != len(source_times):
        raise ValueError("prepared partition cardinality mismatch")
    if not np.isfinite(features).all() or not np.isfinite(targets).all():
        raise ValueError("prepared matrices must be finite")

    path.parent.mkdir(parents=True, exist_ok=True)
    source_ns = np.asarray(
        [int(item.timestamp() * 1_000_000_000) for item in source_times],
        dtype=np.int64,
    )
    np.savez(
        path,
        features=np.asarray(features, dtype=np.float64),
        targets=np.asarray(targets, dtype=np.float64),
        source_ns=source_ns,
    )
    matrix_sha256 = _sha256_file(path)
    payload = {
        "schema": "QORE_SHARED_A2_PREPARED_PARTITION_001",
        "capsule_id": CAPSULE_ID,
        "partition": partition,
        "dataset_sha256": DATASET_SHA256,
        "matrix_sha256": matrix_sha256,
        "feature_names": BASELINE_FEATURE_NAMES,
        "target_names": TARGET_NAMES,
        "row_count": int(features.shape[0]),
        "metadata": metadata,
        "future_market_used_for_source_features": False,
        "future_market_used_offline_for_validation_targets": True,
        "pnl_used": False,
        "trader_methodology_used": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    _prepared_metadata_path(path).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _load_prepared_partition(
    path: Path,
    *,
    expected_partition: str,
) -> tuple[np.ndarray, np.ndarray, tuple[datetime, ...], dict[str, Any]]:
    metadata_path = _prepared_metadata_path(path)
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if payload.get("capsule_id") != CAPSULE_ID:
        raise ValueError("prepared capsule identity drift")
    if payload.get("partition") != expected_partition:
        raise ValueError("prepared partition identity drift")
    if payload.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("prepared dataset identity drift")
    if payload.get("matrix_sha256") != _sha256_file(path):
        raise ValueError("prepared matrix hash mismatch")
    if tuple(payload.get("feature_names", ())) != BASELINE_FEATURE_NAMES:
        raise ValueError("prepared feature-name drift")
    if tuple(payload.get("target_names", ())) != TARGET_NAMES:
        raise ValueError("prepared target-name drift")

    with np.load(path, allow_pickle=False) as data:
        features = np.asarray(data["features"], dtype=np.float64)
        targets = np.asarray(data["targets"], dtype=np.float64)
        source_ns = np.asarray(data["source_ns"], dtype=np.int64)
    source_times = tuple(
        datetime.fromtimestamp(int(value) / 1_000_000_000, tz=UTC)
        for value in source_ns
    )
    if int(payload.get("row_count", -1)) != features.shape[0]:
        raise ValueError("prepared row-count drift")
    if features.shape[0] != targets.shape[0] or features.shape[0] != len(source_times):
        raise ValueError("prepared cardinality drift")
    return features, targets, source_times, payload


def _prepare_partition_from_dataset(
    dataset: Path,
    *,
    partition: str,
    output: Path,
) -> dict[str, Any]:
    temp, root = _extract_dataset(dataset)
    try:
        features, targets, source_times, metadata = _partition(root, partition)
        payload = _save_prepared_partition(
            path=output,
            partition=partition,
            features=features,
            targets=targets,
            source_times=source_times,
            metadata=metadata,
        )
        return {
            "capsule_id": CAPSULE_ID,
            "status": f"{partition.upper()}_PREPARED_PASS",
            "partition": partition,
            "dataset_sha256": DATASET_SHA256,
            "matrix_sha256": payload["matrix_sha256"],
            "row_count": payload["row_count"],
            "source_observation_count": metadata["source_observation_count"],
            "scored_novel_or_near_count": metadata["scored_novel_or_near_count"],
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        }
    finally:
        temp.cleanup()


def _mc23_from_prepared(
    *,
    r6_prepared: Path,
    r5_prepared: Path,
    output: Path,
) -> dict[str, Any]:
    r6_x, r6_y, _r6_times, r6_payload = _load_prepared_partition(
        r6_prepared,
        expected_partition="r6",
    )
    r5_x, r5_y, _r5_times, r5_payload = _load_prepared_partition(
        r5_prepared,
        expected_partition="r5",
    )
    r6_meta = dict(r6_payload["metadata"])
    r5_meta = dict(r5_payload["metadata"])
    if str(r6_meta["source_max"]) >= str(r5_meta["source_min"]):
        raise ValueError("R6/R5 temporal order invalid")

    r6_adaptive = _adaptive_design(r6_x)
    r5_adaptive = _adaptive_design(r5_x)
    baseline = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
    adaptive = _fit(
        r6_adaptive,
        r6_y,
        BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    validation = _evaluate(
        baseline,
        adaptive,
        r5_x,
        r5_adaptive,
        r5_y,
    )
    baseline_repeat = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
    adaptive_repeat = _fit(
        r6_adaptive,
        r6_y,
        BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    validation_repeat = _evaluate(
        baseline_repeat,
        adaptive_repeat,
        r5_x,
        r5_adaptive,
        r5_y,
    )
    deterministic = (
        baseline.fingerprint() == baseline_repeat.fingerprint()
        and adaptive.fingerprint() == adaptive_repeat.fingerprint()
        and validation == validation_repeat
    )
    if not deterministic:
        raise AssertionError("MC23 deterministic repeat failed")

    if validation.sample_count < MINIMUM_R5_SCORED_OBSERVATIONS:
        status = (
            "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_"
            "INSUFFICIENT_EVIDENCE"
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

    payload = {
        "capsule_id": CAPSULE_ID,
        "identity": "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_001",
        "preregistration": MC23_PREREG,
        "canonical_source_blobs": CANONICAL_SOURCE_BLOBS,
        "dataset_sha256": DATASET_SHA256,
        "status": status,
        "r6": r6_meta,
        "r5": r5_meta,
        "r6_prepared_matrix_sha256": r6_payload["matrix_sha256"],
        "r5_prepared_matrix_sha256": r5_payload["matrix_sha256"],
        "baseline_feature_names": BASELINE_FEATURE_NAMES,
        "adaptive_interaction_names": ADAPTIVE_INTERACTION_NAMES,
        "target_names": TARGET_NAMES,
        "baseline_model_fingerprint": baseline.fingerprint(),
        "adaptive_model_fingerprint": adaptive.fingerprint(),
        "validation": asdict(validation),
        "deterministic_repeat_pass": True,
        "temporal_order_pass": True,
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _half_life_from_prepared(
    *,
    r6_prepared: Path,
    r5_prepared: Path,
    mc23_result_path: Path,
    prior_mc24_path: Path,
    output: Path,
) -> dict[str, Any]:
    mc23 = json.loads(mc23_result_path.read_text(encoding="utf-8"))
    if mc23.get("status") != "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_PASS":
        raise ValueError("MC24 cannot bind failed MC23 adaptation")
    prior_mc24 = json.loads(prior_mc24_path.read_text(encoding="utf-8"))
    if prior_mc24.get("status") != "MC24_REAL_REGRESSION_SUITE_BOUND_PASS":
        raise ValueError("sealed prior MC24 regression evidence missing")
    if prior_mc24.get("catastrophic_forgetting_detected") is not False:
        raise ValueError("sealed prior MC24 detected forgetting")

    r6_x, r6_y, _r6_times, _ = _load_prepared_partition(
        r6_prepared,
        expected_partition="r6",
    )
    r5_x, r5_y, r5_times, _ = _load_prepared_partition(
        r5_prepared,
        expected_partition="r5",
    )
    r6_adaptive = _adaptive_design(r6_x)
    r5_adaptive = _adaptive_design(r5_x)
    baseline = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
    adaptive = _fit(
        r6_adaptive,
        r6_y,
        BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    if baseline.fingerprint() != mc23["baseline_model_fingerprint"]:
        raise ValueError("MC23 baseline fingerprint drift")
    if adaptive.fingerprint() != mc23["adaptive_model_fingerprint"]:
        raise ValueError("MC23 adaptive fingerprint drift")

    origin = min(r5_times)
    grouped: dict[int, list[int]] = {}
    for index, observed_at in enumerate(r5_times):
        age_days = int((observed_at - origin).total_seconds() // 86_400)
        grouped.setdefault(age_days // HALF_LIFE_BIN_DAYS, []).append(index)

    bins: list[dict[str, Any]] = []
    for bin_index in sorted(grouped):
        indexes = np.asarray(grouped[bin_index], dtype=np.int64)
        validation = _evaluate(
            baseline,
            adaptive,
            r5_x[indexes],
            r5_adaptive[indexes],
            r5_y[indexes],
        )
        bins.append(
            {
                "bin_index": bin_index,
                "start_age_days": bin_index * HALF_LIFE_BIN_DAYS,
                "end_age_days": (bin_index + 1) * HALF_LIFE_BIN_DAYS,
                "sample_count": validation.sample_count,
                "pooled_incremental_information_bps": (
                    validation.pooled_incremental_information_bps
                ),
                "maximum_target_regression_bps": (
                    validation.maximum_target_regression_bps
                ),
                "positive_target_count": validation.positive_target_count,
                "incremental_information_bps": (
                    validation.incremental_information_bps
                ),
            }
        )

    eligible = [
        row for row in bins
        if row["sample_count"] >= HALF_LIFE_MIN_SAMPLES_PER_BIN
    ]
    forgetting = any(
        row["maximum_target_regression_bps"] > MAXIMUM_TARGET_REGRESSION_BPS
        for row in eligible
    )
    half_life_days = None
    lower_bound_days = None
    reference = next(
        (
            row for row in eligible
            if row["pooled_incremental_information_bps"] > 0
        ),
        None,
    )
    empirical = False
    disposition = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_INSUFFICIENT_EVIDENCE"
    threshold = None
    if len(eligible) >= HALF_LIFE_MIN_ELIGIBLE_BINS and reference is not None:
        threshold = (
            reference["pooled_incremental_information_bps"]
            * HALF_LIFE_FRACTION_BPS
            // 10_000
        )
        after = [
            row for row in eligible
            if row["bin_index"] >= reference["bin_index"]
        ]
        for first, second in zip(after, after[1:], strict=False):
            if (
                second["bin_index"] == first["bin_index"] + 1
                and first["pooled_incremental_information_bps"] <= threshold
                and second["pooled_incremental_information_bps"] <= threshold
            ):
                half_life_days = first["start_age_days"]
                disposition = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_MEASURED"
                empirical = True
                break
        if not empirical:
            lower_bound_days = max(row["end_age_days"] for row in eligible)
            disposition = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_LOWER_BOUND"
            empirical = True

    completed = empirical and not forgetting
    payload = {
        "capsule_id": CAPSULE_ID,
        "identity": "QORE_SHARED_MC24_VALIDATED_ADAPTATION_HALF_LIFE_001",
        "preregistration": MC24_PREREG,
        "dataset_sha256": DATASET_SHA256,
        "status": (
            "MC24_VALIDATED_ADAPTATION_HALF_LIFE_PASS"
            if completed
            else "MC24_VALIDATED_ADAPTATION_HALF_LIFE_NOT_CLOSED"
        ),
        "half_life_disposition": disposition,
        "half_life_bins": bins,
        "eligible_bin_count": len(eligible),
        "reference_bin_index": None if reference is None else reference["bin_index"],
        "reference_incremental_information_bps": (
            None
            if reference is None
            else reference["pooled_incremental_information_bps"]
        ),
        "half_life_threshold_bps": threshold,
        "half_life_days": half_life_days,
        "lower_bound_days": lower_bound_days,
        "mc23_real_regime_adaptation_bound": True,
        "prior_real_regression_suite_bound": True,
        "empirical_half_life_validated": empirical,
        "catastrophic_forgetting_detected": forgetting,
        "retained_knowledge_non_degradation_pass": not forgetting,
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _mc23(dataset: Path, output: Path) -> dict[str, Any]:
    temp, root = _extract_dataset(dataset)
    try:
        r6_x, r6_y, _r6_times, r6_meta = _partition(root, "r6")
        r5_x, r5_y, _r5_times, r5_meta = _partition(root, "r5")
        if r6_meta["source_max"] >= r5_meta["source_min"]:
            raise ValueError("R6/R5 temporal order invalid")

        r6_adaptive = _adaptive_design(r6_x)
        r5_adaptive = _adaptive_design(r5_x)
        baseline = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
        adaptive = _fit(
            r6_adaptive,
            r6_y,
            BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
        )
        validation = _evaluate(
            baseline, adaptive, r5_x, r5_adaptive, r5_y
        )

        baseline_repeat = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
        adaptive_repeat = _fit(
            r6_adaptive,
            r6_y,
            BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
        )
        validation_repeat = _evaluate(
            baseline_repeat, adaptive_repeat, r5_x, r5_adaptive, r5_y
        )
        deterministic = (
            baseline.fingerprint() == baseline_repeat.fingerprint()
            and adaptive.fingerprint() == adaptive_repeat.fingerprint()
            and validation == validation_repeat
        )
        if not deterministic:
            raise AssertionError("MC23 deterministic repeat failed")

        if validation.sample_count < MINIMUM_R5_SCORED_OBSERVATIONS:
            status = (
                "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_"
                "INSUFFICIENT_EVIDENCE"
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

        payload = {
            "capsule_id": CAPSULE_ID,
            "identity": "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_001",
            "preregistration": MC23_PREREG,
            "canonical_source_blobs": CANONICAL_SOURCE_BLOBS,
            "dataset_sha256": DATASET_SHA256,
            "status": status,
            "r6": r6_meta,
            "r5": r5_meta,
            "baseline_feature_names": BASELINE_FEATURE_NAMES,
            "adaptive_interaction_names": ADAPTIVE_INTERACTION_NAMES,
            "target_names": TARGET_NAMES,
            "baseline_model_fingerprint": baseline.fingerprint(),
            "adaptive_model_fingerprint": adaptive.fingerprint(),
            "validation": asdict(validation),
            "deterministic_repeat_pass": True,
            "temporal_order_pass": True,
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
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        return payload
    finally:
        temp.cleanup()


def _half_life(
    dataset: Path,
    mc23_result_path: Path,
    output: Path,
) -> dict[str, Any]:
    mc23 = json.loads(mc23_result_path.read_text())
    if mc23.get("status") != "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_PASS":
        raise ValueError("MC24 cannot bind failed MC23 adaptation")
    temp, root = _extract_dataset(dataset)
    try:
        prior_mc24 = json.loads(
            (root / "sealed" / "mc24-real-regression-suite.json").read_text()
        )
        if prior_mc24.get("status") != "MC24_REAL_REGRESSION_SUITE_BOUND_PASS":
            raise ValueError("sealed prior MC24 regression evidence missing")
        if prior_mc24.get("catastrophic_forgetting_detected") is not False:
            raise ValueError("sealed prior MC24 detected forgetting")

        r6_x, r6_y, _r6_times, _ = _partition(root, "r6")
        r5_x, r5_y, r5_times, _ = _partition(root, "r5")
        r6_adaptive = _adaptive_design(r6_x)
        r5_adaptive = _adaptive_design(r5_x)
        baseline = _fit(r6_x, r6_y, BASELINE_FEATURE_NAMES)
        adaptive = _fit(
            r6_adaptive,
            r6_y,
            BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
        )
        if baseline.fingerprint() != mc23["baseline_model_fingerprint"]:
            raise ValueError("MC23 baseline fingerprint drift")
        if adaptive.fingerprint() != mc23["adaptive_model_fingerprint"]:
            raise ValueError("MC23 adaptive fingerprint drift")

        origin = min(r5_times)
        grouped: dict[int, list[int]] = {}
        for index, observed_at in enumerate(r5_times):
            age_days = int((observed_at - origin).total_seconds() // 86_400)
            grouped.setdefault(age_days // HALF_LIFE_BIN_DAYS, []).append(index)

        bins: list[dict[str, Any]] = []
        for bin_index in sorted(grouped):
            indexes = np.asarray(grouped[bin_index], dtype=np.int64)
            validation = _evaluate(
                baseline,
                adaptive,
                r5_x[indexes],
                r5_adaptive[indexes],
                r5_y[indexes],
            )
            bins.append(
                {
                    "bin_index": bin_index,
                    "start_age_days": bin_index * HALF_LIFE_BIN_DAYS,
                    "end_age_days": (bin_index + 1) * HALF_LIFE_BIN_DAYS,
                    "sample_count": validation.sample_count,
                    "pooled_incremental_information_bps": (
                        validation.pooled_incremental_information_bps
                    ),
                    "maximum_target_regression_bps": (
                        validation.maximum_target_regression_bps
                    ),
                    "positive_target_count": validation.positive_target_count,
                    "incremental_information_bps": (
                        validation.incremental_information_bps
                    ),
                }
            )

        eligible = [
            row for row in bins
            if row["sample_count"] >= HALF_LIFE_MIN_SAMPLES_PER_BIN
        ]
        forgetting = any(
            row["maximum_target_regression_bps"] > MAXIMUM_TARGET_REGRESSION_BPS
            for row in eligible
        )
        half_life_days = None
        lower_bound_days = None
        reference = next(
            (
                row for row in eligible
                if row["pooled_incremental_information_bps"] > 0
            ),
            None,
        )
        empirical = False
        status = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_INSUFFICIENT_EVIDENCE"
        threshold = None

        if len(eligible) >= HALF_LIFE_MIN_ELIGIBLE_BINS and reference is not None:
            threshold = (
                reference["pooled_incremental_information_bps"]
                * HALF_LIFE_FRACTION_BPS
                // 10_000
            )
            after = [
                row for row in eligible
                if row["bin_index"] >= reference["bin_index"]
            ]
            for first, second in zip(after, after[1:], strict=False):
                if (
                    second["bin_index"] == first["bin_index"] + 1
                    and first["pooled_incremental_information_bps"] <= threshold
                    and second["pooled_incremental_information_bps"] <= threshold
                ):
                    half_life_days = first["start_age_days"]
                    status = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_MEASURED"
                    empirical = True
                    break
            if not empirical:
                lower_bound_days = max(row["end_age_days"] for row in eligible)
                status = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_LOWER_BOUND"
                empirical = True

        completed = empirical and not forgetting
        payload = {
            "capsule_id": CAPSULE_ID,
            "identity": "QORE_SHARED_MC24_VALIDATED_ADAPTATION_HALF_LIFE_001",
            "preregistration": MC24_PREREG,
            "dataset_sha256": DATASET_SHA256,
            "status": (
                "MC24_VALIDATED_ADAPTATION_HALF_LIFE_PASS"
                if completed
                else "MC24_VALIDATED_ADAPTATION_HALF_LIFE_NOT_CLOSED"
            ),
            "half_life_disposition": status,
            "half_life_bins": bins,
            "eligible_bin_count": len(eligible),
            "reference_bin_index": None if reference is None else reference["bin_index"],
            "reference_incremental_information_bps": (
                None
                if reference is None
                else reference["pooled_incremental_information_bps"]
            ),
            "half_life_threshold_bps": threshold,
            "half_life_days": half_life_days,
            "lower_bound_days": lower_bound_days,
            "mc23_real_regime_adaptation_bound": True,
            "prior_real_regression_suite_bound": True,
            "empirical_half_life_validated": empirical,
            "catastrophic_forgetting_detected": forgetting,
            "retained_knowledge_non_degradation_pass": not forgetting,
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
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        return payload
    finally:
        temp.cleanup()


def _self_test() -> dict[str, Any]:
    rng = np.random.default_rng(11)
    train = rng.uniform(0.0, 1.0, size=(6_000, len(BASELINE_FEATURE_NAMES)))
    valid = rng.uniform(0.0, 1.0, size=(5_500, len(BASELINE_FEATURE_NAMES)))
    train_adaptive = _adaptive_design(train)
    valid_adaptive = _adaptive_design(valid)
    weights = np.array([0.8, -0.6, 0.5, 0.7, 0.4, -0.3])
    train_signal = train_adaptive[:, -6:] @ weights
    valid_signal = valid_adaptive[:, -6:] @ weights
    train_y = np.column_stack(
        tuple(
            train_signal + rng.normal(0, 0.05, train.shape[0])
            for _ in TARGET_NAMES
        )
    )
    valid_y = np.column_stack(
        tuple(
            valid_signal + rng.normal(0, 0.05, valid.shape[0])
            for _ in TARGET_NAMES
        )
    )
    baseline = _fit(train, train_y, BASELINE_FEATURE_NAMES)
    adaptive = _fit(
        train_adaptive,
        train_y,
        BASELINE_FEATURE_NAMES + ADAPTIVE_INTERACTION_NAMES,
    )
    result = _evaluate(
        baseline, adaptive, valid, valid_adaptive, valid_y
    )
    if not result.pass_gate or result.positive_target_count != 4:
        raise AssertionError("capsule synthetic mechanics self-test failed")
    repeat = _fit(train, train_y, BASELINE_FEATURE_NAMES)
    if repeat.fingerprint() != baseline.fingerprint():
        raise AssertionError("capsule deterministic model fingerprint failed")
    return {
        "capsule_id": CAPSULE_ID,
        "status": "PASS",
        "synthetic_mechanics_only": True,
        "r5_scientific_population_opened": False,
        "canonical_source_blobs": CANONICAL_SOURCE_BLOBS,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("self-test", "prepare-r6", "prepare-r5", "mc23", "mc23-prepared", "mc24", "mc24-prepared"),
        required=True,
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--mc23-result", type=Path)
    parser.add_argument("--r6-prepared", type=Path)
    parser.add_argument("--r5-prepared", type=Path)
    parser.add_argument("--prior-mc24", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.mode == "self-test":
        payload = _self_test()
        print(json.dumps(payload, sort_keys=True))
        return

    if args.mode in {"prepare-r6", "prepare-r5"}:
        if args.dataset is None or args.output is None:
            raise SystemExit("prepare-r6/prepare-r5 require --dataset and --output")
        partition = "r6" if args.mode == "prepare-r6" else "r5"
        payload = _prepare_partition_from_dataset(
            args.dataset,
            partition=partition,
            output=args.output,
        )
        print(json.dumps(payload, sort_keys=True))
        return

    if args.mode == "mc23-prepared":
        if args.r6_prepared is None or args.r5_prepared is None or args.output is None:
            raise SystemExit(
                "mc23-prepared requires --r6-prepared --r5-prepared --output"
            )
        payload = _mc23_from_prepared(
            r6_prepared=args.r6_prepared,
            r5_prepared=args.r5_prepared,
            output=args.output,
        )
        print(json.dumps(payload, sort_keys=True))
        raise SystemExit(
            0 if payload["real_novel_regime_validated_adaptation"] else 2
        )

    if args.mode == "mc24-prepared":
        if (
            args.r6_prepared is None
            or args.r5_prepared is None
            or args.mc23_result is None
            or args.prior_mc24 is None
            or args.output is None
        ):
            raise SystemExit(
                "mc24-prepared requires prepared matrices, MC23 result, "
                "prior MC24 evidence and --output"
            )
        payload = _half_life_from_prepared(
            r6_prepared=args.r6_prepared,
            r5_prepared=args.r5_prepared,
            mc23_result_path=args.mc23_result,
            prior_mc24_path=args.prior_mc24,
            output=args.output,
        )
        print(json.dumps(payload, sort_keys=True))
        raise SystemExit(0 if payload["mc24_completed_and_proven"] else 2)

    if args.dataset is None or args.output is None:
        raise SystemExit("mc23/mc24 require --dataset and --output")

    if args.mode == "mc23":
        payload = _mc23(args.dataset, args.output)
        print(json.dumps(payload, sort_keys=True))
        raise SystemExit(
            0 if payload["real_novel_regime_validated_adaptation"] else 2
        )

    if args.mc23_result is None:
        raise SystemExit("mc24 requires --mc23-result")
    payload = _half_life(args.dataset, args.mc23_result, args.output)
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if payload["mc24_completed_and_proven"] else 2)


if __name__ == "__main__":
    main()
