"""VT31 NAS100 A+B admission integration frontier V1.

Consumed/burned evidence development only.

This frontier keeps the fixed B-side research comparator unchanged:

    H3 + W5 soft-DOL1 + full-cognition DOL2 + PS2

and applies predeclared Architect-A admission hypotheses before comparing final
economics. The purpose is to measure whether a cleaner entry population and
the already-surviving position stack compose positively.

Admission hypotheses:
- expanded 09:00 reference volatility -> hard ABSTAIN;
- Order Block family -> hard ABSTAIN;
- narrower Order Block with entry-evidence age 0-2m -> hard ABSTAIN;
- the two corresponding combinations with expanded volatility.

These hypotheses were discovered on consumed evidence. This workflow is
therefore development evidence only and cannot authorize candidate freeze or
fresh holdout.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.a_b_admission_integration_frontier.v1"
COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5
DENSITY_FLOOR = Decimal("0.75")
WINNER_COUNT_FLOOR = Decimal("0.80")
WINNER_R_FLOOR = Decimal("0.90")
PREFERRED_RESIDUAL_VARIANT = (
    "A_ABSTAIN_ORDER_BLOCK_AGE_0_2M_OR_EXPANDED"
)

VARIANTS = (
    "CONTROL_B_W5",
    "A_ABSTAIN_EXPANDED_REFERENCE",
    "A_ABSTAIN_ORDER_BLOCK",
    "A_ABSTAIN_ORDER_BLOCK_AGE_0_2M",
    "A_ABSTAIN_ORDER_BLOCK_OR_EXPANDED",
    "A_ABSTAIN_ORDER_BLOCK_AGE_0_2M_OR_EXPANDED",
    "A_EXPANDED_OB_REQUIRE_SHORT",
    "A_EXPANDED_OB_REQUIRE_AGE_11M",
    "A_EXPANDED_OB_REQUIRE_SHORT_AGE_11M",
    "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _entry_context(row: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], row["entry_context"])


def _order_block(row: dict[str, object]) -> bool:
    return str(row["entry_family"]) == "order-block"


def _order_block_age_0_2m(row: dict[str, object]) -> bool:
    if not _order_block(row):
        return False
    value = _entry_context(row).get("entry_evidence_age_minutes")
    if value is None:
        return False
    age = _d(value)
    return Decimal(0) <= age <= Decimal(2)


def _expanded(row: dict[str, object]) -> bool:
    return (
        str(_entry_context(row).get("reference_volatility_state"))
        == "expanded"
    )


def _context_minutes(row: dict[str, object], field: str) -> int | None:
    value = _entry_context(row).get(field)
    if value is None:
        return None
    return int(value)


def _order_block_positive_evidence(
    row: dict[str, object],
    *,
    require_short: bool = False,
    min_entry_age: int | None = None,
    min_reclaim_age: int | None = None,
) -> bool:
    if not _order_block(row):
        return True
    if require_short and str(row["side"]) != "short":
        return False
    if min_entry_age is not None:
        age = _context_minutes(row, "entry_evidence_age_minutes")
        if age is None or age < min_entry_age:
            return False
    if min_reclaim_age is not None:
        age = _context_minutes(row, "reference_reclaim_age_minutes")
        if age is None or age < min_reclaim_age:
            return False
    return True


def _is_abstained(row: dict[str, object], variant: str) -> bool:
    if variant == "CONTROL_B_W5":
        return False
    order_block = _order_block(row)
    order_block_fresh = _order_block_age_0_2m(row)
    expanded = _expanded(row)
    if variant == "A_ABSTAIN_EXPANDED_REFERENCE":
        return expanded
    if variant == "A_ABSTAIN_ORDER_BLOCK":
        return order_block
    if variant == "A_ABSTAIN_ORDER_BLOCK_AGE_0_2M":
        return order_block_fresh
    if variant == "A_ABSTAIN_ORDER_BLOCK_OR_EXPANDED":
        return order_block or expanded
    if variant == "A_ABSTAIN_ORDER_BLOCK_AGE_0_2M_OR_EXPANDED":
        return order_block_fresh or expanded
    if variant == "A_EXPANDED_OB_REQUIRE_SHORT":
        return expanded or not _order_block_positive_evidence(
            row,
            require_short=True,
        )
    if variant == "A_EXPANDED_OB_REQUIRE_AGE_11M":
        return expanded or not _order_block_positive_evidence(
            row,
            min_entry_age=11,
        )
    if variant == "A_EXPANDED_OB_REQUIRE_SHORT_AGE_11M":
        return expanded or not _order_block_positive_evidence(
            row,
            require_short=True,
            min_entry_age=11,
        )
    if variant == "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M":
        return expanded or not _order_block_positive_evidence(
            row,
            require_short=True,
            min_reclaim_age=15,
        )
    raise ValueError(f"unsupported variant: {variant}")


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    baseline_winners = [
        row for row in baseline if _d(row["r_multiple"]) > 0
    ]
    candidate_winners = [
        row for row in candidate if _d(row["r_multiple"]) > 0
    ]
    baseline_r = sum(
        (_d(row["r_multiple"]) for row in baseline_winners),
        Decimal(0),
    )
    candidate_r = sum(
        (_d(row["r_multiple"]) for row in candidate_winners),
        Decimal(0),
    )
    count_ratio = (
        Decimal(1)
        if not baseline_winners
        else Decimal(len(candidate_winners)) / Decimal(len(baseline_winners))
    )
    r_ratio = (
        Decimal(1)
        if baseline_r <= 0
        else candidate_r / baseline_r
    )
    return {
        "baseline_winner_count": len(baseline_winners),
        "candidate_winner_count": len(candidate_winners),
        "winner_count_preservation": format(count_ratio, "f"),
        "baseline_winner_r": format(baseline_r, "f"),
        "candidate_winner_r": format(candidate_r, "f"),
        "winner_r_preservation": format(r_ratio, "f"),
    }


def _minutes_bucket(value: object) -> str:
    if value is None:
        return "unavailable"
    minute = int(value)
    if minute <= 2:
        return "0_2m"
    if minute <= 5:
        return "3_5m"
    if minute <= 10:
        return "6_10m"
    return "11m_plus"


def _residual_class_keys(row: dict[str, object]) -> tuple[str, ...]:
    context = _entry_context(row)
    family = str(row["entry_family"])
    side = str(row["side"])
    h1 = str(context.get("h1_state", "NA"))
    m15 = str(context.get("m15_state", "NA"))
    prior = str(context.get("prior_day_state", "NA"))
    location = str(context.get("position_in_prior_day_range", "NA"))
    volatility = str(context.get("reference_volatility_state", "NA"))
    confirmation = _minutes_bucket(
        context.get("confirmation_latency_minutes")
    )
    entry_age = _minutes_bucket(
        context.get("entry_evidence_age_minutes")
    )
    return (
        f"family_m15={family}|{m15}",
        f"family_prior={family}|{prior}",
        f"family_location={family}|{location}",
        f"side_m15={side}|{m15}",
        f"side_prior={side}|{prior}",
        f"m15_prior={m15}|{prior}",
        f"m15_location={m15}|{location}",
        f"prior_location={prior}|{location}",
        f"family_h1_m15={family}|{h1}|{m15}",
        f"family_m15_prior={family}|{m15}|{prior}",
        f"family_m15_location={family}|{m15}|{location}",
        f"side_m15_prior={side}|{m15}|{prior}",
        f"side_m15_location={side}|{m15}|{location}",
        f"m15_prior_location={m15}|{prior}|{location}",
        (
            "family_m15_confirmation="
            f"{family}|{m15}|{confirmation}"
        ),
        (
            "family_prior_entry_age="
            f"{family}|{prior}|{entry_age}"
        ),
        (
            "m15_prior_confirmation="
            f"{m15}|{prior}|{confirmation}"
        ),
        (
            "family_volatility_m15="
            f"{family}|{volatility}|{m15}"
        ),
    )


def _residual_multivariate_groups(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for key in _residual_class_keys(row):
            groups[key].append(row)
    result: dict[str, dict[str, object]] = {}
    for key, group in sorted(groups.items()):
        if len(group) < 2:
            continue
        result[key] = {
            "sample": len(group),
            "stress_0_05r": specialist._metrics(
                group,
                friction=specialist.FRICTION,
            ),
        }
    return result


def _remaining_order_block_traces(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    fields = (
        "decision_minute_ny",
        "prior_day_state",
        "h4_state",
        "h1_state",
        "m15_state",
        "premarket_state",
        "cash_open_state",
        "position_in_prior_day_range",
        "reference_volatility_state",
        "reference_width_vs_prior5",
        "current_path_vs_previous",
        "confirmation_latency_minutes",
        "entry_evidence_age_minutes",
        "reference_reclaim_age_minutes",
        "risk_ref",
        "destination_distance_ref",
        "raid_depth_ref",
        "recent_path_efficiency",
        "recent_overlap_rate",
    )
    result = []
    for row in rows:
        if not _order_block(row):
            continue
        context = _entry_context(row)
        result.append(
            {
                "local_date": row.get("local_date"),
                "signal_at": row.get("signal_at"),
                "side": row.get("side"),
                "r_multiple": row.get("r_multiple"),
                "exit_reason": row.get("exit_reason"),
                "entry_context": {
                    field: context.get(field)
                    for field in fields
                },
            }
        )
    return sorted(result, key=lambda item: str(item["signal_at"]))


def _removed_context(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    fields = (
        "reference_volatility_state",
        "prior_day_state",
        "h1_state",
        "m15_state",
        "premarket_state",
        "cash_open_state",
        "position_in_prior_day_range",
        "confirmation_latency_minutes",
        "entry_evidence_age_minutes",
        "reference_reclaim_age_minutes",
    )
    result: dict[str, dict[str, int]] = {}
    for field in fields:
        counts = Counter(
            str(_entry_context(row).get(field, "NA"))
            for row in rows
        )
        result[field] = dict(sorted(counts.items()))
    result["entry_family"] = dict(
        sorted(Counter(str(row["entry_family"]) for row in rows).items())
    )
    result["side"] = dict(
        sorted(Counter(str(row["side"]) for row in rows).items())
    )
    return result


def _variant_report(
    control: list[dict[str, object]],
    variant: str,
) -> dict[str, object]:
    candidate = [
        row for row in control if not _is_abstained(row, variant)
    ]
    removed = [
        row for row in control if _is_abstained(row, variant)
    ]
    density = (
        Decimal(0)
        if not control
        else Decimal(len(candidate)) / Decimal(len(control))
    )
    return {
        "trade_count": len(candidate),
        "removed_trade_count": len(removed),
        "relative_density": format(density, "f"),
        "stress_0_05r": specialist._metrics(
            candidate,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(candidate),
        "halfyear_stress": specialist._block_metrics(
            candidate,
            halfyear=True,
        ),
        "winner_preservation": _winner_preservation(control, candidate),
        "removed_metrics": (
            specialist._metrics(removed, friction=specialist.FRICTION)
            if removed
            else None
        ),
        "removed_context": _removed_context(removed),
        "sequence_diagnostics": (
            composition._sequence_diagnostics(candidate)
            if variant == PREFERRED_RESIDUAL_VARIANT
            else None
        ),
        "residual_multivariate_groups": (
            _residual_multivariate_groups(candidate)
            if variant == PREFERRED_RESIDUAL_VARIANT
            else None
        ),
        "remaining_order_block_traces": (
            _remaining_order_block_traces(candidate)
            if variant == PREFERRED_RESIDUAL_VARIANT
            else None
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    control_rows: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        baseline = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if baseline.get("status") != "terminal":
            return baseline

        outcome = composition._simulate_composite(
            day_bars,
            executable,
            state,
            window=WINDOW,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                f"fixed B comparator changed terminal eligibility: {outcome}"
            )
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        control_rows.append(outcome)
        return baseline

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    control_ids = [str(row["signal_at"]) for row in control_rows]
    if structural_ids != control_ids:
        raise AssertionError(
            "fixed B comparator changed the sovereign terminal population"
        )

    variants = {
        variant: _variant_report(control_rows, variant)
        for variant in VARIANTS
    }
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "variants": variants,
        "governance": {
            "consumed_evidence_only": True,
            "a_hypotheses_predeclared": True,
            "a_hypotheses_discovered_on_consumed_evidence": True,
            "order_block_positive_evidence_frontier_predeclared": True,
            "order_block_positive_evidence_frontier_development_only": True,
            "b_comparator_fixed": True,
            "b_h3_horizon_m1": 3,
            "b_soft_dol1_window_m1": WINDOW,
            "b_target": "FULL_COGNITION_DOL2",
            "b_protection": "PS2_CONFIRMED_M1_NEXT_BAR_ACTUATION",
            "maximum_cognition_branch_used": True,
            "m15_context_present_in_entry_state": True,
            "runtime_policy_changed": False,
            "entry_price_changed": False,
            "initial_stop_changed": False,
            "b_position_logic_changed": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
            "residual_clustering_diagnostics_observation_only": True,
            "residual_clustering_diagnostics_action_authority": False,
            "residual_multivariate_diagnostics_observation_only": True,
            "residual_multivariate_diagnostics_action_authority": False,
            "remaining_order_block_diagnostics_observation_only": True,
            "remaining_order_block_diagnostics_action_authority": False,
            "residual_preferred_variant": PREFERRED_RESIDUAL_VARIANT,
            "density_floor_predeclared": format(DENSITY_FLOOR, "f"),
            "winner_count_floor_predeclared": format(
                WINNER_COUNT_FLOOR,
                "f",
            ),
            "winner_r_floor_predeclared": format(WINNER_R_FLOOR, "f"),
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
    print(
        json.dumps(
            {
                "comparator_id": payload["comparator_id"],
                "variants": {
                    name: {
                        "trade_count": report["trade_count"],
                        "removed_trade_count": report[
                            "removed_trade_count"
                        ],
                        "relative_density": report["relative_density"],
                        "stress_0_05r": report["stress_0_05r"],
                        "monte_carlo": report["monte_carlo"],
                        "winner_preservation": report[
                            "winner_preservation"
                        ],
                    }
                    for name, report in cast(
                        dict[str, dict[str, object]],
                        payload["variants"],
                    ).items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
