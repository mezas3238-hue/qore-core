"""Shared V4: regime-transfer intelligence with adaptive trust.

V3 proved EXTEND transfers to R5, while Decision/DEFEND drift across temporal
regimes. V4 adds a causal regime-transfer layer. It does not retune on R5.

The layer estimates, from CLOSED historical episodes only, whether each
specialist head is trustworthy in the current regime context. R6 calibrates the
minimum transfer reliability; the frozen threshold is then evaluated on R5.

No capital weighting. No current/future outcome as a decision feature.
"""
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
import vt31_core_stack_v3_journey_split_heads_v3 as v3heads
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.regime_transfer_intelligence.v4"
IDENTITY = "VT31_NAS100_SHARED_REGIME_TRANSFER_INTELLIGENCE_V4"
FRICTION = Decimal("0.05")

TRANSFER_FIELDS = (
    "side",
    "prior_nas100_regime",
    "prior_nas100_first_breach",
    "prior_nas100_objective_hit",
    "prior3_reversal_rate",
    "prior3_objective_rate",
    "prior3_same_breach_rate",
    "prior_peer_direction_state",
    "prior_sp500_regime",
    "prior_us30_regime",
    "sp500_breach_asof",
    "us30_breach_asof",
    "peer_consensus",
)


@dataclass(frozen=True, slots=True)
class TransferPolicy:
    minimum_regime_samples: int
    minimum_decision_precision: Decimal
    minimum_defense_positive_rate: Decimal
    minimum_extension_positive_rate: Decimal
    maximum_decision_winner_cost_r: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "minimum_regime_samples": self.minimum_regime_samples,
            "minimum_decision_precision": format(
                self.minimum_decision_precision, "f"
            ),
            "minimum_defense_positive_rate": format(
                self.minimum_defense_positive_rate, "f"
            ),
            "minimum_extension_positive_rate": format(
                self.minimum_extension_positive_rate, "f"
            ),
            "maximum_decision_winner_cost_r": format(
                self.maximum_decision_winner_cost_r, "f"
            ),
        }


POLICIES = tuple(
    TransferPolicy(samples, precision, defense_rate, extension_rate, winner_cost)
    for samples in (3, 5, 8)
    for precision in (Decimal("0.75"), Decimal("0.80"), Decimal("0.85"))
    for defense_rate in (Decimal("0.55"), Decimal("0.60"), Decimal("0.65"))
    for extension_rate in (Decimal("0.55"), Decimal("0.60"))
    for winner_cost in (Decimal("0.50"), Decimal("1.00"), Decimal("2.00"))
)


@dataclass(slots=True)
class TransferStats:
    count: int = 0
    positive: int = 0
    total_uplift: Decimal = Decimal(0)
    winner_cost_r: Decimal = Decimal(0)

    def add(
        self,
        *,
        uplift: Decimal,
        positive: bool,
        winner_cost_r: Decimal = Decimal(0),
    ) -> None:
        self.count += 1
        self.total_uplift += uplift
        self.winner_cost_r += winner_cost_r
        if positive:
            self.positive += 1

    @property
    def positive_rate(self) -> Decimal:
        return (
            Decimal(0)
            if self.count == 0
            else Decimal(self.positive) / Decimal(self.count)
        )

    @property
    def mean_uplift(self) -> Decimal:
        return (
            Decimal(0)
            if self.count == 0
            else self.total_uplift / Decimal(self.count)
        )

    @property
    def mean_winner_cost(self) -> Decimal:
        return (
            Decimal(0)
            if self.count == 0
            else self.winner_cost_r / Decimal(self.count)
        )


@dataclass(slots=True)
class TransferMemory:
    exact: dict[tuple[str, ...], dict[str, TransferStats]]
    reduced: dict[tuple[str, ...], dict[str, TransferStats]]


def _signature(row: dict[str, object]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    full = tuple(str(row.get(field, "unavailable")) for field in TRANSFER_FIELDS)
    reduced = (
        str(row.get("side", "unavailable")),
        str(row.get("prior_nas100_regime", "unavailable")),
        str(row.get("prior_peer_direction_state", "unavailable")),
        str(row.get("peer_consensus", "unavailable")),
        str(row.get("prior3_reversal_rate", "unavailable")),
        str(row.get("prior3_objective_rate", "unavailable")),
    )
    return full, reduced


def _stats(
    memory: TransferMemory,
    row: dict[str, object],
    head: str,
    minimum_samples: int,
) -> TransferStats | None:
    full, reduced = _signature(row)
    exact = memory.exact.get(full, {}).get(head)
    if exact is not None and exact.count >= minimum_samples:
        return exact
    small = memory.reduced.get(reduced, {}).get(head)
    if small is not None and small.count >= minimum_samples:
        return small
    return None


def _add(
    mapping: dict[tuple[str, ...], dict[str, TransferStats]],
    key: tuple[str, ...],
    head: str,
    *,
    uplift: Decimal,
    positive: bool,
    winner_cost_r: Decimal = Decimal(0),
) -> None:
    heads = mapping.setdefault(key, {})
    stats = heads.setdefault(head, TransferStats())
    stats.add(
        uplift=uplift,
        positive=positive,
        winner_cost_r=winner_cost_r,
    )


def _decision_outcome(
    *,
    row: dict[str, object],
    memories: dict[str, object],
) -> tuple[bool, Decimal, Decimal]:
    result = decision._decision(
        cast(dict[str, object], memories),
        row,
        v1.DECISION_POLICY,
    )
    if result["action"] != "ABSTAIN_SHADOW":
        return False, Decimal(0), Decimal(0)
    r = v3._d(row["net_r_after_friction"])
    if r < 0:
        return True, -r, Decimal(0)
    if r > 0:
        return True, -r, r
    return True, Decimal(0), Decimal(0)


def _journey_actions(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    memory: v2.JourneyMemory,
    policy: v3heads.SplitPolicy,
) -> list[tuple[str, Decimal]]:
    fill_index, exit_index = v2._fill_and_exit_indices(setup, day_bars, row)
    baseline_r = v3._d(row["net_r_after_friction"])
    actions: list[tuple[str, Decimal]] = []
    for index in range(fill_index + 1, exit_index):
        full, small, state = v2._state_signature(
            row=row,
            bars=list(day_bars),
            setup=setup,
            fill_index=fill_index,
            current_index=index,
        )
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        defense = v2._query(
            memory,
            full,
            small,
            "DEFEND",
            policy.defend_minimum_samples,
        )
        if defense is not None:
            ev = v3._d(cast(object, defense["mean_uplift_r"]))
            rate = v3._d(defense["positive_rate"])
            if (
                close_r <= 0
                and ev >= policy.defend_min_mean_uplift_r
                and rate >= policy.defend_minimum_positive_rate
            ):
                cf = v2._defend_counterfactual(
                    setup=setup,
                    day_bars=day_bars,
                    snapshot_index=index,
                )
                if cf is not None:
                    actions.append(("DEFEND", (cf - FRICTION) - baseline_r))
                break

        extension = v2._query(
            memory,
            full,
            small,
            "EXTEND",
            policy.extend_minimum_samples,
        )
        if extension is not None:
            ev = v3._d(cast(object, extension["mean_uplift_r"]))
            rate = v3._d(extension["positive_rate"])
            if (
                progress >= policy.extend_min_progress_fraction
                and close_r > 0
                and ev >= policy.extend_min_mean_uplift_r
                and rate >= policy.extend_minimum_positive_rate
            ):
                cf = v2._extension_counterfactual(
                    setup=setup,
                    day_bars=day_bars,
                    fill_index=fill_index,
                    snapshot_index=index,
                    extension_fraction=policy.extension_reference_fraction,
                )
                if cf is not None:
                    actions.append(("EXTEND", (cf - FRICTION) - baseline_r))
                break
    return actions


def _build_transfer_memory(
    *,
    history: list[dict[str, object]],
    paths: dict[str, tuple[object, tuple[object, ...]]],
    journey_memory: v2.JourneyMemory,
    journey_policy: v3heads.SplitPolicy,
) -> TransferMemory:
    exact: dict[tuple[str, ...], dict[str, TransferStats]] = {}
    reduced: dict[tuple[str, ...], dict[str, TransferStats]] = {}
    memories = {
        name: decision._memory(history, fields)
        for name, fields in decision.VIEWS.items()
    }

    for row in history:
        full, small = _signature(row)
        fired, uplift, winner_cost = _decision_outcome(
            row=row,
            memories=cast(dict[str, object], memories),
        )
        if fired:
            for mapping, key in ((exact, full), (reduced, small)):
                _add(
                    mapping,
                    key,
                    "DECISION",
                    uplift=uplift,
                    positive=uplift > 0,
                    winner_cost_r=winner_cost,
                )

        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        for head, action_uplift in _journey_actions(
            row=row,
            setup=setup,
            day_bars=day_bars,
            memory=journey_memory,
            policy=journey_policy,
        ):
            for mapping, key in ((exact, full), (reduced, small)):
                _add(
                    mapping,
                    key,
                    head,
                    uplift=action_uplift,
                    positive=action_uplift > 0,
                )

    return TransferMemory(exact=exact, reduced=reduced)


def _head_trusted(
    *,
    transfer: TransferMemory,
    row: dict[str, object],
    head: str,
    policy: TransferPolicy,
) -> bool:
    stats = _stats(
        transfer,
        row,
        head,
        policy.minimum_regime_samples,
    )
    if stats is None:
        return False
    if head == "DECISION":
        return (
            stats.positive_rate >= policy.minimum_decision_precision
            and stats.mean_uplift > 0
            and stats.mean_winner_cost
            <= policy.maximum_decision_winner_cost_r
        )
    if head == "DEFEND":
        return (
            stats.positive_rate >= policy.minimum_defense_positive_rate
            and stats.mean_uplift > 0
        )
    if head == "EXTEND":
        return (
            stats.positive_rate >= policy.minimum_extension_positive_rate
            and stats.mean_uplift > 0
        )
    raise ValueError(head)


def _simulate_regime_journey(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    journey_memory: v2.JourneyMemory,
    journey_policy: v3heads.SplitPolicy,
    transfer: TransferMemory,
    transfer_policy: TransferPolicy,
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
        + sign
        * ref_width
        * journey_policy.extension_reference_fraction
    )
    current_stop = cast(object, setup).stop_price
    active_target = original_target
    be_armed = False
    extended = False
    extension_pending = False
    defend_pending = False
    extend_signals = 0
    defend_signals = 0

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if v1._local_minute(bar) >= v1.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = v1._bar_values(bar)

        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
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
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
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
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        if _head_trusted(
            transfer=transfer,
            row=row,
            head="DEFEND",
            policy=transfer_policy,
        ):
            defense = v2._query(
                journey_memory,
                full,
                small,
                "DEFEND",
                journey_policy.defend_minimum_samples,
            )
            if defense is not None:
                if (
                    close_r <= 0
                    and v3._d(cast(object, defense["mean_uplift_r"]))
                    >= journey_policy.defend_min_mean_uplift_r
                    and v3._d(defense["positive_rate"])
                    >= journey_policy.defend_minimum_positive_rate
                ):
                    defend_pending = True
                    defend_signals += 1
                    continue

        if (
            not extended
            and not extension_pending
            and _head_trusted(
                transfer=transfer,
                row=row,
                head="EXTEND",
                policy=transfer_policy,
            )
        ):
            extension = v2._query(
                journey_memory,
                full,
                small,
                "EXTEND",
                journey_policy.extend_minimum_samples,
            )
            if extension is not None:
                if (
                    progress >= journey_policy.extend_min_progress_fraction
                    and close_r > 0
                    and v3._d(cast(object, extension["mean_uplift_r"]))
                    >= journey_policy.extend_min_mean_uplift_r
                    and v3._d(extension["positive_rate"])
                    >= journey_policy.extend_minimum_positive_rate
                ):
                    extension_pending = True
                    extend_signals += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v1._local_minute(bar) < v1.LIFECYCLE_MINUTE
    ]
    close = v1._bar_values(eligible[-1])[3]
    return {
        "r_multiple": format(sign * (close - entry) / risk, "f"),
        "extend_signals": extend_signals,
        "defend_signals": defend_signals,
    }


def _evaluate(
    *,
    history: list[dict[str, object]],
    memory_paths: dict[str, tuple[object, tuple[object, ...]]],
    rows: list[dict[str, object]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    journey_policy: v3heads.SplitPolicy,
    transfer_policy: TransferPolicy,
) -> dict[str, object]:
    decision_memories = {
        name: decision._memory(history, fields)
        for name, fields in decision.VIEWS.items()
    }
    journey_memory = v2._build_memory(
        rows=history,
        paths=memory_paths,
        extension_fraction=journey_policy.extension_reference_fraction,
    )
    transfer = _build_transfer_memory(
        history=history,
        paths=memory_paths,
        journey_memory=journey_memory,
        journey_policy=journey_policy,
    )

    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    kept_baseline: list[Decimal] = []
    ext_n = def_n = 0
    ext_u = def_u = Decimal(0)

    for row in rows:
        baseline_r = v3._d(row["net_r_after_friction"])
        baseline_values.append(baseline_r)
        pre = decision._decision(
            decision_memories,
            row,
            v1.DECISION_POLICY,
        )
        if (
            pre["action"] == "ABSTAIN_SHADOW"
            and _head_trusted(
                transfer=transfer,
                row=row,
                head="DECISION",
                policy=transfer_policy,
            )
        ):
            abstained.append(row)
            continue

        signal = cast(str, row["signal_at"])
        setup, day_bars = evaluation_paths[signal]
        journey = _simulate_regime_journey(
            row=row,
            setup=setup,
            day_bars=day_bars,
            journey_memory=journey_memory,
            journey_policy=journey_policy,
            transfer=transfer,
            transfer_policy=transfer_policy,
        )
        shared_r = v3._d(journey["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        kept_baseline.append(baseline_r)
        uplift = shared_r - baseline_r
        if int(journey["extend_signals"]) > 0:
            ext_n += 1
            ext_u += uplift
        if int(journey["defend_signals"]) > 0:
            def_n += 1
            def_u += uplift

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
        },
        "transfer_memory": {
            "exact_regimes": len(transfer.exact),
            "reduced_regimes": len(transfer.reduced),
        },
    }


def _calibration_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_integrated"])
    dec = cast(dict[str, object], result["decision"])
    journey = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid_metrics": False}
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, shared["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(shared["max_drawdown_r"])
    return {
        "pf_plus_20pct": spf >= bpf * Decimal("1.20"),
        "dd_minus_25pct": sdd <= bdd * Decimal("0.75"),
        "total_r_not_lower": v3._d(shared["total_r"]) >= v3._d(baseline["total_r"]),
        "loss_recall_at_least_15pct": v3._d(dec["loss_rejection_recall"]) >= Decimal("0.15"),
        "winner_count_retention_at_least_85pct": v3._d(dec["winner_count_retention"]) >= Decimal("0.85"),
        "winner_r_retention_at_least_90pct": v3._d(dec["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_70pct": v3._d(dec["density_retained"]) >= Decimal("0.70"),
        "extension_positive": int(journey["extension_signaled_trades"]) > 0 and v3._d(journey["extension_signaled_trade_uplift_r"]) > 0,
        "defense_nonnegative": v3._d(journey["defense_signaled_trade_uplift_r"]) >= 0,
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _calibration_gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_integrated"])
    return (
        v3._d(cast(object, shared["profit_factor"]))
        / v3._d(cast(object, baseline["profit_factor"]))
        * v3._d(baseline["max_drawdown_r"])
        / max(v3._d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * v3._d(shared["total_r"])
        / max(v3._d(baseline["total_r"]), Decimal("0.000001"))
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

    p8 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r8_evidence))
    p6 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r6_evidence))
    p5 = cast(dict[str, tuple[object, tuple[object, ...]]], v1._reconstruct_partition(r5_evidence))

    # Frozen journey architecture from V3 R6. V4 changes trust transfer only.
    journey_policy = v3heads.SplitPolicy(
        extension_reference_fraction=Decimal("0.25"),
        extend_minimum_samples=12,
        extend_minimum_positive_rate=Decimal("0.65"),
        extend_min_mean_uplift_r=Decimal("0.10"),
        extend_min_progress_fraction=Decimal("0.50"),
        defend_minimum_samples=4,
        defend_minimum_positive_rate=Decimal("0.65"),
        defend_min_mean_uplift_r=Decimal("0.25"),
    )

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, TransferPolicy] | None = None
    for policy in POLICIES:
        calibration = _evaluate(
            history=r8,
            memory_paths=p8,
            rows=r6,
            evaluation_paths=p6,
            journey_policy=journey_policy,
            transfer_policy=policy,
        )
        gates = _calibration_gates(calibration)
        score = _score(calibration)
        frontier.append({
            "policy": policy.payload(),
            "calibration": calibration,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades":822,"losses":711,"wins":111},
            "frozen_transfer_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "frontier": frontier,
            "governance": {
                "regime_transfer_layer": True,
                "r5_retuned": False,
                "capital_risk_weighting_used": False,
                "current_future_outcome_used": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        history=r8+r6,
        memory_paths={**p8,**p6},
        rows=r5,
        evaluation_paths=p5,
        journey_policy=journey_policy,
        transfer_policy=frozen,
    )
    gates = _calibration_gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set": {"trades":822,"losses":711,"wins":111},
        "frozen_journey_policy": journey_policy.payload(),
        "frozen_transfer_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared": passed,
        "frontier": frontier,
        "governance": {
            "regime_transfer_layer": True,
            "r5_retuned": False,
            "capital_risk_weighting_used": False,
            "current_future_outcome_used": False,
            "live_authorized": False,
            "merge_authorized": False,
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
        "frozen_transfer_policy":payload["frozen_transfer_policy"],
        "evaluation":payload["evaluation"],
        "gates":payload["gates"],
    },sort_keys=True))


if __name__=="__main__":
    main()
