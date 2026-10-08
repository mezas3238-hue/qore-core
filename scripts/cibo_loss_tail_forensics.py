#!/usr/bin/env python3
"""Reproducible EX-POST CIBO loss audit. Never use realized labels as causal trade signals."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

D = Decimal


def audit(payload: dict, raw: bytes, target: Decimal) -> dict:
    trades = payload["trade_receipts"]
    assert len(trades) == payload["decision_count"] == payload["trade_count"] == 3368
    assert payload["economic_group_report"]["all_entries_preserved"] is True
    assert D(payload["attack_sovereign_breach_usd"]) == 0
    groups = defaultdict(lambda: {"trades": 0, "losers": 0, "winners": 0,
                                  "gross_loss": D(0), "gross_profit": D(0),
                                  "provider_costs": D(0)})
    losers = []
    gross_loss = gross_profit = D(0)
    for trade in trades:
        pnl = D(trade["realized_net_pnl_usd"])
        row = groups[trade["mode"]]
        row["trades"] += 1
        row["provider_costs"] += D(trade["provider_cost_usd"])
        if pnl < 0:
            gross_loss -= pnl
            row["losers"] += 1
            row["gross_loss"] -= pnl
            losers.append((-pnl, trade))
        elif pnl > 0:
            gross_profit += pnl
            row["winners"] += 1
            row["gross_profit"] += pnl
    ledger = payload["economic_group_report"]["portfolio_loss_report"]
    assert gross_loss == D(ledger["total_gross_loss_usd"])
    assert gross_profit == D(ledger["total_gross_profit_usd"])
    final = D(payload["ending_total_capital_usd"])
    initial = D(payload["initial_capital_usd"])
    assert abs(initial + gross_profit - gross_loss - final) <= D("0.00000001")
    losers.sort(key=lambda pair: pair[0], reverse=True)

    distribution = []
    for k in (1, 3, 5, 10, 20, 30, 50, 100, 200):
        top = losers[:k]
        loss = sum((x[0] for x in top), D(0))
        costs = sum((D(x[1]["provider_cost_usd"]) for x in top), D(0))
        stop = sum((D(x[1]["stop_risk_usd"]) for x in top), D(0))
        distribution.append({"n": k, "loss_usd": str(loss),
                             "share_of_all_losses_pct": str(loss / gross_loss * 100),
                             "costs_usd": str(costs),
                             "registered_stop_risk_usd": str(stop)})

    dd_episodes = []
    for item in payload["drawdown_forensics"]["top_10_episodes"]:
        peak = D(item["peak_capital_usd"])
        drawdown_loss = D(item["drawdown_usd"])
        start, end = item["peak_at"], item["trough_at"]
        closed = [r for r in trades if start < r["realized_exit_at"] <= end]
        losing = sum((-D(r["realized_net_pnl_usd"]) for r in closed
                      if D(r["realized_net_pnl_usd"]) < 0), D(0))
        winning = sum((D(r["realized_net_pnl_usd"]) for r in closed
                       if D(r["realized_net_pnl_usd"]) > 0), D(0))
        dd_episodes.append({
            "rank": item["rank"], "peak_at": start, "trough_at": end,
            "peak_usd": str(peak), "drawdown_loss_usd": str(drawdown_loss),
            "drawdown_pct": str(D(item["drawdown_fraction"]) * 100),
            "minimum_loss_reduction_fixed_peak_usd": str(max(D(0), drawdown_loss - target * peak)),
            "net_by_mode_usd": item["net_by_mode_usd"],
            "settlements": len(closed),
            "losing_settlements": sum(D(r["realized_net_pnl_usd"]) < 0 for r in closed),
            "gross_loss_in_window_usd": str(losing),
            "gross_profit_in_window_usd": str(winning),
        })

    def to_strings(row: dict) -> dict:
        return {key: str(value) if isinstance(value, D) else value
                for key, value in row.items()}

    return {
        "schema": "qore.cibo.loss-tail-forensics.v1",
        "research_only": True,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "causal_decision_feature": False,
        "warning": "Trade outcomes, drawdown episodes and post-decision PnL are hindsight diagnostics, NOT live eligibility or stop triggers.",
        "target_max_drawdown_pct": str(target * 100),
        "decision_count": len(trades),
        "negative_count": len(losers),
        "positive_count": sum(g["winners"] for g in groups.values()),
        "initial_capital_usd": str(initial), "final_capital_usd": str(final),
        "max_dd_pct": str(D(payload["max_drawdown_fraction"]) * 100),
        "total_gross_loss_usd": str(gross_loss),
        "total_gross_profit_usd": str(gross_profit),
        "sovereign_floor_breach_usd": payload.get("sovereign_floor_breach_usd"),
        "attack_sovereign_breach_usd": payload["attack_sovereign_breach_usd"],
        "mode_breakdown": {name: to_strings(g) for name, g in sorted(groups.items())},
        "loss_concentration": distribution,
        "top_10_drawdown_episodes": dd_episodes,
        "top_20_losses": [{"loss_usd": str(amount), "mode": t["mode"],
                           "multiplier": t["multiplier"],
                           "registered_stop_risk_usd": t["stop_risk_usd"],
                           "provider_cost_usd": t["provider_cost_usd"],
                           "realized_exit_at": t["realized_exit_at"]}
                          for amount, t in losers[:20]],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--target-dd", type=D, default=D("0.22"))
    args = ap.parse_args()
    assert D(0) < args.target_dd < D(1)
    raw = args.replay.read_bytes()
    result = audit(json.loads(raw), raw, args.target_dd)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print("CIBO_ALL_LOSS_AUDIT=" + json.dumps({
        "trades": result["decision_count"],
        "DD_pct": result["max_dd_pct"],
        "gross_loss_usd": result["total_gross_loss_usd"],
        "top20_loss_share_pct": result["loss_concentration"][4]["share_of_all_losses_pct"],
        "episodes_gt_22pct": sum(D(e["drawdown_pct"]) > D("22")
                               for e in result["top_10_drawdown_episodes"]),
        "sovereign_floor_breach_usd": result["sovereign_floor_breach_usd"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
