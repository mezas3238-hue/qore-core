"""Streaming conditional-edge surfaces for Trader Lab research evidence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from typing import cast

from qore.infrastructure.trader_lab.first_cohort_characterization import (
    _return_metrics,
    _summary,
)
from qore.infrastructure.traders.contracts import DemoTradingDecision
from qore.kernel.errors import InfrastructureError

MIN_SURFACE_TRADES = 10
STANDARD_SURFACES: tuple[tuple[str, ...], ...] = (
    ("side",),
    ("trend_regime",),
    ("trend_transition",),
    ("volatility_regime",),
    ("volatility_percentile_bucket",),
    ("session_context",),
    ("session_overlap",),
    ("hour_utc",),
    ("weekday_utc",),
    ("momentum_regime",),
    ("momentum_acceleration",),
    ("range_position",),
    ("gap_state",),
    ("cross_timeframe_alignment",),
    ("expansion_state",),
    ("side", "trend_regime"),
    ("side", "volatility_regime"),
    ("trend_regime", "volatility_regime"),
    ("side", "session_context"),
    ("side", "trend_regime", "volatility_regime"),
    ("side", "session_context", "volatility_regime"),
    ("hour_utc", "side"),
)


class ConditionalSurfaceError(InfrastructureError):
    __slots__ = ()


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values, Decimal(0)) / Decimal(len(values))


def observation_value(observation: dict[str, object], dimension: str) -> str:
    if dimension == "market":
        return str(observation["market"])
    if dimension == "side":
        decision = cast(dict[str, object], observation["decision"])
        value = decision.get("side")
        return "none" if value is None else str(value)
    state = cast(dict[str, object], observation["decision_time_state"])
    value = state.get(dimension)
    if value is None:
        raise ConditionalSurfaceError(
            f"unknown conditional surface dimension: {dimension}"
        )
    return str(value)


@dataclass(slots=True)
class SurfaceBucket:
    opportunity_count: int = 0
    evaluation_failure_count: int = 0
    abstain_count: int = 0
    setup_count: int = 0
    filled_count: int = 0
    returns: list[Decimal] = field(default_factory=list)
    mfe: list[Decimal] = field(default_factory=list)
    mae: list[Decimal] = field(default_factory=list)
    bars_to_fill: list[Decimal] = field(default_factory=list)
    holding_bars: list[Decimal] = field(default_factory=list)
    exit_reasons: Counter[str] = field(default_factory=Counter)

    def record(self, observation: dict[str, object]) -> None:
        self.opportunity_count += 1
        decision = cast(dict[str, object], observation["decision"])
        status = str(decision["status"])
        if status == "evaluation_failure":
            self.evaluation_failure_count += 1
            return
        if status == DemoTradingDecision.ABSTAIN.value:
            self.abstain_count += 1
            return
        if status != DemoTradingDecision.SETUP.value:
            return
        self.setup_count += 1
        outcome = cast(dict[str, object], observation["outcome_evaluation"])
        if outcome["trade_filled"] is not True:
            return
        self.filled_count += 1
        raw_return = outcome["trade_return_rate"]
        raw_mfe = outcome["mfe_fraction"]
        raw_mae = outcome["mae_fraction"]
        raw_bars_to_fill = outcome.get("bars_to_fill")
        raw_holding_bars = outcome.get("holding_bars")
        if isinstance(raw_return, str):
            self.returns.append(Decimal(raw_return))
        if isinstance(raw_mfe, str):
            self.mfe.append(Decimal(raw_mfe))
        if isinstance(raw_mae, str):
            self.mae.append(Decimal(raw_mae))
        if isinstance(raw_bars_to_fill, str):
            self.bars_to_fill.append(Decimal(raw_bars_to_fill))
        if isinstance(raw_holding_bars, str):
            self.holding_bars.append(Decimal(raw_holding_bars))
        exit_reason = outcome.get("exit_reason")
        if isinstance(exit_reason, str):
            self.exit_reasons[exit_reason] += 1

    def evidence_state(self) -> str:
        if self.filled_count < MIN_SURFACE_TRADES:
            return "INSUFFICIENT_EVIDENCE"
        mean_return = _mean(self.returns)
        positive = sum((value for value in self.returns if value > 0), Decimal(0))
        negative = abs(sum((value for value in self.returns if value < 0), Decimal(0)))
        if mean_return > 0 and positive > negative:
            return "FAVORABLE_EXPLORATORY"
        if mean_return < 0 and negative > positive:
            return "ADVERSE_EXPLORATORY"
        return "MIXED_UNCERTAIN"

    def payload(self) -> dict[str, object]:
        return {
            "opportunity_count": self.opportunity_count,
            "evaluation_failure_count": self.evaluation_failure_count,
            "abstain_count": self.abstain_count,
            "setup_count": self.setup_count,
            "filled_count": self.filled_count,
            "unfilled_setup_count": self.setup_count - self.filled_count,
            "fill_rate": (
                format(Decimal(self.filled_count) / Decimal(self.setup_count), "f")
                if self.setup_count
                else "0"
            ),
            "outcomes": _return_metrics(self.returns),
            "mfe_fraction": _summary(self.mfe),
            "mae_fraction": _summary(self.mae),
            "bars_to_fill": _summary(self.bars_to_fill),
            "holding_bars": _summary(self.holding_bars),
            "exit_reason_counts": dict(sorted(self.exit_reasons.items())),
            "evidence_state": self.evidence_state(),
            "certified": False,
            "fresh_holdout_required_for_promotion": True,
        }


class StreamingSurface:
    __slots__ = ("dimensions", "buckets")

    def __init__(self, dimensions: tuple[str, ...]) -> None:
        if not dimensions:
            raise ConditionalSurfaceError("surface dimensions cannot be empty")
        self.dimensions = dimensions
        self.buckets: dict[tuple[str, ...], SurfaceBucket] = {}

    def record(self, observation: dict[str, object]) -> None:
        key = tuple(
            observation_value(observation, dimension) for dimension in self.dimensions
        )
        self.buckets.setdefault(key, SurfaceBucket()).record(observation)

    def payload(self) -> dict[str, object]:
        cells = [
            {
                "conditions": dict(zip(self.dimensions, key, strict=True)),
                **bucket.payload(),
            }
            for key, bucket in sorted(self.buckets.items())
        ]
        return {
            "dimensions": list(self.dimensions),
            "cell_count": len(cells),
            "minimum_filled_trades_for_directional_label": MIN_SURFACE_TRADES,
            "cells": cells,
        }


def build_conditional_surface(
    observations: tuple[dict[str, object], ...],
    dimensions: tuple[str, ...],
) -> dict[str, object]:
    surface = StreamingSurface(dimensions)
    for observation in observations:
        surface.record(observation)
    return surface.payload()
