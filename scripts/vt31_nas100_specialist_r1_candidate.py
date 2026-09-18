"""Frozen-candidate implementation for the intelligent NAS100 VT31 specialist.

The specialist reconstructs its decision state directly from NAS100 M1 evidence.
It does not query CIBO by date.  CIBO Atlas was the consumed historical learning
source used to define the causal state machine; runtime observation is rebuilt
from closed bars.

Research-only candidate.  No holdout is opened by this module.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_r1_candidate as baseline

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    last_causal_structure_event,
)
from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    cibo_market_memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    Nas100ReasoningState,
    reason,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.specialist_r1.replay.v1"
CANDIDATE_ID = "VT31_NAS100_SPECIALIST_R1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
COMPRESSION_THRESHOLD = Decimal("0.75")
LATE_STATE_CUTOFF_MINUTE = 10 * 60 + 30
PARTIAL_TARGET_R = Decimal("1.25")
PARTIAL_FRACTION = Decimal("0.50")
CIBO_EIGHT_LEDGER_RUN_ID = 35175782935
CIBO_EIGHT_LEDGER_ARTIFACT_ID = 10478487667
CIBO_EIGHT_LEDGER_DIGEST = (
    "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
)


def contract_payload() -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    return {
        "candidate_id": CANDIDATE_ID,
        "market": MARKET,
        "timezone": "America/New_York",
        "methodology": "VT31-AM-Silver-Bullet-R2.2-specialized-NAS100",
        "reference": "09:00-10:00-NY-frozen-M1",
        "source_setup_window": "10:00-11:00-NY",
        "source_model": "strict-first-side-raid->structural-close->PD-array",
        "entry_families": ["breaker", "fair-value-gap", "order-block"],
        "execution_policy_fingerprint": policy.fingerprint(),
        "embedded_cognitive_memory": {
            "architecture": "THREE_PERSISTENT_MEMORIES_PLUS_SITUATION",
            "bundle_fingerprint": memory_fingerprint(),
            "strategy_identity_memory_fingerprint": (
                strategy_identity_fingerprint()
            ),
            "cibo_market_memory_fingerprint": (
                cibo_market_memory_fingerprint()
            ),
            "trader_experience_memory_fingerprint": (
                trader_experience_fingerprint()
            ),
            "situation_model": {
                "persistent": False,
                "rebuilt_each_decision": True,
                "historical_outcome_labels_allowed": False,
            },
            "external_cibo_runtime_dependency": False,
            "memory_location": "inside-VT31-specialist",
            "memory_sources": [
                "VT31-strategy-identity",
                "governed-CIBO-NAS100-market-dossier",
                "consumed-VT31-trader-experience",
                "causal-current-NAS100-situation",
            ],
            "runtime_mutation": False,
        },
        "runtime_intelligence": {
            "source": "NAS100-closed-M1-only",
            "date_level_cibo_lookup": False,
            "future_bar_lookup": False,
            "cross_index_required": False,
            "last_structure_state": (
                "causal-v2:closed-M1-only;liquidity-reclaims-at-bar-close;"
                "PD-array-touch-not-before-formation"
            ),
            "legacy_cibo_structure_timestamp_semantics_allowed": False,
            "entry_state": {
                "last_observed_structure_event": "reference-liquidity-sweep",
                "current_path_volatility_state": (
                    "compressed:<0.75x previous admitted NY 00:00-16:00 range"
                ),
                "conditional_timing": "decision-before-10:30-NY",
                "sequence_freshness": "reject first-reference-reclaim age 8-14m",
            },
        },
        "entry": "earliest-source-valid-R2.2-executable-confluence",
        "initial_stop": "source-methodological-swing-extreme-no-buffer",
        "target_intelligence": {
            "reference_volatility_definition": (
                "09:00-reference-width / median(last-up-to-5 admitted prior "
                "09:00-reference-widths)"
            ),
            "compressed_reference": {
                "condition": "<0.75",
                "action": "full-opposite-frozen-09-boundary",
                "management": "single-BE-at-source-3R-next-bar;no-trailing",
            },
            "normal_or_expanded_reference": {
                "condition": ">=0.75",
                "action": (
                    "50%-at-1.25R + 50%-runner-to-opposite-frozen-09-boundary"
                ),
                "runner_management": "move-runner-to-BE-next-bar-after-partial",
            },
            "boundary_closer_than_partial": "full-exit-at-boundary",
        },
        "pending_expiry": "11:00-NY",
        "filled_lifecycle": "16:00-NY",
        "same_bar_ambiguity": "censor/fail-closed",
        "friction_r_per_trade": format(FRICTION, "f"),
        "cross_index": (
            "optional-context-telemetry-only;not-required-so-SP500/US30 "
            "fresh-holdouts-remain-independent"
        ),
        "historical_learning_binding": {
            "cibo_run_id": CIBO_EIGHT_LEDGER_RUN_ID,
            "cibo_artifact_id": CIBO_EIGHT_LEDGER_ARTIFACT_ID,
            "cibo_digest": CIBO_EIGHT_LEDGER_DIGEST,
            "market_state_run": 35284479467,
            "cibo_bridge_run": 35288950361,
            "market_understanding_run": 35289940990,
            "policy_lab_run": 35290200552,
        },
        "development_gates": {
            "per_fold_terminal_sample": ">=30",
            "per_fold_stressed_mean_r": ">0",
            "per_fold_stressed_profit_factor": ">=1.15",
            "per_fold_max_drawdown_r": "<=20",
            "per_fold_max_losing_streak": "<=15",
            "per_fold_mc_positive_terminal_probability": ">=0.70",
            "per_fold_mc_p95_max_drawdown_r": "<=20",
        },
        "holdout_order": (
            "implementation->focused/static/full-QORE->exact-SHA+fingerprint-"
            "freeze->one-shot-2015-04-19..2016-04-19-holdout"
        ),
        "holdout_retuning": False,
        "research_only": True,
        "candidate_frozen": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    encoded = json.dumps(
        contract_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _slice(
    bars: tuple[object, ...],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
) -> tuple[object, ...]:
    return tuple(
        bar
        for bar in bars
        if start <= _wall(getattr(bar, "opened_at")) < end
    )


def _interval_range(bars: tuple[object, ...]) -> Decimal | None:
    if not bars:
        return None
    return max(_d(getattr(bar, "high")) for bar in bars) - min(
        _d(getattr(bar, "low")) for bar in bars
    )


def _admitted_day(day_bars: tuple[object, ...]) -> bool:
    return (
        len(_slice(day_bars, (9, 0, 0), (10, 0, 0))) == 60
        and len(_slice(day_bars, (10, 0, 0), (11, 0, 0))) == 60
    )


def _last_structure_event_family(
    session_prefix: tuple[object, ...],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> tuple[str, int | None]:
    path = tuple(
        bar
        for bar in session_prefix
        if cast(datetime, getattr(bar, "closed_at"))
        >= source.structure.raid_at
        and cast(datetime, getattr(bar, "closed_at")) <= decision_at
    )
    return last_causal_structure_event(
        cast(Any, path),
        source,
        decision_at,
    )


def _first_reference_reclaim_at(
    session_prefix: tuple[object, ...],
    source: Vt31R22SourceSetup,
) -> datetime | None:
    for bar in session_prefix:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at < source.structure.raid_at:
            continue
        close = _d(getattr(bar, "close"))
        if source.side.value == "short" and close < source.reference.high:
            return closed_at
        if source.side.value == "long" and close > source.reference.low:
            return closed_at
    return None


def _reference_width(day_bars: tuple[object, ...]) -> Decimal | None:
    reference = _slice(day_bars, (9, 0, 0), (10, 0, 0))
    if len(reference) != 60:
        return None
    return _interval_range(reference)


def _context_map(
    by_day: dict[date, tuple[object, ...]],
) -> dict[date, tuple[Decimal | None, Decimal | None]]:
    result: dict[date, tuple[Decimal | None, Decimal | None]] = {}
    admitted_ranges: list[Decimal | None] = []
    admitted_widths: list[Decimal] = []
    for local_day in sorted(by_day):
        previous_path_range = (
            admitted_ranges[-1] if admitted_ranges else None
        )
        prior_ref_median = (
            median(admitted_widths[-5:]) if admitted_widths else None
        )
        result[local_day] = (previous_path_range, prior_ref_median)

        day_bars = by_day[local_day]
        if not _admitted_day(day_bars):
            continue
        admitted_ranges.append(
            _interval_range(
                _slice(day_bars, (0, 0, 0), (16, 0, 0))
            )
        )
        width = _reference_width(day_bars)
        if width is not None and width > 0:
            admitted_widths.append(width)
    return result


def _state_snapshot(
    day_bars: tuple[object, ...],
    previous_path_range: Decimal | None,
    prior_ref_median: Decimal | None,
    session_prefix: tuple[object, ...],
    source: Vt31R22SourceSetup,
    executable: Vt31R22ExecutableSetup,
) -> dict[str, object]:
    decision_at = executable.decision_at
    decision_local = decision_at.astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York")
    )
    decision_minute = decision_local.hour * 60 + decision_local.minute

    current_path = tuple(
        bar
        for bar in day_bars
        if (0, 0, 0)
        <= _wall(getattr(bar, "opened_at"))
        < (16, 0, 0)
        and cast(datetime, getattr(bar, "closed_at")) <= decision_at
    )
    current_path_range = _interval_range(current_path)
    current_path_ratio = (
        current_path_range / previous_path_range
        if current_path_range is not None
        and previous_path_range is not None
        and previous_path_range > 0
        else None
    )
    current_path_compressed = (
        current_path_ratio is not None
        and current_path_ratio < COMPRESSION_THRESHOLD
    )

    reference_width = source.reference.high - source.reference.low
    ref_ratio = (
        reference_width / prior_ref_median
        if prior_ref_median is not None and prior_ref_median > 0
        else None
    )
    reference_volatility_state = (
        "unavailable"
        if ref_ratio is None
        else (
            "compressed"
            if ref_ratio < COMPRESSION_THRESHOLD
            else (
                "normal"
                if ref_ratio <= Decimal("1.25")
                else "expanded"
            )
        )
    )

    reclaim_at = _first_reference_reclaim_at(session_prefix, source)
    reclaim_age = (
        int((decision_at - reclaim_at).total_seconds() // 60)
        if reclaim_at is not None
        else None
    )
    stale_8_14 = (
        reclaim_age is not None and 8 <= reclaim_age < 15
    )
    last_family, last_age = _last_structure_event_family(
        session_prefix,
        source,
        decision_at,
    )

    current_range_state = (
        "unavailable"
        if current_path_ratio is None
        else (
            "compressed"
            if current_path_ratio < Decimal("0.75")
            else (
                "normal"
                if current_path_ratio <= Decimal("1.25")
                else "expanded"
            )
        )
    )
    breach_side = "high" if source.side.value == "short" else "low"
    confirmation_latency = int(
        (
            source.structure.confirmation_at - source.structure.raid_at
        ).total_seconds()
        // 60
    )
    selected_candidates = [
        candidate
        for candidate in source.candidates
        if candidate.family == executable.selected_family
        and candidate.formed_at <= decision_at
    ]
    selected_formed_at = (
        min(candidate.formed_at for candidate in selected_candidates)
        if selected_candidates
        else decision_at
    )
    entry_evidence_age = int(
        (decision_at - selected_formed_at).total_seconds() // 60
    )
    risk_ref = (
        executable.initial_risk / reference_width
        if reference_width > 0
        else None
    )
    planned_target_r = (
        abs(executable.target_price - executable.entry_price)
        / executable.initial_risk
        if executable.initial_risk > 0
        else None
    )
    destination_distance_ref = (
        abs(executable.target_price - executable.entry_price)
        / reference_width
        if reference_width > 0
        else None
    )

    reasoning = reason(
        Nas100ReasoningState(
            as_of=decision_at.astimezone(UTC).isoformat(),
            weekday=decision_local.strftime("%A"),
            session="NY_AM_SILVER_BULLET",
            decision_minute_ny=decision_minute,
            side=executable.side.value,
            setup_family="VT31_AM_SILVER_BULLET_R2_2",
            confirmation_state="confirmed",
            prior_day_state="UNRESOLVED_IN_DIRECT_RUNTIME",
            h4_state="UNRESOLVED_IN_DIRECT_RUNTIME",
            h1_state="UNRESOLVED_IN_DIRECT_RUNTIME",
            range_state=current_range_state,
            volatility_state=reference_volatility_state,
            current_path_vs_previous=current_path_ratio,
            reference_width_vs_prior5=ref_ratio,
            first_breach_side=breach_side,
            double_sided_before_decision=False,
            reference_reclaimed=reclaim_at is not None,
            reference_reclaim_age_minutes=reclaim_age,
            last_structure_event_family=last_family,
            last_structure_event_age_minutes=last_age,
            recent_liquidity_event_count_10m=None,
            displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
            entry_evidence_family=executable.selected_family.value,
            confirmation_latency_minutes=confirmation_latency,
            entry_evidence_freshness=(
                "fresh-0-5m"
                if entry_evidence_age <= 5
                else "older-than-5m"
            ),
            stop_plan="SOURCE_SWING_EXTREME",
            risk_ref=risk_ref,
            planned_target_r=planned_target_r,
            structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
            destination_distance_ref=destination_distance_ref,
            journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
            dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
            dol2_state="RESEARCH_ONLY_UNCALIBRATED",
            dol3_state="RESEARCH_ONLY_UNCALIBRATED",
            extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
            exhaustion_state="UNKNOWN",
            cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
        )
    )
    abstain_reasons = list(reasoning.contradictions)
    target_plan = reasoning.target_plan
    return {
        "decision_at": decision_at.astimezone(UTC).isoformat(),
        "decision_minute_ny": decision_minute,
        "last_structure_event_family": last_family,
        "last_structure_event_age_minutes": last_age,
        "reference_reclaim_age_minutes": reclaim_age,
        "sequence_stale_8_14": stale_8_14,
        "previous_admitted_path_range": (
            None
            if previous_path_range is None
            else format(previous_path_range, "f")
        ),
        "current_path_range": (
            None
            if current_path_range is None
            else format(current_path_range, "f")
        ),
        "current_path_vs_previous": (
            None
            if current_path_ratio is None
            else format(current_path_ratio, "f")
        ),
        "current_path_compressed": current_path_compressed,
        "reference_width": format(reference_width, "f"),
        "prior5_reference_width_median": (
            None
            if prior_ref_median is None
            else format(prior_ref_median, "f")
        ),
        "reference_width_vs_prior5": (
            None if ref_ratio is None else format(ref_ratio, "f")
        ),
        "reference_volatility_state": reference_volatility_state,
        "risk_ref": None if risk_ref is None else format(risk_ref, "f"),
        "planned_target_r": (
            None
            if planned_target_r is None
            else format(planned_target_r, "f")
        ),
        "destination_distance_ref": (
            None
            if destination_distance_ref is None
            else format(destination_distance_ref, "f")
        ),
        "confirmation_latency_minutes": confirmation_latency,
        "entry_evidence_age_minutes": entry_evidence_age,
        "action": reasoning.action,
        "abstain_reasons": abstain_reasons,
        "reasoning_thesis": reasoning.thesis,
        "reasoning_support": list(reasoning.supporting_evidence),
        "reasoning_contradictions": list(reasoning.contradictions),
        "reasoning_uncertainty": list(reasoning.uncertainty),
        "reasoning_wait_reasons": (
            list(reasoning.uncertainty)
            if reasoning.action == "WAIT"
            else []
        ),
        "journey_capacity_state": reasoning.journey_capacity_state,
        "management_context_state": reasoning.management_context_state,
        "strategy_memory_used": list(reasoning.strategy_memory_used),
        "cibo_market_memory_used": list(reasoning.cibo_market_memory_used),
        "trader_experience_memory_used": list(
            reasoning.trader_experience_memory_used
        ),
        "situation_fingerprint": reasoning.situation_fingerprint,
        "strategy_memory_fingerprint": (
            reasoning.strategy_memory_fingerprint
        ),
        "cibo_market_memory_fingerprint": (
            reasoning.cibo_market_memory_fingerprint
        ),
        "trader_experience_memory_fingerprint": (
            reasoning.trader_experience_memory_fingerprint
        ),
        "cognitive_memory_fingerprint": reasoning.memory_fingerprint,
        "stop_plan": "SOURCE_SWING_EXTREME",
        "target_plan": target_plan,
    }


def _simulate_selected_plan(
    day_bars: tuple[object, ...],
    executable: Vt31R22ExecutableSetup,
    state: dict[str, object],
) -> dict[str, object]:
    if state["target_plan"] == "FULL_STRUCTURAL_BOUNDARY":
        outcome = baseline._simulate(day_bars, executable)
        if outcome.get("status") == "terminal":
            outcome["target_plan"] = state["target_plan"]
        return outcome
    outcome = v2b._simulate_partial_runner(
        day_bars,
        executable,
        PARTIAL_TARGET_R,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
    return outcome


def _monte_carlo(
    trades: list[dict[str, object]],
) -> dict[str, object]:
    values = [
        Decimal(cast(str, trade["r_multiple"])) - FRICTION
        for trade in trades
    ]
    n = len(values)
    if n == 0:
        return {
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
    domain = (
        b"qore:vt31-nas100-specialist-r1:"
        + contract_fingerprint().encode()
    )
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(5)
            )
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for value in sampled[:n]:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(max_dd)
    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(
            Decimal(sum(value > 0 for value in terminals))
            / Decimal(10000),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(len(terminals) - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(len(terminals) - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(len(drawdowns) - 1) * 95 // 100],
            "f",
        ),
    }


def _block_metrics(
    trades: list[dict[str, object]],
    halfyear: bool,
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        local_date = cast(str, trade["local_date"])
        month = int(local_date[5:7])
        key = (
            f"{local_date[:4]}-H{1 if month <= 6 else 2}"
            if halfyear
            else f"{local_date[:4]}-Q{(month - 1) // 3 + 1}"
        )
        groups[key].append(trade)
    return {
        key: _metrics(group, friction=FRICTION)
        for key, group in sorted(groups.items())
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("VT31_NAS100_SPECIALIST_R1 requires NAS100 evidence")

    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day: dict[date, tuple[object, ...]] = {
        day: tuple(sorted(bars, key=lambda bar: getattr(bar, "opened_at")))
        for day, bars in raw_by_day.items()
    }

    context_by_day = _context_map(by_day)

    policy = Vt31R22ExecutionPolicy()
    trades: list[dict[str, object]] = []
    reasoning_trace: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    target_plan_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = _slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = _slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status_counts["incomplete-day"] += 1
            continue

        prefix = list(reference)
        previous_path_range, prior_ref_median = context_by_day[local_day]
        selected_source: Vt31R22SourceSetup | None = None
        selected: Vt31R22ExecutableSetup | None = None
        selected_state: dict[str, object] | None = None
        saw_source = False
        saw_wait = False
        hard_abstain = False

        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue

            saw_source = True
            executable, _ = make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                status_counts["source-not-executable"] += 1
                hard_abstain = True
                break

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            state = _state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                session_prefix,
                evaluation.setup,
                executable,
            )
            reasoning_trace.append(
                {
                    "local_date": local_day.isoformat(),
                    "side": executable.side.value,
                    "entry_family": executable.selected_family.value,
                    "entry": format(executable.entry_price, "f"),
                    "stop": format(executable.stop_price, "f"),
                    "structural_boundary": format(
                        executable.target_price,
                        "f",
                    ),
                    **state,
                    "outcome_fields_used_for_decision": False,
                }
            )

            action = cast(str, state["action"])
            if action == "WAIT":
                saw_wait = True
                status_counts["intelligence-wait-observation"] += 1
                continue
            if action == "ABSTAIN":
                status_counts["intelligence-abstain"] += 1
                hard_abstain = True
                break
            if action != "EXECUTE":
                raise ValueError(f"unsupported intelligence action: {action}")

            selected_source = evaluation.setup
            selected = executable
            selected_state = state
            break

        if selected is None or selected_source is None or selected_state is None:
            if saw_wait and not hard_abstain:
                status_counts["intelligence-wait-expired"] += 1
            elif not saw_source and not hard_abstain:
                status_counts["no-source-setup"] += 1
            continue

        state = selected_state
        target_plan_counts[cast(str, state["target_plan"])] += 1
        outcome = _simulate_selected_plan(day_bars, selected, state)
        status = cast(str, outcome["status"])
        status_counts[status] += 1
        if status != "terminal":
            continue
        outcome["intelligence_state"] = {
            key: state[key]
            for key in (
                "decision_minute_ny",
                "last_structure_event_family",
                "last_structure_event_age_minutes",
                "reference_reclaim_age_minutes",
                "current_path_vs_previous",
                "reference_width_vs_prior5",
                "reference_volatility_state",
                "risk_ref",
                "planned_target_r",
                "destination_distance_ref",
                "confirmation_latency_minutes",
                "entry_evidence_age_minutes",
                "journey_capacity_state",
                "management_context_state",
                "target_plan",
            )
        }
        trades.append(outcome)

    trades.sort(key=lambda trade: cast(str, trade["signal_at"]))
    stress = _metrics(trades, friction=FRICTION)
    mc = _monte_carlo(trades)
    gates = {
        "terminal_sample_at_least_30": int(stress["sample"]) >= 30,
        "stressed_mean_positive": (
            stress["mean_r"] is not None
            and Decimal(cast(str, stress["mean_r"])) > 0
        ),
        "stressed_profit_factor_at_least_1_15": (
            stress["profit_factor"] is not None
            and Decimal(cast(str, stress["profit_factor"]))
            >= Decimal("1.15")
        ),
        "stressed_max_drawdown_at_most_20r": (
            Decimal(cast(str, stress["max_drawdown_r"]))
            <= Decimal(20)
        ),
        "max_losing_streak_at_most_15": (
            int(stress["max_losing_streak"]) <= 15
        ),
        "mc_positive_terminal_probability_at_least_0_70": (
            Decimal(cast(str, mc["positive_terminal_probability"]))
            >= Decimal("0.70")
        ),
        "mc_p95_max_drawdown_at_most_20r": (
            Decimal(cast(str, mc["p95_max_drawdown_r"]))
            <= Decimal(20)
        ),
    }
    return {
        "schema": SCHEMA,
        "candidate_id": CANDIDATE_ID,
        "contract": contract_payload(),
        "contract_fingerprint": contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
            "bar_count": len(series),
            "first_opened_at": getattr(series[0], "opened_at")
            .astimezone(UTC)
            .isoformat(),
            "last_closed_at": getattr(series[-1], "closed_at")
            .astimezone(UTC)
            .isoformat(),
        },
        "market_days": len(by_day),
        "status_counts": dict(sorted(status_counts.items())),
        "target_plan_counts": dict(sorted(target_plan_counts.items())),
        "stress_0_05r": stress,
        "halfyear_stress": _block_metrics(trades, halfyear=True),
        "quarter_stress": _block_metrics(trades, halfyear=False),
        "monte_carlo": mc,
        "development_gates": gates,
        "passes_development_gates": all(gates.values()),
        "trade_count": len(trades),
        "trades": trades,
        "reasoning_trace": reasoning_trace,
        "research_only": True,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def self_test() -> None:
    validate_memory()
    contract = contract_payload()
    assert contract["candidate_id"] == CANDIDATE_ID
    assert contract["market"] == MARKET
    runtime = cast(dict[str, object], contract["runtime_intelligence"])
    assert runtime["date_level_cibo_lookup"] is False
    assert runtime["future_bar_lookup"] is False
    assert runtime["cross_index_required"] is False
    memory = cast(dict[str, object], contract["embedded_cognitive_memory"])
    assert (
        memory["architecture"]
        == "THREE_PERSISTENT_MEMORIES_PLUS_SITUATION"
    )
    assert memory["external_cibo_runtime_dependency"] is False
    assert memory["bundle_fingerprint"] == memory_fingerprint()
    assert (
        memory["strategy_identity_memory_fingerprint"]
        == strategy_identity_fingerprint()
    )
    assert (
        memory["cibo_market_memory_fingerprint"]
        == cibo_market_memory_fingerprint()
    )
    assert (
        memory["trader_experience_memory_fingerprint"]
        == trader_experience_fingerprint()
    )
    assert contract["initial_stop"] == (
        "source-methodological-swing-extreme-no-buffer"
    )
    assert len(contract_fingerprint()) == 64
    assert COMPRESSION_THRESHOLD == Decimal("0.75")
    assert PARTIAL_TARGET_R == Decimal("1.25")
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "contract_fingerprint": contract_fingerprint(),
            },
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.evidence is None or args.output is None:
        parser.error("evidence and --output are required")
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": CANDIDATE_ID,
                "contract_fingerprint": payload["contract_fingerprint"],
                "stress_0_05r": payload["stress_0_05r"],
                "monte_carlo": payload["monte_carlo"],
                "development_gates": payload["development_gates"],
                "passes_development_gates": payload[
                    "passes_development_gates"
                ],
                "target_plan_counts": payload["target_plan_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
