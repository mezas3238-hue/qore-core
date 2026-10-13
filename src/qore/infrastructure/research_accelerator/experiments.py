"""Parametric O(log n) indexed event screening and block bootstrap diagnostics.

Research outputs are NOT edge certification; hypothesis names and controls must be
precommitted to the config before looking at the forward outcomes.
"""
from __future__ import annotations

import csv
import json
from bisect import bisect_left
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from random import Random

from qore.infrastructure.research_accelerator.core import (
    BidBar,
    ResearchDataError,
    checked_time,
    digest,
    number,
)
from qore.infrastructure.research_accelerator.regimes import Regime, label_regimes

VALID_FEATURES = ("ob", "fvg", "displacement", "breaker")
VALID_CONTROLS = ("local_extreme",)


@dataclass(frozen=True, slots=True)
class Signal:
    event_id: str
    anchor_at: datetime
    available_at: datetime
    side: str
    anchor_price: Decimal
    features: dict[str, float]


def read_signals(path: Path) -> tuple[Signal, ...]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"event_id", "anchor_at", "available_at", "side", "anchor_price"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ResearchDataError("signals require event_id,anchor_at,available_at,side,anchor_price")
        extras = set(reader.fieldnames) - required
        if not extras.issubset(set(VALID_FEATURES)):
            raise ResearchDataError("unknown feature; do not execute arbitrary predicate code")
        output: list[Signal] = []
        seen: set[str] = set()
        for row in reader:
            event_id = row["event_id"]
            if not event_id or event_id in seen:
                raise ResearchDataError("missing or duplicate event identity")
            seen.add(event_id)
            t = checked_time(row["anchor_at"])
            available = checked_time(row["available_at"])
            if available > t:
                raise ResearchDataError("feature future availability (lookahead)")
            if row["side"] not in ("long", "short"):
                raise ResearchDataError("invalid direction")
            try:
                features = {k: float(row[k]) for k in extras}
            except (ValueError, TypeError) as exc:
                raise ResearchDataError("missing/invalid feature value") from exc
            if any(not 0 <= x <= 1 for x in features.values()):
                raise ResearchDataError("features must be normalized finite [0,1]")
            output.append(Signal(event_id, t, available, row["side"], number(row["anchor_price"]), features))
    if not output:
        raise ResearchDataError("empty signal export")
    return tuple(output)


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    name: str
    horizons_minutes: tuple[int, ...]
    feature_min: dict[str, float]
    controls: tuple[str, ...]
    block_bootstrap_draws: int
    seed: int
    regime_lookback: int = 30
    regime_trend_threshold: float = 0.6
    regime_high_vol_bps: float = 12.0

    @classmethod
    def read(cls, path: Path) -> ExperimentSpec:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ResearchDataError("experiment specification must be object")
        expected = {
            "name", "horizons_minutes", "feature_min", "controls",
            "block_bootstrap_draws", "seed",
        }
        if set(obj) != expected:
            raise ResearchDataError("spec requires exactly six frozen fields")
        if not isinstance(obj["name"], str) or not obj["name"].strip():
            raise ResearchDataError("experiment must be named")
        hz = obj["horizons_minutes"]
        if not isinstance(hz, list) or not hz or any(type(x) is not int or x < 1 for x in hz):
            raise ResearchDataError("positive whole-minute horizons required")
        if hz != sorted(set(hz)):
            raise ResearchDataError("horizons must be ordered and unique")
        feats = obj["feature_min"]
        if not isinstance(feats, dict) or any(
            k not in VALID_FEATURES or not isinstance(v, (int, float)) or not 0 <= v <= 1
            for k, v in feats.items()
        ):
            raise ResearchDataError("non-preregistered feature threshold")
        controls = obj["controls"]
        if not isinstance(controls, list) or any(x not in VALID_CONTROLS for x in controls):
            raise ResearchDataError("unsupported placebo")
        draws = obj["block_bootstrap_draws"]
        seed = obj["seed"]
        if type(draws) is not int or not 100 <= draws <= 100000:
            raise ResearchDataError("draws outside [100,100000]")
        if type(seed) is not int:
            raise ResearchDataError("seed must be integer")
        return cls(obj["name"], tuple(hz), feats, tuple(controls), draws, seed)


def _percentile(sorted_values: list[float], quantile: float) -> float:
    return sorted_values[min(len(sorted_values) - 1, int(quantile * (len(sorted_values) - 1)))]


def day_block_interval(pairs: list[tuple[datetime, float]], *, draws: int, seed: int) -> dict[str, float | int | None]:
    """Day-block bootstrap: group correlated events by UTC date, not IID signals."""
    if not pairs:
        return {"n": 0, "days": 0, "mean_bps": None, "ci_low_bps": None, "ci_high_bps": None}
    grouped: dict[str, list[float]] = {}
    for instant, outcome in pairs:
        grouped.setdefault(instant.astimezone(UTC).date().isoformat(), []).append(outcome)
    blocks = list(grouped.values())
    rng = Random(seed)
    stats = []
    for _ in range(draws):
        total = 0.0
        count = 0
        for _day in blocks:
            block = blocks[rng.randrange(len(blocks))]
            total += sum(block)
            count += len(block)
        stats.append(total / count)
    stats.sort()
    return {
        "n": len(pairs), "days": len(blocks),
        "mean_bps": sum(v for _, v in pairs) / len(pairs),
        "ci_low_bps": _percentile(stats, .025),
        "ci_high_bps": _percentile(stats, .975),
    }


def causal_local_extremes(bars: tuple[BidBar, ...], *, lookback: int = 10) -> tuple[Signal, ...]:
    """Control uses ONLY candles closed at or before anchor time, never future pivots."""
    if lookback < 2:
        raise ResearchDataError("local-extreme lookback too short")
    events: list[Signal] = []
    for i in range(lookback, len(bars)):
        window = bars[i - lookback:i + 1]
        current = bars[i]
        if current.low == min(b.low for b in window):
            events.append(Signal("ctrl_long_" + str(i), current.closed_at, current.closed_at, "long", current.close, {}))
        if current.high == max(b.high for b in window):
            events.append(Signal("ctrl_short_" + str(i), current.closed_at, current.closed_at, "short", current.close, {}))
    return tuple(events)


def _measure(
    signals: tuple[Signal, ...],
    bars: tuple[BidBar, ...],
    horizons: tuple[int, ...],
    regimes: tuple[Regime | None, ...],
    *,
    enforce_anchor: bool,
) -> tuple[dict[int, list[tuple[datetime, float]]], dict[int, dict[str, list[tuple[datetime, float]]]], int]:
    stamps = tuple(b.closed_at for b in bars)
    results: dict[int, list[tuple[datetime, float]]] = {h: [] for h in horizons}
    regime_results: dict[int, dict[str, list[tuple[datetime, float]]]] = {h: {} for h in horizons}
    missing = 0
    for signal in signals:
        idx = bisect_left(stamps, signal.anchor_at)
        if idx >= len(stamps) or stamps[idx] != signal.anchor_at:
            missing += 1
            continue
        if enforce_anchor and bars[idx].close != signal.anchor_price:
            raise ResearchDataError("signal anchor differs from observed closed BID M1 price")
        for h in horizons:
            target_at = signal.anchor_at + timedelta(minutes=h)
            j = bisect_left(stamps, target_at, lo=idx + 1)
            if j >= len(stamps) or stamps[j] != target_at:
                continue  # Gap, weekend or unavailable forward sample: do not interpolate
            sign = 1 if signal.side == "long" else -1
            value = float((bars[j].close / signal.anchor_price - 1) * 10000) * sign
            pair = (signal.anchor_at, value)
            results[h].append(pair)
            regime = regimes[idx]
            if regime is not None:
                key = regime.trend + "/" + regime.volatility + "/" + regime.phase
                regime_results[h].setdefault(key, []).append(pair)
    return results, regime_results, missing


def screen(
    spec: ExperimentSpec,
    bars: tuple[BidBar, ...],
    signals: tuple[Signal, ...],
) -> dict[str, object]:
    """Offline directional screening; BID-only means NEVER a net/executable P&L."""
    selected = tuple(
        s for s in signals
        if all(s.features.get(key, -1) >= threshold for key, threshold in spec.feature_min.items())
    )
    regimes = label_regimes(
        bars, lookback=spec.regime_lookback,
        trend_ratio_threshold=spec.regime_trend_threshold,
        high_vol_bps=spec.regime_high_vol_bps,
    )
    result, conditional, missing = _measure(
        selected, bars, spec.horizons_minutes, regimes, enforce_anchor=True,
    )
    report: dict[str, object] = {
        "schema": "qore.research-accelerator.screen.v1",
        "status": "DIRECTIONAL_DIAGNOSTIC_ONLY_NOT_EDGE_OR_NET",
        "name": spec.name, "signals_total": len(signals),
        "signals_selected": len(selected), "unmatched_anchors": missing,
        "horizons": {}, "controls": {}, "regime_diagnostics": {},
        "config_fingerprint": digest({
            "name": spec.name, "horizons": spec.horizons_minutes,
            "features": spec.feature_min, "controls": spec.controls,
            "bootstrap_draws": spec.block_bootstrap_draws, "seed": spec.seed,
        }),
    }
    primary = {}
    conditional_out = {}
    for h, pairs in result.items():
        primary[str(h)] = day_block_interval(pairs, draws=spec.block_bootstrap_draws, seed=spec.seed + h)
        conditional_out[str(h)] = {
            k: day_block_interval(v, draws=spec.block_bootstrap_draws, seed=spec.seed + h)
            for k, v in conditional[h].items()
        }
    report["horizons"] = primary
    report["regime_diagnostics"] = conditional_out
    if "local_extreme" in spec.controls:
        control = causal_local_extremes(bars)
        matched_sides = {s.side for s in selected}
        control = tuple(s for s in control if s.side in matched_sides)
        ctrl_results, _, _ = _measure(
            control, bars, spec.horizons_minutes, regimes, enforce_anchor=False,
        )
        report["controls"] = {
            "local_extreme": {
                str(h): day_block_interval(pairs, draws=spec.block_bootstrap_draws, seed=spec.seed + h)
                for h, pairs in ctrl_results.items()
            }
        }
    return report
