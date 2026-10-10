"""Research-only same-source nine-market H1 external-liquidity target replay.

Only the target price may change. M15 stop, entry, trigger, chronological
MAX3, same M1 and stop-first lifecycle are frozen. Source V49 must be exactly
replayed first or ALL candidate economics fail-closed. No ex-post selection.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import _aggregate
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    materialize_trade_intent,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_liquidity_target_v1 import (
    discover_h1_liquidity_targets,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_winner_retention_v1 import (
    _origin,
    _source_table,
    compare_winner_mass,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
    _replay_one,
    _session_bars,
)

IDENTITY = "QORE_SCALPER_A2_H1_EXTERNAL_TARGET_PAIRED_REPLAY_V1"


def build_market(
    v49_root: Path, native_m1_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...],
           dict[str, tuple[V49EconomicTrade, ...]]]:
    paths = sorted(v49_root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    baselines = sorted(v49_root.rglob("capitalizer-*-v49-development-economics-trades.jsonl"))
    if len(paths) != 1 or len(baselines) != 1:
        raise ValueError("paired target replay needs one frozen source and trade ledger")
    sources = tuple(V49Opportunity(**raw) for raw in _jsonl(paths[0]))
    baseline = tuple(V49EconomicTrade(**raw) for raw in _jsonl(baselines[0]))
    if not sources or len(sources) != len(baseline):
        raise ValueError("different original candidate/entry population")
    symbol = sources[0].symbol
    if any(s.symbol != symbol or s.session != sources[0].session for s in sources):
        raise ValueError("source ledger market mixed")
    source_table = _source_table(sources)
    baseline_by_id = {_origin(t, source_table): t for t in baseline}
    if len(baseline_by_id) != len(sources):
        raise ValueError("duplicate historical replay source identity")

    bars = tuple(
        b for b in iter_cibo_m1(native_m1_root)
        if DEV_WINDOW_START - DEFAULT_LOOKBACK <= b.opened_at < DEV_WINDOW_END
    )
    if not bars or any(b.symbol != symbol for b in bars):
        raise ValueError("M1 original symbol missing or inconsistent")
    economic_bars = tuple(b for b in bars if b.opened_at >= DEV_WINDOW_START)
    econ_opened = tuple(b.opened_at for b in economic_bars)
    opened = tuple(b.opened_at for b in bars)
    h1 = _aggregate(bars, minutes=60)
    h1_closed = tuple(b.closed_at for b in h1)
    if not economic_bars or not h1:
        raise ValueError("native H1/M1 is incomplete")

    decisions: list[dict[str, Any]] = []
    old: list[V49EconomicTrade] = []
    new: list[V49EconomicTrade] = []
    for source in sources:
        at = datetime.fromisoformat(source.m1_trigger_confirmed_at)
        if at.utcoffset() is None:
            raise ValueError("entry timestamp requires timezone")
        start = at - DEFAULT_LOOKBACK
        left_m1 = bisect.bisect_left(opened, start)
        right_m1 = bisect.bisect_left(opened, at)
        left_h1 = bisect.bisect_left(h1_closed, start)
        right_h1 = bisect.bisect_right(h1_closed, at)
        if right_m1 <= left_m1 or right_h1 <= left_h1:
            raise ValueError("source lookback missing causal raw H1/M1")
        decision = discover_h1_liquidity_targets(
            source, h1[left_h1:right_h1], bars[left_m1:right_m1]
        )
        if decision.selected is None:
            raise ValueError("every original V49 source must retain a valid target")
        intent = materialize_trade_intent(source)
        session_bars = _session_bars(economic_bars, econ_opened, intent=intent)
        original_fill = _replay_one(session_bars, intent)
        identifier = source_id(source)
        if original_fill is None or original_fill != baseline_by_id[identifier]:
            raise ValueError("new replay did not exactly reproduce frozen V49")
        alternative_intent = replace(intent, target_price=decision.selected.price)
        alternative_fill = _replay_one(session_bars, alternative_intent)
        if alternative_fill is None:
            raise ValueError("alternative target lost original session M1 lifecycle")
        if (
            alternative_fill.entry_at != original_fill.entry_at
            or alternative_fill.stop_price != original_fill.stop_price
            or alternative_fill.entry_price != original_fill.entry_price
        ):
            raise ValueError("paired target changed entry/stop/source")
        old.append(original_fill)
        new.append(alternative_fill)
        decisions.append({
            "source_opportunity_id": identifier,
            "symbol": symbol,
            "session": source.session,
            "entry_at": source.m1_trigger_confirmed_at,
            "family": source.m1_trigger_family,
            "baseline_target_price": source.structural_target_witness_price,
            "candidate_target_price": str(decision.selected.price),
            "candidate_target_kind": decision.selected.kind.value,
            "candidate_target_r": str(decision.selected.target_r_vs_m15_stop),
            "candidate_confirmed_at": decision.selected.confirmed_at.isoformat(),
            "untouched_external_candidate_count": len(
                decision.available_external_swings
            ),
            "unmitigated_internal_fvg_count": len(decision.available_internal_fvgs),
            "same_target": decision.selected.price == intent.target_price,
            "baseline_gross_r_posthoc": original_fill.realized_gross_r,
            "candidate_gross_r_posthoc": alternative_fill.realized_gross_r,
            "entry_policy_changed": False,
            "target_selection_uses_outcome": False,
        })
    return ({
        "identity": IDENTITY,
        "symbol": symbol,
        "source_opportunities": len(sources),
        "original_v49_replays_reconciled": len(old),
        "target_changed": sum(not x["same_target"] for x in decisions),
        "target_unchanged": sum(bool(x["same_target"]) for x in decisions),
        "types": sorted(Counter(x["candidate_target_kind"] for x in decisions).items()),
        "no_trade_removed": True,
        "full_master_frame_evaluated": False,
        "broker_physical_costs_applied": False,
        "trader_certified": False,
        "live_authorized": False,
    }, tuple(decisions), {
        "V49_FROZEN": tuple(old),
        "H1_EXTERNAL_FIRST": tuple(new),
    })


def write_market(
    report: dict[str, Any], decisions: tuple[dict[str, Any], ...],
    arms: dict[str, tuple[V49EconomicTrade, ...]], out: Path,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "scalper-h1-liquidity-market.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (out / "scalper-h1-liquidity-decisions.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in decisions:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    for arm, trades in arms.items():
        with (out / f"scalper-h1-liquidity-{arm}.jsonl").open(
            "w", encoding="utf-8"
        ) as f:
            for row in trades:
                f.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def aggregate(root: Path) -> dict[str, Any]:
    reports = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-h1-liquidity-market.json"))
    ]
    if len(reports) != 9 or len({r["symbol"] for r in reports}) != 9:
        raise ValueError("9 market source reports mandatory")
    all_decisions = [
        x for path in sorted(root.rglob("scalper-h1-liquidity-decisions.jsonl"))
        for x in _jsonl(path)
    ]
    if len(all_decisions) != 2876:
        raise ValueError("source identity coverage must be 2876")
    ids = {x["source_opportunity_id"] for x in all_decisions}
    if len(ids) != 2876 or sum(r["source_opportunities"] for r in reports) != 2876:
        raise ValueError("9-market source identities must reconcile")
    if any(x["entry_policy_changed"] or x["target_selection_uses_outcome"]
           for x in all_decisions):
        raise ValueError("future outcome or entry policy in alternative target")
    decisions_by_id = {x["source_opportunity_id"]: x for x in all_decisions}
    all_selected: dict[str, tuple[V49EconomicTrade, ...]] = {}
    metrics: dict[str, Any] = {}
    source_ids_by_trade = {
        (
            row["symbol"], row["session"], row["entry_at"],
            row["family"],
        ): source for source, row in decisions_by_id.items()
    }
    if len(source_ids_by_trade) != 2876:
        raise ValueError("ambiguous replay trade-source parent")
    for arm in ("V49_FROZEN", "H1_EXTERNAL_FIRST"):
        files = sorted(root.rglob(f"scalper-h1-liquidity-{arm}.jsonl"))
        if len(files) != 9:
            raise ValueError("missing or duplicate market alternative trade ledger")
        trades = tuple(V49EconomicTrade(**x) for f in files for x in _jsonl(f))
        if len(trades) != 2876:
            raise ValueError("alternative trade universe reduced from control")
        selected = tuple(t for _, t in _portfolio_select(trades))
        all_selected[arm] = selected
        metrics[arm] = asdict(_metrics(selected))
    def index(trades: tuple[V49EconomicTrade, ...]) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for t in trades:
            key = (t.symbol,t.session,t.entry_at,t.trigger_family)
            if key not in source_ids_by_trade:
                raise ValueError("unjoined selected source ID")
            identifier = source_ids_by_trade[key]
            if identifier in result:
                raise ValueError("duplicate selected source ID")
            result[identifier] = Decimal(t.realized_gross_r)
        return result

    baseline = index(all_selected["V49_FROZEN"])
    candidate = index(all_selected["H1_EXTERNAL_FIRST"])
    if len(baseline) != 2020 or len(candidate) != 2020:
        raise ValueError("MAX3 first-three chronological census must remain fixed")
    retention = compare_winner_mass(baseline, candidate)
    if retention["baseline_positive_winners"] != 1167:
        raise ValueError("V49 baseline original winner count altered")
    if metrics["V49_FROZEN"]["profit_factor"] != (
        "0.6644630742216047176197070525"
    ):
        raise ValueError("V49 control base PF is no longer byte-faithful")
    return {
        "identity": IDENTITY,
        "market_count": 9,
        "source_opportunities": 2876,
        "post_max3_control_and_candidate": 2020,
        "target_changed_source_opportunities": sum(
            not x["same_target"] for x in all_decisions
        ),
        "target_selected_kinds": dict(Counter(
            x["candidate_target_kind"] for x in all_decisions
        )),
        "arms": metrics,
        "matched_winner_retention": retention,
        "source_selection_changed": False,
        "stop_location_changed": False,
        "target_only_ablation": True,
        "no_outcome_selected_target": True,
        "all_segments_are_in_sample_exploratory": True,
        "full_master_frame_evaluated": False,
        "broker_physical_costs_applied": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("control", type=Path)
    m.add_argument("raw_m1", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("reports", type=Path)
    a.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        r, decisions, arms = build_market(args.control,args.raw_m1)
        write_market(r,decisions,arms,args.output)
        print(json.dumps({
            "identity": IDENTITY, "symbol": r["symbol"],
            "source_opportunities": r["source_opportunities"],
            "target_changed": r["target_changed"],
            "trader_certified": False,
        }, sort_keys=True))
    else:
        r = aggregate(args.reports)
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output / "scalper-h1-liquidity-nine-market.json").write_text(
            json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8"
        )
        print(json.dumps({
            "identity": IDENTITY,
            "target_changed": r["target_changed_source_opportunities"],
            "gross_arms": r["arms"],
            "matched": r["matched_winner_retention"],
            "trader_certified": False,
        },sort_keys=True))


if __name__ == "__main__":
    main()
