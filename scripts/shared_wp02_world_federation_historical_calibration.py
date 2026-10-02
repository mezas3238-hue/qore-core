"""Historical calibration lab for WP-02 Federation of Worlds.

VT31 is used only as a falsification laboratory that supplies immutable
opportunity timestamps. The lab never reads trade direction, entry, stop,
target, PnL or terminal outcome. At each timestamp it reconstructs generic
market dynamics from NAS100/SP500/US30 closed M1 observations.

R8 is the only calibration partition. A single posterior-temperature parameter
is fitted there using forward market-dynamics quality as an evaluation label.
The frozen parameter is then evaluated unchanged on R6 and R5.

Future market data is evaluation-only. It never enters WorldEvidence or the
runtime federation state.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelFamily,
)
from qore.infrastructure.core_stack_v2.multi_world_federation import (
    WorldEvidence,
    WorldFederationState,
    update_world_federation,
)
from qore.infrastructure.core_stack_v2.world_federation_calibration import (
    RealizedWorldQuality,
    WorldCalibrationEpisode,
    WorldEvaluationPartition,
    compare_calibration_to_holdout,
    episode_from_state,
    summarize_world_calibration,
)

SCHEMA = "qore.shared.wp02.world_federation_historical_calibration.v1"
IDENTITY = "QORE_SHARED_WP02_FEDERATION_HISTORICAL_CALIBRATION_001"
MARKETS = ("NAS100", "SP500", "US30")
FAMILIES = tuple(WorldModelFamily)
EXPECTED_COUNTS = {"r8": 228, "r6": 278, "r5": 316}
BASELINE_TEMPERATURE_BPS = 10_000
PRIOR_MEMORY_HALF_LIFE_SECONDS = 3_600
REGIME_TRANSITION_BPS = 500


@dataclass(frozen=True, slots=True)
class _Metric:
    net_bps: float
    path_bps: float
    efficiency: float
    range_mean_bps: float
    max_abs_return_bps: float
    wick_fraction: float


@dataclass(frozen=True, slots=True)
class _PreparedEpisode:
    as_of: datetime
    regime_key: str
    evidence: tuple[WorldEvidence, ...]
    realized_quality: tuple[RealizedWorldQuality, ...]


def _clamp_bps(value: float) -> int:
    return max(0, min(10_000, int(round(value))))


def _return_bps(last: float, first: float) -> float:
    if first == 0:
        return 0.0
    return (last / first - 1.0) * 10_000.0


def _signal_timestamps(path: Path) -> tuple[str, ...]:
    payload = cast(dict[str, Any], json.loads(path.read_text()))
    trades = cast(list[dict[str, Any]], payload["trades"])
    return tuple(sorted(str(row["signal_at"]) for row in trades))


def _load_market_windows(
    path: Path,
    signals: tuple[str, ...],
) -> dict[str, list[dict[str, Any]]]:
    payload = cast(dict[str, Any], json.loads(path.read_text()))
    periods = cast(dict[str, list[dict[str, Any]]], payload["periods"])
    bars = periods["M1"]
    closed_keys = [str(bar["closed_at"])[:19] for bar in bars]

    windows: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        signal_key = signal[:19]
        index = bisect.bisect_right(closed_keys, signal_key)
        windows[signal] = bars[max(0, index - 90) : min(len(bars), index + 45)]
    return windows


def _split(
    bars: list[dict[str, Any]],
    signal: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    signal_key = signal[:19]
    pre = [
        bar
        for bar in bars
        if str(bar["closed_at"])[:19] <= signal_key
    ]
    post = [
        bar
        for bar in bars
        if str(bar["opened_at"])[:19] >= signal_key
    ]
    return pre, post


def _ohlc(
    bars: list[dict[str, Any]],
) -> tuple[list[float], list[float], list[float], list[float]]:
    opened = [float(bar["open"]) for bar in bars]
    high = [float(bar["high"]) for bar in bars]
    low = [float(bar["low"]) for bar in bars]
    close = [float(bar["close"]) for bar in bars]
    return opened, high, low, close


def _metric(bars: list[dict[str, Any]]) -> _Metric:
    if len(bars) < 2:
        raise ValueError("market metric requires at least two M1 bars")

    opened, high, low, close = _ohlc(bars)
    one_minute = [
        _return_bps(close[index], close[index - 1])
        for index in range(1, len(close))
    ]
    net = _return_bps(close[-1], close[0])
    path = sum(abs(value) for value in one_minute)
    efficiency = 0.0 if path == 0 else abs(net) / path
    ranges = [
        (high[index] - low[index]) / close[index] * 10_000.0
        if close[index]
        else 0.0
        for index in range(len(close))
    ]
    wick = [
        1.0
        - (
            abs(close[index] - opened[index])
            / (high[index] - low[index])
            if high[index] > low[index]
            else 0.0
        )
        for index in range(len(close))
    ]
    return _Metric(
        net_bps=net,
        path_bps=path,
        efficiency=efficiency,
        range_mean_bps=statistics.fmean(ranges),
        max_abs_return_bps=max((abs(value) for value in one_minute), default=0.0),
        wick_fraction=statistics.fmean(wick),
    )


def _pre_signal_evidence(
    market_windows: dict[str, list[dict[str, Any]]],
    signal: str,
) -> tuple[tuple[WorldEvidence, ...], str] | None:
    metrics: dict[str, dict[int | str, _Metric | float]] = {}

    for market, bars in market_windows.items():
        pre, _ = _split(bars, signal)
        if len(pre) < 61:
            return None
        recent = pre[-5:]
        prior = pre[-25:-5]
        _, prior_high, prior_low, _ = _ohlc(prior)
        _, recent_high, recent_low, recent_close = _ohlc(recent)
        prior_peak = max(prior_high)
        prior_floor = min(prior_low)
        last_close = recent_close[-1]
        sweep = float(
            (max(recent_high) > prior_peak and last_close < prior_peak)
            or (min(recent_low) < prior_floor and last_close > prior_floor)
        )
        width = prior_peak - prior_floor
        position = 0.5 if width <= 0 else (last_close - prior_floor) / width
        metrics[market] = {
            5: _metric(pre[-5:]),
            15: _metric(pre[-15:]),
            60: _metric(pre[-60:]),
            "sweep": sweep,
            "edge": min(1.0, abs(position - 0.5) * 2.0),
        }

    def _m(market: str, horizon: int) -> _Metric:
        return cast(_Metric, metrics[market][horizon])

    def _coherence(horizon: int) -> tuple[float, float]:
        returns = [_m(market, horizon).net_bps for market in MARKETS]
        signs = [
            0 if abs(value) < 1e-12 else (1 if value > 0 else -1)
            for value in returns
        ]
        signed = sum(signs) / len(signs)
        return abs(signed), signed

    nas5 = _m("NAS100", 5)
    nas15 = _m("NAS100", 15)
    nas60 = _m("NAS100", 60)
    coherence15, direction15 = _coherence(15)
    coherence60, _ = _coherence(60)

    volatility_ratio = nas5.range_mean_bps / max(
        1e-9,
        nas60.range_mean_bps,
    )
    stretch = abs(nas15.net_bps) / max(
        1e-9,
        nas60.range_mean_bps * math.sqrt(15),
    )
    reversal = float(nas5.net_bps * nas15.net_bps < 0)
    sweep = cast(float, metrics["NAS100"]["sweep"])
    edge = cast(float, metrics["NAS100"]["edge"])

    momentum = min(
        1.0,
        0.35 * nas5.efficiency
        + 0.25 * nas15.efficiency
        + 0.20 * coherence15
        + 0.20 * coherence60,
    )
    liquidity = min(
        1.0,
        0.50 * sweep
        + 0.20 * nas5.wick_fraction
        + 0.15 * edge
        + 0.15 * (1.0 - nas5.efficiency),
    )
    mean_reversion = min(
        1.0,
        0.30 * min(1.0, stretch)
        + 0.30 * reversal
        + 0.20 * (1.0 - nas5.efficiency)
        + 0.20 * nas5.wick_fraction,
    )
    agency = min(
        1.0,
        0.35 * (1.0 - nas5.efficiency)
        + 0.25 * nas5.wick_fraction
        + 0.20 * min(1.0, volatility_ratio)
        + 0.20 * (1.0 - coherence15),
    )
    macro = min(
        1.0,
        0.40 * coherence60
        + 0.30 * coherence15
        + 0.15 * nas60.efficiency
        + 0.15 * nas15.efficiency,
    )
    event = min(
        1.0,
        0.45 * min(1.0, max(0.0, volatility_ratio - 1.0) / 1.5)
        + 0.35
        * min(
            1.0,
            nas5.max_abs_return_bps
            / max(1e-9, nas60.range_mean_bps * 2.0),
        )
        + 0.20 * (1.0 - coherence15),
    )
    known = [liquidity, momentum, mean_reversion, agency, macro, event]
    spread = max(known) - statistics.fmean(known)
    unresolved = min(
        1.0,
        0.45 * (1.0 - max(known))
        + 0.35 * (1.0 - spread)
        + 0.20 * (1.0 - min(1.0, abs(direction15))),
    )

    current = {
        WorldModelFamily.LIQUIDITY_DRIVEN: _clamp_bps(2_500 + 7_000 * liquidity),
        WorldModelFamily.MOMENTUM_DRIVEN: _clamp_bps(2_500 + 7_000 * momentum),
        WorldModelFamily.MEAN_REVERSION: _clamp_bps(
            2_500 + 7_000 * mean_reversion
        ),
        WorldModelFamily.AGENCY_INVENTORY: _clamp_bps(2_500 + 7_000 * agency),
        WorldModelFamily.MACRO_DRIVEN: _clamp_bps(2_500 + 7_000 * macro),
        WorldModelFamily.EVENT_DISLOCATION: _clamp_bps(2_500 + 7_000 * event),
        WorldModelFamily.UNRESOLVED: _clamp_bps(2_500 + 7_000 * unresolved),
    }

    causal = {
        WorldModelFamily.MOMENTUM_DRIVEN: _clamp_bps(
            3_000
            + 3_500 * coherence15
            + 3_500 * float(nas5.net_bps * nas15.net_bps >= 0)
        ),
        WorldModelFamily.MACRO_DRIVEN: _clamp_bps(
            2_500 + 4_000 * coherence15 + 3_500 * coherence60
        ),
        WorldModelFamily.LIQUIDITY_DRIVEN: _clamp_bps(
            3_000 + 5_000 * sweep + 2_000 * nas5.wick_fraction
        ),
        WorldModelFamily.MEAN_REVERSION: _clamp_bps(
            3_000 + 3_500 * reversal + 3_500 * (1.0 - nas5.efficiency)
        ),
        WorldModelFamily.AGENCY_INVENTORY: _clamp_bps(
            3_000
            + 3_500 * (1.0 - nas5.efficiency)
            + 3_500 * nas5.wick_fraction
        ),
        WorldModelFamily.EVENT_DISLOCATION: _clamp_bps(
            3_000
            + 5_000 * min(1.0, max(0.0, volatility_ratio - 1.0) / 1.5)
            + 2_000 * (1.0 - coherence15)
        ),
        WorldModelFamily.UNRESOLVED: _clamp_bps(3_500 + 6_500 * unresolved),
    }

    if event >= 0.68:
        regime = "DISLOCATION"
    elif momentum >= 0.67 and macro >= 0.58:
        regime = "TREND_COHERENT"
    elif mean_reversion >= 0.65 or agency >= 0.68:
        regime = "RANGE_ABSORPTION"
    elif liquidity >= 0.65:
        regime = "LIQUIDITY_TRANSITION"
    else:
        regime = "MIXED"

    as_of = datetime.fromisoformat(signal)
    evidence = tuple(
        WorldEvidence(
            family=family,
            as_of=as_of,
            prediction_error_bps=5_000,
            prediction_observation_count=0,
            causal_consistency_bps=causal[family],
            calibration_bps=5_000,
            trajectory_accuracy_bps=5_000,
            current_evidence_bps=current[family],
            integrity_bps=10_000,
        )
        for family in FAMILIES
    )
    return evidence, regime


def _future_quality(
    market_windows: dict[str, list[dict[str, Any]]],
    signal: str,
) -> tuple[RealizedWorldQuality, ...] | None:
    future: dict[str, dict[int | str, _Metric]] = {}

    for market, bars in market_windows.items():
        pre, post = _split(bars, signal)
        if len(pre) < 61 or len(post) < 30:
            return None
        future[market] = {
            5: _metric(post[:5]),
            15: _metric(post[:15]),
            30: _metric(post[:30]),
            "pre60": _metric(pre[-60:]),
        }

    def _m(market: str, horizon: int | str) -> _Metric:
        return future[market][horizon]

    nas5 = _m("NAS100", 5)
    nas15 = _m("NAS100", 15)
    nas30 = _m("NAS100", 30)
    pre60 = _m("NAS100", "pre60")
    returns30 = [_m(market, 30).net_bps for market in MARKETS]
    signs = [
        0 if abs(value) < 1e-12 else (1 if value > 0 else -1)
        for value in returns30
    ]
    coherence30 = abs(sum(signs)) / len(signs)
    same_5_30 = float(nas5.net_bps * nas30.net_bps > 0)
    same_15_30 = float(nas15.net_bps * nas30.net_bps > 0)
    volatility_ratio = nas30.range_mean_bps / max(
        1e-9,
        pre60.range_mean_bps,
    )
    standardized_jump = nas30.max_abs_return_bps / max(
        1e-9,
        pre60.range_mean_bps,
    )

    if abs(nas5.net_bps) < 1e-12:
        reversal = 0.30
    elif nas5.net_bps * nas30.net_bps < 0:
        reversal = 1.0
    else:
        reversal = max(
            0.0,
            min(
                1.0,
                1.0 - abs(nas30.net_bps) / (abs(nas5.net_bps) + 1e-9),
            ),
        )

    nas_pre, nas_post = _split(market_windows["NAS100"], signal)
    prior = nas_pre[-20:]
    _, prior_high, prior_low, _ = _ohlc(prior)
    _, future_high, future_low, future_close = _ohlc(nas_post[:30])
    prior_peak = max(prior_high)
    prior_floor = min(prior_low)
    prior_width = max(1e-9, prior_peak - prior_floor)
    liquidity = 0.0

    if max(future_high) > prior_peak:
        excursion = (max(future_high) - prior_peak) / prior_width
        reject = float(future_close[-1] < prior_peak)
        liquidity = max(
            liquidity,
            min(1.0, 0.40 * min(1.0, excursion * 4.0) + 0.60 * reject),
        )
    if min(future_low) < prior_floor:
        excursion = (prior_floor - min(future_low)) / prior_width
        reject = float(future_close[-1] > prior_floor)
        liquidity = max(
            liquidity,
            min(1.0, 0.40 * min(1.0, excursion * 4.0) + 0.60 * reject),
        )

    momentum = min(
        1.0,
        0.35 * same_5_30
        + 0.25 * same_15_30
        + 0.25 * nas30.efficiency
        + 0.15 * coherence30,
    )
    mean_reversion = min(
        1.0,
        0.55 * reversal
        + 0.25 * (1.0 - nas30.efficiency)
        + 0.20 * nas30.wick_fraction,
    )
    agency = min(
        1.0,
        0.45 * (1.0 - nas30.efficiency)
        + 0.25 * nas30.wick_fraction
        + 0.20 * min(1.0, volatility_ratio)
        + 0.10 * (1.0 - coherence30),
    )
    macro = min(
        1.0,
        0.45 * coherence30
        + 0.30 * same_15_30
        + 0.25 * nas30.efficiency,
    )
    event = min(
        1.0,
        0.45 * min(1.0, max(0.0, volatility_ratio - 1.0) / 1.5)
        + 0.45 * min(1.0, standardized_jump / 3.0)
        + 0.10 * (1.0 - coherence30),
    )
    known = [liquidity, momentum, mean_reversion, agency, macro, event]
    unresolved = min(
        1.0,
        0.55 * (1.0 - max(known))
        + 0.45 * (1.0 - (max(known) - statistics.fmean(known))),
    )
    values = {
        WorldModelFamily.LIQUIDITY_DRIVEN: liquidity,
        WorldModelFamily.MOMENTUM_DRIVEN: momentum,
        WorldModelFamily.MEAN_REVERSION: mean_reversion,
        WorldModelFamily.AGENCY_INVENTORY: agency,
        WorldModelFamily.MACRO_DRIVEN: macro,
        WorldModelFamily.EVENT_DISLOCATION: event,
        WorldModelFamily.UNRESOLVED: unresolved,
    }
    return tuple(
        RealizedWorldQuality(
            family=family,
            quality_bps=_clamp_bps(values[family] * 10_000),
        )
        for family in FAMILIES
    )


def _prepare_partition(
    *,
    trade_path: Path,
    evidence_paths: dict[str, Path],
) -> tuple[_PreparedEpisode, ...]:
    signals = _signal_timestamps(trade_path)
    windows_by_market = {
        market: _load_market_windows(evidence_paths[market], signals)
        for market in MARKETS
    }

    prepared: list[_PreparedEpisode] = []
    for signal in signals:
        local = {
            market: windows_by_market[market][signal]
            for market in MARKETS
        }
        pre = _pre_signal_evidence(local, signal)
        quality = _future_quality(local, signal)
        if pre is None or quality is None:
            continue
        evidence, regime = pre
        prepared.append(
            _PreparedEpisode(
                as_of=datetime.fromisoformat(signal),
                regime_key=regime,
                evidence=evidence,
                realized_quality=quality,
            )
        )
    return tuple(prepared)


def _run_partition(
    prepared: tuple[_PreparedEpisode, ...],
    *,
    partition: WorldEvaluationPartition,
    temperature_bps: int,
) -> tuple[WorldCalibrationEpisode, ...]:
    previous: WorldFederationState | None = None
    episodes: list[WorldCalibrationEpisode] = []
    for item in prepared:
        state = update_world_federation(
            as_of=item.as_of,
            evidence=item.evidence,
            epistemic_uncertainty_bps=0,
            ood_risk_bps=0,
            previous=previous,
            regime_transition_bps=REGIME_TRANSITION_BPS,
            prior_memory_half_life_seconds=PRIOR_MEMORY_HALF_LIFE_SECONDS,
            posterior_temperature_bps=temperature_bps,
        )
        episodes.append(
            episode_from_state(
                state=state,
                evaluated_at=item.as_of + timedelta(minutes=30),
                partition=partition,
                regime_key=item.regime_key,
                realized_quality=item.realized_quality,
            )
        )
        previous = state
    return tuple(episodes)


def _soft_target(
    episode: WorldCalibrationEpisode,
) -> dict[WorldModelFamily, float]:
    total = sum(max(1, item.quality_bps) for item in episode.realized_quality)
    return {
        item.family: max(1, item.quality_bps) / total
        for item in episode.realized_quality
    }


def _soft_metrics(
    episodes: tuple[WorldCalibrationEpisode, ...],
) -> dict[str, int]:
    brier_total = 0.0
    cross_entropy_total = 0.0
    for episode in episodes:
        target = _soft_target(episode)
        posterior = {
            family: probability_bps / 10_000.0
            for family, probability_bps in episode.posterior_bps
        }
        brier_total += sum(
            (posterior[family] - target[family]) ** 2
            for family in FAMILIES
        ) / len(FAMILIES)
        cross_entropy_total += -sum(
            target[family] * math.log(max(1e-12, posterior[family]))
            for family in FAMILIES
        )
    return {
        "soft_quality_brier_micros": int(
            round(brier_total / len(episodes) * 1_000_000)
        ),
        "soft_quality_cross_entropy_micros": int(
            round(cross_entropy_total / len(episodes) * 1_000_000)
        ),
    }


def _fit_temperature(
    prepared: tuple[_PreparedEpisode, ...],
) -> int:
    cache: dict[int, int] = {}

    def objective(log_temperature: float) -> int:
        raw = int(round(math.exp(log_temperature) / 100.0)) * 100
        temperature = max(5_000, min(50_000, raw))
        if temperature not in cache:
            episodes = _run_partition(
                prepared,
                partition=WorldEvaluationPartition.CALIBRATION,
                temperature_bps=temperature,
            )
            cache[temperature] = _soft_metrics(episodes)[
                "soft_quality_cross_entropy_micros"
            ]
        return cache[temperature]

    low = math.log(5_000.0)
    high = math.log(50_000.0)
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left = high - ratio * (high - low)
    right = low + ratio * (high - low)
    left_score = objective(left)
    right_score = objective(right)

    for _ in range(36):
        if left_score < right_score:
            high = right
            right = left
            right_score = left_score
            left = high - ratio * (high - low)
            left_score = objective(left)
        else:
            low = left
            left = right
            left_score = right_score
            right = low + ratio * (high - low)
            right_score = objective(right)

    candidate = int(round(math.exp((low + high) / 2.0) / 100.0)) * 100
    return max(5_000, min(50_000, candidate))


def _summary_payload(
    episodes: tuple[WorldCalibrationEpisode, ...],
) -> dict[str, Any]:
    summary = summarize_world_calibration(episodes)
    dominant_counts = Counter(
        max(
            episode.posterior_bps,
            key=lambda item: (item[1], item[0].value),
        )[0].value
        for episode in episodes
    )
    return {
        "partition": summary.partition.value,
        "episode_count": summary.episode_count,
        "top_world_accuracy_bps": summary.top_world_accuracy_bps,
        "expected_calibration_error_bps": (
            summary.expected_calibration_error_bps
        ),
        "brier_score_bps": summary.brier_score_bps,
        "mean_dominant_probability_bps": (
            summary.mean_dominant_probability_bps
        ),
        "mean_dominant_realized_quality_bps": (
            summary.mean_dominant_realized_quality_bps
        ),
        "monopoly_episode_count": summary.monopoly_episode_count,
        "monopoly_rate_bps": summary.monopoly_rate_bps,
        "regime_shift_count": summary.regime_shift_count,
        "recovered_regime_shift_count": (
            summary.recovered_regime_shift_count
        ),
        "unresolved_regime_shift_count": (
            summary.unresolved_regime_shift_count
        ),
        "mean_recovery_steps_milli": summary.mean_recovery_steps_milli,
        "dominant_world_counts": dict(sorted(dominant_counts.items())),
        **_soft_metrics(episodes),
    }


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r5_trades: Path,
    r8_evidence: dict[str, Path],
    r6_evidence: dict[str, Path],
    r5_evidence: dict[str, Path],
) -> dict[str, Any]:
    r8_prepared = _prepare_partition(
        trade_path=r8_trades,
        evidence_paths=r8_evidence,
    )
    r6_prepared = _prepare_partition(
        trade_path=r6_trades,
        evidence_paths=r6_evidence,
    )
    r5_prepared = _prepare_partition(
        trade_path=r5_trades,
        evidence_paths=r5_evidence,
    )

    prepared = {
        "r8": r8_prepared,
        "r6": r6_prepared,
        "r5": r5_prepared,
    }
    counts = {name: len(rows) for name, rows in prepared.items()}
    if counts != EXPECTED_COUNTS:
        raise AssertionError(
            f"WP02 historical calibration population drift: {counts}"
        )

    temperature = _fit_temperature(r8_prepared)

    baseline_r8 = _run_partition(
        r8_prepared,
        partition=WorldEvaluationPartition.CALIBRATION,
        temperature_bps=BASELINE_TEMPERATURE_BPS,
    )
    baseline_r6 = _run_partition(
        r6_prepared,
        partition=WorldEvaluationPartition.HOLDOUT,
        temperature_bps=BASELINE_TEMPERATURE_BPS,
    )
    baseline_r5 = _run_partition(
        r5_prepared,
        partition=WorldEvaluationPartition.HOLDOUT,
        temperature_bps=BASELINE_TEMPERATURE_BPS,
    )
    calibrated_r8 = _run_partition(
        r8_prepared,
        partition=WorldEvaluationPartition.CALIBRATION,
        temperature_bps=temperature,
    )
    calibrated_r6 = _run_partition(
        r6_prepared,
        partition=WorldEvaluationPartition.HOLDOUT,
        temperature_bps=temperature,
    )
    calibrated_r5 = _run_partition(
        r5_prepared,
        partition=WorldEvaluationPartition.HOLDOUT,
        temperature_bps=temperature,
    )

    baseline = {
        "r8": _summary_payload(baseline_r8),
        "r6": _summary_payload(baseline_r6),
        "r5": _summary_payload(baseline_r5),
    }
    calibrated = {
        "r8": _summary_payload(calibrated_r8),
        "r6": _summary_payload(calibrated_r6),
        "r5": _summary_payload(calibrated_r5),
    }

    r8_r6 = compare_calibration_to_holdout(
        calibration=calibrated_r8,
        holdout=calibrated_r6,
    )
    r8_r5 = compare_calibration_to_holdout(
        calibration=calibrated_r8,
        holdout=calibrated_r5,
    )

    gates = {
        "r8_population_exact": counts["r8"] == EXPECTED_COUNTS["r8"],
        "r6_population_exact": counts["r6"] == EXPECTED_COUNTS["r6"],
        "r5_population_exact": counts["r5"] == EXPECTED_COUNTS["r5"],
        "r6_temporally_disjoint": r8_r6.temporal_holdout,
        "r5_temporally_disjoint": r8_r5.temporal_holdout,
        "r8_no_single_world_monopoly": (
            calibrated["r8"]["monopoly_rate_bps"] == 0
        ),
        "r6_no_single_world_monopoly": (
            calibrated["r6"]["monopoly_rate_bps"] == 0
        ),
        "r5_no_single_world_monopoly": (
            calibrated["r5"]["monopoly_rate_bps"] == 0
        ),
        "r6_soft_brier_not_worse": (
            calibrated["r6"]["soft_quality_brier_micros"]
            <= baseline["r6"]["soft_quality_brier_micros"]
        ),
        "r6_cross_entropy_not_worse": (
            calibrated["r6"]["soft_quality_cross_entropy_micros"]
            <= baseline["r6"]["soft_quality_cross_entropy_micros"]
        ),
        "r5_soft_brier_not_worse": (
            calibrated["r5"]["soft_quality_brier_micros"]
            <= baseline["r5"]["soft_quality_brier_micros"]
        ),
        "r5_cross_entropy_not_worse": (
            calibrated["r5"]["soft_quality_cross_entropy_micros"]
            <= baseline["r5"]["soft_quality_cross_entropy_micros"]
        ),
    }
    passed = all(gates.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "status": (
            "WP02_HISTORICAL_CALIBRATION_PASS_RESEARCH_ONLY"
            if passed
            else "WP02_HISTORICAL_CALIBRATION_FALSIFIED"
        ),
        "population": counts,
        "calibration_partition": "r8",
        "holdout_partition": "r6",
        "replication_partition": "r5",
        "baseline_temperature_bps": BASELINE_TEMPERATURE_BPS,
        "frozen_r8_temperature_candidate_bps": temperature,
        "prior_memory_half_life_seconds": PRIOR_MEMORY_HALF_LIFE_SECONDS,
        "regime_transition_bps": REGIME_TRANSITION_BPS,
        "baseline": baseline,
        "calibrated": calibrated,
        "gates": gates,
        "passes_wp02_historical_calibration": passed,
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "trade_rows_used_only_for_signal_timestamp": True,
            "trade_direction_used": False,
            "trade_entry_used": False,
            "trade_stop_used": False,
            "trade_target_used": False,
            "trade_pnl_used": False,
            "trade_terminal_outcome_used": False,
            "future_market_used_for_world_evidence": False,
            "future_market_used_for_evaluation_labels_only": True,
            "temperature_fit_partition": "r8_only",
            "r6_used_for_temperature_fit": False,
            "r5_used_for_temperature_fit": False,
            "runtime_default_temperature_mutated": False,
            "calibration_candidate_promoted_to_universal_shared": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_sizing_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def _market_args(args: argparse.Namespace, prefix: str) -> dict[str, Path]:
    return {
        "NAS100": getattr(args, f"{prefix}_nas"),
        "SP500": getattr(args, f"{prefix}_sp"),
        "US30": getattr(args, f"{prefix}_us"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    for prefix in ("r8", "r6", "r5"):
        parser.add_argument(f"--{prefix}-nas", type=Path, required=True)
        parser.add_argument(f"--{prefix}-sp", type=Path, required=True)
        parser.add_argument(f"--{prefix}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r5_trades=args.r5_trades,
        r8_evidence=_market_args(args, "r8"),
        r6_evidence=_market_args(args, "r6"),
        r5_evidence=_market_args(args, "r5"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "temperature_bps": payload[
                    "frozen_r8_temperature_candidate_bps"
                ],
                "baseline": payload["baseline"],
                "calibrated": payload["calibrated"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
