#!/usr/bin/env python3
"""STI-6 / STI-8 causal open-position intelligence replay.

R8 freezes source-only score thresholds. R6 evaluates the frozen engines.
R5 and protected certification holdouts remain closed. Terminal trade outcome
is read only after source-time engine outputs have been materialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_core_stack_v3_integrated_shared_intelligence_v1 as journey
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as counter
import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedContinuationPositiveTailPolicy,
    SharedPositionCausalObservation,
    assess_continuation_positive_tail,
    continuation_source_scores,
)
from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatPolicy,
    assess_position_threat,
    threat_source_score_bps,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

IDENTITY = "QORE_SHARED_STI6_STI8_REAL_POSITION_INTELLIGENCE_V1"
SCHEMA = "qore.shared.sti6_sti8.real_position_intelligence.v1"

STI6_WINNER_MIN_PRECISION_BPS = 6_000
STI6_WINNER_MIN_RECALL_BPS = 4_000
STI6_TAIL_MIN_PRECISION_BPS = 6_000
STI6_TAIL_MIN_RECALL_BPS = 3_000
STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS = 4_000

STI8_MIN_PRECISION_BPS = 6_000
STI8_MIN_RECALL_BPS = 4_000
STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS = 4_000
STI8_MAX_MISSED_LOSS_BPS = 6_000

POSITIVE_TAIL_R = Decimal("2.0")
THREAT_LEVELS = {
    SharedPositionThreatLevel.ELEVATED,
    SharedPositionThreatLevel.HIGH,
    SharedPositionThreatLevel.CRITICAL,
}


def _clip(value: int, low: int = 0, high: int = 10_000) -> int:
    return max(low, min(high, value))


def _decimal_bps(value: object, *, signed: bool = False) -> int:
    raw = int(Decimal(str(value)) * Decimal("10000"))
    return _clip(raw, -10_000, 10_000) if signed else _clip(raw)


def _reconstruct_source_partition(
    evidence_path: Path,
) -> dict[str, tuple[object, tuple[object, ...]]]:
    """Reconstruct methodology-valid setups without terminal-outcome filtering."""

    series, _, evidence, _, _, _ = journey.native.load_market_evidence(
        evidence_path
    )
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[journey.native._day(getattr(bar, "opened_at"))].append(bar)

    result: dict[str, tuple[object, tuple[object, ...]]] = {}
    execution_policy = Vt31R22ExecutionPolicy()
    for local_day in sorted(grouped):
        day_bars = tuple(
            sorted(
                grouped[local_day],
                key=lambda item: getattr(item, "opened_at"),
            )
        )
        reference = journey.specialist._slice(
            day_bars, (9, 0, 0), (10, 0, 0)
        )
        session = journey.specialist._slice(
            day_bars, (10, 0, 0), (11, 0, 0)
        )
        if len(reference) != 60 or len(session) != 60:
            continue
        prefix = list(reference)
        selected = None
        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=cast(Any, getattr(bar, "closed_at")),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if evaluation.both_sides_swept:
                    break
                continue
            executable, _ = make_executable_setup(
                evaluation.setup,
                execution_policy,
            )
            if executable is None:
                break
            selected = executable
            break
        if selected is None:
            continue
        signal = selected.decision_at.astimezone(UTC).isoformat()
        result[signal] = (selected, day_bars)
    return result


_SYNC_SUPPORT_BPS = {
    "BOTH_SUPPORT": 9_000,
    "MIXED_NEUTRAL": 5_000,
    "DIVERGENT": 4_000,
    "BOTH_ADVERSE": 1_000,
    "INCOMPLETE": 0,
}
_BREADTH_SUPPORT_BPS = {
    "3_SUPPORT": 10_000,
    "2_SUPPORT": 7_500,
    "NEUTRAL": 5_000,
    "SPLIT": 4_000,
    "2_ADVERSE": 2_500,
    "3_ADVERSE": 0,
}
_TRANSITION_ADVERSE_BPS = {
    "ADVERSE_ACCELERATING": 10_000,
    "REVERSING_TO_ADVERSE": 8_500,
    "ADVERSE": 7_000,
    "NEUTRAL": 4_000,
    "UNAVAILABLE": 5_000,
    "SUPPORTIVE": 2_000,
    "REVERSING_TO_SUPPORT": 1_000,
    "SUPPORT_ACCELERATING": 0,
}


def _build_observation(
    *,
    partition: str,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    snapshot_index: int,
    sp_by_day: dict[date, tuple[object, ...]],
    us_by_day: dict[date, tuple[object, ...]],
) -> SharedPositionCausalObservation:
    _, _, state = counter._state_signature(
        row=row,
        bars=list(day_bars),
        setup=setup,
        fill_index=fill_index,
        current_index=snapshot_index,
    )
    snapshot_bar = day_bars[snapshot_index]
    decision_at = cast(Any, getattr(snapshot_bar, "closed_at"))
    side = str(row["side"])
    local_day = date.fromisoformat(str(row["local_date"]))

    nas_observed = tuple(day_bars[fill_index : snapshot_index + 1])
    sp = v13._eligible(sp_by_day, local_day, decision_at)
    us = v13._eligible(us_by_day, local_day, decision_at)

    nas3 = v13._signed_move(nas_observed, side=side, window=3)
    sp3 = v13._signed_move(sp, side=side, window=3)
    sp10 = v13._signed_move(sp, side=side, window=10)
    us3 = v13._signed_move(us, side=side, window=3)
    us10 = v13._signed_move(us, side=side, window=10)

    sync = v13._sync(sp3, us3)
    breadth = v13._breadth((nas3, sp3, us3))
    sp_transition = v13._transition(sp3, sp10)
    us_transition = v13._transition(us3, us10)

    peer_confirmation = _SYNC_SUPPORT_BPS[sync]
    breadth_bps = _BREADTH_SUPPORT_BPS[breadth]
    peer_adverse = (
        _TRANSITION_ADVERSE_BPS[sp_transition]
        + _TRANSITION_ADVERSE_BPS[us_transition]
    ) // 2
    integrity = 10_000 if sp and us else 7_000

    efficiency = _decimal_bps(state["efficiency"], signed=True)
    overlap = _decimal_bps(state["overlap"])
    signed_close = _decimal_bps(state["close_r"], signed=True)
    signed_body = _decimal_bps(state["signed_body_r"], signed=True)
    progress = _decimal_bps(
        max(Decimal("0"), Decimal(str(state["progress_fraction"])))
    )
    positive_local = (
        max(0, efficiency)
        + max(0, signed_close)
        + (10_000 - overlap)
    ) // 3
    adverse_local = (
        max(0, -efficiency)
        + max(0, -signed_close)
        + overlap
    ) // 3
    world_support = (
        positive_local + peer_confirmation + breadth_bps + (10_000 - peer_adverse)
    ) // 4
    world_fragility = (
        adverse_local
        + peer_adverse
        + (10_000 - peer_confirmation)
        + (10_000 - breadth_bps)
    ) // 4

    signal = str(row["signal_at"])
    return SharedPositionCausalObservation(
        observation_id=(
            f"{partition}:{signal}:{int(state['minutes_since_fill'])}"
        ),
        position_id=signal,
        asset="NAS100",
        as_of=decision_at,
        evidence_cutoff_at=decision_at,
        minutes_since_fill=int(state["minutes_since_fill"]),
        progress_bps=progress,
        signed_close_r_bps=signed_close,
        efficiency_bps=efficiency,
        overlap_bps=overlap,
        signed_body_r_bps=signed_body,
        peer_confirmation_bps=peer_confirmation,
        breadth_bps=breadth_bps,
        peer_transition_adverse_bps=peer_adverse,
        world_support_bps=world_support,
        world_fragility_bps=world_fragility,
        data_integrity_bps=integrity,
        provenance_refs=tuple(
            sorted(
                (
                    f"immutable-{partition}-NAS100-M1",
                    f"immutable-{partition}-SP500-M1",
                    f"immutable-{partition}-US30-M1",
                    "vt31-methodology-valid-open-position",
                )
            )
        ),
    )


def _source_sequences(
    *,
    partition: str,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> tuple[dict[str, object], ...]:
    rows = journey.v3._load_trades(trades_path)
    paths = _reconstruct_source_partition(nas_path)
    sp_by_day = v13._group_market(sp_path)
    us_by_day = v13._group_market(us_path)

    sequences: list[dict[str, object]] = []
    for row in rows:
        signal = str(row["signal_at"])
        if signal not in paths:
            raise AssertionError(
                f"source reconstruction missing methodology-valid signal {signal}"
            )
        setup, day_bars = paths[signal]
        fill_index, exit_index = counter._fill_and_exit_indices(
            setup,
            day_bars,
            row,
        )
        observations = tuple(
            _build_observation(
                partition=partition,
                row=row,
                setup=setup,
                day_bars=day_bars,
                fill_index=fill_index,
                snapshot_index=snapshot_index,
                sp_by_day=sp_by_day,
                us_by_day=us_by_day,
            )
            for snapshot_index in range(fill_index + 1, exit_index)
        )
        sequences.append(
            {
                "signal_at": signal,
                "row": row,
                "observations": observations,
                "open_position_observation_count": len(observations),
            }
        )
    return tuple(sequences)


def _quantile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("source-only position intelligence has no scores")
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _strict_thresholds(
    values: list[int],
    fractions: tuple[float, ...],
) -> tuple[int, ...]:
    distinct = sorted(set(values))
    if len(distinct) < len(fractions):
        raise ValueError("source-only score distribution lacks diversity")
    selected = [_quantile(distinct, fraction) for fraction in fractions]
    if len(set(selected)) == len(selected):
        return tuple(selected)
    return tuple(distinct[-len(fractions) :])


def _policy_fingerprint(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def freeze_policies(
    *,
    r8_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
) -> dict[str, object]:
    sequences = _source_sequences(
        partition="r8",
        trades_path=r8_trades,
        nas_path=r8_nas,
        sp_path=r8_sp,
        us_path=r8_us,
    )
    observations = [
        observation
        for sequence in sequences
        for observation in cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
    ]
    continuation_scores = [
        continuation_source_scores(item)[0] for item in observations
    ]
    tail_scores = [
        continuation_source_scores(item)[1] for item in observations
    ]
    threat_scores = [
        threat_source_score_bps(item)[0] for item in observations
    ]

    continuation_threshold = _quantile(continuation_scores, 0.75)
    positive_tail_threshold = _quantile(tail_scores, 0.90)
    if continuation_threshold >= positive_tail_threshold:
        distinct = sorted(set(continuation_scores + tail_scores))
        continuation_threshold, positive_tail_threshold = (
            distinct[-2],
            distinct[-1],
        )

    moderate, elevated, high, critical = _strict_thresholds(
        threat_scores,
        (0.60, 0.75, 0.90, 0.97),
    )
    sti6_policy = {
        "policy_id": "QORE_SHARED_STI6_SOURCE_ONLY_POLICY_V1",
        "continuation_threshold_bps": continuation_threshold,
        "positive_tail_threshold_bps": positive_tail_threshold,
        "minimum_integrity_bps": 9_500,
        "source_only_calibration": True,
        "evidence_refs": ["immutable-r8-open-position-source-score-distribution"],
    }
    sti8_policy = {
        "policy_id": "QORE_SHARED_STI8_SOURCE_ONLY_POLICY_V1",
        "moderate_threshold_bps": moderate,
        "elevated_threshold_bps": elevated,
        "high_threshold_bps": high,
        "critical_threshold_bps": critical,
        "minimum_integrity_bps": 9_500,
        "source_only_calibration": True,
        "evidence_refs": ["immutable-r8-open-position-threat-score-distribution"],
    }
    # Instantiate to enforce engine invariants before sealing.
    SharedContinuationPositiveTailPolicy(
        **{
            **sti6_policy,
            "evidence_refs": tuple(sti6_policy["evidence_refs"]),
        }
    )
    SharedPositionThreatPolicy(
        **{
            **sti8_policy,
            "evidence_refs": tuple(sti8_policy["evidence_refs"]),
        }
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "mode": "SOURCE_ONLY_POLICY_FREEZE",
        "r8_trade_count": len(sequences),
        "r8_source_observation_count": len(observations),
        "sti6_policy": sti6_policy,
        "sti6_policy_fingerprint": _policy_fingerprint(sti6_policy),
        "sti8_policy": sti8_policy,
        "sti8_policy_fingerprint": _policy_fingerprint(sti8_policy),
        "future_market_data_read_for_freeze": False,
        "future_trade_outcomes_read_for_freeze": False,
        "pnl_used_for_freeze": False,
        "r5_opened": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
    }


def _sti6_policy(payload: dict[str, object]) -> SharedContinuationPositiveTailPolicy:
    raw = cast(dict[str, object], payload["sti6_policy"])
    if _policy_fingerprint(raw) != payload["sti6_policy_fingerprint"]:
        raise ValueError("STI-6 frozen policy fingerprint mismatch")
    return SharedContinuationPositiveTailPolicy(
        policy_id=str(raw["policy_id"]),
        continuation_threshold_bps=int(raw["continuation_threshold_bps"]),
        positive_tail_threshold_bps=int(raw["positive_tail_threshold_bps"]),
        minimum_integrity_bps=int(raw["minimum_integrity_bps"]),
        source_only_calibration=bool(raw["source_only_calibration"]),
        evidence_refs=tuple(cast(list[str], raw["evidence_refs"])),
    )


def _sti8_policy(payload: dict[str, object]) -> SharedPositionThreatPolicy:
    raw = cast(dict[str, object], payload["sti8_policy"])
    if _policy_fingerprint(raw) != payload["sti8_policy_fingerprint"]:
        raise ValueError("STI-8 frozen policy fingerprint mismatch")
    return SharedPositionThreatPolicy(
        policy_id=str(raw["policy_id"]),
        moderate_threshold_bps=int(raw["moderate_threshold_bps"]),
        elevated_threshold_bps=int(raw["elevated_threshold_bps"]),
        high_threshold_bps=int(raw["high_threshold_bps"]),
        critical_threshold_bps=int(raw["critical_threshold_bps"]),
        minimum_integrity_bps=int(raw["minimum_integrity_bps"]),
        source_only_calibration=bool(raw["source_only_calibration"]),
        evidence_refs=tuple(cast(list[str], raw["evidence_refs"])),
    )


def _ratio_bps(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def evaluate(
    *,
    frozen: dict[str, object],
    r6_trades: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
) -> dict[str, object]:
    sti6_policy = _sti6_policy(frozen)
    sti8_policy = _sti8_policy(frozen)
    sequences = _source_sequences(
        partition="r6",
        trades_path=r6_trades,
        nas_path=r6_nas,
        sp_path=r6_sp,
        us_path=r6_us,
    )

    winners = tails = losses = 0
    continuation_signals = tail_signals = threat_signals = 0
    continuation_tp = continuation_fp = continuation_fn = 0
    tail_tp = tail_fp = tail_fn = 0
    threat_tp = threat_fp = threat_fn = 0
    continuation_leads: list[int] = []
    tail_leads: list[int] = []
    threat_leads: list[int] = []
    source_observation_count = 0

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        source_observation_count += len(observations)

        # Outcome is intentionally touched only after all source observations
        # have been created.
        final_r = Decimal(str(row["net_r_after_friction"]))
        is_winner = final_r > 0
        is_tail = final_r >= POSITIVE_TAIL_R
        is_loss = final_r < 0
        winners += int(is_winner)
        tails += int(is_tail)
        losses += int(is_loss)

        first_continuation = None
        first_tail = None
        first_threat = None
        for index, observation in enumerate(observations):
            continuation = assess_continuation_positive_tail(
                observation,
                policy=sti6_policy,
            )
            if first_continuation is None and continuation.materially_supported:
                first_continuation = index
            if first_tail is None and continuation.positive_tail_candidate:
                first_tail = index

            threat = assess_position_threat(
                observation,
                policy=sti8_policy,
            )
            if first_threat is None and threat.threat_level in THREAT_LEVELS:
                first_threat = index

        continuation_signal = first_continuation is not None
        tail_signal = first_tail is not None
        threat_signal = first_threat is not None
        continuation_signals += int(continuation_signal)
        tail_signals += int(tail_signal)
        threat_signals += int(threat_signal)

        if continuation_signal and is_winner:
            continuation_tp += 1
            continuation_leads.append(len(observations) - 1 - cast(int, first_continuation))
        elif continuation_signal and not is_winner:
            continuation_fp += 1
        elif not continuation_signal and is_winner:
            continuation_fn += 1

        if tail_signal and is_tail:
            tail_tp += 1
            tail_leads.append(len(observations) - 1 - cast(int, first_tail))
        elif tail_signal and not is_tail:
            tail_fp += 1
        elif not tail_signal and is_tail:
            tail_fn += 1

        if threat_signal and is_loss:
            threat_tp += 1
            threat_leads.append(len(observations) - 1 - cast(int, first_threat))
        elif threat_signal and not is_loss:
            threat_fp += 1
        elif not threat_signal and is_loss:
            threat_fn += 1

    cont_precision = _ratio_bps(
        continuation_tp,
        continuation_tp + continuation_fp,
    )
    cont_recall = _ratio_bps(
        continuation_tp,
        continuation_tp + continuation_fn,
    )
    tail_precision = _ratio_bps(tail_tp, tail_tp + tail_fp)
    tail_recall = _ratio_bps(tail_tp, tail_tp + tail_fn)
    false_cont_on_losses = _ratio_bps(
        continuation_fp,
        continuation_tp + continuation_fp,
    )

    threat_precision = _ratio_bps(threat_tp, threat_tp + threat_fp)
    threat_recall = _ratio_bps(threat_tp, threat_tp + threat_fn)
    false_threat_on_winners = _ratio_bps(
        threat_fp,
        threat_tp + threat_fp,
    )
    missed_loss = _ratio_bps(threat_fn, threat_tp + threat_fn)

    sti6_gate = (
        cont_precision >= STI6_WINNER_MIN_PRECISION_BPS
        and cont_recall >= STI6_WINNER_MIN_RECALL_BPS
        and tail_precision >= STI6_TAIL_MIN_PRECISION_BPS
        and tail_recall >= STI6_TAIL_MIN_RECALL_BPS
        and false_cont_on_losses <= STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
    )
    sti8_gate = (
        threat_precision >= STI8_MIN_PRECISION_BPS
        and threat_recall >= STI8_MIN_RECALL_BPS
        and false_threat_on_winners <= STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS
        and missed_loss <= STI8_MAX_MISSED_LOSS_BPS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "mode": "CAUSAL_OPEN_POSITION_REPLAY",
        "engine_state": (
            "ENGINE_IMPLEMENTED_REAL_DATA_BOUND_CAUSAL_REPLAY_EXECUTED"
        ),
        "r6_trade_count": len(sequences),
        "r6_source_observation_count": source_observation_count,
        "outcome_population": {
            "winners": winners,
            "positive_tail_ge_2r": tails,
            "losses": losses,
        },
        "sti6": {
            "signal_value_status": (
                "SIGNAL_VALUE_DEMONSTRATED_R6"
                if sti6_gate
                else "STI6_V1_FALSIFIED_ON_CONSUMED_R6"
            ),
            "economic_position_management_value_proven": False,
            "continuation_signal_count": continuation_signals,
            "positive_tail_signal_count": tail_signals,
            "winner_precision_bps": cont_precision,
            "winner_recall_bps": cont_recall,
            "positive_tail_precision_bps": tail_precision,
            "positive_tail_recall_bps": tail_recall,
            "false_continuation_on_nonwinners_bps": false_cont_on_losses,
            "median_true_winner_lead_minutes": (
                None if not continuation_leads else median(continuation_leads)
            ),
            "median_true_tail_lead_minutes": (
                None if not tail_leads else median(tail_leads)
            ),
            "gate_pass": sti6_gate,
        },
        "sti8": {
            "signal_value_status": (
                "SIGNAL_VALUE_DEMONSTRATED_R6"
                if sti8_gate
                else "STI8_V1_FALSIFIED_ON_CONSUMED_R6"
            ),
            "economic_position_management_value_proven": False,
            "threat_signal_count": threat_signals,
            "loss_precision_bps": threat_precision,
            "loss_recall_bps": threat_recall,
            "false_threat_on_nonlosses_bps": false_threat_on_winners,
            "missed_loss_bps": missed_loss,
            "median_true_threat_lead_minutes": (
                None if not threat_leads else median(threat_leads)
            ),
            "gate_pass": sti8_gate,
        },
        "frozen_gates": {
            "sti6_winner_min_precision_bps": STI6_WINNER_MIN_PRECISION_BPS,
            "sti6_winner_min_recall_bps": STI6_WINNER_MIN_RECALL_BPS,
            "sti6_tail_min_precision_bps": STI6_TAIL_MIN_PRECISION_BPS,
            "sti6_tail_min_recall_bps": STI6_TAIL_MIN_RECALL_BPS,
            "sti6_max_false_continuation_on_losers_bps": (
                STI6_MAX_FALSE_CONTINUATION_ON_LOSERS_BPS
            ),
            "sti8_min_precision_bps": STI8_MIN_PRECISION_BPS,
            "sti8_min_recall_bps": STI8_MIN_RECALL_BPS,
            "sti8_max_false_threat_on_winners_bps": (
                STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS
            ),
            "sti8_max_missed_loss_bps": STI8_MAX_MISSED_LOSS_BPS,
            "positive_tail_r": str(POSITIVE_TAIL_R),
        },
        "source_only_engine": True,
        "future_data_used_for_intelligence": False,
        "terminal_outcome_used_offline_for_evaluation": True,
        "outcome_used_for_policy_freeze": False,
        "r5_opened": False,
        "protected_holdout_opened": False,
        "trader_methodology_mutated": False,
        "mandatory_hold_or_exit_authority": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("freeze", "evaluate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    for partition in ("r8", "r6"):
        parser.add_argument(f"--{partition}-trades", type=Path)
        parser.add_argument(f"--{partition}-nas", type=Path)
        parser.add_argument(f"--{partition}-sp", type=Path)
        parser.add_argument(f"--{partition}-us", type=Path)
    args = parser.parse_args()

    if args.mode == "freeze":
        required = (
            args.r8_trades,
            args.r8_nas,
            args.r8_sp,
            args.r8_us,
        )
        if any(item is None for item in required):
            raise SystemExit("freeze requires R8 trades + NAS/SP/US evidence")
        payload = freeze_policies(
            r8_trades=cast(Path, args.r8_trades),
            r8_nas=cast(Path, args.r8_nas),
            r8_sp=cast(Path, args.r8_sp),
            r8_us=cast(Path, args.r8_us),
        )
    else:
        required = (
            args.policy,
            args.r6_trades,
            args.r6_nas,
            args.r6_sp,
            args.r6_us,
        )
        if any(item is None for item in required):
            raise SystemExit("evaluate requires policy + R6 evidence")
        frozen = json.loads(cast(Path, args.policy).read_text())
        payload = evaluate(
            frozen=frozen,
            r6_trades=cast(Path, args.r6_trades),
            r6_nas=cast(Path, args.r6_nas),
            r6_sp=cast(Path, args.r6_sp),
            r6_us=cast(Path, args.r6_us),
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "mode": payload["mode"],
                "engine_state": payload.get("engine_state"),
                "sti6": payload.get("sti6"),
                "sti8": payload.get("sti8"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
