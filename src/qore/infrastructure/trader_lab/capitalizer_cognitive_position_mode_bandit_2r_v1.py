"""Online position-mode learning for the true-2R Capitalizer.

Each market learns from its own *actually chosen and already closed* position
management outcomes. Counterfactual modes for prior trades are never revealed to
the learner. This makes the replay equivalent to a deterministic contextual
bandit rather than retrospective mode selection.

All 948 entries remain admitted. The only decision is which already-causal
position-protection mode to use before the current trade outcome exists.
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
    capitalizer_cognitive_m3_stop_protection_true_2r_v2 as m3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_stability_intelligence_2r_v1 as stability,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_POSITION_MODE_BANDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M3_RUN_ID = 36177149363
SOURCE_M3_SHA = "2d3cb599a9a6eb5566a7374e17317a43d4d6a6b0"
EXPECTED_TRADES = 948
PRIOR_STRENGTH = Decimal("6")
WARMUP_SELECTIONS_PER_ARM = 3
PRESSURE_RECENT = 6
PRESSURE_MIN_NEGATIVE_SYMBOLS = 3
PRESSURE_SUM_R = Decimal("-2")

ARMS = (
    m3.ProtectionMode.ORIGINAL.value,
    m3.ProtectionMode.M3_PROFITABLE_SWING_LOCK.value,
    m3.ProtectionMode.M3_SWING_IMPROVE.value,
)
POLICIES = (
    "ORIGINAL_ONLY",
    "SYMBOL_GREEDY_MEAN",
    "SYMBOL_STATE_UTILITY",
    "SYMBOL_PRESSURE_UTILITY",
    "GLOBAL_STATE_UTILITY",
)


@dataclass(frozen=True, slots=True)
class ModeDecision:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    policy: str
    state: str
    systemic_pressure: bool
    selected_mode: str
    selection_reason: str
    closed_history: int
    symbol_closed_history: int
    arm_closed_counts: dict[str, int]
    arm_posterior_mean_r: dict[str, str]
    arm_posterior_stop_rate: dict[str, str]
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_outcomes_visible_to_decision: bool = False


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    return stability._load_rebase(root)


def _load_modes(
    root: Path,
) -> dict[str, tuple[stability.TradeOutcome, ...]]:
    return {
        arm: stability._load_mode(root, mode=arm)
        for arm in ARMS
    }


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _closed_before(
    chosen: tuple[stability.TradeOutcome, ...],
    *,
    entry_at: object,
) -> tuple[stability.TradeOutcome, ...]:
    current = stability._aware(entry_at, field="entry_at")
    return tuple(
        sorted(
            (
                item
                for item in chosen
                if stability._aware(item.exit_at, field="exit_at") <= current
            ),
            key=lambda item: (
                stability._aware(item.exit_at, field="exit_at"),
                item.symbol,
            ),
        )
    )


def _mean_and_stop(
    rows: tuple[stability.TradeOutcome, ...],
) -> tuple[Decimal, Decimal]:
    if not rows:
        return Decimal("0"), Decimal("0")
    mean_r = sum(
        (Decimal(item.realized_gross_r) for item in rows),
        Decimal("0"),
    ) / Decimal(len(rows))
    stop_rate = Decimal(sum(item.exit_reason == "STOP" for item in rows)) / Decimal(
        len(rows)
    )
    return mean_r, stop_rate


def _posterior(
    *,
    rows: tuple[stability.TradeOutcome, ...],
    global_mean: Decimal,
    global_stop: Decimal,
) -> tuple[Decimal, Decimal]:
    values = sum(
        (Decimal(item.realized_gross_r) for item in rows),
        Decimal("0"),
    )
    stops = Decimal(sum(item.exit_reason == "STOP" for item in rows))
    denom = PRIOR_STRENGTH + Decimal(len(rows))
    mean_r = (PRIOR_STRENGTH * global_mean + values) / denom
    stop_rate = (PRIOR_STRENGTH * global_stop + stops) / denom
    return mean_r, stop_rate


def _systemic_pressure(
    history: tuple[stability.TradeOutcome, ...],
) -> bool:
    recent = history[-PRESSURE_RECENT:]
    if len(recent) < PRESSURE_RECENT:
        return False
    total = sum(
        (Decimal(item.realized_gross_r) for item in recent),
        Decimal("0"),
    )
    negative_symbols = {
        item.symbol
        for item in recent
        if Decimal(item.realized_gross_r) < 0
    }
    return total <= PRESSURE_SUM_R and len(negative_symbols) >= PRESSURE_MIN_NEGATIVE_SYMBOLS


def _warmup_mode(
    *,
    symbol: str,
    selection_counts: Counter[tuple[str, str]],
) -> str | None:
    counts = {arm: selection_counts[(symbol, arm)] for arm in ARMS}
    minimum = min(counts.values())
    if minimum >= WARMUP_SELECTIONS_PER_ARM:
        return None
    return next(arm for arm in ARMS if counts[arm] == minimum)


def _scores(
    *,
    policy: str,
    state: stability.StabilityState,
    pressure: bool,
    symbol: str,
    history: tuple[stability.TradeOutcome, ...],
) -> tuple[dict[str, Decimal], dict[str, Decimal], dict[str, Decimal], dict[str, int]]:
    global_mean, global_stop = _mean_and_stop(history)
    means: dict[str, Decimal] = {}
    stops: dict[str, Decimal] = {}
    counts: dict[str, int] = {}

    for arm in ARMS:
        if policy == "GLOBAL_STATE_UTILITY":
            arm_rows = tuple(item for item in history if item.mode == arm)
        else:
            arm_rows = tuple(
                item
                for item in history
                if item.symbol == symbol and item.mode == arm
            )
        mean_r, stop_rate = _posterior(
            rows=arm_rows,
            global_mean=global_mean,
            global_stop=global_stop,
        )
        means[arm] = mean_r
        stops[arm] = stop_rate
        counts[arm] = len(arm_rows)

    scores: dict[str, Decimal] = {}
    for arm in ARMS:
        if policy == "SYMBOL_GREEDY_MEAN":
            penalty = Decimal("0")
        elif state is stability.StabilityState.STABLE:
            penalty = Decimal("0")
        elif state is stability.StabilityState.WATCH:
            penalty = Decimal("0.50")
        else:
            penalty = Decimal("1.00")

        if policy == "SYMBOL_PRESSURE_UTILITY" and pressure:
            penalty += Decimal("0.75")
        scores[arm] = means[arm] - penalty * stops[arm]

    return scores, means, stops, counts


def _choose_mode(
    *,
    policy: str,
    row: dict[str, Any],
    history: tuple[stability.TradeOutcome, ...],
    selection_counts: Counter[tuple[str, str]],
) -> tuple[
    str,
    str,
    stability.StabilityState,
    bool,
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, int],
]:
    state, _dd, _recent5, _loss_streak, _stop_streak = stability._state(history)
    pressure = _systemic_pressure(history)

    if policy == "ORIGINAL_ONLY":
        return (
            m3.ProtectionMode.ORIGINAL.value,
            "FIXED_ORIGINAL_CONTROL",
            state,
            pressure,
            {arm: Decimal("0") for arm in ARMS},
            {arm: Decimal("0") for arm in ARMS},
            {arm: 0 for arm in ARMS},
        )

    symbol = str(row["symbol"])
    warmup = _warmup_mode(symbol=symbol, selection_counts=selection_counts)
    scores, means, stops, counts = _scores(
        policy=policy,
        state=state,
        pressure=pressure,
        symbol=symbol,
        history=history,
    )
    if warmup is not None:
        return warmup, "DETERMINISTIC_ARM_WARMUP", state, pressure, means, stops, counts

    selected = max(
        ARMS,
        key=lambda arm: (
            scores[arm],
            means[arm],
            -stops[arm],
            -ARMS.index(arm),
        ),
    )
    return selected, "ONLINE_POSTERIOR_UTILITY", state, pressure, means, stops, counts


def _simulate(
    *,
    policy: str,
    rows: tuple[dict[str, Any], ...],
    mode_ledgers: dict[str, tuple[stability.TradeOutcome, ...]],
) -> tuple[dict[str, Any], tuple[ModeDecision, ...]]:
    by_mode = {
        mode: {(item.symbol, item.entry_at): item for item in ledger}
        for mode, ledger in mode_ledgers.items()
    }
    keys = {_join_key(row) for row in rows}
    if any(set(index) != keys for index in by_mode.values()):
        raise ValueError("bandit rebase/mode identities differ")

    ordered_rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                stability._aware(row["entry_at"], field="entry_at"),
                str(row["symbol"]),
            ),
        )
    )
    chosen: list[stability.TradeOutcome] = []
    decisions: list[ModeDecision] = []
    selection_counts: Counter[tuple[str, str]] = Counter()

    for row in ordered_rows:
        key = _join_key(row)
        history = _closed_before(tuple(chosen), entry_at=row["entry_at"])
        selected, reason, state, pressure, means, stops, counts = _choose_mode(
            policy=policy,
            row=row,
            history=history,
            selection_counts=selection_counts,
        )
        outcome = by_mode[selected][key]
        chosen.append(outcome)
        selection_counts[(str(row["symbol"]), selected)] += 1

        decisions.append(
            ModeDecision(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                policy=policy,
                state=state.value,
                systemic_pressure=pressure,
                selected_mode=selected,
                selection_reason=reason,
                closed_history=len(history),
                symbol_closed_history=sum(
                    item.symbol == str(row["symbol"]) for item in history
                ),
                arm_closed_counts=counts,
                arm_posterior_mean_r={
                    arm: str(means[arm]) for arm in ARMS
                },
                arm_posterior_stop_rate={
                    arm: str(stops[arm]) for arm in ARMS
                },
            )
        )

    ledger = tuple(chosen)
    metrics = stability._metrics(ledger)
    control = mode_ledgers[m3.ProtectionMode.ORIGINAL.value]
    control_metrics = stability._metrics(control)
    return {
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": metrics,
        "control_metrics": control_metrics,
        "mode_counts": {
            arm: selection_counts[(symbol, arm)]
            for arm in ARMS
            for symbol in ()
        },
        "aggregate_mode_counts": {
            arm: sum(
                count
                for (symbol, selected), count in selection_counts.items()
                if selected == arm
            )
            for arm in ARMS
        },
        "systemic_pressure_decisions": sum(
            item.systemic_pressure for item in decisions
        ),
        "pf_at_least_control": (
            metrics["profit_factor"] is not None
            and control_metrics["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"]))
            >= Decimal(str(control_metrics["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(metrics["total_r"]))
            >= Decimal(str(control_metrics["total_r"]))
        ),
        "dd_below_control": (
            Decimal(str(metrics["max_drawdown_r"]))
            < Decimal(str(control_metrics["max_drawdown_r"]))
        ),
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_outcomes_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    rebase_root: Path,
    m3_root: Path,
) -> tuple[dict[str, Any], tuple[ModeDecision, ...]]:
    rebase_report, rows = _load_rebase(rebase_root)
    modes = _load_modes(m3_root)

    results: list[dict[str, Any]] = []
    decisions: list[ModeDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(
            policy=policy,
            rows=rows,
            mode_ledgers=modes,
        )
        results.append(result)
        decisions.extend(audit)

    pareto = tuple(
        row
        for row in results
        if row["pf_at_least_control"]
        and row["total_r_at_least_control"]
        and row["dd_below_control"]
    )
    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m3_run_id": SOURCE_M3_RUN_ID,
        "source_m3_sha": SOURCE_M3_SHA,
        "development_window_role": "PREQUENTIAL_CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "policy_count": len(POLICIES),
        "results": results,
        "pareto_improving_policy_count": len(pareto),
        "all_entries_preserved": True,
        "prior_chosen_closed_outcomes_only": True,
        "unchosen_counterfactuals_hidden_from_learner": True,
        "current_trade_outcome_visible_to_decision": False,
        "automatic_policy_selection": False,
        "runtime_rule_selected": False,
        "fresh_holdout_required_after_candidate_selection": True,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(rows)
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
            "FRESH_HOLDOUT_POSITION_MODE_LEARNER"
            if pareto
            else "ADD_CROSS_MARKET_PRESSURE_AND_DESTINATION_CONTEXT"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[ModeDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-position-mode-bandit-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-position-mode-bandit-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("m3_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(args.rebase_root, args.m3_root)
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
