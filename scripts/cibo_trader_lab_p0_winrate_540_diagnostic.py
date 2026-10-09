#!/usr/bin/env python3
"""P0 scientific PAPER diagnostic for the exact 540 financed M5 opportunities.

FROZEN COHORT: DO NOT change admission, signal IDs, volume, entry, source or
close fees in counterfactuals. ATR14 uses ONLY 15 previously closed consecutive
M5 bars. OHLC intrabar ordering unknown => STOP FIRST. NO LIVE / MT5 evidence.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
import json
import statistics

from cibo_trader_lab_native_qdle_market_atlas_3368 import (
    SCREENSHOT_SPREAD, SYMBOL_ALIAS, price_usd_per_unit,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import load_raw_m5

ZERO = D("0")
SL_GRID = (D("0.5"), D("1.0"), D("1.5"))
TP_GRID = (D("1"), D("2"), D("3"))
MAX_BARS = 3200
MAX_DAYS = 14


def signed_move(price: D, entry: D, buy: bool) -> D:
    return price - entry if buy else entry - price


def atr14_before(bars, pos: int):
    """No ATR computation may access entry/current/future M5 candles."""
    if pos < 15:
        return None
    prior = bars[pos - 15:pos]
    if prior[-1].closed_at != bars[pos].opened_at:
        return None
    if any(x.closed_at != y.opened_at for x, y in zip(prior, prior[1:])):
        return None
    ranges = []
    for prev, bar in zip(prior[:-1], prior[1:]):
        ranges.append(max(bar.high - bar.low,
                          abs(bar.high - prev.close),
                          abs(bar.low - prev.close)))
    return sum(ranges, ZERO) / D(14)


def contiguous_path(bars, pos, *, max_bars=MAX_BARS):
    """Only actual successive M5 bars; never cross a historical data gap."""
    start = bars[pos].opened_at
    result = []
    for bar in bars[pos:pos + max_bars]:
        if bar.opened_at >= start + timedelta(days=MAX_DAYS):
            break
        if result and result[-1].closed_at != bar.opened_at:
            break
        result.append(bar)
    return result


def fixed_exit(path, *, entry: D, stop: D, target: D, side: str,
               spread: D, lots: D, per_unit: D, open_fee: D):
    """A: no trailing/partial/defensive. STOP first if both inside one M5 bar."""
    if side not in ("BUY", "SELL"):
        raise ValueError("invalid side")
    buy = side == "BUY"
    if ((buy and not (ZERO < stop < entry < target))
            or (not buy and not (ZERO < target < entry < stop))):
        return {"status": "INVALID_CROSS_SIDE_GEOMETRY"}
    half = spread / D(2)
    for i, bar in enumerate(path):
        side_open = bar.open - half if buy else bar.open + half
        favorable = bar.high - half if buy else bar.low + half
        adverse = bar.low - half if buy else bar.high + half
        stop_open = signed_move(side_open, stop, buy) <= ZERO
        target_open = signed_move(side_open, target, buy) >= ZERO
        if stop_open:
            exit_price, reason, at = side_open, "GAP_STOP", bar.opened_at
        elif target_open:
            exit_price, reason, at = target, "GAP_TARGET", bar.opened_at
        else:
            stop_hit = signed_move(adverse, stop, buy) <= ZERO
            tp_hit = signed_move(favorable, target, buy) >= ZERO
            if stop_hit:
                exit_price, reason, at = stop, "STOP", bar.closed_at
            elif tp_hit:
                exit_price, reason, at = target, "TARGET", bar.closed_at
            else:
                continue
        gross = signed_move(exit_price, entry, buy) * per_unit * lots
        return {
            "status": "SETTLED", "exit_reason": reason,
            "exit_bar_index": i, "exit_at": at.isoformat(),
            "exit_price": str(exit_price), "gross_usd": str(gross),
            "net_usd": str(gross - open_fee),
            "same_bar_sl_tp_ambiguous": (
                not stop_open and not target_open
                and signed_move(adverse, stop, buy) <= ZERO
                and signed_move(favorable, target, buy) >= ZERO
            ),
        }
    return {"status": "NO_CONTIGUOUS_TERMINAL_PATH"}


def pre_exit_extremes(path, *, exit_at: datetime | None, entry: D,
                      target: D, side: str, spread: D):
    """Conservative COMPLETED-bars-only extrema strictly before managed exit.

    Exit bar is excluded, so unknown OHLC ordering cannot inflate MFE/MAE
    while claiming those movements occurred before an exit.
    """
    if exit_at is None:
        return {"status": "CENSORED_NO_MANAGED_EXIT"}
    buy = side == "BUY"
    half = spread / D(2)
    movements = []
    for bar in path:
        if not bar.closed_at < exit_at:
            break
        favorable = bar.high-half if buy else bar.low+half
        adverse = bar.low-half if buy else bar.high+half
        movements.append((signed_move(favorable, entry, buy),
                          signed_move(adverse, entry, buy)))
    if not movements:
        return {"status": "NO_COMPLETE_BAR_STRICTLY_BEFORE_EXIT",
                "completed_bars": 0}
    mfe = max(x[0] for x in movements)
    mae = min(x[1] for x in movements)
    target_distance = signed_move(target, entry, buy)
    return {
        "status": "STRICT_PRE_EXIT_COMPLETED_BARS",
        "completed_bars": len(movements),
        "mfe_price_units": str(mfe),
        "mae_price_units": str(mae),
        "mfe_to_original_target_fraction": str(mfe / target_distance),
        "hit_half_original_tp_before_exit_bar": mfe >= target_distance / D(2),
    }


def post_stop_tp_hindsight(path, first_exit: dict, *, entry: D, original_target: D,
                           side: str, spread: D, hours=24):
    """Diagnostic only. Future after a stop is NEVER a usable trade decision."""
    if first_exit.get("exit_reason") not in ("STOP", "GAP_STOP"):
        return {"status": "NO_INITIAL_STOP"}
    i = first_exit["exit_bar_index"]
    stop_at = datetime.fromisoformat(first_exit["exit_at"])
    buy = side == "BUY"
    half = spread / D(2)
    end = stop_at + timedelta(hours=hours)
    observed = 0
    for bar in path[i+1:]:
        if bar.opened_at >= end:
            break
        observed += 1
        favorable = bar.high-half if buy else bar.low+half
        if signed_move(favorable, original_target, buy) >= ZERO:
            return {"status": "TP_AFTER_STOP_HINDSIGHT_ONLY",
                    "bars_observed_after_stop": observed,
                    "first_touch_at_or_before": bar.closed_at.isoformat()}
    fully_observed = bool(path and path[-1].closed_at >= end)
    return {"status": ("NO_TP_WITHIN_24H" if fully_observed
                       else "AFTER_STOP_24H_PATH_CENSORED"),
            "bars_observed_after_stop": observed}


def metrics(trades):
    values = [D(row["net_usd"]) for row in trades]
    wins = [x for x in values if x > ZERO]
    losses = [-x for x in values if x < ZERO]
    gain = sum(wins, ZERO)
    loss = sum(losses, ZERO)
    return {
        "settled": len(values), "wins": len(wins), "losses": len(losses),
        "flats": len(values)-len(wins)-len(losses),
        "win_rate_pct": str(D(100)*D(len(wins))/D(len(values))) if values else None,
        "gross_wins_usd": str(gain), "gross_losses_usd": str(loss),
        "pnl_usd": str(gain - loss),
        "net_pf": str(gain/loss) if loss else None,
        "expectancy_usd_per_trade": str((gain-loss)/D(len(values))) if values else None,
    }


def run(manifest, scenario, roots, *, max_bars=MAX_BARS):
    sources = {x["signal_fingerprint"]: x["trader_opportunity"]
               for x in manifest["opportunities"]}
    decisions = {x["signal_fingerprint"]: x for x in scenario["signal_decisions"]}
    opens = [x for x in decisions.values()
             if x.get("status") in ("PAPER_OPEN", "PAPER_OPEN_UNRESOLVED_NO_EXIT_PATH")]
    closed = {x["signal_fingerprint"]: x for x in scenario["closed_trades"]}
    if (scenario["signal_count"] != 3368 or len(opens) != 540
            or len(closed) != 538 or len(set(sources)) != 3368
            or any(x["signal_fingerprint"] not in sources for x in opens)):
        raise ValueError("unexpected source identity or change to frozen 540 cohort")
    atlas = {}
    for sym in SCREENSHOT_SPREAD:
        corpus, _ = load_raw_m5(roots[sym])
        if corpus.symbol != SYMBOL_ALIAS.get(sym, sym):
            raise ValueError("Atlas symbol mismatch")
        atlas[sym] = (corpus.bars, tuple(b.opened_at for b in corpus.bars))
    rows = []
    variants = ("A_ECONOMIC_STOP_TP_ORIGINAL", "A_STRUCTURAL_STOP_TP_ORIGINAL",
                *(f"SL_{k}ATR_TP_ORIGINAL" for k in ("0.5", "1.0", "1.5")),
                *(f"SL_ECONOMIC_TP_{k}ATR" for k in ("1", "2", "3")))
    for rec in sorted(opens, key=lambda o: (o["paper_entry_at"], o["signal_fingerprint"])):
        sid = rec["signal_fingerprint"]
        orig = sources[sid]
        sym = rec["symbol"]
        buy = orig["side"] == "long"
        side = "BUY" if buy else "SELL"
        bars, times = atlas[sym]
        entered_at = datetime.fromisoformat(rec["paper_entry_at"])
        pos = bisect_left(times, entered_at)
        if pos >= len(bars) or bars[pos].opened_at != entered_at:
            raise ValueError("PAPER fill timestamp lacks matching causal Atlas bar")
        path = contiguous_path(bars, pos, max_bars=max_bars)
        if not path:
            raise ValueError("missing first contiguous M5 bar")
        entry = D(rec["paper_entry_price"])
        original_entry = D(orig["intended_entry"])
        orig_stop_dist = abs(original_entry - D(orig["stop_loss"]))
        # The economic stop was calculated by CIBO before QDLE, but its
        # proposed absolute price is only retained in the 3368 native quote input.
        # It must be provided by the caller via source decision map.
        native = scenario.get("_native_decisions", {}).get(sid)
        if native is None:
            raise ValueError("native decision/geometry input not attached")
        econ_stop_dist = abs(original_entry - D(native["cibo_manager_stop_proposed"]))
        tp_dist = abs(original_entry - D(orig["take_profit"]))
        mid = bars[pos].open
        sign = D(1) if buy else D(-1)
        original_stop = mid - sign * orig_stop_dist
        economic_stop = mid - sign * econ_stop_dist
        original_tp = mid + sign * tp_dist
        half = SCREENSHOT_SPREAD[sym] / D(2)
        if not ((buy and original_stop <= economic_stop < entry < original_tp)
                or (not buy and original_tp < entry < economic_stop <= original_stop)):
            raise ValueError("frozen PAPER geometry drift")
        lot = D(rec["qdle_lots"])
        open_fee = D(rec["paper_open_fee_usd"])
        per_unit = price_usd_per_unit(sym)
        atr = atr14_before(bars, pos)
        arms = {
            "A_ECONOMIC_STOP_TP_ORIGINAL": (economic_stop, original_tp),
            "A_STRUCTURAL_STOP_TP_ORIGINAL": (original_stop, original_tp),
        }
        if atr is not None:
            for factor in SL_GRID:
                arms["SL_"+str(factor)+"ATR_TP_ORIGINAL"] = (entry-sign*factor*atr,
                                                           original_tp)
            for factor in TP_GRID:
                arms["SL_ECONOMIC_TP_"+str(factor)+"ATR"] = (economic_stop,
                                                           entry+sign*factor*atr)
        outcomes = {}
        for arm, (stop, target) in arms.items():
            result = fixed_exit(path, entry=entry, stop=stop, target=target,
                                side=side, spread=SCREENSHOT_SPREAD[sym],
                                lots=lot, per_unit=per_unit, open_fee=open_fee)
            risk = abs(entry-stop)*per_unit*lot+open_fee
            risk_budget = min(D(rec["economic_desired_risk_usd"]),
                              D(rec["bank_at_entry"])*D("0.05"))
            result["counterfactual_frozen_lots_only"] = True
            result["risk_under_original_qdle_request"] = risk <= risk_budget
            result["stop_all_in_risk_usd"] = str(risk)
            result["risk_budget_usd"] = str(risk_budget)
            outcomes[arm] = result
        managed = closed.get(sid)
        native_exit_time = (datetime.fromisoformat(managed["exit_at"])
                            if managed else None)
        strict = pre_exit_extremes(path, exit_at=native_exit_time, entry=entry,
                                  target=original_tp, side=side,
                                  spread=SCREENSHOT_SPREAD[sym])
        fx = outcomes["A_ECONOMIC_STOP_TP_ORIGINAL"]
        hindsight = post_stop_tp_hindsight(
            path, fx, entry=entry, original_target=original_tp,
            side=side, spread=SCREENSHOT_SPREAD[sym])
        rows.append({
            "signal_fingerprint": sid, "symbol": sym, "mode": rec["mode"],
            "trader": native.get("trader", ""),
            "entry_at": entered_at.isoformat(),
            "year": entered_at.year, "side": side, "entry_price": str(entry),
            "original_structural_stop": str(original_stop),
            "initial_economic_stop": str(economic_stop),
            "original_tp": str(original_tp),
            "atr14_pre_entry": str(atr) if atr is not None else None,
            "lot": str(lot), "fee_open_usd": str(open_fee),
            "managed_status": "SETTLED" if managed else "CENSORED_NO_EXIT",
            "managed_net_usd": managed["net_usd"] if managed else None,
            "managed_exit_reason": managed["exit_reason"] if managed else None,
            "managed_life_minutes": (
                str((native_exit_time-entered_at).total_seconds()/60)
                if managed else None),
            "strict_pre_exit_extremes": strict,
            "original_stop_then_tp_hindsight": hindsight,
            "price_path_m5_bars": len(path),
            "fixed_variants": outcomes,
            "real_bidask_verified": False,
            "full_cognitive_native_authority_verified": False,
        })
    if len(rows) != 540:
        raise ValueError("cohort cardinality drift")
    def paired(arm):
        return [r for r in rows if r["managed_status"] == "SETTLED"
                and r["fixed_variants"].get(arm, {}).get("status") == "SETTLED"]
    summary = {}
    for arm in variants:
        paired_rows = paired(arm)
        summary[arm] = {
            "paired_with_managed": len(paired_rows),
            "fixed": metrics([r["fixed_variants"][arm] for r in paired_rows]),
            "managed_on_identical_subset": metrics([
                {"net_usd": r["managed_net_usd"]} for r in paired_rows]),
            "risk_compatible_with_original_request": sum(
                r["fixed_variants"][arm]["risk_under_original_qdle_request"]
                for r in paired_rows),
            "incomplete_vs_540": sum(
                r["fixed_variants"].get(arm, {}).get("status") != "SETTLED"
                for r in rows),
        }
    durations = {}
    for pnl in ("WIN", "LOSS", "FLAT"):
        minutes = [
            D(r["managed_life_minutes"]) for r in rows
            if r["managed_status"] == "SETTLED"
            and (("WIN" if D(r["managed_net_usd"]) > ZERO
                  else "LOSS" if D(r["managed_net_usd"]) < ZERO
                  else "FLAT") == pnl)
        ]
        durations[pnl] = {"count": len(minutes),
                          "average_min": str(sum(minutes, ZERO)/D(len(minutes))) if minutes else None,
                          "median_min": str(statistics.median(minutes)) if minutes else None}
    maemfe = [
        r["strict_pre_exit_extremes"] for r in rows
        if r["strict_pre_exit_extremes"]["status"] == "STRICT_PRE_EXIT_COMPLETED_BARS"]
    return {
        "schema": "qore.trader-lab.p0-winrate-diagnostic-fixed-540.v1",
        "research_only": True, "certified": False, "broker_fills": 0,
        "source_signals": 3368, "frozen_paper_openings": 540,
        "managed_settled": len(closed),
        "managed_summary": metrics(list(closed.values())),
        "fixed_counterfactual_pairs": summary,
        "strict_pre_exit_extremes_measurable": len(maemfe),
        "strict_pre_exit_half_tp_hits": sum(
            bool(x["hit_half_original_tp_before_exit_bar"]) for x in maemfe),
        "atr14_available": sum(r["atr14_pre_entry"] is not None for r in rows),
        "stop_then_tp_hindsight_only_counts": dict(Counter(
            r["original_stop_then_tp_hindsight"]["status"] for r in rows)),
        "managed_winner_loser_durations": durations,
        "rows": rows,
        "limitations": [
            "Synthetic bid/ask fixed October 2026 spread, not historical broker bid/ask",
            "Stop-first M5 intrabar ambiguity; extrema exclude terminal bar",
            "Post-stop TP is hindsight, not realized trading profit",
            "Fixed cohort retains original lots; alternate SL needs fresh QDLE physical resizing",
            "Counterfactuals selected on same cohort are exploratory, never OOS proof",
            "No direct H1/H4 signal reconstruction or authenticated broker spread",
            "No genuine fresh Native MAX cognition or live MT5 fills",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--native-stellar-qdle", type=Path, required=True)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--atlas-root", action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    roots = {}
    for row in a.atlas_root:
        sym, separator, path = row.partition("=")
        if not separator or sym in roots:
            p.error("unique SYMBOL=ROOT required")
        roots[sym] = Path(path)
    if set(roots) != set(SCREENSHOT_SPREAD):
        p.error("exact six Atlas symbols required")
    source = json.loads(a.manifest.read_text())
    quotes = json.loads(a.native_stellar_qdle.read_text())
    replay = json.loads(a.replay.read_text())
    native = {x["signal_fingerprint"]: x for x in quotes["decisions"]}
    replay["_native_decisions"] = native
    report = run(source, replay, roots)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("CIBO_P0_WINRATE_DIAGNOSTIC_540", json.dumps({
        k:report[k] for k in ("frozen_paper_openings","managed_settled",
                              "atr14_available","strict_pre_exit_extremes_measurable",
                              "strict_pre_exit_half_tp_hits",
                              "stop_then_tp_hindsight_only_counts",
                              "fixed_counterfactual_pairs",
                              "managed_winner_loser_durations")
    },sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
