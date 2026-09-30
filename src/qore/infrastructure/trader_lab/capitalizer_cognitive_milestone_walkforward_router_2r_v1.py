"""Temporal walk-forward router for validated R-milestone protection.

The prior online bandit paid too much exploration cost.  This lab instead asks a
more realistic deployment question: can each market select a protection regime
from a *completed past block* and transfer it into the next unseen block?

Each symbol is split chronologically into three contiguous blocks.
- Block 0 is research warmup and uses ORIGINAL in the deployment-path ledger.
- Block 1 chooses one arm using only Block-0 outcomes.
- Block 2 reselects using only Blocks 0+1 and is then evaluated unseen.

The selection criteria are fixed engineering objectives, not thresholds fitted
to the test outcomes.  All 948 entries remain present in the deployment path.
The primary out-of-sample metrics cover Blocks 1+2 only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_stability_intelligence_2r_v1 as stability,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_MILESTONE_WALKFORWARD_ROUTER_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_MILESTONE_RUN_ID = 36194480697
SOURCE_MILESTONE_SHA = "24421d9c043eaf15197e30851851f8b926f167a0"
EXPECTED_TRADES = 948
BLOCKS = 3

ARMS = tuple(mode.value for mode in milestone.ProtectionMode)
POLICIES = (
    "MEAN_R",
    "DOWNSIDE_UTILITY",
    "DD_UTILITY",
    "TAIL_UTILITY",
)


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    symbol: str
    policy: str
    target_block: int
    training_trades: int
    selected_mode: str
    selected_score: str
    selected_mean_r: str
    selected_negative_rate: str
    selected_downside_r: str
    selected_train_dd_r: str
    test_trades: int
    future_block_visible_to_selection: bool = False


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    return stability._load_rebase(root)


def _load_arms(
    root: Path,
) -> dict[str, tuple[milestone.SimulatedTrade, ...]]:
    return {
        mode.value: milestone._load_mode(root, mode=mode)
        for mode in milestone.ProtectionMode
    }


def _key(row: milestone.SimulatedTrade) -> tuple[str, str]:
    return row.symbol, row.entry_at


def _split_keys(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (
                stability._aware(row.entry_at, field="entry_at"),
                row.symbol,
            ),
        )
    )
    n = len(ordered)
    if n < 9:
        raise ValueError("walkforward market requires at least 9 trades")
    cut1 = n // 3
    cut2 = (2 * n) // 3
    blocks = (
        tuple(_key(row) for row in ordered[:cut1]),
        tuple(_key(row) for row in ordered[cut1:cut2]),
        tuple(_key(row) for row in ordered[cut2:]),
    )
    if any(not block for block in blocks):
        raise ValueError("walkforward block cannot be empty")
    flattened = tuple(key for block in blocks for key in block)
    if len(flattened) != n or len(set(flattened)) != n:
        raise ValueError("walkforward blocks must partition market trades")
    return blocks


def _arm_stats(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if not rows:
        raise ValueError("arm stats require rows")
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    negative = tuple(-value for value in values if value < 0)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    negative_rate = Decimal(len(negative)) / Decimal(len(values))
    downside = (
        Decimal("0")
        if not negative
        else sum(negative, Decimal("0")) / Decimal(len(negative))
    )
    dd = Decimal(str(milestone._metrics(rows)["max_drawdown_r"]))
    return mean_r, negative_rate, downside, dd


def _score(
    *,
    policy: str,
    mean_r: Decimal,
    negative_rate: Decimal,
    downside: Decimal,
    dd: Decimal,
) -> Decimal:
    if policy == "MEAN_R":
        return mean_r
    if policy == "DOWNSIDE_UTILITY":
        return mean_r - Decimal("0.35") * negative_rate - Decimal("0.20") * downside
    if policy == "DD_UTILITY":
        return mean_r - Decimal("0.03") * dd
    if policy == "TAIL_UTILITY":
        return mean_r - Decimal("0.50") * negative_rate - Decimal("0.50") * downside
    raise ValueError(f"unknown walkforward policy: {policy}")


def _choose(
    *,
    policy: str,
    train_keys: set[tuple[str, str]],
    by_arm: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> tuple[str, Decimal, Decimal, Decimal, Decimal, Decimal]:
    candidates: list[
        tuple[Decimal, Decimal, Decimal, Decimal, Decimal, str]
    ] = []
    for arm in ARMS:
        rows = tuple(
            row
            for key, row in by_arm[arm].items()
            if key in train_keys
        )
        mean_r, negative_rate, downside, dd = _arm_stats(rows)
        score = _score(
            policy=policy,
            mean_r=mean_r,
            negative_rate=negative_rate,
            downside=downside,
            dd=dd,
        )
        candidates.append(
            (score, mean_r, -negative_rate, -downside, -dd, arm)
        )
    best = max(candidates)
    score, mean_r, neg_negative_rate, neg_downside, neg_dd, arm = best
    return (
        arm,
        score,
        mean_r,
        -neg_negative_rate,
        -neg_downside,
        -neg_dd,
    )


def _metrics(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> dict[str, Any]:
    return milestone._metrics(rows)


def _simulate(
    *,
    policy: str,
    original: tuple[milestone.SimulatedTrade, ...],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[dict[str, Any], tuple[RoutingDecision, ...]]:
    by_arm = {
        arm: {_key(row): row for row in rows}
        for arm, rows in ledgers.items()
    }
    original_by_key = {_key(row): row for row in original}
    symbols = sorted({row.symbol for row in original})

    deployment: list[milestone.SimulatedTrade] = []
    out_of_sample: list[milestone.SimulatedTrade] = []
    decisions: list[RoutingDecision] = []
    selection_counts: Counter[str] = Counter()

    for symbol in symbols:
        market_original = tuple(row for row in original if row.symbol == symbol)
        blocks = _split_keys(market_original)

        for key in blocks[0]:
            deployment.append(original_by_key[key])

        training: set[tuple[str, str]] = set(blocks[0])
        for block_index in (1, 2):
            selected, score, mean_r, neg_rate, downside, train_dd = _choose(
                policy=policy,
                train_keys=training,
                by_arm=by_arm,
            )
            selection_counts[selected] += 1
            test_keys = blocks[block_index]
            selected_rows = tuple(by_arm[selected][key] for key in test_keys)
            deployment.extend(selected_rows)
            out_of_sample.extend(selected_rows)
            decisions.append(
                RoutingDecision(
                    symbol=symbol,
                    policy=policy,
                    target_block=block_index,
                    training_trades=len(training),
                    selected_mode=selected,
                    selected_score=str(score),
                    selected_mean_r=str(mean_r),
                    selected_negative_rate=str(neg_rate),
                    selected_downside_r=str(downside),
                    selected_train_dd_r=str(train_dd),
                    test_trades=len(test_keys),
                )
            )
            training.update(test_keys)

    deployment_ledger = tuple(
        sorted(
            deployment,
            key=lambda row: (
                stability._aware(row.entry_at, field="entry_at"),
                row.symbol,
            ),
        )
    )
    oos_ledger = tuple(
        sorted(
            out_of_sample,
            key=lambda row: (
                stability._aware(row.entry_at, field="entry_at"),
                row.symbol,
            ),
        )
    )
    if len(deployment_ledger) != EXPECTED_TRADES:
        raise ValueError("walkforward deployment path must preserve 948 trades")
    if len({_key(row) for row in deployment_ledger}) != EXPECTED_TRADES:
        raise ValueError("walkforward deployment path duplicated identities")

    original_metrics = _metrics(original)
    deployment_metrics = _metrics(deployment_ledger)
    oos_original_keys = {_key(row) for row in oos_ledger}
    original_oos = tuple(
        row for row in original if _key(row) in oos_original_keys
    )
    oos_control_metrics = _metrics(original_oos)
    oos_metrics = _metrics(oos_ledger)

    return {
        "policy": policy,
        "deployment_trades": len(deployment_ledger),
        "oos_trades": len(oos_ledger),
        "density_retention": "1",
        "selection_counts": dict(sorted(selection_counts.items())),
        "original_full_metrics": original_metrics,
        "deployment_full_metrics": deployment_metrics,
        "oos_original_metrics": oos_control_metrics,
        "oos_routed_metrics": oos_metrics,
        "oos_pf_at_least_control": (
            oos_metrics["profit_factor"] is not None
            and oos_control_metrics["profit_factor"] is not None
            and Decimal(str(oos_metrics["profit_factor"]))
            >= Decimal(str(oos_control_metrics["profit_factor"]))
        ),
        "oos_total_r_at_least_control": (
            Decimal(str(oos_metrics["total_r"]))
            >= Decimal(str(oos_control_metrics["total_r"]))
        ),
        "oos_dd_below_control": (
            Decimal(str(oos_metrics["max_drawdown_r"]))
            < Decimal(str(oos_control_metrics["max_drawdown_r"]))
        ),
        "deployment_pf_at_least_full_control": (
            deployment_metrics["profit_factor"] is not None
            and original_metrics["profit_factor"] is not None
            and Decimal(str(deployment_metrics["profit_factor"]))
            >= Decimal(str(original_metrics["profit_factor"]))
        ),
        "deployment_total_r_at_least_full_control": (
            Decimal(str(deployment_metrics["total_r"]))
            >= Decimal(str(original_metrics["total_r"]))
        ),
        "deployment_dd_below_full_control": (
            Decimal(str(deployment_metrics["max_drawdown_r"]))
            < Decimal(str(original_metrics["max_drawdown_r"]))
        ),
        "deployment_dd_at_or_below_6r": (
            Decimal(str(deployment_metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "future_block_visible_to_selection": False,
    }, tuple(decisions)


def build_report(
    rebase_root: Path,
    milestone_root: Path,
) -> tuple[dict[str, Any], tuple[RoutingDecision, ...]]:
    rebase_report, rebase_rows = _load_rebase(rebase_root)
    ledgers = _load_arms(milestone_root)
    original = ledgers[milestone.ProtectionMode.ORIGINAL.value]

    if len(rebase_rows) != len(original):
        raise ValueError("walkforward rebase/milestone population mismatch")
    rebase_keys = {
        (str(row["symbol"]), str(row["entry_at"])) for row in rebase_rows
    }
    if rebase_keys != {_key(row) for row in original}:
        raise ValueError("walkforward rebase/milestone identities differ")

    results: list[dict[str, Any]] = []
    decisions: list[RoutingDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(
            policy=policy,
            original=original,
            ledgers=ledgers,
        )
        results.append(result)
        decisions.extend(audit)

    oos_pareto = tuple(
        row
        for row in results
        if row["oos_pf_at_least_control"]
        and row["oos_total_r_at_least_control"]
        and row["oos_dd_below_control"]
    )
    deployment_pareto = tuple(
        row
        for row in results
        if row["deployment_pf_at_least_full_control"]
        and row["deployment_total_r_at_least_full_control"]
        and row["deployment_dd_below_full_control"]
    )
    dd6 = tuple(
        row for row in deployment_pareto if row["deployment_dd_at_or_below_6r"]
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_milestone_run_id": SOURCE_MILESTONE_RUN_ID,
        "source_milestone_sha": SOURCE_MILESTONE_SHA,
        "development_window_role": "TEMPORAL_WALKFORWARD_CONSUMED_RESEARCH",
        "target_r": "2.00",
        "control_trades": len(original),
        "market_count": len({row.symbol for row in original}),
        "block_count": BLOCKS,
        "arm_count": len(ARMS),
        "policy_count": len(POLICIES),
        "results": results,
        "oos_pareto_policy_count": len(oos_pareto),
        "deployment_pareto_policy_count": len(deployment_pareto),
        "deployment_dd6_policy_count": len(dd6),
        "all_entries_preserved_in_deployment_path": True,
        "future_block_visible_to_selection": False,
        "selection_uses_completed_prior_blocks_only": True,
        "automatic_policy_selection": False,
        "runtime_rule_selected": False,
        "fresh_holdout_required_after_candidate_selection": True,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(original)
        ),
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FRESH_HOLDOUT_TEMPORAL_ROUTER"
            if deployment_pareto
            else "ADD_CAUSAL_REGIME_DESTINATION_STATE"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[RoutingDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-milestone-walkforward-router-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-milestone-walkforward-router-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("milestone_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(args.rebase_root, args.milestone_root)
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
