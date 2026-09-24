"""Shared Hypothesis-First Decision Intelligence V7 for VT31 NAS100.

Evidence order:
CURRENT M1 PERCEPTION
-> competing current-market hypotheses
-> historical memory as secondary confirmation
-> PASS / ABSTAIN shadow decision.

For VT31, adverse pre-reversal movement is not automatically contradictory.
The current hypothesis ensemble distinguishes reversal formation from adverse
continuation, range noise and anomaly before historical evidence is consulted.

No journey management, no capital/risk weighting, no current/future outcome
feature. R8 -> memory, R6 -> calibration/freeze, R5 -> no-retune evaluation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_core_stack_v3_perception_first_v6 as v6

from qore.infrastructure.core_stack_v2.analog_memory import CausalAnalogMemory
from qore.infrastructure.core_stack_v2.hypothesis_ensemble import (
    HypothesisEnsemble,
    MarketHypothesis,
    evaluate_reversal_hypotheses,
)

SCHEMA = "qore.core_stack_v3.vt31.hypothesis_first.v7"
IDENTITY = "VT31_NAS100_SHARED_HYPOTHESIS_FIRST_DECISION_V7"

HYPOTHESIS_FIELDS = (
    "side",
    "entry_family",
    "hypothesis_primary",
    "hypothesis_reversal_bucket",
    "hypothesis_continuation_bucket",
    "hypothesis_range_bucket",
    "hypothesis_anomaly_bucket",
    "perception_sweep_recovery",
    "perception_cross_market",
    "perception_compression_expansion",
    "prior_nas100_regime",
    "peer_consensus",
)


def _bucket(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    if value == 3:
        return "3"
    return "4_plus"


@dataclass(frozen=True, slots=True)
class Policy:
    memory_policy: ev.Policy
    reversal_rescue_min: int
    reversal_margin_min: int
    continuation_reject_min: int
    continuation_margin_min: int
    range_reject_min: int
    anomaly_reject_min: int
    hypothesis_memory_conflict_ev: Decimal
    hypothesis_memory_min_confidence_bps: int
    severe_continuation_reject: bool

    def payload(self) -> dict[str, object]:
        return {
            "memory_policy": self.memory_policy.payload(),
            "reversal_rescue_min": self.reversal_rescue_min,
            "reversal_margin_min": self.reversal_margin_min,
            "continuation_reject_min": self.continuation_reject_min,
            "continuation_margin_min": self.continuation_margin_min,
            "range_reject_min": self.range_reject_min,
            "anomaly_reject_min": self.anomaly_reject_min,
            "hypothesis_memory_conflict_ev": format(
                self.hypothesis_memory_conflict_ev, "f"
            ),
            "hypothesis_memory_min_confidence_bps": (
                self.hypothesis_memory_min_confidence_bps
            ),
            "severe_continuation_reject": self.severe_continuation_reject,
        }


MEMORY_POLICIES = (
    ev.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        conflict_ev_r=conflict,
        favorable_ev_r=Decimal("0.30"),
        minimum_negative_views=2,
        caution_multiplier=Decimal("0.50"),
    )
    for conflict in (Decimal("-0.05"), Decimal("-0.10"))
)

POLICIES = tuple(
    Policy(
        memory_policy=memory,
        reversal_rescue_min=reversal,
        reversal_margin_min=margin,
        continuation_reject_min=continuation,
        continuation_margin_min=margin,
        range_reject_min=range_min,
        anomaly_reject_min=anomaly_min,
        hypothesis_memory_conflict_ev=hypothesis_ev,
        hypothesis_memory_min_confidence_bps=1500,
        severe_continuation_reject=severe,
    )
    for memory in MEMORY_POLICIES
    for reversal in (4, 5, 6)
    for margin in (1, 2)
    for continuation in (3, 4, 5)
    for range_min in (2, 3)
    for anomaly_min in (3, 4)
    for hypothesis_ev in (Decimal("-0.05"), Decimal("0"))
    for severe in (False, True)
)


def _annotate(
    rows: list[dict[str, object]],
    *,
    nas_path: Path,
    sp500_path: Path,
    us30_path: Path,
) -> list[dict[str, object]]:
    nas = v6._load_index(nas_path)
    sp500 = v6._load_index(sp500_path)
    us30 = v6._load_index(us30_path)
    output: list[dict[str, object]] = []

    for source in rows:
        row = dict(source)
        perception = v6._perception_for(
            row,
            nas=nas,
            sp500=sp500,
            us30=us30,
        )
        hypotheses = evaluate_reversal_hypotheses(perception)
        row.update(
            {
                "perception_trend": perception.trend_state.value,
                "perception_volatility": perception.volatility_state.value,
                "perception_compression_expansion": (
                    perception.compression_expansion_state.value
                ),
                "perception_displacement": perception.displacement_state.value,
                "perception_sweep_recovery": (
                    perception.sweep_recovery_state.value
                ),
                "perception_cross_market": (
                    perception.cross_market_state.value
                ),
                "perception_anomaly": perception.anomaly_state.value,
                "hypothesis_primary": hypotheses.primary.value,
                "hypothesis_reversal_score": hypotheses.reversal_score,
                "hypothesis_continuation_score": (
                    hypotheses.continuation_against_score
                ),
                "hypothesis_range_score": hypotheses.range_noise_score,
                "hypothesis_anomaly_score": hypotheses.anomaly_score,
                "hypothesis_reversal_bucket": _bucket(
                    hypotheses.reversal_score
                ),
                "hypothesis_continuation_bucket": _bucket(
                    hypotheses.continuation_against_score
                ),
                "hypothesis_range_bucket": _bucket(
                    hypotheses.range_noise_score
                ),
                "hypothesis_anomaly_bucket": _bucket(
                    hypotheses.anomaly_score
                ),
                "hypothesis_evidence": hypotheses.evidence,
            }
        )
        output.append(row)
    return output


def _memories(
    rows: list[dict[str, object]],
) -> dict[str, CausalAnalogMemory]:
    result = {
        name: ev._memory(rows, fields)
        for name, fields in ev.VIEWS.items()
    }
    result["HYPOTHESIS"] = ev._memory(rows, HYPOTHESIS_FIELDS)
    return result


def _historical_view(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    negative = positive = 0
    weighted_ev = Decimal(0)
    weight_sum = Decimal(0)
    details: dict[str, object] = {}

    for name, fields in ev.VIEWS.items():
        item = ev._analog_economics(
            memories[name],
            row,
            fields,
            policy.memory_policy,
        )
        details[name] = item
        raw = item["ev_r"]
        if raw is None:
            continue
        confidence = int(item["confidence_bps"])
        effective_n = v3._d(item["effective_n"])
        if (
            confidence < policy.memory_policy.minimum_confidence_bps
            or effective_n < Decimal("6")
        ):
            continue
        value = v3._d(raw)
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += value * weight
        weight_sum += weight
        if value < policy.memory_policy.conflict_ev_r:
            negative += 1
        if value >= policy.memory_policy.favorable_ev_r:
            positive += 1

    ensemble = None if weight_sum == 0 else weighted_ev / weight_sum
    return {
        "negative_views": negative,
        "positive_views": positive,
        "ensemble_ev_r": (
            None if ensemble is None else format(ensemble, "f")
        ),
        "details": details,
    }


def _hypothesis_memory(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    item = ev._analog_economics(
        memories["HYPOTHESIS"],
        row,
        HYPOTHESIS_FIELDS,
        policy.memory_policy,
    )
    raw = item["ev_r"]
    negative = (
        raw is not None
        and int(item["confidence_bps"])
        >= policy.hypothesis_memory_min_confidence_bps
        and v3._d(item["effective_n"]) >= Decimal("4")
        and v3._d(raw) < policy.hypothesis_memory_conflict_ev
    )
    positive = (
        raw is not None
        and int(item["confidence_bps"])
        >= policy.hypothesis_memory_min_confidence_bps
        and v3._d(item["effective_n"]) >= Decimal("4")
        and v3._d(raw) >= Decimal("0.20")
    )
    return {**item, "negative": negative, "positive": positive}


def _current_hypotheses(
    row: dict[str, object],
) -> HypothesisEnsemble:
    primary = MarketHypothesis(str(row["hypothesis_primary"]))
    evidence_raw = row.get("hypothesis_evidence", ())
    return HypothesisEnsemble(
        primary=primary,
        reversal_score=int(row["hypothesis_reversal_score"]),
        continuation_against_score=int(
            row["hypothesis_continuation_score"]
        ),
        range_noise_score=int(row["hypothesis_range_score"]),
        anomaly_score=int(row["hypothesis_anomaly_score"]),
        evidence=tuple(cast(tuple[str, ...], evidence_raw)),
    )


def _decide(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    current = _current_hypotheses(row)
    historical = _historical_view(memories, row, policy)
    hypothesis_memory = _hypothesis_memory(memories, row, policy)

    reversal_rescue = (
        current.reversal_score >= policy.reversal_rescue_min
        and (
            current.reversal_score
            - current.continuation_against_score
        )
        >= policy.reversal_margin_min
        and current.reversal_score > current.range_noise_score
    )

    continuation_current = (
        current.continuation_against_score
        >= policy.continuation_reject_min
        and (
            current.continuation_against_score
            - current.reversal_score
        )
        >= policy.continuation_margin_min
    )
    range_current = (
        current.range_noise_score >= policy.range_reject_min
        and current.reversal_score <= current.range_noise_score
    )
    anomaly_current = (
        current.anomaly_score >= policy.anomaly_reject_min
        and current.reversal_score <= current.continuation_against_score
    )

    historical_negative = (
        int(historical["negative_views"])
        >= policy.memory_policy.minimum_negative_views
        and int(historical["positive_views"]) == 0
    )

    secondary_negative = (
        historical_negative or bool(hypothesis_memory["negative"])
    )
    current_bad = continuation_current or range_current or anomaly_current

    severe_continuation = (
        policy.severe_continuation_reject
        and current.continuation_against_score
        >= policy.continuation_reject_min + 2
        and current.reversal_score == 0
    )

    reject = (
        (current_bad and secondary_negative)
        or severe_continuation
    )

    # Current reversal evidence has priority over stale negative history.
    if reversal_rescue:
        reject = False

    # Positive memory cannot create a reversal hypothesis but may preserve an
    # unresolved current state from being rejected solely for anomaly/range.
    if (
        bool(hypothesis_memory["positive"])
        and not continuation_current
    ):
        reject = False

    return {
        "action": "ABSTAIN_SHADOW" if reject else "PASS",
        "current_primary": current.primary.value,
        "reversal_rescue": reversal_rescue,
        "current_bad": current_bad,
        "continuation_current": continuation_current,
        "range_current": range_current,
        "anomaly_current": anomaly_current,
        "severe_continuation": severe_continuation,
        "historical": historical,
        "hypothesis_memory": hypothesis_memory,
    }


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    memories = _memories(history)
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescue_count = 0
    primary_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = v3._d(row["net_r_after_friction"])
        baseline_values.append(value)
        verdict = _decide(memories, row, policy)
        primary = str(verdict["current_primary"])
        primary_counts[primary] = primary_counts.get(primary, 0) + 1
        if bool(verdict["reversal_rescue"]):
            rescue_count += 1
        for key in (
            "continuation_current",
            "range_current",
            "anomaly_current",
            "severe_continuation",
        ):
            if bool(verdict[key]):
                reason_counts[key] = reason_counts.get(key, 0) + 1
        if verdict["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
        else:
            kept_values.append(value)

    baseline = v6._metrics(baseline_values)
    shared = v6._metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0
        for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0
        for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    sacrificed_r = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in abstained
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    return {
        "baseline": baseline,
        "shared": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if base_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(base_losses),
                    "f",
                )
            ),
            "winner_count_retention": (
                "0"
                if base_wins == 0
                else format(
                    Decimal(base_wins - winners_sacrificed)
                    / Decimal(base_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1"
                if gross_winner_r == 0
                else format(
                    (gross_winner_r - sacrificed_r) / gross_winner_r,
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(
                    Decimal(len(kept_values)) / Decimal(len(rows)),
                    "f",
                )
            ),
            "reversal_rescue_count": rescue_count,
            "primary_hypothesis_counts": dict(sorted(primary_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    return v6._gates(result)


def _score(result: dict[str, object]) -> Decimal | None:
    return v6._score(result)


def run(
    *,
    r8_json: Path,
    r6_json: Path,
    r5_json: Path,
    daily_path: Path,
    r8_nas: Path,
    r8_sp500: Path,
    r8_us30: Path,
    r6_nas: Path,
    r6_sp500: Path,
    r6_us30: Path,
    r5_nas: Path,
    r5_sp500: Path,
    r5_us30: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = v3._decorate(v3._load_trades(r8_json), daily)
    r6 = v3._decorate(v3._load_trades(r6_json), daily)
    r5 = v3._decorate(v3._load_trades(r5_json), daily)

    r8 = _annotate(
        r8, nas_path=r8_nas, sp500_path=r8_sp500, us30_path=r8_us30
    )
    r6 = _annotate(
        r6, nas_path=r6_nas, sp500_path=r6_sp500, us30_path=r6_us30
    )
    r5 = _annotate(
        r5, nas_path=r5_nas, sp500_path=r5_sp500, us30_path=r5_us30
    )

    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        calibration = _evaluate(r8, r6, policy)
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append(
            {
                "policy": policy.payload(),
                "calibration": calibration,
                "gates": gates,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared_hypothesis": False,
            "frontier": frontier,
            "governance": {
                "perception_precedes_hypothesis": True,
                "hypothesis_precedes_memory": True,
                "memory_can_create_current_evidence": False,
                "memory_can_reject_alone": False,
                "current_outcome_used": False,
                "journey_management_used": False,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(r8 + r6, r5, frozen)
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "PERCEPTION_HYPOTHESIS_MEMORY",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_hypothesis": passed,
        "frontier": frontier,
        "governance": {
            "perception_precedes_hypothesis": True,
            "hypothesis_precedes_memory": True,
            "memory_can_create_current_evidence": False,
            "memory_can_reject_alone": False,
            "current_outcome_used": False,
            "journey_management_used": False,
            "capital_risk_weighting_used": False,
            "r5_retuned": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-json", type=Path, required=True)
    parser.add_argument("--r6-json", type=Path, required=True)
    parser.add_argument("--r5-json", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    for partition in ("r8", "r6", "r5"):
        for market in ("nas", "sp500", "us30"):
            parser.add_argument(
                f"--{partition}-{market}",
                type=Path,
                required=True,
            )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
        r8_nas=args.r8_nas,
        r8_sp500=args.r8_sp500,
        r8_us30=args.r8_us30,
        r6_nas=args.r6_nas,
        r6_sp500=args.r6_sp500,
        r6_us30=args.r6_us30,
        r5_nas=args.r5_nas,
        r5_sp500=args.r5_sp500,
        r5_us30=args.r5_us30,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared_hypothesis": payload[
                    "passes_shared_hypothesis"
                ],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
