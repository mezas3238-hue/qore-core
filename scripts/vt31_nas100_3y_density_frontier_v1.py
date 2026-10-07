#!/usr/bin/env python3
"""Causal admission-density ablation frontier for the owner-designated VT31 3Y base.

This is a research-only diagnostic. It does not promote any relaxed admission
rule. Each variant keeps the exact same causal inputs and full reasoning output,
then demotes one or more pre-entry contradictions from hard veto to context so
we can measure the density/economic cost of the historical admission gates.

No sizing, leverage, compounding, portfolio weighting, date labels, outcomes,
or future information are used in the action decision.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp010_live_context_adverse_exit_v1 as current
import vt31_nas100_specialist_r1_candidate as specialist

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SCHEMA = "qore.vt31.nas100.owner_3y_density_frontier.v1"
TARGET_TRADES = 450

PATH_NOT_COMPRESSED = "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
LOW_DD_REFERENCE = "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE"
TOO_LATE = "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE"
NO_REFERENCE_LIQUIDITY = "SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF"

TRANSIENT_WAIT = frozenset(
    {
        "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
        "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
    }
)

VARIANTS: dict[str, frozenset[str]] = {
    "CURRENT": frozenset(),
    "RELAX_PATH_COMPRESSION": frozenset({PATH_NOT_COMPRESSED}),
    "RELAX_LOW_DD_REFERENCE": frozenset({LOW_DD_REFERENCE}),
    "RELAX_LATE_ENTRY": frozenset({TOO_LATE}),
    "RELAX_REFERENCE_LIQUIDITY_CUTOFF": frozenset(
        {NO_REFERENCE_LIQUIDITY}
    ),
    "RELAX_PATH_AND_REFERENCE_GATE": frozenset(
        {PATH_NOT_COMPRESSED, LOW_DD_REFERENCE}
    ),
    "RELAX_LIQUIDITY_AND_LATE": frozenset(
        {NO_REFERENCE_LIQUIDITY, TOO_LATE}
    ),
    "RELAX_ALL_FOUR": frozenset(
        {
            PATH_NOT_COMPRESSED,
            LOW_DD_REFERENCE,
            TOO_LATE,
            NO_REFERENCE_LIQUIDITY,
        }
    ),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


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


def _evaluate(
    evidence_raw: str,
    name: str,
    ignored: frozenset[str],
) -> tuple[str, dict[str, object]]:
    evidence_path = Path(evidence_raw)
    original_reason = specialist.reason
    contradiction_counts: Counter[str] = Counter()
    uncertainty_counts: Counter[str] = Counter()
    demoted_counts: Counter[str] = Counter()

    def ablated_reason(
        state: object,
        *,
        apply_comp008_admission: bool = False,
    ) -> object:
        raw = original_reason(
            state,
            apply_comp008_admission=apply_comp008_admission,
        )
        contradiction_counts.update(raw.contradictions)
        uncertainty_counts.update(raw.uncertainty)

        kept = tuple(
            code for code in raw.contradictions if code not in ignored
        )
        removed = tuple(
            code for code in raw.contradictions if code in ignored
        )
        demoted_counts.update(removed)

        if kept:
            action = "ABSTAIN"
        elif any(code in TRANSIENT_WAIT for code in raw.uncertainty):
            action = "WAIT"
        else:
            action = "EXECUTE"

        context = list(raw.context_observations)
        context.extend(
            f"DENSITY_ABLATION:DEMOTED_ADMISSION_CONTRADICTION={code}"
            for code in removed
        )
        return replace(
            raw,
            action=action,
            contradictions=kept,
            context_observations=tuple(context),
        )

    specialist.reason = ablated_reason
    try:
        structural_rows, position_rows = current._build_variant_rows(
            evidence_path
        )
    finally:
        specialist.reason = original_reason

    rows = position_rows[current.LAB_CONTROL_ALIAS]
    metrics = specialist._metrics(rows, friction=specialist.FRICTION)
    result: dict[str, object] = {
        "variant": name,
        "ignored_admission_contradictions": sorted(ignored),
        "structural_terminal_count": len(structural_rows),
        "admitted_trade_count": len(rows),
        "admission_rejection_count": len(structural_rows) - len(rows),
        "gap_to_450": TARGET_TRADES - len(rows),
        "target_fraction": format(
            Decimal(len(rows)) / Decimal(TARGET_TRADES),
            "f",
        ),
        "stress_0_05r": metrics,
        "contradiction_observation_counts": dict(
            sorted(contradiction_counts.items())
        ),
        "uncertainty_observation_counts": dict(
            sorted(uncertainty_counts.items())
        ),
        "demoted_contradiction_counts": dict(
            sorted(demoted_counts.items())
        ),
        "candidate_rows": _minimal_rows(rows),
        "governance": {
            "research_only": True,
            "single_contiguous_3y_base": True,
            "outcome_used_for_action": False,
            "date_identity_used_for_action": False,
            "fold_identity_used_for_action": False,
            "future_information_used_for_action": False,
            "same_causal_state_inputs_as_control": True,
            "full_reasoning_still_executed": True,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "policy_promoted": False,
            "candidate_certified": False,
        },
    }
    return name, result


def _new_trade_quality(
    control: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    control_rows = {
        str(row["signal_at"]): row
        for row in cast(list[dict[str, object]], control["candidate_rows"])
    }
    candidate_rows = {
        str(row["signal_at"]): row
        for row in cast(list[dict[str, object]], candidate["candidate_rows"])
    }
    added_ids = sorted(set(candidate_rows) - set(control_rows))
    removed_ids = sorted(set(control_rows) - set(candidate_rows))
    added = [candidate_rows[item] for item in added_ids]
    if added:
        metrics = specialist._metrics(
            added,
            friction=specialist.FRICTION,
        )
    else:
        metrics = None
    return {
        "added_trade_count": len(added_ids),
        "removed_control_trade_count": len(removed_ids),
        "added_trade_metrics_0_05r": metrics,
        "added_trade_rows": added,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if evidence.get("base_id") != BASE_ID:
        raise SystemExit("unexpected owner 3Y base identity")
    if evidence.get("legacy_r5_r6_r8_operating_folds_used") is not False:
        raise SystemExit("legacy R5/R6/R8 operating folds are forbidden")

    max_workers = min(
        len(VARIANTS),
        max(1, os.cpu_count() or 1),
    )
    results: dict[str, dict[str, object]] = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _evaluate,
                str(args.evidence),
                name,
                ignored,
            ): name
            for name, ignored in VARIANTS.items()
        }
        for future in as_completed(futures):
            name, result = future.result()
            results[name] = result

    control = results["CURRENT"]
    if int(control["admitted_trade_count"]) != 55:
        raise AssertionError(
            "3Y density control drifted from verified 55-trade baseline"
        )

    for _name, result in results.items():
        result["delta_admitted_trades_vs_current"] = (
            int(result["admitted_trade_count"])
            - int(control["admitted_trade_count"])
        )
        result["new_trade_quality_vs_current"] = _new_trade_quality(
            control,
            result,
        )

    ordered = {
        name: results[name]
        for name in VARIANTS
    }
    ranking = sorted(
        (
            {
                "variant": name,
                "trade_count": int(item["admitted_trade_count"]),
                "delta_vs_current": int(
                    item["delta_admitted_trades_vs_current"]
                ),
                "pf_0_05r": cast(
                    dict[str, object],
                    item["stress_0_05r"],
                )["profit_factor"],
                "mean_r_0_05r": cast(
                    dict[str, object],
                    item["stress_0_05r"],
                )["mean_r"],
                "max_dd_r_0_05r": cast(
                    dict[str, object],
                    item["stress_0_05r"],
                )["max_drawdown_r"],
            }
            for name, item in ordered.items()
        ),
        key=lambda row: (
            -int(row["trade_count"]),
            -_d(row["mean_r_0_05r"]),
        ),
    )

    payload = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "target_trades_3y": TARGET_TRADES,
        "control_trade_count": int(control["admitted_trade_count"]),
        "variants": ordered,
        "density_ranking": ranking,
        "governance": {
            "research_only": True,
            "single_contiguous_3y_base": True,
            "legacy_r5_r6_r8_operating_folds_used": False,
            "ablation_only_no_policy_promotion": True,
            "outcome_aware_action": False,
            "sizing_or_leverage_rescue": False,
            "candidate_certified": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "base_id": BASE_ID,
                "target_trades_3y": TARGET_TRADES,
                "density_ranking": ranking,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
