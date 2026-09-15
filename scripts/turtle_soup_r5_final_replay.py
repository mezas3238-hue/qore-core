"""Build the final Turtle Soup Classic R5 replay artifact from frozen evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from turtle_soup_r5_economics import (
    POLICIES, R1_STRESS, R1_TOTAL, Trade, metrics, policy_report, replay
)
from turtle_soup_r5_replay_core import MARKETS, OOS_START, Evaluation, Market, run_census


def serialize(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def digest(value: object) -> str:
    raw = json.dumps(
        value,
        default=serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return sha256(raw).hexdigest()


def validate_baseline(fills: list[tuple[Evaluation, Market, int]]) -> dict[str, object]:
    if len(fills) != 14:
        raise AssertionError(f"R1 fill count drifted: {len(fills)}")
    result: dict[str, object] = {}
    for policy in POLICIES:
        trades = [replay(market, evaluation, index, policy) for evaluation, market, index in fills]
        primary = metrics(trades)
        stress = metrics(trades, "net_2bp_r")
        if primary["total_r"] != R1_TOTAL or stress["total_r"] != R1_STRESS:
            raise AssertionError(f"R1 economics drifted for {policy}")
        result[policy] = {"primary": primary, "stress": stress}
    return {"status": "PASS_EXACT_R1_REPRODUCTION", "policies": result}


def build_report(root: Path, software_sha: str) -> tuple[dict[str, object], dict[str, list[Trade]]]:
    markets = {symbol: Market(root, symbol) for symbol in MARKETS}
    baseline_evaluations, baseline_fills = run_census(markets, False)
    baseline_counts = Counter(item.status for item in baseline_evaluations)
    if baseline_counts["m1-ambiguous"] != 293 or baseline_counts["m1-data-unavailable"] != 3:
        raise AssertionError(f"R1 census drifted: {baseline_counts}")
    baseline = validate_baseline(baseline_fills)
    evaluations, fills = run_census(markets, True)
    counts = Counter(item.status for item in evaluations)
    unresolved = {key: value for key, value in counts.items() if key.startswith("tick-") and value}
    if unresolved:
        raise AssertionError(f"Wave3 required before economics: {unresolved}")
    tick_counts: Counter[str] = Counter()
    provenance: dict[str, object] = {}
    for symbol, market in markets.items():
        tick_counts.update(market.tick_counts)
        provenance[symbol] = market.provenance
    expected = Counter({"wave1": 291, "wave1b": 2, "wave2": 20})
    if tick_counts != expected:
        raise AssertionError(f"tick census drifted: {tick_counts}")
    trades_by_policy: dict[str, list[Trade]] = {}
    reports: dict[str, object] = {}
    for policy in POLICIES:
        trades = [replay(market, evaluation, index, policy) for evaluation, market, index in fills]
        trades_by_policy[policy] = trades
        reports[policy] = policy_report(trades)
    limitations = [
        {
            "market": item.market,
            "source_session": item.session,
            "side": item.side,
            "m15_opened_at": item.context[0].opened_at if item.context else None,
        }
        for item in evaluations
        if item.status == "m1-data-unavailable"
    ]
    report: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup_candidate_r5.classic_final_replay.v1",
        "research_identity_root": "turtle-soup-candidate-r1",
        "research_round_identity": "turtle-soup-candidate-r5",
        "canonical_trader_code": "CODE_UNASSIGNED",
        "software_sha": software_sha,
        "fresh_oos_consumed": False,
        "fresh_oos_authorized": False,
        "fresh_oos_embargo_start": OOS_START,
        "r1_baseline_validation": baseline,
        "r1_causal_census": baseline_counts,
        "r5_tick_target_census": tick_counts,
        "r5_tick_provenance": provenance,
        "r5_final_causal_census": counts,
        "r5_source_fills": len(fills),
        "m1_data_resolution_limitations": limitations,
        "wave3_required": False,
        "policies": reports,
        "candidate_freeze": None,
        "final_verdict": "CLASSIC_R5_REJECTED",
        "rejection_reason": (
            "NO_FROZEN_CLASSIC_POLICY_PASSES_ABSOLUTE_DEVELOPMENT_WALK_FORWARD_GATE"
        ),
    }
    report["report_digest_sha256"] = digest(report)
    return report, trades_by_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()
    report, trades = build_report(args.input_root, args.software_sha)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, default=serialize, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    payload = {policy: [asdict(trade) for trade in rows] for policy, rows in trades.items()}
    args.trades.write_text(
        json.dumps(payload, default=serialize, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "final_verdict": report["final_verdict"],
                "source_fills": report["r5_source_fills"],
                "wave3_required": report["wave3_required"],
                "report_digest_sha256": report["report_digest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
