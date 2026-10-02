"""Real-operation falsification harness for Shared Core V2.

The harness compares VT31 actually executed trades against immutable Shared
Core shadow decisions produced no later than the corresponding entry time.

It never invents entries.  A Shared PASS reuses the exact realized R of the
real VT31 trade; a Shared ABSTAIN removes that trade from the shadow curve.
This makes the comparison use the same realized market path and actual
cost-adjusted trade outcome while preventing hindsight.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ShadowAction(StrEnum):
    PASS = "PASS"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class ActualTrade:
    trade_id: str
    entry_at: datetime
    exit_at: datetime
    realized_r: Decimal

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("trade_id must be non-empty")
        if self.entry_at.tzinfo is None or self.entry_at.utcoffset() is None:
            raise ValueError("entry_at must be timezone-aware")
        if self.exit_at.tzinfo is None or self.exit_at.utcoffset() is None:
            raise ValueError("exit_at must be timezone-aware")
        if self.exit_at < self.entry_at:
            raise ValueError("exit_at cannot predate entry_at")


@dataclass(frozen=True, slots=True)
class SharedShadowDecision:
    trade_id: str
    decided_at: datetime
    action: ShadowAction
    context_fingerprint: str

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("trade_id must be non-empty")
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() is None:
            raise ValueError("decided_at must be timezone-aware")
        if not self.context_fingerprint:
            raise ValueError("context_fingerprint must be non-empty")


@dataclass(frozen=True, slots=True)
class CurveMetrics:
    trades: int
    wins: int
    losses: int
    flats: int
    total_r: Decimal
    mean_r: Decimal
    profit_factor: Decimal | None
    max_drawdown_r: Decimal
    max_losing_streak: int


@dataclass(frozen=True, slots=True)
class OperationalFalsificationResult:
    baseline: CurveMetrics
    shared_shadow: CurveMetrics
    input_trades: int
    retained_trades: int
    density_retained: Decimal
    losses_avoided: int
    winners_sacrificed: int
    flats_sacrificed: int
    pf_delta_pct: Decimal | None
    total_r_delta: Decimal
    dd_reduction_pct: Decimal | None
    mean_r_delta_pct: Decimal | None
    exact_opportunity_binding: bool
    all_shadow_decisions_pre_entry: bool
    current_outcome_used_by_shadow: bool = False
    shared_order_authority: bool = False
    shared_risk_authority: bool = False


def _metrics(values: tuple[Decimal, ...]) -> CurveMetrics:
    if not values:
        return CurveMetrics(
            trades=0,
            wins=0,
            losses=0,
            flats=0,
            total_r=Decimal(0),
            mean_r=Decimal(0),
            profit_factor=None,
            max_drawdown_r=Decimal(0),
            max_losing_streak=0,
        )

    wins = sum(1 for value in values if value > 0)
    losses = sum(1 for value in values if value < 0)
    flats = len(values) - wins - losses
    gross_win = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))

    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return CurveMetrics(
        trades=len(values),
        wins=wins,
        losses=losses,
        flats=flats,
        total_r=total,
        mean_r=total / Decimal(len(values)),
        profit_factor=(gross_win / gross_loss if gross_loss > 0 else None),
        max_drawdown_r=max_dd,
        max_losing_streak=max_streak,
    )


def _pct_delta(new: Decimal, old: Decimal) -> Decimal | None:
    if old == 0:
        return None
    return (new / old - Decimal(1)) * Decimal(100)


def evaluate_real_operation_falsification(
    trades: tuple[ActualTrade, ...],
    decisions: tuple[SharedShadowDecision, ...],
) -> OperationalFalsificationResult:
    """Evaluate exact real VT31 trades against pre-entry Shared shadow decisions."""
    if not trades:
        raise ValueError("real-operation falsification requires closed actual trades")

    trade_ids = tuple(item.trade_id for item in trades)
    decision_ids = tuple(item.trade_id for item in decisions)
    if len(set(trade_ids)) != len(trade_ids):
        raise ValueError("actual trade ids must be unique")
    if len(set(decision_ids)) != len(decision_ids):
        raise ValueError("shadow decision ids must be unique")
    if set(trade_ids) != set(decision_ids):
        raise ValueError("actual trades and shadow decisions must bind exactly")

    by_decision = {item.trade_id: item for item in decisions}
    ordered = tuple(sorted(trades, key=lambda item: (item.entry_at, item.trade_id)))

    for trade in ordered:
        decision = by_decision[trade.trade_id]
        if decision.decided_at > trade.entry_at:
            raise ValueError(
                f"shadow decision for {trade.trade_id} was produced after entry"
            )

    baseline_values = tuple(item.realized_r for item in ordered)
    retained = tuple(
        item
        for item in ordered
        if by_decision[item.trade_id].action is ShadowAction.PASS
    )
    retained_values = tuple(item.realized_r for item in retained)
    abstained = tuple(
        item
        for item in ordered
        if by_decision[item.trade_id].action is ShadowAction.ABSTAIN
    )

    baseline = _metrics(baseline_values)
    shared = _metrics(retained_values)

    pf_delta: Decimal | None = None
    if baseline.profit_factor is not None and shared.profit_factor is not None:
        pf_delta = _pct_delta(shared.profit_factor, baseline.profit_factor)

    dd_reduction: Decimal | None = None
    if baseline.max_drawdown_r > 0:
        dd_reduction = (
            Decimal(1) - shared.max_drawdown_r / baseline.max_drawdown_r
        ) * Decimal(100)

    return OperationalFalsificationResult(
        baseline=baseline,
        shared_shadow=shared,
        input_trades=len(ordered),
        retained_trades=len(retained),
        density_retained=Decimal(len(retained)) / Decimal(len(ordered)),
        losses_avoided=sum(1 for item in abstained if item.realized_r < 0),
        winners_sacrificed=sum(1 for item in abstained if item.realized_r > 0),
        flats_sacrificed=sum(1 for item in abstained if item.realized_r == 0),
        pf_delta_pct=pf_delta,
        total_r_delta=shared.total_r - baseline.total_r,
        dd_reduction_pct=dd_reduction,
        mean_r_delta_pct=_pct_delta(shared.mean_r, baseline.mean_r),
        exact_opportunity_binding=True,
        all_shadow_decisions_pre_entry=True,
    )
