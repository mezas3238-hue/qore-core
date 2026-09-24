"""Shared temporal-invariance laboratory for VT31 NAS100.

Goal: fix the R6->R5 regime-transfer failure without retuning R5.

Shared now estimates whether historical knowledge is transferable to the
current opportunity. A decision/action is allowed only when multiple historical
eras agree on its sign. Recent closed history may veto stale evidence.

Protocol:
- R8 is split chronologically into OLD and RECENT closed memory.
- R6 calibrates and freezes the transfer policy.
- R5 is evaluation only; its outcomes never tune the policy.
- For R5, RECENT memory becomes the fully closed R6 partition.

No capital/risk weighting. No Shared execution authority.
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
import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_core_stack_v3_integrated_shared_intelligence_v1 as integrated
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as journey
import vt31_core_stack_v3_journey_split_heads_v3 as split
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.temporal_invariance.v4"
IDENTITY = "VT31_NAS100_SHARED_TEMPORAL_INVARIANCE_V4"
FRICTION = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class TransferPolicy:
    decision_policy: decision.Policy
    recent_minimum_analogs: int
    recent_minimum_confidence_bps: int
    recent_abstain_ev_r: Decimal
    required_recent_negative_views: int
    maximum_recent_positive_views: int
    extension_reference_fraction: Decimal
    extend_minimum_samples: int
    extend_minimum_positive_rate: Decimal
    extend_min_mean_uplift_r: Decimal
    extend_min_progress_fraction: Decimal
    defend_minimum_samples: int
    defend_minimum_positive_rate: Decimal
    defend_min_mean_uplift_r: Decimal
    require_recent_action_agreement: bool

    def payload(self) -> dict[str, object]:
        return {
            "decision_policy": self.decision_policy.payload(),
            "recent_minimum_analogs": self.recent_minimum_analogs,
            "recent_minimum_confidence_bps": self.recent_minimum_confidence_bps,
            "recent_abstain_ev_r": format(self.recent_abstain_ev_r, "f"),
            "required_recent_negative_views": self.required_recent_negative_views,
            "maximum_recent_positive_views": self.maximum_recent_positive_views,
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
            "require_recent_action_agreement": self.require_recent_action_agreement,
        }


DECISION_POLICIES = (
    decision.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        abstain_ev_r=Decimal("-0.10"),
        required_negative_views=2,
        maximum_positive_views=0,
        winner_archetype_ev_floor=Decimal("0.30"),
        winner_archetype_payoff_floor=Decimal("2.5"),
        tail_mean_win_r_floor=Decimal("4.5"),
        tail_payoff_floor=Decimal("3"),
        tail_min_win_rate=Decimal("0.12"),
    ),
    decision.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        abstain_ev_r=Decimal("-0.05"),
        required_negative_views=2,
        maximum_positive_views=0,
        winner_archetype_ev_floor=Decimal("0.30"),
        winner_archetype_payoff_floor=Decimal("2.5"),
        tail_mean_win_r_floor=Decimal("4.5"),
        tail_payoff_floor=Decimal("3"),
        tail_min_win_rate=Decimal("0.12"),
    ),
)

POLICIES = tuple(
    TransferPolicy(
        decision_policy=dp,
        recent_minimum_analogs=recent_n,
        recent_minimum_confidence_bps=recent_conf,
        recent_abstain_ev_r=recent_ev,
        required_recent_negative_views=recent_neg,
        maximum_recent_positive_views=0,
        extension_reference_fraction=Decimal("0.25"),
        extend_minimum_samples=12,
        extend_minimum_positive_rate=Decimal("0.65"),
        extend_min_mean_uplift_r=Decimal("0.10"),
        extend_min_progress_fraction=Decimal("0.50"),
        defend_minimum_samples=def_n,
        defend_minimum_positive_rate=Decimal("0.65"),
        defend_min_mean_uplift_r=def_ev,
        require_recent_action_agreement=True,
    )
    for dp in DECISION_POLICIES
    for recent_n in (4, 6)
    for recent_conf in (1500, 2500)
    for recent_ev in (Decimal("-0.10"), Decimal("-0.05"))
    for recent_neg in (2, 3)
    for def_n in (4, 6)
    for def_ev in (Decimal("0.10"), Decimal("0.25"))
)


def _chronological_split(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = max(1, len(ordered) // 2)
    return ordered[:cut], ordered[cut:]


def _view_stats(
    memories: dict[str, object],
    row: dict[str, object],
    policy: TransferPolicy,
) -> dict[str, object]:
    negative = positive = confident = 0
    weighted_ev = Decimal(0)
    weight_sum = Decimal(0)
    views: dict[str, object] = {}
    for name, fields in decision.VIEWS.items():
        item = decision._view(
            cast(object, memories[name]),
            row,
            fields,
            policy.decision_policy,
        )
        views[name] = item
        ev_raw = item["ev_r"]
        confidence = int(item["confidence_bps"])
        effective_n = Decimal(str(item["effective_n"]))
        analog_count = int(item.get("analog_count", 0) or 0)
        if analog_count == 0:
            analog_count = int(effective_n)
        if (
            ev_raw is None
            or confidence < policy.recent_minimum_confidence_bps
            or effective_n < Decimal(policy.recent_minimum_analogs)
            or analog_count < policy.recent_minimum_analogs
        ):
            continue
        confident += 1
        value = Decimal(str(ev_raw))
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += value * weight
        weight_sum += weight
        if value < policy.recent_abstain_ev_r:
            negative += 1
        if value >= policy.decision_policy.winner_archetype_ev_floor:
            positive += 1
    ensemble = None if weight_sum == 0 else weighted_ev / weight_sum
    return {
        "confident_views": confident,
        "negative_views": negative,
        "positive_views": positive,
        "ensemble_ev_r": None if ensemble is None else format(ensemble, "f"),
        "views": views,
    }


def _transfer_decision(
    *,
    long_memories: dict[str, object],
    recent_memories: dict[str, object],
    row: dict[str, object],
    policy: TransferPolicy,
) -> dict[str, object]:
    long_view = decision._decision(
        cast(dict, long_memories),
        row,
        policy.decision_policy,
    )
    recent = _view_stats(recent_memories, row, policy)
    recent_ev = recent["ensemble_ev_r"]
    recent_negative = (
        recent_ev is not None
        and int(recent["confident_views"]) >= 2
        and int(recent["negative_views"]) >= policy.required_recent_negative_views
        and int(recent["positive_views"]) <= policy.maximum_recent_positive_views
        and Decimal(str(recent_ev)) < policy.recent_abstain_ev_r
    )
    long_negative = str(long_view["action"]) == "ABSTAIN_SHADOW"
    abstain = long_negative and recent_negative
    return {
        "action": "ABSTAIN_SHADOW" if abstain else "PASS",
        "long_term": long_view,
        "recent": recent,
        "temporal_agreement": abstain,
    }


def _action_view(
    *,
    long_memory: journey.JourneyMemory,
    recent_memory: journey.JourneyMemory,
    full: tuple[str, ...],
    reduced: tuple[str, ...],
    action: str,
    minimum_samples: int,
    minimum_positive_rate: Decimal,
    minimum_mean_uplift_r: Decimal,
    require_recent: bool,
) -> tuple[bool, Decimal, dict[str, object]]:
    long = journey._query(
        long_memory,
        full,
        reduced,
        action,
        minimum_samples,
    )
    recent = journey._query(
        recent_memory,
        full,
        reduced,
        action,
        max(3, minimum_samples // 2),
    )
    if long is None:
        return False, Decimal("-999"), {"long": None, "recent": recent}
    long_ev = v3._d(cast(object, long["mean_uplift_r"]))
    long_ok = (
        long_ev >= minimum_mean_uplift_r
        and v3._d(long["positive_rate"]) >= minimum_positive_rate
    )
    if not long_ok:
        return False, long_ev, {"long": long, "recent": recent}
    if not require_recent:
        return True, long_ev, {"long": long, "recent": recent}
    if recent is None:
        return False, long_ev, {"long": long, "recent": None}
    recent_ev = v3._d(cast(object, recent["mean_uplift_r"]))
    recent_ok = (
        recent_ev >= Decimal(0)
        and v3._d(recent["positive_rate"]) >= Decimal("0.50")
    )
    return (
        recent_ok,
        min(long_ev, recent_ev),
        {"long": long, "recent": recent},
    )


def _simulate(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    long_memory: journey.JourneyMemory,
    recent_memory: journey.JourneyMemory,
    policy: TransferPolicy,
) -> dict[str, object]:
    fill_index, _ = journey._fill_and_exit_indices(setup, day_bars, row)
    side = cast(object, setup).side.value
    sign = integrated._side_sign(side)
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
    ext_n = def_n = 0
    situations: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if integrated._local_minute(bar) >= integrated.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = integrated._bar_values(bar)
        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "extend_signals": ext_n,
                "defend_signals": def_n,
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
                "extend_signals": ext_n,
                "defend_signals": def_n,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "extend_signals": ext_n,
                "defend_signals": def_n,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "extend_signals": ext_n,
                "defend_signals": def_n,
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

        full, reduced, state = journey._state_signature(
            row=row,
            bars=list(day_bars),
            setup=setup,
            fill_index=fill_index,
            current_index=index,
        )
        mode = cast(str, state["mode"])
        situations[mode] = situations.get(mode, 0) + 1
        close_r = v3._d(state["close_r"])
        progress = v3._d(state["progress_fraction"])

        defend_ok, defend_ev, _ = _action_view(
            long_memory=long_memory,
            recent_memory=recent_memory,
            full=full,
            reduced=reduced,
            action="DEFEND",
            minimum_samples=policy.defend_minimum_samples,
            minimum_positive_rate=policy.defend_minimum_positive_rate,
            minimum_mean_uplift_r=policy.defend_min_mean_uplift_r,
            require_recent=policy.require_recent_action_agreement,
        )
        extend_ok, extend_ev, _ = _action_view(
            long_memory=long_memory,
            recent_memory=recent_memory,
            full=full,
            reduced=reduced,
            action="EXTEND",
            minimum_samples=policy.extend_minimum_samples,
            minimum_positive_rate=policy.extend_minimum_positive_rate,
            minimum_mean_uplift_r=policy.extend_min_mean_uplift_r,
            require_recent=policy.require_recent_action_agreement,
        )
        defend_ok = defend_ok and close_r <= 0
        extend_ok = (
            extend_ok
            and not extended
            and not extension_pending
            and close_r > 0
            and progress >= policy.extend_min_progress_fraction
        )
        if defend_ok and (not extend_ok or defend_ev >= extend_ev):
            defend_pending = True
            def_n += 1
        elif extend_ok:
            extension_pending = True
            ext_n += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if integrated._local_minute(bar) < integrated.LIFECYCLE_MINUTE
    ]
    close = integrated._bar_values(eligible[-1])[3]
    return {
        "r_multiple": format(sign * (close - entry) / risk, "f"),
        "extend_signals": ext_n,
        "defend_signals": def_n,
        "situation_counts": dict(sorted(situations.items())),
    }


def _evaluate(
    *,
    long_history: list[dict[str, object]],
    recent_history: list[dict[str, object]],
    rows: list[dict[str, object]],
    long_paths: dict[str, tuple[object, tuple[object, ...]]],
    recent_paths: dict[str, tuple[object, tuple[object, ...]]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    policy: TransferPolicy,
    memory_cache: dict[str, object],
) -> dict[str, object]:
    long_memories = {
        name: decision._memory(long_history, fields)
        for name, fields in decision.VIEWS.items()
    }
    recent_memories = {
        name: decision._memory(recent_history, fields)
        for name, fields in decision.VIEWS.items()
    }
    key_long = "L:" + format(policy.extension_reference_fraction, "f")
    key_recent = "R:" + format(policy.extension_reference_fraction, "f")
    if key_long not in memory_cache:
        memory_cache[key_long] = journey._build_memory(
            rows=long_history,
            paths=long_paths,
            extension_fraction=policy.extension_reference_fraction,
        )
    if key_recent not in memory_cache:
        memory_cache[key_recent] = journey._build_memory(
            rows=recent_history,
            paths=recent_paths,
            extension_fraction=policy.extension_reference_fraction,
        )
    long_journey = cast(journey.JourneyMemory, memory_cache[key_long])
    recent_journey = cast(journey.JourneyMemory, memory_cache[key_recent])

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
        pre = _transfer_decision(
            long_memories=long_memories,
            recent_memories=recent_memories,
            row=row,
            policy=policy,
        )
        if pre["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
            continue
        signal = cast(str, row["signal_at"])
        setup, day_bars = evaluation_paths[signal]
        result = _simulate(
            row=row,
            setup=setup,
            day_bars=day_bars,
            long_memory=long_journey,
            recent_memory=recent_journey,
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

    baseline = integrated._metrics_values(baseline_values)
    selected = integrated._metrics_values(kept_baseline)
    shared = integrated._metrics_values(shared_values)
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
    }


def _calibration_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_integrated"])
    dec = cast(dict[str, object], result["decision"])
    j = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, shared["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(shared["max_drawdown_r"])
    return {
        "pf_plus_20pct": spf >= bpf * Decimal("1.20"),
        "dd_minus_25pct": sdd <= bdd * Decimal("0.75"),
        "total_r_not_lower": v3._d(shared["total_r"]) >= v3._d(baseline["total_r"]),
        "loss_recall_at_least_20pct": v3._d(dec["loss_rejection_recall"]) >= Decimal("0.20"),
        "winner_count_retention_at_least_80pct": v3._d(dec["winner_count_retention"]) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": v3._d(dec["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_55pct": v3._d(dec["density_retained"]) >= Decimal("0.55"),
        "extension_positive": int(j["extension_signaled_trades"]) > 0 and v3._d(j["extension_signaled_trade_uplift_r"]) > 0,
        "defense_positive": int(j["defense_signaled_trades"]) > 0 and v3._d(j["defense_signaled_trade_uplift_r"]) > 0,
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _calibration_gates(result)
    if not gates or not all(gates.values()):
        return None
    b = cast(dict[str, object], result["baseline"])
    s = cast(dict[str, object], result["shared_integrated"])
    return (
        v3._d(cast(object, s["profit_factor"]))
        / v3._d(cast(object, b["profit_factor"]))
        * v3._d(b["max_drawdown_r"])
        / max(v3._d(s["max_drawdown_r"]), Decimal("0.000001"))
        * v3._d(s["total_r"])
        / max(v3._d(b["total_r"]), Decimal("0.000001"))
    )


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

    p8 = cast(dict[str, tuple[object, tuple[object, ...]]], integrated._reconstruct_partition(r8_evidence))
    p6 = cast(dict[str, tuple[object, tuple[object, ...]]], integrated._reconstruct_partition(r6_evidence))
    p5 = cast(dict[str, tuple[object, tuple[object, ...]]], integrated._reconstruct_partition(r5_evidence))
    r8_old, r8_recent = _chronological_split(r8)
    p8_old = {cast(str, row["signal_at"]): p8[cast(str, row["signal_at"])] for row in r8_old}
    p8_recent = {cast(str, row["signal_at"]): p8[cast(str, row["signal_at"])] for row in r8_recent}

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, TransferPolicy] | None = None
    cache: dict[str, object] = {}
    for policy in POLICIES:
        calibration = _evaluate(
            long_history=r8,
            recent_history=r8_recent,
            rows=r6,
            long_paths=p8,
            recent_paths=p8_recent,
            evaluation_paths=p6,
            policy=policy,
            memory_cache=cache,
        )
        gates = _calibration_gates(calibration)
        score = _score(calibration)
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
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "frontier": frontier,
            "governance": {
                "temporal_invariance_required": True,
                "current_outcome_used": False,
                "r5_retuned": False,
                "capital_risk_weighting_used": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        long_history=r8 + r6,
        recent_history=r6,
        rows=r5,
        long_paths={**p8, **p6},
        recent_paths=p6,
        evaluation_paths=p5,
        policy=frozen,
        memory_cache={},
    )
    gates = _calibration_gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "LONG_MEMORY_PLUS_RECENT_R8_HALF",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "LONG_MEMORY_R8_R6_PLUS_RECENT_R6_NO_RETUNE",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared": passed,
        "frontier": frontier,
        "governance": {
            "temporal_invariance_required": True,
            "current_outcome_used": False,
            "r5_retuned": False,
            "capital_risk_weighting_used": False,
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
    parser.add_argument("--r8-evidence", type=Path, required=True)
    parser.add_argument("--r6-evidence", type=Path, required=True)
    parser.add_argument("--r5-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
        r8_evidence=args.r8_evidence,
        r6_evidence=args.r6_evidence,
        r5_evidence=args.r5_evidence,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_shared": payload["passes_shared"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
