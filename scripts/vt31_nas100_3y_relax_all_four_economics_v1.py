#!/usr/bin/env python3
"""Economic replay of the only 3Y admission ablation with enough density capacity.

The owner target is approximately 450 real trades over the canonical contiguous
3Y NAS100 base. Single-pass admission mapping proved that every proper subset of
the four dominant historical hard vetoes selects at most 351 EXECUTE days and
therefore cannot reach the >=400 reasonable-density floor.

This frontier tests only RELAX_ALL_FOUR:
- SITUATION:CURRENT_PATH_NOT_COMPRESSED
- EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE
- EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE
- SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF

All four facts remain observed by full cognition. The experiment only demotes
them from hard pre-entry vetoes to context. No outcome, future bar, date/fold
identity, sizing, leverage, compounding, portfolio or capital state may affect
the decision.

The current post-entry position stack and current downstream Comparator-009
admission remain unchanged so the result measures real selected->terminal->
admitted attrition and economics.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_comp010_live_context_adverse_exit_v1 as current
import vt31_nas100_specialist_r1_candidate as specialist

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.nas100.owner_3y.relax_all_four_economics.v1"
VARIANT = "RELAX_ALL_FOUR"
TARGET_TRADES = 450
REASONABLE_DENSITY_FLOOR = 400

IGNORED = frozenset(
    {
        "SITUATION:CURRENT_PATH_NOT_COMPRESSED",
        "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE",
        "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE",
        "SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF",
    }
)
TRANSIENT_WAIT = frozenset(
    {
        "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
        "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
    }
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        wins = int(metrics["wins"])
        losses = int(metrics["losses"])
        if wins > 0 and losses == 0:
            return Decimal("Infinity")
        return Decimal("-Infinity")
    return _d(value)


def _minimal_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "local_date": row["local_date"],
            "entry_family": row.get("entry_family"),
            "side": row.get("side"),
            "exit_reason": row.get("exit_reason"),
            "r_multiple": row["r_multiple"],
        }
        for row in rows
    ]


def _year_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row["local_date"])[:4]] += 1
    return dict(sorted(counts.items()))


def _month_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row["local_date"])[:7]] += 1
    return dict(sorted(counts.items()))


def replay(evidence_path: Path) -> dict[str, object]:
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence_payload.get("base_id") != BASE_ID:
        raise ValueError("economic frontier requires canonical owner 3Y base")
    if evidence_payload.get("legacy_r5_r6_r8_operating_folds_used") is not False:
        raise ValueError("legacy R5/R6/R8 operating folds are forbidden")

    original_reason = specialist.reason
    original_simulator = specialist._simulate_selected_plan
    demoted_counts: Counter[str] = Counter()
    raw_contradiction_counts: Counter[str] = Counter()
    position_rows: list[dict[str, object]] = []

    def relaxed_reason(
        state: object,
        *,
        apply_comp008_admission: bool = False,
    ) -> object:
        raw = original_reason(
            state,
            apply_comp008_admission=apply_comp008_admission,
        )
        raw_contradiction_counts.update(raw.contradictions)
        kept = tuple(
            code for code in raw.contradictions if code not in IGNORED
        )
        demoted = tuple(
            code for code in raw.contradictions if code in IGNORED
        )
        demoted_counts.update(demoted)

        if kept:
            action = "ABSTAIN"
        elif any(code in TRANSIENT_WAIT for code in raw.uncertainty):
            action = "WAIT"
        else:
            action = "EXECUTE"

        context = list(raw.context_observations)
        context.extend(
            f"3Y_RELAX_ALL_FOUR:DEMOTED_ADMISSION_CONTRADICTION={code}"
            for code in demoted
        )
        return replace(
            raw,
            action=action,
            contradictions=kept,
            context_observations=tuple(context),
        )

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

        outcome = current._simulate_variant(
            day_bars,
            executable,
            state,
            variant=current.LAB_CONTROL_ALIAS,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "current position stack changed sovereign terminal eligibility"
            )
        position_rows.append(outcome)
        return structural

    specialist.reason = relaxed_reason
    specialist._simulate_selected_plan = simulator
    try:
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist.reason = original_reason
        specialist._simulate_selected_plan = original_simulator

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    position_ids = [str(row["signal_at"]) for row in position_rows]
    if structural_ids != position_ids:
        raise AssertionError(
            "position stack changed structural terminal trade identity"
        )

    admitted = current._apply_comp009_admission(position_rows)
    eligible_dates = current._eligible_dates(evidence_path)
    metrics = specialist._metrics(
        admitted,
        friction=pack.BASELINE_FRICTION_R,
    )
    payoff = pack._payoff(admitted, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(
        pack._daily_series(admitted, eligible_dates)
    )
    mc = specialist._monte_carlo(admitted)
    stress = pack._cost_stress(admitted)
    dd = pack._drawdown_episode(admitted, pack.BASELINE_FRICTION_R)

    reasoning_trace = cast(
        list[dict[str, object]],
        base_payload["reasoning_trace"],
    )
    action_counts = Counter(
        str(row.get("action", "UNKNOWN"))
        for row in reasoning_trace
    )
    selected_execute_count = action_counts["EXECUTE"]

    status_counts = cast(dict[str, int], base_payload["status_counts"])
    structural_terminal_count = len(structural_rows)
    admitted_count = len(admitted)
    downstream_removed_count = structural_terminal_count - admitted_count

    gates = {
        "reasonable_density_at_least_400_trades": (
            admitted_count >= REASONABLE_DENSITY_FLOOR
        ),
        "observed_dd_at_most_6r": (
            _d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "pf_at_least_1_50": _pf(metrics) >= Decimal("1.50"),
        "expectancy_at_least_0_15r": (
            _d(metrics["mean_r"]) >= Decimal("0.15")
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= Decimal("1.20")
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= Decimal("1.50")
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= Decimal("2.00")
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
        ),
        "degraded_0_10r_pf_gt_1": (
            _pf(cast(dict[str, object], stress["0.10"])) > Decimal("1")
        ),
    }

    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "variant": VARIANT,
        "ignored_admission_contradictions": sorted(IGNORED),
        "selection": {
            "selected_execute_days": selected_execute_count,
            "expected_from_selection_map": 609,
            "selection_map_parity": selected_execute_count == 609,
            "reasoning_action_counts": dict(sorted(action_counts.items())),
            "raw_contradiction_observation_counts": dict(
                sorted(raw_contradiction_counts.items())
            ),
            "demoted_contradiction_observation_counts": dict(
                sorted(demoted_counts.items())
            ),
        },
        "attrition": {
            "selected_execute_days": selected_execute_count,
            "structural_terminal_trades": structural_terminal_count,
            "selected_to_terminal_rate": (
                "0"
                if selected_execute_count == 0
                else format(
                    Decimal(structural_terminal_count)
                    / Decimal(selected_execute_count),
                    "f",
                )
            ),
            "downstream_comp009_removed": downstream_removed_count,
            "admitted_trade_count": admitted_count,
            "terminal_to_admitted_rate": (
                "0"
                if structural_terminal_count == 0
                else format(
                    Decimal(admitted_count)
                    / Decimal(structural_terminal_count),
                    "f",
                )
            ),
            "selected_to_admitted_rate": (
                "0"
                if selected_execute_count == 0
                else format(
                    Decimal(admitted_count)
                    / Decimal(selected_execute_count),
                    "f",
                )
            ),
            "target_trades_3y": TARGET_TRADES,
            "reasonable_density_floor": REASONABLE_DENSITY_FLOOR,
            "gap_to_450": TARGET_TRADES - admitted_count,
            "status_counts": status_counts,
            "trades_by_year": _year_counts(admitted),
            "trades_by_month": _month_counts(admitted),
        },
        "economics": {
            "stress_0_05r": metrics,
            "payoff_ratio": (
                None if payoff is None else format(payoff, "f")
            ),
            "risk_adjusted": risk,
            "monte_carlo": mc,
            "cost_stress": stress,
            "drawdown_episode": dd,
        },
        "gates": gates,
        "certification_gate_pass": all(gates.values()),
        "candidate_rows": _minimal_rows(admitted),
        "governance": {
            "research_only": True,
            "single_contiguous_3y_base": True,
            "legacy_r5_r6_r8_operating_folds_used": False,
            "same_full_cognition_inputs": True,
            "only_four_historical_admission_vetoes_demoted": True,
            "current_post_entry_position_stack_preserved": True,
            "current_downstream_comp009_admission_preserved": True,
            "outcome_used_for_action": False,
            "future_information_used_for_action": False,
            "date_or_fold_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variant": VARIANT,
                "selection": payload["selection"],
                "attrition": payload["attrition"],
                "economics": payload["economics"],
                "gates": payload["gates"],
                "certification_gate_pass": payload[
                    "certification_gate_pass"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
