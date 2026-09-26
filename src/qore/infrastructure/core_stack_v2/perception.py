"""Causal market perception for Shared Core V2.

Perception is deliberately independent from historical outcomes. It describes
what the market is doing *now* from closed bars available no later than as_of.
Historical memory may consume this state later, but cannot create it.

No setup, risk, order, target or execution authority is carried here.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class PerceptionState(StrEnum):
    SUPPORTIVE = "SUPPORTIVE"
    MIXED = "MIXED"
    CONTRADICTORY = "CONTRADICTORY"
    ANOMALOUS = "ANOMALOUS"
    INSUFFICIENT = "INSUFFICIENT"


class ClosedBar(Protocol):
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class PerceptionVector:
    as_of: datetime
    side: str
    trend_state: PerceptionState
    volatility_state: PerceptionState
    compression_expansion_state: PerceptionState
    displacement_state: PerceptionState
    sweep_recovery_state: PerceptionState
    cross_market_state: PerceptionState
    anomaly_state: PerceptionState
    signed_efficiency_5: Decimal
    signed_efficiency_10: Decimal
    overlap_5: Decimal
    volatility_acceleration: Decimal
    signed_body_bias_5: Decimal
    sweep_recovery_ref: Decimal
    peer_consensus: Decimal
    peer_divergence: Decimal
    contradiction_score: int
    support_score: int
    evidence_cutoff_at: datetime
    order_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future perception evidence forbidden")
        if self.side not in {"long", "short"}:
            raise ValueError("side must be long or short")
        if self.contradiction_score < 0 or self.support_score < 0:
            raise ValueError("perception scores cannot be negative")
        if (
            self.order_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise ValueError("Shared perception cannot carry trading authority")


def _d(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _open(bar: ClosedBar) -> Decimal:
    return _d(bar.open)


def _high(bar: ClosedBar) -> Decimal:
    return _d(bar.high)


def _low(bar: ClosedBar) -> Decimal:
    return _d(bar.low)


def _close(bar: ClosedBar) -> Decimal:
    return _d(bar.close)


def _safe_div(left: Decimal, right: Decimal) -> Decimal:
    return Decimal(0) if right == 0 else left / right


def _range(bar: ClosedBar) -> Decimal:
    return max(Decimal(0), _high(bar) - _low(bar))


def _signed_efficiency(
    bars: Sequence[ClosedBar],
    *,
    sign: Decimal,
) -> Decimal:
    if len(bars) < 2:
        return Decimal(0)
    path = sum(
        (
            abs(_close(bars[index]) - _close(bars[index - 1]))
            for index in range(1, len(bars))
        ),
        Decimal(0),
    )
    return _safe_div(sign * (_close(bars[-1]) - _close(bars[0])), path)


def _body_bias(
    bars: Sequence[ClosedBar],
    *,
    sign: Decimal,
) -> Decimal:
    denominator = sum((_range(bar) for bar in bars), Decimal(0))
    numerator = sum(
        (sign * (_close(bar) - _open(bar)) for bar in bars),
        Decimal(0),
    )
    return _safe_div(numerator, denominator)


def _overlap(left: ClosedBar, right: ClosedBar) -> Decimal:
    intersection = max(
        Decimal(0),
        min(_high(left), _high(right)) - max(_low(left), _low(right)),
    )
    denominator = min(_range(left), _range(right))
    return min(Decimal(1), _safe_div(intersection, denominator))


def _mean_overlap(bars: Sequence[ClosedBar]) -> Decimal:
    if len(bars) < 2:
        return Decimal(1)
    values = [
        _overlap(left, right)
        for left, right in zip(bars, bars[1:], strict=False)
    ]
    return sum(values, Decimal(0)) / Decimal(len(values))


def _mean_range(bars: Sequence[ClosedBar]) -> Decimal:
    if not bars:
        return Decimal(0)
    return sum((_range(bar) for bar in bars), Decimal(0)) / Decimal(len(bars))


def _state_from_signed(
    value: Decimal,
    *,
    support: Decimal,
    contradict: Decimal,
) -> PerceptionState:
    if value >= support:
        return PerceptionState.SUPPORTIVE
    if value <= contradict:
        return PerceptionState.CONTRADICTORY
    return PerceptionState.MIXED


def perceive(
    *,
    as_of: datetime,
    side: str,
    reference_width: Decimal,
    nas_recent: Sequence[ClosedBar],
    nas_prior: Sequence[ClosedBar],
    sweep_to_signal: Sequence[ClosedBar],
    sp500_recent: Sequence[ClosedBar],
    us30_recent: Sequence[ClosedBar],
) -> PerceptionVector:
    """Build one causal perception vector from already-closed bars."""
    if reference_width <= 0:
        raise ValueError("reference_width must be positive")
    sign = Decimal(1) if side == "long" else Decimal(-1)
    all_bars = (
        tuple(nas_recent)
        + tuple(nas_prior)
        + tuple(sweep_to_signal)
        + tuple(sp500_recent)
        + tuple(us30_recent)
    )
    if not all_bars:
        cutoff = as_of
    else:
        cutoff = max(bar.closed_at for bar in all_bars)
        if cutoff > as_of:
            raise ValueError("future closed bar supplied to perception")

    nas5 = tuple(nas_recent[-5:])
    nas10 = tuple(nas_recent[-10:])
    eff5 = _signed_efficiency(nas5, sign=sign)
    eff10 = _signed_efficiency(nas10, sign=sign)
    overlap5 = _mean_overlap(nas5)
    body5 = _body_bias(nas5, sign=sign)
    current_vol = _mean_range(nas5)
    prior_vol = _mean_range(tuple(nas_prior[-20:]))
    vol_accel = _safe_div(current_vol, prior_vol)

    if sweep_to_signal:
        extreme = (
            min(_low(bar) for bar in sweep_to_signal)
            if side == "long"
            else max(_high(bar) for bar in sweep_to_signal)
        )
        recovery = sign * (_close(sweep_to_signal[-1]) - extreme)
        recovery_ref = recovery / reference_width
    else:
        recovery_ref = Decimal(0)

    def peer_move(bars: Sequence[ClosedBar]) -> Decimal:
        if len(bars) < 2:
            return Decimal(0)
        scale = _mean_range(bars)
        return _safe_div(
            sign * (_close(bars[-1]) - _open(bars[0])),
            scale * Decimal(len(bars)),
        )

    sp_move = peer_move(tuple(sp500_recent[-5:]))
    us_move = peer_move(tuple(us30_recent[-5:]))
    peer_consensus = (sp_move + us_move) / Decimal(2)
    peer_divergence = abs(sp_move - us_move)

    trend = _state_from_signed(
        (eff5 + eff10) / Decimal(2),
        support=Decimal("0.15"),
        contradict=Decimal("-0.15"),
    )
    displacement = _state_from_signed(
        body5,
        support=Decimal("0.10"),
        contradict=Decimal("-0.10"),
    )
    recovery_state = (
        PerceptionState.SUPPORTIVE
        if recovery_ref >= Decimal("0.20")
        else PerceptionState.CONTRADICTORY
        if recovery_ref < Decimal("0.08")
        else PerceptionState.MIXED
    )
    cross_state = (
        PerceptionState.ANOMALOUS
        if peer_divergence >= Decimal("0.80")
        else _state_from_signed(
            peer_consensus,
            support=Decimal("0.05"),
            contradict=Decimal("-0.05"),
        )
    )
    volatility = (
        PerceptionState.ANOMALOUS
        if vol_accel >= Decimal("2.25")
        else PerceptionState.SUPPORTIVE
        if Decimal("0.90") <= vol_accel <= Decimal("1.75")
        else PerceptionState.MIXED
    )
    compression_expansion = (
        PerceptionState.CONTRADICTORY
        if overlap5 >= Decimal("0.90") and abs(eff5) < Decimal("0.15")
        else PerceptionState.SUPPORTIVE
        if overlap5 <= Decimal("0.70") and eff5 > Decimal("0.10")
        else PerceptionState.MIXED
    )
    anomaly = (
        PerceptionState.ANOMALOUS
        if (
            vol_accel >= Decimal("2.25")
            or peer_divergence >= Decimal("0.80")
        )
        else PerceptionState.MIXED
    )

    states = (
        trend,
        displacement,
        recovery_state,
        cross_state,
        compression_expansion,
    )
    contradictions = sum(
        state in {PerceptionState.CONTRADICTORY, PerceptionState.ANOMALOUS}
        for state in states
    )
    supports = sum(state is PerceptionState.SUPPORTIVE for state in states)

    return PerceptionVector(
        as_of=as_of,
        side=side,
        trend_state=trend,
        volatility_state=volatility,
        compression_expansion_state=compression_expansion,
        displacement_state=displacement,
        sweep_recovery_state=recovery_state,
        cross_market_state=cross_state,
        anomaly_state=anomaly,
        signed_efficiency_5=eff5,
        signed_efficiency_10=eff10,
        overlap_5=overlap5,
        volatility_acceleration=vol_accel,
        signed_body_bias_5=body5,
        sweep_recovery_ref=recovery_ref,
        peer_consensus=peer_consensus,
        peer_divergence=peer_divergence,
        contradiction_score=contradictions,
        support_score=supports,
        evidence_cutoff_at=cutoff,
    )
