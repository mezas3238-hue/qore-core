"""Shared Journey Intelligence V3 with independent EXTEND/DEFEND heads.

V2 proved that the two journey actions have different evidence-density needs.
V3 shares one causal market-state memory but calibrates:
- EXTENSION HEAD independently;
- DEFENSE HEAD independently.

R8 memory -> R6 joint freeze -> R5 no-retune.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_integrated_shared_intelligence_v1 as v1
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as v2
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.journey_split_heads.v3"
IDENTITY = "VT31_NAS100_SHARED_JOURNEY_SPLIT_HEADS_V3"
FRICTION = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class SplitPolicy:
    extension_reference_fraction: Decimal
    extend_minimum_samples: int
    extend_minimum_positive_rate: Decimal
    extend_min_mean_uplift_r: Decimal
    extend_min_progress_fraction: Decimal
    defend_minimum_samples: int
    defend_minimum_positive_rate: Decimal
    defend_min_mean_uplift_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "extension_reference_fraction": format(
                self.extension_reference_fraction, "f"
            ),
            "extend_minimum_samples": self.extend_minimum_samples,
            "extend_minimum_positive_rate": format(
                self.extend_minimum_positive_rate, "f"
            ),
            "extend_min_mean_uplift_r": format(
                self.extend_min_mean_uplift_r, "f"
            ),
            "extend_min_progress_fraction": format(
                self.extend_min_progress_fraction, "f"
            ),
            "defend_minimum_samples": self.defend_minimum_samples,
            "defend_minimum_positive_rate": format(
                self.defend_minimum_positive_rate, "f"
            ),
            "defend_min_mean_uplift_r": format(
                self.defend_min_mean_uplift_r, "f"
            ),
        }


POLICIES = tuple(
    SplitPolicy(
        extension_reference_fraction=extension,
        extend_minimum_samples=extend_samples,
        extend_minimum_positive_rate=Decimal("0.65"),
        extend_min_mean_uplift_r=extend_ev,
        extend_min_progress_fraction=progress,
        defend_minimum_samples=defend_samples,
        defend_minimum_positive_rate=Decimal("0.65"),
        defend_min_mean_uplift_r=defend_ev,
    )
    for extension in (Decimal("0.25"), Decimal("0.50"))
    for extend_samples in (8, 12)
    for extend_ev in (Decimal("0.10"), Decimal("0.25"))
    for progress in (Decimal("0.50"), Decimal("0.75"))
    for defend_samples in (4, 8)
    for defend_ev in (Decimal("0.10"), Decimal("0.25"))
)


def _simulate(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    memory: v2.JourneyMemory,
    policy: SplitPolicy,
) -> dict[str, object]:
    fill_index, _ = v2._fill_and_exit_indices(setup, day_bars, row)
    side = cast(object, setup).side.value
    sign = v1._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    original_target = cast(object, setup).target_price
    reference = cast(object, setup).source_setup.reference
    ref_width = reference.high - reference.low
    extension_target = (
        original_target
        + sign * ref_width * policy.extension_reference_fraction
    )
    current_stop = cast(object, setup).stop_price
    active_target = original_target
    be_armed = False
    extended = False
    extension_pending = False
    defend_pending = False
    extend_signals = 0
    defend_signals = 0
    situations: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if v1._local_minute(bar) >= v1.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = v1._bar_values(bar)

        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "exit_reason": "SPLIT_DEFEND_NEXT_OPEN",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if extension_pending:
            active_target = extension_target
            extended = True
            extension_pending = False

        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= active_target if side == "long" else low <= active_target
        if hit_stop and hit_target:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "SPLIT_STOP_FIRST",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "SPLIT_STOP",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "exit_reason": (
                    "SPLIT_EXTENDED_TARGET"
                    if extended
                    else "SPLIT_ORIGINAL_TARGET"
                ),
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situations.items())),
            }

        if not be_armed:
            touched_three_r = (
                high >= cast(object, setup).three_r_price
                if side == "long"
                else low <= cast(object, setup).three_r_price
            )
            if touched_three_r:
                be_armed = True
                current_stop = entry

        full, small, state = v2._state_signature(
            row=row,
            bars=list(day_bars),
            setup=setup,
            fill_index=fill_index,
            current_index=index,
        )
        mode = cast(str, state["mode"])
        situations[mode] = situations.get(mode, 0) + 1
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        defense = v2._query(
            memory,
            full,
            small,
            "DEFEND",
            policy.defend_minimum_samples,
        )
        extension = v2._query(
            memory,
            full,
            small,
            "EXTEND",
            policy.extend_minimum_samples,
        )

        defend_ok = False
        defend_ev = Decimal("-999")
        if defense is not None:
            defend_ev = v3._d(cast(object, defense["mean_uplift_r"]))
            defend_ok = (
                close_r <= 0
                and defend_ev >= policy.defend_min_mean_uplift_r
                and v3._d(defense["positive_rate"])
                >= policy.defend_minimum_positive_rate
            )

        extend_ok = False
        extend_ev = Decimal("-999")
        if extension is not None and not extended and not extension_pending:
            extend_ev = v3._d(cast(object, extension["mean_uplift_r"]))
            extend_ok = (
                progress >= policy.extend_min_progress_fraction
                and close_r > 0
                and extend_ev >= policy.extend_min_mean_uplift_r
                and v3._d(extension["positive_rate"])
                >= policy.extend_minimum_positive_rate
            )

        if defend_ok and (not extend_ok or defend_ev >= extend_ev):
            defend_pending = True
            defend_signals += 1
        elif extend_ok:
            extension_pending = True
            extend_signals += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v1._local_minute(bar) < v1.LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise ValueError("missing lifecycle close")
    close = v1._bar_values(eligible[-1])[3]
    return {
        "r_multiple": format(sign * (close - entry) / risk, "f"),
        "exit_reason": "SPLIT_LIFECYCLE",
        "extend_signals": extend_signals,
        "defend_signals": defend_signals,
        "situation_counts": dict(sorted(situations.items())),
    }


def _evaluate(
    *,
    decision_history: list[dict[str, object]],
    journey_memory_rows: list[dict[str, object]],
    rows: list[dict[str, object]],
    memory_paths: dict[str, tuple[object, tuple[object, ...]]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    policy: SplitPolicy,
    memory_cache: dict[str, v2.JourneyMemory],
) -> dict[str, object]:
    memories = {
        name: decision._memory(decision_history, fields)
        for name, fields in decision.VIEWS.items()
    }
    cache_key = format(policy.extension_reference_fraction, "f")
    if cache_key not in memory_cache:
        memory_cache[cache_key] = v2._build_memory(
            rows=journey_memory_rows,
            paths=memory_paths,
            extension_fraction=policy.extension_reference_fraction,
        )
    journey_memory = memory_cache[cache_key]

    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    kept_baseline: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    ext_n = def_n = 0
    ext_u = def_u = total_u = Decimal(0)
    situations: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = v3._d(row["net_r_after_friction"])
        baseline_values.append(baseline_r)
        pre = decision._decision(memories, row, v1.DECISION_POLICY)
        if pre["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
            continue

        signal = cast(str, row["signal_at"])
        setup, day_bars = evaluation_paths[signal]
        result = _simulate(
            row=row,
            setup=setup,
            day_bars=day_bars,
            memory=journey_memory,
            policy=policy,
        )
        shared_r = v3._d(result["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        kept_baseline.append(baseline_r)
        uplift = shared_r - baseline_r
        total_u += uplift
        if int(result["extend_signals"]) > 0:
            ext_n += 1
            ext_u += uplift
        if int(result["defend_signals"]) > 0:
            def_n += 1
            def_u += uplift
        for mode, count in cast(dict[str, int], result["situation_counts"]).items():
            situations[mode] = situations.get(mode, 0) + count

    baseline = v1._metrics_values(baseline_values)
    selected = v1._metrics_values(kept_baseline)
    shared = v1._metrics_values(shared_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(v3._d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(v3._d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((x for x in baseline_values if x > 0), Decimal(0))
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
        "selected_baseline_before_journey": selected,
        "shared_integrated": shared,
        "decision": {
            "input": len(rows),
            "kept": len(shared_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0" if base_losses == 0
                else format(Decimal(losses_avoided) / Decimal(base_losses), "f")
            ),
            "winner_count_retention": (
                "0" if base_wins == 0
                else format(
                    Decimal(base_wins - winners_sacrificed) / Decimal(base_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1" if gross_winner_r == 0
                else format((gross_winner_r - sacrificed_r) / gross_winner_r, "f")
            ),
            "density_retained": (
                "0" if not rows
                else format(Decimal(len(shared_values)) / Decimal(len(rows)), "f")
            ),
        },
        "journey": {
            "extension_signaled_trades": ext_n,
            "defense_signaled_trades": def_n,
            "extension_signaled_trade_uplift_r": format(ext_u, "f"),
            "defense_signaled_trade_uplift_r": format(def_u, "f"),
            "all_journey_uplift_r_vs_kept_baseline": format(total_u, "f"),
            "situation_counts": dict(sorted(situations.items())),
        },
        "memory": {
            "exact_state_count": len(journey_memory.exact),
            "reduced_state_count": len(journey_memory.reduced),
        },
    }


def run(
    *,
    r8_json: Path,
    r6_json: Path,
    r5_json: Path,
    daily_path: Path,
    r8_evidence: Path,
    r6_evidence: Path,
    r5_evidence: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = v3._decorate(v3._load_trades(r8_json), daily)
    r6 = v3._decorate(v3._load_trades(r6_json), daily)
    r5 = v3._decorate(v3._load_trades(r5_json), daily)
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("winner binding drift")

    p8 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r8_evidence))
    p6 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r6_evidence))
    p5 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r5_evidence))

    cache: dict[str, v2.JourneyMemory] = {}
    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, SplitPolicy] | None = None
    for policy in POLICIES:
        calibration = _evaluate(
            decision_history=r8,
            journey_memory_rows=r8,
            rows=r6,
            memory_paths=p8,
            evaluation_paths=p6,
            policy=policy,
            memory_cache=cache,
        )
        gates = v1._gates(calibration)
        score = v1._selection_score(calibration)
        frontier.append({
            "policy": policy.payload(),
            "calibration": calibration,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades":822,"losses":711,"wins":111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "frontier": frontier,
            "governance": {
                "split_extension_defense_heads": True,
                "historical_counterfactual_labels_only": True,
                "current_trade_future_used": False,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        decision_history=r8+r6,
        journey_memory_rows=r8+r6,
        rows=r5,
        memory_paths={**p8,**p6},
        evaluation_paths=p5,
        policy=frozen,
        memory_cache={},
    )
    gates=v1._gates(evaluation)
    passed=all(gates.values())
    return {
        "schema":SCHEMA,
        "identity":IDENTITY,
        "economic_status":"PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set":{"trades":822,"losses":711,"wins":111},
        "temporal_protocol":{
            "r8":"CLOSED_COUNTERFACTUAL_MEMORY",
            "r6":"SPLIT_HEADS_CALIBRATION_FREEZE",
            "r5":"NO_RETUNE_EVALUATION",
        },
        "frozen_policy":frozen.payload(),
        "evaluation":evaluation,
        "gates":gates,
        "passes_shared":passed,
        "frontier":frontier,
        "governance":{
            "split_extension_defense_heads":True,
            "historical_counterfactual_labels_only":True,
            "current_trade_future_used":False,
            "capital_risk_weighting_used":False,
            "r5_retuned":False,
            "live_authorized":False,
            "merge_authorized":False,
        },
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--r8-json",type=Path,required=True)
    parser.add_argument("--r6-json",type=Path,required=True)
    parser.add_argument("--r5-json",type=Path,required=True)
    parser.add_argument("--daily-path",type=Path,required=True)
    parser.add_argument("--r8-evidence",type=Path,required=True)
    parser.add_argument("--r6-evidence",type=Path,required=True)
    parser.add_argument("--r5-evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=run(
        r8_json=args.r8_json,r6_json=args.r6_json,r5_json=args.r5_json,
        daily_path=args.daily_path,r8_evidence=args.r8_evidence,
        r6_evidence=args.r6_evidence,r5_evidence=args.r5_evidence,
    )
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "economic_status":payload["economic_status"],
        "passes_shared":payload["passes_shared"],
        "frozen_policy":payload["frozen_policy"],
        "evaluation":payload["evaluation"],
        "gates":payload["gates"],
    },sort_keys=True))


if __name__=="__main__":
    main()
