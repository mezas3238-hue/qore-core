"""Perception-first VT31 falsification.

Runtime decision inputs are present-market observations only. There is no
analog lookup at decision time. Historical outcomes are used only offline to
select/freeze one deterministic perception policy in R8/R6 before untouched R5.

R8: discovery of perception policy.
R6: calibration + freeze.
R5: no-retune evaluation.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v4_high_resolution_perception_v1 as hr

from qore.infrastructure.core_stack_v2.perception_engine import (
    PerceptionBar,
    infer_situation,
    perceive_market,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.core_stack_v4.vt31.perception_first.v2"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_FIRST_V2"


@dataclass(frozen=True, slots=True)
class PerceptionPolicy:
    adverse_score_threshold: int
    uncertainty_threshold: Decimal
    trend_pressure_threshold: Decimal
    range_pressure_threshold: Decimal
    expansion_pressure_threshold: Decimal
    exhaustion_pressure_threshold: Decimal
    minimum_peer_risk: int
    protect_strong_alignment: bool

    def payload(self) -> dict[str, object]:
        return {
            "adverse_score_threshold": self.adverse_score_threshold,
            "uncertainty_threshold": format(self.uncertainty_threshold, "f"),
            "trend_pressure_threshold": format(self.trend_pressure_threshold, "f"),
            "range_pressure_threshold": format(self.range_pressure_threshold, "f"),
            "expansion_pressure_threshold": format(self.expansion_pressure_threshold, "f"),
            "exhaustion_pressure_threshold": format(self.exhaustion_pressure_threshold, "f"),
            "minimum_peer_risk": self.minimum_peer_risk,
            "protect_strong_alignment": self.protect_strong_alignment,
        }


POLICIES = tuple(
    PerceptionPolicy(
        adverse_score_threshold=score,
        uncertainty_threshold=uncertainty,
        trend_pressure_threshold=trend,
        range_pressure_threshold=range_p,
        expansion_pressure_threshold=expansion,
        exhaustion_pressure_threshold=exhaustion,
        minimum_peer_risk=peer,
        protect_strong_alignment=protect,
    )
    for score in (3, 4, 5)
    for uncertainty in (Decimal("0.30"), Decimal("0.45"), Decimal("0.60"))
    for trend in (Decimal("0.45"), Decimal("0.60"))
    for range_p in (Decimal("0.50"), Decimal("0.65"))
    for expansion in (Decimal("0.35"), Decimal("0.50"))
    for exhaustion in (Decimal("0.20"), Decimal("0.35"))
    for peer in (0, 1)
    for protect in (False, True)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _convert_bar(bar: object) -> PerceptionBar:
    return PerceptionBar(
        opened_at=getattr(bar, "opened_at").isoformat(),
        closed_at=getattr(bar, "closed_at").isoformat(),
        open=_d(getattr(bar, "open")),
        high=_d(getattr(bar, "high")),
        low=_d(getattr(bar, "low")),
        close=_d(getattr(bar, "close")),
    )


def _direction(
    bars: tuple[object, ...],
    *,
    decision_at: object,
    lookback: int,
) -> str:
    closed = [
        bar
        for bar in bars
        if getattr(bar, "closed_at") <= decision_at
    ][-lookback:]
    if len(closed) < 2:
        return "FLAT"
    first = _d(getattr(closed[0], "open"))
    last = _d(getattr(closed[-1], "close"))
    if last > first:
        return "UP"
    if last < first:
        return "DOWN"
    return "FLAT"


def _alignment(side: str, direction: str) -> str:
    if direction == "FLAT":
        return "NEUTRAL"
    if (side == "long" and direction == "UP") or (
        side == "short" and direction == "DOWN"
    ):
        return "ALIGNED"
    return "OPPOSED"


def _perception_rows(
    raw_path: Path,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    # Keep all pre-existing causal high-resolution context, including peer
    # consensus, then add the new present-market perception engine.
    base_rows = hr._raw_context(raw_path, rows)
    series, _, _, _, _, _ = load_market_evidence(raw_path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        key: tuple(sorted(values, key=lambda item: getattr(item, "opened_at")))
        for key, values in grouped.items()
    }

    output: list[dict[str, object]] = []
    for source in base_rows:
        row = dict(source)
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        day_bars = by_day[local_day]
        decision_at = v3._dt(row["signal_at"])
        visible = tuple(
            bar
            for bar in day_bars
            if getattr(bar, "closed_at") <= decision_at
            and (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
        )
        if not visible:
            raise ValueError(f"no visible M1 bars for {row['signal_at']}")

        converted = tuple(_convert_bar(bar) for bar in visible)
        current = perceive_market(
            converted,
            as_of=decision_at.isoformat(),
            short_window=5,
            long_window=20,
        )
        prior_at = decision_at - timedelta(minutes=5)
        prior_visible = tuple(
            bar
            for bar in visible
            if getattr(bar, "closed_at") <= prior_at
        )
        previous = None
        if prior_visible:
            previous = perceive_market(
                tuple(_convert_bar(bar) for bar in prior_visible),
                as_of=prior_at.isoformat(),
                short_window=5,
                long_window=20,
            )
        situation = infer_situation(current, previous=previous)
        direction5 = _direction(
            day_bars,
            decision_at=decision_at,
            lookback=5,
        )
        direction20 = _direction(
            day_bars,
            decision_at=decision_at,
            lookback=20,
        )
        side = str(row["side"])

        row.update({
            "perception_regime": situation.regime,
            "perception_transition": situation.transition,
            "perception_confidence_bps": situation.confidence_bps,
            "trend_pressure": format(situation.trend_pressure, "f"),
            "range_pressure": format(situation.range_pressure, "f"),
            "expansion_pressure": format(situation.expansion_pressure, "f"),
            "exhaustion_pressure": format(situation.exhaustion_pressure, "f"),
            "uncertainty_pressure": format(situation.uncertainty_pressure, "f"),
            "momentum_state": current.momentum_state,
            "volatility_state": current.volatility_state,
            "structure_state": current.structure_state,
            "direction5": direction5,
            "direction20": direction20,
            "alignment5": _alignment(side, direction5),
            "alignment20": _alignment(side, direction20),
            "anomaly_flags": "|".join(current.anomaly_flags),
            "perception_fingerprint": current.fingerprint,
            "situation_fingerprint": situation.fingerprint,
        })
        output.append(row)
    return output


def _peer_risk(row: dict[str, object]) -> int:
    state = str(row.get("peer_consensus", "incomplete"))
    return {
        "both-confirm": 0,
        "one-confirm": 0,
        "incomplete": 1,
        "divergent": 1,
        "both-oppose": 2,
    }.get(state, 1)


def _score(row: dict[str, object], policy: PerceptionPolicy) -> dict[str, object]:
    score = 0
    reasons: list[str] = []
    trend = _d(row["trend_pressure"])
    range_p = _d(row["range_pressure"])
    expansion = _d(row["expansion_pressure"])
    exhaustion = _d(row["exhaustion_pressure"])
    uncertainty = _d(row["uncertainty_pressure"])
    alignment5 = str(row["alignment5"])
    alignment20 = str(row["alignment20"])
    regime = str(row["perception_regime"])
    transition = str(row["perception_transition"])
    peer = _peer_risk(row)

    if alignment5 == "OPPOSED" and trend >= policy.trend_pressure_threshold:
        score += 2
        reasons.append("SHORT_TERM_OPPOSED_TREND")
    if alignment20 == "OPPOSED" and trend >= policy.trend_pressure_threshold:
        score += 1
        reasons.append("MEDIUM_TERM_OPPOSED_TREND")
    if range_p >= policy.range_pressure_threshold:
        score += 1
        reasons.append("RANGE_PRESSURE")
    if uncertainty >= policy.uncertainty_threshold:
        score += 1
        reasons.append("HIGH_UNCERTAINTY")
    if exhaustion >= policy.exhaustion_pressure_threshold:
        score += 1
        reasons.append("EXHAUSTION")
    if regime == "TRANSITION":
        score += 1
        reasons.append("TRANSITION_REGIME")
    if "TO_TRANSITION" in transition or "TO_EXHAUSTION" in transition:
        score += 1
        reasons.append("ADVERSE_TRANSITION")
    if peer >= policy.minimum_peer_risk and peer > 0:
        score += peer
        reasons.append("PEER_RISK")
    if (
        expansion >= policy.expansion_pressure_threshold
        and alignment5 == "OPPOSED"
    ):
        score += 2
        reasons.append("OPPOSED_EXPANSION")

    protected = False
    if policy.protect_strong_alignment:
        protected = (
            alignment5 == "ALIGNED"
            and alignment20 == "ALIGNED"
            and trend >= policy.trend_pressure_threshold
            and expansion >= policy.expansion_pressure_threshold
            and peer == 0
        )
    action = (
        "PASS_STRONG_ALIGNMENT"
        if protected
        else "ABSTAIN_PERCEPTION"
        if score >= policy.adverse_score_threshold
        else "PASS"
    )
    return {
        "action": action,
        "adverse_score": score,
        "reasons": reasons,
        "protected": protected,
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
    policy: PerceptionPolicy,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    score_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    regime_counts: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        verdict = _score(row, policy)
        score_key = str(verdict["adverse_score"])
        score_counts[score_key] = score_counts.get(score_key, 0) + 1
        regime = str(row["perception_regime"])
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
        for reason in cast(list[str], verdict["reasons"]):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if verdict["action"] == "ABSTAIN_PERCEPTION":
            abstained.append(row)
        else:
            kept_values.append(value)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
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
    sacrificed_winner_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    return {
        "baseline": baseline,
        "shared_perception_first": shared,
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
                    Decimal(losses_avoided) / Decimal(baseline_losses), "f"
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
                    Decimal(len(kept_values)) / Decimal(len(rows)), "f"
                )
            ),
        },
        "perception": {
            "adverse_score_counts": dict(sorted(score_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
            "regime_counts": dict(sorted(regime_counts.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_perception_first"])
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


def _score_policy(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_perception_first"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(cast(object, shared["profit_factor"]))
        / _d(cast(object, baseline["profit_factor"]))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(selection["winner_r_retention"])
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
    daily = v3._load_daily(daily_path)
    r8 = _perception_rows(
        r8_raw,
        v3._decorate(v3._load_trades(r8_trades), daily),
    )
    r6 = _perception_rows(
        r6_raw,
        v3._decorate(v3._load_trades(r6_trades), daily),
    )
    r5 = _perception_rows(
        r5_raw,
        v3._decorate(v3._load_trades(r5_trades), daily),
    )
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    discovery: list[tuple[Decimal, PerceptionPolicy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(r8, policy)
        gates = _gates(result)
        score = _score_policy(result)
        r8_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None:
            discovery.append((score, policy))

    # Discovery must pass on R8 before calibration. Take at most the best 64 to
    # R6, preserving a genuine temporal funnel.
    discovery.sort(key=lambda item: item[0], reverse=True)
    candidates = discovery[:64]
    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, PerceptionPolicy] | None = None
    for _, policy in candidates:
        result = _evaluate(r6, policy)
        gates = _gates(result)
        score = _score_policy(result)
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
            "passes_perception_first": False,
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
            "r8": "PERCEPTION_POLICY_DISCOVERY",
            "r6": "PERCEPTION_POLICY_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_perception_first": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_outcome_label_used": False,
        "present_market_perception_primary": True,
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_perception_first": payload["passes_perception_first"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
