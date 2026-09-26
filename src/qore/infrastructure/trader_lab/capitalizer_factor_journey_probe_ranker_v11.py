"""Factor/Journey feature delta for Capitalizer V10.

V11 deliberately reuses the V10 ranker, policies, thresholds, loaders and
economic comparison. The only experimental delta is an enriched pre-entry
vector built from causally available state:
- prior entries that are still open at the current decision;
- canonical Exposure Graph factor alignment/conflict;
- same-day and prior-session journey from trades already closed;
- exact-timestamp factor competition among simultaneously decision-ready tickets.

Open trades contribute structure only, never their future outcome. V10's
_pretrade hook is replaced only inside build_report() and restored in finally.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import capitalizer_exposure_graph as exposure
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)

IDENTITY = "QORE_CAPITALIZER_FACTOR_JOURNEY_PROBE_RANKER_V11"
SESSION_ORDER = {"ASIA": 0, "LONDON": 1, "NEW_YORK": 2}
_BASE_PRETRADE = v10._pretrade

# Bound only while build_report() is running. Keys are period/session/entry timestamp.
# Rows expose symbol/side/time structure only; peer outcomes are never read.
_SIMULTANEOUS: dict[
    tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
] = {}


def _factor_map(
    *,
    symbol: str,
    side: str,
) -> dict[str, exposure.CapitalizerFactorExposure]:
    position = exposure.CapitalizerExposurePosition(
        symbol=symbol,
        side=exposure.CapitalizerSide(side),
        risk_r=Decimal("1"),
    )
    return {
        row.factor: row
        for row in exposure.factor_exposures((position,))
    }


def _competition_features(
    *,
    period: str,
    trade: milestone.SimulatedTrade,
) -> tuple[float, ...]:
    """Describe simultaneous factor competition without selecting a winner."""

    peers = tuple(
        row
        for row in _SIMULTANEOUS.get(
            (period, trade.session, trade.entry_at),
            (),
        )
        if row.symbol != trade.symbol
    )
    candidate = _factor_map(symbol=trade.symbol, side=trade.side)
    same_factor_peers = 0
    aligned_peers = 0
    opposed_peers = 0
    shared_factors: set[str] = set()

    for peer in peers:
        other = _factor_map(symbol=peer.symbol, side=peer.side)
        shared = frozenset(candidate) & frozenset(other)
        if not shared:
            continue
        same_factor_peers += 1
        shared_factors.update(shared)
        products = tuple(candidate[f].net_r * other[f].net_r for f in shared)
        if any(value > 0 for value in products):
            aligned_peers += 1
        if any(value < 0 for value in products):
            opposed_peers += 1

    return (
        v10._clip(len(peers) / 3.0, 0.0, 2.0),
        v10._clip(same_factor_peers / 3.0, 0.0, 2.0),
        v10._clip(aligned_peers / 3.0, 0.0, 2.0),
        v10._clip(opposed_peers / 3.0, 0.0, 2.0),
        v10._clip(len(shared_factors) / 3.0, 0.0, 2.0),
    )


def _simultaneous_map(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> dict[tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]]:
    grouped: dict[
        tuple[str, str, str], list[milestone.SimulatedTrade]
    ] = defaultdict(list)
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    for row in baseline:
        grouped[(period, row.session, row.entry_at)].append(row)
    return {
        key: tuple(sorted(rows, key=lambda item: item.symbol))
        for key, rows in grouped.items()
        if len(rows) > 1
    }


def _active_trades(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    entry_at: str,
) -> tuple[milestone.SimulatedTrade, ...]:
    current = direct._aware(entry_at)
    return tuple(
        row
        for row in chosen
        if direct._aware(row.entry_at) < current < direct._aware(row.exit_at)
    )


def _closed_trades(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    entry_at: str,
) -> tuple[milestone.SimulatedTrade, ...]:
    current = direct._aware(entry_at)
    return tuple(
        row
        for row in chosen
        if direct._aware(row.exit_at) <= current
    )


def _factor_features(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    trade: milestone.SimulatedTrade,
) -> tuple[float, ...]:
    active = _active_trades(chosen, entry_at=trade.entry_at)
    active_positions = tuple(
        exposure.CapitalizerExposurePosition(
            symbol=row.symbol,
            side=exposure.CapitalizerSide(row.side),
            risk_r=Decimal("1"),
        )
        for row in active
    )
    active_map = {
        row.factor: row
        for row in exposure.factor_exposures(active_positions)
    }
    current_map = _factor_map(symbol=trade.symbol, side=trade.side)
    current_factors = frozenset(current_map)

    shared_positions = sum(
        bool(
            current_factors
            & frozenset(_factor_map(symbol=row.symbol, side=row.side))
        )
        for row in active
    )
    shared_gross = Decimal("0")
    aligned = Decimal("0")
    opposed = Decimal("0")
    for factor, candidate in current_map.items():
        prior = active_map.get(factor)
        if prior is None:
            continue
        shared_gross += prior.gross_r
        product = candidate.net_r * prior.net_r
        if product > 0:
            aligned += abs(prior.net_r)
        elif product < 0:
            opposed += abs(prior.net_r)

    return (
        v10._clip(len(active) / 3.0, 0.0, 2.0),
        v10._clip(shared_positions / 3.0, 0.0, 2.0),
        v10._clip(float(shared_gross / Decimal("2")), 0.0, 2.0),
        v10._clip(float(aligned / Decimal("2")), 0.0, 2.0),
        v10._clip(float(opposed / Decimal("2")), 0.0, 2.0),
    )


def _stats(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal]:
    if not rows:
        return Decimal("0"), Decimal("0.5")
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    return (
        sum(values, Decimal("0")),
        Decimal(sum(value < 0 for value in values)) / Decimal(len(values)),
    )


def _journey_features(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    trade: milestone.SimulatedTrade,
) -> tuple[float, ...]:
    closed = _closed_trades(chosen, entry_at=trade.entry_at)
    same_day = tuple(
        row for row in closed
        if row.operating_date == trade.operating_date
    )
    rank = SESSION_ORDER[trade.session]
    current_session = tuple(
        row for row in same_day
        if row.session == trade.session
    )
    prior_sessions = tuple(
        row for row in same_day
        if SESSION_ORDER.get(row.session, -1) < rank
    )
    factors = frozenset(_factor_map(symbol=trade.symbol, side=trade.side))
    related = tuple(
        row
        for row in same_day
        if factors & frozenset(_factor_map(symbol=row.symbol, side=row.side))
    )
    day_sum, day_neg = _stats(same_day)
    current_sum, current_neg = _stats(current_session)
    prior_sum, prior_neg = _stats(prior_sessions)
    factor_sum, factor_neg = _stats(related)
    return (
        v10._clip(float(day_sum / Decimal("6"))),
        v10._clip(float(day_neg), 0.0, 1.0),
        v10._clip(float(current_sum / Decimal("4"))),
        v10._clip(float(current_neg), 0.0, 1.0),
        v10._clip(float(prior_sum / Decimal("4"))),
        v10._clip(float(prior_neg), 0.0, 1.0),
        v10._clip(float(factor_sum / Decimal("4"))),
        v10._clip(float(factor_neg), 0.0, 1.0),
        v10._clip(rank / 2.0, 0.0, 1.0),
        v10._clip(len(same_day) / 9.0, 0.0, 1.0),
    )


def _pretrade(
    *,
    period: str,
    trade: milestone.SimulatedTrade,
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    chosen_scaled: tuple[milestone.SimulatedTrade, ...],
    records: tuple[Any, ...],
) -> v10.Pretrade:
    base = _BASE_PRETRADE(
        period=period,
        trade=trade,
        contexts=contexts,
        contextual_model=contextual_model,
        chosen_scaled=chosen_scaled,
        records=records,
    )
    point = replace(
        base.point,
        vector=(
            *base.point.vector,
            *_factor_features(chosen_scaled, trade=trade),
            *_competition_features(period=period, trade=trade),
            *_journey_features(chosen_scaled, trade=trade),
        ),
    )
    return replace(base, point=point)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[v10.RankDecision, ...]]:
    development = v10.router._load_selected(
        development_root,
        expected=v10.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = v10.router._load_selected(
        validation_root,
        expected=v10.EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    simultaneous.update(
        _simultaneous_map(
            period=v10.DEVELOPMENT_PERIOD,
            ledgers=development,
        )
    )
    simultaneous.update(
        _simultaneous_map(
            period="CONSUMED_VALIDATION_2022_2024",
            ledgers=validation,
        )
    )
    simultaneous.update(
        _simultaneous_map(
            period="CONSUMED_RESERVED_2020_2022",
            ledgers=reserved,
        )
    )

    original = v10._pretrade
    previous_simultaneous = dict(_SIMULTANEOUS)
    try:
        _SIMULTANEOUS.clear()
        _SIMULTANEOUS.update(simultaneous)
        v10._pretrade = _pretrade
        report, audits = v10.build_report(
            development_root,
            validation_root,
            reserved_root,
            development_validation_context_root,
            reserved_context_root,
        )
    finally:
        v10._pretrade = original
        _SIMULTANEOUS.clear()
        _SIMULTANEOUS.update(previous_simultaneous)

    report = dict(report)
    report.pop("all_windows_consumed_before_v10", None)
    report["identity"] = IDENTITY
    report["evaluation"] = (
        "FACTOR_JOURNEY_ENRICHED_DUAL_MODEL_WITH_FIXED_DEVELOPMENT_ROUTER"
    )
    report["all_windows_consumed_before_v11"] = True
    report["feature_delta_only_vs_v10"] = True
    report["ranker_hyperparameters_inherited_from_v10"] = True
    report["ranker_policies_inherited_from_v10"] = True
    report["open_exposure_uses_structural_unit_risk_only"] = True
    report["active_trade_outcomes_visible_to_features"] = False
    report["exact_timestamp_competition_bound"] = True
    report["simultaneous_peer_outcomes_visible_to_features"] = False
    report["competition_selects_winner"] = False
    report["simultaneous_factor_cluster_count"] = len(simultaneous)
    report["journey_outcomes_require_prior_close"] = True
    report["next_phase"] = (
        "FREEZE_V11_CANDIDATE_THEN_OPEN_2018_2020_FRESH_HOLDOUT"
        if int(report["robust_full_and_all_windows_dd6_policy_count"]) > 0
        else "ENGINEER_FACTOR_JOURNEY_CONFLICT_ABSTENTION_V12"
    )
    return report, audits


def write_report(
    report: dict[str, Any],
    audits: tuple[v10.RankDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-factor-journey-probe-ranker-v11.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-factor-journey-probe-ranker-v11-decisions.jsonl"
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
