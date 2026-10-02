"""VT31 Shared Perception Sequence Topology V8.

Targeted repair of the V6/V7 R6 near-miss.

The negative present-state model is frozen from the V6 near-miss. V8 adds a
high-precision tail-winner rescue head using causal PRE-ENTRY event topology:
- last local sweep/reclaim direction and freshness;
- last displacement direction and freshness;
- last FVG direction and freshness;
- sweep -> displacement ordering and latency;
- event alignment with the VT31 side;
- compact sequence archetype.

All topology features are observable no later than signal_at. Historical R8
outcomes are used only offline to learn state semantics. Runtime uses exact
present-state lookup. R6 calibrates/finalizes. R5 is untouched unless every R6
hard gate passes.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import cibo_atlas_vt31_complete_behavior_explainer as complete
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_state_model_v5 as v5

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.core_stack_v4.vt31.perception_sequence_topology.v8"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_SEQUENCE_TOPOLOGY_V8"

NEGATIVE_VIEWS = v5.STATE_VIEWS

TOPOLOGY_VIEWS = {
    "CHAIN_REGIME_PEER": (
        "sequence_chain",
        "perception_regime",
        "peer_consensus",
    ),
    "CHAIN_STRUCTURE_PEER": (
        "sequence_chain",
        "structure_state",
        "peer_consensus",
    ),
    "CHAIN_ALIGNMENT_REGIME": (
        "sequence_chain",
        "alignment5",
        "perception_regime",
    ),
    "SWEEP_DISP_FRESHNESS": (
        "sweep_alignment",
        "displacement_alignment",
        "sweep_freshness",
        "displacement_freshness",
    ),
    "SWEEP_DISP_ORDER_PEER": (
        "sweep_displacement_order",
        "sweep_alignment",
        "displacement_alignment",
        "peer_consensus",
    ),
    "FVG_DISP_ORDER_REGIME": (
        "fvg_displacement_order",
        "fvg_alignment",
        "displacement_alignment",
        "perception_regime",
    ),
    "CHAIN_VOLATILITY_STRUCTURE": (
        "sequence_chain",
        "volatility_state",
        "structure_state",
    ),
    "CHAIN_BEHAVIOR_PEER": (
        "sequence_chain",
        "pre_behavior_proxy",
        "peer_consensus",
    ),
    "CHAIN_ALIGN20_PEER": (
        "sequence_chain",
        "alignment20",
        "peer_consensus",
    ),
}


@dataclass(frozen=True, slots=True)
class Policy:
    minimum_half_sample: int
    tail_mean_winner_r_floor: Decimal
    tail_pf_floor: Decimal
    required_topology_views: int
    allow_single_view_when_unique_chain: bool

    def payload(self) -> dict[str, object]:
        return {
            "negative_minimum_half_sample": 3,
            "negative_pf_ceiling": "0.80",
            "required_negative_views": 1,
            "minimum_half_sample": self.minimum_half_sample,
            "tail_mean_winner_r_floor": format(
                self.tail_mean_winner_r_floor, "f"
            ),
            "tail_pf_floor": format(self.tail_pf_floor, "f"),
            "required_topology_views": self.required_topology_views,
            "allow_single_view_when_unique_chain": (
                self.allow_single_view_when_unique_chain
            ),
        }


POLICIES = tuple(
    Policy(
        minimum_half_sample=min_sample,
        tail_mean_winner_r_floor=winner_r,
        tail_pf_floor=tail_pf,
        required_topology_views=views,
        allow_single_view_when_unique_chain=allow_single,
    )
    for min_sample in (2, 3, 4)
    for winner_r in (Decimal("4"), Decimal("6"), Decimal("8"))
    for tail_pf in (
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("2.00"),
    )
    for views in (1, 2, 3)
    for allow_single in (False, True)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _event_time(event: dict[str, object] | None) -> datetime | None:
    if not event:
        return None
    raw = event.get("at")
    if raw is None:
        return None
    value = datetime.fromisoformat(str(raw))
    if value.tzinfo is None:
        raise ValueError("event time must be timezone-aware")
    return value


def _age_bucket(
    event: dict[str, object] | None,
    decision_at: datetime,
) -> str:
    at = _event_time(event)
    if at is None:
        return "NONE"
    minutes = int((decision_at - at).total_seconds() // 60)
    if minutes < 0:
        raise ValueError("future event in pre-entry topology")
    if minutes <= 2:
        return "FRESH_0_2"
    if minutes <= 5:
        return "FRESH_3_5"
    if minutes <= 10:
        return "RECENT_6_10"
    if minutes <= 20:
        return "AGING_11_20"
    return "STALE_GT20"


def _event_alignment(
    event: dict[str, object] | None,
    *,
    side: str,
    kind: str,
) -> str:
    if not event:
        return "NONE"
    raw = str(event.get("side", "none"))
    if kind == "sweep":
        expected = "bullish-reclaim" if side == "long" else "bearish-reclaim"
    else:
        expected = "bullish" if side == "long" else "bearish"
    return "ALIGNED" if raw == expected else "OPPOSED"


def _order(
    left: dict[str, object] | None,
    right: dict[str, object] | None,
    *,
    left_name: str,
    right_name: str,
) -> str:
    left_at = _event_time(left)
    right_at = _event_time(right)
    if left_at is None or right_at is None:
        return "INCOMPLETE"
    if left_at < right_at:
        delta = int((right_at - left_at).total_seconds() // 60)
        if delta <= 5:
            return f"{left_name}_THEN_{right_name}_LE5"
        return f"{left_name}_THEN_{right_name}_GT5"
    if right_at < left_at:
        delta = int((left_at - right_at).total_seconds() // 60)
        if delta <= 5:
            return f"{right_name}_THEN_{left_name}_LE5"
        return f"{right_name}_THEN_{left_name}_GT5"
    return "SAME_MINUTE"


def _chain(
    sweep_alignment: str,
    displacement_alignment: str,
    fvg_alignment: str,
    sweep_order: str,
    fvg_order: str,
    displacement_freshness: str,
) -> str:
    aligned_count = sum(
        item == "ALIGNED"
        for item in (
            sweep_alignment,
            displacement_alignment,
            fvg_alignment,
        )
    )
    opposed_count = sum(
        item == "OPPOSED"
        for item in (
            sweep_alignment,
            displacement_alignment,
            fvg_alignment,
        )
    )
    if (
        sweep_alignment == "ALIGNED"
        and displacement_alignment == "ALIGNED"
        and sweep_order.startswith("SWEEP_THEN_DISPLACEMENT")
    ):
        return "ALIGNED_SWEEP_TO_DISPLACEMENT"
    if (
        fvg_alignment == "ALIGNED"
        and displacement_alignment == "ALIGNED"
        and (
            fvg_order.startswith("FVG_THEN_DISPLACEMENT")
            or fvg_order.startswith("DISPLACEMENT_THEN_FVG")
        )
    ):
        return "ALIGNED_FVG_DISPLACEMENT_CLUSTER"
    if aligned_count >= 2 and opposed_count == 0:
        return "ALIGNED_MULTI_EVENT"
    if opposed_count >= 2 and aligned_count == 0:
        return "OPPOSED_MULTI_EVENT"
    if (
        displacement_alignment == "ALIGNED"
        and displacement_freshness in {"FRESH_0_2", "FRESH_3_5"}
    ):
        return "FRESH_ALIGNED_DISPLACEMENT"
    if aligned_count and opposed_count:
        return "MIXED_CONFLICT"
    if aligned_count == 1:
        return "SINGLE_ALIGNED_EVENT"
    if opposed_count == 1:
        return "SINGLE_OPPOSED_EVENT"
    return "NO_SEQUENCE_EVIDENCE"


def _sequence_rows(
    raw_path: Path,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    base = v2._perception_rows(raw_path, rows)
    series, _, _, _, _, _ = load_market_evidence(raw_path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        key: tuple(
            sorted(values, key=lambda item: getattr(item, "opened_at"))
        )
        for key, values in grouped.items()
    }

    output: list[dict[str, object]] = []
    for source in base:
        row = dict(source)
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        decision_at = v2.v3._dt(row["signal_at"])
        day_bars = by_day[local_day]
        pre_entry = tuple(
            bar
            for bar in day_bars
            if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
            and getattr(bar, "closed_at") <= decision_at
        )
        sweeps = complete.local_sweep_events(cast(tuple, pre_entry))
        displacements = complete.displacement_events(cast(tuple, pre_entry))
        fvgs = complete.fvg_events(cast(tuple, pre_entry))
        last_sweep = sweeps[-1] if sweeps else None
        last_disp = displacements[-1] if displacements else None
        last_fvg = fvgs[-1] if fvgs else None
        side = str(row["side"])

        sweep_alignment = _event_alignment(
            last_sweep,
            side=side,
            kind="sweep",
        )
        displacement_alignment = _event_alignment(
            last_disp,
            side=side,
            kind="displacement",
        )
        fvg_alignment = _event_alignment(
            last_fvg,
            side=side,
            kind="fvg",
        )
        sweep_freshness = _age_bucket(last_sweep, decision_at)
        displacement_freshness = _age_bucket(last_disp, decision_at)
        fvg_freshness = _age_bucket(last_fvg, decision_at)
        sweep_displacement_order = _order(
            last_sweep,
            last_disp,
            left_name="SWEEP",
            right_name="DISPLACEMENT",
        )
        fvg_displacement_order = _order(
            last_fvg,
            last_disp,
            left_name="FVG",
            right_name="DISPLACEMENT",
        )
        sequence_chain = _chain(
            sweep_alignment,
            displacement_alignment,
            fvg_alignment,
            sweep_displacement_order,
            fvg_displacement_order,
            displacement_freshness,
        )

        row.update(
            {
                "sweep_alignment": sweep_alignment,
                "displacement_alignment": displacement_alignment,
                "fvg_alignment": fvg_alignment,
                "sweep_freshness": sweep_freshness,
                "displacement_freshness": displacement_freshness,
                "fvg_freshness": fvg_freshness,
                "sweep_displacement_order": sweep_displacement_order,
                "fvg_displacement_order": fvg_displacement_order,
                "sequence_chain": sequence_chain,
                "sequence_sweep_count": len(sweeps),
                "sequence_displacement_count": len(displacements),
                "sequence_fvg_count": len(fvgs),
            }
        )
        output.append(row)
    return output


def _split(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = len(ordered) // 2
    return ordered[:cut], ordered[cut:]


def _groups(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, object]]]:
    groups: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[v5._state(row, fields)].append(row)
    return groups


def _negative_tables(
    history: list[dict[str, object]],
) -> dict[str, set[tuple[str, ...]]]:
    old, recent = _split(history)
    output: dict[str, set[tuple[str, ...]]] = {}
    for name, fields in NEGATIVE_VIEWS.items():
        left_groups = _groups(old, fields)
        right_groups = _groups(recent, fields)
        states: set[tuple[str, ...]] = set()
        for key in set(left_groups).intersection(right_groups):
            left = v5._stats(left_groups[key])
            right = v5._stats(right_groups[key])
            if int(left["sample"]) < 3 or int(right["sample"]) < 3:
                continue
            lpf = cast(Decimal | None, left["profit_factor"])
            rpf = cast(Decimal | None, right["profit_factor"])
            if lpf is None or rpf is None:
                continue
            if (
                lpf <= Decimal("0.80")
                and rpf <= Decimal("0.80")
                and cast(Decimal, left["total_r"]) < 0
                and cast(Decimal, right["total_r"]) < 0
            ):
                states.add(key)
        output[name] = states
    return output


def _topology_tail_tables(
    history: list[dict[str, object]],
    policy: Policy,
) -> tuple[dict[str, set[tuple[str, ...]]], dict[str, object]]:
    old, recent = _split(history)
    output: dict[str, set[tuple[str, ...]]] = {}
    diagnostics: dict[str, object] = {}

    for name, fields in TOPOLOGY_VIEWS.items():
        left_groups = _groups(old, fields)
        right_groups = _groups(recent, fields)
        states: set[tuple[str, ...]] = set()
        details: list[dict[str, object]] = []
        for key in set(left_groups).intersection(right_groups):
            left = v5._stats(left_groups[key])
            right = v5._stats(right_groups[key])
            if (
                int(left["sample"]) < policy.minimum_half_sample
                or int(right["sample"]) < policy.minimum_half_sample
            ):
                continue
            lpf = cast(Decimal | None, left["profit_factor"])
            rpf = cast(Decimal | None, right["profit_factor"])
            if lpf is None or rpf is None:
                continue
            lw = int(left["wins"])
            rw = int(right["wins"])
            if lw < 1 or rw < 1:
                continue
            lm = cast(Decimal, left["gross_winner_r"]) / Decimal(lw)
            rm = cast(Decimal, right["gross_winner_r"]) / Decimal(rw)
            qualifies = (
                lpf >= policy.tail_pf_floor
                and rpf >= policy.tail_pf_floor
                and cast(Decimal, left["total_r"]) > 0
                and cast(Decimal, right["total_r"]) > 0
                and lm >= policy.tail_mean_winner_r_floor
                and rm >= policy.tail_mean_winner_r_floor
            )
            if qualifies:
                states.add(key)
                details.append(
                    {
                        "state": key,
                        "old_sample": left["sample"],
                        "recent_sample": right["sample"],
                        "old_pf": format(lpf, "f"),
                        "recent_pf": format(rpf, "f"),
                        "old_mean_winner_r": format(lm, "f"),
                        "recent_mean_winner_r": format(rm, "f"),
                    }
                )
        output[name] = states
        diagnostics[name] = {
            "tail_state_count": len(states),
            "states": details,
        }
    return output, diagnostics


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = peak = dd = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "profit_factor": (
            None if losses == 0 else format(gains / losses, "f")
        ),
        "total_r": format(total, "f"),
        "mean_r": (
            "0" if not values else format(total / Decimal(len(values)), "f")
        ),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    topology_tail: dict[str, set[tuple[str, ...]]],
    policy: Policy,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []
    chain_rescues: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative_views = sum(
            v5._state(row, fields) in negative[name]
            for name, fields in NEGATIVE_VIEWS.items()
        )
        if negative_views == 0:
            kept_values.append(value)
            continue

        topology_views = sum(
            v5._state(row, fields) in topology_tail[name]
            for name, fields in TOPOLOGY_VIEWS.items()
        )
        unique_chain_rescue = (
            policy.allow_single_view_when_unique_chain
            and topology_views >= 1
            and str(row["sequence_chain"])
            in {
                "ALIGNED_SWEEP_TO_DISPLACEMENT",
                "ALIGNED_FVG_DISPLACEMENT_CLUSTER",
                "ALIGNED_MULTI_EVENT",
                "FRESH_ALIGNED_DISPLACEMENT",
            }
        )
        rescue = (
            topology_views >= policy.required_topology_views
            or unique_chain_rescue
        )
        if rescue:
            kept_values.append(value)
            rescued.append(row)
            chain = str(row["sequence_chain"])
            chain_rescues[chain] = chain_rescues.get(chain, 0) + 1
        else:
            abstained.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0 for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    rescued_winners = sum(
        _d(row["net_r_after_friction"]) > 0 for row in rescued
    )
    rescued_losses = sum(
        _d(row["net_r_after_friction"]) < 0 for row in rescued
    )

    return {
        "baseline": baseline,
        "shared_sequence_topology": shared,
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
            "rescued_trades": len(rescued),
            "rescued_winners": rescued_winners,
            "rescued_losses": rescued_losses,
            "rescue_precision": (
                "0"
                if not rescued
                else format(
                    Decimal(rescued_winners) / Decimal(len(rescued)),
                    "f",
                )
            ),
            "chain_rescues": dict(sorted(chain_rescues.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_sequence_topology"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = _d(cast(object, baseline["profit_factor"]))
    spf = _d(cast(object, shared["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    sdd = _d(shared["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": (
            _d(selection["loss_rejection_recall"]) >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            _d(selection["winner_count_retention"]) >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            _d(selection["winner_r_retention"]) >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            _d(selection["density_retained"]) >= Decimal("0.55")
        ),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_sequence_topology"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(cast(object, shared["profit_factor"]))
        / _d(cast(object, baseline["profit_factor"]))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(selection["winner_r_retention"])
        * (Decimal("1") + _d(selection["loss_rejection_recall"]))
    )


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r5_trades: Path,
    r8_raw: Path,
    r6_raw: Path,
    r5_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = _sequence_rows(
        r8_raw,
        v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
    )
    r6 = _sequence_rows(
        r6_raw,
        v2.v3._decorate(v2.v3._load_trades(r6_trades), daily),
    )
    r5 = _sequence_rows(
        r5_raw,
        v2.v3._decorate(v2.v3._load_trades(r5_trades), daily),
    )
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    negative = _negative_tables(r8)
    frontier: list[dict[str, object]] = []
    best: tuple[
        Decimal,
        Policy,
        dict[str, set[tuple[str, ...]]],
        dict[str, object],
    ] | None = None

    for policy in POLICIES:
        topology_tail, diagnostics = _topology_tail_tables(r8, policy)
        calibration = _evaluate(
            r6,
            negative=negative,
            topology_tail=topology_tail,
            policy=policy,
        )
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append(
            {
                "policy": policy.payload(),
                "topology_tail_model": diagnostics,
                "calibration": calibration,
                "gates": gates,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, topology_tail, diagnostics)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_R6_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "frozen_topology_model": None,
            "evaluation": None,
            "gates": None,
            "passes_sequence_topology": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen, topology_tail, diagnostics = best
    evaluation = _evaluate(
        r5,
        negative=negative,
        topology_tail=topology_tail,
        policy=frozen,
    )
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
            "r8": "SEQUENCE_TOPOLOGY_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "frozen_topology_model": diagnostics,
        "evaluation": evaluation,
        "gates": gates,
        "passes_sequence_topology": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_exact_present_state_lookup_only": True,
        "sequence_topology_pre_entry_only": True,
        "future_m1_used": False,
        "current_outcome_used_at_runtime": False,
        "r5_retuned": False,
        "capital_risk_weighting_used": False,
        "methodology_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "live_authorized": False,
        "merge_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--r6-raw", type=Path, required=True)
    parser.add_argument("--r5-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r5_trades=args.r5_trades,
        r8_raw=args.r8_raw,
        r6_raw=args.r6_raw,
        r5_raw=args.r5_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_sequence_topology": payload["passes_sequence_topology"],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
