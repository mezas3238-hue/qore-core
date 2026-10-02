#!/usr/bin/env python3
"""STI-6 V3 latent trajectory discovery and temporal validation.

R8 fits six source-only latent trajectory states without outcomes. R6 outcomes
are then used only to associate already-formed states with generic winners and
>=2R tails. Those state IDs are frozen before R5 temporal validation.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_continuation_latent_trajectory_v3 import (
    SharedLatentTrajectoryModel,
    assign_latent_trajectory_state,
    fit_latent_trajectory_model,
    trajectory_feature_vector,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)

IDENTITY = "QORE_SHARED_STI6_LATENT_TRAJECTORY_V3"
MIN_STATE_VISITORS = 10
CONTINUATION_STATE_WINNER_PRECISION_MIN_BPS = 6_000
TAIL_STATE_TAIL_PRECISION_MIN_BPS = 6_000


def _ratio(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _fit_r8_model(
    *,
    r8_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
) -> tuple[SharedLatentTrajectoryModel, dict[str, object]]:
    sequences = base._source_sequences(
        partition="r8",
        trades_path=r8_trades,
        nas_path=r8_nas,
        sp_path=r8_sp,
        us_path=r8_us,
    )
    rows: list[tuple[float, ...]] = []
    for sequence in sequences:
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        history: list[SharedPositionCausalObservation] = []
        for observation in observations:
            history.append(observation)
            rows.append(trajectory_feature_vector(tuple(history)))

    model = fit_latent_trajectory_model(rows)
    return model, {
        "r8_trade_count": len(sequences),
        "r8_source_state_rows": len(rows),
        "cluster_count": model.cluster_count,
        "iterations": model.iterations,
        "outcomes_used_for_state_formation": False,
        "future_market_used_for_state_formation": False,
        "model_fingerprint": model.fingerprint(),
    }


def _materialize_state_paths(
    *,
    partition: str,
    model: SharedLatentTrajectoryModel,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> tuple[dict[str, object], ...]:
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    materialized: list[dict[str, object]] = []
    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        history: list[SharedPositionCausalObservation] = []
        state_ids: list[str] = []
        for observation in observations:
            history.append(observation)
            state = assign_latent_trajectory_state(
                tuple(history),
                model=model,
            )
            state_ids.append(state.state_id)
        materialized.append(
            {
                "row": row,
                "state_ids": tuple(state_ids),
                "observation_count": len(observations),
            }
        )
    return tuple(materialized)


def _develop_state_mapping(
    materialized: tuple[dict[str, object], ...],
) -> dict[str, object]:
    visitors: dict[str, set[int]] = defaultdict(set)
    winners_by_state: dict[str, int] = defaultdict(int)
    tails_by_state: dict[str, int] = defaultdict(int)
    losses_by_state: dict[str, int] = defaultdict(int)
    total_winners = total_tails = total_losses = 0

    classified: list[tuple[int, set[str], bool, bool, bool]] = []
    for index, item in enumerate(materialized):
        row = cast(dict[str, object], item["row"])
        states = set(cast(tuple[str, ...], item["state_ids"]))
        # Outcome is touched only after the full latent-state path exists.
        final_r = Decimal(str(row["net_r_after_friction"]))
        winner = final_r > 0
        tail = final_r >= base.POSITIVE_TAIL_R
        loss = final_r < 0
        total_winners += int(winner)
        total_tails += int(tail)
        total_losses += int(loss)
        classified.append((index, states, winner, tail, loss))
        for state_id in states:
            visitors[state_id].add(index)
            winners_by_state[state_id] += int(winner)
            tails_by_state[state_id] += int(tail)
            losses_by_state[state_id] += int(loss)

    profiles: dict[str, dict[str, int]] = {}
    for state_id in sorted(visitors):
        count = len(visitors[state_id])
        profiles[state_id] = {
            "visitors": count,
            "winners": winners_by_state[state_id],
            "tails_ge_2r": tails_by_state[state_id],
            "losses": losses_by_state[state_id],
            "winner_precision_bps": _ratio(
                winners_by_state[state_id],
                count,
            ),
            "winner_recall_bps": _ratio(
                winners_by_state[state_id],
                total_winners,
            ),
            "tail_precision_bps": _ratio(
                tails_by_state[state_id],
                count,
            ),
            "tail_recall_bps": _ratio(
                tails_by_state[state_id],
                total_tails,
            ),
        }

    continuation_states = tuple(
        state_id
        for state_id, profile in sorted(profiles.items())
        if profile["visitors"] >= MIN_STATE_VISITORS
        and profile["winner_precision_bps"]
        >= CONTINUATION_STATE_WINNER_PRECISION_MIN_BPS
    )
    tail_states = tuple(
        state_id
        for state_id, profile in sorted(profiles.items())
        if profile["visitors"] >= MIN_STATE_VISITORS
        and profile["tail_precision_bps"]
        >= TAIL_STATE_TAIL_PRECISION_MIN_BPS
    )
    return {
        "state_profiles": profiles,
        "continuation_state_ids": continuation_states,
        "positive_tail_state_ids": tail_states,
        "development_population": {
            "trades": len(materialized),
            "winners": total_winners,
            "tails_ge_2r": total_tails,
            "losses": total_losses,
        },
        "mapping_frozen_after_r6": True,
    }


def _validate_partition(
    *,
    materialized: tuple[dict[str, object], ...],
    continuation_states: tuple[str, ...],
    tail_states: tuple[str, ...],
) -> dict[str, object]:
    cont_tp = cont_fp = cont_fn = 0
    tail_tp = tail_fp = tail_fn = 0
    continuation_signals = tail_signals = 0
    winners = tails = losses = 0
    continuation_leads: list[int] = []
    tail_leads: list[int] = []

    for item in materialized:
        row = cast(dict[str, object], item["row"])
        state_ids = cast(tuple[str, ...], item["state_ids"])
        observation_count = int(item["observation_count"])

        first_cont = next(
            (
                index
                for index, state_id in enumerate(state_ids)
                if state_id in continuation_states
            ),
            None,
        )
        first_tail = next(
            (
                index
                for index, state_id in enumerate(state_ids)
                if state_id in tail_states
            ),
            None,
        )

        # Terminal outcome touched after source-time state path and signals.
        final_r = Decimal(str(row["net_r_after_friction"]))
        winner = final_r > 0
        tail = final_r >= base.POSITIVE_TAIL_R
        loss = final_r < 0
        winners += int(winner)
        tails += int(tail)
        losses += int(loss)

        cont_signal = first_cont is not None
        tail_signal = first_tail is not None
        continuation_signals += int(cont_signal)
        tail_signals += int(tail_signal)

        if cont_signal and winner:
            cont_tp += 1
            continuation_leads.append(
                observation_count - 1 - cast(int, first_cont)
            )
        elif cont_signal and not winner:
            cont_fp += 1
        elif not cont_signal and winner:
            cont_fn += 1

        if tail_signal and tail:
            tail_tp += 1
            tail_leads.append(
                observation_count - 1 - cast(int, first_tail)
            )
        elif tail_signal and not tail:
            tail_fp += 1
        elif not tail_signal and tail:
            tail_fn += 1

    cont_precision = _ratio(cont_tp, cont_tp + cont_fp)
    cont_recall = _ratio(cont_tp, cont_tp + cont_fn)
    tail_precision = _ratio(tail_tp, tail_tp + tail_fp)
    tail_recall = _ratio(tail_tp, tail_tp + tail_fn)
    false_cont = _ratio(cont_fp, cont_tp + cont_fp)
    gate = (
        cont_precision >= base.STI6_WINNER_MIN_PRECISION_BPS
        and cont_recall >= base.STI6_WINNER_MIN_RECALL_BPS
        and tail_precision >= base.STI6_TAIL_MIN_PRECISION_BPS
        and tail_recall >= base.STI6_TAIL_MIN_RECALL_BPS
        and false_cont
        <= base.STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
    )
    return {
        "trade_count": len(materialized),
        "outcome_population": {
            "winners": winners,
            "tails_ge_2r": tails,
            "losses": losses,
        },
        "continuation_signal_count": continuation_signals,
        "positive_tail_signal_count": tail_signals,
        "winner_precision_bps": cont_precision,
        "winner_recall_bps": cont_recall,
        "positive_tail_precision_bps": tail_precision,
        "positive_tail_recall_bps": tail_recall,
        "false_continuation_on_nonwinners_bps": false_cont,
        "median_true_winner_lead_minutes": (
            None if not continuation_leads else median(continuation_leads)
        ),
        "median_true_tail_lead_minutes": (
            None if not tail_leads else median(tail_leads)
        ),
        "gate_pass": gate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model, fit = _fit_r8_model(
        r8_trades=args.r8_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
    )
    r6_materialized = _materialize_state_paths(
        partition="r6",
        model=model,
        trades=args.r6_trades,
        nas=args.r6_nas,
        sp=args.r6_sp,
        us=args.r6_us,
    )
    development = _develop_state_mapping(r6_materialized)
    continuation_states = cast(
        tuple[str, ...],
        development["continuation_state_ids"],
    )
    tail_states = cast(
        tuple[str, ...],
        development["positive_tail_state_ids"],
    )

    development_viable = bool(continuation_states and tail_states)
    if development_viable:
        r5_materialized = _materialize_state_paths(
            partition="r5",
            model=model,
            trades=args.r5_trades,
            nas=args.r5_nas,
            sp=args.r5_sp,
            us=args.r5_us,
        )
        r5 = _validate_partition(
            materialized=r5_materialized,
            continuation_states=continuation_states,
            tail_states=tail_states,
        )
        validation_pass = bool(r5["gate_pass"])
        r5_opened = True
    else:
        r5 = {
            "status": "NOT_OPENED_DEVELOPMENT_MAPPING_NOT_VIABLE",
            "gate_pass": False,
        }
        validation_pass = False
        r5_opened = False

    payload = {
        "identity": IDENTITY,
        "generation": "V3",
        "hypothesis": "UNSUPERVISED_LATENT_TRAJECTORY_STATES",
        "scientific_status": (
            "STI6_V3_TEMPORAL_VALIDATION_PASS_R5"
            if validation_pass
            else (
                "STI6_V3_FALSIFIED_R6_DEVELOPMENT_MAPPING"
                if not development_viable
                else "STI6_V3_FALSIFIED_R5_TEMPORAL_VALIDATION"
            )
        ),
        "value_demonstrated": validation_pass,
        "source_only_model_fit": fit,
        "model": {
            "model_id": model.model_id,
            "fingerprint": model.fingerprint(),
            "feature_names": model.feature_names,
            "means": model.means,
            "scales": model.scales,
            "centroids": model.centroids,
            "cluster_count": model.cluster_count,
            "iterations": model.iterations,
        },
        "r6_development_mapping": development,
        "r5_temporal_validation": r5,
        "frozen_gates": {
            "minimum_state_visitors": MIN_STATE_VISITORS,
            "continuation_state_winner_precision_bps_min": (
                CONTINUATION_STATE_WINNER_PRECISION_MIN_BPS
            ),
            "tail_state_tail_precision_bps_min": (
                TAIL_STATE_TAIL_PRECISION_MIN_BPS
            ),
            "winner_precision_bps_min": base.STI6_WINNER_MIN_PRECISION_BPS,
            "winner_recall_bps_min": base.STI6_WINNER_MIN_RECALL_BPS,
            "positive_tail_precision_bps_min": (
                base.STI6_TAIL_MIN_PRECISION_BPS
            ),
            "positive_tail_recall_bps_min": (
                base.STI6_TAIL_MIN_RECALL_BPS
            ),
            "false_continuation_on_nonwinners_bps_max": (
                base.STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
            ),
        },
        "governance": {
            "r8_outcomes_used_for_cluster_fit": False,
            "r6_outcomes_used_only_after_state_paths_materialized": True,
            "r6_used_for_state_mapping": True,
            "r5_used_for_cluster_fit": False,
            "r5_used_for_state_selection": False,
            "r5_opened": r5_opened,
            "future_market_used_for_inference": False,
            "v1_or_v2_threshold_rescue_used": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "scientific_status": payload["scientific_status"],
                "continuation_state_ids": continuation_states,
                "positive_tail_state_ids": tail_states,
                "r5": r5,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
