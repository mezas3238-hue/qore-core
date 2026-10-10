"""Cross-market stability governor over validated R-milestone protection.

The direct native-M1 holdout showed that milestone protection transfers, but a
static per-market mode map still leaves a large portfolio drawdown.  This lab
keeps the entire frozen trade population and switches ONLY the post-entry
milestone protection mode using portfolio information that was already realized
before the current entry.

The governor is path dependent:
- current realized drawdown from already CLOSED chosen trades;
- recent-five closed realized R;
- current closed-trade loss streak.

No current outcome, open-trade future path, or unchosen counterfactual outcome
is visible to the decision.  Because a chosen protection mode changes exit time,
the next decision sees the actual chosen path rather than a filtered final
ledger.

The same fixed policies are evaluated on development and fresh holdout without
retuning.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)

IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_STABILITY_GOVERNOR_2R_V1"
SOURCE_DIRECT_RUN_ID = 36196002610
SOURCE_DIRECT_SHA = "ddd00209e50d5ec16c8cb94f34e9e5e95f401839"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_HOLDOUT_TRADES = 1034


class StabilityState(StrEnum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEFENSIVE = "DEFENSIVE"


POLICIES: dict[str, dict[StabilityState, str]] = {
    "STATIC_LOCK025_075": {
        StabilityState.STABLE: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.WATCH: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.DEFENSIVE: milestone.ProtectionMode.LOCK025_AFTER_075.value,
    },
    "STAGED_SHIELD": {
        StabilityState.STABLE: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.WATCH: milestone.ProtectionMode.STAGED_075_125_150.value,
        StabilityState.DEFENSIVE: milestone.ProtectionMode.STAGED_050_100_150.value,
    },
    "BE_SHIELD": {
        StabilityState.STABLE: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.WATCH: milestone.ProtectionMode.BE_AFTER_075.value,
        StabilityState.DEFENSIVE: milestone.ProtectionMode.BE_AFTER_050.value,
    },
    "LOCK_THEN_STAGE": {
        StabilityState.STABLE: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.WATCH: milestone.ProtectionMode.LOCK050_AFTER_100.value,
        StabilityState.DEFENSIVE: milestone.ProtectionMode.STAGED_050_100_150.value,
    },
    "ORIGINAL_THEN_SHIELD": {
        StabilityState.STABLE: milestone.ProtectionMode.ORIGINAL.value,
        StabilityState.WATCH: milestone.ProtectionMode.LOCK025_AFTER_075.value,
        StabilityState.DEFENSIVE: milestone.ProtectionMode.STAGED_050_100_150.value,
    },
}

WATCH_DD_R = Decimal("2")
DEFENSIVE_DD_R = Decimal("4")
WATCH_RECENT5_R = Decimal("-1.5")
DEFENSIVE_RECENT5_R = Decimal("-3")
WATCH_LOSS_STREAK = 2
DEFENSIVE_LOSS_STREAK = 3


@dataclass(frozen=True, slots=True)
class GovernorDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    state: str
    selected_mode: str
    closed_history: int
    realized_equity_r: str
    realized_peak_r: str
    current_drawdown_r: str
    recent5_r: str
    loss_streak: int
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("governor requires timezone-aware timestamps")
    return parsed


def _load_role(
    root: Path,
    *,
    expected_trades: int,
) -> dict[str, tuple[milestone.SimulatedTrade, ...]]:
    raw_by_mode = {
        mode.value: direct._load_mode(root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    selected = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_by_mode.items()
    }
    counts = {len(rows) for rows in selected.values()}
    if counts != {expected_trades}:
        raise ValueError(
            f"governor role population mismatch: {sorted(counts)} "
            f"expected {expected_trades}"
        )
    identities = {
        mode: {(row.symbol, row.entry_at) for row in rows}
        for mode, rows in selected.items()
    }
    baseline = identities[milestone.ProtectionMode.ORIGINAL.value]
    if any(keys != baseline for keys in identities.values()):
        raise ValueError("governor mode ledgers have different trade identities")
    return selected


def _closed_history(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    entry_at: datetime,
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            (
                row
                for row in chosen
                if _aware(row.exit_at) <= entry_at
            ),
            key=lambda row: (_aware(row.exit_at), row.symbol),
        )
    )


def _state(
    history: tuple[milestone.SimulatedTrade, ...],
) -> tuple[StabilityState, Decimal, Decimal, Decimal, int]:
    equity = Decimal("0")
    peak = Decimal("0")
    for row in history:
        equity += Decimal(row.realized_gross_r)
        peak = max(peak, equity)
    current_dd = peak - equity

    recent = history[-5:]
    recent5 = sum(
        (Decimal(row.realized_gross_r) for row in recent),
        Decimal("0"),
    )

    loss_streak = 0
    for row in reversed(history):
        if Decimal(row.realized_gross_r) < 0:
            loss_streak += 1
        else:
            break

    if (
        current_dd >= DEFENSIVE_DD_R
        or recent5 <= DEFENSIVE_RECENT5_R
        or loss_streak >= DEFENSIVE_LOSS_STREAK
    ):
        state = StabilityState.DEFENSIVE
    elif (
        current_dd >= WATCH_DD_R
        or recent5 <= WATCH_RECENT5_R
        or loss_streak >= WATCH_LOSS_STREAK
    ):
        state = StabilityState.WATCH
    else:
        state = StabilityState.STABLE
    return state, equity, peak, current_dd, loss_streak


def _metrics(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> dict[str, Any]:
    return milestone._metrics(rows)


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[dict[str, Any], tuple[GovernorDecision, ...]]:
    mapping = POLICIES[policy]
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(
            baseline,
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )

    chosen: list[milestone.SimulatedTrade] = []
    decisions: list[GovernorDecision] = []
    state_counts: dict[str, int] = defaultdict(int)
    mode_counts: dict[str, int] = defaultdict(int)

    for base in ordered:
        entry_at = _aware(base.entry_at)
        history = _closed_history(tuple(chosen), entry_at=entry_at)
        state, equity, peak, current_dd, loss_streak = _state(history)
        mode = mapping[state]
        selected = by_mode[mode][(base.symbol, base.entry_at)]
        chosen.append(selected)
        state_counts[state.value] += 1
        mode_counts[mode] += 1

        recent5 = sum(
            (Decimal(row.realized_gross_r) for row in history[-5:]),
            Decimal("0"),
        )
        decisions.append(
            GovernorDecision(
                role=role,
                policy=policy,
                symbol=base.symbol,
                session=base.session,
                operating_date=base.operating_date,
                entry_at=base.entry_at,
                state=state.value,
                selected_mode=mode,
                closed_history=len(history),
                realized_equity_r=str(equity),
                realized_peak_r=str(peak),
                current_drawdown_r=str(current_dd),
                recent5_r=str(recent5),
                loss_streak=loss_streak,
            )
        )

    result = tuple(chosen)
    metrics = _metrics(result)
    control = _metrics(baseline)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": metrics,
        "control_metrics": control,
        "state_counts": dict(sorted(state_counts.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "pf_at_least_control": (
            metrics["profit_factor"] is not None
            and control["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"]))
            >= Decimal(str(control["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(metrics["total_r"]))
            >= Decimal(str(control["total_r"]))
        ),
        "dd_below_control": (
            Decimal(str(metrics["max_drawdown_r"]))
            < Decimal(str(control["max_drawdown_r"]))
        ),
        "dd_at_or_below_6r": (
            Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    holdout_root: Path,
) -> tuple[dict[str, Any], tuple[GovernorDecision, ...]]:
    development = _load_role(
        development_root,
        expected_trades=EXPECTED_DEVELOPMENT_TRADES,
    )
    holdout = _load_role(
        holdout_root,
        expected_trades=EXPECTED_HOLDOUT_TRADES,
    )

    results: list[dict[str, Any]] = []
    audits: list[GovernorDecision] = []
    for policy in POLICIES:
        dev_result, dev_audit = _simulate(
            role="DEVELOPMENT",
            policy=policy,
            ledgers=development,
        )
        hold_result, hold_audit = _simulate(
            role="FRESH_HOLDOUT",
            policy=policy,
            ledgers=holdout,
        )
        results.append(
            {
                "policy": policy,
                "development": dev_result,
                "fresh_holdout": hold_result,
                "fresh_holdout_pareto_vs_control": (
                    bool(hold_result["pf_at_least_control"])
                    and bool(hold_result["total_r_at_least_control"])
                    and bool(hold_result["dd_below_control"])
                ),
                "fresh_holdout_full_gate": (
                    bool(hold_result["pf_at_least_control"])
                    and bool(hold_result["total_r_at_least_control"])
                    and bool(hold_result["dd_at_or_below_6r"])
                ),
            }
        )
        audits.extend(dev_audit)
        audits.extend(hold_audit)

    pareto = tuple(
        row for row in results if row["fresh_holdout_pareto_vs_control"]
    )
    full_gate = tuple(
        row for row in results if row["fresh_holdout_full_gate"]
    )

    return {
        "identity": IDENTITY,
        "source_direct_run_id": SOURCE_DIRECT_RUN_ID,
        "source_direct_sha": SOURCE_DIRECT_SHA,
        "development_role": "CONSUMED_RESEARCH",
        "holdout_role": "FRESH_NON_OVERLAPPING_HOLDOUT",
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "fresh_holdout_trades": EXPECTED_HOLDOUT_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "fresh_holdout_pareto_policy_count": len(pareto),
        "fresh_holdout_full_gate_policy_count": len(full_gate),
        "fixed_state_thresholds": {
            "watch_dd_r": str(WATCH_DD_R),
            "defensive_dd_r": str(DEFENSIVE_DD_R),
            "watch_recent5_r": str(WATCH_RECENT5_R),
            "defensive_recent5_r": str(DEFENSIVE_RECENT5_R),
            "watch_loss_streak": WATCH_LOSS_STREAK,
            "defensive_loss_streak": DEFENSIVE_LOSS_STREAK,
        },
        "thresholds_selected_from_holdout_outcomes": False,
        "same_policy_definitions_on_development_and_holdout": True,
        "all_entries_preserved": True,
        "current_trade_outcome_visible_to_decision": False,
        "open_trade_future_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed_at_entry": False,
        "target_changed": False,
        "max3_changed": False,
        "automatic_policy_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "ADD_REGIME_AND_DESTINATION_TO_STABILITY_STATE"
            if not full_gate
            else "FREEZE_GOVERNOR_AND_RUN_ADDITIONAL_TEMPORAL_STRESS"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[GovernorDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cross-market-stability-governor-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cross-market-stability-governor-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("holdout_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(args.development_root, args.holdout_root)
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
