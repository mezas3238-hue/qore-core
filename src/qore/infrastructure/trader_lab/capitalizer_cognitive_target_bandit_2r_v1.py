"""Prequential target-intelligence learner for Capitalizer true-2R research.

The frozen entry universe is unchanged. For each accepted candidate, a
deterministic online learner chooses one target from the corrected Target
Sensitivity V2 grid. The learner sees only outcomes of targets it actually chose
and only after those trades have closed. Outcomes for all unchosen target arms
remain hidden.

Because the chosen target changes exit time, the learner's history and stability
state are reconstructed from the chosen path itself. This is therefore a causal
path simulation rather than a retrospective per-trade target oracle.
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
    capitalizer_cognitive_stability_intelligence_2r_v1 as stability,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as target_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v2 as target_v2,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_TARGET_BANDIT_2R_V1"
SOURCE_TARGET_RUN_ID = 36077843102
SOURCE_TARGET_SHA = "a47de3b491b4468527c945d6eff3afbbaec82d4e"
EXPECTED_TRADES = 948
BASELINE_TARGET = Decimal("2.00")
ARMS = tuple(target_v2.TARGET_RS)
PRIOR_STRENGTH = Decimal("5")
WARMUP_PER_ARM = 2

POLICIES = (
    "FIXED_2R",
    "SYMBOL_GREEDY_MEAN",
    "SYMBOL_STATE_UTILITY",
    "SYMBOL_DD_SHORTEN",
    "GLOBAL_GREEDY_MEAN",
)


@dataclass(frozen=True, slots=True)
class TargetDecision:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    policy: str
    stability_state: str
    selected_target_r: str
    selection_reason: str
    closed_history: int
    symbol_closed_history: int
    arm_closed_counts: dict[str, int]
    arm_posterior_mean_r: dict[str, str]
    arm_posterior_stop_rate: dict[str, str]
    current_outcome_visible_to_decision: bool = False
    unchosen_target_outcomes_visible_to_decision: bool = False


def _aware(value: object, *, field: str):
    return stability._aware(value, field=field)


def _key(item: target_v1.TargetOutcome) -> tuple[str, str]:
    return item.symbol, item.entry_at


def _load_arms(root: Path) -> dict[Decimal, tuple[target_v1.TargetOutcome, ...]]:
    raw = target_v2._load_outcomes(root)
    result: dict[Decimal, tuple[target_v1.TargetOutcome, ...]] = {}
    for target_r in ARMS:
        selected_raw = tuple(item for item in raw if Decimal(item.target_r) == target_r)
        selected = target_v1._max3(selected_raw)
        ordered = tuple(
            sorted(
                selected,
                key=lambda item: (_aware(item.entry_at, field="entry_at"), item.symbol),
            )
        )
        if len(ordered) != EXPECTED_TRADES:
            raise ValueError(f"target arm {target_r} must contain 948 MAX3 trades")
        result[target_r] = ordered

    baseline_keys = {_key(item) for item in result[BASELINE_TARGET]}
    for target_r, rows in result.items():
        if {_key(item) for item in rows} != baseline_keys:
            raise ValueError(f"target arm {target_r} changed the frozen entry universe")
    return result


def _as_path_outcome(item: target_v1.TargetOutcome) -> stability.TradeOutcome:
    return stability.TradeOutcome(
        symbol=item.symbol,
        session=item.session,
        operating_date=item.operating_date,
        side=item.side,
        entry_at=item.entry_at,
        exit_at=item.exit_at,
        realized_gross_r=item.realized_gross_r,
        exit_reason=item.exit_reason,
        mode=f"TARGET_{item.target_r}",
    )


def _metrics(rows: tuple[stability.TradeOutcome, ...]) -> dict[str, Any]:
    return stability._metrics(rows)


def _mean_stop(
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
    rows: tuple[stability.TradeOutcome, ...],
    *,
    prior_mean: Decimal,
    prior_stop: Decimal,
) -> tuple[Decimal, Decimal]:
    total = sum(
        (Decimal(item.realized_gross_r) for item in rows),
        Decimal("0"),
    )
    stops = Decimal(sum(item.exit_reason == "STOP" for item in rows))
    denom = PRIOR_STRENGTH + Decimal(len(rows))
    return (
        (PRIOR_STRENGTH * prior_mean + total) / denom,
        (PRIOR_STRENGTH * prior_stop + stops) / denom,
    )


def _warmup(
    *,
    symbol: str,
    counts: Counter[tuple[str, Decimal]],
) -> Decimal | None:
    minimum = min(counts[(symbol, arm)] for arm in ARMS)
    if minimum >= WARMUP_PER_ARM:
        return None
    return next(arm for arm in ARMS if counts[(symbol, arm)] == minimum)


def _choose(
    *,
    policy: str,
    symbol: str,
    history: tuple[stability.TradeOutcome, ...],
    counts: Counter[tuple[str, Decimal]],
) -> tuple[
    Decimal,
    str,
    stability.StabilityState,
    dict[Decimal, Decimal],
    dict[Decimal, Decimal],
    dict[Decimal, int],
]:
    state, current_dd, _recent5, _loss_streak, _stop_streak = stability._state(history)
    if policy == "FIXED_2R":
        return (
            BASELINE_TARGET,
            "FIXED_2R_CONTROL",
            state,
            {arm: Decimal("0") for arm in ARMS},
            {arm: Decimal("0") for arm in ARMS},
            {arm: 0 for arm in ARMS},
        )

    warmup = _warmup(symbol=symbol, counts=counts)
    prior_mean, prior_stop = _mean_stop(history)
    means: dict[Decimal, Decimal] = {}
    stops: dict[Decimal, Decimal] = {}
    arm_counts: dict[Decimal, int] = {}
    for arm in ARMS:
        if policy == "GLOBAL_GREEDY_MEAN":
            selected = tuple(item for item in history if item.mode == f"TARGET_{arm}")
        else:
            selected = tuple(
                item
                for item in history
                if item.symbol == symbol and item.mode == f"TARGET_{arm}"
            )
        mean_r, stop_rate = _posterior(
            selected,
            prior_mean=prior_mean,
            prior_stop=prior_stop,
        )
        means[arm] = mean_r
        stops[arm] = stop_rate
        arm_counts[arm] = len(selected)

    if warmup is not None and policy != "GLOBAL_GREEDY_MEAN":
        return warmup, "DETERMINISTIC_TARGET_WARMUP", state, means, stops, arm_counts

    scores: dict[Decimal, Decimal] = {}
    for arm in ARMS:
        score = means[arm]
        if policy == "SYMBOL_STATE_UTILITY":
            if state is stability.StabilityState.WATCH:
                score -= Decimal("0.35") * stops[arm]
            elif state is stability.StabilityState.DEFENSIVE:
                score -= Decimal("0.70") * stops[arm]
        elif policy == "SYMBOL_DD_SHORTEN":
            if current_dd >= Decimal("4"):
                score -= Decimal("0.30") * (arm - Decimal("1"))
            elif current_dd >= Decimal("2"):
                score -= Decimal("0.15") * (arm - Decimal("1"))
        scores[arm] = score

    selected_arm = max(
        ARMS,
        key=lambda arm: (
            scores[arm],
            means[arm],
            -stops[arm],
            -abs(arm - BASELINE_TARGET),
        ),
    )
    return selected_arm, "ONLINE_TARGET_POSTERIOR", state, means, stops, arm_counts


def _simulate(
    *,
    policy: str,
    arms: dict[Decimal, tuple[target_v1.TargetOutcome, ...]],
) -> tuple[dict[str, Any], tuple[TargetDecision, ...]]:
    index = {
        arm: {_key(item): item for item in rows}
        for arm, rows in arms.items()
    }
    baseline = arms[BASELINE_TARGET]
    ordered_keys = [_key(item) for item in baseline]

    chosen: list[stability.TradeOutcome] = []
    decisions: list[TargetDecision] = []
    counts: Counter[tuple[str, Decimal]] = Counter()

    for key in ordered_keys:
        symbol, entry_at = key
        entry_dt = _aware(entry_at, field="entry_at")
        history = tuple(
            sorted(
                (
                    item
                    for item in chosen
                    if _aware(item.exit_at, field="exit_at") <= entry_dt
                ),
                key=lambda item: (_aware(item.exit_at, field="exit_at"), item.symbol),
            )
        )
        (
            selected_arm,
            reason,
            state,
            means,
            stops,
            arm_counts,
        ) = _choose(
            policy=policy,
            symbol=symbol,
            history=history,
            counts=counts,
        )
        source = index[selected_arm][key]
        outcome = _as_path_outcome(source)
        chosen.append(outcome)
        counts[(symbol, selected_arm)] += 1

        decisions.append(
            TargetDecision(
                symbol=source.symbol,
                session=source.session,
                operating_date=source.operating_date,
                entry_at=source.entry_at,
                policy=policy,
                stability_state=state.value,
                selected_target_r=str(selected_arm),
                selection_reason=reason,
                closed_history=len(history),
                symbol_closed_history=sum(item.symbol == symbol for item in history),
                arm_closed_counts={str(arm): arm_counts[arm] for arm in ARMS},
                arm_posterior_mean_r={str(arm): str(means[arm]) for arm in ARMS},
                arm_posterior_stop_rate={str(arm): str(stops[arm]) for arm in ARMS},
            )
        )

    ledger = tuple(chosen)
    metrics = _metrics(ledger)
    control = tuple(_as_path_outcome(item) for item in baseline)
    control_metrics = _metrics(control)
    return {
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": metrics,
        "control_metrics": control_metrics,
        "target_counts": {
            str(arm): sum(counts[(symbol, arm)] for symbol in {item.symbol for item in baseline})
            for arm in ARMS
        },
        "pf_at_least_control": (
            metrics["profit_factor"] is not None
            and control_metrics["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"]))
            >= Decimal(str(control_metrics["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(metrics["total_r"])) >= Decimal(str(control_metrics["total_r"]))
        ),
        "dd_below_control": (
            Decimal(str(metrics["max_drawdown_r"]))
            < Decimal(str(control_metrics["max_drawdown_r"]))
        ),
        "current_outcome_visible_to_decision": False,
        "unchosen_target_outcomes_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    target_root: Path,
) -> tuple[dict[str, Any], tuple[TargetDecision, ...]]:
    arms = _load_arms(target_root)
    results: list[dict[str, Any]] = []
    decisions: list[TargetDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(policy=policy, arms=arms)
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
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "PREQUENTIAL_CONSUMED_TARGET_RESEARCH",
        "control_trades": EXPECTED_TRADES,
        "target_grid_r": [str(arm) for arm in ARMS],
        "policy_count": len(POLICIES),
        "results": results,
        "pareto_improving_policy_count": len(pareto),
        "all_entries_preserved": True,
        "chosen_target_changes_exit_path": True,
        "prior_chosen_closed_outcomes_only": True,
        "unchosen_target_outcomes_hidden_from_learner": True,
        "current_trade_outcome_visible_to_decision": False,
        "automatic_policy_selection": False,
        "runtime_rule_selected": False,
        "fresh_holdout_required_after_candidate_selection": True,
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "JOINT_TARGET_AND_POSITION_INTELLIGENCE"
            if pareto
            else "KEEP_FIXED_2R_AND_ENGINEER_DESTINATION_CONTEXT"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[TargetDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-target-bandit-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / "capitalizer-cognitive-target-bandit-2r-v1-decisions.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(args.target_root)
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
