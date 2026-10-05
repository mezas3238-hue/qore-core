"""Full-cognition attribution for VT31 NAS100 on consumed evidence.

Research-only diagnostic. It keeps the admitted OCO population unchanged and
evaluates every terminal trade on equal normalized R. No position sizing,
capital weighting, leverage, compounding, provider lot size or partial-volume
assumption is allowed to affect economics.

The goal is to discover which causal VT31 cognition states generalize before
any post-entry policy is promoted.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    assess_full_cognitive_position,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    Nas100ReasoningDecision,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

SCHEMA = "qore.vt31.nas100.full_cognition_attribution.v1"
MARKET = "NAS100"
MIN_SIGNAL_SAMPLE = 10


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _range_state(current_path_ratio: Decimal | None) -> str:
    if current_path_ratio is None:
        return "unavailable"
    if current_path_ratio < Decimal("0.75"):
        return "compressed"
    if current_path_ratio <= Decimal("1.25"):
        return "normal"
    return "expanded"


def _reconstruct_situation(
    *,
    state: dict[str, object],
    selected: object,
    source: object,
    observation_at: datetime,
) -> Nas100SituationModel:
    side = str(getattr(getattr(selected, "side"), "value"))
    entry_family = str(
        getattr(getattr(selected, "selected_family"), "value")
    )
    current_ratio = _opt_d(state["current_path_vs_previous"])
    reclaim_age = cast(int | None, state["reference_reclaim_age_minutes"])
    entry_age = int(cast(int, state["entry_evidence_age_minutes"]))
    decision_local = observation_at.astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York")
    )
    return Nas100SituationModel(
        as_of=observation_at.astimezone(UTC).isoformat(),
        weekday=decision_local.strftime("%A"),
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=int(cast(int, state["decision_minute_ny"])),
        side=side,
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state=str(state["prior_day_state"]),
        h4_state=str(state["h4_state"]),
        h1_state=str(state["h1_state"]),
        premarket_state=str(state["premarket_state"]),
        cash_open_state=str(state["cash_open_state"]),
        position_in_prior_day_range=str(
            state["position_in_prior_day_range"]
        ),
        range_state=_range_state(current_ratio),
        volatility_state=str(state["reference_volatility_state"]),
        current_path_vs_previous=current_ratio,
        reference_width_vs_prior5=_opt_d(
            state["reference_width_vs_prior5"]
        ),
        raid_depth_ref=_opt_d(state["raid_depth_ref"]),
        recent_path_efficiency=_opt_d(
            state["recent_path_efficiency"]
        ),
        recent_overlap_rate=_opt_d(state["recent_overlap_rate"]),
        first_breach_side="high" if side == "short" else "low",
        double_sided_before_decision=False,
        reference_reclaimed=reclaim_age is not None,
        reference_reclaim_age_minutes=reclaim_age,
        last_structure_event_family=str(
            state["last_structure_event_family"]
        ),
        last_structure_event_age_minutes=cast(
            int | None,
            state["last_structure_event_age_minutes"],
        ),
        recent_liquidity_event_count_10m=None,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family=entry_family,
        confirmation_latency_minutes=int(
            cast(int, state["confirmation_latency_minutes"])
        ),
        entry_evidence_freshness=(
            "fresh-0-5m" if entry_age <= 5 else "older-than-5m"
        ),
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=_opt_d(state["risk_ref"]),
        planned_target_r=_opt_d(state["planned_target_r"]),
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=_opt_d(
            state["destination_distance_ref"]
        ),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="RESEARCH_ONLY_UNCALIBRATED",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
    )


def _reconstruct_reasoning(
    state: dict[str, object],
) -> Nas100ReasoningDecision:
    return Nas100ReasoningDecision(
        action=cast(str, state["action"]),
        target_plan=cast(str, state["target_plan"]),
        thesis=str(state["reasoning_thesis"]),
        journey_capacity_state=str(state["journey_capacity_state"]),
        management_context_state=str(state["management_context_state"]),
        supporting_evidence=tuple(
            cast(list[str], state["reasoning_support"])
        ),
        contradictions=tuple(
            cast(list[str], state["reasoning_contradictions"])
        ),
        uncertainty=tuple(
            cast(list[str], state["reasoning_uncertainty"])
        ),
        context_observations=tuple(
            cast(list[str], state["reasoning_context_observations"])
        ),
        strategy_memory_used=tuple(
            cast(list[str], state["strategy_memory_used"])
        ),
        cibo_market_memory_used=tuple(
            cast(list[str], state["cibo_market_memory_used"])
        ),
        trader_experience_memory_used=tuple(
            cast(list[str], state["trader_experience_memory_used"])
        ),
        situation_fingerprint=str(state["situation_fingerprint"]),
        strategy_memory_fingerprint=str(
            state["strategy_memory_fingerprint"]
        ),
        cibo_market_memory_fingerprint=str(
            state["cibo_market_memory_fingerprint"]
        ),
        trader_experience_memory_fingerprint=str(
            state["trader_experience_memory_fingerprint"]
        ),
        memory_fingerprint=str(state["cognitive_memory_fingerprint"]),
    )


def _support_margin_bucket(margin: int) -> str:
    if margin <= -5:
        return "LE_NEG5"
    if margin <= -2:
        return "NEG4_TO_NEG2"
    if margin <= 1:
        return "NEG1_TO_POS1"
    if margin <= 4:
        return "POS2_TO_POS4"
    return "GE_POS5"


def _metrics(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "profit_factor": None,
            "mean_r": None,
            "total_r": "0",
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
            "payoff": None,
            "sequence_sharpe": None,
            "sequence_sortino": None,
        }

    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_win = sum(wins, Decimal(0))
    gross_loss = -sum(losses, Decimal(0))
    total = sum(values, Decimal(0))
    mean = total / Decimal(len(values))

    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    payoff = None
    if wins and losses:
        payoff = (
            gross_win / Decimal(len(wins))
        ) / (
            gross_loss / Decimal(len(losses))
        )

    floats = [float(value) for value in values]
    mean_float = sum(floats) / len(floats)
    variance = sum(
        (value - mean_float) ** 2 for value in floats
    ) / len(floats)
    sigma = math.sqrt(variance)
    downside = math.sqrt(
        sum(min(0.0, value) ** 2 for value in floats) / len(floats)
    )
    scale = math.sqrt(len(floats))

    return {
        "sample": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "profit_factor": (
            None if gross_loss == 0 else format(gross_win / gross_loss, "f")
        ),
        "mean_r": format(mean, "f"),
        "total_r": format(total, "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_streak,
        "payoff": None if payoff is None else format(payoff, "f"),
        "sequence_sharpe": (
            None if sigma == 0 else mean_float / sigma * scale
        ),
        "sequence_sortino": (
            None if downside == 0 else mean_float / downside * scale
        ),
    }


def _group_metrics(
    rows: list[dict[str, object]],
    field: str,
) -> dict[str, object]:
    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(_d(row["normalized_net_r"]))
    return {
        key: _metrics(values)
        for key, values in sorted(grouped.items())
    }


def _signal_metrics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    grouped: dict[str, list[Decimal]] = defaultdict(list)
    blocked_prefixes = (
        "OBSERVE_ONLY:",
        "STRATEGY_MEMORY_USED:",
        "CIBO_MEMORY_USED:",
        "EXPERIENCE_MEMORY_USED:",
    )
    for row in rows:
        for signal in cast(list[str], row["signal_codes"]):
            if signal.startswith(blocked_prefixes):
                continue
            grouped[signal].append(_d(row["normalized_net_r"]))
    return {
        key: _metrics(values)
        for key, values in sorted(grouped.items())
        if len(values) >= MIN_SIGNAL_SAMPLE
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("full cognition attribution requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = oco.Vt31R22ExecutionPolicy()
    status: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
            continue

        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            timeline.source,
            selected,
            observation_at,
        )
        situation = _reconstruct_situation(
            state=state,
            selected=selected,
            source=timeline.source,
            observation_at=observation_at,
        )
        if situation.fingerprint() != state["situation_fingerprint"]:
            raise AssertionError("reconstructed situation fingerprint drift")

        reasoning = _reconstruct_reasoning(state)
        cognition: FullCognitivePositionState = (
            assess_full_cognitive_position(
                situation=situation,
                reasoning=reasoning,
                entry_tier="CORE",
                dol1_acceptance_observed=None,
            )
        )
        outcome = specialist.baseline._simulate(day_bars, selected)
        status[f"outcome-{outcome['status']}"] += 1
        if outcome["status"] != "terminal":
            continue

        gross_r = _d(outcome["r_multiple"])
        normalized_net = gross_r - specialist.FRICTION
        margin = cognition.support_score - cognition.caution_score
        rows.append(
            {
                "local_date": local_day.isoformat(),
                "signal_at": observation_at.astimezone(UTC).isoformat(),
                "side": selected.side.value,
                "entry_family": selected.selected_family.value,
                "reference_volatility_state": state[
                    "reference_volatility_state"
                ],
                "last_structure_event_family": state[
                    "last_structure_event_family"
                ],
                "management_context": cognition.management_context.value,
                "destination_state": cognition.destination_state,
                "support_score": cognition.support_score,
                "caution_score": cognition.caution_score,
                "support_margin": margin,
                "support_margin_bucket": _support_margin_bucket(margin),
                "target_intent": cognition.target_intent.value,
                "cognitive_coverage_ratio": format(
                    cognition.cognitive_coverage_ratio,
                    "f",
                ),
                "signal_codes": list(cognition.signal_codes),
                "normalized_gross_r": format(gross_r, "f"),
                "normalized_net_r": format(normalized_net, "f"),
                "exit_reason": outcome["exit_reason"],
                "mfe_r": outcome["mfe_r"],
                "mae_r": outcome["mae_r"],
            }
        )

    overall = _metrics(
        [_d(row["normalized_net_r"]) for row in rows]
    )
    context_destination = [
        {
            **row,
            "context_x_destination": (
                f"{row['management_context']}|{row['destination_state']}"
            ),
            "family_x_destination": (
                f"{row['entry_family']}|{row['destination_state']}"
            ),
        }
        for row in rows
    ]

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "status_counts": dict(sorted(status.items())),
        "overall_normalized": overall,
        "by_management_context": _group_metrics(
            rows,
            "management_context",
        ),
        "by_destination_state": _group_metrics(
            rows,
            "destination_state",
        ),
        "by_support_margin": _group_metrics(
            rows,
            "support_margin_bucket",
        ),
        "by_entry_family": _group_metrics(
            rows,
            "entry_family",
        ),
        "by_reference_volatility": _group_metrics(
            rows,
            "reference_volatility_state",
        ),
        "by_context_destination": _group_metrics(
            context_destination,
            "context_x_destination",
        ),
        "by_family_destination": _group_metrics(
            context_destination,
            "family_x_destination",
        ),
        "signal_metrics_min_sample_10": _signal_metrics(rows),
        "rows": rows,
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_filtering_by_cognition": False,
            "position_policy_changed": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "absolute_volume_used": False,
            "provider_volume_rule_used": False,
            "terminal_pnl_used_for_runtime_decision": False,
            "future_journey_label_used": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "overall_normalized": payload["overall_normalized"],
                "by_management_context": payload["by_management_context"],
                "by_destination_state": payload["by_destination_state"],
                "by_support_margin": payload["by_support_margin"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
