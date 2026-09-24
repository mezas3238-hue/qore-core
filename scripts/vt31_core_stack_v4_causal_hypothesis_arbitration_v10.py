"""VT31 Shared causal hypothesis arbitration V10.

Perception-first economic falsification using explicit concurrent hypotheses.

The runtime decision is not an analog lookup and not a winner-rescue table.
Present-market evidence builds SUPPORT, FAILURE and UNCERTAINTY hypotheses.
R8-derived negative state memory is permitted only as a secondary risk
contrast after the present-market hypothesis scores exist.

Protocol:
- R8: policy discovery.
- R6: calibration + freeze.
- R5: untouched evaluation only if every R6 hard gate passes.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_core_stack_v4_perception_state_model_v5 as v5

SCHEMA = "qore.core_stack_v4.vt31.causal_hypothesis_arbitration.v10"
IDENTITY = "VT31_NAS100_SHARED_CAUSAL_HYPOTHESIS_ARBITRATION_V10"


@dataclass(frozen=True, slots=True)
class Policy:
    minimum_memory_risk_views: int
    failure_threshold: int
    dominance_margin: int
    support_override_threshold: int
    standalone_failure_threshold: int
    maximum_uncertainty_for_abstain: int
    memory_bonus: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_memory_risk_views": self.minimum_memory_risk_views,
            "failure_threshold": self.failure_threshold,
            "dominance_margin": self.dominance_margin,
            "support_override_threshold": self.support_override_threshold,
            "standalone_failure_threshold": self.standalone_failure_threshold,
            "maximum_uncertainty_for_abstain": self.maximum_uncertainty_for_abstain,
            "memory_bonus": self.memory_bonus,
        }


POLICIES = tuple(
    Policy(
        minimum_memory_risk_views=memory_views,
        failure_threshold=failure,
        dominance_margin=margin,
        support_override_threshold=override,
        standalone_failure_threshold=standalone,
        maximum_uncertainty_for_abstain=max_uncertainty,
        memory_bonus=memory_bonus,
    )
    for memory_views in (1, 2)
    for failure in (3, 4, 5, 6)
    for margin in (1, 2, 3)
    for override in (4, 5, 6, 7)
    for standalone in (7, 8, 99)
    for max_uncertainty in (2, 3, 4, 99)
    for memory_bonus in (0, 1)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _relative_direction(state: str, side: str) -> str:
    if state not in {"bullish", "bearish"}:
        return "NEUTRAL"
    aligned = (side == "long" and state == "bullish") or (
        side == "short" and state == "bearish"
    )
    return "ALIGNED" if aligned else "OPPOSED"


def _hypotheses(
    row: dict[str, object],
    *,
    negative_views: int,
    policy: Policy,
) -> dict[str, object]:
    support = 0
    failure = 0
    uncertainty = 0
    support_evidence: list[str] = []
    failure_evidence: list[str] = []
    uncertainty_evidence: list[str] = []

    def add_support(points: int, reason: str) -> None:
        nonlocal support
        support += points
        support_evidence.append(reason)

    def add_failure(points: int, reason: str) -> None:
        nonlocal failure
        failure += points
        failure_evidence.append(reason)

    def add_uncertainty(points: int, reason: str) -> None:
        nonlocal uncertainty
        uncertainty += points
        uncertainty_evidence.append(reason)

    alignment5 = str(row.get("alignment5", "NEUTRAL"))
    alignment20 = str(row.get("alignment20", "NEUTRAL"))
    if alignment5 == "ALIGNED":
        add_support(2, "SHORT_PATH_ALIGNED")
    elif alignment5 == "OPPOSED":
        add_failure(2, "SHORT_PATH_OPPOSED")
    else:
        add_uncertainty(1, "SHORT_PATH_NEUTRAL")

    if alignment20 == "ALIGNED":
        add_support(1, "MEDIUM_PATH_ALIGNED")
    elif alignment20 == "OPPOSED":
        add_failure(1, "MEDIUM_PATH_OPPOSED")

    displacement = str(row.get("displacement_alignment", "NONE"))
    displacement_freshness = str(row.get("displacement_freshness", "NONE"))
    if displacement == "ALIGNED":
        add_support(2, "DISPLACEMENT_ALIGNED")
        if displacement_freshness in {"FRESH_0_2", "FRESH_3_5"}:
            add_support(1, "DISPLACEMENT_FRESH")
    elif displacement == "OPPOSED":
        add_failure(2, "DISPLACEMENT_OPPOSED")
        if displacement_freshness in {"FRESH_0_2", "FRESH_3_5"}:
            add_failure(1, "ADVERSE_DISPLACEMENT_FRESH")

    sweep = str(row.get("sweep_alignment", "NONE"))
    if sweep == "ALIGNED":
        add_support(1, "SWEEP_RECLAIM_ALIGNED")
    elif sweep == "OPPOSED":
        add_failure(1, "SWEEP_RECLAIM_OPPOSED")

    fvg = str(row.get("fvg_alignment", "NONE"))
    if fvg == "ALIGNED":
        add_support(1, "FVG_ALIGNED")
    elif fvg == "OPPOSED":
        add_failure(1, "FVG_OPPOSED")

    chain = str(row.get("sequence_chain", "NO_SEQUENCE_EVIDENCE"))
    if chain == "ALIGNED_SWEEP_TO_DISPLACEMENT":
        add_support(3, "CHAIN_SWEEP_TO_DISPLACEMENT")
    elif chain == "ALIGNED_FVG_DISPLACEMENT_CLUSTER":
        add_support(2, "CHAIN_FVG_DISPLACEMENT")
    elif chain == "ALIGNED_MULTI_EVENT":
        add_support(2, "CHAIN_MULTI_EVENT_ALIGNED")
    elif chain == "FRESH_ALIGNED_DISPLACEMENT":
        add_support(2, "CHAIN_FRESH_DISPLACEMENT")
    elif chain == "OPPOSED_MULTI_EVENT":
        add_failure(3, "CHAIN_MULTI_EVENT_OPPOSED")
    elif chain == "MIXED_CONFLICT":
        add_uncertainty(2, "CHAIN_CONFLICT")
    elif chain == "NO_SEQUENCE_EVIDENCE":
        add_uncertainty(1, "CHAIN_ABSENT")

    peer = str(row.get("peer_consensus", "incomplete"))
    if peer == "both-confirm":
        add_support(2, "PEERS_BOTH_CONFIRM")
    elif peer == "one-confirm":
        add_support(1, "PEER_ONE_CONFIRM")
    elif peer == "both-oppose":
        add_failure(2, "PEERS_BOTH_OPPOSE")
    elif peer == "divergent":
        add_uncertainty(2, "PEER_DIVERGENCE")
    else:
        add_uncertainty(1, "PEER_INCOMPLETE")

    side = str(row.get("side", ""))
    h1 = _relative_direction(str(row.get("h1_state_hr", "unavailable")), side)
    if h1 == "ALIGNED":
        add_support(1, "H1_ALIGNED")
    elif h1 == "OPPOSED":
        add_failure(1, "H1_OPPOSED")
    else:
        add_uncertainty(1, "H1_UNRESOLVED")

    trend = _d(row.get("trend_pressure", "0"))
    expansion = _d(row.get("expansion_pressure", "0"))
    range_pressure = _d(row.get("range_pressure", "0"))
    exhaustion = _d(row.get("exhaustion_pressure", "0"))
    uncertainty_pressure = _d(row.get("uncertainty_pressure", "0"))

    if trend >= Decimal("0.60"):
        if alignment5 == "ALIGNED":
            add_support(1, "TREND_PRESSURE_SUPPORTS_SIDE")
        elif alignment5 == "OPPOSED":
            add_failure(1, "TREND_PRESSURE_OPPOSES_SIDE")
    if expansion >= Decimal("0.50"):
        if alignment5 == "ALIGNED":
            add_support(1, "EXPANSION_SUPPORTS_SIDE")
        elif alignment5 == "OPPOSED":
            add_failure(1, "EXPANSION_OPPOSES_SIDE")
    if range_pressure >= Decimal("0.65"):
        add_uncertainty(1, "HIGH_RANGE_PRESSURE")
    if exhaustion >= Decimal("0.35"):
        add_uncertainty(1, "EXHAUSTION_PRESENT")
    if uncertainty_pressure >= Decimal("0.45"):
        add_uncertainty(1, "PERCEPTION_UNCERTAINTY")

    transition = str(row.get("perception_transition", "STABLE"))
    if transition.endswith("_TO_TREND_EXPANSION"):
        if alignment5 == "ALIGNED":
            add_support(2, "TRANSITION_TO_ALIGNED_EXPANSION")
        elif alignment5 == "OPPOSED":
            add_failure(2, "TRANSITION_TO_ADVERSE_EXPANSION")
    elif (
        transition.endswith("_TO_RANGE")
        or transition.endswith("_TO_COMPRESSION")
        or transition.endswith("_TO_EXHAUSTION")
    ):
        add_uncertainty(1, "TRANSITION_NON_DIRECTIONAL")

    memory_risk = negative_views >= policy.minimum_memory_risk_views
    effective_failure = failure + (
        min(negative_views, 2) * policy.memory_bonus if memory_risk else 0
    )
    dominant_failure = (
        effective_failure >= policy.failure_threshold
        and effective_failure - support >= policy.dominance_margin
        and support < policy.support_override_threshold
        and uncertainty <= policy.maximum_uncertainty_for_abstain
    )
    standalone_failure = (
        failure >= policy.standalone_failure_threshold
        and failure - support >= policy.dominance_margin
        and support < policy.support_override_threshold
        and uncertainty <= policy.maximum_uncertainty_for_abstain
    )
    abstain = (memory_risk and dominant_failure) or standalone_failure

    return {
        "support_score": support,
        "failure_score": failure,
        "effective_failure_score": effective_failure,
        "uncertainty_score": uncertainty,
        "negative_memory_views": negative_views,
        "memory_risk": memory_risk,
        "support_evidence": support_evidence,
        "failure_evidence": failure_evidence,
        "uncertainty_evidence": uncertainty_evidence,
        "action": "ABSTAIN_FAILURE_DOMINANT" if abstain else "PASS",
    }


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
        "profit_factor": None if losses == 0 else format(gains / losses, "f"),
        "total_r": format(total, "f"),
        "mean_r": "0" if not values else format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    policy: Policy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    hypothesis_histogram: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative_views = sum(
            v5._state(row, fields) in negative[name]
            for name, fields in v8.NEGATIVE_VIEWS.items()
        )
        view = _hypotheses(row, negative_views=negative_views, policy=policy)
        key = (
            f"S{view['support_score']}_F{view['failure_score']}"
            f"_U{view['uncertainty_score']}_M{negative_views}"
        )
        hypothesis_histogram[key] = hypothesis_histogram.get(key, 0) + 1
        if view["action"] == "ABSTAIN_FAILURE_DOMINANT":
            item = dict(row)
            item["hypothesis_view"] = view
            abstained.append(item)
        else:
            kept_values.append(value)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((value for value in baseline_values if value > 0), Decimal(0))
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    return {
        "baseline": baseline,
        "shared_hypothesis_arbitration": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0" if base_losses == 0 else format(Decimal(losses_avoided) / Decimal(base_losses), "f"),
            "winner_count_retention": "0" if base_wins == 0 else format(Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f"),
            "winner_r_retention": "1" if gross_winner_r == 0 else format((gross_winner_r - sacrificed_r) / gross_winner_r, "f"),
            "density_retained": "0" if not rows else format(Decimal(len(kept_values)) / Decimal(len(rows)), "f"),
            "hypothesis_histogram": dict(sorted(hypothesis_histogram.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_hypothesis_arbitration"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"]) >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_minus_30pct": _d(shared["max_drawdown_r"]) <= _d(baseline["max_drawdown_r"]) * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(selection["loss_rejection_recall"]) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(selection["winner_count_retention"]) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": _d(selection["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"]) >= Decimal("0.55"),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_hypothesis_arbitration"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(shared["profit_factor"]) / _d(baseline["profit_factor"])
        * _d(baseline["max_drawdown_r"]) / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
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
    r8 = v8._sequence_rows(r8_raw, v2.v3._decorate(v2.v3._load_trades(r8_trades), daily))
    r6 = v8._sequence_rows(r6_raw, v2.v3._decorate(v2.v3._load_trades(r6_trades), daily))
    all_discovery_rows = r8 + r6
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    discovery: list[tuple[Decimal, Policy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(r8, negative=negative, policy=policy)
        gates = _gates(result)
        score = _score(result)
        r8_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None:
            discovery.append((score, policy))

    discovery.sort(key=lambda item: item[0], reverse=True)
    candidates = discovery[:96]
    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for _, policy in candidates:
        result = _evaluate(r6, negative=negative, policy=policy)
        gates = _gates(result)
        score = _score(result)
        r6_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_BEFORE_R5",
            "challenge_set": {"r8": 228, "r6": 278, "r5": 316},
            "r5_opened": False,
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_hypothesis_arbitration": False,
            "r8_frontier": r8_frontier,
            "r6_frontier": r6_frontier,
            "governance": _governance(),
        }

    frozen = best[1]
    r5 = v8._sequence_rows(r5_raw, v2.v3._decorate(v2.v3._load_trades(r5_trades), daily))
    if len(r5) != 316 or len(all_discovery_rows) + len(r5) != 822:
        raise AssertionError("VT31 R5 challenge-set drift")
    evaluation = _evaluate(r5, negative=negative, policy=frozen)
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set": {"r8": 228, "r6": 278, "r5": 316},
        "r5_opened": True,
        "temporal_protocol": {
            "r8": "CAUSAL_HYPOTHESIS_POLICY_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_hypothesis_arbitration": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "present_market_hypotheses_primary": True,
        "historical_memory_secondary_only": True,
        "runtime_analog_lookup_used": False,
        "runtime_outcome_label_used": False,
        "future_m1_used": False,
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
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "r5_opened": payload["r5_opened"],
        "passes_hypothesis_arbitration": payload["passes_hypothesis_arbitration"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
