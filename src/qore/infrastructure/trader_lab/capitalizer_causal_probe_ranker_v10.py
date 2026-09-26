"""Continuous cross-period probe-value ranker for Capitalizer.

V9 falsified sparse categorical lookup for deciding when SURFACE_SELECTIVE may
release its sticky 0.20R defensive state. V10 replaces cells with a continuous
nearest-neighbour ranker over causal pre-entry state.

For each consumed window held out, TWO independent models are calibrated:
one from each of the other consumed windows. The held-out window contributes no
labels, thresholds, examples, or calibration. A probe can release only when
both models rank it above the same predeclared percentile and both corresponding
training tails have positive expectancy.

All entries, true 2R target, contextual position routing, and MAX3 are preserved.
Only exposure on an existing 0.20R decision may be released to 0.35R/0.55R.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_loss_pressure_surface_v7 as pressure_v7,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dd_path_state_machine_v8 as path_v8,
)
from qore.infrastructure.trader_lab import (
    capitalizer_local_edge_convex_surface_v6 as edge_v6,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_market_context_v1 as context,
)
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)

IDENTITY = "QORE_CAPITALIZER_CAUSAL_PROBE_RANKER_V10"
BASE_POSITION_POLICY = "CONTEXT_STABILITY_STAGE"
EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034
EXPECTED_RESERVED_TRADES = 1088
NEIGHBOURS = 24
MIN_TAIL_SUPPORT = 8
QUANTILES = (0.60, 0.70, 0.80, 0.90)
POLICIES = (
    "SURFACE_CONTROL",
    "RANK_Q60_035",
    "RANK_Q70_035",
    "RANK_Q80_035",
    "RANK_Q80_DYNAMIC",
    "RANK_Q90_035",
)
POLICY_Q = {
    "RANK_Q60_035": 0.60,
    "RANK_Q70_035": 0.70,
    "RANK_Q80_035": 0.80,
    "RANK_Q80_DYNAMIC": 0.80,
    "RANK_Q90_035": 0.90,
}


@dataclass(frozen=True, slots=True)
class ProbePoint:
    period: str
    symbol: str
    session: str
    provenance: str
    mode: str
    regime: str
    destination: str
    entry_at: str
    vector: tuple[float, ...]
    realized_r: str | None = None


@dataclass(frozen=True, slots=True)
class PeriodModel:
    period: str
    points: tuple[ProbePoint, ...]
    loo_scores: tuple[float, ...]
    tail_mean_r: dict[str, float]
    tail_support: dict[str, int]


@dataclass(frozen=True, slots=True)
class Pretrade:
    ctx: context.NativeContextRow
    mode: str
    current_dd: Decimal
    base_multiplier: Decimal
    point: ProbePoint


@dataclass(frozen=True, slots=True)
class RankDecision:
    heldout_period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    base_multiplier: str
    final_multiplier: str
    training_periods: tuple[str, str] | None
    model_scores: tuple[str, str] | None
    model_percentiles: tuple[str, str] | None
    minimum_percentile: str | None
    minimum_training_tail_mean_r: str | None
    minimum_training_tail_support: int
    release_applied: bool
    current_outcome_visible_to_decision: bool = False
    heldout_outcomes_visible_to_models: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _clip(value: float, low: float = -2.0, high: float = 2.0) -> float:
    return max(low, min(high, value))


def _ratio(value: Decimal, scale: Decimal) -> float:
    return _clip(float(value / scale))


def _alignment(value: str) -> float:
    if value == "ALIGNED":
        return 1.0
    if value == "OPPOSED":
        return -1.0
    return 0.0


def _scope_summary(
    evidence: tuple[memory.ScopeEvidence, ...],
) -> tuple[float, float, float]:
    bound = tuple(
        item
        for item in evidence
        if item.posterior_mean_r is not None
        and item.posterior_negative_rate is not None
    )
    if not bound:
        return 0.0, 0.5, 0.0
    means = tuple(float(Decimal(item.posterior_mean_r or "0")) for item in bound)
    negatives = tuple(
        float(Decimal(item.posterior_negative_rate or "0.5")) for item in bound
    )
    support = sum(item.support for item in bound) / (20.0 * len(bound))
    return (
        _clip(sum(means) / len(means)),
        _clip(sum(negatives) / len(negatives), 0.0, 1.0),
        _clip(support, 0.0, 2.0),
    )


def _vector(
    *,
    ctx: context.NativeContextRow,
    current_dd: Decimal,
    loss_streak: int,
    hazard_score: int,
    evidence: tuple[memory.ScopeEvidence, ...],
    pressure: pressure_v7.PressureState,
    recent3_sum: Decimal,
    recent3_positive: int,
    session_support: int,
    session_mean: Decimal | None,
    session_negative: Decimal | None,
) -> tuple[float, ...]:
    adverse = sum(item.adverse for item in evidence)
    severe = sum(item.severe for item in evidence)
    favorable = path_v8._favorable_votes(evidence)
    scope_mean, scope_negative, scope_support = _scope_summary(evidence)
    vol_delta = (
        0.0
        if ctx.volatility_ratio is None
        else _clip(float(Decimal(ctx.volatility_ratio) - Decimal("1")))
    )
    room = (
        2.0
        if ctx.destination_room_r is None
        else _clip(float(Decimal(ctx.destination_room_r) / Decimal("3")), 0.0, 2.0)
    )
    session_edge_mean = 0.0 if session_mean is None else _clip(float(session_mean))
    session_edge_negative = (
        0.5
        if session_negative is None
        else _clip(float(session_negative), 0.0, 1.0)
    )
    global_loss_rate = (
        pressure.global_losses / pressure.global_support
        if pressure.global_support
        else 0.0
    )
    severe_loss_rate = (
        pressure.severe_losses / pressure.severe_support
        if pressure.severe_support
        else 0.0
    )
    session_loss_rate = (
        pressure.session_losses / pressure.session_support
        if pressure.session_support
        else 0.0
    )
    return (
        _ratio(current_dd, Decimal("6")),
        _clip(loss_streak / 8.0, 0.0, 2.0),
        _clip(hazard_score / 12.0, 0.0, 2.0),
        _clip(adverse / 4.0, 0.0, 1.0),
        _clip(severe / 4.0, 0.0, 1.0),
        _clip(favorable / 4.0, 0.0, 1.0),
        _ratio(recent3_sum, Decimal("3")),
        _clip(recent3_positive / 3.0, 0.0, 1.0),
        _ratio(Decimal(pressure.global_sum_r), Decimal("8")),
        _clip(global_loss_rate, 0.0, 1.0),
        _clip(pressure.global_negative_symbols / 8.0, 0.0, 1.0),
        _ratio(Decimal(pressure.severe_sum_r), Decimal("10")),
        _clip(severe_loss_rate, 0.0, 1.0),
        _ratio(Decimal(pressure.session_sum_r), Decimal("6")),
        _clip(session_loss_rate, 0.0, 1.0),
        _clip(session_support / 12.0, 0.0, 1.0),
        session_edge_mean,
        session_edge_negative,
        vol_delta,
        room,
        scope_mean,
        scope_negative,
        scope_support,
        _alignment(ctx.h1_body_alignment),
        _alignment(ctx.m15_slope_alignment),
    )


def _pretrade(
    *,
    period: str,
    trade: milestone.SimulatedTrade,
    contexts: dict[tuple[str, str], context.NativeContextRow],
    contextual_model: dict[str, Any],
    chosen_scaled: tuple[milestone.SimulatedTrade, ...],
    records: tuple[memory.MemoryRecord, ...],
) -> Pretrade:
    ctx = contexts[(trade.symbol, trade.entry_at)]
    entry_at = direct._aware(trade.entry_at)
    history = governor._closed_history(chosen_scaled, entry_at=entry_at)
    state, _eq, _peak, current_dd, loss_streak = governor._state(history)
    mode, _level, _support = router._lookup(contextual_model, ctx)
    mode, _overlay = router._overlay(
        policy=BASE_POSITION_POLICY,
        base_mode=mode,
        state=state,
    )
    causal_records = memory._closed_records(records, entry_at=trade.entry_at)
    evidence = memory._evidence(records=causal_records, ctx=ctx)
    adverse = sum(item.adverse for item in evidence)
    hazards = frozen._frozen_hazards(
        ctx=ctx,
        current_dd=current_dd,
        adverse_votes=adverse,
    )
    hazard_score = frozen._frozen_score(hazards)
    base_multiplier = frozen._frozen_multiplier(
        current_dd=current_dd,
        score=hazard_score,
        adverse_votes=adverse,
    )
    pressure = pressure_v7._pressure(causal_records, session=trade.session)
    recent3_sum, recent3_positive = path_v8._recent3(causal_records)
    session_support, session_mean, session_negative = edge_v6._session_stats(
        causal_records,
        session=trade.session,
    )
    point = ProbePoint(
        period=period,
        symbol=ctx.symbol,
        session=ctx.session,
        provenance=ctx.provenance,
        mode=mode,
        regime=ctx.regime_signature,
        destination=ctx.destination_state,
        entry_at=trade.entry_at,
        vector=_vector(
            ctx=ctx,
            current_dd=current_dd,
            loss_streak=loss_streak,
            hazard_score=hazard_score,
            evidence=evidence,
            pressure=pressure,
            recent3_sum=recent3_sum,
            recent3_positive=recent3_positive,
            session_support=session_support,
            session_mean=session_mean,
            session_negative=session_negative,
        ),
    )
    return Pretrade(
        ctx=ctx,
        mode=mode,
        current_dd=current_dd,
        base_multiplier=base_multiplier,
        point=point,
    )


def _distance(left: ProbePoint, right: ProbePoint) -> float:
    distance = math.sqrt(
        sum((a - b) ** 2 for a, b in zip(left.vector, right.vector, strict=True))
    )
    distance += 0.25 if left.symbol != right.symbol else 0.0
    distance += 0.15 if left.session != right.session else 0.0
    distance += 0.15 if left.provenance != right.provenance else 0.0
    distance += 0.10 if left.mode != right.mode else 0.0
    distance += 0.10 if left.regime != right.regime else 0.0
    distance += 0.10 if left.destination != right.destination else 0.0
    return distance


def _predict(
    training: tuple[ProbePoint, ...],
    query: ProbePoint,
    *,
    exclude_key: tuple[str, str] | None = None,
) -> float:
    candidates = tuple(
        row
        for row in training
        if row.realized_r is not None
        and (
            exclude_key is None
            or (row.symbol, row.entry_at) != exclude_key
        )
    )
    if len(candidates) < NEIGHBOURS:
        raise ValueError("V10 ranker has insufficient training neighbours")
    selected = sorted(
        candidates,
        key=lambda row: _distance(row, query),
    )[:NEIGHBOURS]
    numerator = 0.0
    denominator = 0.0
    for row in selected:
        distance = _distance(row, query)
        weight = 1.0 / (0.05 + distance)
        numerator += weight * float(Decimal(row.realized_r or "0"))
        denominator += weight
    return numerator / denominator


def _quantile(values: tuple[float, ...], quantile: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def _fit_period(
    points: tuple[ProbePoint, ...],
    *,
    period: str,
) -> PeriodModel:
    selected = tuple(row for row in points if row.period == period)
    if len(selected) < 40:
        raise ValueError(f"{period} has too few 0.20R examples")
    loo_scores = tuple(
        _predict(
            selected,
            row,
            exclude_key=(row.symbol, row.entry_at),
        )
        for row in selected
    )
    tail_mean: dict[str, float] = {}
    tail_support: dict[str, int] = {}
    for quantile in QUANTILES:
        threshold = _quantile(loo_scores, quantile)
        labels = tuple(
            float(Decimal(row.realized_r or "0"))
            for score, row in zip(loo_scores, selected, strict=True)
            if score >= threshold
        )
        key = f"{quantile:.2f}"
        tail_support[key] = len(labels)
        tail_mean[key] = sum(labels) / len(labels) if labels else float("-inf")
    return PeriodModel(
        period=period,
        points=selected,
        loo_scores=loo_scores,
        tail_mean_r=tail_mean,
        tail_support=tail_support,
    )


def _percentile(model: PeriodModel, score: float) -> float:
    return sum(value <= score for value in model.loo_scores) / len(model.loo_scores)


def _release(
    models: tuple[PeriodModel, PeriodModel],
    *,
    point: ProbePoint,
    policy: str,
) -> tuple[Decimal, tuple[float, float], tuple[float, float], float, float, int]:
    quantile = POLICY_Q[policy]
    key = f"{quantile:.2f}"
    scores = tuple(_predict(model.points, point) for model in models)
    percentiles = tuple(
        _percentile(model, score)
        for model, score in zip(models, scores, strict=True)
    )
    min_percentile = min(percentiles)
    min_tail_mean = min(model.tail_mean_r[key] for model in models)
    min_tail_support = min(model.tail_support[key] for model in models)
    eligible = (
        min_percentile >= quantile
        and min_tail_mean > 0
        and min_tail_support >= MIN_TAIL_SUPPORT
    )
    release = Decimal("0.35") if eligible else Decimal("0.20")
    if policy == "RANK_Q80_DYNAMIC" and eligible:
        q90_mean = min(model.tail_mean_r["0.90"] for model in models)
        q90_support = min(model.tail_support["0.90"] for model in models)
        if (
            min_percentile >= 0.90
            and q90_mean >= 0.20
            and q90_support >= MIN_TAIL_SUPPORT
        ):
            release = Decimal("0.55")
    return (
        release,
        (scores[0], scores[1]),
        (percentiles[0], percentiles[1]),
        min_percentile,
        min_tail_mean,
        min_tail_support,
    )


def _surface_examples(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    contextual_model: dict[str, Any],
) -> tuple[ProbePoint, ...]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (direct._aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    result: list[ProbePoint] = []
    for trade in ordered:
        pre = _pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        unscaled = by_mode[pre.mode][(trade.symbol, trade.entry_at)]
        chosen.append(
            replace(
                unscaled,
                realized_gross_r=str(
                    Decimal(unscaled.realized_gross_r) * pre.base_multiplier
                ),
            )
        )
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        if pre.base_multiplier == Decimal("0.20"):
            result.append(
                replace(pre.point, realized_r=unscaled.realized_gross_r)
            )
    return tuple(result)


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    contextual_model: dict[str, Any],
    models: tuple[PeriodModel, PeriodModel] | None,
) -> tuple[dict[str, Any], tuple[RankDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (direct._aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[RankDecision] = []
    multipliers: Counter[str] = Counter()
    release_count = 0
    for trade in ordered:
        pre = _pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        final_multiplier = pre.base_multiplier
        scores: tuple[float, float] | None = None
        percentiles: tuple[float, float] | None = None
        minimum_percentile: float | None = None
        minimum_tail_mean: float | None = None
        minimum_tail_support = 0
        if policy != "SURFACE_CONTROL" and pre.base_multiplier == Decimal("0.20"):
            if models is None:
                raise ValueError("V10 rank policy requires two training models")
            (
                candidate,
                scores,
                percentiles,
                minimum_percentile,
                minimum_tail_mean,
                minimum_tail_support,
            ) = _release(models, point=pre.point, policy=policy)
            if candidate > pre.base_multiplier:
                final_multiplier = candidate
                release_count += 1

        # The current outcome is first touched after the decision is frozen.
        unscaled = by_mode[pre.mode][(trade.symbol, trade.entry_at)]
        chosen.append(
            replace(
                unscaled,
                realized_gross_r=str(
                    Decimal(unscaled.realized_gross_r) * final_multiplier
                ),
            )
        )
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        multipliers[str(final_multiplier)] += 1
        decisions.append(
            RankDecision(
                heldout_period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=pre.mode,
                base_multiplier=str(pre.base_multiplier),
                final_multiplier=str(final_multiplier),
                training_periods=(
                    None if models is None else (models[0].period, models[1].period)
                ),
                model_scores=(
                    None if scores is None else (str(scores[0]), str(scores[1]))
                ),
                model_percentiles=(
                    None
                    if percentiles is None
                    else (str(percentiles[0]), str(percentiles[1]))
                ),
                minimum_percentile=(
                    None if minimum_percentile is None else str(minimum_percentile)
                ),
                minimum_training_tail_mean_r=(
                    None if minimum_tail_mean is None else str(minimum_tail_mean)
                ),
                minimum_training_tail_support=minimum_tail_support,
                release_applied=final_multiplier > pre.base_multiplier,
            )
        )
    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "release_count": release_count,
        "multiplier_counts": dict(sorted(multipliers.items())),
    }, tuple(decisions)


def _annotate(current: dict[str, Any], control: dict[str, Any]) -> None:
    metrics = current["metrics"]
    base = control["metrics"]
    current["pf_at_least_surface_control"] = (
        Decimal(str(metrics["profit_factor"]))
        >= Decimal(str(base["profit_factor"]))
    )
    current["dd_below_surface_control"] = (
        Decimal(str(metrics["max_drawdown_r"]))
        < Decimal(str(base["max_drawdown_r"]))
    )
    current["total_r_at_least_surface_control"] = (
        Decimal(str(metrics["total_r"])) >= Decimal(str(base["total_r"]))
    )
    current["dd_at_or_below_6r"] = (
        Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
    )


def _diagnostics(model: PeriodModel) -> dict[str, Any]:
    labels = tuple(float(Decimal(row.realized_r or "0")) for row in model.points)
    return {
        "period": model.period,
        "training_examples": len(model.points),
        "mean_training_r": str(sum(labels) / len(labels)),
        "tail_mean_r": {
            key: str(value) for key, value in sorted(model.tail_mean_r.items())
        },
        "tail_support": dict(sorted(model.tail_support.items())),
    }


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[RankDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    if {len(rows) for rows in reserved.values()} != {EXPECTED_RESERVED_TRADES}:
        raise ValueError("V10 consumed reserved population mismatch")

    dev_context = router._load_contexts(
        development_validation_context_root,
        role="dev",
    )
    validation_context = router._load_contexts(
        development_validation_context_root,
        role="holdout",
    )
    reserved_keys = {
        (row.symbol, row.entry_at)
        for row in reserved[milestone.ProtectionMode.ORIGINAL.value]
    }
    reserved_context = edge_v6._load_reserved_contexts(
        reserved_context_root,
        baseline_keys=reserved_keys,
    )
    contextual_model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )
    windows = {
        "DEVELOPMENT_2024_2026": (development, dev_context),
        "CONSUMED_VALIDATION_2022_2024": (validation, validation_context),
        "CONSUMED_RESERVED_2020_2022": (reserved, reserved_context),
    }
    examples = {
        period: _surface_examples(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
        )
        for period, (ledgers, contexts) in windows.items()
    }
    models = {
        period: _fit_period(points, period=period)
        for period, points in examples.items()
    }

    controls: dict[str, dict[str, Any]] = {}
    audits: list[RankDecision] = []
    for period, (ledgers, contexts) in windows.items():
        control, audit = _simulate(
            period=period,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            models=None,
        )
        controls[period] = control
        audits.extend(audit)

    results: list[dict[str, Any]] = []
    for policy in POLICIES:
        heldouts: dict[str, Any] = {}
        diagnostics: dict[str, Any] = {}
        for heldout, (ledgers, contexts) in windows.items():
            if policy == "SURFACE_CONTROL":
                current = controls[heldout]
                diagnostics[heldout] = []
            else:
                training = tuple(period for period in windows if period != heldout)
                pair = (models[training[0]], models[training[1]])
                diagnostics[heldout] = [_diagnostics(model) for model in pair]
                current, audit = _simulate(
                    period=heldout,
                    policy=policy,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    models=pair,
                )
                audits.extend(audit)
            _annotate(current, controls[heldout])
            heldouts[heldout] = current
        robust_pf_dd = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            for row in heldouts.values()
        )
        robust_full = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            and row["total_r_at_least_surface_control"]
            for row in heldouts.values()
        )
        all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
        results.append(
            {
                "policy": policy,
                "heldouts": heldouts,
                "model_diagnostics": diagnostics,
                "robust_pf_up_dd_down_all_loo_windows": robust_pf_dd,
                "robust_pf_dd_total_r_all_loo_windows": robust_full,
                "all_loo_windows_dd6": all_dd6,
            }
        )

    robust = tuple(
        row for row in results if row["robust_pf_up_dd_down_all_loo_windows"]
    )
    robust_full = tuple(
        row for row in results if row["robust_pf_dd_total_r_all_loo_windows"]
    )
    dd6 = tuple(row for row in robust_full if row["all_loo_windows_dd6"])
    next_phase = (
        "FREEZE_V10_ON_ALL_CONSUMED_THEN_OPEN_2018_2020"
        if dd6
        else (
            "BUILD_FACTOR_GRAPH_PROBE_VALUE_WITH_CONCURRENT_EXPOSURE_"
            "AND_SESSION_JOURNEY"
        )
    )
    return {
        "identity": IDENTITY,
        "evaluation": "THREE_WAY_DUAL_MODEL_CONTINUOUS_LOO",
        "windows": list(windows),
        "all_windows_consumed_before_v10": True,
        "next_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "surface_020_example_counts": {
            period: len(points) for period, points in examples.items()
        },
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "robust_pf_dd_total_r_policy_count": len(robust_full),
        "robust_full_and_all_windows_dd6_policy_count": len(dd6),
        "heldout_outcomes_visible_to_models": False,
        "each_model_uses_exactly_one_other_period": True,
        "release_requires_cross_period_model_agreement": True,
        "continuous_preentry_features_used": True,
        "runtime_decisions_use_preentry_or_prior_closed_only": True,
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "all_entries_preserved": True,
        "target_r": "2.00",
        "max3_preserved": True,
        "automatic_policy_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": next_phase,
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[RankDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-causal-probe-ranker-v10.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-causal-probe-ranker-v10-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
