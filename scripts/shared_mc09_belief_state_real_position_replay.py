#!/usr/bin/env python3
"""Current real-data binding for MC-09 explicit belief state."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.causal_hypothesis_belief import (
    CausalHypothesisEvidence,
    accumulate_causal_hypotheses,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    continuation_source_scores,
)

IDENTITY = "QORE_SHARED_MC09_BELIEF_STATE_REAL_POSITION_REPLAY_001"


def _frame(observation: Any) -> CausalHypothesisEvidence:
    continuation, tail, failure, _coherence, uncertainty = (
        continuation_source_scores(observation)
    )
    no_event = max(0, 10_000 - max(continuation, tail, failure))
    return CausalHypothesisEvidence(
        as_of=observation.as_of,
        terminal_bps=failure,
        recovery_bps=continuation,
        target_bps=tail,
        no_event_bps=no_event,
        uncertainty_bps=uncertainty,
        data_integrity_bps=observation.data_integrity_bps,
    )


def _partition(
    *,
    partition: str,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> dict[str, object]:
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    if not sequences:
        raise ValueError(f"{partition}: no real position sequences")

    disposition_counts: Counter[str] = Counter()
    belief_count = 0
    deterministic_count = 0
    insufficient_count = 0
    future_or_outcome_used = False

    for sequence in sequences:
        observations = cast(tuple[Any, ...], sequence["observations"])
        frames: list[CausalHypothesisEvidence] = []
        for observation in observations:
            if (
                observation.future_market_used
                or observation.future_outcome_used
                or observation.pnl_used
            ):
                future_or_outcome_used = True
                raise AssertionError(
                    "MC-09 received non-source-time position evidence"
                )
            frames.append(_frame(observation))
            first = accumulate_causal_hypotheses(tuple(frames))
            second = accumulate_causal_hypotheses(tuple(frames))
            belief_count += 1
            if (
                first.terminal_bps == second.terminal_bps
                and first.recovery_bps == second.recovery_bps
                and first.target_bps == second.target_bps
                and first.no_event_bps == second.no_event_bps
                and first.confidence_bps == second.confidence_bps
                and first.disposition is second.disposition
            ):
                deterministic_count += 1
            disposition_counts[first.disposition.value] += 1
            insufficient_count += int(first.disposition.value == "INSUFFICIENT")
            if (
                first.outcome_used
                or first.pnl_used
                or first.future_market_used
                or first.sizing_authority
                or first.risk_authority
                or first.order_authority
                or first.stop_authority
                or first.target_authority
                or first.execution_authority
            ):
                raise AssertionError("MC-09 belief leaked forbidden authority")

    return {
        "partition": partition,
        "position_sequence_count": len(sequences),
        "belief_state_count": belief_count,
        "deterministic_count": deterministic_count,
        "deterministic_replay": deterministic_count == belief_count,
        "insufficient_count": insufficient_count,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "future_or_outcome_used": future_or_outcome_used,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for partition in ("r6", "r5"):
        results[partition] = _partition(
            partition=f"mc09_{partition}",
            trades=getattr(args, f"{partition}_trades"),
            nas=getattr(args, f"{partition}_nas"),
            sp=getattr(args, f"{partition}_sp"),
            us=getattr(args, f"{partition}_us"),
        )

    replay_pass = all(
        row["position_sequence_count"] > 0
        and row["belief_state_count"] > 0
        and row["deterministic_replay"]
        and row["future_or_outcome_used"] is False
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC09_BELIEF_STATE_ENGINE_REAL_DATA_BOUND_CAUSAL_REPLAY_PASS"
            if replay_pass
            else "MC09_BELIEF_STATE_REAL_REPLAY_FAIL"
        ),
        "results": results,
        "proof": {
            "real_position_sequences": replay_pass,
            "causal_source_only": replay_pass,
            "deterministic_replay": replay_pass,
            "future_market_used": False,
            "future_outcome_used": False,
            "pnl_used": False,
            "sovereign_authority": False,
        },
        "scientific_claims": {
            "belief_calibration_demonstrated": False,
            "oos_value_demonstrated": False,
            "mc09_completed_and_proven": False,
        },
        "governance": {
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": payload["status"], "results": results}, sort_keys=True))


if __name__ == "__main__":
    main()
