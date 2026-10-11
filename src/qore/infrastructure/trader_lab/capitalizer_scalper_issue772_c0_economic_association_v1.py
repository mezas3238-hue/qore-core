"""Exploratory E0 association: C0 source-only integrity joined to frozen V49 PnL.

Do NOT mistake associations with market/clock/provider for causal damage or a
tradeable filter. Zero signal/selection changes, no physical BID/ASK claim.
The preregistered source-only MAX3 is the only selection authority.
"""
from __future__ import annotations

import argparse
import bisect
import json
import random
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_START, DEV_WINDOW_END, V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_direction_source_forensic_v1 import (
    load_sources,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_source_census_aggregate_v1 import (
    max3,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade, _metrics, _replay_one, _session_bars,
)

IDENTITY = "QORE_SCALPER_ISSUE772_E0_C0_ECONOMIC_ASSOCIATION_V1"
SEED = 77220261011
COST = Decimal("0.025")


def read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def find_exactly_one(root: Path, pattern: str) -> Path:
    found = tuple(root.rglob(pattern))
    if len(found) != 1:
        raise ValueError(f"expected exactly one {pattern}, found {len(found)}")
    return found[0]


def market(frozen: Path, native: Path, c0: Path, out: Path) -> dict[str, Any]:
    sources = load_sources(frozen)
    c0_path = find_exactly_one(c0, "scalper-issue772-c0-source-aggregate-exposure.jsonl")
    statuses = read_jsonl(c0_path)
    status_by_id = {row["source_opportunity_id"]: row for row in statuses}
    source_ids = {source_id(row) for row in sources}
    if (
        len(source_ids) != len(sources)
        or len(status_by_id) != len(statuses)
        or source_ids != set(status_by_id)
    ):
        raise ValueError("C0/source ID mismatch, duplicated, or missing")
    symbols = {src.symbol for src in sources}
    if len(symbols) != 1:
        raise ValueError("one symbol per market")
    symbol = next(iter(symbols))
    bars = tuple(
        b for b in iter_cibo_m1(native)
        if DEV_WINDOW_START <= b.opened_at < DEV_WINDOW_END
    )
    if not bars or any(b.symbol != symbol for b in bars):
        raise ValueError("native M1 feed missing or wrong symbol")
    opened = tuple(b.opened_at for b in bars)
    output: list[dict[str, Any]] = []
    for src in sources:
        sid = source_id(src)
        trade = _replay_one(
            _session_bars(bars, opened, intent=materialize_trade_intent(src)),
            materialize_trade_intent(src),
        )
        if trade is None:
            raise ValueError("original source not economically adjudicated")
        if trade.entry_at != src.m1_trigger_confirmed_at:
            raise ValueError("source economics changed entry instant")
        if trade.symbol != src.symbol or trade.trigger_family != src.m1_trigger_family:
            raise ValueError("source economics changed symbol/trigger")
        c = status_by_id[sid]
        if c["entry_at"] != trade.entry_at or c["symbol"] != symbol:
            raise ValueError("C0 and V49 economics not aligned")
        output.append({
            "source_opportunity_id": sid,
            "source": asdict(src),
            "trade": asdict(trade),
            "partial": bool(c["h1_local_closure_has_non_strict_bucket"] or
                            c["m15_direct_components_non_strict"]),
            "h1_partial": bool(c["h1_local_closure_has_non_strict_bucket"]),
            "m15_partial": bool(c["m15_direct_components_non_strict"]),
            "h1_strict_signature_changed": not bool(
                c["h1_strict_full_H1_same_original_event"]
            ),
            "inherited": bool(c["h1_inherited"]),
        })
    out.mkdir(parents=True, exist_ok=True)
    (out / f"scalper-issue772-E0-{symbol}-all-source-joined.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in output),
        encoding="utf-8",
    )
    result = {"identity": IDENTITY, "symbol": symbol, "source_n": len(sources),
              "joined_n": len(output), "selected_here": False,
              "gross_outcomes_loaded_for_posthoc_audit": True,
              "v49_modified": False}
    (out / f"scalper-issue772-E0-{symbol}-report.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
    )
    return result


def performance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [Decimal(r["trade"]["realized_gross_r"]) for r in rows]
    def stats(xs: list[Decimal]) -> dict[str, str | None]:
        if not xs:
            return {"expectancy": None, "PF": None, "sum_R": None,
                    "gross_win_R": None, "gross_loss_R": None, "WR": None}
        profit = sum((v for v in xs if v > 0), Decimal(0))
        loss = -sum((v for v in xs if v < 0), Decimal(0))
        return {
            "expectancy": str(sum(xs, Decimal(0)) / Decimal(len(xs))),
            "PF": str(profit / loss) if loss else None,
            "sum_R": str(sum(xs, Decimal(0))),
            "gross_win_R": str(profit),
            "gross_loss_R": str(loss),
            "WR": str(Decimal(sum(v > 0 for v in xs)) / Decimal(len(xs))),
        }
    return {"N": len(rows), "gross": stats(values),
            "assumed_cost_0p025R": stats([v - COST for v in values])}


def adjusted_diff(
    rows: list[dict[str, Any]],
    stratification: tuple[str, ...] = ("symbol",),
) -> float | None:
    cells: dict[tuple[str, ...], dict[bool, list[float]]] = defaultdict(
        lambda: {True: [], False: []}
    )
    for row in rows:
        key = tuple(str(row[x]) for x in stratification)
        cells[key][bool(row["partial"])].append(
            float(row["trade"]["realized_gross_r"])
        )
    top = 0.0
    bottom = 0.0
    for sides in cells.values():
        a, b = sides[True], sides[False]
        if not a or not b:
            continue
        weight = len(a) * len(b) / (len(a) + len(b))
        delta = sum(a) / len(a) - sum(b) / len(b)
        top += weight * delta
        bottom += weight
    return top / bottom if bottom else None


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires observations")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    i = int(position)
    f = position - i
    return ordered[i] * (1 - f) + ordered[min(i + 1, len(ordered) - 1)] * f


def block_bootstrap(
    rows: list[dict[str, Any]], n: int = 2000,
    seed: int = SEED, length: int = 5,
) -> dict[str, Any]:
    """Circular five-observed-date blocks; all markets travel as one date cluster."""
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[str(row["operating_date"])].append(row)
    dates = sorted(by_date)
    if len(dates) < length:
        raise ValueError("too few calendar dates for five-date block bootstrap")
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n):
        selected: list[dict[str, Any]] = []
        count = 0
        while count < len(dates):
            start = rng.randrange(len(dates))
            for k in range(min(length, len(dates) - count)):
                selected.extend(by_date[dates[(start + k) % len(dates)]])
                count += 1
        delta = adjusted_diff(selected)
        if delta is not None:
            samples.append(delta)
    if len(samples) != n:
        raise ValueError("block bootstrap lost exposed/control support")
    return {
        "method": "circular_move_blocks_by_operating_date_all_symbols_joint",
        "observed_dates": len(dates), "block_observed_dates": length,
        "replications": n, "seed": seed,
        "CI95": [quantile(samples, .025), quantile(samples, .975)],
        "median": quantile(samples, .5),
        "not_confirmatory": True,
    }


def summary_by(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    keys = sorted(set(str(r[key]) for r in rows))
    return {k: performance([r for r in rows if str(r[key]) == k]) for k in keys}


def aggregate(root: Path, output: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("scalper-issue772-E0-*-all-source-joined.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"exactly 9 market joined source files required: {len(paths)}")
    all_rows = [r for p in paths for r in read_jsonl(p)]
    sources = tuple(V49Opportunity(**r["source"]) for r in all_rows)
    source_ids = {r["source_opportunity_id"] for r in all_rows}
    if len(all_rows) != 2876 or len(source_ids) != 2876:
        raise ValueError("frozen universe identity mismatch 2876")
    if len({r["symbol"] for r in (json.loads(p.read_text(encoding="utf-8"))
                               for p in root.rglob("scalper-issue772-E0-*-report.json"))}) != 9:
        raise ValueError("exactly 9 distinct market reports required")
    selected = max3(sources)
    if len(selected) != 2020:
        raise ValueError("source-only A MAX3 identity mismatch 2020")
    a = [r for r in all_rows if r["source_opportunity_id"] in selected]
    if len(a) != 2020:
        raise ValueError("C0/PnL join changed A")
    trades = tuple(V49EconomicTrade(**r["trade"]) for r in a)
    baseline = _metrics(trades)
    if (baseline.trades != 2020 or baseline.wins != 1167 or
        baseline.losses != 852 or baseline.flats != 1 or
        abs(Decimal(baseline.total_r) - Decimal("-233.269327")) > Decimal(".001")
        or abs(Decimal(baseline.max_drawdown_r) - Decimal("236.134284")) > Decimal(".001")
        or abs(Decimal(baseline.profit_factor or "0") - Decimal(".664463")) > Decimal(".00001")):
        raise ValueError(f"FAIL CLOSED: original V49 economic baseline not reproduced: {baseline}")
    partial = [r for r in a if r["partial"]]
    clean = [r for r in a if not r["partial"]]
    strict_different = [r for r in a if r["h1_strict_signature_changed"]]
    if len(partial) != 382 or len(clean) != 1638 or len(strict_different) != 382:
        raise ValueError("FAIL CLOSED: C0 exposure/signature frozen counts changed")
    h1partial = [r for r in a if r["h1_partial"]]
    if (len(h1partial) != 375 or
        sum(r["h1_strict_signature_changed"] for r in h1partial) != 334):
        raise ValueError("FAIL CLOSED: H1 local partial/signature intersection changed")
    group2x2 = {
        f"partial={str(p).lower()}|h1_signature_changed={str(s).lower()}":
        performance([r for r in a if r["partial"] == p
                     and r["h1_strict_signature_changed"] == s])
        for p in (False, True) for s in (False, True)
    }
    bymarket: dict[str, Any] = {}
    for symbol in sorted({r["symbol"] for r in a}):
        subset = [r for r in a if r["symbol"] == symbol]
        bymarket[symbol] = {
            "all": performance(subset),
            "partial": performance([r for r in subset if r["partial"]]),
            "non_partial": performance([r for r in subset if not r["partial"]]),
            "h1_signature_changed": performance(
                [r for r in subset if r["h1_strict_signature_changed"]]
            ),
            "partial_fraction": sum(r["partial"] for r in subset) / len(subset),
        }
    raw_mean = float(sum((Decimal(r["trade"]["realized_gross_r"])
                          for r in partial), Decimal(0)) / Decimal(len(partial))) - float(
        sum((Decimal(r["trade"]["realized_gross_r"])
             for r in clean), Decimal(0)) / Decimal(len(clean))
    )
    primary = adjusted_diff(a)
    output.mkdir(parents=True, exist_ok=True)
    (output / "scalper-issue772-E0-original-A2020-joined-PNL-research-only.jsonl").write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in a), encoding="utf-8"
    )
    report = {
        "identity": IDENTITY,
        "sources": len(all_rows), "A_trades": len(a), "baseline": asdict(baseline),
        "preregistered_primary": "within-symbol-adjusted-partial-minus-nonpartial-mean-gross-R",
        "primary_delta_R": primary,
        "unadjusted_delta_R": raw_mean,
        "primary_bootstrap": block_bootstrap(a),
        "symbol_session_inherited_adjusted_exploratory": adjusted_diff(
            a, ("symbol", "session", "inherited")
        ),
        "partial": performance(partial), "non_partial": performance(clean),
        "h1_signature_changed": performance(strict_different),
        "h1_signature_unchanged": performance(
            [r for r in a if not r["h1_strict_signature_changed"]]
        ),
        "partial_x_strict_signature_table": group2x2,
        "by_market": bymarket,
        "by_session": summary_by(a, "session"),
        "by_inherited": summary_by(a, "inherited"),
        "gross_outcomes_loaded_only_in_E0": True,
        "not_causal_and_history_consumed": True,
        "broker_net_not_verified": True,
        "no_feed_changes_or_strategy_changes": True,
        "no_certification": True,
    }
    (output / "scalper-issue772-E0-economic-association-results.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    subs = p.add_subparsers(dest="mode", required=True)
    a = subs.add_parser("market")
    for x in ("frozen", "native", "c0", "output"):
        a.add_argument(x, type=Path)
    b = subs.add_parser("aggregate")
    b.add_argument("nine_markets", type=Path)
    b.add_argument("output", type=Path)
    args = p.parse_args()
    if args.mode == "market":
        print("E0_MARKET", json.dumps(market(args.frozen, args.native, args.c0, args.output), sort_keys=True))
    else:
        result = aggregate(args.nine_markets, args.output)
        print("E0_FINAL", json.dumps({
            "primary_R": result["primary_delta_R"],
            "CI95": result["primary_bootstrap"]["CI95"],
            "market_counts": {k: v["partial"]["N"] for k, v in result["by_market"].items()},
            "baseline": result["baseline"],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
