"""Shared Core V2 cross-market decision-intelligence falsification on VT31.

Uses the already GREEN VT31 source-only 5Y trade artifact plus the governed CIBO
daily path ledger. For the current VT31 trade, cross-market features are built
strictly as-of signal_at. Only a peer first-breach whose timestamp is <= the
VT31 signal may be visible. Post-outcome day regime, departure, objective, MFE,
MAE, exit and realized outcome are forbidden current-decision features.

Temporal protocol:
- R8 trade outcomes = discovery memory.
- R6 = calibration and policy freeze.
- R5 = no-retune evaluation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

SCHEMA = "qore.core_stack_v2.vt31.shared_cross_market_v2"
IDENTITY = "VT31_NAS100_SHARED_CROSS_MARKET_V2"
MARKETS = ("NAS100", "SP500", "US30")

LOCAL_FEATURES = (
    "side",
    "entry_family",
    "raid_minute_bucket",
    "confirmation_minute_bucket",
    "decision_minute_bucket",
    "raid_depth_ref_bucket",
    "risk_ref_bucket",
    "planned_target_r_bucket",
    "entry_location_ref_bucket",
    "candidate_combo",
)
CROSS_FEATURES = (
    "peer_consensus",
    "peer_breached_count",
    "peer_expected_raid_count",
    "peer_opposite_raid_count",
    "sp500_breach_asof",
    "us30_breach_asof",
    "first_peer_leader",
    "first_peer_lead_bucket",
)
FULL_FEATURES = LOCAL_FEATURES + CROSS_FEATURES

INTERACTIONS = (
    ("side", "entry_family"),
    ("side", "peer_consensus"),
    ("entry_family", "peer_consensus"),
    ("risk_ref_bucket", "peer_consensus"),
    ("planned_target_r_bucket", "peer_consensus"),
    ("entry_family", "sp500_breach_asof"),
    ("entry_family", "us30_breach_asof"),
    ("peer_expected_raid_count", "peer_opposite_raid_count"),
)

FORBIDDEN = (
    "net_r_after_friction",
    "r_multiple",
    "loss_path_class",
    "mfe_r",
    "mae_r",
    "exit_reason",
    "exit_at",
    "filled_at",
    "day_regime",
    "both_sides_by_11",
    "both_sides_by_16",
    "opposite_boundary_hit_by_16",
)


@dataclass(frozen=True, slots=True)
class Policy:
    profile: str
    shrinkage: int
    threshold: Decimal
    minimum_groups: int

    @property
    def features(self) -> tuple[str, ...]:
        if self.profile == "CROSS":
            return CROSS_FEATURES
        if self.profile == "LOCAL_PLUS_CROSS":
            return FULL_FEATURES
        raise ValueError("unknown profile")

    def payload(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "features": self.features,
            "shrinkage": self.shrinkage,
            "threshold": str(self.threshold),
            "minimum_groups": self.minimum_groups,
        }


POLICIES = tuple(
    Policy(profile, shrinkage, threshold, groups)
    for profile in ("CROSS", "LOCAL_PLUS_CROSS")
    for shrinkage in (8, 16, 32)
    for threshold in (
        Decimal("-0.10"),
        Decimal("-0.05"),
        Decimal("0"),
        Decimal("0.05"),
        Decimal("0.10"),
    )
    for groups in (3, 5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _bucket_minutes(value: int | None) -> str:
    if value is None:
        return "none"
    if value < 0:
        return "future_forbidden"
    if value <= 2:
        return "0_2m"
    if value <= 5:
        return "3_5m"
    if value <= 10:
        return "6_10m"
    if value <= 20:
        return "11_20m"
    return "gt_20m"


def _load_rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text())
    rows = cast(list[dict[str, object]], payload["trades"])
    return sorted(rows, key=lambda row: cast(str, row["signal_at"]))


def _load_daily(path: Path) -> dict[str, dict[str, dict[str, object]]]:
    result: dict[str, dict[str, dict[str, object]]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = cast(dict[str, object], json.loads(line))
        market = str(row.get("market"))
        if market not in MARKETS:
            continue
        day = str(row["ny_date"])
        result.setdefault(day, {})[market] = row
    return result


def _breach_asof(day: dict[str, dict[str, object]], market: str, signal: datetime) -> tuple[str, datetime | None]:
    row = day.get(market)
    if row is None:
        return "missing", None
    raw = row.get("first_breach_at")
    side = str(row.get("first_breach", "none"))
    if raw is None or side == "none":
        return "none", None
    at = _dt(raw)
    if at > signal:
        return "none", None
    return side, at


def _decorate(
    rows: list[dict[str, object]],
    daily: dict[str, dict[str, dict[str, object]]],
) -> list[dict[str, object]]:
    decorated: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        for forbidden in FORBIDDEN:
            if forbidden in CROSS_FEATURES:
                raise AssertionError(f"forbidden cross-market feature: {forbidden}")
        signal = _dt(row["signal_at"])
        day = daily.get(str(row["local_date"]), {})
        expected_raid = "low" if str(row["side"]) == "long" else "high"

        peers: list[tuple[str, str, datetime | None]] = []
        for market in ("SP500", "US30"):
            side, at = _breach_asof(day, market, signal)
            peers.append((market, side, at))
            row[f"{market.lower()}_breach_asof"] = side

        breached = [(m, s, at) for m, s, at in peers if at is not None]
        expected = sum(1 for _, side, _ in breached if side == expected_raid)
        opposite = sum(
            1
            for _, side, _ in breached
            if side in ("high", "low") and side != expected_raid
        )

        if expected == 2:
            consensus = "BOTH_CONFIRM_EXPECTED_RAID"
        elif expected == 1 and opposite == 0:
            consensus = "ONE_CONFIRMS_EXPECTED_RAID"
        elif expected == 0 and opposite == 0:
            consensus = "NO_PEER_BREACH_YET"
        elif expected > 0 and opposite > 0:
            consensus = "PEER_DIVERGENCE"
        elif opposite == 2:
            consensus = "BOTH_OPPOSE_EXPECTED_RAID"
        else:
            consensus = "ONE_OPPOSES_EXPECTED_RAID"

        if breached:
            leader_market, _, leader_at = min(
                breached,
                key=lambda item: cast(datetime, item[2]),
            )
            assert leader_at is not None
            lead_minutes = int((signal - leader_at).total_seconds() // 60)
        else:
            leader_market = "none"
            lead_minutes = None

        row["peer_consensus"] = consensus
        row["peer_breached_count"] = str(len(breached))
        row["peer_expected_raid_count"] = str(expected)
        row["peer_opposite_raid_count"] = str(opposite)
        row["first_peer_leader"] = leader_market
        row["first_peer_lead_bucket"] = _bucket_minutes(lead_minutes)
        decorated.append(row)
    return decorated


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    if not values:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "profit_factor": None,
            "total_r": "0",
            "mean_r": "0",
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    gains = sum((v for v in values if v > 0), Decimal(0))
    losses = -sum((v for v in values if v < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = peak = max_dd = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "profit_factor": None if losses == 0 else format(gains / losses, "f"),
        "total_r": format(total, "f"),
        "mean_r": format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_streak,
    }


def _posterior(
    history: list[dict[str, object]],
    current: dict[str, object],
    fields: tuple[str, ...],
    global_mean: Decimal,
    shrinkage: int,
) -> tuple[Decimal, int] | None:
    key = tuple(str(current.get(field)) for field in fields)
    selected = [
        row
        for row in history
        if tuple(str(row.get(field)) for field in fields) == key
    ]
    if len(selected) < 4:
        return None
    total = sum((_d(row["net_r_after_friction"]) for row in selected), Decimal(0))
    n = Decimal(len(selected))
    alpha = Decimal(shrinkage)
    return (total + alpha * global_mean) / (n + alpha), len(selected)


def _score(
    history: list[dict[str, object]],
    current: dict[str, object],
    policy: Policy,
) -> tuple[Decimal | None, int]:
    if len(history) < 80:
        return None, 0
    global_mean = sum(
        (_d(row["net_r_after_friction"]) for row in history), Decimal(0)
    ) / Decimal(len(history))
    estimates: list[tuple[Decimal, Decimal]] = []
    for field in policy.features:
        item = _posterior(
            history,
            current,
            (field,),
            global_mean,
            policy.shrinkage,
        )
        if item is not None:
            estimate, n = item
            estimates.append((estimate, Decimal(n).sqrt()))
    for fields in INTERACTIONS:
        if any(field not in policy.features for field in fields):
            continue
        item = _posterior(
            history,
            current,
            fields,
            global_mean,
            policy.shrinkage,
        )
        if item is not None:
            estimate, n = item
            estimates.append((estimate, Decimal(n).sqrt() * Decimal("1.5")))
    if len(estimates) < policy.minimum_groups:
        return None, len(estimates)
    weight = sum((weight for _, weight in estimates), Decimal(0))
    score = sum(
        (estimate * weight for estimate, weight in estimates),
        Decimal(0),
    ) / weight
    return score, len(estimates)


def _apply(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    kept: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    for source in rows:
        score, groups = _score(history, source, policy)
        row = dict(source)
        row["shared_cross_score_r"] = None if score is None else format(score, "f")
        row["shared_cross_evidence_groups"] = groups
        if score is not None and score < policy.threshold:
            row["shared_cross_action"] = "ABSTAIN_SHADOW"
            abstained.append(row)
        else:
            row["shared_cross_action"] = "PASS"
            kept.append(row)
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    baseline_losses = sum(_d(row["net_r_after_friction"]) < 0 for row in rows)
    baseline_wins = sum(_d(row["net_r_after_friction"]) > 0 for row in rows)
    return {
        "metrics": _metrics(kept),
        "input": len(rows),
        "kept": len(kept),
        "abstained": len(abstained),
        "losses_avoided": losses_avoided,
        "winners_sacrificed": winners_sacrificed,
        "loss_rejection_recall": (
            "0"
            if baseline_losses == 0
            else format(Decimal(losses_avoided) / Decimal(baseline_losses), "f")
        ),
        "winner_retention": (
            "0"
            if baseline_wins == 0
            else format(
                Decimal(baseline_wins - winners_sacrificed) / Decimal(baseline_wins),
                "f",
            )
        ),
        "density_retained": (
            "0" if not rows else format(Decimal(len(kept)) / Decimal(len(rows)), "f")
        ),
    }


def _calibration_score(
    baseline: dict[str, object],
    candidate: dict[str, object],
) -> Decimal | None:
    metrics = cast(dict[str, object], candidate["metrics"])
    if baseline["profit_factor"] is None or metrics["profit_factor"] is None:
        return None
    bpf = _d(cast(object, baseline["profit_factor"]))
    cpf = _d(cast(object, metrics["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    cdd = _d(metrics["max_drawdown_r"])
    density = _d(candidate["density_retained"])
    winner_retention = _d(candidate["winner_retention"])
    recall = _d(candidate["loss_rejection_recall"])
    if density < Decimal("0.55") or density > Decimal("0.92"):
        return None
    if winner_retention < Decimal("0.75"):
        return None
    if recall < Decimal("0.15"):
        return None
    if cpf < bpf * Decimal("1.15"):
        return None
    if cdd > bdd * Decimal("0.90"):
        return None
    return (
        (cpf / bpf)
        * (bdd / max(cdd, Decimal("0.000001")))
        * winner_retention
        * (Decimal(1) + recall)
    )


def run(r8: Path, r6: Path, r5: Path, daily_path: Path) -> dict[str, object]:
    daily = _load_daily(daily_path)
    r8_rows = _decorate(_load_rows(r8), daily)
    r6_rows = _decorate(_load_rows(r6), daily)
    r5_rows = _decorate(_load_rows(r5), daily)

    all_rows = r8_rows + r6_rows + r5_rows
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 711-loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 111-winner binding drift")

    calibration_baseline = _metrics(r6_rows)
    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        candidate = _apply(r8_rows, r6_rows, policy)
        score = _calibration_score(calibration_baseline, candidate)
        frontier.append({
            "policy": policy.payload(),
            "candidate": candidate,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "selection_status": "NO_CROSS_MARKET_CALIBRATION_SURVIVOR",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "r6_baseline": calibration_baseline,
            "frontier": frontier,
            "frozen_policy": None,
            "r5_evaluation": None,
            "passes_cross_market_mission1": False,
            "governance": {
                "methodology_modified": False,
                "post_outcome_cross_market_features_used": False,
                "current_trade_outcome_used": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _apply(r8_rows + r6_rows, r5_rows, frozen)
    r5_baseline = _metrics(r5_rows)
    e_metrics = cast(dict[str, object], evaluation["metrics"])
    bpf = _d(cast(object, r5_baseline["profit_factor"]))
    epf = _d(cast(object, e_metrics["profit_factor"]))
    bdd = _d(r5_baseline["max_drawdown_r"])
    gates = {
        "pf_improvement_at_least_20pct": epf >= bpf * Decimal("1.20"),
        "dd_reduction_at_least_25pct": (
            _d(e_metrics["max_drawdown_r"]) <= bdd * Decimal("0.75")
        ),
        "loss_rejection_recall_at_least_20pct": (
            _d(evaluation["loss_rejection_recall"]) >= Decimal("0.20")
        ),
        "winner_retention_at_least_75pct": (
            _d(evaluation["winner_retention"]) >= Decimal("0.75")
        ),
        "density_at_least_55pct": (
            _d(evaluation["density_retained"]) >= Decimal("0.55")
        ),
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "selection_status": "CROSS_MARKET_POLICY_FROZEN_ON_R6",
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "DISCOVERY_MEMORY",
            "r6": "CALIBRATION_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "r5_baseline": r5_baseline,
        "r5_evaluation": evaluation,
        "gates": gates,
        "passes_cross_market_mission1": all(gates.values()),
        "governance": {
            "methodology_modified": False,
            "post_outcome_cross_market_features_used": False,
            "current_trade_outcome_used": False,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
        "frontier": frontier,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", type=Path, required=True)
    parser.add_argument("--r6", type=Path, required=True)
    parser.add_argument("--r5", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.r8, args.r6, args.r5, args.daily_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "selection_status": payload["selection_status"],
        "frozen_policy": payload["frozen_policy"],
        "r5_evaluation": payload["r5_evaluation"],
        "passes_cross_market_mission1": payload["passes_cross_market_mission1"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
