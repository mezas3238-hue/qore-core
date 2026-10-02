#!/usr/bin/env python3
"""STI-8 V1 economic-response failure diagnostic.

This diagnostic does not retune STI-8 and does not choose a new response policy.
It asks why a strong predictive threat signal destroyed winners when a naive
Trader-owned EXIT_NEXT_M1_OPEN response was applied.

Only already-consumed R6/R5 and burned research-OOS evidence are used.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
    assess_position_threat,
)

IDENTITY = "QORE_SHARED_STI8_ECONOMIC_RESPONSE_V1_FAILURE_DIAGNOSTIC_001"

SOURCE_FIELDS = (
    "minutes_since_fill",
    "progress_bps",
    "signed_close_r_bps",
    "efficiency_bps",
    "overlap_bps",
    "signed_body_r_bps",
    "peer_confirmation_bps",
    "breadth_bps",
    "peer_transition_adverse_bps",
    "world_support_bps",
    "world_fragility_bps",
)

ASSESSMENT_FIELDS = (
    "threat_score_bps",
    "continuation_support_bps",
    "failure_hazard_bps",
    "relationship_break_bps",
    "systemic_stress_bps",
    "uncertainty_bps",
)


def _mean(rows: list[dict[str, int]], key: str) -> int:
    if not rows:
        return 0
    return sum(row[key] for row in rows) // len(rows)


def _profile(rows: list[dict[str, int]]) -> dict[str, int]:
    keys = SOURCE_FIELDS + ASSESSMENT_FIELDS
    return {key: _mean(rows, key) for key in keys}


def _delta(
    left: dict[str, int],
    right: dict[str, int],
) -> dict[str, int]:
    return {key: left[key] - right[key] for key in left}


def _snapshot(
    observation: Any,
    assessment: SharedPositionThreatEngineAssessment,
) -> dict[str, int]:
    row = {
        key: int(getattr(observation, key))
        for key in SOURCE_FIELDS
    }
    row.update(
        {
            key: int(getattr(assessment, key))
            for key in ASSESSMENT_FIELDS
        }
    )
    return row


def diagnose(
    *,
    partition: str,
    frozen_policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )

    groups: dict[str, list[dict[str, int]]] = {
        "THREATENED_LOSS": [],
        "THREATENED_WINNER": [],
        "UNTHREATENED_LOSS": [],
        "UNTHREATENED_WINNER": [],
    }
    scopes: dict[str, Counter[str]] = {
        key: Counter() for key in groups
    }
    levels: dict[str, Counter[str]] = {
        key: Counter() for key in groups
    }
    terminal_r: dict[str, list[Decimal]] = {
        key: [] for key in groups
    }

    # Materialize source-time threat cognition before touching terminal outcome.
    materialized: list[
        tuple[dict[str, object], dict[str, int] | None, str | None, str | None]
    ] = []
    source_observation_count = 0

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(tuple[Any, ...], sequence["observations"])
        source_observation_count += len(observations)
        first: dict[str, int] | None = None
        first_scope: str | None = None
        first_level: str | None = None

        for observation in observations:
            assessment = assess_position_threat(observation, policy=policy)
            if (
                first is None
                and assessment.threat_level in base.THREAT_LEVELS
            ):
                first = _snapshot(observation, assessment)
                first_scope = assessment.threat_scope.value
                first_level = assessment.threat_level.value

        materialized.append((row, first, first_scope, first_level))

    for row, first, scope, level in materialized:
        final_r = Decimal(str(row["net_r_after_friction"]))
        is_loss = final_r < 0
        if first is not None and is_loss:
            key = "THREATENED_LOSS"
        elif first is not None:
            key = "THREATENED_WINNER"
        elif is_loss:
            key = "UNTHREATENED_LOSS"
        else:
            key = "UNTHREATENED_WINNER"

        if first is not None:
            groups[key].append(first)
        if scope is not None:
            scopes[key][scope] += 1
        if level is not None:
            levels[key][level] += 1
        terminal_r[key].append(final_r)

    profiles = {
        key: _profile(value)
        for key, value in groups.items()
        if value
    }
    threatened_loss = profiles["THREATENED_LOSS"]
    threatened_winner = profiles["THREATENED_WINNER"]
    winner_minus_loss = _delta(threatened_winner, threatened_loss)

    hypotheses: list[dict[str, object]] = []

    local_resilience = max(
        winner_minus_loss["progress_bps"],
        winner_minus_loss["signed_close_r_bps"],
        winner_minus_loss["efficiency_bps"],
        winner_minus_loss["signed_body_r_bps"],
    )
    if local_resilience >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_LOCAL_THESIS_RESILIENCE_COUNTERSIGNATURE",
                "evidence": {
                    "max_threatened_winner_minus_loss_bps": local_resilience,
                    "feature_deltas_bps": {
                        key: winner_minus_loss[key]
                        for key in (
                            "progress_bps",
                            "signed_close_r_bps",
                            "efficiency_bps",
                            "signed_body_r_bps",
                        )
                    },
                },
                "meaning": (
                    "Material global threat may be non-actionable while the local "
                    "position thesis remains causally resilient. V2 should arbitrate "
                    "threat against local thesis deterioration rather than exit on "
                    "threat alone."
                ),
            }
        )

    relational_resilience = max(
        winner_minus_loss["peer_confirmation_bps"],
        winner_minus_loss["breadth_bps"],
        winner_minus_loss["world_support_bps"],
    )
    if relational_resilience >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_RELATIONAL_RESILIENCE_COUNTERSIGNATURE",
                "evidence": {
                    "max_threatened_winner_minus_loss_bps": relational_resilience,
                    "feature_deltas_bps": {
                        key: winner_minus_loss[key]
                        for key in (
                            "peer_confirmation_bps",
                            "breadth_bps",
                            "world_support_bps",
                        )
                    },
                },
                "meaning": (
                    "Threatened winners may preserve broader confirmation despite "
                    "a material threat score; response should require unresolved "
                    "threat plus collapsing relational support."
                ),
            }
        )

    failure_separation = (
        threatened_loss["failure_hazard_bps"]
        - threatened_winner["failure_hazard_bps"]
    )
    if failure_separation >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_FAILURE_HAZARD_DOMINANCE_REQUIRED",
                "evidence": {
                    "threatened_loss_minus_winner_failure_hazard_bps": (
                        failure_separation
                    ),
                    "loss_failure_hazard_bps": threatened_loss[
                        "failure_hazard_bps"
                    ],
                    "winner_failure_hazard_bps": threatened_winner[
                        "failure_hazard_bps"
                    ],
                },
                "meaning": (
                    "A material threat should not trigger a Trader response unless "
                    "failure hazard dominates continuation/local resilience."
                ),
            }
        )

    continuation_separation = (
        threatened_winner["continuation_support_bps"]
        - threatened_loss["continuation_support_bps"]
    )
    if continuation_separation >= 500:
        hypotheses.append(
            {
                "hypothesis": "V2_CONTINUATION_COUNTEREVIDENCE_VETO",
                "evidence": {
                    "threatened_winner_minus_loss_continuation_bps": (
                        continuation_separation
                    ),
                },
                "meaning": (
                    "Strong continuation evidence may veto an otherwise material "
                    "threat response. This requires a newly validated continuation "
                    "head; falsified STI-6 V1 cannot be imported as truth."
                ),
            }
        )

    scope_delta = {
        scope: scopes["THREATENED_WINNER"][scope]
        - scopes["THREATENED_LOSS"][scope]
        for scope in sorted(
            set(scopes["THREATENED_WINNER"])
            | set(scopes["THREATENED_LOSS"])
        )
    }
    if scope_delta:
        hypotheses.append(
            {
                "hypothesis": "V2_THREAT_SCOPE_CONDITIONAL_RESPONSE",
                "evidence": {
                    "scope_count_delta_winner_minus_loss": scope_delta,
                    "threatened_winner_scope_histogram": dict(
                        sorted(scopes["THREATENED_WINNER"].items())
                    ),
                    "threatened_loss_scope_histogram": dict(
                        sorted(scopes["THREATENED_LOSS"].items())
                    ),
                },
                "meaning": (
                    "LOCAL/CROSS_ASSET/SYSTEMIC threat scopes may require different "
                    "Trader responses instead of one universal exit action."
                ),
            }
        )

    return {
        "partition": partition,
        "trade_count": len(sequences),
        "source_observation_count": source_observation_count,
        "group_counts": {
            key: (
                len(groups[key])
                if "THREATENED" in key and not key.startswith("UN")
                else len(terminal_r[key])
            )
            for key in groups
        },
        "first_material_threat_profiles_bps": profiles,
        "threatened_winner_minus_loss_delta_bps": winner_minus_loss,
        "scope_histograms": {
            key: dict(sorted(value.items()))
            for key, value in scopes.items()
        },
        "level_histograms": {
            key: dict(sorted(value.items()))
            for key, value in levels.items()
        },
        "terminal_r_summary": {
            key: {
                "count": len(values),
                "total_r": str(sum(values, Decimal(0))),
                "mean_r": str(
                    Decimal(0)
                    if not values
                    else sum(values, Decimal(0)) / Decimal(len(values))
                ),
            }
            for key, values in terminal_r.items()
        },
        "v2_response_hypothesis_candidates": hypotheses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    for partition in ("r6", "r5", "oos"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    partitions = {
        "r6": "r6",
        "r5": "r5",
        "oos": "sti8_research_oos_v1",
    }
    results = {}
    for cli_name, source_name in partitions.items():
        results[cli_name] = diagnose(
            partition=source_name,
            frozen_policy_path=args.policy,
            trades_path=getattr(args, f"{cli_name}_trades"),
            nas_path=getattr(args, f"{cli_name}_nas"),
            sp_path=getattr(args, f"{cli_name}_sp"),
            us_path=getattr(args, f"{cli_name}_us"),
        )

    candidate_sets = [
        {
            item["hypothesis"]
            for item in cast(
                list[dict[str, object]],
                result["v2_response_hypothesis_candidates"],
            )
        }
        for result in results.values()
    ]
    cross_partition = sorted(set.intersection(*candidate_sets))

    payload = {
        "identity": IDENTITY,
        "status": "V1_RESPONSE_FAILURE_KNOWLEDGE_EXTRACTED_NO_RETUNING",
        "partitions": results,
        "cross_partition_hypotheses": cross_partition,
        "governance": {
            "sti8_engine_changed": False,
            "sti8_thresholds_changed": False,
            "economic_response_v1_reopened": False,
            "v2_response_policy_selected": False,
            "burned_evidence_only": True,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "status": payload["status"],
                "cross_partition_hypotheses": cross_partition,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
