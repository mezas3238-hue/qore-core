"""Bind cTrader DEMO behavior evidence into the CIBO economic-floor engine.

This adapter is passive research infrastructure. It converts one behavior-lab
case report into reconciled position economics only when the caller can prove
broker/protection reconciliation. It performs no capital action.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_economic_floor import (
    EconomicFloorResult,
    ReconciledPositionEconomics,
    evaluate_economic_floor,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import LiveBehaviorCaseReport


class CmaBehaviorBindingError(ValueError):
    """Behavior evidence cannot safely create an economic floor."""


def economic_floor_from_behavior_case(
    report: LiveBehaviorCaseReport,
    *,
    position_open: bool,
    broker_position_reconciled: bool,
    protection_reconciled: bool,
    mutation_outcome_unknown: bool,
    future_cost_reserve_usd: Decimal = Decimal(0),
    slippage_reserve_usd: Decimal = Decimal(0),
) -> EconomicFloorResult:
    """Evaluate one case conservatively from observed settlement/path evidence."""

    if not isinstance(report, LiveBehaviorCaseReport):
        raise CmaBehaviorBindingError("report must be LiveBehaviorCaseReport")
    if type(position_open) is not bool:
        raise CmaBehaviorBindingError("position_open must be bool")
    trader = _trader_lineage(report.trader)
    if report.trader is None or report.symbol is None:
        raise CmaBehaviorBindingError("case report missing trader/symbol identity")

    realized = _decimal_or_zero(report.realized_net_pnl, "realized_net_pnl")
    if position_open:
        if report.estimated_remaining_stop_pnl is None:
            return evaluate_economic_floor(
                ReconciledPositionEconomics(
                    trader_id=trader,
                    signal_fingerprint=_signal_fingerprint(report),
                    realized_net_pnl_usd=realized,
                    remaining_stop_worst_case_pnl_usd=Decimal(0),
                    future_cost_reserve_usd=future_cost_reserve_usd,
                    slippage_reserve_usd=slippage_reserve_usd,
                    broker_position_reconciled=False,
                    protection_reconciled=False,
                    mutation_outcome_unknown=mutation_outcome_unknown,
                )
            )
        remaining = _decimal_required(
            report.estimated_remaining_stop_pnl,
            "estimated_remaining_stop_pnl",
        )
    else:
        if "CTRADER_DEMO_EXIT_SETTLEMENT" not in report.settlement_events:
            return evaluate_economic_floor(
                ReconciledPositionEconomics(
                    trader_id=trader,
                    signal_fingerprint=_signal_fingerprint(report),
                    realized_net_pnl_usd=realized,
                    remaining_stop_worst_case_pnl_usd=Decimal(0),
                    future_cost_reserve_usd=future_cost_reserve_usd,
                    slippage_reserve_usd=slippage_reserve_usd,
                    broker_position_reconciled=False,
                    protection_reconciled=False,
                    mutation_outcome_unknown=mutation_outcome_unknown,
                )
            )
        remaining = Decimal(0)

    economics = ReconciledPositionEconomics(
        trader_id=trader,
        signal_fingerprint=_signal_fingerprint(report),
        realized_net_pnl_usd=realized,
        remaining_stop_worst_case_pnl_usd=remaining,
        future_cost_reserve_usd=future_cost_reserve_usd,
        slippage_reserve_usd=slippage_reserve_usd,
        broker_position_reconciled=broker_position_reconciled,
        protection_reconciled=protection_reconciled,
        mutation_outcome_unknown=mutation_outcome_unknown,
    )
    return evaluate_economic_floor(economics)


def _trader_lineage(value: str | None) -> TraderLineage:
    if value is None:
        raise CmaBehaviorBindingError("case report missing trader")
    try:
        return TraderLineage(value)
    except ValueError as error:
        raise CmaBehaviorBindingError(
            f"unsupported CMA trader lineage: {value}"
        ) from error


def _signal_fingerprint(report: LiveBehaviorCaseReport) -> str:
    if report.case_id.startswith("signal:"):
        value = report.case_id.removeprefix("signal:")
        if value:
            return value
    raise CmaBehaviorBindingError(
        "behavior case lacks signal-keyed identity"
    )


def _decimal_or_zero(value: str | None, field: str) -> Decimal:
    if value is None:
        return Decimal(0)
    return _decimal_required(value, field)


def _decimal_required(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise CmaBehaviorBindingError(f"{field} is not decimal") from error
    if not parsed.is_finite():
        raise CmaBehaviorBindingError(f"{field} must be finite")
    return parsed
