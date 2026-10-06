"""VT31 NAS100 Comparator-010 neutral-destination adverse exit V1.

Consumed development evidence only. Fresh Holdout remains sealed.

Frozen base:
    VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR

Only new degree of freedom:
- on a fully closed M1, for Breaker/FVG positions still in the pretarget
  cognitive-management path, additionally authorize next-M1-open EXIT when:
    * maximum cognition is verified;
    * current_open_r <= the pre-existing material-adverse threshold (-0.50R);
    * management_context == MIXED;
    * destination_state == NEUTRAL.

No new numeric threshold is introduced. No outcome, fold/date identity, sizing,
leverage, compounding, portfolio or capital state can influence action.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live_cognition
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp010.neutral_destination_adverse_exit.v1"
COMPARATOR_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
VARIANT_ID = "VT31_AB_COMP010_BREAKER_FVG_NEUTRAL_DESTINATION_EXIT"

ENTRY_FAMILIES = frozenset({"breaker", "fair-value-gap"})


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _neutral_destination_exit_allowed(
    diagnostic: dict[str, object],
    *,
    entry_family: str,
) -> bool:
    if entry_family not in ENTRY_FAMILIES:
        return False
    if diagnostic.get("maximum_cognition_verified") is not True:
        return False
    if _d(diagnostic["current_open_r"]) > adverse.MATERIAL_ADVERSE_R:
        return False
    if str(diagnostic["management_context"]) != "MIXED":
        return False
    return str(diagnostic.get("destination_state")) == "NEUTRAL"


def _simulate_candidate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object]:
    evaluations: list[dict[str, object]] = []
    entry_family = str(executable.selected_family.value)
    reference_volatility_state = str(state["reference_volatility_state"])

    def exit_authorizer(
        bar: object,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, bar.closed_at)
        _, diagnostic = live_cognition._live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=observation_at,
            current_stop=current_stop,
            candidate_stop=current_stop,
            confirmations=1,
            mode="WEAK_PATH",
        )
        base_allowed = adverse._exit_allowed(
            diagnostic,
            variant=rapid.POSITION_VARIANT,
            entry_family=entry_family,
            reference_volatility_state=reference_volatility_state,
        )
        weak_allowed = weak._extra_exit_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        existing_allowed = base_allowed or weak_allowed
        neutral_allowed = _neutral_destination_exit_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        allowed = existing_allowed or neutral_allowed

        diagnostic["cognitive_exit_variant"] = VARIANT_ID
        diagnostic["cognitive_exit_authorized"] = allowed
        diagnostic["comp007_base_exit_authorized"] = base_allowed
        diagnostic["breaker_mixed_weak_efficiency_exit_authorized"] = (
            weak_allowed
        )
        diagnostic["neutral_destination_exit_authorized"] = neutral_allowed
        diagnostic["neutral_destination_exit_effective"] = (
            neutral_allowed and not existing_allowed
        )
        evaluations.append(diagnostic)
        return allowed

    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=adverse.WINDOW,
        pretarget_cognitive_exit_authorizer=exit_authorizer,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["cognitive_exit_variant"] = VARIANT_ID
        outcome["cognitive_exit_evaluations"] = evaluations
    return outcome


def _build_candidate_rows(
    evidence_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    original = specialist._simulate_selected_plan
    position_rows: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural

        outcome = _simulate_candidate(day_bars, executable, state)
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "Comparator-010 changed sovereign terminal eligibility: "
                f"{outcome}"
            )
        position_rows.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    if [str(row["signal_at"]) for row in position_rows] != structural_ids:
        raise AssertionError(
            "Comparator-010 changed sovereign terminal trade identity"
        )

    comp007_rows = weak._apply_comp007_admission(position_rows)
    candidate = [row for row in comp007_rows if not mid._conflict(row)]
    return structural_rows, candidate


def _changed_trade_forensics(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    baseline_map = {str(row["signal_at"]): row for row in baseline}
    candidate_map = {str(row["signal_at"]): row for row in candidate}
    if set(baseline_map) != set(candidate_map):
        raise AssertionError(
            "position-only Comparator-010 changed Comparator-009 trade identity"
        )

    changed: list[dict[str, object]] = []
    for signal_at in sorted(baseline_map):
        left = baseline_map[signal_at]
        right = candidate_map[signal_at]
        left_r = _d(left["r_multiple"])
        right_r = _d(right["r_multiple"])
        if left_r == right_r and left.get("exit_reason") == right.get(
            "exit_reason"
        ):
            continue

        events = cast(
            list[dict[str, object]],
            right.get("cognitive_exit_evaluations", []),
        )
        neutral_events = [
            event
            for event in events
            if event.get("neutral_destination_exit_effective") is True
        ]
        changed.append(
            {
                "signal_at": signal_at,
                "entry_family": right.get("entry_family"),
                "side": right.get("side"),
                "baseline_r": format(left_r, "f"),
                "candidate_r": format(right_r, "f"),
                "delta_r": format(right_r - left_r, "f"),
                "baseline_exit_reason": left.get("exit_reason"),
                "candidate_exit_reason": right.get("exit_reason"),
                "entry_context": right.get("entry_context", {}),
                "neutral_destination_effective_events": neutral_events,
            }
        )
    return changed


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    return admission._winner_preservation(baseline, candidate)


def _partition_report(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    baseline = pack._candidate_rows(evidence_path)
    structural, candidate = _build_candidate_rows(evidence_path)

    baseline_ids = [str(row["signal_at"]) for row in baseline]
    candidate_ids = [str(row["signal_at"]) for row in candidate]
    if baseline_ids != candidate_ids:
        raise AssertionError(
            "Comparator-010 must preserve Comparator-009 admitted trade identity"
        )

    eligible_dates, evidence = pack._eligible_dates(evidence_path)
    daily = pack._daily_series(candidate, eligible_dates)
    metrics = specialist._metrics(
        candidate,
        friction=pack.BASELINE_FRICTION_R,
    )
    baseline_metrics = specialist._metrics(
        baseline,
        friction=pack.BASELINE_FRICTION_R,
    )
    payoff = pack._payoff(candidate, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(daily)
    mc = specialist._monte_carlo(candidate)
    stress = pack._cost_stress(candidate)
    years = pack._year_totals(candidate)
    winner = _winner_preservation(baseline, candidate)
    changed = _changed_trade_forensics(baseline, candidate)

    gates = {
        "same_trade_identity_vs_comp009": baseline_ids == candidate_ids,
        "density_at_least_0_75": (
            Decimal(len(candidate)) / Decimal(len(baseline))
            >= Decimal("0.75")
        ),
        "winner_count_preservation_at_least_0_80": (
            _d(winner["winner_count_preservation"]) >= Decimal("0.80")
        ),
        "winner_r_preservation_at_least_0_90": (
            _d(winner["winner_r_preservation"]) >= Decimal("0.90")
        ),
        "pf_nondegrade_vs_comp009": (
            pack._pf_decimal(metrics) >= pack._pf_decimal(baseline_metrics)
        ),
        "mean_nondegrade_vs_comp009": (
            _d(metrics["mean_r"]) >= _d(baseline_metrics["mean_r"])
        ),
        "dd_nondegrade_vs_comp009": (
            _d(metrics["max_drawdown_r"])
            <= _d(baseline_metrics["max_drawdown_r"])
        ),
        "era_pf_at_least_1_50": pack._pf_pass(
            metrics,
            pack.ERA_PF_MIN,
        ),
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"]) <= pack.OBSERVED_DD_MAX
        ),
    }

    return {
        "schema": SCHEMA,
        "mode": "partition",
        "partition": partition,
        "comparator_id": COMPARATOR_ID,
        "variant_id": VARIANT_ID,
        "policy_fingerprint_base": pack.policy_fingerprint(),
        "baseline_trade_count": len(baseline),
        "structural_trade_count": len(structural),
        "candidate_trade_count": len(candidate),
        "baseline_metrics": baseline_metrics,
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "monte_carlo": mc,
        "cost_stress": stress,
        "year_total_r": years,
        "halfyear_stress": specialist._block_metrics(
            candidate,
            halfyear=True,
        ),
        "winner_preservation_vs_comp009": winner,
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "neutral_destination_effective_exit_count": sum(
            len(
                cast(
                    list[dict[str, object]],
                    item["neutral_destination_effective_events"],
                )
            )
            for item in changed
        ),
        "eligible_dates": eligible_dates,
        "daily_series": daily,
        "candidate_rows": pack._minimal_rows(candidate),
        "evidence": evidence,
        "gates": gates,
        "partition_pass": all(gates.values()),
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "base_is_frozen_comp009": True,
            "same_comp009_admission": True,
            "same_comp009_position_stack_until_new_exit": True,
            "entry_family_scope_breaker_fvg_only": True,
            "order_block_explicitly_unchanged": True,
            "maximum_cognition_required": True,
            "material_adverse_threshold_preexisting": True,
            "destination_state_existing_categorical_state": True,
            "new_numeric_threshold_added": False,
            "next_m1_open_execution": True,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _aggregate(reports: list[dict[str, object]]) -> dict[str, object]:
    required = {"r5", "r6", "r8", "consumed"}
    by_partition = {
        str(report["partition"]): report
        for report in reports
    }
    if set(by_partition) != required:
        raise AssertionError(
            f"expected partitions {sorted(required)}, got {sorted(by_partition)}"
        )

    fingerprints = {
        str(report["policy_fingerprint_base"])
        for report in reports
    }
    if fingerprints != {pack.policy_fingerprint()}:
        raise AssertionError("Comparator-009 policy fingerprint drift")

    rows = [
        cast(dict[str, object], row)
        for partition in ("r5", "r6", "r8", "consumed")
        for row in cast(
            list[dict[str, object]],
            by_partition[partition]["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    signal_ids = [str(row["signal_at"]) for row in rows]
    if len(signal_ids) != len(set(signal_ids)):
        raise AssertionError("candidate signal identities overlap across folds")

    daily = [
        cast(dict[str, str], item)
        for partition in ("r5", "r6", "r8", "consumed")
        for item in cast(
            list[dict[str, str]],
            by_partition[partition]["daily_series"],
        )
    ]
    daily.sort(key=lambda item: item["local_date"])
    daily_dates = [item["local_date"] for item in daily]
    if len(daily_dates) != len(set(daily_dates)):
        raise AssertionError("eligible session dates overlap across folds")

    metrics = specialist._metrics(
        rows,
        friction=pack.BASELINE_FRICTION_R,
    )
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(daily)
    mc = specialist._monte_carlo(rows)
    stress = pack._cost_stress(rows)
    years = pack._year_totals(rows)
    drawdown = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    per_partition_pass = all(
        bool(by_partition[name]["partition_pass"])
        for name in required
    )
    winner_count_ok = all(
        _d(
            cast(
                dict[str, object],
                by_partition[name]["winner_preservation_vs_comp009"],
            )["winner_count_preservation"]
        )
        >= Decimal("0.80")
        for name in required
    )
    winner_r_ok = all(
        _d(
            cast(
                dict[str, object],
                by_partition[name]["winner_preservation_vs_comp009"],
            )["winner_r_preservation"]
        )
        >= Decimal("0.90")
        for name in required
    )
    density_ok = all(
        int(by_partition[name]["candidate_trade_count"])
        * 4
        >= int(by_partition[name]["baseline_trade_count"])
        * 3
        for name in required
    )

    gates = {
        "all_partition_gates_pass": per_partition_pass,
        "no_signal_overlap_across_folds": True,
        "no_eligible_session_overlap_across_folds": True,
        "density_at_least_0_75_all_partitions": density_ok,
        "winner_count_preservation_at_least_0_80_all_partitions": (
            winner_count_ok
        ),
        "winner_r_preservation_at_least_0_90_all_partitions": winner_r_ok,
        "all_fold_pf_at_least_1_50": all(
            pack._pf_pass(
                cast(dict[str, object], by_partition[name]["metrics"]),
                pack.ERA_PF_MIN,
            )
            for name in required
        ),
        "all_fold_observed_dd_at_most_6r": all(
            _d(
                cast(dict[str, object], by_partition[name]["metrics"])[
                    "max_drawdown_r"
                ]
            )
            <= pack.OBSERVED_DD_MAX
            for name in required
        ),
        "combined_pf_at_least_1_70": pack._pf_pass(
            metrics,
            pack.COMBINED_PF_MIN,
        ),
        "combined_expectancy_positive": _d(metrics["mean_r"]) > 0,
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= pack.PAYOFF_MIN
        ),
        "stitched_observed_dd_at_most_6r": (
            _d(drawdown["max_drawdown_r"]) <= pack.OBSERVED_DD_MAX
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= pack.SHARPE_MIN
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= pack.SORTINO_MIN
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"])
            >= pack.MC_POSITIVE_MIN
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= pack.MC_P95_DD_MAX
        ),
        "degraded_0_10r_pf_gt_1": pack._pf_gt(
            stress["0.10"],
            Decimal(1),
        ),
    }

    changed = [
        {
            "partition": partition,
            **cast(dict[str, object], item),
        }
        for partition in ("r5", "r6", "r8", "consumed")
        for item in cast(
            list[dict[str, object]],
            by_partition[partition]["changed_trade_forensics"],
        )
    ]

    return {
        "schema": SCHEMA,
        "mode": "aggregate",
        "comparator_id": COMPARATOR_ID,
        "variant_id": VARIANT_ID,
        "policy_fingerprint_base": pack.policy_fingerprint(),
        "partitions": {
            name: {
                "partition_pass": by_partition[name]["partition_pass"],
                "baseline_trade_count": by_partition[name][
                    "baseline_trade_count"
                ],
                "candidate_trade_count": by_partition[name][
                    "candidate_trade_count"
                ],
                "baseline_metrics": by_partition[name]["baseline_metrics"],
                "metrics": by_partition[name]["metrics"],
                "winner_preservation_vs_comp009": by_partition[name][
                    "winner_preservation_vs_comp009"
                ],
                "changed_trade_count": by_partition[name][
                    "changed_trade_count"
                ],
                "neutral_destination_effective_exit_count": (
                    by_partition[name][
                        "neutral_destination_effective_exit_count"
                    ]
                ),
            }
            for name in ("r5", "r6", "r8", "consumed")
        },
        "combined": {
            "trade_count": len(rows),
            "metrics": metrics,
            "payoff_ratio": (
                None if payoff is None else format(payoff, "f")
            ),
            "risk_adjusted": risk,
            "monte_carlo": mc,
            "cost_stress": stress,
            "year_total_r": years,
            "drawdown_episode": drawdown,
        },
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "gates": gates,
        "comparator010_survivor": all(gates.values()),
        "fresh_holdout_opened": False,
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "single_predeclared_hypothesis": True,
            "new_numeric_threshold_added": False,
            "next_m1_open_execution": True,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    partition_parser = sub.add_parser("partition")
    partition_parser.add_argument("evidence", type=Path)
    partition_parser.add_argument("--partition", required=True)
    partition_parser.add_argument("--output", required=True, type=Path)

    aggregate_parser = sub.add_parser("aggregate")
    aggregate_parser.add_argument("reports", nargs="+", type=Path)
    aggregate_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "partition":
        payload = _partition_report(
            args.evidence,
            partition=args.partition,
        )
    else:
        payload = _aggregate(
            [
                json.loads(path.read_text(encoding="utf-8"))
                for path in args.reports
            ]
        )
    _write(args.output, payload)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
