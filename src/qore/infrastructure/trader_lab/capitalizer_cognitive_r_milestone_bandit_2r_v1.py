"""Online R-milestone management bandit for Capitalizer true-2R.

This learner chooses among a compact family of already-causal milestone
protection modes.  Each symbol learns only from the outcomes of modes that were
actually chosen for trades already CLOSED before the next decision.

Important distinction: an exit_reason=STOP is not automatically adverse after
protection because the stop may have been moved to breakeven or positive R.
Therefore the utility penalizes *negative realized outcomes* and their downside
magnitude, not raw stop counts.

All frozen entries, 2R targets, structural entry stops and MAX3 admissions are
preserved.  Unchosen counterfactual outcomes are hidden from the learner.
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

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_R_MILESTONE_BANDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_MILESTONE_RUN_ID = 36194480697
SOURCE_MILESTONE_SHA = "24421d9c043eaf15197e30851851f8b926f167a0"
EXPECTED_TRADES = 948

PRIOR_STRENGTH = Decimal("5")
WARMUP_SELECTIONS_PER_ARM = 2
PRESSURE_RECENT = 6
PRESSURE_SUM_R = Decimal("-2")
PRESSURE_MIN_NEGATIVE_SYMBOLS = 3

ARMS = (
    milestone.ProtectionMode.ORIGINAL.value,
    milestone.ProtectionMode.BE_AFTER_050.value,
    milestone.ProtectionMode.BE_AFTER_075.value,
    milestone.ProtectionMode.LOCK025_AFTER_075.value,
    milestone.ProtectionMode.LOCK025_AFTER_100.value,
    milestone.ProtectionMode.STAGED_075_125_150.value,
)

POLICIES = (
    "ORIGINAL_ONLY",
    "SYMBOL_GREEDY_MEAN",
    "SYMBOL_STATE_DOWNSIDE_UTILITY",
    "SYMBOL_PRESSURE_DOWNSIDE_UTILITY",
    "GLOBAL_STATE_DOWNSIDE_UTILITY",
)


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    mode: str


@dataclass(frozen=True, slots=True)
class MilestoneBanditDecision:
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
    arm_posterior_negative_rate: dict[str, str]
    arm_posterior_downside_r: dict[str, str]
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_outcomes_visible_to_decision: bool = False


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    return stability._load_rebase(root)


def _load_arm(root: Path, *, arm: str) -> tuple[TradeOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-r-milestone-protection-2r-v1-"
            f"{arm.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"milestone bandit requires 9 {arm} ledgers")
    rows: list[TradeOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                rows.append(
                    TradeOutcome(
                        symbol=str(raw["symbol"]),
                        session=str(raw["session"]),
                        operating_date=str(raw["operating_date"]),
                        side=str(raw["side"]),
                        entry_at=str(raw["entry_at"]),
                        exit_at=str(raw["exit_at"]),
                        realized_gross_r=str(raw["realized_gross_r"]),
                        exit_reason=str(raw["exit_reason"]),
                        mode=str(raw["mode"]),
                    )
                )
    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (
                stability._aware(item.entry_at, field="entry_at"),
                item.symbol,
            ),
        )
    )
    if len(ordered) != EXPECTED_TRADES:
        raise ValueError(f"milestone {arm} ledger must contain 948 trades")
    return ordered


def _load_arms(root: Path) -> dict[str, tuple[TradeOutcome, ...]]:
    return {arm: _load_arm(root, arm=arm) for arm in ARMS}


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _closed_before(
    chosen: tuple[TradeOutcome, ...],
    *,
    entry_at: object,
) -> tuple[TradeOutcome, ...]:
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


def _distribution(
    rows: tuple[TradeOutcome, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    if not rows:
        return Decimal("0"), Decimal("0"), Decimal("0")
    values = tuple(Decimal(item.realized_gross_r) for item in rows)
    negative = tuple(-value for value in values if value < 0)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    negative_rate = Decimal(len(negative)) / Decimal(len(values))
    downside_r = (
        Decimal("0")
        if not negative
        else sum(negative, Decimal("0")) / Decimal(len(negative))
    )
    return mean_r, negative_rate, downside_r


def _posterior(
    *,
    rows: tuple[TradeOutcome, ...],
    global_mean: Decimal,
    global_negative_rate: Decimal,
    global_downside: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    n = Decimal(len(rows))
    denom = PRIOR_STRENGTH + n
    values = tuple(Decimal(item.realized_gross_r) for item in rows)
    negative = tuple(-value for value in values if value < 0)

    mean_r = (
        PRIOR_STRENGTH * global_mean + sum(values, Decimal("0"))
    ) / denom
    negative_rate = (
        PRIOR_STRENGTH * global_negative_rate + Decimal(len(negative))
    ) / denom

    if negative:
        downside_observed = sum(negative, Decimal("0")) / Decimal(len(negative))
    else:
        downside_observed = Decimal("0")
    downside_r = (
        PRIOR_STRENGTH * global_downside + n * downside_observed
    ) / denom
    return mean_r, negative_rate, downside_r


def _systemic_pressure(history: tuple[TradeOutcome, ...]) -> bool:
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
    return (
        total <= PRESSURE_SUM_R
        and len(negative_symbols) >= PRESSURE_MIN_NEGATIVE_SYMBOLS
    )


def _warmup_arm(
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
    history: tuple[TradeOutcome, ...],
) -> tuple[
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, int],
]:
    global_mean, global_negative, global_downside = _distribution(history)
    means: dict[str, Decimal] = {}
    negatives: dict[str, Decimal] = {}
    downsides: dict[str, Decimal] = {}
    counts: dict[str, int] = {}

    for arm in ARMS:
        if policy == "GLOBAL_STATE_DOWNSIDE_UTILITY":
            arm_rows = tuple(item for item in history if item.mode == arm)
        else:
            arm_rows = tuple(
                item
                for item in history
                if item.symbol == symbol and item.mode == arm
            )
        mean_r, negative_rate, downside_r = _posterior(
            rows=arm_rows,
            global_mean=global_mean,
            global_negative_rate=global_negative,
            global_downside=global_downside,
        )
        means[arm] = mean_r
        negatives[arm] = negative_rate
        downsides[arm] = downside_r
        counts[arm] = len(arm_rows)

    if policy == "SYMBOL_GREEDY_MEAN":
        negative_weight = Decimal("0")
        downside_weight = Decimal("0")
    elif state is stability.StabilityState.STABLE:
        negative_weight = Decimal("0.20")
        downside_weight = Decimal("0.10")
    elif state is stability.StabilityState.WATCH:
        negative_weight = Decimal("0.60")
        downside_weight = Decimal("0.30")
    else:
        negative_weight = Decimal("1.00")
        downside_weight = Decimal("0.50")

    if policy == "SYMBOL_PRESSURE_DOWNSIDE_UTILITY" and pressure:
        negative_weight += Decimal("0.50")
        downside_weight += Decimal("0.25")

    scores = {
        arm: (
            means[arm]
            - negative_weight * negatives[arm]
            - downside_weight * downsides[arm]
        )
        for arm in ARMS
    }
    return scores, means, negatives, downsides, counts


def _choose(
    *,
    policy: str,
    row: dict[str, Any],
    history: tuple[TradeOutcome, ...],
    selection_counts: Counter[tuple[str, str]],
) -> tuple[
    str,
    str,
    stability.StabilityState,
    bool,
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, Decimal],
    dict[str, int],
]:
    converted_history = tuple(
        stability.TradeOutcome(
            symbol=item.symbol,
            session=item.session,
            operating_date=item.operating_date,
            side=item.side,
            entry_at=item.entry_at,
            exit_at=item.exit_at,
            realized_gross_r=item.realized_gross_r,
            exit_reason=item.exit_reason,
            mode=item.mode,
        )
        for item in history
    )
    state, _dd, _recent5, _loss_streak, _stop_streak = stability._state(
        converted_history
    )
    pressure = _systemic_pressure(history)

    zeros = {arm: Decimal("0") for arm in ARMS}
    zero_counts = {arm: 0 for arm in ARMS}
    if policy == "ORIGINAL_ONLY":
        return (
            milestone.ProtectionMode.ORIGINAL.value,
            "FIXED_ORIGINAL_CONTROL",
            state,
            pressure,
            zeros,
            zeros,
            zeros,
            zero_counts,
        )

    symbol = str(row["symbol"])
    warmup = _warmup_arm(symbol=symbol, selection_counts=selection_counts)
    scores, means, negatives, downsides, counts = _scores(
        policy=policy,
        state=state,
        pressure=pressure,
        symbol=symbol,
        history=history,
    )
    if warmup is not None:
        return (
            warmup,
            "DETERMINISTIC_ARM_WARMUP",
            state,
            pressure,
            means,
            negatives,
            downsides,
            counts,
        )

    selected = max(
        ARMS,
        key=lambda arm: (
            scores[arm],
            means[arm],
            -negatives[arm],
            -downsides[arm],
            -ARMS.index(arm),
        ),
    )
    return (
        selected,
        "ONLINE_DOWNSIDE_UTILITY",
        state,
        pressure,
        means,
        negatives,
        downsides,
        counts,
    )


def _metrics(rows: tuple[TradeOutcome, ...]) -> dict[str, Any]:
    converted = tuple(
        stability.TradeOutcome(
            symbol=item.symbol,
            session=item.session,
            operating_date=item.operating_date,
            side=item.side,
            entry_at=item.entry_at,
            exit_at=item.exit_at,
            realized_gross_r=item.realized_gross_r,
            exit_reason=item.exit_reason,
            mode=item.mode,
        )
        for item in rows
    )
    return stability._metrics(converted)


def _simulate(
    *,
    policy: str,
    rows: tuple[dict[str, Any], ...],
    ledgers: dict[str, tuple[TradeOutcome, ...]],
) -> tuple[dict[str, Any], tuple[MilestoneBanditDecision, ...]]:
    by_arm = {
        arm: {(item.symbol, item.entry_at): item for item in ledger}
        for arm, ledger in ledgers.items()
    }
    keys = {_join_key(row) for row in rows}
    if any(set(index) != keys for index in by_arm.values()):
        raise ValueError("milestone bandit rebase/arm identities differ")

    ordered_rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                stability._aware(row["entry_at"], field="entry_at"),
                str(row["symbol"]),
            ),
        )
    )
    chosen: list[TradeOutcome] = []
    decisions: list[MilestoneBanditDecision] = []
    selection_counts: Counter[tuple[str, str]] = Counter()

    for row in ordered_rows:
        key = _join_key(row)
        history = _closed_before(tuple(chosen), entry_at=row["entry_at"])
        (
            selected,
            reason,
            state,
            pressure,
            means,
            negatives,
            downsides,
            counts,
        ) = _choose(
            policy=policy,
            row=row,
            history=history,
            selection_counts=selection_counts,
        )
        outcome = by_arm[selected][key]
        chosen.append(outcome)
        selection_counts[(str(row["symbol"]), selected)] += 1

        decisions.append(
            MilestoneBanditDecision(
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
                arm_posterior_negative_rate={
                    arm: str(negatives[arm]) for arm in ARMS
                },
                arm_posterior_downside_r={
                    arm: str(downsides[arm]) for arm in ARMS
                },
            )
        )

    ledger = tuple(chosen)
    metrics = _metrics(ledger)
    control = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    control_metrics = _metrics(control)
    return {
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": metrics,
        "control_metrics": control_metrics,
        "aggregate_mode_counts": {
            arm: sum(
                count
                for (_symbol, selected), count in selection_counts.items()
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
        "dd_at_or_below_6r": (
            Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_outcomes_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    rebase_root: Path,
    milestone_root: Path,
) -> tuple[dict[str, Any], tuple[MilestoneBanditDecision, ...]]:
    rebase_report, rows = _load_rebase(rebase_root)
    ledgers = _load_arms(milestone_root)

    results: list[dict[str, Any]] = []
    decisions: list[MilestoneBanditDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(
            policy=policy,
            rows=rows,
            ledgers=ledgers,
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
    dd6 = tuple(
        row
        for row in pareto
        if row["dd_at_or_below_6r"]
    )
    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_milestone_run_id": SOURCE_MILESTONE_RUN_ID,
        "source_milestone_sha": SOURCE_MILESTONE_SHA,
        "development_window_role": "PREQUENTIAL_CONSUMED_POSITION_RESEARCH",
        "target_r": "2.00",
        "control_trades": len(rows),
        "arm_count": len(ARMS),
        "policy_count": len(POLICIES),
        "results": results,
        "pareto_improving_policy_count": len(pareto),
        "pareto_dd6_policy_count": len(dd6),
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
            "FRESH_HOLDOUT_MILESTONE_BANDIT"
            if dd6
            else "COMBINE_BEST_MILESTONE_ROUTING_WITH_CAUSAL_REGIME_DESTINATION_STATE"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[MilestoneBanditDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-r-milestone-bandit-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-r-milestone-bandit-2r-v1-decisions.jsonl"
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
