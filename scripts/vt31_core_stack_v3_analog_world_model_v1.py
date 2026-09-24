"""Shared Core V3 analog/world-model falsification on VT31 source-only NAS100.

This laboratory upgrades Shared from bucket posterior filters to causal episodic
reasoning:
- historical analog memory of closed episodes only;
- prior-day / rolling regime transition context;
- contemporaneous cross-index observations available by signal time;
- explicit uncertainty via analog confidence and effective sample;
- failure-memory proxy via analog loss concentration.

Temporal protocol is immutable:
R8 = discovery/history only.
R6 = calibration and one policy freeze.
R5 = no-retune evaluation.

The current trade's outcome, MFE/MAE, exit reason, loss class and future day
state are forbidden decision inputs.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.core_stack_v2.analog_memory import (
    AnalogQuery,
    CausalAnalogMemory,
    ClosedEpisode,
)

SCHEMA = "qore.core_stack_v3.vt31.analog_world_model.v1"
IDENTITY = "VT31_NAS100_SHARED_ANALOG_WORLD_MODEL_V3"
MARKETS = ("NAS100", "SP500", "US30")

FORBIDDEN_CURRENT = (
    "net_r_after_friction",
    "r_multiple",
    "loss_path_class",
    "mfe_r",
    "mae_r",
    "exit_reason",
    "exit_at",
    "filled_at",
    "fill_delay_minutes",
    "fill_delay_bucket",
    "pre_loss_streak_bucket",
)

LOCAL_FIELDS = (
    "side",
    "entry_family",
    "raid_minute",
    "confirmation_minute",
    "decision_minute",
    "raid_to_confirmation_minutes",
    "confirmation_to_decision_minutes",
    "raid_depth_ref",
    "risk_ref",
    "planned_target_r_native",
    "entry_location_ref",
    "zone_width_ref",
    "extreme_body_fraction",
    "reference_width_pct_mid",
    "candidate_count",
    "candidate_combo",
)

REGIME_FIELDS = LOCAL_FIELDS + (
    "prior_nas100_regime",
    "prior_nas100_first_breach",
    "prior_nas100_objective_hit",
    "prior_nas100_reference_width",
    "prior3_reversal_rate",
    "prior3_objective_rate",
    "prior3_same_breach_rate",
)

GLOBAL_FIELDS = REGIME_FIELDS + (
    "prior_sp500_regime",
    "prior_us30_regime",
    "prior_peer_direction_state",
    "sp500_breach_asof",
    "us30_breach_asof",
    "peer_consensus",
)


@dataclass(frozen=True, slots=True)
class Policy:
    profile: str
    maximum_analogs: int
    minimum_similarity_bps: int
    conflict_mean_r: Decimal
    conflict_loss_rate: Decimal
    minimum_confidence_bps: int
    caution_multiplier: Decimal

    @property
    def fields(self) -> tuple[str, ...]:
        if self.profile == "LOCAL":
            return LOCAL_FIELDS
        if self.profile == "REGIME":
            return REGIME_FIELDS
        if self.profile == "GLOBAL":
            return GLOBAL_FIELDS
        raise ValueError("unknown profile")

    def payload(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "fields": self.fields,
            "maximum_analogs": self.maximum_analogs,
            "minimum_similarity_bps": self.minimum_similarity_bps,
            "conflict_mean_r": format(self.conflict_mean_r, "f"),
            "conflict_loss_rate": format(self.conflict_loss_rate, "f"),
            "minimum_confidence_bps": self.minimum_confidence_bps,
            "caution_multiplier": format(self.caution_multiplier, "f"),
        }


_MEMORY_CACHE: dict[
    tuple[int, tuple[str, ...]],
    CausalAnalogMemory,
] = {}
_ANALOG_CACHE: dict[
    tuple[int, int, int, str],
    dict[str, object],
] = {}

POLICIES = tuple(
    Policy(
        profile,
        maximum,
        similarity,
        mean_threshold,
        loss_rate,
        confidence,
        caution,
    )
    for profile in ("LOCAL", "REGIME", "GLOBAL")
    for maximum in (16, 32, 48)
    for similarity in (4500, 5500)
    for mean_threshold in (Decimal("0"), Decimal("0.05"), Decimal("0.10"))
    for loss_rate in (Decimal("0.82"), Decimal("0.86"), Decimal("0.90"))
    for confidence in (2500, 4000)
    for caution in (Decimal("0.25"), Decimal("0.50"))
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_trades(path: Path) -> list[dict[str, object]]:
    payload = cast(dict[str, object], json.loads(path.read_text()))
    rows = cast(list[dict[str, object]], payload["trades"])
    return sorted(rows, key=lambda row: cast(str, row["signal_at"]))


def _load_daily(path: Path) -> dict[str, dict[str, dict[str, object]]]:
    result: dict[str, dict[str, dict[str, object]]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = cast(dict[str, object], json.loads(line))
        market = str(row["market"])
        if market not in MARKETS:
            continue
        result.setdefault(str(row["ny_date"]), {})[market] = row
    return result


def _previous_dates(
    daily: dict[str, dict[str, dict[str, object]]],
    current: str,
    count: int,
) -> list[str]:
    available = sorted(
        key
        for key, by_market in daily.items()
        if key < current and "NAS100" in by_market
    )
    return available[-count:]


def _safe_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except Exception:
        return None
    return result if result.is_finite() else None


def _rate(flags: list[bool]) -> str:
    if not flags:
        return "unavailable"
    return format(
        Decimal(sum(flags)) / Decimal(len(flags)),
        "f",
    )


def _same_breach_rate(rows: list[dict[str, object]]) -> str:
    sides = [
        str(row.get("first_breach"))
        for row in rows
        if str(row.get("first_breach")) in {"high", "low"}
    ]
    if not sides:
        return "unavailable"
    latest = sides[-1]
    return format(
        Decimal(sum(side == latest for side in sides)) / Decimal(len(sides)),
        "f",
    )


def _breach_asof(
    daily: dict[str, dict[str, dict[str, object]]],
    day: str,
    market: str,
    signal: datetime,
) -> str:
    row = daily.get(day, {}).get(market)
    if row is None:
        return "missing"
    raw = row.get("first_breach_at")
    side = str(row.get("first_breach", "none"))
    if raw is None or side not in {"high", "low"}:
        return "none"
    return side if _dt(raw) <= signal else "none"


def _decorate(
    rows: list[dict[str, object]],
    daily: dict[str, dict[str, dict[str, object]]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        current = str(row["local_date"])
        previous = _previous_dates(daily, current, 3)
        prior = previous[-1] if previous else None
        nas_history = [
            daily[day]["NAS100"]
            for day in previous
            if "NAS100" in daily.get(day, {})
        ]

        if prior is None:
            prior_nas = {}
            prior_sp = {}
            prior_us = {}
        else:
            prior_nas = daily.get(prior, {}).get("NAS100", {})
            prior_sp = daily.get(prior, {}).get("SP500", {})
            prior_us = daily.get(prior, {}).get("US30", {})

        row["prior_nas100_regime"] = str(
            prior_nas.get("day_regime", "unavailable")
        )
        row["prior_nas100_first_breach"] = str(
            prior_nas.get("first_breach", "unavailable")
        )
        row["prior_nas100_objective_hit"] = str(
            prior_nas.get("opposite_boundary_hit_by_16", "unavailable")
        )
        row["prior_nas100_reference_width"] = str(
            prior_nas.get("reference_width", "unavailable")
        )
        row["prior3_reversal_rate"] = _rate(
            [
                str(item.get("day_regime")) == "reversal-completion"
                for item in nas_history
            ]
        )
        row["prior3_objective_rate"] = _rate(
            [
                bool(item.get("opposite_boundary_hit_by_16"))
                for item in nas_history
            ]
        )
        row["prior3_same_breach_rate"] = _same_breach_rate(nas_history)
        row["prior_sp500_regime"] = str(
            prior_sp.get("day_regime", "unavailable")
        )
        row["prior_us30_regime"] = str(
            prior_us.get("day_regime", "unavailable")
        )

        peer_dirs = [
            str(prior_sp.get("first_breach", "none")),
            str(prior_us.get("first_breach", "none")),
        ]
        directional = [item for item in peer_dirs if item in {"high", "low"}]
        if len(directional) == 2 and len(set(directional)) == 1:
            prior_peer_state = f"unanimous-{directional[0]}"
        elif len(directional) == 2:
            prior_peer_state = "divergent"
        else:
            prior_peer_state = "incomplete"
        row["prior_peer_direction_state"] = prior_peer_state

        signal = _dt(row["signal_at"])
        sp = _breach_asof(daily, current, "SP500", signal)
        us = _breach_asof(daily, current, "US30", signal)
        row["sp500_breach_asof"] = sp
        row["us30_breach_asof"] = us
        expected = "low" if str(row["side"]) == "long" else "high"
        if sp == expected and us == expected:
            consensus = "both-confirm"
        elif expected in {sp, us} and "none" in {sp, us}:
            consensus = "one-confirm"
        elif sp in {"high", "low"} and us in {"high", "low"} and sp != us:
            consensus = "divergent"
        elif (
            sp in {"high", "low"}
            and us in {"high", "low"}
            and sp == us
            and sp != expected
        ):
            consensus = "both-oppose"
        else:
            consensus = "incomplete"
        row["peer_consensus"] = consensus
        output.append(row)
    return output


def _signature(
    row: dict[str, object],
    fields: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    for forbidden in FORBIDDEN_CURRENT:
        if forbidden in fields:
            raise AssertionError(f"forbidden current feature: {forbidden}")
    values: list[tuple[str, str]] = []
    for field in fields:
        value = row.get(field)
        if value is None:
            values.append((field, "unavailable"))
        else:
            values.append((field, str(value)))
    return tuple(sorted(values))


def _episode(
    row: dict[str, object],
    fields: tuple[str, ...],
) -> ClosedEpisode:
    return ClosedEpisode(
        episode_id=(
            f"{row['partition']}:{row['local_date']}:{row['signal_at']}"
        ),
        market="NAS100",
        closed_at=_dt(row["exit_at"]),
        signature=_signature(row, fields),
        terminal_r=_d(row["net_r_after_friction"]),
    )


def _memory(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> CausalAnalogMemory:
    cache_key = (id(rows), fields)
    cached = _MEMORY_CACHE.get(cache_key)
    if cached is not None:
        return cached
    weights = {
        "side": Decimal("2"),
        "entry_family": Decimal("2"),
        "risk_ref": Decimal("1.5"),
        "raid_depth_ref": Decimal("1.5"),
        "planned_target_r_native": Decimal("1.5"),
        "peer_consensus": Decimal("2"),
        "prior_nas100_regime": Decimal("1.5"),
        "prior_peer_direction_state": Decimal("1.25"),
    }
    memory = CausalAnalogMemory(
        tuple(_episode(row, fields) for row in rows),
        feature_weights=weights,
    )
    _MEMORY_CACHE[cache_key] = memory
    return memory


def _analog_view(
    memory: CausalAnalogMemory,
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    cache_key = (
        id(memory),
        policy.maximum_analogs,
        policy.minimum_similarity_bps,
        cast(str, row["signal_at"]),
    )
    cached = _ANALOG_CACHE.get(cache_key)
    if cached is not None:
        return cached
    summary = memory.query(
        AnalogQuery(
            market="NAS100",
            as_of=_dt(row["signal_at"]),
            signature=_signature(row, policy.fields),
            maximum_analogs=policy.maximum_analogs,
            minimum_similarity_bps=policy.minimum_similarity_bps,
        )
    )
    view = {
        "weighted_mean_r": summary.weighted_mean_r,
        "weighted_loss_rate": summary.weighted_loss_rate,
        "effective_sample_size": view["effective_sample_size"],
        "confidence_bps": view["confidence_bps"],
        "analog_count": view["analog_count"],
    }
    _ANALOG_CACHE[cache_key] = view
    return view


def _query(
    memory: CausalAnalogMemory,
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    view = _analog_view(memory, row, policy)
    mean_raw = view["weighted_mean_r"]
    loss_raw = view["weighted_loss_rate"]
    mean = None if mean_raw is None else _d(mean_raw)
    loss_rate = None if loss_raw is None else _d(loss_raw)
    effective_n = _d(view["effective_sample_size"])
    sufficient = (
        mean is not None
        and loss_rate is not None
        and int(view["confidence_bps"]) >= policy.minimum_confidence_bps
        and effective_n >= Decimal("6")
    )

    if not sufficient:
        disposition = "INSUFFICIENT"
    elif (
        mean < policy.conflict_mean_r
        and loss_rate >= policy.conflict_loss_rate
    ):
        disposition = "CONFLICT"
    elif mean < Decimal("0.10") or loss_rate >= Decimal("0.82"):
        disposition = "CAUTION"
    elif mean >= Decimal("0.25") and loss_rate <= Decimal("0.75"):
        disposition = "FAVORABLE"
    else:
        disposition = "NEUTRAL"

    return {
        "disposition": disposition,
        "weighted_mean_r": (
            None if mean is None else format(mean, "f")
        ),
        "weighted_loss_rate": (
            None if loss_rate is None else format(loss_rate, "f")
        ),
        "effective_sample_size": summary.effective_sample_size,
        "confidence_bps": summary.confidence_bps,
        "analog_count": len(summary.analogs),
    }


def _metrics_values(values: list[Decimal]) -> dict[str, object]:
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
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "profit_factor": (
            None if losses == 0 else format(gains / losses, "f")
        ),
        "total_r": format(total, "f"),
        "mean_r": format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _metrics(
    rows: list[dict[str, object]],
    field: str = "net_r_after_friction",
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda item: cast(str, item["signal_at"]))
    return _metrics_values([_d(row[field]) for row in ordered])


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    memory = _memory(history, policy.fields)
    kept: list[dict[str, object]] = []
    weighted: list[dict[str, object]] = []
    combined: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    dispositions: dict[str, int] = {}

    for source in rows:
        row = dict(source)
        view = _query(memory, row, policy)
        disposition = str(view["disposition"])
        dispositions[disposition] = dispositions.get(disposition, 0) + 1
        row["shared_v3"] = view
        raw = _d(row["net_r_after_friction"])

        if disposition == "CONFLICT":
            multiplier = Decimal("0.25")
            abstained.append(row)
        elif disposition == "CAUTION":
            multiplier = policy.caution_multiplier
            kept.append(row)
        elif disposition == "NEUTRAL":
            multiplier = Decimal("0.75")
            kept.append(row)
        else:
            multiplier = Decimal("1")
            kept.append(row)

        weighted_row = dict(row)
        weighted_row["shared_weighted_r"] = format(raw * multiplier, "f")
        weighted.append(weighted_row)
        if disposition != "CONFLICT":
            combined.append(weighted_row)

    baseline = _metrics(rows)
    mission1 = _metrics(kept)
    mission2 = _metrics(weighted, "shared_weighted_r")
    combined_metrics = _metrics(combined, "shared_weighted_r")

    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0
        for row in abstained
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0
        for row in abstained
    )
    return {
        "baseline": baseline,
        "disposition_counts": dict(sorted(dispositions.items())),
        "mission_1": {
            "metrics": mission1,
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
            "winner_retention": (
                "0"
                if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed)
                    / Decimal(baseline_wins),
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(
                    Decimal(len(kept)) / Decimal(len(rows)),
                    "f",
                )
            ),
        },
        "mission_2": {
            "metrics": mission2,
            "trade_count_preserved": len(weighted) == len(rows),
        },
        "combined": {
            "metrics": combined_metrics,
            "trade_count": len(combined),
        },
    }


def _ratio(new: object, old: object) -> Decimal:
    return _d(new) / _d(old)


def _calibration_score(result: dict[str, object]) -> Decimal | None:
    baseline = cast(dict[str, object], result["baseline"])
    mission1 = cast(dict[str, object], result["mission_1"])
    mission2 = cast(dict[str, object], result["mission_2"])
    m1 = cast(dict[str, object], mission1["metrics"])
    m2 = cast(dict[str, object], mission2["metrics"])
    if (
        baseline["profit_factor"] is None
        or m1["profit_factor"] is None
        or m2["profit_factor"] is None
    ):
        return None

    bpf = _d(cast(object, baseline["profit_factor"]))
    m1pf = _d(cast(object, m1["profit_factor"]))
    m2pf = _d(cast(object, m2["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    m1dd = _d(m1["max_drawdown_r"])
    m2dd = _d(m2["max_drawdown_r"])

    if _d(mission1["density_retained"]) < Decimal("0.55"):
        return None
    if _d(mission1["winner_retention"]) < Decimal("0.75"):
        return None
    if _d(mission1["loss_rejection_recall"]) < Decimal("0.20"):
        return None
    if m1pf < bpf * Decimal("1.15"):
        return None
    if m1dd > bdd * Decimal("0.80"):
        return None
    if m2pf < bpf * Decimal("1.15"):
        return None
    if m2dd > bdd:
        return None
    return (
        (m1pf / bpf)
        * (m2pf / bpf)
        * (bdd / max(m1dd, Decimal("0.000001")))
        * _d(mission1["winner_retention"])
    )


def _final_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    mission1 = cast(dict[str, object], result["mission_1"])
    mission2 = cast(dict[str, object], result["mission_2"])
    combined = cast(dict[str, object], result["combined"])
    m1 = cast(dict[str, object], mission1["metrics"])
    m2 = cast(dict[str, object], mission2["metrics"])
    combo = cast(dict[str, object], combined["metrics"])

    bpf = _d(cast(object, baseline["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    m1pf = _d(cast(object, m1["profit_factor"]))
    m2pf = _d(cast(object, m2["profit_factor"]))
    cpf = _d(cast(object, combo["profit_factor"]))
    return {
        "mission1_pf_plus_25pct": m1pf >= bpf * Decimal("1.25"),
        "mission1_dd_minus_30pct": (
            _d(m1["max_drawdown_r"]) <= bdd * Decimal("0.70")
        ),
        "mission1_loss_recall_at_least_25pct": (
            _d(mission1["loss_rejection_recall"]) >= Decimal("0.25")
        ),
        "mission1_winner_retention_at_least_80pct": (
            _d(mission1["winner_retention"]) >= Decimal("0.80")
        ),
        "mission1_density_at_least_55pct": (
            _d(mission1["density_retained"]) >= Decimal("0.55")
        ),
        "mission2_pf_plus_25pct": m2pf >= bpf * Decimal("1.25"),
        "mission2_dd_not_worse": _d(m2["max_drawdown_r"]) <= bdd,
        "mission2_trade_count_preserved": bool(
            mission2["trade_count_preserved"]
        ),
        "combined_pf_at_least_1_75": cpf >= Decimal("1.75"),
        "combined_dd_at_most_60pct_baseline": (
            _d(combo["max_drawdown_r"]) <= bdd * Decimal("0.60")
        ),
    }


def run(
    r8: Path,
    r6: Path,
    r5: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = _load_daily(daily_path)
    r8_rows = _decorate(_load_trades(r8), daily)
    r6_rows = _decorate(_load_trades(r6), daily)
    r5_rows = _decorate(_load_trades(r5), daily)
    all_rows = r8_rows + r6_rows + r5_rows

    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 711-loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 111-winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        result = _evaluate(r8_rows, r6_rows, policy)
        score = _calibration_score(result)
        frontier.append(
            {
                "policy": policy.payload(),
                "calibration": result,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {
                "trades": 822,
                "losses": 711,
                "wins": 111,
            },
            "frozen_policy": None,
            "evaluation": None,
            "passes_shared_v3": False,
            "frontier": frontier,
            "governance": {
                "methodology_modified": False,
                "current_outcome_used": False,
                "future_day_state_used": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(r8_rows + r6_rows, r5_rows, frozen)
    gates = _final_gates(evaluation)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if all(gates.values())
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {
            "trades": 822,
            "losses": 711,
            "wins": 111,
        },
        "temporal_protocol": {
            "r8": "DISCOVERY_CLOSED_EPISODE_MEMORY",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_v3": all(gates.values()),
        "frontier": frontier,
        "governance": {
            "methodology_modified": False,
            "current_outcome_used": False,
            "future_day_state_used": False,
            "historical_closed_outcomes_allowed": True,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload.get("gates"),
                "passes_shared_v3": payload["passes_shared_v3"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
