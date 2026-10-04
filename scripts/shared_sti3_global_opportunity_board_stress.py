#!/usr/bin/env python3
"""Real source stress for STI-3 Global Opportunity Attention Board."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import shared_sti2_real_opportunity_discovery as v1
import shared_sti2_v2_trajectory_heads as sti2

from qore.infrastructure.core_stack_v2.shared_global_opportunity_board import (
    SharedOpportunityBoardCandidate,
    build_global_opportunity_attention_board,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    assess_opportunity_trajectory,
)

IDENTITY = "QORE_SHARED_STI3_GLOBAL_OPPORTUNITY_BOARD_SOURCE_STRESS_001"
CONTRADICTION_UNCERTAINTY_STRESS_BPS = 2_000
FAILED_DATA_HEALTH_BPS = 9_000


def _candidate(
    *,
    partition: str,
    observation: SharedOpportunitySourceObservation,
    assessment: object,
    suffix: str,
) -> SharedOpportunityBoardCandidate:
    return SharedOpportunityBoardCandidate(
        candidate_id=f"{partition}:{suffix}:{observation.observation_id}",
        assessment=assessment,
        observed_at=observation.as_of,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        horizon="M1",
        data_health_bps=observation.data_integrity_bps,
        relevant_traders=(("VT31_NAS100",) if observation.asset == "NAS100" else ()),
        provenance_refs=tuple(
            sorted(
                set(
                    observation.provenance_refs
                    + (
                        "sti2-v2-frozen-trajectory-policy",
                        "sti3-source-stress-001",
                    )
                )
            )
        ),
    )


def _board(candidate: SharedOpportunityBoardCandidate):
    return build_global_opportunity_attention_board(
        board_id=f"board:{candidate.candidate_id}",
        as_of=candidate.observed_at,
        evidence_cutoff_at=candidate.evidence_cutoff_at,
        candidates=(candidate,),
    )


def _run(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: object,
) -> dict[str, object]:
    rows = v1._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    history: deque[SharedOpportunitySourceObservation] = deque(
        maxlen=policy.sequence_window
    )
    baseline_active = 0
    contradiction_checked = 0
    contradiction_nonincrease = 0
    data_health_checked = 0
    data_health_fail_closed = 0

    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("STI-3 stress must remain source-only")
        history.append(observation)
        assessment = assess_opportunity_trajectory(tuple(history), policy=policy)
        baseline = _board(
            _candidate(
                partition=partition,
                observation=observation,
                assessment=assessment,
                suffix="baseline",
            )
        )

        if baseline.entries:
            baseline_active += 1
            stressed_assessment = replace(
                assessment,
                contradiction_bps=min(
                    10_000,
                    assessment.contradiction_bps
                    + CONTRADICTION_UNCERTAINTY_STRESS_BPS,
                ),
                uncertainty_bps=min(
                    10_000,
                    assessment.uncertainty_bps
                    + CONTRADICTION_UNCERTAINTY_STRESS_BPS,
                ),
                reason_codes=tuple(
                    sorted(
                        set(
                            assessment.reason_codes
                            + (
                                "STRESS_CONTRADICTION_UP",
                                "STRESS_UNCERTAINTY_UP",
                            )
                        )
                    )
                ),
            )
            stressed = _board(
                _candidate(
                    partition=partition,
                    observation=observation,
                    assessment=stressed_assessment,
                    suffix="contradiction",
                )
            )
            contradiction_checked += 1
            if (
                not stressed.entries
                or stressed.entries[0].support_bps
                <= baseline.entries[0].support_bps
            ):
                contradiction_nonincrease += 1

        degraded = replace(
            observation,
            data_integrity_bps=FAILED_DATA_HEALTH_BPS,
        )
        degraded_history = tuple(history)[:-1] + (degraded,)
        degraded_assessment = assess_opportunity_trajectory(
            degraded_history,
            policy=policy,
        )
        degraded_board = _board(
            _candidate(
                partition=partition,
                observation=degraded,
                assessment=degraded_assessment,
                suffix="data-health",
            )
        )
        data_health_checked += 1
        if degraded_board.is_empty:
            data_health_fail_closed += 1

    if not rows:
        raise ValueError("STI-3 stress has no source observations")

    return {
        "partition": partition,
        "source_observation_count": len(rows),
        "baseline_active_entry_count": baseline_active,
        "contradiction_uncertainty_checked": contradiction_checked,
        "contradiction_uncertainty_nonincrease": contradiction_nonincrease,
        "contradiction_uncertainty_pass": (
            contradiction_checked > 0
            and contradiction_nonincrease == contradiction_checked
        ),
        "data_health_checked": data_health_checked,
        "data_health_fail_closed_count": data_health_fail_closed,
        "data_health_fail_closed_pass": (
            data_health_checked > 0
            and data_health_fail_closed == data_health_checked
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = sti2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _run(
            partition=partition,
            paths={
                "NAS100": getattr(args, f"{partition}_nas"),
                "SP500": getattr(args, f"{partition}_sp"),
                "US30": getattr(args, f"{partition}_us"),
            },
            policy=policy,
        )

    passed = all(
        row["contradiction_uncertainty_pass"]
        and row["data_health_fail_closed_pass"]
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI3_SOURCE_STRESS_PASS"
            if passed
            else "STI3_SOURCE_STRESS_FAIL"
        ),
        "r8_source_only_calibration": calibration,
        "stress": {
            "contradiction_uncertainty_add_bps": (
                CONTRADICTION_UNCERTAINTY_STRESS_BPS
            ),
            "failed_data_health_bps": FAILED_DATA_HEALTH_BPS,
        },
        "results": results,
        "proof": {
            "future_market_read": False,
            "future_outcome_read": False,
            "trader_methodology_read": False,
            "higher_contradiction_never_increases_board_support": all(
                row["contradiction_uncertainty_pass"]
                for row in results.values()
            ),
            "degraded_data_health_fails_closed": all(
                row["data_health_fail_closed_pass"]
                for row in results.values()
            ),
        },
        "governance": {
            "execution_authority": False,
            "capital_authority": False,
            "risk_authority": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"], "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
