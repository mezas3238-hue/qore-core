"""Multi-horizon cumulative-incidence representation for Shared Core.

This module does not train a model. It receives causal, point-in-time
cumulative-incidence estimates for increasing horizons and converts them into a
compact timing profile.

The key distinction is between *direction* and *imminence*:
- direction asks whether adverse or favorable outcomes are more likely;
- imminence asks how much of the longer-horizon incidence is concentrated in
  the nearest horizon.

This representation is authority-free and contains no strategy, sizing, risk,
stop, target, order, broker or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HorizonIncidencePoint:
    horizon_bars: int
    adverse_bps: int
    favorable_bps: int

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            raise ValueError("horizon_bars must be positive")
        for name in ("adverse_bps", "favorable_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class MultiHorizonIncidenceProfile:
    horizons: tuple[int, ...]
    adverse_curve_bps: tuple[int, ...]
    favorable_curve_bps: tuple[int, ...]
    near_adverse_bps: int
    far_adverse_bps: int
    near_favorable_bps: int
    far_favorable_bps: int
    near_directional_margin_bps: int
    far_directional_margin_bps: int
    adverse_frontload_bps: int
    favorable_frontload_bps: int
    frontload_margin_bps: int
    adverse_curve_gain_bps: int
    favorable_curve_gain_bps: int
    adverse_monotonic_repairs: int
    favorable_monotonic_repairs: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.horizons) < 2:
            raise ValueError("at least two horizons are required")
        if len(self.horizons) != len(self.adverse_curve_bps):
            raise ValueError("adverse curve length mismatch")
        if len(self.horizons) != len(self.favorable_curve_bps):
            raise ValueError("favorable curve length mismatch")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("incidence profile cannot carry trading authority")


def _monotonic_curve(values: tuple[int, ...]) -> tuple[tuple[int, ...], int]:
    repaired: list[int] = []
    repairs = 0
    running = 0
    for value in values:
        current = max(0, min(10_000, int(value)))
        if current < running:
            current = running
            repairs += 1
        running = current
        repaired.append(current)
    return tuple(repaired), repairs


def _frontload(near: int, far: int) -> int:
    if far <= 0:
        return 0
    return max(0, min(10_000, near * 10_000 // far))


def build_multi_horizon_incidence_profile(
    points: tuple[HorizonIncidencePoint, ...],
) -> MultiHorizonIncidenceProfile:
    """Build an outcome-blind timing profile from cumulative incidences."""

    if len(points) < 2:
        raise ValueError("at least two horizon points are required")
    horizons = tuple(point.horizon_bars for point in points)
    if any(right <= left for left, right in zip(horizons, horizons[1:], strict=False)):
        raise ValueError("horizons must be strictly increasing")

    adverse_curve, adverse_repairs = _monotonic_curve(
        tuple(point.adverse_bps for point in points)
    )
    favorable_curve, favorable_repairs = _monotonic_curve(
        tuple(point.favorable_bps for point in points)
    )
    near_adverse = adverse_curve[0]
    far_adverse = adverse_curve[-1]
    near_favorable = favorable_curve[0]
    far_favorable = favorable_curve[-1]
    adverse_frontload = _frontload(near_adverse, far_adverse)
    favorable_frontload = _frontload(near_favorable, far_favorable)

    return MultiHorizonIncidenceProfile(
        horizons=horizons,
        adverse_curve_bps=adverse_curve,
        favorable_curve_bps=favorable_curve,
        near_adverse_bps=near_adverse,
        far_adverse_bps=far_adverse,
        near_favorable_bps=near_favorable,
        far_favorable_bps=far_favorable,
        near_directional_margin_bps=near_adverse - near_favorable,
        far_directional_margin_bps=far_adverse - far_favorable,
        adverse_frontload_bps=adverse_frontload,
        favorable_frontload_bps=favorable_frontload,
        frontload_margin_bps=adverse_frontload - favorable_frontload,
        adverse_curve_gain_bps=far_adverse - near_adverse,
        favorable_curve_gain_bps=far_favorable - near_favorable,
        adverse_monotonic_repairs=adverse_repairs,
        favorable_monotonic_repairs=favorable_repairs,
    )
