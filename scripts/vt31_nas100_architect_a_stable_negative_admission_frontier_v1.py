"""VT31 NAS100 Architect A stable-negative admission frontier V1.

Consumed/burned evidence development only.

The preceding admitted-state attribution found two pre-entry states with
negative mean-R in all four burned folds:

- selected entry family == order-block;
- reference volatility state == expanded.

This frontier tests only those predeclared universal-negative hypotheses.
It does not use the recent-only regime-flip observations as runtime rules.

Candidate behavior is represented as a hard ABSTAIN before order activation.
Because current Architect A admits at most one selected source operation and a
hard ABSTAIN terminates that source/day path, filtering the already-admitted
terminal ledger is an exact shadow representation of these additional
admission vetoes. No rearm/fallback is introduced.

No result from this frontier is promotion evidence: the hypotheses were
discovered on the same consumed folds and therefore remain burned development
evidence.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_architect_a_admitted_attribution_v1 as attribution
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.architect_a_stable_negative_admission_frontier.v1"
DENSITY_FLOOR = Decimal("0.75")
WINNER_COUNT_FLOOR = Decimal("0.80")
WINNER_R_FLOOR = Decimal("0.90")

VARIANTS = (
    "BASELINE",
    "ABSTAIN_ORDER_BLOCK",
    "ABSTAIN_EXPANDED_REFERENCE",
    "ABSTAIN_ORDER_BLOCK_OR_EXPANDED",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _is_abstained(
    row: dict[str, object],
    variant: str,
) -> bool:
    if variant == "BASELINE":
        return False

    features = cast(dict[str, str], row["pre_entry_features"])
    order_block = features["family"] == "order-block"
    expanded = features["volatility"] == "expanded"

    if variant == "ABSTAIN_ORDER_BLOCK":
        return order_block
    if variant == "ABSTAIN_EXPANDED_REFERENCE":
        return expanded
    if variant == "ABSTAIN_ORDER_BLOCK_OR_EXPANDED":
        return order_block or expanded
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
    baseline_winner_r = sum(
        (_d(row["r_multiple"]) for row in baseline_winners),
        Decimal(0),
    )
    candidate_winner_r = sum(
        (_d(row["r_multiple"]) for row in candidate_winners),
        Decimal(0),
    )
    count_preservation = (
        Decimal(1)
        if not baseline_winners
        else Decimal(len(candidate_winners)) / Decimal(len(baseline_winners))
    )
    r_preservation = (
        Decimal(1)
        if baseline_winner_r <= 0
        else candidate_winner_r / baseline_winner_r
    )
    return {
        "baseline_winner_count": len(baseline_winners),
        "candidate_winner_count": len(candidate_winners),
        "winner_count_preservation": format(count_preservation, "f"),
        "baseline_winner_r": format(baseline_winner_r, "f"),
        "candidate_winner_r": format(candidate_winner_r, "f"),
        "winner_r_preservation": format(r_preservation, "f"),
    }


def _variant_report(
    baseline: list[dict[str, object]],
    variant: str,
) -> dict[str, object]:
    candidate = [
        row for row in baseline if not _is_abstained(row, variant)
    ]
    removed = [
        row for row in baseline if _is_abstained(row, variant)
    ]
    density = (
        Decimal(0)
        if not baseline
        else Decimal(len(candidate)) / Decimal(len(baseline))
    )
    winner = _winner_preservation(baseline, candidate)
    stress = specialist._metrics(candidate, friction=specialist.FRICTION)
    mc = specialist._monte_carlo(candidate)
    halfyears = specialist._block_metrics(candidate, halfyear=True)

    removed_metrics = (
        specialist._metrics(removed, friction=specialist.FRICTION)
        if removed
        else None
    )
    return {
        "trade_count": len(candidate),
        "removed_trade_count": len(removed),
        "relative_density": format(density, "f"),
        "stress_0_05r": stress,
        "monte_carlo": mc,
        "halfyear_stress": halfyears,
        "winner_preservation": winner,
        "removed_metrics": removed_metrics,
        "removed_family_counts": {
            family: sum(
                cast(dict[str, str], row["pre_entry_features"])["family"]
                == family
                for row in removed
            )
            for family in ("breaker", "fair-value-gap", "order-block")
        },
        "removed_expanded_count": sum(
            cast(dict[str, str], row["pre_entry_features"])["volatility"]
            == "expanded"
            for row in removed
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    base = attribution.replay(evidence_path)
    baseline = [
        cast(dict[str, object], row)
        for row in cast(list[object], base["trades"])
    ]
    variants = {
        variant: _variant_report(baseline, variant)
        for variant in VARIANTS
    }
    baseline_ids = {
        str(row["signal_at"])
        for row in baseline
    }
    for variant in VARIANTS[1:]:
        retained = {
            str(row["signal_at"])
            for row in baseline
            if not _is_abstained(row, variant)
        }
        if not retained <= baseline_ids:
            raise AssertionError("candidate introduced a non-baseline trade")

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "evidence": base["evidence"],
        "variants": variants,
        "governance": {
            "consumed_evidence_only": True,
            "hypotheses_predeclared_before_frontier_run": True,
            "hypotheses_discovered_on_same_consumed_folds": True,
            "frontier_is_development_evidence_only": True,
            "runtime_reasoning_changed": False,
            "hard_abstain_shadow_semantics": True,
            "same_source_no_fallback": True,
            "rearm_introduced": False,
            "entry_price_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "position_management_changed": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
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
                "variants": {
                    name: {
                        "trade_count": report["trade_count"],
                        "removed_trade_count": report["removed_trade_count"],
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
                }
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
