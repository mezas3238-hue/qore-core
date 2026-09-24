"""Perception-first VT31 V3: independent causal confluence.

Unlike V2's generic additive score, V3 abstains only when multiple independent
present-market failure families agree. It also protects strong continuation
states using present observations only.

Runtime inputs:
- current M1 perception/situation,
- causal high-resolution pre-entry path state,
- current peer consensus as of signal.

No analog lookup, no outcome lookup, no capital weighting.
R8 discovery -> R6 calibration/freeze -> untouched R5.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_first_v2 as v2


SCHEMA = "qore.core_stack_v4.vt31.perception_confluence.v3"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_CONFLUENCE_V3"


@dataclass(frozen=True, slots=True)
class Policy:
    trend_threshold: Decimal
    expansion_threshold: Decimal
    range_threshold: Decimal
    uncertainty_threshold: Decimal
    exhaustion_threshold: Decimal
    overlap_threshold: Decimal
    efficiency_threshold: Decimal
    required_adverse_families: int
    maximum_favorable_families: int
    protect_required_families: int

    def payload(self) -> dict[str, object]:
        return {
            "trend_threshold": format(self.trend_threshold, "f"),
            "expansion_threshold": format(self.expansion_threshold, "f"),
            "range_threshold": format(self.range_threshold, "f"),
            "uncertainty_threshold": format(self.uncertainty_threshold, "f"),
            "exhaustion_threshold": format(self.exhaustion_threshold, "f"),
            "overlap_threshold": format(self.overlap_threshold, "f"),
            "efficiency_threshold": format(self.efficiency_threshold, "f"),
            "required_adverse_families": self.required_adverse_families,
            "maximum_favorable_families": self.maximum_favorable_families,
            "protect_required_families": self.protect_required_families,
        }


POLICIES = tuple(
    Policy(
        trend_threshold=trend,
        expansion_threshold=expansion,
        range_threshold=range_p,
        uncertainty_threshold=uncertainty,
        exhaustion_threshold=exhaustion,
        overlap_threshold=overlap,
        efficiency_threshold=efficiency,
        required_adverse_families=required,
        maximum_favorable_families=max_fav,
        protect_required_families=protect,
    )
    for trend in (Decimal("0.45"), Decimal("0.60"))
    for expansion in (Decimal("0.35"), Decimal("0.50"))
    for range_p in (Decimal("0.50"), Decimal("0.65"))
    for uncertainty in (Decimal("0.30"), Decimal("0.45"))
    for exhaustion in (Decimal("0.20"), Decimal("0.35"))
    for overlap in (Decimal("0.65"), Decimal("0.75"))
    for efficiency in (Decimal("0.50"), Decimal("0.65"))
    for required in (2, 3)
    for max_fav in (0, 1)
    for protect in (2, 3)
)


def _d_or_none(value: object) -> Decimal | None:
    raw = str(value)
    if raw in {"unavailable", "None", "null", ""}:
        return None
    try:
        return Decimal(raw)
    except Exception:
        return None


def _peer_state(row: dict[str, object]) -> str:
    return str(row.get("peer_consensus", "incomplete"))


def _families(
    row: dict[str, object],
    policy: Policy,
) -> tuple[set[str], set[str]]:
    adverse: set[str] = set()
    favorable: set[str] = set()

    trend = Decimal(str(row["trend_pressure"]))
    expansion = Decimal(str(row["expansion_pressure"]))
    range_p = Decimal(str(row["range_pressure"]))
    uncertainty = Decimal(str(row["uncertainty_pressure"]))
    exhaustion = Decimal(str(row["exhaustion_pressure"]))
    alignment5 = str(row["alignment5"])
    alignment20 = str(row["alignment20"])
    transition = str(row["perception_transition"])
    regime = str(row["perception_regime"])
    structure = str(row["structure_state"])
    momentum = str(row["momentum_state"])
    peer = _peer_state(row)

    pre_overlap = _d_or_none(row.get("pre_overlap_rate"))
    recent_overlap = _d_or_none(row.get("recent_overlap_rate_hr"))
    pre_eff = _d_or_none(row.get("pre_path_efficiency"))
    recent_eff = _d_or_none(row.get("recent_path_efficiency_hr"))
    displacement_count = _d_or_none(row.get("pre_displacement_count"))
    sweep_count = _d_or_none(row.get("pre_sweep_reclaim_count"))

    # Independent adverse families.
    if (
        alignment5 == "OPPOSED"
        and trend >= policy.trend_threshold
    ):
        adverse.add("DIRECTIONAL_CONTRADICTION")

    if (
        alignment5 == "OPPOSED"
        and expansion >= policy.expansion_threshold
        and structure in {"IMPULSE", "TRANSITIONAL"}
    ):
        adverse.add("ADVERSE_EXPANSION")

    overlap_high = any(
        value is not None and value >= policy.overlap_threshold
        for value in (pre_overlap, recent_overlap)
    )
    if (
        range_p >= policy.range_threshold
        and uncertainty >= policy.uncertainty_threshold
        and overlap_high
    ):
        adverse.add("ROTATIONAL_TRAP")

    if (
        exhaustion >= policy.exhaustion_threshold
        and (
            "TO_TRANSITION" in transition
            or "TO_EXHAUSTION" in transition
            or regime in {"EXHAUSTION", "TRANSITION"}
        )
    ):
        adverse.add("EXHAUSTION_TRANSITION")

    if peer in {"divergent", "both-oppose"}:
        adverse.add("CROSS_MARKET_CONTRADICTION")

    if (
        alignment20 == "OPPOSED"
        and momentum == "DIRECTIONAL"
        and trend >= policy.trend_threshold
    ):
        adverse.add("MEDIUM_PATH_CONTRADICTION")

    # Independent favorable families.
    if (
        alignment5 == "ALIGNED"
        and alignment20 == "ALIGNED"
        and trend >= policy.trend_threshold
    ):
        favorable.add("DIRECTIONAL_ALIGNMENT")

    if (
        alignment5 == "ALIGNED"
        and expansion >= policy.expansion_threshold
        and structure == "IMPULSE"
    ):
        favorable.add("ALIGNED_EXPANSION")

    if peer == "both-confirm":
        favorable.add("CROSS_MARKET_CONFIRMATION")

    efficiency_good = any(
        value is not None and value >= policy.efficiency_threshold
        for value in (pre_eff, recent_eff)
    )
    overlap_low = all(
        value is None or value < policy.overlap_threshold
        for value in (pre_overlap, recent_overlap)
    )
    if efficiency_good and overlap_low:
        favorable.add("EFFICIENT_LOW_OVERLAP_PATH")

    if (
        displacement_count is not None
        and displacement_count >= Decimal("1")
        and sweep_count is not None
        and sweep_count >= Decimal("1")
        and alignment5 != "OPPOSED"
    ):
        favorable.add("STRUCTURAL_DISPLACEMENT_SUPPORT")

    return adverse, favorable


def _verdict(
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    adverse, favorable = _families(row, policy)

    severe = (
        "DIRECTIONAL_CONTRADICTION" in adverse
        and (
            "ADVERSE_EXPANSION" in adverse
            or "CROSS_MARKET_CONTRADICTION" in adverse
        )
    )
    protected = (
        len(favorable) >= policy.protect_required_families
        and "CROSS_MARKET_CONTRADICTION" not in adverse
        and not severe
    )
    abstain = (
        not protected
        and len(adverse) >= policy.required_adverse_families
        and len(favorable) <= policy.maximum_favorable_families
    )

    return {
        "action": (
            "PASS_PROTECTED"
            if protected
            else "ABSTAIN_PERCEPTION"
            if abstain
            else "PASS"
        ),
        "adverse_families": tuple(sorted(adverse)),
        "favorable_families": tuple(sorted(favorable)),
        "severe": severe,
        "protected": protected,
    }


def _evaluate(
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    protected_rows: list[dict[str, object]] = []
    adverse_counts: dict[str, int] = {}
    favorable_counts: dict[str, int] = {}

    for row in ordered:
        value = Decimal(str(row["net_r_after_friction"]))
        baseline_values.append(value)
        verdict = _verdict(row, policy)
        for name in cast(tuple[str, ...], verdict["adverse_families"]):
            adverse_counts[name] = adverse_counts.get(name, 0) + 1
        for name in cast(tuple[str, ...], verdict["favorable_families"]):
            favorable_counts[name] = favorable_counts.get(name, 0) + 1
        if verdict["action"] == "ABSTAIN_PERCEPTION":
            abstained.append(row)
        else:
            kept_values.append(value)
            if verdict["action"] == "PASS_PROTECTED":
                protected_rows.append(row)

    baseline = v2._metrics(baseline_values)
    shared = v2._metrics(kept_values)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(
        Decimal(str(row["net_r_after_friction"])) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        Decimal(str(row["net_r_after_friction"])) > 0 for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    sacrificed_winner_r = sum(
        (
            Decimal(str(row["net_r_after_friction"]))
            for row in abstained
            if Decimal(str(row["net_r_after_friction"])) > 0
        ),
        Decimal(0),
    )
    protected_winners = sum(
        Decimal(str(row["net_r_after_friction"])) > 0 for row in protected_rows
    )
    protected_losses = sum(
        Decimal(str(row["net_r_after_friction"])) < 0 for row in protected_rows
    )

    return {
        "baseline": baseline,
        "shared_perception_confluence": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if baseline_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(baseline_losses),
                    "f",
                )
            ),
            "winner_count_retention": (
                "0"
                if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed)
                    / Decimal(baseline_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1"
                if gross_winner_r == 0
                else format(
                    (gross_winner_r - sacrificed_winner_r)
                    / gross_winner_r,
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
            "protected_trades": len(protected_rows),
            "protected_winners": protected_winners,
            "protected_losses": protected_losses,
        },
        "perception": {
            "adverse_family_counts": dict(sorted(adverse_counts.items())),
            "favorable_family_counts": dict(sorted(favorable_counts.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_perception_confluence"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = Decimal(str(baseline["profit_factor"]))
    spf = Decimal(str(shared["profit_factor"]))
    bdd = Decimal(str(baseline["max_drawdown_r"]))
    sdd = Decimal(str(shared["max_drawdown_r"]))
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "total_r_not_lower": Decimal(str(shared["total_r"])) >= Decimal(str(baseline["total_r"])),
        "loss_recall_at_least_25pct": Decimal(str(selection["loss_rejection_recall"])) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": Decimal(str(selection["winner_count_retention"])) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": Decimal(str(selection["winner_r_retention"])) >= Decimal("0.90"),
        "density_at_least_55pct": Decimal(str(selection["density_retained"])) >= Decimal("0.55"),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_perception_confluence"])
    selection = cast(dict[str, object], result["selection"])
    return (
        Decimal(str(shared["profit_factor"]))
        / Decimal(str(baseline["profit_factor"]))
        * Decimal(str(baseline["max_drawdown_r"]))
        / max(Decimal(str(shared["max_drawdown_r"])), Decimal("0.000001"))
        * Decimal(str(selection["winner_r_retention"]))
        * (Decimal("1") + Decimal(str(selection["loss_rejection_recall"])))
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
    r8 = v2._perception_rows(
        r8_raw,
        v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
    )
    r6 = v2._perception_rows(
        r6_raw,
        v2.v3._decorate(v2.v3._load_trades(r6_trades), daily),
    )
    r5 = v2._perception_rows(
        r5_raw,
        v2.v3._decorate(v2.v3._load_trades(r5_trades), daily),
    )
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(Decimal(str(row["net_r_after_friction"])) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(Decimal(str(row["net_r_after_friction"])) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    discovery: list[tuple[Decimal, Policy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(r8, policy)
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
        result = _evaluate(r6, policy)
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
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_perception_confluence": False,
            "r8_frontier": r8_frontier,
            "r6_frontier": r6_frontier,
            "governance": _governance(),
        }

    frozen = best[1]
    evaluation = _evaluate(r5, frozen)
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
            "r8": "PERCEPTION_CONFLUENCE_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_perception_confluence": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_outcome_label_used": False,
        "present_market_perception_primary": True,
        "independent_causal_confluence_required": True,
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
        "passes_perception_confluence": payload["passes_perception_confluence"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
