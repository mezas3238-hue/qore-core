"""VT31 NAS100 Breaker rotation recovery-exception frontier V1.

Consumed-evidence development only.

Fixed B-side comparator:
    VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT

Tests a causal exception to the previously tested Breaker-short / prior-day
rotation / compressed-reference abstention rule. The exception keeps trades
whose entry-time state shows the pre-existing bullish recovery sequence:
H1 bullish + M15 mixed + premarket bullish + cash-open rotation + reclaim <8m.

No outcome, fold/date identity, sizing, leverage, compounding or capital state
can influence action.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.breaker_rotation_recovery_exception_frontier.v1"
ADMISSION_BASE = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
COMPARATOR_ID = "VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT"
POSITION_VARIANT = "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL"
LIVE_POSITION_VARIANTS = (
    "COMP003_PLUS_MIXED_DEEP_ADVERSE",
    "COMP003_PLUS_BREAKER_MIXED_DEEP_ADVERSE",
)

VARIANTS = (
    "COMP003_CONTROL",
    "ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED_EXCEPT_BULLISH_RECOVERY_SEQUENCE",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _base_breaker_rotation_compressed(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "rotation"
        and str(context.get("reference_volatility_state")) == "compressed"
    )


def _bullish_recovery_sequence(row: dict[str, object]) -> bool:
    context = cast(dict[str, object], row.get("entry_context", {}))
    reclaim = context.get("reference_reclaim_age_minutes")
    return (
        str(context.get("h1_state")) == "bullish"
        and str(context.get("m15_state")) == "mixed"
        and str(context.get("premarket_state")) == "bullish"
        and str(context.get("cash_open_state")) == "rotation"
        and reclaim is not None
        and int(reclaim) < 8
    )


def _should_abstain(row: dict[str, object]) -> bool:
    return (
        _base_breaker_rotation_compressed(row)
        and not _bullish_recovery_sequence(row)
    )


def _fvg_short_compressed_fresh_fast(
    row: dict[str, object],
) -> bool:
    if str(row["entry_family"]) != "fair-value-gap":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("reference_volatility_state")) == "compressed"
        and adverse._reclaim_sequence_state(
            context.get("reference_reclaim_age_minutes")
        )
        == "FRESH_LT8M"
        and adverse._confirmation_latency_state(
            context.get("confirmation_latency_minutes")
        )
        == "FAST_LE5M"
    )


def _episode_fvg_normal_bullish_rotation(
    row: dict[str, object],
) -> bool:
    if str(row["entry_family"]) != "fair-value-gap":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "bullish"
        and str(context.get("reference_volatility_state")) == "normal"
        and str(context.get("h1_state")) == "mixed"
        and str(context.get("premarket_state")) == "rotation"
        and str(context.get("cash_open_state")) == "bullish"
    )


def _episode_breaker_bearish_compressed_bullish(
    row: dict[str, object],
) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "bearish"
        and str(context.get("reference_volatility_state")) == "compressed"
        and str(context.get("h1_state")) == "bullish"
    )


def _r8_breaker_short_normal_mature_fast(
    row: dict[str, object],
) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("reference_volatility_state")) == "normal"
        and adverse._reclaim_sequence_state(
            context.get("reference_reclaim_age_minutes")
        )
        == "MATURE_GE15M"
        and adverse._confirmation_latency_state(
            context.get("confirmation_latency_minutes")
        )
        == "FAST_LE5M"
    )


def _residual_entry_quality_forensics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    for row in rows:
        context = cast(dict[str, object], row.get("entry_context", {}))
        net_r = _d(row["r_multiple"]) - specialist.FRICTION
        first_material_adverse = next(
            (
                event
                for event in cast(
                    list[dict[str, object]],
                    row.get("cognitive_exit_evaluations", []),
                )
                if event.get("current_open_r") is not None
                and _d(event["current_open_r"])
                <= adverse.MATERIAL_ADVERSE_R
            ),
            None,
        )
        rapid_invalidation = (
            str(row.get("exit_reason")) == "structural-invalidation"
            and first_material_adverse is None
            and net_r < 0
        )
        samples.append(
            {
                "net_r": net_r,
                "winner": net_r > 0,
                "loser": net_r < 0,
                "rapid_invalidation": rapid_invalidation,
                "entry_family": str(row["entry_family"]),
                "side": str(row["side"]),
                "prior_day_state": str(
                    context.get("prior_day_state", "NA")
                ),
                "reference_volatility_state": str(
                    context.get("reference_volatility_state", "NA")
                ),
                "h4_state": str(context.get("h4_state", "NA")),
                "h1_state": str(context.get("h1_state", "NA")),
                "m15_state": str(context.get("m15_state", "NA")),
                "premarket_state": str(
                    context.get("premarket_state", "NA")
                ),
                "cash_open_state": str(
                    context.get("cash_open_state", "NA")
                ),
                "position_in_prior_day_range": str(
                    context.get("position_in_prior_day_range", "NA")
                ),
                "entry_freshness_state": adverse._entry_freshness_state(
                    context.get("entry_evidence_age_minutes")
                ),
                "reclaim_sequence_state": adverse._reclaim_sequence_state(
                    context.get("reference_reclaim_age_minutes")
                ),
                "confirmation_latency_state": (
                    adverse._confirmation_latency_state(
                        context.get("confirmation_latency_minutes")
                    )
                ),
            }
        )

    fields = (
        (
            "entry_family",
            "side",
            "prior_day_state",
            "reference_volatility_state",
            "h1_state",
        ),
        (
            "entry_family",
            "side",
            "prior_day_state",
            "reference_volatility_state",
            "h1_state",
            "cash_open_state",
        ),
        (
            "entry_family",
            "side",
            "prior_day_state",
            "reference_volatility_state",
            "h1_state",
            "premarket_state",
            "cash_open_state",
        ),
        (
            "entry_family",
            "side",
            "reference_volatility_state",
            "h1_state",
            "m15_state",
        ),
        (
            "entry_family",
            "side",
            "prior_day_state",
            "position_in_prior_day_range",
        ),
        (
            "entry_family",
            "side",
            "reference_volatility_state",
            "reclaim_sequence_state",
            "confirmation_latency_state",
        ),
        (
            "entry_family",
            "side",
            "entry_freshness_state",
            "confirmation_latency_state",
        ),
        (
            "entry_family",
            "side",
            "reclaim_sequence_state",
            "confirmation_latency_state",
        ),
        (
            "entry_family",
            "side",
            "h4_state",
            "h1_state",
            "m15_state",
        ),
        (
            "entry_family",
            "side",
            "premarket_state",
            "cash_open_state",
        ),
        (
            "entry_family",
            "side",
            "prior_day_state",
            "reference_volatility_state",
            "reclaim_sequence_state",
            "confirmation_latency_state",
        ),
        (
            "side",
            "h1_state",
            "m15_state",
            "reclaim_sequence_state",
        ),
        (
            "side",
            "premarket_state",
            "cash_open_state",
            "confirmation_latency_state",
        ),
    )

    grouped: dict[str, dict[str, object]] = {}
    for field_tuple in fields:
        table: dict[str, list[dict[str, object]]] = defaultdict(list)
        for sample in samples:
            key = "|".join(str(sample[field]) for field in field_tuple)
            table[key].append(sample)
        grouped["+".join(field_tuple)] = {
            key: {
                "sample": len(items),
                "wins": sum(bool(item["winner"]) for item in items),
                "losses": sum(bool(item["loser"]) for item in items),
                "rapid_invalidations": sum(
                    bool(item["rapid_invalidation"]) for item in items
                ),
                "mean_net_r": format(
                    sum(
                        (
                            cast(Decimal, item["net_r"])
                            for item in items
                        ),
                        Decimal(0),
                    )
                    / Decimal(len(items)),
                    "f",
                ),
            }
            for key, items in sorted(table.items())
        }

    return {
        "observation_only": True,
        "action_authority": False,
        "outcome_runtime_authority": False,
        "trade_count": len(samples),
        "groups": grouped,
    }


def _report(
    *,
    structural_count: int,
    comparator: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    kept = {str(row["signal_at"]) for row in rows}
    excluded = [
        row for row in comparator if str(row["signal_at"]) not in kept
    ]
    return {
        "trade_count": len(rows),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(
                Decimal(len(rows)) / Decimal(structural_count),
                "f",
            )
        ),
        "relative_density_vs_comp003": (
            "0"
            if not comparator
            else format(
                Decimal(len(rows)) / Decimal(len(comparator)),
                "f",
            )
        ),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(
            rows,
            halfyear=True,
        ),
        "winner_preservation_vs_comp003": admission._winner_preservation(
            comparator,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "residual_entry_quality_forensics": (
            _residual_entry_quality_forensics(rows)
        ),
        "first_material_adverse_forensics": (
            adverse._first_material_adverse_forensics(
                comparator,
                rows,
            )
        ),
        "max_drawdown_episode_forensics": (
            adverse._max_drawdown_episode_forensics(
                comparator,
                rows,
            )
        ),
        "excluded_trade_count": len(excluded),
        "excluded_trade_forensics": [
            {
                "signal_at": row["signal_at"],
                "r_multiple": row["r_multiple"],
                "exit_reason": row["exit_reason"],
                "entry_family": row["entry_family"],
                "side": row["side"],
                "recovery_sequence": _bullish_recovery_sequence(row),
            }
            for row in excluded
        ],
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    comp003_rows: list[dict[str, object]] = []
    live_position_rows: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in LIVE_POSITION_VARIANTS
    }

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

        outcome = adverse._simulate(
            day_bars,
            executable,
            state,
            variant=POSITION_VARIANT,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "Comparator 003 changed terminal eligibility: "
                f"{outcome}"
            )
        comp003_rows.append(outcome)

        for live_variant in LIVE_POSITION_VARIANTS:
            live_outcome = adverse._simulate(
                day_bars,
                executable,
                state,
                variant=live_variant,
            )
            if live_outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{live_variant} changed terminal eligibility: "
                    f"{live_outcome}"
                )
            live_position_rows[live_variant].append(live_outcome)
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
    if [str(row["signal_at"]) for row in comp003_rows] != structural_ids:
        raise AssertionError(
            "Comparator 003 changed sovereign terminal trade identity"
        )
    for live_variant, live_rows in live_position_rows.items():
        if [str(row["signal_at"]) for row in live_rows] != structural_ids:
            raise AssertionError(
                f"{live_variant} changed sovereign terminal trade identity"
            )

    comparator = [
        row
        for row in comp003_rows
        if not admission._is_abstained(row, ADMISSION_BASE)
    ]
    candidate = [
        row for row in comparator if not _should_abstain(row)
    ]
    fvg_fresh_fast_candidate = [
        row
        for row in candidate
        if not _fvg_short_compressed_fresh_fast(row)
    ]
    episode_fvg_candidate = [
        row
        for row in fvg_fresh_fast_candidate
        if not _episode_fvg_normal_bullish_rotation(row)
    ]
    episode_breaker_candidate = [
        row
        for row in fvg_fresh_fast_candidate
        if not _episode_breaker_bearish_compressed_bullish(row)
    ]
    episode_union_candidate = [
        row
        for row in fvg_fresh_fast_candidate
        if not (
            _episode_fvg_normal_bullish_rotation(row)
            or _episode_breaker_bearish_compressed_bullish(row)
        )
    ]
    r8_repair_candidate = [
        row
        for row in fvg_fresh_fast_candidate
        if not _r8_breaker_short_normal_mature_fast(row)
    ]
    union_plus_r8_candidate = [
        row
        for row in fvg_fresh_fast_candidate
        if not (
            _episode_fvg_normal_bullish_rotation(row)
            or _episode_breaker_bearish_compressed_bullish(row)
            or _r8_breaker_short_normal_mature_fast(row)
        )
    ]

    clean_admission_control = episode_breaker_candidate

    live_clean_candidates: dict[str, list[dict[str, object]]] = {}
    for live_variant, live_rows in live_position_rows.items():
        admitted = [
            row
            for row in live_rows
            if not admission._is_abstained(row, ADMISSION_BASE)
        ]
        recovery_filtered = [
            row for row in admitted if not _should_abstain(row)
        ]
        fvg_filtered = [
            row
            for row in recovery_filtered
            if not _fvg_short_compressed_fresh_fast(row)
        ]
        live_clean_candidates[live_variant] = [
            row
            for row in fvg_filtered
            if not _episode_breaker_bearish_compressed_bullish(row)
        ]

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_base": ADMISSION_BASE,
        "comparator_id": COMPARATOR_ID,
        "position_variant": POSITION_VARIANT,
        "variants": {
            "COMP003_CONTROL": _report(
                structural_count=len(structural_rows),
                comparator=comparator,
                rows=comparator,
            ),
            (
                "ABSTAIN_BREAKER_SHORT_ROTATION_COMPRESSED_"
                "EXCEPT_BULLISH_RECOVERY_SEQUENCE"
            ): _report(
                structural_count=len(structural_rows),
                comparator=comparator,
                rows=candidate,
            ),
            (
                "CURRENT_SURVIVOR_PLUS_"
                "ABSTAIN_FVG_SHORT_COMPRESSED_FRESH_FAST"
            ): _report(
                structural_count=len(structural_rows),
                comparator=candidate,
                rows=fvg_fresh_fast_candidate,
            ),
            "COMP005_PLUS_EPISODE_FVG_NORMAL_BULLISH_ROTATION": _report(
                structural_count=len(structural_rows),
                comparator=fvg_fresh_fast_candidate,
                rows=episode_fvg_candidate,
            ),
            "COMP005_PLUS_EPISODE_BREAKER_BEARISH_COMPRESSED_BULLISH": _report(
                structural_count=len(structural_rows),
                comparator=fvg_fresh_fast_candidate,
                rows=episode_breaker_candidate,
            ),
            "COMP005_PLUS_EPISODE_UNION": _report(
                structural_count=len(structural_rows),
                comparator=fvg_fresh_fast_candidate,
                rows=episode_union_candidate,
            ),
            "COMP005_PLUS_R8_MATURE_NORMAL_BREAKER_REPAIR": _report(
                structural_count=len(structural_rows),
                comparator=fvg_fresh_fast_candidate,
                rows=r8_repair_candidate,
            ),
            "COMP005_PLUS_EPISODE_UNION_PLUS_R8_REPAIR": _report(
                structural_count=len(structural_rows),
                comparator=fvg_fresh_fast_candidate,
                rows=union_plus_r8_candidate,
            ),
            "CLEAN_ADMISSION_SURVIVOR_CONTROL": _report(
                structural_count=len(structural_rows),
                comparator=clean_admission_control,
                rows=clean_admission_control,
            ),
            "CLEAN_PLUS_MIXED_DEEP_ADVERSE_EXIT": _report(
                structural_count=len(structural_rows),
                comparator=clean_admission_control,
                rows=live_clean_candidates[
                    "COMP003_PLUS_MIXED_DEEP_ADVERSE"
                ],
            ),
            "CLEAN_PLUS_BREAKER_MIXED_DEEP_ADVERSE_EXIT": _report(
                structural_count=len(structural_rows),
                comparator=clean_admission_control,
                rows=live_clean_candidates[
                    "COMP003_PLUS_BREAKER_MIXED_DEEP_ADVERSE"
                ],
            ),
        },
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_admission_degree_of_freedom": True,
            "recovery_exception_entry_time_only": True,
            "reclaim_fresh_bucket_preexisting": True,
            "residual_entry_quality_forensics_observation_only": True,
            "residual_entry_quality_forensics_action_authority": False,
            "residual_entry_quality_expanded_observation_only": True,
            "residual_entry_quality_expanded_action_authority": False,
            "first_material_adverse_forensics_observation_only": True,
            "first_material_adverse_forensics_action_authority": False,
            "fvg_fresh_fast_candidate_predeclared": True,
            "fvg_fresh_fast_uses_preexisting_buckets": True,
            "residual_episode_frontier_predeclared": True,
            "residual_episode_frontier_uses_entry_time_only": True,
            "r8_repair_uses_preexisting_buckets": True,
            "mixed_deep_adverse_live_exit_predeclared": True,
            "mixed_deep_adverse_bucket_preexisting": True,
            "live_exit_decision_closed_m1": True,
            "live_exit_execution_next_m1_open": True,
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


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
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
