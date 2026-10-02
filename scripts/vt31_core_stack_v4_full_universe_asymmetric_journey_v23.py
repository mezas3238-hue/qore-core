"""VT31 Shared full-universe asymmetric journey defense laboratory V23.

V22 preserved trade count but inherited V18 preparation, which reconstructed
post-fill journey events only for opportunities retained by the older V15 entry
selector. That meant a material part of the methodology-valid universe had no
Shared journey observations even though density was reported as 100%.

V23 removes that inherited blind spot. Every R8/R6 methodology-valid trade is
reconstructed and observed. Shared never abstains at entry. Defense is allowed
only from causal market/environment evidence plus the CURRENT position path;
terminal outcome, future M1, PnL history, risk weighting and sizing are absent.

The semantic hypothesis is asymmetric:
- adverse market context alone is not enough to defend;
- current position progress must also be non-supportive;
- stronger policies additionally require a terminal trajectory sequence and
  negative path efficiency/body evidence.

R8/R6 remain consumed research folds. R5 and fresh holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_adverse_environment_journey_only_v22 as v22

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryState,
)

SCHEMA = "qore.core_stack_v4.vt31.full_universe_asymmetric_journey.v23"
IDENTITY = "VT31_NAS100_SHARED_FULL_UNIVERSE_ASYMMETRIC_JOURNEY_V23"
ZERO = Decimal("0")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
v18 = v22.v21.v20.v19.v18


@dataclass(frozen=True, slots=True)
class AsymmetricJourneyPolicy:
    name: str
    environment_states: frozenset[MarketEnvironmentState]
    trajectory_states: frozenset[MarketTrajectoryState]
    require_deteriorating_to_failure: bool = False
    require_close_nonpositive: bool = True
    require_efficiency_nonpositive: bool = False
    require_body_nonpositive: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "environment_states": tuple(sorted(x.value for x in self.environment_states)),
            "trajectory_states": tuple(sorted(x.value for x in self.trajectory_states)),
            "require_deteriorating_to_failure": self.require_deteriorating_to_failure,
            "require_close_nonpositive": self.require_close_nonpositive,
            "require_efficiency_nonpositive": self.require_efficiency_nonpositive,
            "require_body_nonpositive": self.require_body_nonpositive,
            "entry_abstention_allowed": False,
            "numeric_threshold_grid_search": False,
        }


POLICIES = (
    AsymmetricJourneyPolicy(
        "DEFENSIVE_NONPOSITIVE",
        frozenset({MarketEnvironmentState.DEFENSIVE}),
        frozenset(
            {
                MarketTrajectoryState.DETERIORATING,
                MarketTrajectoryState.FAILURE,
            }
        ),
    ),
    AsymmetricJourneyPolicy(
        "ADVERSE_FAILURE_NONPOSITIVE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
    ),
    AsymmetricJourneyPolicy(
        "ADVERSE_DTF_NONPOSITIVE",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
        require_deteriorating_to_failure=True,
    ),
    AsymmetricJourneyPolicy(
        "ADVERSE_FAILURE_NEGATIVE_FLOW",
        frozenset(
            {
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset({MarketTrajectoryState.FAILURE}),
        require_efficiency_nonpositive=True,
        require_body_nonpositive=True,
    ),
    AsymmetricJourneyPolicy(
        "DEGRADING_MULTIAXIS_BREAK",
        frozenset(
            {
                MarketEnvironmentState.DEGRADING,
                MarketEnvironmentState.ADVERSE_FORMING,
                MarketEnvironmentState.DEFENSIVE,
            }
        ),
        frozenset(
            {
                MarketTrajectoryState.DETERIORATING,
                MarketTrajectoryState.FAILURE,
            }
        ),
        require_efficiency_nonpositive=True,
        require_body_nonpositive=True,
    ),
    AsymmetricJourneyPolicy(
        "DEFENSIVE_DTF_NEGATIVE_FLOW",
        frozenset({MarketEnvironmentState.DEFENSIVE}),
        frozenset({MarketTrajectoryState.FAILURE}),
        require_deteriorating_to_failure=True,
        require_efficiency_nonpositive=True,
        require_body_nonpositive=True,
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _prepare_full_universe(
    rows: list[dict[str, object]],
    *,
    nas_evidence: Path,
    sp_evidence: Path,
    us_evidence: Path,
) -> list[dict[str, object]]:
    """Reconstruct post-fill events for every methodology-valid opportunity."""
    paths = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        v18.journey._reconstruct_partition(nas_evidence),
    )
    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)

    prepared: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = _d(row["net_r_after_friction"])
        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, exit_index = v18.counter._fill_and_exit_indices(
            setup,
            day_bars,
            row,
        )
        side = cast(str, row["side"])
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        events: list[dict[str, object]] = []

        for snapshot_index in range(fill_index + 1, exit_index):
            _, _, state = v18.counter._state_signature(
                row=row,
                bars=list(day_bars),
                setup=setup,
                fill_index=fill_index,
                current_index=snapshot_index,
            )
            defense = v18.counter._defend_counterfactual(
                setup=setup,
                day_bars=day_bars,
                snapshot_index=snapshot_index,
            )
            if defense is None:
                continue

            snapshot_bar = day_bars[snapshot_index]
            decision_at = cast(object, snapshot_bar).closed_at
            nas_observed = tuple(day_bars[fill_index : snapshot_index + 1])
            sp = v18.v13._eligible(sp_by_day, local_day, decision_at)
            us = v18.v13._eligible(us_by_day, local_day, decision_at)
            nas3 = v18.v13._signed_move(nas_observed, side=side, window=3)
            nas10 = v18.v13._signed_move(nas_observed, side=side, window=10)
            sp3 = v18.v13._signed_move(sp, side=side, window=3)
            sp10 = v18.v13._signed_move(sp, side=side, window=10)
            us3 = v18.v13._signed_move(us, side=side, window=3)
            us10 = v18.v13._signed_move(us, side=side, window=10)
            events.append(
                {
                    **state,
                    "peer_sync3": v18.v13._sync(sp3, us3),
                    "breadth3": v18.v13._breadth((nas3, sp3, us3)),
                    "breadth10": v18.v13._breadth((nas10, sp10, us10)),
                    "sp500_transition": v18.v13._transition(sp3, sp10),
                    "us30_transition": v18.v13._transition(us3, us10),
                    "defense_r_after_friction": format(
                        defense - v18.FRICTION,
                        "f",
                    ),
                }
            )

        prepared.append(
            {
                "row": row,
                "baseline_r": baseline_r,
                "entry_keep": True,
                "events": events,
            }
        )
    return prepared


def _matches(
    event: dict[str, object],
    policy: AsymmetricJourneyPolicy,
) -> bool:
    environment = MarketEnvironmentState(str(event["environment_state"]))
    if environment not in policy.environment_states:
        return False

    trajectory = MarketTrajectoryState(str(event["trajectory_state"]))
    if trajectory not in policy.trajectory_states:
        return False

    if policy.require_deteriorating_to_failure:
        history = tuple(str(x) for x in cast(object, event["trajectory_state_history"]))
        if len(history) < 2 or history[-2:] != ("DETERIORATING", "FAILURE"):
            return False

    if policy.require_close_nonpositive and _d(event["close_r"]) > ZERO:
        return False
    if policy.require_efficiency_nonpositive and _d(event["efficiency"]) > ZERO:
        return False
    if policy.require_body_nonpositive and _d(event["signed_body_r"]) > ZERO:
        return False
    return True


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v22._metrics(values)


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: AsymmetricJourneyPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    defended: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        shared_r = baseline_r

        for event in cast(list[dict[str, object]], item["events"]):
            if not _matches(event, policy):
                continue
            shared_r = _d(event["defense_r_after_friction"])
            defended.append(
                {
                    "signal_at": row["signal_at"],
                    "baseline_r": format(baseline_r, "f"),
                    "defense_r": format(shared_r, "f"),
                    "uplift_r": format(shared_r - baseline_r, "f"),
                    "minutes_since_fill": event["minutes_since_fill"],
                    "close_r": event["close_r"],
                    "efficiency": event["efficiency"],
                    "signed_body_r": event["signed_body_r"],
                    "environment_state": event["environment_state"],
                    "trajectory_state": event["trajectory_state"],
                    "trajectory_state_history": event["trajectory_state_history"],
                    "environment_adverse_bps": event["environment_adverse_bps"],
                    "environment_adverse_persistence_bps": event[
                        "environment_adverse_persistence_bps"
                    ],
                }
            )
            break
        shared_values.append(shared_r)

    baseline = _metrics(baseline_values)
    shared = _metrics(shared_values)
    defended_losers = [
        item for item in defended if _d(item["baseline_r"]) < ZERO
    ]
    defended_winners = [
        item for item in defended if _d(item["baseline_r"]) > ZERO
    ]
    baseline_winner_r = _d(baseline["gross_winner_r"])
    shared_winner_r = _d(shared["gross_winner_r"])
    winner_r_retention = (
        Decimal("1")
        if baseline_winner_r == ZERO
        else shared_winner_r / baseline_winner_r
    )
    loser_uplift = sum(
        (_d(item["uplift_r"]) for item in defended_losers),
        ZERO,
    )
    winner_damage = -min(
        ZERO,
        sum((_d(item["uplift_r"]) for item in defended_winners), ZERO),
    )
    base_losses = int(baseline["losses"])

    return {
        "baseline": baseline,
        "shared_v23": shared,
        "density": {
            "input": len(baseline_values),
            "kept": len(shared_values),
            "retained": "1",
            "entry_abstentions": 0,
            "all_trades_received_journey_reconstruction": all(
                bool(cast(list[dict[str, object]], item["events"]))
                for item in prepared
            ),
            "trades_with_journey_events": sum(
                bool(cast(list[dict[str, object]], item["events"]))
                for item in prepared
            ),
        },
        "journey": {
            "defended_trades": len(defended),
            "defended_baseline_losses": len(defended_losers),
            "defended_baseline_winners": len(defended_winners),
            "baseline_loss_defense_recall": (
                "0"
                if base_losses == 0
                else format(Decimal(len(defended_losers)) / Decimal(base_losses), "f")
            ),
            "loser_uplift_r": format(loser_uplift, "f"),
            "winner_damage_r": format(winner_damage, "f"),
            "winner_r_retention": format(winner_r_retention, "f"),
            "net_journey_uplift_r": format(
                sum((_d(item["uplift_r"]) for item in defended), ZERO),
                "f",
            ),
            "best_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v23"])
    journey = cast(dict[str, object], result["journey"])
    density = cast(dict[str, object], result["density"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    baseline_pf = _d(baseline["profit_factor"])
    shared_pf = _d(shared["profit_factor"])
    dd = _d(shared["max_drawdown_r"])
    return {
        "profit_factor_above_baseline": shared_pf > baseline_pf,
        "profit_factor_plus_25pct": shared_pf >= baseline_pf * Decimal("1.25"),
        "drawdown_at_most_6r": dd <= DD_ACCEPTABLE_MAX_R,
        "drawdown_below_4r_exceptional": dd < DD_EXCEPTIONAL_R,
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "density_exactly_preserved": density["retained"] == "1",
        "entry_abstentions_zero": density["entry_abstentions"] == 0,
        "winner_r_retention_at_least_95pct": (
            _d(journey["winner_r_retention"]) >= Decimal("0.95")
        ),
    }


def _hard_pass(gates: dict[str, bool]) -> bool:
    required = (
        "profit_factor_above_baseline",
        "profit_factor_plus_25pct",
        "drawdown_at_most_6r",
        "total_r_not_lower",
        "density_exactly_preserved",
        "entry_abstentions_zero",
        "winner_r_retention_at_least_95pct",
    )
    return all(gates.get(key, False) for key in required)


def _diagnostic_score(result: dict[str, object]) -> Decimal:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v23"])
    journey = cast(dict[str, object], result["journey"])
    baseline_pf = max(_d(baseline["profit_factor"]), Decimal("0.000001"))
    shared_pf = _d(shared["profit_factor"])
    baseline_dd = max(_d(baseline["max_drawdown_r"]), Decimal("0.000001"))
    shared_dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        shared_pf
        / baseline_pf
        * baseline_dd
        / shared_dd
        * _d(journey["winner_r_retention"])
        * (Decimal("1") + _d(journey["baseline_loss_defense_recall"]))
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "full_methodology_valid_universe_reconstructed": True,
        "v15_entry_selection_used_for_journey_availability": False,
        "shared_generic_environment_engine_used": True,
        "journey_only_no_entry_abstention": True,
        "density_preservation_is_hard_gate": True,
        "current_position_path_used_causally": True,
        "runtime_terminal_trade_outcome_used": False,
        "runtime_prior_trade_pnl_used": False,
        "runtime_prior_loss_streak_used": False,
        "future_m1_used": False,
        "r5_opened": False,
        "new_holdout_opened": False,
        "capital_risk_weighting_used": False,
        "methodology_entry_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "stop_widening_used": False,
        "live_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8 = _prepare_full_universe(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6 = _prepare_full_universe(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    a8, trajectory_r8 = v22.v21.v20.v19._annotate_trajectory(p8)
    a6, trajectory_r6 = v22.v21.v20.v19._annotate_trajectory(p6)
    h8 = v22.v21._with_state_history(a8)
    h6 = v22.v21._with_state_history(a6)
    e8, environment_r8 = v22._annotate_environment(h8)
    e6, environment_r6 = v22._annotate_environment(h6)

    results: list[dict[str, object]] = []
    passing: list[tuple[Decimal, AsymmetricJourneyPolicy]] = []
    for policy in POLICIES:
        r8_result = _evaluate(e8, policy=policy)
        r6_result = _evaluate(e6, policy=policy)
        g8 = _gates(r8_result)
        g6 = _gates(r6_result)
        passed = _hard_pass(g8) and _hard_pass(g6)
        score = (
            _diagnostic_score(r8_result) + _diagnostic_score(r6_result)
        ) / Decimal("2")
        results.append(
            {
                "policy": policy.payload(),
                "r8": {"evaluation": r8_result, "gates": g8},
                "r6": {"evaluation": r6_result, "gates": g6},
                "passes_both_consumed_folds": passed,
                "diagnostic_score": format(score, "f"),
            }
        )
        if passed:
            passing.append((score, policy))

    results.sort(key=lambda item: _d(item["diagnostic_score"]), reverse=True)
    frozen_policy: dict[str, object] | None = None
    if passing:
        passing.sort(key=lambda item: item[0], reverse=True)
        score, policy = passing[0]
        frozen_policy = {
            "journey_policy": policy.payload(),
            "generic_environment_defaults": "FROZEN_DEFAULTS",
            "joint_score": format(score, "f"),
            "density_retained": "1",
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED"
            if frozen_policy is not None
            else "FALSIFIED_BEFORE_NEW_HOLDOUT"
        ),
        "owner_objective": {
            "profit_factor_must_increase": True,
            "profit_factor_plus_25pct_reference_gate": True,
            "acceptable_drawdown_r": [4, 6],
            "exceptional_drawdown_r": "<4",
            "density_must_be_preserved": True,
        },
        "v22_blind_spot_corrected": {
            "description": (
                "V22 retained full trade count but V18 preparation omitted "
                "journey events for V15-rejected opportunities"
            ),
            "full_universe_journey_reconstruction_now_required": True,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": frozen_policy is not None,
        "frozen_policy": frozen_policy,
        "policy_results": results,
        "best_diagnostic_policy": None if not results else results[0]["policy"],
        "representation": {
            "trajectory_r8": trajectory_r8,
            "trajectory_r6": trajectory_r6,
            "environment_r8": environment_r8,
            "environment_r6": environment_r6,
            "entry_filtering_disabled": True,
            "density_preserved_by_design": True,
            "journey_reconstructed_for_full_universe": True,
        },
        "governance": _governance(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_calibration": payload["passes_calibration"],
                "frozen_policy": payload["frozen_policy"],
                "best_diagnostic_policy": payload["best_diagnostic_policy"],
                "v22_blind_spot_corrected": payload["v22_blind_spot_corrected"],
                "policy_results": payload["policy_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
