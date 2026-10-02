"""Predictive-coding engine for Shared Core.

The engine compares expected near-term market consequences against observed
ones. Prediction error is treated as evidence that should revise world-model
and hypothesis confidence, not as a simple "signal failure".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PredictiveChannel(StrEnum):
    VOLATILITY = "VOLATILITY"
    DISPLACEMENT = "DISPLACEMENT"
    RETRACEMENT_DEPTH = "RETRACEMENT_DEPTH"
    INTERMARKET_REACTION = "INTERMARKET_REACTION"
    LIQUIDITY_RESPONSE = "LIQUIDITY_RESPONSE"


@dataclass(frozen=True, slots=True)
class PredictiveExpectation:
    channel: PredictiveChannel
    expected_bps: int
    tolerance_bps: int

    def __post_init__(self) -> None:
        for name in ("expected_bps", "tolerance_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class PredictiveObservation:
    channel: PredictiveChannel
    observed_bps: int

    def __post_init__(self) -> None:
        if not 0 <= self.observed_bps <= 10_000:
            raise ValueError("observed_bps must be within 0..10000")


@dataclass(frozen=True, slots=True)
class PredictionError:
    channel: PredictiveChannel
    signed_error_bps: int
    absolute_error_bps: int
    normalized_error_bps: int
    surprise_bps: int

    def __post_init__(self) -> None:
        if not -10_000 <= self.signed_error_bps <= 10_000:
            raise ValueError("signed prediction error must be within -10000..10000")
        for name in ("absolute_error_bps", "normalized_error_bps", "surprise_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class PredictiveCodingState:
    errors: tuple[PredictionError, ...]
    aggregate_surprise_bps: int
    model_revision_pressure_bps: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("aggregate_surprise_bps", "model_revision_pressure_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("predictive coding cannot carry trading authority")


def compute_predictive_coding_state(
    *,
    expectations: tuple[PredictiveExpectation, ...],
    observations: tuple[PredictiveObservation, ...],
) -> PredictiveCodingState:
    """Convert expected-vs-observed discrepancies into cognitive evidence."""

    expected = {item.channel: item for item in expectations}
    observed = {item.channel: item for item in observations}
    if set(expected) != set(observed):
        raise ValueError("predictive channels must match exactly")
    if not expected:
        raise ValueError("at least one predictive channel is required")

    errors: list[PredictionError] = []
    for channel in sorted(expected, key=lambda item: item.value):
        exp_item = expected[channel]
        obs_item = observed[channel]
        signed = obs_item.observed_bps - exp_item.expected_bps
        absolute = abs(signed)
        tolerance = max(1, exp_item.tolerance_bps)
        normalized = min(10_000, absolute * 10_000 // tolerance)
        surprise = min(
            10_000,
            max(0, normalized - 10_000) if normalized > 10_000 else normalized,
        )
        errors.append(
            PredictionError(
                channel=channel,
                signed_error_bps=signed,
                absolute_error_bps=absolute,
                normalized_error_bps=normalized,
                surprise_bps=surprise,
            )
        )

    aggregate = sum(item.surprise_bps for item in errors) // len(errors)
    severe = sum(item.surprise_bps >= 7_500 for item in errors)
    revision_pressure = min(
        10_000,
        aggregate + severe * 750,
    )
    return PredictiveCodingState(
        errors=tuple(errors),
        aggregate_surprise_bps=aggregate,
        model_revision_pressure_bps=revision_pressure,
    )
