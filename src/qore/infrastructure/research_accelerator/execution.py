"""Conservative observed-tick execution diagnostic, not a broker execution guarantee.

A one-point quote sample does not establish all intrabar touch events.
Only SAME-INSTRUMENT/SAME-VENUE paired observations may support this simulation.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.research_accelerator.core import Quote, ResearchDataError


@dataclass(frozen=True, slots=True)
class LimitOrder:
    event_id: str
    activated_at: datetime
    expires_at: datetime
    forced_exit_at: datetime
    side: str
    limit: Decimal
    stop: Decimal
    target: Decimal


def _check(order: LimitOrder) -> None:
    if order.side not in ("long", "short"):
        raise ResearchDataError("invalid side")
    if not order.activated_at < order.expires_at <= order.forced_exit_at:
        raise ResearchDataError("invalid order chronology")
    if min(order.limit, order.stop, order.target) <= 0:
        raise ResearchDataError("positive limit, stop and target required")
    if order.side == "long" and not order.stop < order.limit < order.target:
        raise ResearchDataError("long stop < entry < target required")
    if order.side == "short" and not order.target < order.limit < order.stop:
        raise ResearchDataError("short target < entry < stop required")


def simulate_ticks(
    quotes: tuple[Quote, ...],
    orders: tuple[LimitOrder, ...],
    *,
    tick_size: Decimal,
    slippage_ticks: Decimal = Decimal("0"),
    commission_per_unit: Decimal = Decimal("0"),
) -> list[dict[str, str]]:
    """Executable-side quote observations; unfilled/unknown never equal zero-profit fills.

    LONG LIMIT: ASK <= limit, exit on BID; SHORT LIMIT: BID >= limit, exit on ASK.
    Stop uses worst-of observed quote or stop level, then adversarial slippage.
    TP uses target price (no positive price improvement). Time exit needs quote.
    """
    if tick_size <= 0 or slippage_ticks < 0 or commission_per_unit < 0:
        raise ResearchDataError("invalid fee, price increment or slip")
    timestamps = tuple(q.at for q in quotes)
    if any(a >= b for a, b in zip(timestamps, timestamps[1:], strict=False)):
        raise ResearchDataError("quotes must be strictly ordered")
    ledger: list[dict[str, str]] = []
    for order in orders:
        _check(order)
        i = bisect_left(timestamps, order.activated_at)
        fill: Decimal | None = None
        opened_at: datetime | None = None
        slip = tick_size * slippage_ticks
        while i < len(quotes) and quotes[i].at < order.expires_at:
            q = quotes[i]
            if order.side == "long" and q.ask <= order.limit:
                fill = min(q.ask + slip, order.limit + slip)
            elif order.side == "short" and q.bid >= order.limit:
                fill = max(q.bid - slip, order.limit - slip)
            if fill is not None:
                opened_at = q.at
                i += 1
                break
            i += 1
        if fill is None:
            ledger.append({"event_id": order.event_id, "status": "UNFILLED_OBSERVED_ONLY"})
            continue
        side_sign = Decimal("1") if order.side == "long" else Decimal("-1")
        exit_at: datetime | None = None
        exit_price: Decimal | None = None
        reason = "UNKNOWN_NO_EXIT_QUOTE"
        while i < len(quotes):
            q = quotes[i]
            if q.at > order.forced_exit_at:
                break
            exit_side = q.bid if order.side == "long" else q.ask
            if order.side == "long" and exit_side <= order.stop:
                exit_price = min(exit_side, order.stop) - slip
                reason = "STOP"
            elif order.side == "short" and exit_side >= order.stop:
                exit_price = max(exit_side, order.stop) + slip
                reason = "STOP"
            elif order.side == "long" and exit_side >= order.target:
                exit_price = order.target - slip
                reason = "TARGET"
            elif order.side == "short" and exit_side <= order.target:
                exit_price = order.target + slip
                reason = "TARGET"
            elif q.at >= order.forced_exit_at:
                exit_price = exit_side - side_sign * slip
                reason = "TIME"
            if exit_price is not None:
                exit_at = q.at
                break
            i += 1
        if exit_price is None or exit_at is None or opened_at is None:
            ledger.append({
                "event_id": order.event_id, "status": "INCOMPLETE_NO_EXIT_QUOTE",
                "opened_at": opened_at.isoformat() if opened_at else "",
            })
            continue
        pnl_points = (exit_price - fill) * side_sign
        net_points = pnl_points - commission_per_unit * 2
        ledger.append({
            "event_id": order.event_id, "status": "CLOSED_OBSERVED_TICKS",
            "opened_at": opened_at.isoformat(), "closed_at": exit_at.isoformat(),
            "fill_price": str(fill), "exit_price": str(exit_price),
            "gross_price_points_per_unit": str(pnl_points),
            "net_price_points_per_unit": str(net_points),
            "exit_reason": reason,
            "duration_seconds": str(int((exit_at - opened_at).total_seconds())),
        })
    return ledger
