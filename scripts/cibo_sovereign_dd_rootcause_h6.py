#!/usr/bin/env python3
"""Independent EX-POST CIBO sovereign/DD forensic audit; NEVER an execution signal.

Input must be a pinned 3,368-entry full replay.  No dates, outcomes or trader
identities produced here may be used to select or reject Trader entries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

D = Decimal
ZERO = D(0)
TARGET_DD = D("0.25")


def decimal(row: dict, key: str) -> Decimal:
    return D(str(row[key]))


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def summarize(replay: dict, source: bytes) -> dict:
    trades = replay["trade_receipts"]
    snapshots = replay["epoch_receipts"]
    assert len(trades) == replay["trade_count"] == replay["decision_count"] == 3368
    assert replay["economic_group_report"]["all_entries_preserved"] is True
    # --summary-telemetry intentionally omits epoch receipts. The ledger
    # counters and full 3368 settlement receipts still permit a real audit.
    assert D(replay["attack_sovereign_breach_usd"]) == ZERO
    ledger = replay["economic_group_report"]["portfolio_loss_report"]
    losses = sum((-decimal(t, "realized_net_pnl_usd") for t in trades
                  if decimal(t, "realized_net_pnl_usd") < ZERO), ZERO)
    profits = sum((decimal(t, "realized_net_pnl_usd") for t in trades
                   if decimal(t, "realized_net_pnl_usd") > ZERO), ZERO)
    assert losses == decimal(ledger, "total_gross_loss_usd")
    assert profits == decimal(ledger, "total_gross_profit_usd")
    assert abs(decimal(replay, "initial_capital_usd") + profits - losses -
               decimal(replay, "ending_total_capital_usd")) <= D("0.00000001")
    assert len({t["signal_fingerprint"] for t in trades}) == 3368

    settlements = sorted(trades, key=lambda t: timestamp(t["realized_exit_at"]))
    snapshot_rows = sorted(snapshots, key=lambda e: timestamp(e["decision_at"]))
    sovereign_floor_violations = []
    first_floor_violation = None
    max_snapshot_breach = ZERO
    peak_equity_proxy = decimal(replay, "initial_capital_usd")
    open_risk_pressure = []
    ratio_max = ZERO
    for idx, e in enumerate(snapshot_rows):
        sovereign = decimal(e, "sovereign_bank_usd")
        floor = decimal(e, "sovereign_protection_floor_usd")
        portfolio = decimal(e, "portfolio_cushion_usd")
        open_risk = decimal(e, "open_stop_risk_usd")
        capital = sovereign + portfolio
        peak_equity_proxy = max(peak_equity_proxy, capital)
        floor_breach = max(ZERO, floor - sovereign)
        max_snapshot_breach = max(max_snapshot_breach, floor_breach)
        if floor_breach > ZERO:
            violation = {
                "epoch_index": e["epoch_index"],
                "decision_at": e["decision_at"],
                "sovereign_usd": str(sovereign),
                "sovereign_floor_usd": str(floor),
                "shortfall_usd": str(floor_breach),
                "portfolio_cushion_usd": str(portfolio),
                "open_stop_risk_usd": str(open_risk),
            }
            if first_floor_violation is None:
                first_floor_violation = violation
            sovereign_floor_violations.append(violation)
        # This is a *settlement-equity* proxy, not mark-to-market open PnL.
        # Declared stop risk is NOT a guaranteed maximum (gaps and costs).
        current_dd = peak_equity_proxy - capital
        pressure = current_dd + open_risk
        ratio = pressure / peak_equity_proxy if peak_equity_proxy > ZERO else ZERO
        ratio_max = max(ratio_max, ratio)
        if ratio > TARGET_DD:
            open_risk_pressure.append({
                "decision_at": e["decision_at"],
                "epoch_index": e["epoch_index"],
                "pressure_ratio": str(ratio),
                "equity_proxy_usd": str(capital),
                "peak_proxy_usd": str(peak_equity_proxy),
                "open_stop_risk_usd": str(open_risk),
                "settled_drawdown_usd": str(current_dd),
            })
    reported_breach = decimal(replay, "sovereign_floor_breach_usd")
    # mark() is called at settlements as well as after decision snapshots.
    # Snapshot shortfalls must be <= true recorded max; difference is coverage.
    assert reported_breach >= max_snapshot_breach - D("0.00000001")
    assert reported_breach > ZERO, "expected frozen em-s06745 breach"
    assert decimal(replay, "ending_sovereign_bank_usd") < ZERO
    medium_losses = decimal(replay, "medium_compound_negative_net_usd")
    medium_recovered = decimal(replay, "medium_compound_recovered_usd")
    medium_to_bank = decimal(replay, "medium_profit_to_sovereign_usd")
    bank_expected = (
        decimal(replay, "initial_capital_usd") - medium_losses
        + medium_recovered + medium_to_bank
        - decimal(replay, "attack_sovereign_breach_usd")
    )
    reported_bank = decimal(replay, "ending_sovereign_bank_usd")
    assert abs(bank_expected - reported_bank) <= D("0.00000001")
    reported_min_bank = decimal(replay, "minimum_sovereign_bank_usd")
    reported_floor = decimal(replay, "sovereign_protection_floor_usd")
    assert abs(max(ZERO, reported_floor-reported_min_bank)-reported_breach) <= D("0.00000001")

    # Approximate chronology from final settlements only: partial lifecycle
    # events may shift exact bank-change times, never turn a proxy into proof.
    proxy_bank = decimal(replay, "initial_capital_usd")
    proxy_deficit = ZERO
    proxy_low = proxy_bank
    proxy_first = None
    proxy_low_at = None
    for receipt in settlements:
        if receipt["mode"] != "MEDIUM":
            continue
        pnl = decimal(receipt, "realized_net_pnl_usd")
        if pnl < ZERO:
            proxy_bank += pnl
            proxy_deficit -= pnl
        elif pnl > ZERO:
            recovery = min(pnl, proxy_deficit)
            proxy_bank += recovery
            proxy_deficit -= recovery
        if proxy_first is None and proxy_bank < reported_floor:
            proxy_first = {
                "settled_at_proxy": receipt["realized_exit_at"],
                "bank_usd_proxy": str(proxy_bank),
                "unrecovered_deficit_usd_proxy": str(proxy_deficit),
                "caveat": "Final-exit ordering, not partial lifecycle event timeline.",
            }
        if proxy_bank < proxy_low:
            proxy_low = proxy_bank
            proxy_low_at = receipt["realized_exit_at"]
    assert abs(proxy_bank - reported_bank) <= D("0.00000001")

    def settled_window(start: str, end: str) -> dict:
        start_at, end_at = timestamp(start), timestamp(end)
        rows = [r for r in settlements
                if start_at < timestamp(r["realized_exit_at"]) <= end_at]
        out = {}
        for mode in ("ATTACK", "MEDIUM"):
            chosen = [r for r in rows if r["mode"] == mode]
            negative = sum((-decimal(r, "realized_net_pnl_usd") for r in chosen
                            if decimal(r, "realized_net_pnl_usd") < ZERO), ZERO)
            positive = sum((decimal(r, "realized_net_pnl_usd") for r in chosen
                            if decimal(r, "realized_net_pnl_usd") > ZERO), ZERO)
            out[mode] = {"settlements": len(chosen), "gross_loss_usd": str(negative),
                         "gross_profit_usd": str(positive), "net_usd": str(positive-negative)}
        return out

    episodes = []
    for ep in replay["drawdown_forensics"]["top_10_episodes"]:
        peak = decimal(ep, "peak_capital_usd")
        dd_loss = decimal(ep, "drawdown_usd")
        episodes.append({
            "rank": ep["rank"], "peak_at": ep["peak_at"], "trough_at": ep["trough_at"],
            "drawdown_pct": str(decimal(ep, "drawdown_fraction") * 100),
            "fixed_peak_gap_to_25pct_usd": str(max(ZERO, dd_loss - peak*TARGET_DD)),
            "fixed_peak_gap_to_20pct_usd": str(max(ZERO, dd_loss - peak*D("0.20"))),
            "settlements_by_mode": settled_window(ep["peak_at"], ep["trough_at"]),
        })
    breach_settlement_context = None
    if first_floor_violation is not None:
        hit = next(i for i, e in enumerate(snapshot_rows)
                   if e["epoch_index"] == first_floor_violation["epoch_index"])
        prior_at = (snapshot_rows[hit-1]["decision_at"] if hit else
                    replay["trade_receipts"][0]["decision_at"])
        breach_settlement_context = {
            "previous_epoch_at": prior_at,
            "first_breach_epoch_at": first_floor_violation["decision_at"],
            "settlements_between_epochs_by_mode": settled_window(
                prior_at, first_floor_violation["decision_at"]),
            "qualification": "Attribution window only; not a unique causal proof. "
                             "Settlement and decision events may share timestamps.",
        }
    return {
        "schema": "qore.cibo.sovereign-dd-rootcause.v1",
        "research_only": True,
        "uses_future_outcomes_for_decisions": False,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_case": "em-s06745",
        "trade_count": len(trades),
        "epoch_count": len(snapshot_rows),
        "epoch_snapshots_available": bool(snapshot_rows),
        "sovereign_ledger_reconciliation": {
            "initial_bank_usd": replay["initial_capital_usd"],
            "medium_debits_usd": str(medium_losses),
            "medium_recovery_credits_usd": str(medium_recovered),
            "medium_profit_allocated_to_bank_usd": str(medium_to_bank),
            "attack_bank_overflow_usd": replay["attack_sovereign_breach_usd"],
            "reconstructed_ending_bank_usd": str(bank_expected),
            "actual_ending_bank_usd": str(reported_bank),
            "unrecovered_medium_deficit_usd": replay["medium_compound_recovery_deficit_usd"],
            "reported_minimum_bank_usd": str(reported_min_bank),
            "reported_sovereign_floor_usd": str(reported_floor),
        },
        "proxy_first_breach_from_medium_final_settlements": proxy_first,
        "proxy_min_bank_usd": str(proxy_low),
        "proxy_min_bank_at": proxy_low_at,
        "capital_final_usd": replay["ending_total_capital_usd"],
        "max_drawdown_pct": str(decimal(replay, "max_drawdown_fraction")*100),
        "gross_loss_usd": str(losses),
        "gross_profit_usd": str(profits),
        "attack_sovereign_breach_usd": replay["attack_sovereign_breach_usd"],
        "sovereign_floor_breach_usd": str(reported_breach),
        "ending_sovereign_bank_usd": replay["ending_sovereign_bank_usd"],
        "snapshot_floor_breach_max_usd": str(max_snapshot_breach),
        "non_snapshot_breach_coverage_gap_usd": str(reported_breach-max_snapshot_breach),
        "floor_breached_epoch_count": len(sovereign_floor_violations),
        "first_floor_breach_snapshot": first_floor_violation,
        "first_floor_breach_settlement_context": breach_settlement_context,
        "worst_floor_breach_snapshots": sorted(
            sovereign_floor_violations,
            key=lambda x: D(x["shortfall_usd"]), reverse=True)[:12],
        "drawdown_episodes": episodes,
        "epochs_exceeding_25pct_equity_plus_declared_stop_risk_proxy":
            len(open_risk_pressure),
        "maximum_equity_plus_stop_risk_pressure_pct": str(ratio_max*100),
        "first_25pct_stress_epochs": open_risk_pressure[:15],
        "qualification": (
            "Recorded sovereign floor is a REAL observed-accounting breach until "
            "reconciled, not ATTACK-only leakage. Snapshot lower bound may differ "
            "from recorded maximum between epochs. Open-risk stress is not a "
            "guaranteed DD limit and must not be used as an oracle trade veto. "
            "Fixed-peak gap is a sensitivity calculation, not a replay."),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    raw = args.replay.read_bytes()
    report = summarize(json.loads(raw), raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print("CIBO_H6_SOVEREIGN_DD_ROOTCAUSE=" + json.dumps({
        key: report[key] for key in (
            "trade_count", "epoch_count", "max_drawdown_pct",
            "capital_final_usd", "sovereign_floor_breach_usd",
            "snapshot_floor_breach_max_usd", "non_snapshot_breach_coverage_gap_usd",
            "floor_breached_epoch_count",
            "epochs_exceeding_25pct_equity_plus_declared_stop_risk_proxy",
            "maximum_equity_plus_stop_risk_pressure_pct")},
        sort_keys=True))
    print("CIBO_H6_FIRST_BREACH=" + json.dumps(
        report["first_floor_breach_snapshot"], sort_keys=True))
    print("CIBO_H6_FIRST_BREACH_CONTEXT=" + json.dumps(
        report["first_floor_breach_settlement_context"], sort_keys=True))
    print("CIBO_H6_MEDIUM_LEDGER=" + json.dumps(
        report["sovereign_ledger_reconciliation"], sort_keys=True))
    print("CIBO_H6_FIRST_BREACH_PROXY=" + json.dumps(
        report["proxy_first_breach_from_medium_final_settlements"], sort_keys=True))


if __name__ == "__main__":
    main()
