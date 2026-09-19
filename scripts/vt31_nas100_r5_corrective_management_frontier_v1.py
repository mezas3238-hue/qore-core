"""Corrective management frontier for VT31_NAS100 after R5 holdout rejection.

Consumed-evidence development only.

The rejected final holdout showed that density survived but SECONDARY/SCOUT
and REARM management lost expectancy. This lab keeps entry authorization,
source selection, structural stops, ACTIVITY_L rearm budgeting, and the global
0.60 risk scalar unchanged. It changes only post-fill management for non-CORE
positions using the already causal partial-runner simulator:

- ALT_P100: SECONDARY/SCOUT take 50% at +1.00R, runner BE next bar.
- ALT_P125: SECONDARY/SCOUT take 50% at +1.25R, runner BE next bar.
- REARM_SCORE: existing SCORE_PROTECT management.
- REARM_P100/P125: same causal partial-runner management for rearm.

No terminal outcome, fold identity, or date label authorizes a trade.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_density_v2 as hybrid
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_causal_hybrid_replay_v1 as v1
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier
import vt31_nas100_structural_rearm_quality_frontier_v1 as quality

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.r5.corrective_management_frontier.v1"
MARKET = "NAS100"
WAIT_RELEASE_MINUTE = 10 * 60 + 25
MONTHLY_ALT_BUDGET = Decimal("0.60")
GLOBAL_SCALAR = Decimal("0.60")
ACTIVITY_L = {
    "sparse_max": 8,
    "balanced_max": 10,
    "sparse_budget": Decimal("0.30"),
    "balanced_budget": Decimal("0.17"),
    "dense_budget": Decimal("0.04"),
}
REARM_RISK_MAP = engine.RISK_PROFILES["REARM_CONSERVATIVE"]
VARIANTS = {
    "ALT_P050_REARM_SCORE": (Decimal("0.50"), None),
    "ALT_P075_REARM_SCORE": (Decimal("0.75"), None),
    "ALT_P050_REARM_P050": (Decimal("0.50"), Decimal("0.50")),
    "ALT_P075_REARM_P050": (Decimal("0.75"), Decimal("0.50")),
    "ALT_P050_REARM_P075": (Decimal("0.50"), Decimal("0.75")),
    "ALT_P075_REARM_P075": (Decimal("0.75"), Decimal("0.75")),
    "ALT_P100_REARM_SCORE": (Decimal("1.00"), None),
    "ALT_P125_REARM_SCORE": (Decimal("1.25"), None),
    "ALT_P100_REARM_P100": (Decimal("1.00"), Decimal("1.00")),
    "ALT_P125_REARM_P100": (Decimal("1.25"), Decimal("1.00")),
    "ALT_P100_REARM_P125": (Decimal("1.00"), Decimal("1.25")),
    "ALT_P125_REARM_P125": (Decimal("1.25"), Decimal("1.25")),
}


def _causal_negative_management_state(
    *,
    tier: str,
    family: str,
    state: dict[str, object],
) -> bool:
    """Decision-time contexts negative across all four consumed ALLOC_G windows."""
    risk_ref_raw = state.get("risk_ref")
    risk_ref = None if risk_ref_raw is None else Decimal(str(risk_ref_raw))
    current_path_raw = state.get("current_path_vs_previous")
    current_path = (
        None
        if current_path_raw is None
        else Decimal(str(current_path_raw))
    )
    return bool(
        (
            family == "fair-value-gap"
            and state.get("premarket_state") == "rotation"
        )
        or (
            family == "fair-value-gap"
            and state.get("h1_state") == "bullish"
        )
        or (
            family == "order-block"
            and risk_ref is not None
            and risk_ref < Decimal("0.30")
        )
        or (
            family == "order-block"
            and current_path is not None
            and current_path < Decimal("0.75")
        )
        or (tier == "SECONDARY" and family == "breaker")
    )


def _first_rows(
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[
        date,
        tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    ],
    *,
    evidence: str,
    alt_partial_r: Decimal | None,
    secondary_route_policy: str = "ORIGINAL",
    secondary_be_r: Decimal | None = None,
    secondary_be_scope: str = "NONE",
    secondary_partial_scope: str = "ALL",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    policy = Vt31R22ExecutionPolicy()
    trades: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    budget_ledger: dict[str, dict[str, object]] = {}
    current_month: str | None = None
    alt_budget = Decimal(0)

    for local_day in sorted(by_day):
        month = local_day.isoformat()[:7]
        if month != current_month:
            current_month = month
            alt_budget = MONTHLY_ALT_BUDGET
            budget_ledger[month] = {
                "opening_budget_r": format(alt_budget, "f"),
                "secondary_count": 0,
                "scout_count": 0,
                "remaining_budget_r": format(alt_budget, "f"),
            }

        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(day_bars, evidence_fingerprint=evidence)
        prefix = list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]

        core_selected: Vt31R22ExecutableSetup | None = None
        core_state: dict[str, object] | None = None
        alt_authorized_at: datetime | None = None
        alt_reason: str | None = None
        alt_tier: str | None = None
        alt_risk: Decimal | None = None
        saw_wait = False
        source_invalidated = False

        for bar in session:
            prefix.append(bar)
            closed_at = cast(datetime, getattr(bar, "closed_at"))
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=closed_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if saw_wait and evaluation.both_sides_swept:
                    source_invalidated = True
                    status["core-invalidated-after-wait"] += 1
                    break
                continue

            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                alt_authorized_at = closed_at
                alt_reason = "CORE_SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE"
                alt_tier = "SECONDARY"
                alt_risk = hybrid.SECONDARY_RISK
                break

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            state = specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                session_prefix,
                evaluation.setup,
                executable,
                closed_at,
            )
            action = cast(str, state["action"])
            if action == "WAIT":
                saw_wait = True
                if (
                    specialist.baseline._local_minute(bar)
                    >= WAIT_RELEASE_MINUTE
                ):
                    alt_authorized_at = closed_at
                    alt_reason = "CORE_PERSISTENT_WAIT_625"
                    alt_tier = "SCOUT"
                    alt_risk = hybrid.SCOUT_RISK
                    break
                continue
            if action == "ABSTAIN":
                alt_authorized_at = closed_at
                alt_reason = "CORE_CAUSAL_ABSTAIN"
                alt_tier = "SECONDARY"
                alt_risk = hybrid.SECONDARY_RISK
                break
            if action != "EXECUTE":
                raise ValueError(action)
            core_selected = v1._activation_setup(executable, closed_at)
            core_state = state
            break

        if core_selected is not None and core_state is not None:
            outcome = specialist._simulate_selected_plan(
                day_bars,
                core_selected,
                core_state,
            )
            status[f"core-{outcome['status']}"] += 1
            if outcome.get("status") == "terminal":
                weighted = hybrid._weighted(
                    outcome,
                    tier="CORE",
                    risk=hybrid.CORE_RISK,
                    reason="CORE_EXECUTE",
                )
                weighted.update(
                    {
                        "reference_volatility_state": core_state.get(
                            "reference_volatility_state"
                        ),
                        "current_path_vs_previous": core_state.get(
                            "current_path_vs_previous"
                        ),
                        "h1_state": core_state.get("h1_state"),
                        "h4_state": core_state.get("h4_state"),
                        "prior_day_state": core_state.get("prior_day_state"),
                        "premarket_state": core_state.get("premarket_state"),
                        "cash_open_state": core_state.get("cash_open_state"),
                        "last_structure_event_family": core_state.get(
                            "last_structure_event_family"
                        ),
                        "reference_reclaim_age_minutes": core_state.get(
                            "reference_reclaim_age_minutes"
                        ),
                        "confirmation_latency_minutes": core_state.get(
                            "confirmation_latency_minutes"
                        ),
                        "risk_ref": core_state.get("risk_ref"),
                    }
                )
                trades.append(weighted)
            continue

        if (
            source_invalidated
            or alt_authorized_at is None
            or alt_risk is None
            or alt_tier is None
            or timeline is None
        ):
            continue
        if alt_budget < alt_risk:
            status["alt-monthly-budget-exhausted"] += 1
            continue

        selected, selection_status = v1._select_secondary_after(
            day_bars,
            timeline,
            policy,
            authorization_at=alt_authorized_at,
        )
        status[f"alt-{selection_status}"] += 1
        if selected is None:
            continue

        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at"))
            <= selected.decision_at
        )
        selected_source = timeline.source
        alt_state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            selected_source,
            selected,
            selected.decision_at,
        )

        if alt_tier == "SECONDARY" and secondary_route_policy != "ORIGINAL":
            family = selected.selected_family.value
            breaker_bad_context = (
                family == "breaker"
                and (
                    alt_state.get("h1_state") == "mixed"
                    or alt_state.get("reference_volatility_state") == "expanded"
                    or alt_state.get("last_structure_event_family") == "breaker"
                )
            )
            side = selected.side.value
            exact_stable_negative = (
                family == "breaker"
                or (family == "order-block" and side == "long")
            )
            cash_bullish = alt_state.get("cash_open_state") == "bullish"
            risk_ref_raw = alt_state.get("risk_ref")
            risk_ref_value = (
                None
                if risk_ref_raw is None
                else Decimal(str(risk_ref_raw))
            )
            fvg_premarket_rotation = (
                family == "fair-value-gap"
                and alt_state.get("premarket_state") == "rotation"
            )
            order_block_low_risk_ref = (
                family == "order-block"
                and risk_ref_value is not None
                and risk_ref_value < Decimal("0.30")
            )
            persistent_negative_state = (
                fvg_premarket_rotation or order_block_low_risk_ref
            )
            should_route = (
                breaker_bad_context
                if secondary_route_policy == "RENEW_BREAKER_CONTEXT"
                else cash_bullish
                if secondary_route_policy == "RENEW_CASH_BULLISH"
                else breaker_bad_context or cash_bullish
                if secondary_route_policy in {
                    "RENEW_STABLE_NEGATIVE",
                    "ABSTAIN_STABLE_NEGATIVE",
                }
                else exact_stable_negative
                if secondary_route_policy in {
                    "RENEW_EXACT_STABLE_NEGATIVE",
                    "ABSTAIN_EXACT_STABLE_NEGATIVE",
                }
                else family == "breaker"
                if secondary_route_policy == "RENEW_ALL_SECONDARY_BREAKER"
                else fvg_premarket_rotation
                if secondary_route_policy == "RENEW_FVG_PREMARKET_ROTATION"
                else order_block_low_risk_ref
                if secondary_route_policy == "RENEW_OB_LOW_RISK_REF"
                else persistent_negative_state
                if secondary_route_policy in {
                    "RENEW_CAUSAL_PERSISTENT_NEGATIVE",
                    "ABSTAIN_CAUSAL_PERSISTENT_NEGATIVE",
                }
                else False
            )
            if should_route:
                status[f"route-{secondary_route_policy}"] += 1
                if secondary_route_policy in {
                    "ABSTAIN_STABLE_NEGATIVE",
                    "ABSTAIN_EXACT_STABLE_NEGATIVE",
                    "ABSTAIN_CAUSAL_PERSISTENT_NEGATIVE",
                }:
                    continue
                renewed = frontier._next_executable_after(
                    reference=reference,
                    session=session,
                    after_at=selected.decision_at,
                    evidence=evidence,
                    policy=policy,
                )
                if renewed is None:
                    status["route-no-renewed-event"] += 1
                    continue
                renewed_source, renewed_selected = renewed
                rejected_at = selected.decision_at
                if not (
                    renewed_source.structure.raid_at > rejected_at
                    and renewed_source.structure.confirmation_at > rejected_at
                    and renewed_selected.decision_at > rejected_at
                ):
                    status["route-renewal-invariant-failed"] += 1
                    continue
                selected_source = renewed_source
                selected = renewed_selected
                session_prefix = tuple(
                    bar
                    for bar in session
                    if cast(datetime, getattr(bar, "closed_at"))
                    <= selected.decision_at
                )
                alt_state = specialist._state_snapshot(
                    day_bars,
                    previous_path_range,
                    prior_ref_median,
                    prior_admitted_day_bars,
                    session_prefix,
                    selected_source,
                    selected,
                    selected.decision_at,
                )
                alt_reason = (
                    f"{alt_reason}:NEW_RAID_CONFIRMATION_DECISION"
                )
                status["route-renewed-event-selected"] += 1

        managed_selected = selected
        be_applied = False
        if secondary_be_r is not None:
            family = selected.selected_family.value
            side = selected.side.value
            stable_positive = (
                family == "fair-value-gap"
                and alt_state.get("h1_state") == "mixed"
            )
            stable_negative = (
                family == "breaker"
                or (family == "order-block" and side == "long")
                or alt_state.get("cash_open_state") == "bullish"
            )
            be_applied = (
                secondary_be_scope == "ALL"
                or (
                    secondary_be_scope == "STABLE_NEGATIVE"
                    and stable_negative
                )
                or (
                    secondary_be_scope == "ALL_EXCEPT_STABLE_POSITIVE"
                    and not stable_positive
                )
                or (
                    secondary_be_scope == "SCOUT_OR_STABLE_NEGATIVE"
                    and (alt_tier == "SCOUT" or stable_negative)
                )
            )
            if be_applied:
                entry = selected.entry_price
                risk = selected.initial_risk
                boundary = (
                    entry + risk * secondary_be_r
                    if side == "long"
                    else entry - risk * secondary_be_r
                )
                managed_selected = replace(
                    selected,
                    three_r_price=boundary,
                )

        selected_partial_r = alt_partial_r
        if alt_partial_r is not None and secondary_partial_scope != "ALL":
            if secondary_partial_scope != "CAUSAL_NEGATIVE":
                raise ValueError(
                    f"unsupported secondary_partial_scope={secondary_partial_scope}"
                )
            selected_partial_r = (
                alt_partial_r
                if _causal_negative_management_state(
                    tier=alt_tier,
                    family=selected.selected_family.value,
                    state=alt_state,
                )
                else None
            )
        partial_applied = selected_partial_r is not None

        outcome = (
            specialist.baseline._simulate(day_bars, managed_selected)
            if selected_partial_r is None
            else v2b._simulate_partial_runner(
                day_bars,
                managed_selected,
                selected_partial_r,
            )
        )
        status[f"alt-outcome-{outcome['status']}"] += 1
        if outcome.get("status") != "terminal":
            continue

        alt_budget -= alt_risk
        key = "scout_count" if alt_tier == "SCOUT" else "secondary_count"
        budget_ledger[month][key] = int(budget_ledger[month][key]) + 1
        budget_ledger[month]["remaining_budget_r"] = format(alt_budget, "f")
        weighted = hybrid._weighted(
            outcome,
            tier=alt_tier,
            risk=alt_risk,
            reason=cast(str, alt_reason),
        )
        weighted.update(
            {
                "reference_volatility_state": alt_state.get(
                    "reference_volatility_state"
                ),
                "current_path_vs_previous": alt_state.get(
                    "current_path_vs_previous"
                ),
                "h1_state": alt_state.get("h1_state"),
                "h4_state": alt_state.get("h4_state"),
                "prior_day_state": alt_state.get("prior_day_state"),
                "premarket_state": alt_state.get("premarket_state"),
                "cash_open_state": alt_state.get("cash_open_state"),
                "last_structure_event_family": alt_state.get(
                    "last_structure_event_family"
                ),
                "reference_reclaim_age_minutes": alt_state.get(
                    "reference_reclaim_age_minutes"
                ),
                "confirmation_latency_minutes": alt_state.get(
                    "confirmation_latency_minutes"
                ),
                "risk_ref": alt_state.get("risk_ref"),
                "secondary_be_scope": secondary_be_scope,
                "secondary_be_r": (
                    None
                    if secondary_be_r is None
                    else format(secondary_be_r, "f")
                ),
                "secondary_be_applied": be_applied,
                "secondary_partial_scope": secondary_partial_scope,
                "secondary_partial_r": (
                    None
                    if selected_partial_r is None
                    else format(selected_partial_r, "f")
                ),
                "secondary_partial_applied": partial_applied,
            }
        )
        trades.append(weighted)

    trades.sort(key=lambda row: cast(str, row["signal_at"]))
    return trades, {
        "status_counts": dict(sorted(status.items())),
        "monthly_alt_budget_ledger": budget_ledger,
        "secondary_route_policy": secondary_route_policy,
        "secondary_be_scope": secondary_be_scope,
        "secondary_be_r": (
            None if secondary_be_r is None else format(secondary_be_r, "f")
        ),
        "secondary_partial_scope": secondary_partial_scope,
    }


def _rearm_rows(
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[
        date,
        tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    ],
    first_rows: list[dict[str, object]],
    *,
    evidence: str,
    rearm_partial_r: Decimal | None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    policy = Vt31R22ExecutionPolicy()
    raw_rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    first_by_day = {
        date.fromisoformat(cast(str, row["local_date"])): row
        for row in first_rows
    }

    for local_day, first_row in sorted(first_by_day.items()):
        exit_at = datetime.fromisoformat(cast(str, first_row["exit_at"]))
        if _wall(exit_at) >= (11, 0, 0):
            continue
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue

        selected = frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=exit_at,
            evidence=evidence,
            policy=policy,
        )
        if selected is None:
            continue
        source, setup = selected
        if not structurally_rearmed(
            protected_exit_at_epoch=int(exit_at.timestamp()),
            new_raid_at_epoch=int(source.structure.raid_at.timestamp()),
            new_confirmation_at_epoch=int(
                source.structure.confirmation_at.timestamp()
            ),
            new_decision_at_epoch=int(setup.decision_at.timestamp()),
        ):
            continue

        prev_range, prior_ref, prior_bars = context_by_day[local_day]
        observation_at = setup.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at"))
            <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            prev_range,
            prior_ref,
            prior_bars,
            session_prefix,
            source,
            setup,
            observation_at,
        )
        score, reasons = quality._quality_score(state, setup)
        risk_class = engine._risk_class(score)

        if rearm_partial_r is None:
            outcome = protection._simulate_single_structural_trail(
                day_bars,
                setup,
                required_confirmations=(1 if score < 5 else None),
            )
            mode = "SCORE_PROTECT"
        else:
            outcome = v2b._simulate_partial_runner(
                day_bars,
                setup,
                rearm_partial_r,
            )
            mode = f"PARTIAL_{format(rearm_partial_r, 'f')}R"

        status[f"{mode}:{outcome['status']}"] += 1
        if outcome.get("status") != "terminal":
            continue
        row = dict(outcome)
        row.update(
            {
                "local_date": local_day.isoformat(),
                "rearm_quality_score": score,
                "rearm_quality_reasons": list(reasons),
                "rearm_risk_class": risk_class,
                "first_tier": first_row["tier"],
                "first_exit_reason": first_row.get("exit_reason"),
                "first_requested_risk_r": first_row["requested_risk_r"],
                "entry_family": setup.selected_family.value,
                "side": setup.side.value,
                "reference_volatility_state": state.get(
                    "reference_volatility_state"
                ),
                "current_path_vs_previous": state.get(
                    "current_path_vs_previous"
                ),
                "h1_state": state.get("h1_state"),
                "h4_state": state.get("h4_state"),
                "prior_day_state": state.get("prior_day_state"),
                "premarket_state": state.get("premarket_state"),
                "cash_open_state": state.get("cash_open_state"),
                "last_structure_event_family": state.get(
                    "last_structure_event_family"
                ),
                "reference_reclaim_age_minutes": state.get(
                    "reference_reclaim_age_minutes"
                ),
                "confirmation_latency_minutes": state.get(
                    "confirmation_latency_minutes"
                ),
                "risk_ref": state.get("risk_ref"),
                "used_for_runtime_decision": False,
            }
        )
        raw_rows.append(row)

    weighted, activity_ledger = engine._adaptive_budgeted_rearm_rows(
        raw_rows,
        risk_map=REARM_RISK_MAP,
        first_rows=first_rows,
        profile=ACTIVITY_L,
        mode=(
            "SCORE_PROTECT"
            if rearm_partial_r is None
            else f"PARTIAL_{format(rearm_partial_r, 'f')}R"
        ),
    )
    return weighted, {
        "status_counts": dict(sorted(status.items())),
        "activity_budget_ledger": activity_ledger,
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(evidence_path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("corrective frontier requires NAS100")

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

    variants: dict[str, object] = {}
    for name, (alt_partial_r, rearm_partial_r) in VARIANTS.items():
        first_rows, first_diag = _first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=alt_partial_r,
        )
        rearm_rows, rearm_diag = _rearm_rows(
            by_day,
            context_by_day,
            first_rows,
            evidence=evidence,
            rearm_partial_r=rearm_partial_r,
        )
        combined = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        scaled = engine._scale_capital_rows(
            combined,
            scalar=GLOBAL_SCALAR,
        )
        metrics = engine._capital_metrics(scaled)
        mc = engine._monte_carlo(
            scaled,
            variant=f"CORRECTIVE:{name}:{partition}",
        )
        variants[name] = {
            "trade_count": len(scaled),
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "alt_partial_r": format(alt_partial_r, "f"),
            "rearm_management": (
                "SCORE_PROTECT"
                if rearm_partial_r is None
                else f"PARTIAL_{format(rearm_partial_r, 'f')}R"
            ),
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
            "objectives": {
                "density_300_350": 300 <= len(scaled) <= 350,
                "pf_ge_1_50": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("1.50")
                ),
                "dd_le_6": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("6")
                ),
                "mc_positive_ge_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_le_15": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "variants": variants,
        "governance": {
            "consumed_evidence_only": True,
            "entry_logic_changed": False,
            "authorization_logic_changed": False,
            "structural_stop_changed": False,
            "global_risk_scalar_changed": False,
            "management_only_frontier": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
