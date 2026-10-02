"""Shared Regime-Transfer Stability V5.

V4 falsified complete era unanimity: it preserved winners but destroyed loss
coverage. V5 keeps the global Shared gates unchanged while correcting two
architectural errors:

1. Decision Head is selected for its own job (loss discrimination, winner
   preservation, density, and no PF/DD degradation). The +25% PF / -30% DD
   gates remain GLOBAL gates for integrated Shared, where Journey Intelligence
   is allowed to contribute.
2. Historical eras are used as VETOES against unstable pooled evidence rather
   than requiring unanimous positive votes. Pooled evidence may act only when
   no sufficiently supported era contradicts it.

R8 -> discovery/history and era banks.
R6 -> calibration/freeze.
R5 -> no-retune temporal evaluation.
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
import vt31_core_stack_v3_regime_transfer_invariance_v4 as v4
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.regime_transfer_stability.v5"
IDENTITY = "VT31_NAS100_SHARED_REGIME_TRANSFER_STABILITY_V5"
FRICTION = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class StableDecisionPolicy:
    base: decision.Policy
    positive_era_veto_ev_r: Decimal
    minimum_negative_era_support: int

    def payload(self) -> dict[str, object]:
        return {
            **self.base.payload(),
            "positive_era_veto_ev_r": format(
                self.positive_era_veto_ev_r, "f"
            ),
            "minimum_negative_era_support": self.minimum_negative_era_support,
        }


DECISION_POLICIES = tuple(
    StableDecisionPolicy(
        base=decision.Policy(
            maximum_analogs=maximum,
            minimum_similarity_bps=similarity,
            minimum_confidence_bps=confidence,
            abstain_ev_r=abstain_ev,
            required_negative_views=negative_views,
            maximum_positive_views=0,
            winner_archetype_ev_floor=Decimal("0.30"),
            winner_archetype_payoff_floor=Decimal("2.5"),
            tail_mean_win_r_floor=Decimal("4.5"),
            tail_payoff_floor=Decimal("3"),
            tail_min_win_rate=Decimal("0.12"),
        ),
        positive_era_veto_ev_r=veto_ev,
        minimum_negative_era_support=1,
    )
    for maximum in (24, 32)
    for similarity in (4500, 5500, 6500)
    for confidence in (2000, 3000)
    for abstain_ev in (Decimal("-0.05"), Decimal("0"))
    for negative_views in (1, 2)
    for veto_ev in (Decimal("0.15"), Decimal("0.30"))
)


@dataclass(frozen=True, slots=True)
class StableJourneyPolicy:
    extension_reference_fraction: Decimal
    extend_pooled_min_samples: int
    extend_era_min_samples: int
    extend_min_positive_rate: Decimal
    extend_min_mean_uplift_r: Decimal
    extend_min_progress_fraction: Decimal
    extend_required_era_support: int
    defend_pooled_min_samples: int
    defend_era_min_samples: int
    defend_min_positive_rate: Decimal
    defend_min_mean_uplift_r: Decimal
    defend_required_era_support: int
    negative_era_veto_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "extension_reference_fraction": format(
                self.extension_reference_fraction, "f"
            ),
            "extend_pooled_min_samples": self.extend_pooled_min_samples,
            "extend_era_min_samples": self.extend_era_min_samples,
            "extend_min_positive_rate": format(
                self.extend_min_positive_rate, "f"
            ),
            "extend_min_mean_uplift_r": format(
                self.extend_min_mean_uplift_r, "f"
            ),
            "extend_min_progress_fraction": format(
                self.extend_min_progress_fraction, "f"
            ),
            "extend_required_era_support": self.extend_required_era_support,
            "defend_pooled_min_samples": self.defend_pooled_min_samples,
            "defend_era_min_samples": self.defend_era_min_samples,
            "defend_min_positive_rate": format(
                self.defend_min_positive_rate, "f"
            ),
            "defend_min_mean_uplift_r": format(
                self.defend_min_mean_uplift_r, "f"
            ),
            "defend_required_era_support": self.defend_required_era_support,
            "negative_era_veto_r": format(
                self.negative_era_veto_r, "f"
            ),
        }


JOURNEY_POLICIES = tuple(
    StableJourneyPolicy(
        extension_reference_fraction=extension,
        extend_pooled_min_samples=extend_pool,
        extend_era_min_samples=3,
        extend_min_positive_rate=Decimal("0.60"),
        extend_min_mean_uplift_r=extend_ev,
        extend_min_progress_fraction=progress,
        extend_required_era_support=1,
        defend_pooled_min_samples=defend_pool,
        defend_era_min_samples=3,
        defend_min_positive_rate=Decimal("0.65"),
        defend_min_mean_uplift_r=defend_ev,
        defend_required_era_support=defend_support,
        negative_era_veto_r=Decimal("-0.05"),
    )
    for extension in (Decimal("0.25"), Decimal("0.50"))
    for extend_pool in (8, 12)
    for extend_ev in (Decimal("0.05"), Decimal("0.15"))
    for progress in (Decimal("0.50"), Decimal("0.75"))
    for defend_pool in (4, 8)
    for defend_ev in (Decimal("0.10"), Decimal("0.25"))
    for defend_support in (1, 2)
)


@dataclass(slots=True)
class ActionMemorySet:
    pooled: v4.ActionBank
    eras: list[v4.ActionBank]


def _decision_context(
    history: list[dict[str, object]],
) -> tuple[dict[str, object], list[dict[str, object]], list[int]]:
    pooled = v4._build_decision_memories(history)
    era_rows = v4._history_banks(history)
    eras = [v4._build_decision_memories(bank) for bank in era_rows]
    return pooled, eras, [len(bank) for bank in era_rows]


def _stable_decision(
    *,
    pooled_memories: dict[str, object],
    era_memories: list[dict[str, object]],
    row: dict[str, object],
    policy: StableDecisionPolicy,
) -> dict[str, object]:
    pooled = decision._decision(
        cast(dict, pooled_memories),
        row,
        policy.base,
    )
    if str(pooled["action"]) != "ABSTAIN_SHADOW":
        return {
            "action": "PASS",
            "reason": "POOLED_NOT_ABSTAIN",
            "pooled": pooled,
            "era_views": [],
        }

    era_views = [
        decision._decision(cast(dict, item), row, policy.base)
        for item in era_memories
    ]

    if any(
        str(item["action"]) == "PASS_WINNER_ARCHETYPE_PROTECTED"
        for item in era_views
    ):
        return {
            "action": "PASS",
            "reason": "ERA_WINNER_ARCHETYPE_VETO",
            "pooled": pooled,
            "era_views": era_views,
        }

    positive_veto = False
    negative_support = 0
    for item in era_views:
        raw = item.get("ensemble_ev_r")
        if raw is not None:
            ev = v3._d(raw)
            if ev >= policy.positive_era_veto_ev_r:
                positive_veto = True
        if str(item["action"]) == "ABSTAIN_SHADOW":
            negative_support += 1

    if positive_veto:
        return {
            "action": "PASS",
            "reason": "POSITIVE_ERA_EV_VETO",
            "pooled": pooled,
            "era_views": era_views,
        }

    if negative_support < policy.minimum_negative_era_support:
        return {
            "action": "PASS",
            "reason": "NO_TEMPORAL_NEGATIVE_SUPPORT",
            "pooled": pooled,
            "era_views": era_views,
        }

    return {
        "action": "ABSTAIN_SHADOW",
        "reason": "POOLED_NEGATIVE_WITHOUT_ERA_VETO",
        "pooled": pooled,
        "era_views": era_views,
    }


def _decision_metrics_from_context(
    *,
    pooled_memories: dict[str, object],
    era_memories: list[dict[str, object]],
    bank_sizes: list[int],
    rows: list[dict[str, object]],
    policy: StableDecisionPolicy,
) -> dict[str, object]:
    kept: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        view = _stable_decision(
            pooled_memories=pooled_memories,
            era_memories=era_memories,
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
    metrics = integrated._metrics_values(
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
        "metrics": metrics,
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
            cast(str, row["signal_at"]) for row in kept
        ],
        "history_bank_sizes": bank_sizes,
    }


def _decision_head_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    metrics = cast(dict[str, object], result["metrics"])
    if baseline["profit_factor"] is None or metrics["profit_factor"] is None:
        return {
            "pf_not_lower": False,
            "dd_not_worse": False,
            "loss_recall_at_least_25pct": False,
            "winner_count_retention_at_least_80pct": False,
            "winner_r_retention_at_least_90pct": False,
            "density_at_least_55pct": False,
        }
    return {
        "pf_not_lower": (
            v3._d(cast(object, metrics["profit_factor"]))
            >= v3._d(cast(object, baseline["profit_factor"]))
        ),
        "dd_not_worse": (
            v3._d(metrics["max_drawdown_r"])
            <= v3._d(baseline["max_drawdown_r"])
        ),
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


def _decision_head_score(result: dict[str, object]) -> Decimal | None:
    gates = _decision_head_gates(result)
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


def _stats(
    mapping: dict[tuple[str, ...], journey_v2.ActionStats],
    key: tuple[str, ...],
) -> journey_v2.ActionStats | None:
    return mapping.get(key)


def _stable_action_view(
    *,
    memory: ActionMemorySet,
    key: tuple[str, ...],
    action: str,
    pooled_min_samples: int,
    era_min_samples: int,
    minimum_positive_rate: Decimal,
    minimum_mean_uplift: Decimal,
    required_era_support: int,
    negative_era_veto_r: Decimal,
) -> dict[str, object]:
    pooled_map = (
        memory.pooled.extend if action == "EXTEND"
        else memory.pooled.defend
    )
    pooled = _stats(pooled_map, key)
    if pooled is None or pooled.count < pooled_min_samples:
        return {
            "trusted": False,
            "reason": "POOLED_INSUFFICIENT",
            "mean_uplift_r": None,
        }

    pooled_mean = pooled.total_uplift / Decimal(pooled.count)
    pooled_positive = Decimal(pooled.positive) / Decimal(pooled.count)
    if (
        pooled_mean < minimum_mean_uplift
        or pooled_positive < minimum_positive_rate
    ):
        return {
            "trusted": False,
            "reason": "POOLED_NOT_POSITIVE",
            "mean_uplift_r": format(pooled_mean, "f"),
        }

    support = 0
    veto = 0
    era_views: list[dict[str, object]] = []
    for bank in memory.eras:
        mapping = bank.extend if action == "EXTEND" else bank.defend
        item = _stats(mapping, key)
        if item is None or item.count < era_min_samples:
            era_views.append({
                "status": "INSUFFICIENT",
                "count": 0 if item is None else item.count,
            })
            continue
        mean = item.total_uplift / Decimal(item.count)
        positive = Decimal(item.positive) / Decimal(item.count)
        status = "NEUTRAL"
        if (
            mean >= minimum_mean_uplift
            and positive >= minimum_positive_rate
        ):
            support += 1
            status = "SUPPORT"
        elif mean <= negative_era_veto_r:
            veto += 1
            status = "VETO"
        era_views.append({
            "status": status,
            "count": item.count,
            "mean_uplift_r": format(mean, "f"),
            "positive_rate": format(positive, "f"),
        })

    trusted = veto == 0 and support >= required_era_support
    return {
        "trusted": trusted,
        "reason": (
            "POOLED_POSITIVE_STABLE"
            if trusted
            else "ERA_STABILITY_NOT_MET"
        ),
        "mean_uplift_r": format(pooled_mean, "f"),
        "positive_rate": format(pooled_positive, "f"),
        "era_support": support,
        "era_veto": veto,
        "era_views": era_views,
    }


def _build_action_memory_set(
    *,
    history: list[dict[str, object]],
    paths: dict[str, tuple[object, tuple[object, ...]]],
    extension_fraction: Decimal,
) -> ActionMemorySet:
    pooled = v4._build_action_bank(
        rows=history,
        paths=paths,
        extension_fraction=extension_fraction,
    )
    eras = [
        v4._build_action_bank(
            rows=bank,
            paths=paths,
            extension_fraction=extension_fraction,
        )
        for bank in v4._history_banks(history)
    ]
    return ActionMemorySet(pooled=pooled, eras=eras)


def _simulate_journey(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    memory: ActionMemorySet,
    policy: StableJourneyPolicy,
) -> dict[str, object]:
    fill_index, _ = journey_v2._fill_and_exit_indices(
        setup, day_bars, row
    )
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
    ext_signals = 0
    def_signals = 0
    situations: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if integrated._local_minute(bar) >= integrated.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = integrated._bar_values(bar)

        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "exit_reason": "STABLE_DEFEND_NEXT_OPEN",
                "extend_signals": ext_signals,
                "defend_signals": def_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if extension_pending:
            active_target = extension_target
            extended = True
            extension_pending = False

        hit_stop = (
            low <= current_stop if side == "long"
            else high >= current_stop
        )
        hit_target = (
            high >= active_target if side == "long"
            else low <= active_target
        )
        if hit_stop and hit_target:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "STABLE_STOP_FIRST",
                "extend_signals": ext_signals,
                "defend_signals": def_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "STABLE_STOP",
                "extend_signals": ext_signals,
                "defend_signals": def_signals,
                "situation_counts": dict(sorted(situations.items())),
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "exit_reason": (
                    "STABLE_EXTENDED_TARGET"
                    if extended else "STABLE_ORIGINAL_TARGET"
                ),
                "extend_signals": ext_signals,
                "defend_signals": def_signals,
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

        extend_key, defend_key, state = v4._action_keys(
            row=row,
            day_bars=day_bars,
            setup=setup,
            fill_index=fill_index,
            snapshot_index=index,
        )
        mode = str(state["mode"])
        situations[mode] = situations.get(mode, 0) + 1
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        extension = _stable_action_view(
            memory=memory,
            key=extend_key,
            action="EXTEND",
            pooled_min_samples=policy.extend_pooled_min_samples,
            era_min_samples=policy.extend_era_min_samples,
            minimum_positive_rate=policy.extend_min_positive_rate,
            minimum_mean_uplift=policy.extend_min_mean_uplift_r,
            required_era_support=policy.extend_required_era_support,
            negative_era_veto_r=policy.negative_era_veto_r,
        )
        defense = _stable_action_view(
            memory=memory,
            key=defend_key,
            action="DEFEND",
            pooled_min_samples=policy.defend_pooled_min_samples,
            era_min_samples=policy.defend_era_min_samples,
            minimum_positive_rate=policy.defend_min_positive_rate,
            minimum_mean_uplift=policy.defend_min_mean_uplift_r,
            required_era_support=policy.defend_required_era_support,
            negative_era_veto_r=policy.negative_era_veto_r,
        )

        extend_ok = (
            not extended
            and not extension_pending
            and progress >= policy.extend_min_progress_fraction
            and close_r > 0
            and bool(extension["trusted"])
        )
        defend_ok = close_r <= 0 and bool(defense["trusted"])

        extend_ev = (
            Decimal("-999")
            if extension["mean_uplift_r"] is None
            else v3._d(extension["mean_uplift_r"])
        )
        defend_ev = (
            Decimal("-999")
            if defense["mean_uplift_r"] is None
            else v3._d(defense["mean_uplift_r"])
        )

        if defend_ok and (not extend_ok or defend_ev >= extend_ev):
            defend_pending = True
            def_signals += 1
        elif extend_ok:
            extension_pending = True
            ext_signals += 1

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
        "exit_reason": "STABLE_LIFECYCLE",
        "extend_signals": ext_signals,
        "defend_signals": def_signals,
        "situation_counts": dict(sorted(situations.items())),
    }


def _evaluate_integrated(
    *,
    decision_result: dict[str, object],
    rows: list[dict[str, object]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    action_memory: ActionMemorySet,
    journey_policy: StableJourneyPolicy,
) -> dict[str, object]:
    kept_ids = set(cast(list[str], decision_result["kept_signal_ids"]))
    baseline_values: list[Decimal] = []
    selected_baseline: list[Decimal] = []
    shared_values: list[Decimal] = []
    ext_n = def_n = 0
    ext_u = def_u = total_u = Decimal(0)
    situations: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = v3._d(row["net_r_after_friction"])
        baseline_values.append(baseline_r)
        signal = cast(str, row["signal_at"])
        if signal not in kept_ids:
            continue

        selected_baseline.append(baseline_r)
        setup, day_bars = evaluation_paths[signal]
        result = _simulate_journey(
            row=row,
            setup=setup,
            day_bars=day_bars,
            memory=action_memory,
            policy=journey_policy,
        )
        shared_r = v3._d(result["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        uplift = shared_r - baseline_r
        total_u += uplift
        if int(result["extend_signals"]) > 0:
            ext_n += 1
            ext_u += uplift
        if int(result["defend_signals"]) > 0:
            def_n += 1
            def_u += uplift
        for mode, count in cast(
            dict[str, int], result["situation_counts"]
        ).items():
            situations[mode] = situations.get(mode, 0) + count

    baseline = integrated._metrics_values(baseline_values)
    selected = integrated._metrics_values(selected_baseline)
    shared = integrated._metrics_values(shared_values)
    decision_public = {
        key: value
        for key, value in decision_result.items()
        if key not in {"baseline", "metrics", "kept_signal_ids"}
    }
    return {
        "baseline": baseline,
        "selected_baseline_before_journey": selected,
        "shared_integrated": shared,
        "decision": decision_public,
        "journey": {
            "extension_signaled_trades": ext_n,
            "defense_signaled_trades": def_n,
            "extension_signaled_trade_uplift_r": format(ext_u, "f"),
            "defense_signaled_trade_uplift_r": format(def_u, "f"),
            "all_journey_uplift_r_vs_kept_baseline": format(total_u, "f"),
            "situation_counts": dict(sorted(situations.items())),
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

    pooled_r8, eras_r8, sizes_r8 = _decision_context(r8)
    decision_frontier: list[dict[str, object]] = []
    best_decision: tuple[Decimal, StableDecisionPolicy, dict[str, object]] | None = None
    for policy in DECISION_POLICIES:
        result = _decision_metrics_from_context(
            pooled_memories=pooled_r8,
            era_memories=eras_r8,
            bank_sizes=sizes_r8,
            rows=r6,
            policy=policy,
        )
        gates = _decision_head_gates(result)
        score = _decision_head_score(result)
        decision_frontier.append({
            "policy": policy.payload(),
            "calibration": result,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (
            best_decision is None or score > best_decision[0]
        ):
            best_decision = (score, policy, result)

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
            "governance": _governance(),
        }

    _, frozen_decision, decision_calibration = best_decision

    action_cache: dict[str, ActionMemorySet] = {}
    journey_frontier: list[dict[str, object]] = []
    best_journey: tuple[Decimal, StableJourneyPolicy] | None = None

    for policy in JOURNEY_POLICIES:
        cache_key = format(policy.extension_reference_fraction, "f")
        if cache_key not in action_cache:
            action_cache[cache_key] = _build_action_memory_set(
                history=r8,
                paths=p8,
                extension_fraction=policy.extension_reference_fraction,
            )
        result = _evaluate_integrated(
            decision_result=decision_calibration,
            rows=r6,
            evaluation_paths=p6,
            action_memory=action_cache[cache_key],
            journey_policy=policy,
        )
        gates = integrated._gates(result)
        score = integrated._selection_score(result)
        journey_frontier.append({
            "policy": policy.payload(),
            "calibration": result,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
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
            "governance": _governance(),
        }

    _, frozen_journey = best_journey

    pooled_eval, eras_eval, sizes_eval = _decision_context(r8 + r6)
    decision_evaluation = _decision_metrics_from_context(
        pooled_memories=pooled_eval,
        era_memories=eras_eval,
        bank_sizes=sizes_eval,
        rows=r5,
        policy=frozen_decision,
    )
    eval_memory = _build_action_memory_set(
        history=r8 + r6,
        paths={**p8, **p6},
        extension_fraction=frozen_journey.extension_reference_fraction,
    )
    evaluation = _evaluate_integrated(
        decision_result=decision_evaluation,
        rows=r5,
        evaluation_paths=p5,
        action_memory=eval_memory,
        journey_policy=frozen_journey,
    )
    gates = integrated._gates(evaluation)
    passed = all(gates.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "POOLED_MEMORY_PLUS_TWO_ERA_VETO_BANKS",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "POOLED_R8_R6_PLUS_INDEPENDENT_ERA_VETO_NO_RETUNE",
        },
        "frozen_decision_policy": frozen_decision.payload(),
        "frozen_journey_policy": frozen_journey.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared": passed,
        "decision_frontier": decision_frontier,
        "journey_frontier": journey_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "global_shared_gates_unchanged": True,
        "decision_head_uses_role_specific_gates": True,
        "pooled_evidence_requires_era_veto_check": True,
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
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_shared": payload["passes_shared"],
        "frozen_decision_policy": payload["frozen_decision_policy"],
        "frozen_journey_policy": payload["frozen_journey_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
