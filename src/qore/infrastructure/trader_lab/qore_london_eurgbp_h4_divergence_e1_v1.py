"""E1 London: paired EURGBP state interaction and causal H4 confounding audit.

Uses frozen issue775 price outcomes. Does not change trajectories, labels,
stops, trading, or the TTrades author method. This is exploratory.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar as M1, iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END, DEV_WINDOW_START,
)

SYMBOLS = ("EURUSD", "GBPUSD")
STATES = ("RECLAIM_INSIDE", "ACCEPTED_OUTSIDE")
REGIMES = ("H4_ALIGNED_WITH_RAID", "H4_OPPOSED_TO_RAID")
ID = "QORE_LONDON_ISSUE775_E1_PAIR_DATE_BLOCK_H4_V1"
SEED = 77520261012
BLOCK_DAYS = 5
BOOTSTRAP_N = 2000


def source_rows(folder: Path) -> list[dict[str, Any]]:
    paths = sorted(folder.rglob("london-asia-postraid-*-daily-paths.jsonl"))
    if len(paths) not in (1, 2):
        raise ValueError(f"expected 1 or 2 frozen ledger file(s): {len(paths)}")
    rows = [json.loads(line) for p in paths for line in p.read_text().splitlines() if line.strip()]
    if len(rows) != len({(r["symbol"], r["ny_day"]) for r in rows}):
        raise ValueError("frozen source has duplicate symbol/date")
    if not {r["symbol"] for r in rows}.issubset(set(SYMBOLS)):
        raise ValueError("source contains markets other than EURUSD and GBPUSD")
    return rows


def h4_prior(
    minute_bars: dict[datetime, M1], raid_at: datetime, side: str,
) -> dict[str, Any]:
    if raid_at.tzinfo is None or side not in ("HIGH", "LOW"):
        raise ValueError("UTC-aware raid and HIGH/LOW required")
    instant = raid_at.astimezone(UTC)
    # End of latest strictly completed H4 UTC block.
    latest_end = instant.replace(hour=(instant.hour // 4) * 4,
                                 minute=0, second=0, microsecond=0)
    if latest_end > instant:
        raise AssertionError("H4 from the future")
    start = latest_end - timedelta(hours=12)
    observed: list[M1] = []
    for k in range(720):
        t = start + timedelta(minutes=k)
        b = minute_bars.get(t)
        if b is None:
            return {"status": "H4_UNKNOWN_GAP", "latest_completed_h4_end": latest_end.isoformat(),
                    "missing_m1_at": t.isoformat(), "observed_before_gap": k}
        if b.closed_at != t + timedelta(minutes=1):
            return {"status": "H4_UNKNOWN_INVALID_DURATION", "m1_at": t.isoformat()}
        if b.closed_at > latest_end or b.closed_at > instant:
            raise AssertionError("H4 lookahead")
        observed.append(b)
    h4_closes = [observed[239].close, observed[479].close, observed[719].close]
    change = h4_closes[2] - h4_closes[0]
    if change == 0:
        regime = "H4_FLAT"
    else:
        raid_sign = 1 if side == "HIGH" else -1
        regime = (
            REGIMES[0] if (change > 0 and raid_sign == 1) or
                          (change < 0 and raid_sign == -1)
            else REGIMES[1]
        )
    return {
        "status": regime,
        "latest_completed_h4_end": latest_end.isoformat(),
        "oldest_h4_start": start.isoformat(),
        "h4_three_closes": [str(x) for x in h4_closes],
        "H4_close_3_minus_H4_close_1": str(change),
        "h4_m1_count": 720,
        "last_observed_m1_closed_at": observed[-1].closed_at.isoformat(),
    }


def classify_market(native: Path, frozen: Path, output: Path) -> dict[str, Any]:
    ledger = source_rows(frozen)
    symbols = {r["symbol"] for r in ledger}
    if len(symbols) != 1:
        raise ValueError("per market exactly one frozen ledger")
    symbol = next(iter(symbols))
    if len(ledger) != 261:
        raise ValueError("must reproduce frozen 261 NY days")
    valid = [r for r in ledger if r["status"] == "CHECKPOINT_VALID"]
    if len(valid) != (227 if symbol == "EURUSD" else 231):
        raise ValueError("frozen source original checkpoint mismatch")
    expected = (
        {"RECLAIM_INSIDE": (94, 38), "ACCEPTED_OUTSIDE": (115, 40)}
        if symbol == "EURUSD" else
        {"RECLAIM_INSIDE": (92, 22), "ACCEPTED_OUTSIDE": (123, 50)}
    )
    for state, (n, reversal) in expected.items():
        cells = [r for r in valid if r["checkpoint_state"] == state]
        if len(cells) != n or sum(r["terminal_60"] == "REVERSAL" for r in cells) != reversal:
            raise ValueError("original outcomes changed: DO NOT RECLASSIFY")
    cache: dict[datetime, M1] = {}
    for bar in iter_cibo_m1(native):
        if not (DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END):
            continue
        if bar.symbol != symbol:
            raise ValueError("native source symbol mismatch")
        if bar.opened_at in cache:
            raise ValueError("duplicate native M1")
        cache[bar.opened_at] = bar
    if len(cache) < 300_000:
        raise ValueError("inadequate native M1 coverage")
    output_rows: list[dict[str, Any]] = []
    for row in ledger:
        evidence: dict[str, Any]
        if row["raid_at"] is None or row["raid_side"] is None:
            evidence = {"status": "H4_NOT_APPLICABLE_NO_RAID"}
        else:
            raid = datetime.fromisoformat(row["raid_at"])
            evidence = h4_prior(cache, raid, row["raid_side"])
        output_rows.append({
            "symbol": symbol, "ny_day": row["ny_day"],
            "source_status": row["status"], "raid_at": row["raid_at"],
            "raid_side": row["raid_side"], "checkpoint_at": row["checkpoint_at"],
            "checkpoint_state": row["checkpoint_state"], "terminal_60": row["terminal_60"],
            "h4_prior": evidence,
            "original_states_and_outcomes_unchanged": True,
        })
    output.mkdir(parents=True, exist_ok=True)
    (output / f"issue775-E1-{symbol}-frozen-joined-h4.jsonl").write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in output_rows),
        encoding="utf-8",
    )
    summary = {
        "identity": ID, "symbol": symbol, "source_days": len(ledger),
        "checkpoint_valid": len(valid), "M1_native_count": len(cache),
        "h4_status_counts": dict(Counter(
            r["h4_prior"]["status"] for r in output_rows
            if r["source_status"] == "CHECKPOINT_VALID"
        )),
        "no_new_economic_signal": True,
    }
    (output / f"issue775-E1-{symbol}-h4-source-report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8",
    )
    return summary


def rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    c = Counter(r["terminal_60"] for r in rows)
    return {
        "N": n, "reversal": c["REVERSAL"], "continuation": c["CONTINUATION"],
        "neutral": c["NEUTRAL"], "censored": c["CENSORED"],
        "p_reversal": c["REVERSAL"] / n if n else None,
    }


def interaction(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    cells = {
        (symbol, state): rates([
            r for r in rows
            if r["symbol"] == symbol and r["checkpoint_state"] == state
            and r["source_status"] == "CHECKPOINT_VALID" and r["terminal_60"] != "CENSORED"
        ])
        for symbol in SYMBOLS for state in STATES
    }
    if any(z["N"] == 0 for z in cells.values()):
        return None
    D = {
        symbol: cells[(symbol, STATES[0])]["p_reversal"] -
                cells[(symbol, STATES[1])]["p_reversal"]
        for symbol in SYMBOLS
    }
    return {
        "by_symbol": D,
        "effect_interaction_EUR_minus_GBP": D["EURUSD"]-D["GBPUSD"],
        "simple_reclaim_rate_EUR_minus_GBP": cells[("EURUSD", STATES[0])]["p_reversal"] -
                cells[("GBPUSD", STATES[0])]["p_reversal"],
        "cells": {f"{symbol}|{state}":cells[(symbol, state)]
                  for symbol in SYMBOLS for state in STATES},
    }


def eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r["source_status"] == "CHECKPOINT_VALID"
            and r["checkpoint_state"] in STATES and r["terminal_60"] != "CENSORED"
            and r["h4_prior"]["status"] in REGIMES]


def standardized_interaction(
    rows: list[dict[str, Any]], eligible_regimes: tuple[str, ...],
    weights: dict[str, float], min_cell: int = 1,
) -> dict[str, Any] | None:
    cells = {}
    for reg in eligible_regimes:
        for sym in SYMBOLS:
            for state in STATES:
                sub = [r for r in rows if r["h4_prior"]["status"] == reg
                       and r["symbol"] == sym and r["checkpoint_state"] == state
                       and r["source_status"] == "CHECKPOINT_VALID"]
                if len(sub) < min_cell:
                    return None
                cells[(reg, sym, state)] = rates(sub)
    diffs = {}
    for sym in SYMBOLS:
        d = sum(weights[reg] * (
            cells[(reg,sym,STATES[0])]["p_reversal"] -
            cells[(reg,sym,STATES[1])]["p_reversal"]
        ) for reg in eligible_regimes)
        diffs[sym] = d
    return {
        "per_symbol": diffs,
        "interaction_EUR_minus_GBP": diffs["EURUSD"] - diffs["GBPUSD"],
    }


def common_regimes(rows: list[dict[str, Any]], minimum: int = 10
                  ) -> tuple[tuple[str, ...], dict[str, float], dict[str, Any]]:
    supported: list[str] = []
    counts: dict[str, Any] = {}
    for regime in REGIMES:
        cells = {
            f"{sym}|{state}": sum(
                r["source_status"] == "CHECKPOINT_VALID"
                and r["symbol"] == sym and r["checkpoint_state"] == state
                and r["h4_prior"]["status"] == regime
                and r["terminal_60"] != "CENSORED"
                for r in rows
            )
            for sym in SYMBOLS for state in STATES
        }
        counts[regime] = cells
        if all(n >= minimum for n in cells.values()):
            supported.append(regime)
    total = sum(sum(counts[reg].values()) for reg in supported)
    weights = {
        reg: sum(counts[reg].values()) / total
        for reg in supported
    } if total else {}
    return tuple(supported), weights, counts


def draw_date_blocks(rows: list[dict[str, Any]], days: list[str], rng: random.Random,
                     block: int = BLOCK_DAYS) -> list[dict[str, Any]]:
    """Sample 5 ordered common NY dates circularly, bringing BOTH symbols."""
    if not days:
        raise ValueError("no dates")
    day_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        day_rows[r["ny_day"]].append(r)
    sampled: list[dict[str, Any]] = []
    count = 0
    while count < len(days):
        start = rng.randrange(len(days))
        for step in range(min(block, len(days)-count)):
            sampled.extend(day_rows[days[(start+step) % len(days)]])
            count += 1
    return sampled


def percentile(arr: list[float], q: float) -> float | None:
    if not arr:
        return None
    values = sorted(arr)
    ix = (len(values)-1)*q
    floor = int(ix)
    a = ix - floor
    return values[floor]*(1-a)+values[min(floor+1,len(values)-1)]*a


def bootstrap(
    rows: list[dict[str, Any]], eligible_regimes: tuple[str, ...],
    weights: dict[str, float],
) -> dict[str, Any]:
    dates = sorted({r["ny_day"] for r in rows})
    rng = random.Random(SEED)
    raw: list[float] = []
    reclaim: list[float] = []
    h4_raw: list[float] = []
    adjusted: list[float] = []
    for _ in range(BOOTSTRAP_N):
        draw = draw_date_blocks(rows, dates, rng)
        original = interaction(draw)
        if original:
            raw.append(original["effect_interaction_EUR_minus_GBP"])
            reclaim.append(original["simple_reclaim_rate_EUR_minus_GBP"])
        h4_sub = [r for r in eligible_rows(draw)
                  if r["h4_prior"]["status"] in eligible_regimes]
        if h4_sub:
            h4_same = interaction(h4_sub)
            if h4_same:
                h4_raw.append(h4_same["effect_interaction_EUR_minus_GBP"])
            adj = standardized_interaction(h4_sub, eligible_regimes, weights)
            if adj:
                adjusted.append(adj["interaction_EUR_minus_GBP"])
    def info(values: list[float]) -> dict[str, Any]:
        return {
            "n_valid": len(values),
            "CI95": [percentile(values, .025), percentile(values, .975)],
            "p_bootstrap_nonpositive_descriptive": (
                sum(v<=0 for v in values)/len(values) if values else None
            ),
        }
    return {
        "block": "5 distinct NY date index blocks, circular, both pairs share dates",
        "seed": SEED, "replications_requested": BOOTSTRAP_N,
        "raw_interaction": info(raw),
        "reclaim_between_pairs": info(reclaim),
        "h4_subsample_unadjusted_interaction": info(h4_raw),
        "h4_standardized_interaction": info(adjusted),
        "exploratory_nonconfirmatory": True,
    }


def report(root: Path, output: Path) -> dict[str, Any]:
    files = sorted(root.rglob("issue775-E1-*-frozen-joined-h4.jsonl"))
    if len(files) != 2:
        raise ValueError(f"require EXACTLY 2 native frozen joined ledgers: {len(files)}")
    rows = [json.loads(line) for path in files for line in path.read_text().splitlines()
            if line.strip()]
    if len(rows) != 522 or len({(r["symbol"],r["ny_day"]) for r in rows})!=522:
        raise ValueError("original 522 individual NY-day ledger rows changed")
    if {r["symbol"] for r in rows} != set(SYMBOLS):
        raise ValueError("missing EURUSD or GBPUSD")
    expected = {
        "EURUSD": {"CHECKPOINT_VALID":227, "RECLAIM_INSIDE":(94,38),
                   "ACCEPTED_OUTSIDE":(115,40)},
        "GBPUSD": {"CHECKPOINT_VALID":231, "RECLAIM_INSIDE":(92,22),
                   "ACCEPTED_OUTSIDE":(123,50)},
    }
    for symbol in SYMBOLS:
        current=[r for r in rows if r["symbol"]==symbol]
        for state in STATES:
            cells=[r for r in current if r["checkpoint_state"]==state]
            n,rev=expected[symbol][state]
            if len(cells)!=n or sum(r["terminal_60"]=="REVERSAL" for r in cells)!=rev:
                raise ValueError("source outcomes modified; FAIL CLOSED")
        if sum(r["source_status"]=="CHECKPOINT_VALID" for r in current)!=expected[symbol]["CHECKPOINT_VALID"]:
            raise ValueError("source original checkpoints modified")
    original=interaction(rows)
    if not original:
        raise ValueError("original overlap missing")
    eligible=eligible_rows(rows)
    regimes,weights,coverage=common_regimes(rows)
    h4_sub=[r for r in eligible if r["h4_prior"]["status"] in regimes]
    in_sub=interaction(h4_sub) if h4_sub else None
    adjusted=standardized_interaction(h4_sub,regimes,weights,min_cell=10) if regimes else None
    h4_counts = {
        sym: {
            regime: {
                state:rates([r for r in rows if r["symbol"]==sym
                            and r["checkpoint_state"]==state
                            and r["h4_prior"]["status"]==regime])
                for state in STATES
            } for regime in (*REGIMES,"H4_FLAT","H4_UNKNOWN_GAP",
                             "H4_UNKNOWN_INVALID_DURATION",
                             "H4_UNKNOWN_LOOKBACK")
        }
        for sym in SYMBOLS
    }
    out={
        "identity": ID,
        "preregistered_raw_effect": "difference of R-A reversal-probability differences EUR-GBP",
        "source_days_total":len(rows),
        "original_interaction":original,
        "H4_prior": {
            "definition":"3 contiguous fully-closed 4h UTC bars, compare third close-first close",
            "coverage_by_symbol_regime_state":h4_counts,
            "common_regime_counts":coverage,
            "regimes_supported_min10_all4cells":list(regimes),
            "common_weights_fixed_before_bootstrap":weights,
            "h4_eligible_n":len(eligible),
            "h4_analysis_n":len(h4_sub),
            "interaction_on_H4_subsample_unadjusted":in_sub,
            "interaction_H4_standardized":adjusted,
            "difference_interaction_absolute_reduction_fraction":(
                1-abs(adjusted["interaction_EUR_minus_GBP"])/
                abs(in_sub["effect_interaction_EUR_minus_GBP"])
                if adjusted and in_sub
                and in_sub["effect_interaction_EUR_minus_GBP"]!=0 else None
            ),
        },
        "date_block_bootstrap":bootstrap(rows,regimes,weights),
        "no_SMT_in_this_gate": True,
        "no_TTrades_author_H4_confirmation": True,
        "history_reused_no_independent_OOS": True,
        "no_new_trader_or_PF": True,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"qore-london-issue775-E1-eurgbp-H4-divergence-results.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print("E1_LONDON_H4_INTERACTION",json.dumps(out,sort_keys=True))
    return out


def main() -> None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("native",type=Path)
    m.add_argument("frozen",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("aggregate")
    a.add_argument("markets",type=Path)
    a.add_argument("output",type=Path)
    x=p.parse_args()
    if x.mode=="market":
        print("E1_LONDON_H4_MARKET",json.dumps(classify_market(x.native,x.frozen,x.output),sort_keys=True))
    else:
        report(x.markets,x.output)


if __name__=="__main__":
    main()
