#!/usr/bin/env python3
"""Postdecision capital-path diagnostics for causal CIBO replays.

This tool is read-only research instrumentation.  It consumes only completed
replay receipts and never feeds results back into predecision cognition,
Sizing, Portfolio, Risk, execution, tuning, or certification.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


def _d(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise ValueError(f"{name} must be Decimal-compatible") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def build_capital_path_diagnostics(
    replay: dict[str, Any],
    *,
    initial_capital_usd: Decimal = Decimal("60"),
) -> dict[str, object]:
    if initial_capital_usd <= 0 or not initial_capital_usd.is_finite():
        raise ValueError("initial_capital_usd must be finite positive")

    decisions_raw = replay.get("decision_receipts")
    settlements_raw = replay.get("settlement_receipts")
    if not isinstance(decisions_raw, list) or not isinstance(settlements_raw, list):
        raise ValueError("replay decision/settlement receipts are required")

    decision_by_signal: dict[str, dict[str, Any]] = {}
    for item in decisions_raw:
        if not isinstance(item, dict):
            raise ValueError("decision receipt must be mapping")
        signal = str(item.get("signal_fingerprint", ""))
        if not signal:
            raise ValueError("decision signal fingerprint is required")
        if signal in decision_by_signal:
            raise ValueError("duplicate decision signal fingerprint")
        decision_by_signal[signal] = item

    settlements = sorted(
        settlements_raw,
        key=lambda item: (
            str(item.get("settled_at", "")),
            str(item.get("signal_fingerprint", "")),
        ),
    )

    capital = initial_capital_usd
    peak = initial_capital_usd
    maximum_drawdown = Decimal(0)
    minimum_capital = initial_capital_usd
    minimum_event: dict[str, object] | None = None
    cumulative_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    gross_loss_by_trader: dict[str, Decimal] = defaultdict(Decimal)
    gross_profit_by_trader: dict[str, Decimal] = defaultdict(Decimal)

    fractions = (
        Decimal("0.90"),
        Decimal("0.75"),
        Decimal("0.50"),
        Decimal("0.33"),
        Decimal("0.25"),
    )
    first_crossing: dict[str, dict[str, object]] = {}
    worst_events: list[dict[str, object]] = []
    path: list[dict[str, object]] = []

    for index, settlement in enumerate(settlements, start=1):
        if not isinstance(settlement, dict):
            raise ValueError("settlement receipt must be mapping")
        signal = str(settlement.get("signal_fingerprint", ""))
        decision = decision_by_signal.get(signal)
        if decision is None:
            raise ValueError("settlement signal missing decision receipt")
        pnl = _d(settlement.get("realized_net_pnl_usd"), "realized_net_pnl_usd")
        trader = str(settlement.get("trader_id", ""))
        capital += pnl
        peak = max(peak, capital)
        drawdown = peak - capital
        maximum_drawdown = max(maximum_drawdown, drawdown)
        cumulative_by_trader[trader] += pnl
        if pnl < 0:
            gross_loss_by_trader[trader] += -pnl
        elif pnl > 0:
            gross_profit_by_trader[trader] += pnl

        event = {
            "settlement_index": index,
            "settled_at": settlement.get("settled_at"),
            "signal_fingerprint": signal,
            "trader_id": trader,
            "realized_net_pnl_usd": format(pnl, "f"),
            "capital_after_usd": format(capital, "f"),
            "peak_before_or_at_event_usd": format(peak, "f"),
            "drawdown_after_usd": format(drawdown, "f"),
            "risk_decision": decision.get("risk_decision"),
            "capital_disposition": decision.get("capital_disposition"),
            "sizing_mode": decision.get("sizing_mode"),
            "adaptive_leverage_multiplier": decision.get(
                "adaptive_leverage_multiplier"
            ),
            "requested_volume": decision.get("requested_volume"),
            "authorized_volume": decision.get("authorized_volume"),
            "requested_stop_risk_usd": decision.get("requested_stop_risk_usd"),
            "authorized_stop_risk_usd": decision.get("authorized_stop_risk_usd"),
        }
        path.append(event)

        if capital < minimum_capital:
            minimum_capital = capital
            minimum_event = dict(event)

        for fraction in fractions:
            key = format(fraction, "f")
            threshold = initial_capital_usd * fraction
            if key not in first_crossing and capital <= threshold:
                first_crossing[key] = {
                    **event,
                    "threshold_fraction_of_initial": key,
                    "threshold_capital_usd": format(threshold, "f"),
                }

        if pnl < 0:
            worst_events.append(event)

    worst_events.sort(
        key=lambda item: _d(item["realized_net_pnl_usd"], "event pnl")
    )

    with localcontext() as context:
        context.prec = 100
        ending_return_pct = (
            capital / initial_capital_usd - Decimal(1)
        ) * Decimal(100)
        maximum_drawdown_pct_of_initial = (
            maximum_drawdown / initial_capital_usd
        ) * Decimal(100)

    return {
        "schema": "qore.cibo.walk-forward-capital-path-diagnostics.v1",
        "research_only": True,
        "postdecision_only": True,
        "predecision_authority": False,
        "certification_claimed": False,
        "initial_capital_usd": format(initial_capital_usd, "f"),
        "ending_capital_usd": format(capital, "f"),
        "ending_return_percent": format(ending_return_pct, "f"),
        "peak_capital_usd": format(peak, "f"),
        "minimum_capital_usd": format(minimum_capital, "f"),
        "maximum_drawdown_usd": format(maximum_drawdown, "f"),
        "maximum_drawdown_percent_of_initial": format(
            maximum_drawdown_pct_of_initial, "f"
        ),
        "settlement_count": len(settlements),
        "first_threshold_crossings": first_crossing,
        "minimum_capital_event": minimum_event,
        "worst_settlement_events": worst_events[:25],
        "net_pnl_by_trader_usd": {
            key: format(value, "f")
            for key, value in sorted(cumulative_by_trader.items())
        },
        "gross_loss_by_trader_usd": {
            key: format(value, "f")
            for key, value in sorted(gross_loss_by_trader.items())
        },
        "gross_profit_by_trader_usd": {
            key: format(value, "f")
            for key, value in sorted(gross_profit_by_trader.items())
        },
        "capital_path": path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--initial-capital-usd", default="60")
    args = parser.parse_args()

    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    result = build_capital_path_diagnostics(
        replay,
        initial_capital_usd=_d(args.initial_capital_usd, "initial_capital_usd"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
