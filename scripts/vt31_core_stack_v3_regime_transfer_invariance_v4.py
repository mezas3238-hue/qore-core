"""Shared Regime/Temporal Transfer Invariance V4.

Purpose
-------
The V3 split-head architecture passed all hard gates on R6 but failed R5.
The failure showed that pooled historical evidence was not temporally invariant.

V4 therefore forbids a current decision/action from being trusted merely
because it is profitable in a pooled memory. Evidence must agree across
separate historical era banks.

Calibration protocol:
- R8 is split chronologically into two independent history banks.
- A Decision Head is selected on R6 only if both R8 banks support the abstain.
- EXTEND and DEFEND use action-specific regime memories and require positive
  evidence in both R8 banks.
- After the policy is frozen, R5 is evaluated without retuning.
- For R5, R8 and R6 become separate historical banks. A relation that existed
  only in R6 cannot override contradictory R8 history, and vice versa.

Capital/risk weighting is forbidden. Current outcome/future path are forbidden.
Historical closed episodes and their counterfactual action labels are allowed.
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
import vt31_core_stack_v3_integrated_shared_intelligence_v1 as integrated
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as journey_v2
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.regime_transfer_invariance.v4"
IDENTITY = "VT31_NAS100_SHARED_REGIME_TRANSFER_INVARIANCE_V4"
FRICTION = Decimal("0.05")


DECISION_POLICIES = tuple(
    decision.Policy(
        maximum_analogs=maximum,
        minimum_similarity_bps=similarity,
        minimum_confidence_bps=confidence,
        abstain_ev_r=abstain_ev,
        required_negative_views=2,
        maximum_positive_views=0,
        winner_archetype_ev_floor=Decimal("0.30"),
        winner_archetype_payoff_floor=Decimal("2.5"),
        tail_mean_win_r_floor=Decimal("4.5"),
        tail_payoff_floor=Decimal("3"),
        tail_min_win_rate=Decimal("0.12"),
    )
    for maximum in (24, 32, 48)
    for similarity in (4500, 5500, 6500)
    for confidence in (2000, 3000)
    for abstain_ev in (Decimal("-0.10"), Decimal("-0.05"), Decimal("0"))
)


@dataclass(frozen=True, slots=True)
class JourneyInvariantPolicy:
    extension_reference_fraction: Decimal
    extend_minimum_samples_per_bank: int
    extend_minimum_positive_rate: Decimal
    extend_min_mean_uplift_r: Decimal
    extend_min_progress_fraction: Decimal
    defend_minimum_samples_per_bank: int
    defend_minimum_positive_rate: Decimal
    defend_min_mean_uplift_r: Decimal
    negative_bank_veto_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "extension_reference_fraction": format(
                self.extension_reference_fraction, "f"
            ),
            "extend_minimum_samples_per_bank": (
                self.extend_minimum_samples_per_bank
            ),
            "extend_minimum_positive_rate": format(
                self.extend_minimum_positive_rate, "f"
            ),
            "extend_min_mean_uplift_r": format(
                self.extend_min_mean_uplift_r, "f"
            ),
            "extend_min_progress_fraction": format(
                self.extend_min_progress_fraction, "f"
            ),
            "defend_minimum_samples_per_bank": (
                self.defend_minimum_samples_per_bank
            ),
            "defend_minimum_positive_rate": format(
                self.defend_minimum_positive_rate, "f"
            ),
            "defend_min_mean_uplift_r": format(
                self.defend_min_mean_uplift_r, "f"
            ),
            "negative_bank_veto_r": format(self.negative_bank_veto_r, "f"),
        }


JOURNEY_POLICIES = tuple(
    JourneyInvariantPolicy(
        extension_reference_fraction=extension,
        extend_minimum_samples_per_bank=extend_samples,
        extend_minimum_positive_rate=positive_rate,
        extend_min_mean_uplift_r=extend_ev,
        extend_min_progress_fraction=progress,
        defend_minimum_samples_per_bank=defend_samples,
        defend_minimum_positive_rate=positive_rate,
        defend_min_mean_uplift_r=defend_ev,
        negative_bank_veto_r=Decimal("-0.05"),
    )
    for extension in (Decimal("0.25"), Decimal("0.50"))
    for extend_samples in (3, 5)
    for defend_samples in (3, 5)
    for positive_rate in (Decimal("0.55"), Decimal("0.65"))
    for extend_ev in (Decimal("0.05"), Decimal("0.15"))
    for defend_ev in (Decimal("0.10"), Decimal("0.25"))
    for progress in (Decimal("0.50"), Decimal("0.75"))
)


@dataclass(slots=True)
class ActionBank:
    extend: dict[tuple[str, ...], journey_v2.ActionStats]
    defend: dict[tuple[str, ...], journey_v2.ActionStats]


def _history_banks(
    rows: list[dict[str, object]],
) -> list[list[dict[str, object]]]:
    """Build independent chronological eras without using current fold data."""
    by_partition: dict[str, list[dict[str, object]]] = {}
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        by_partition.setdefault(str(row["partition"]), []).append(row)

    if len(by_partition) >= 2:
        return [by_partition[key] for key in sorted(by_partition)]

    ordered = next(iter(by_partition.values()))
    midpoint = max(1, len(ordered) // 2)
    first = ordered[:midpoint]
    second = ordered[midpoint:]
    if not first or not second:
        raise ValueError("history cannot be split into independent era banks")
    return [first, second]


def _build_decision_memories(
    bank_rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        name: decision._memory(bank_rows, fields)
        for name, fields in decision.VIEWS.items()
    }


def _temporal_decision(
    *,
    bank_memories: list[dict[str, object]],
    row: dict[str, object],
    policy: decision.Policy,
) -> dict[str, object]:
    views = [
        decision._decision(cast(dict, memories), row, policy)
        for memories in bank_memories
    ]
    protected = any(
        str(item["action"]) == "PASS_WINNER_ARCHETYPE_PROTECTED"
        for item in views
    )
    abstain_views = [
        item for item in views
        if str(item["action"]) == "ABSTAIN_SHADOW"
    ]
    insufficient = [
        item for item in views
        if str(item["action"]) == "PASS_INSUFFICIENT"
    ]

    strong_single = False
    if len(abstain_views) == 1 and len(insufficient) == len(views) - 1:
        raw = abstain_views[0].get("ensemble_ev_r")
        strong_single = (
            raw is not None and v3._d(raw) <= Decimal("-0.20")
        )

    abstain = (
        not protected
        and (
            len(abstain_views) == len(views)
            or strong_single
        )
    )
    return {
        "action": "ABSTAIN_SHADOW" if abstain else "PASS",
        "protected_by_any_era": protected,
        "abstain_era_count": len(abstain_views),
        "insufficient_era_count": len(insufficient),
        "era_views": views,
    }


def _decision_metrics(
    *,
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: decision.Policy,
) -> dict[str, object]:
    banks = _history_banks(history)
    bank_memories = [_build_decision_memories(bank) for bank in banks]

    kept: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        view = _temporal_decision(
            bank_memories=bank_memories,
            row=row,
            policy=policy,
        )
        if view["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
        else:
            kept.append(row)

    baseline = integrated._metrics_values(
        [v3._d(row["net_r_after_friction"]) for row in rows]
    )
    selected = integrated._metrics_values(
        [v3._d(row["net_r_after_friction"]) for row in kept]
    )
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
        (
            v3._d(row["net_r_after_friction"])
            for row in rows
            if v3._d(row["net_r_after_friction"]) > 0
        ),
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
        "metrics": selected,
        "input": len(rows),
        "kept": len(kept),
        "abstained": len(abstained),
        "losses_avoided": losses_avoided,
        "winners_sacrificed": winners_sacrificed,
        "loss_rejection_recall": (
            "0"
            if base_losses == 0
            else format(
                Decimal(losses_avoided) / Decimal(base_losses), "f"
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
            else format(Decimal(len(kept)) / Decimal(len(rows)), "f")
        ),
        "kept_signal_ids": [
            cast(str, row["signal_at"])
            for row in kept
        ],
        "history_bank_sizes": [len(bank) for bank in banks],
    }


def _decision_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    metrics = cast(dict[str, object], result["metrics"])
    if baseline["profit_factor"] is None or metrics["profit_factor"] is None:
        return {
            "pf_plus_25pct": False,
            "dd_minus_30pct": False,
            "loss_recall_at_least_25pct": False,
            "winner_count_retention_at_least_80pct": False,
            "winner_r_retention_at_least_90pct": False,
            "density_at_least_55pct": False,
        }
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, metrics["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(metrics["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "loss_recall_at_least_25pct": (
            v3._d(result["loss_rejection_recall"]) >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            v3._d(result["winner_count_retention"]) >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            v3._d(result["winner_r_retention"]) >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            v3._d(result["density_retained"]) >= Decimal("0.55")
        ),
    }


def _decision_score(result: dict[str, object]) -> Decimal | None:
    gates = _decision_gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    metrics = cast(dict[str, object], result["metrics"])
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, metrics["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(metrics["max_drawdown_r"])
    return (
        (spf / bpf)
        * (bdd / max(sdd, Decimal("0.000001")))
        * v3._d(result["winner_r_retention"])
        * (Decimal(1) + v3._d(result["loss_rejection_recall"]))
    )


def _action_keys(
    *,
    row: dict[str, object],
    day_bars: tuple[object, ...],
    setup: object,
    fill_index: int,
    snapshot_index: int,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, object]]:
    full, _, state = journey_v2._state_signature(
        row=row,
        bars=list(day_bars),
        setup=setup,
        fill_index=fill_index,
        current_index=snapshot_index,
    )
    # V2 full layout:
    # side,family,mode,progress,close,efficiency,overlap,body,time,target,
    # peer_consensus,prior_regime
    mode = full[2]
    progress = full[3]
    close_bucket = full[4]
    efficiency = full[5]
    overlap = full[6]
    body = full[7]
    time_bucket = full[8]
    target_bucket = full[9]
    peer = full[10]
    prior_regime = full[11]
    prior_peer = str(
        row.get("prior_peer_direction_state", "unavailable")
    )
    extension_key = (
        mode,
        progress,
        efficiency,
        overlap,
        time_bucket,
        target_bucket,
        peer,
        prior_regime,
        prior_peer,
    )
    defense_key = (
        mode,
        close_bucket,
        efficiency,
        overlap,
        body,
        time_bucket,
        peer,
        prior_regime,
        prior_peer,
    )
    return extension_key, defense_key, state


def _add_action(
    mapping: dict[tuple[str, ...], journey_v2.ActionStats],
    key: tuple[str, ...],
    uplift: Decimal,
) -> None:
    stats = mapping.setdefault(key, journey_v2.ActionStats())
    stats.add(uplift)


def _build_action_bank(
    *,
    rows: list[dict[str, object]],
    paths: dict[str, tuple[object, tuple[object, ...]]],
    extension_fraction: Decimal,
) -> ActionBank:
    extend: dict[tuple[str, ...], journey_v2.ActionStats] = {}
    defend: dict[tuple[str, ...], journey_v2.ActionStats] = {}

    for row in rows:
        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, exit_index = journey_v2._fill_and_exit_indices(
            setup, day_bars, row
        )
        baseline_r = v3._d(row["net_r_after_friction"])

        for snapshot_index in range(fill_index + 1, exit_index):
            extend_key, defend_key, _ = _action_keys(
                row=row,
                day_bars=day_bars,
                setup=setup,
                fill_index=fill_index,
                snapshot_index=snapshot_index,
            )
            extension = journey_v2._extension_counterfactual(
                setup=setup,
                day_bars=day_bars,
                fill_index=fill_index,
                snapshot_index=snapshot_index,
                extension_fraction=extension_fraction,
            )
            if extension is not None:
                _add_action(
                    extend,
                    extend_key,
                    (extension - FRICTION) - baseline_r,
                )
            defense = journey_v2._defend_counterfactual(
                setup=setup,
                day_bars=day_bars,
                snapshot_index=snapshot_index,
            )
            if defense is not None:
                _add_action(
                    defend,
                    defend_key,
                    (defense - FRICTION) - baseline_r,
                )

    return ActionBank(extend=extend, defend=defend)


def _action_view(
    *,
    banks: list[ActionBank],
    key: tuple[str, ...],
    action: str,
    minimum_samples: int,
    minimum_positive_rate: Decimal,
    minimum_mean_uplift: Decimal,
    negative_bank_veto_r: Decimal,
) -> dict[str, object]:
    supported = 0
    vetoed = 0
    means: list[Decimal] = []
    views: list[dict[str, object]] = []

    for bank in banks:
        mapping = bank.extend if action == "EXTEND" else bank.defend
        stats = mapping.get(key)
        if stats is None or stats.count < minimum_samples:
            views.append({"status": "INSUFFICIENT", "count": 0 if stats is None else stats.count})
            continue

        mean = stats.total_uplift / Decimal(stats.count)
        positive_rate = Decimal(stats.positive) / Decimal(stats.count)
        status = "NEUTRAL"
        if (
            mean >= minimum_mean_uplift
            and positive_rate >= minimum_positive_rate
        ):
            supported += 1
            means.append(mean)
            status = "SUPPORT"
        elif mean <= negative_bank_veto_r:
            vetoed += 1
            status = "VETO"

        views.append(
            {
                "status": status,
                "count": stats.count,
                "mean_uplift_r": format(mean, "f"),
                "positive_rate": format(positive_rate, "f"),
            }
        )

    required_support = len(banks)
    trusted = supported == required_support and vetoed == 0
    mean_support = (
        None
        if not means
        else sum(means, Decimal(0)) / Decimal(len(means))
    )
    return {
        "trusted": trusted,
        "supported_banks": supported,
        "required_support_banks": required_support,
        "vetoed_banks": vetoed,
        "mean_supported_uplift_r": (
            None if mean_support is None else format(mean_support, "f")
        ),
        "bank_views": views,
    }


def _simulate_invariant_journey(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    banks: list[ActionBank],
    policy: JourneyInvariantPolicy,
) -> dict[str, object]:
    fill_index, _ = journey_v2._fill_and_exit_indices(setup, day_bars, row)
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
    extension_signals = 0
    defense_signals = 0
    situation_counts: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if integrated._local_minute(bar) >= integrated.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = integrated._bar_values(bar)

        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "exit_reason": "INVARIANT_DEFEND_NEXT_OPEN",
                "extend_signals": extension_signals,
                "defend_signals": defense_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if extension_pending:
            active_target = extension_target
            extended = True
            extension_pending = False

        hit_stop = (
            low <= current_stop if side == "long" else high >= current_stop
        )
        hit_target = (
            high >= active_target if side == "long" else low <= active_target
        )
        if hit_stop and hit_target:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "INVARIANT_STOP_FIRST",
                "extend_signals": extension_signals,
                "defend_signals": defense_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "INVARIANT_STOP",
                "extend_signals": extension_signals,
                "defend_signals": defense_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "exit_reason": (
                    "INVARIANT_EXTENDED_TARGET"
                    if extended
                    else "INVARIANT_ORIGINAL_TARGET"
                ),
                "extend_signals": extension_signals,
                "defend_signals": defense_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
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

        extension_key, defense_key, state = _action_keys(
            row=row,
            day_bars=day_bars,
            setup=setup,
            fill_index=fill_index,
            snapshot_index=index,
        )
        mode = str(state["mode"])
        situation_counts[mode] = situation_counts.get(mode, 0) + 1
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        defense = _action_view(
            banks=banks,
            key=defense_key,
            action="DEFEND",
            minimum_samples=policy.defend_minimum_samples_per_bank,
            minimum_positive_rate=policy.defend_minimum_positive_rate,
            minimum_mean_uplift=policy.defend_min_mean_uplift_r,
            negative_bank_veto_r=policy.negative_bank_veto_r,
        )
        extension = _action_view(
            banks=banks,
            key=extension_key,
            action="EXTEND",
            minimum_samples=policy.extend_minimum_samples_per_bank,
            minimum_positive_rate=policy.extend_minimum_positive_rate,
            minimum_mean_uplift=policy.extend_min_mean_uplift_r,
            negative_bank_veto_r=policy.negative_bank_veto_r,
        )

        defend_ok = close_r <= 0 and bool(defense["trusted"])
        extend_ok = (
            not extended
            and not extension_pending
            and progress >= policy.extend_min_progress_fraction
            and close_r > 0
            and bool(extension["trusted"])
        )

        defend_ev = (
            Decimal("-999")
            if defense["mean_supported_uplift_r"] is None
            else v3._d(defense["mean_supported_uplift_r"])
        )
        extend_ev = (
            Decimal("-999")
            if extension["mean_supported_uplift_r"] is None
            else v3._d(extension["mean_supported_uplift_r"])
        )

        if defend_ok and (not extend_ok or defend_ev >= extend_ev):
            defend_pending = True
            defense_signals += 1
        elif extend_ok:
            extension_pending = True
            extension_signals += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if integrated._local_minute(bar) < integrated.LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise ValueError("missing lifecycle close")
    close = integrated._bar_values(eligible[-1])[3]
    return {
        "r_multiple": format(sign * (close - entry) / risk, "f"),
        "exit_reason": "INVARIANT_LIFECYCLE",
        "extend_signals": extension_signals,
        "defend_signals": defense_signals,
        "situation_counts": dict(sorted(situation_counts.items())),
    }


def _evaluate_integrated(
    *,
    decision_history: list[dict[str, object]],
    journey_history: list[dict[str, object]],
    rows: list[dict[str, object]],
    history_paths: dict[str, tuple[object, tuple[object, ...]]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    decision_policy: decision.Policy,
    journey_policy: JourneyInvariantPolicy,
    action_bank_cache: dict[str, list[ActionBank]],
) -> dict[str, object]:
    decision_banks = _history_banks(decision_history)
    bank_memories = [
        _build_decision_memories(bank) for bank in decision_banks
    ]

    journey_banks_rows = _history_banks(journey_history)
    cache_key = (
        f"{journey_policy.extension_reference_fraction}:"
        + "|".join(
            f"{bank[0]['partition']}:{len(bank)}"
            for bank in journey_banks_rows
        )
    )
    if cache_key not in action_bank_cache:
        action_bank_cache[cache_key] = [
            _build_action_bank(
                rows=bank,
                paths=history_paths,
                extension_fraction=journey_policy.extension_reference_fraction,
            )
            for bank in journey_banks_rows
        ]
    action_banks = action_bank_cache[cache_key]

    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    selected_baseline_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    extension_trades = 0
    defense_trades = 0
    extension_uplift = Decimal(0)
    defense_uplift = Decimal(0)
    total_journey_uplift = Decimal(0)
    situations: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = v3._d(row["net_r_after_friction"])
        baseline_values.append(baseline_r)
        pre = _temporal_decision(
            bank_memories=bank_memories,
            row=row,
            policy=decision_policy,
        )
        if pre["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
            continue

        signal = cast(str, row["signal_at"])
        setup, day_bars = evaluation_paths[signal]
        result = _simulate_invariant_journey(
            row=row,
            setup=setup,
            day_bars=day_bars,
            banks=action_banks,
            policy=journey_policy,
        )
        shared_r = v3._d(result["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        selected_baseline_values.append(baseline_r)
        uplift = shared_r - baseline_r
        total_journey_uplift += uplift

        if int(result["extend_signals"]) > 0:
            extension_trades += 1
            extension_uplift += uplift
        if int(result["defend_signals"]) > 0:
            defense_trades += 1
            defense_uplift += uplift
        for mode, count in cast(
            dict[str, int], result["situation_counts"]
        ).items():
            situations[mode] = situations.get(mode, 0) + count

    baseline = integrated._metrics_values(baseline_values)
    selected = integrated._metrics_values(selected_baseline_values)
    shared = integrated._metrics_values(shared_values)

    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0 for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0), Decimal(0)
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
        "selected_baseline_before_journey": selected,
        "shared_integrated": shared,
        "decision": {
            "input": len(rows),
            "kept": len(shared_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if base_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(base_losses), "f"
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
                    Decimal(len(shared_values)) / Decimal(len(rows)), "f"
                )
            ),
            "history_bank_sizes": [len(bank) for bank in decision_banks],
        },
        "journey": {
            "extension_signaled_trades": extension_trades,
            "defense_signaled_trades": defense_trades,
            "extension_signaled_trade_uplift_r": format(
                extension_uplift, "f"
            ),
            "defense_signaled_trade_uplift_r": format(defense_uplift, "f"),
            "all_journey_uplift_r_vs_kept_baseline": format(
                total_journey_uplift, "f"
            ),
            "situation_counts": dict(sorted(situations.items())),
            "history_bank_sizes": [
                len(bank) for bank in journey_banks_rows
            ],
        },
    }


def _integrated_gates(result: dict[str, object]) -> dict[str, bool]:
    return integrated._gates(result)


def _integrated_score(result: dict[str, object]) -> Decimal | None:
    return integrated._selection_score(result)


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

    p8 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        integrated._reconstruct_partition(r8_evidence),
    )
    p6 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        integrated._reconstruct_partition(r6_evidence),
    )
    p5 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        integrated._reconstruct_partition(r5_evidence),
    )

    decision_frontier: list[dict[str, object]] = []
    best_decision: tuple[Decimal, decision.Policy] | None = None
    for policy in DECISION_POLICIES:
        result = _decision_metrics(
            history=r8,
            rows=r6,
            policy=policy,
        )
        gates = _decision_gates(result)
        score = _decision_score(result)
        decision_frontier.append(
            {
                "policy": policy.payload(),
                "calibration": result,
                "gates": gates,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (
            best_decision is None or score > best_decision[0]
        ):
            best_decision = (score, policy)

    if best_decision is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_DECISION_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_decision_policy": None,
            "frozen_journey_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "decision_frontier": decision_frontier,
            "journey_frontier": [],
            "governance": {
                "temporal_era_consensus_required": True,
                "action_regime_keys_required": True,
                "historical_counterfactual_labels_only": True,
                "current_trade_future_used": False,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen_decision = best_decision[1]
    action_bank_cache: dict[str, list[ActionBank]] = {}
    journey_frontier: list[dict[str, object]] = []
    best_journey: tuple[Decimal, JourneyInvariantPolicy] | None = None

    for policy in JOURNEY_POLICIES:
        result = _evaluate_integrated(
            decision_history=r8,
            journey_history=r8,
            rows=r6,
            history_paths=p8,
            evaluation_paths=p6,
            decision_policy=frozen_decision,
            journey_policy=policy,
            action_bank_cache=action_bank_cache,
        )
        gates = _integrated_gates(result)
        score = _integrated_score(result)
        journey_frontier.append(
            {
                "policy": policy.payload(),
                "calibration": result,
                "gates": gates,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (
            best_journey is None or score > best_journey[0]
        ):
            best_journey = (score, policy)

    if best_journey is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_JOURNEY_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_decision_policy": frozen_decision.payload(),
            "frozen_journey_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "decision_frontier": decision_frontier,
            "journey_frontier": journey_frontier,
            "governance": {
                "temporal_era_consensus_required": True,
                "action_regime_keys_required": True,
                "historical_counterfactual_labels_only": True,
                "current_trade_future_used": False,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen_journey = best_journey[1]
    evaluation = _evaluate_integrated(
        decision_history=r8 + r6,
        journey_history=r8 + r6,
        rows=r5,
        history_paths={**p8, **p6},
        evaluation_paths=p5,
        decision_policy=frozen_decision,
        journey_policy=frozen_journey,
        action_bank_cache={},
    )
    gates = _integrated_gates(evaluation)
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
            "r8": "TWO_INDEPENDENT_ERA_BANKS",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "R8_AND_R6_INDEPENDENT_BANKS_NO_RETUNE",
        },
        "frozen_decision_policy": frozen_decision.payload(),
        "frozen_journey_policy": frozen_journey.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared": passed,
        "decision_frontier": decision_frontier,
        "journey_frontier": journey_frontier,
        "governance": {
            "temporal_era_consensus_required": True,
            "action_regime_keys_required": True,
            "historical_counterfactual_labels_only": True,
            "current_trade_future_used": False,
            "capital_risk_weighting_used": False,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "stop_widening_allowed": False,
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared": payload["passes_shared"],
                "frozen_decision_policy": payload[
                    "frozen_decision_policy"
                ],
                "frozen_journey_policy": payload[
                    "frozen_journey_policy"
                ],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
