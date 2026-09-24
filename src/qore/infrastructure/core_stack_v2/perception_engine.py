"""Shared Perception Engine V1.\n\n# ruff: noqa: E501

Causal, decision-time market perception. This module deliberately contains no
PnL, outcome labels, analog search, order authority, risk authority or
execution authority. It converts the market that is observable *now* into a
deterministic situation vector that downstream Shared cognition may reason
about before consulting historical memory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
import json
from typing import Iterable

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PerceptionBar:
    opened_at: str
    closed_at: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def direction(self) -> int:
        if self.close > self.open:
            return 1
        if self.close < self.open:
            return -1
        return 0


@dataclass(frozen=True, slots=True)
class MarketPerception:
    as_of: str
    sample_bars: int
    short_range: Decimal
    long_range: Decimal
    volatility_ratio: Decimal | None
    short_body_fraction: Decimal | None
    long_body_fraction: Decimal | None
    overlap_rate: Decimal | None
    path_efficiency: Decimal | None
    displacement_ratio: Decimal | None
    directional_persistence: Decimal | None
    compression_score: Decimal | None
    expansion_score: Decimal | None
    momentum_state: str
    volatility_state: str
    structure_state: str
    anomaly_flags: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class SituationVector:
    as_of: str
    regime: str
    transition: str
    confidence_bps: int
    trend_pressure: Decimal
    range_pressure: Decimal
    expansion_pressure: Decimal
    exhaustion_pressure: Decimal
    uncertainty_pressure: Decimal
    anomaly_flags: tuple[str, ...]
    fingerprint: str


def _mean(values: Iterable[Decimal]) -> Decimal | None:
    items = tuple(values)
    if not items:
        return None
    return sum(items, ZERO) / Decimal(len(items))


def _range(window: tuple[PerceptionBar, ...]) -> Decimal:
    if not window:
        return ZERO
    return max(bar.high for bar in window) - min(bar.low for bar in window)


def _body_fraction(window: tuple[PerceptionBar, ...]) -> Decimal | None:
    total_range = sum((bar.range for bar in window), ZERO)
    if total_range <= 0:
        return None
    return sum((bar.body for bar in window), ZERO) / total_range


def _overlap_rate(window: tuple[PerceptionBar, ...]) -> Decimal | None:
    if len(window) < 2:
        return None
    overlaps = 0
    for left, right in zip(window, window[1:], strict=False):
        if min(left.high, right.high) >= max(left.low, right.low):
            overlaps += 1
    return Decimal(overlaps) / Decimal(len(window) - 1)


def _efficiency(window: tuple[PerceptionBar, ...]) -> Decimal | None:
    if len(window) < 2:
        return None
    travelled = sum(
        (abs(right.close - left.close) for left, right in zip(window, window[1:])),
        ZERO,
    )
    if travelled <= 0:
        return ZERO
    return abs(window[-1].close - window[0].open) / travelled


def _persistence(window: tuple[PerceptionBar, ...]) -> Decimal | None:
    dirs = tuple(bar.direction for bar in window if bar.direction)
    if not dirs:
        return None
    signed = abs(sum(dirs))
    return Decimal(signed) / Decimal(len(dirs))


def _fingerprint(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(normalized.encode()).hexdigest()


def perceive_market(
    bars: Iterable[PerceptionBar],
    *,
    as_of: str,
    short_window: int = 5,
    long_window: int = 20,
) -> MarketPerception:
    closed = tuple(
        sorted(
            (bar for bar in bars if bar.closed_at <= as_of),
            key=lambda bar: bar.closed_at,
        )
    )
    if not closed:
        raise ValueError("perception requires at least one closed bar")
    long = closed[-long_window:]
    short = closed[-short_window:]
    short_range = _range(short)
    long_range = _range(long)
    volatility_ratio = (
        None
        if long_range <= 0
        else short_range / long_range
    )
    short_body = _body_fraction(short)
    long_body = _body_fraction(long)
    overlap = _overlap_rate(short)
    efficiency = _efficiency(short)
    persistence = _persistence(short)
    mean_short_range = _mean(bar.range for bar in short)
    mean_long_range = _mean(bar.range for bar in long)
    displacement = (
        None
        if mean_long_range is None or mean_long_range <= 0 or mean_short_range is None
        else mean_short_range / mean_long_range
    )
    compression = (
        None
        if displacement is None
        else max(ZERO, Decimal("1") - displacement)
    )
    expansion = (
        None
        if displacement is None
        else max(ZERO, displacement - Decimal("1"))
    )

    flags: list[str] = []
    if overlap is not None and overlap >= Decimal("0.75"):
        flags.append("HIGH_OVERLAP")
    if efficiency is not None and efficiency >= Decimal("0.70"):
        flags.append("EFFICIENT_PATH")
    if displacement is not None and displacement >= Decimal("1.50"):
        flags.append("RANGE_EXPANSION")
    if displacement is not None and displacement <= Decimal("0.65"):
        flags.append("RANGE_COMPRESSION")
    if short_body is not None and short_body >= Decimal("0.70"):
        flags.append("BODY_DOMINANCE")
    if persistence is not None and persistence >= Decimal("0.70"):
        flags.append("DIRECTIONAL_PERSISTENCE")

    if (
        efficiency is not None
        and persistence is not None
        and efficiency >= Decimal("0.60")
        and persistence >= Decimal("0.60")
    ):
        momentum = "DIRECTIONAL"
    elif overlap is not None and overlap >= Decimal("0.70"):
        momentum = "ROTATIONAL"
    else:
        momentum = "MIXED"

    if displacement is None:
        volatility_state = "UNKNOWN"
    elif displacement >= Decimal("1.35"):
        volatility_state = "EXPANDING"
    elif displacement <= Decimal("0.75"):
        volatility_state = "COMPRESSING"
    else:
        volatility_state = "NORMAL"

    if momentum == "DIRECTIONAL" and volatility_state == "EXPANDING":
        structure = "IMPULSE"
    elif momentum == "ROTATIONAL":
        structure = "RANGE"
    elif volatility_state == "COMPRESSING":
        structure = "COMPRESSION"
    else:
        structure = "TRANSITIONAL"

    base = {
        "as_of": as_of,
        "sample_bars": len(long),
        "short_range": short_range,
        "long_range": long_range,
        "volatility_ratio": volatility_ratio,
        "short_body_fraction": short_body,
        "long_body_fraction": long_body,
        "overlap_rate": overlap,
        "path_efficiency": efficiency,
        "displacement_ratio": displacement,
        "directional_persistence": persistence,
        "compression_score": compression,
        "expansion_score": expansion,
        "momentum_state": momentum,
        "volatility_state": volatility_state,
        "structure_state": structure,
        "anomaly_flags": tuple(flags),
    }
    return MarketPerception(**base, fingerprint=_fingerprint(base))


def infer_situation(
    perception: MarketPerception,
    *,
    previous: MarketPerception | None = None,
) -> SituationVector:
    efficiency = perception.path_efficiency or ZERO
    persistence = perception.directional_persistence or ZERO
    overlap = perception.overlap_rate or ZERO
    expansion = perception.expansion_score or ZERO
    compression = perception.compression_score or ZERO
    body = perception.short_body_fraction or ZERO

    trend_pressure = (efficiency + persistence + body) / Decimal("3")
    range_pressure = (overlap + compression) / Decimal("2")
    expansion_pressure = min(Decimal("1"), expansion + body / Decimal("2"))
    exhaustion_pressure = ZERO
    if previous is not None:
        previous_eff = previous.path_efficiency or ZERO
        previous_disp = previous.displacement_ratio or Decimal("1")
        current_disp = perception.displacement_ratio or Decimal("1")
        if previous_eff > efficiency:
            exhaustion_pressure += min(Decimal("0.5"), previous_eff - efficiency)
        if previous_disp > current_disp:
            exhaustion_pressure += min(
                Decimal("0.5"),
                (previous_disp - current_disp) / Decimal("2"),
            )
    uncertainty = max(
        ZERO,
        Decimal("1") - max(trend_pressure, range_pressure, expansion_pressure),
    )

    if trend_pressure >= Decimal("0.60") and expansion_pressure >= Decimal("0.45"):
        regime = "TREND_EXPANSION"
    elif range_pressure >= Decimal("0.65"):
        regime = "RANGE"
    elif perception.volatility_state == "COMPRESSING":
        regime = "COMPRESSION"
    elif exhaustion_pressure >= Decimal("0.35"):
        regime = "EXHAUSTION"
    else:
        regime = "TRANSITION"

    transition = "STABLE"
    if previous is not None:
        previous_situation = infer_situation(previous, previous=None)
        if previous_situation.regime != regime:
            transition = f"{previous_situation.regime}_TO_{regime}"
        elif (
            perception.volatility_state != previous.volatility_state
            or perception.structure_state != previous.structure_state
        ):
            transition = "INTRA_REGIME_CHANGE"

    confidence = int(
        min(
            Decimal("10000"),
            max(trend_pressure, range_pressure, expansion_pressure) * Decimal("10000"),
        )
    )
    base = {
        "as_of": perception.as_of,
        "regime": regime,
        "transition": transition,
        "confidence_bps": confidence,
        "trend_pressure": trend_pressure,
        "range_pressure": range_pressure,
        "expansion_pressure": expansion_pressure,
        "exhaustion_pressure": exhaustion_pressure,
        "uncertainty_pressure": uncertainty,
        "anomaly_flags": perception.anomaly_flags,
    }
    return SituationVector(**base, fingerprint=_fingerprint(base))


def public_payload(value: MarketPerception | SituationVector) -> dict[str, object]:
    payload = asdict(value)
    return json.loads(json.dumps(payload, default=str))
