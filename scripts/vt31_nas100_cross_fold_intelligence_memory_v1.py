"""Aggregate VT31_NAS100 intelligence forensics across consumed folds.

This layer derives research-only management-state evidence from structural
counterfactuals, never directly from PnL.

A context can be classified only when it has sufficient evidence in every
consumed fold:
- SUPPORTIVE_LIKE: premature cuts exceed protected failed journeys in every fold;
- CAUTIOUS_LIKE: protected failed journeys exceed premature cuts in every fold;
- MIXED: fold directions disagree or tie;
- UNKNOWN: insufficient per-fold evidence.

These are research memory labels, not an operating trailing policy.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

IDENTITY = "VT31_NAS100_CROSS_FOLD_INTELLIGENCE_MEMORY_V1"
PARTITIONS = ("r8_fresh", "r6", "r5")
MIN_CONTEXT_EVENTS_PER_FOLD = 8
_CONTEXT_DIMENSIONS = (
    "prior_day_state",
    "h4_state",
    "h1_state",
    "premarket_state",
    "cash_open_state",
    "position_in_prior_day_range",
    "reference_volatility_state",
    "last_structure_event_family",
)


def _load_single(root: Path, pattern: str) -> dict[str, Any]:
    matches = list(root.rglob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern}, got {len(matches)}")
    return cast(
        dict[str, Any],
        json.loads(matches[0].read_text(encoding="utf-8")),
    )


def _direction(counts: Counter[str]) -> str:
    premature = counts["PREMATURE_CUT_DEEPER_JOURNEY"]
    protected = counts["PROTECTED_FAILED_JOURNEY"]
    if premature > protected:
        return "SUPPORTIVE"
    if protected > premature:
        return "CAUTIOUS"
    return "MIXED"


def _fold_context_counts(
    position: dict[str, Any],
) -> dict[tuple[str, str], Counter[str]]:
    result: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    observations = cast(list[dict[str, Any]], position["observations"])
    for row in observations:
        context = row.get("pre_entry_context")
        if not isinstance(context, dict):
            continue
        classification = str(row["classification"])
        for dimension in _CONTEXT_DIMENSIONS:
            value = str(context.get(dimension, "unavailable"))
            result[(dimension, value)][classification] += 1
    return result


def _capacity_summary(
    handoff: dict[str, Any],
) -> dict[str, object]:
    journey = cast(dict[str, Any], handoff["journey_capacity"])
    overall = cast(dict[str, Any], journey["overall"])
    return {
        "labeled_opportunities": journey["labeled_opportunities"],
        "rank_counts": journey["rank_counts"],
        "dol1_reach_rate": overall["dol1_reach_rate"],
        "dol2_reach_rate": overall["dol2_reach_rate"],
        "dol3_reach_rate": overall["dol3_reach_rate"],
        "dol4plus_reach_rate": overall["dol4plus_reach_rate"],
        "rank_median": overall["rank_median"],
        "risk_ref_quantiles": journey["risk_ref_quantile_boundaries"],
    }


def build(root: Path) -> dict[str, object]:
    fold_payloads: dict[str, dict[str, Any]] = {}
    for partition in PARTITIONS:
        handoff = _load_single(
            root,
            f"handoff-forensics-{partition}.json",
        )
        position = _load_single(
            root,
            f"position-intelligence-{partition}.json",
        )
        if handoff.get("market") != "NAS100" or position.get("market") != "NAS100":
            raise ValueError("cross-fold memory requires NAS100 only")
        if handoff["governance"]["opens_new_holdout"] is not False:
            raise ValueError("handoff report opened holdout")
        if position["governance"]["opens_new_holdout"] is not False:
            raise ValueError("position report opened holdout")
        fold_payloads[partition] = {
            "handoff": handoff,
            "position": position,
        }

    context_by_fold = {
        partition: _fold_context_counts(
            cast(dict[str, Any], payload["position"])
        )
        for partition, payload in fold_payloads.items()
    }
    keys = sorted(
        set().union(*(set(table) for table in context_by_fold.values()))
    )

    context_states: list[dict[str, object]] = []
    for dimension, value in keys:
        fold_rows: dict[str, object] = {}
        directions: list[str] = []
        sufficient = True
        for partition in PARTITIONS:
            counts = context_by_fold[partition].get(
                (dimension, value),
                Counter(),
            )
            relevant = (
                counts["PREMATURE_CUT_DEEPER_JOURNEY"]
                + counts["PROTECTED_FAILED_JOURNEY"]
            )
            if relevant < MIN_CONTEXT_EVENTS_PER_FOLD:
                sufficient = False
            direction = _direction(counts)
            directions.append(direction)
            fold_rows[partition] = {
                "relevant_events": relevant,
                "premature_cut": counts[
                    "PREMATURE_CUT_DEEPER_JOURNEY"
                ],
                "protected_failed_journey": counts[
                    "PROTECTED_FAILED_JOURNEY"
                ],
                "direction": direction,
            }

        if not sufficient:
            research_state = "UNKNOWN"
        elif all(item == "SUPPORTIVE" for item in directions):
            research_state = "SUPPORTIVE_LIKE"
        elif all(item == "CAUTIOUS" for item in directions):
            research_state = "CAUTIOUS_LIKE"
        else:
            research_state = "MIXED"

        context_states.append(
            {
                "dimension": dimension,
                "value": value,
                "research_state": research_state,
                "folds": fold_rows,
                "operating_policy_authorized": False,
            }
        )

    state_counts = Counter(
        str(row["research_state"]) for row in context_states
    )
    return {
        "identity": IDENTITY,
        "market": "NAS100",
        "partitions": list(PARTITIONS),
        "minimum_context_events_per_fold": MIN_CONTEXT_EVENTS_PER_FOLD,
        "capacity_by_fold": {
            partition: _capacity_summary(
                cast(dict[str, Any], payload["handoff"])
            )
            for partition, payload in fold_payloads.items()
        },
        "position_intelligence_by_fold": {
            partition: {
                "opportunities_assessed": payload["position"][
                    "opportunities_assessed"
                ],
                "reconstruction_failures": payload["position"][
                    "reconstruction_failures"
                ],
                "protection_events": payload["position"][
                    "protection_events"
                ],
                "classification_counts": payload["position"][
                    "classification_counts"
                ],
                "by_event_type": payload["position"]["by_event_type"],
            }
            for partition, payload in fold_payloads.items()
        },
        "context_management_state_counts": dict(
            sorted(state_counts.items())
        ),
        "context_management_states": context_states,
        "governance": {
            "classification_basis": (
                "structural-journey-preservation-not-pnl"
            ),
            "requires_all_consumed_folds": True,
            "xauusd_parameters_copied": False,
            "operating_policy_selection_allowed": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "capacity_by_fold": payload["capacity_by_fold"],
                "position_intelligence_by_fold": payload[
                    "position_intelligence_by_fold"
                ],
                "context_management_state_counts": payload[
                    "context_management_state_counts"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
