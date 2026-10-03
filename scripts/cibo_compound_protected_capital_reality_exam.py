#!/usr/bin/env python3
"""Protected-capital reality exam for CIBO Compound and Compound Portfolio.

This is a measurement exam, not a population gate and not a certification gate.

Trigger:
- only terminal positive realized Core settlements create protected/reinvestible
  research capital;
- no Core loss creates compound capital or counts as a compound failure;
- a compound reinvestment may occur only at a later Core-selected opportunity
  when the protected pool can cover one legal minimum seed plus provider cost;
- QORE hard-risk and margin headroom from the historical predecision snapshot
  remain binding;
- outcome is never used to decide whether the incremental seed is admitted.

Surfaces:
- CIBO_COMPOUND: protected capital remains local to the originating Trader;
- COMPOUND_PORTFOLIO: protected capital is shared account-wide across Traders.

Measurements:
- exact chronological replay;
- walk-forward measurement in chronological folds;
- deterministic block-bootstrap Monte Carlo;
- adversarial stresses;
- min/max/capital-weighted reinvestment return constants.

Research only. No broker mutation, LIVE, Production, real capital, sizing
authority, Risk authority, certification authority, deployment authority, or
merge authority.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    CALIBRATION_MODE,
    ELIGIBLE_SIDE,
    MAX_CAPITAL_NEED_TO_BASE_RATIO,
    MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
    POLICY_ID,
    USD60_MAX_CAPITAL_NEED_USD,
    maximum_reinvestment_capital_need_usd,
)

TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
SIMULATIONS = 1000
WFO_FOLDS = 4
BASE_SEED = 20261003


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError("timestamp must be timezone-aware")
    return parsed


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise RuntimeError("non-finite Decimal")
    return result


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _nearest_rank(values: list[Decimal], percentile: int) -> Decimal:
    if not values:
        raise RuntimeError("cannot percentile empty values")
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return ordered[rank - 1]


def _minimum_seed_volume(row: dict[str, Any]) -> Decimal:
    opportunity = row["trader_opportunity"]
    minimum = _d(opportunity["minimum_volume"])
    steps_required = _d(opportunity["minimum_execution_steps"])
    raw = max(minimum, minimum * steps_required)
    step = _d(opportunity["volume_step"])
    volume = (raw / step).to_integral_value(rounding=ROUND_CEILING) * step
    if volume > _d(opportunity["maximum_volume"]):
        raise RuntimeError("minimum seed exceeds maximum volume")
    return volume


@dataclass(frozen=True, slots=True)
class CandidateEconomics:
    decision_at: datetime
    exit_at: datetime
    signal_fingerprint: str
    trader_id: str
    side: str
    volume: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    provider_cost_usd: Decimal
    capital_need_usd: Decimal
    gross_structural_outcome_r: Decimal
    incremental_pnl_usd: Decimal
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal


@dataclass(frozen=True, slots=True)
class ReinvestmentEpisode:
    episode_id: str
    decision_at: datetime
    exit_at: datetime
    signal_fingerprint: str
    trader_id: str
    side: str
    protected_inflow_since_prior_episode_usd: Decimal
    protected_before_usd: Decimal
    committed_before_usd: Decimal
    eligible_current_capital_usd: Decimal
    dynamic_capital_need_limit_usd: Decimal
    deployed_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    provider_cost_usd: Decimal
    incremental_pnl_usd: Decimal
    protected_after_settlement_usd: Decimal
    protected_pool_breach: bool
    source_scope: str

    @property
    def roi(self) -> Decimal:
        return self.incremental_pnl_usd / self.deployed_capital_usd

    @property
    def capital_multiplier(self) -> Decimal:
        return (self.deployed_capital_usd + self.incremental_pnl_usd) / (
            self.deployed_capital_usd
        )


def _candidate(row: dict[str, Any]) -> CandidateEconomics:
    settlement = row["settlement"]
    cma = row["cma"]
    opportunity = row["trader_opportunity"]
    provider = row["provider_economics_and_execution"]
    pre = row["market_predecision_state"]

    volume = _minimum_seed_volume(row)
    stop_per_volume = _d(opportunity["stop_loss_per_volume"])
    margin_per_volume = _d(opportunity["margin_per_volume"])
    stop_risk = volume * stop_per_volume
    margin = volume * margin_per_volume

    original_stop = _d(cma["candidate_stop_risk_usd"])
    original_volume = (
        Decimal(0)
        if stop_per_volume == 0
        else original_stop / stop_per_volume
    )
    cost_proxy = _d(provider["decision_provider_cost_proxy_usd"])
    cost_per_volume = (
        Decimal(0)
        if original_volume <= 0
        else cost_proxy / original_volume
    )
    cost = cost_per_volume * volume
    gross_r = _d(settlement["gross_structural_outcome_r"])
    pnl = gross_r * stop_risk - cost
    return CandidateEconomics(
        decision_at=_dt(row["market_decision_at"]),
        exit_at=_dt(settlement["capital_released_at"]),
        signal_fingerprint=str(row["signal_fingerprint"]),
        trader_id=str(row["trader_id"]),
        side=str(opportunity["side"]).lower(),
        volume=volume,
        stop_risk_usd=stop_risk,
        margin_usd=margin,
        provider_cost_usd=cost,
        capital_need_usd=stop_risk + cost,
        gross_structural_outcome_r=gross_r,
        incremental_pnl_usd=pnl,
        hard_risk_headroom_usd=_d(pre["hard_risk_headroom_usd"]),
        margin_headroom_usd=_d(pre["margin_headroom_usd"]),
    )


def _settled_rows(trace: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = trace.get("opportunities")
    if not isinstance(rows, list):
        raise RuntimeError("decision trace opportunities missing")
    result = tuple(
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("trader_id") in TRADERS
        and isinstance(row.get("settlement"), dict)
        and isinstance(row.get("cma"), dict)
        and isinstance(row.get("trader_opportunity"), dict)
        and isinstance(row.get("provider_economics_and_execution"), dict)
        and isinstance(row.get("market_predecision_state"), dict)
    )
    if not result:
        raise RuntimeError("no settled Core rows")
    return result


def _simulate_observed(
    rows: tuple[dict[str, Any], ...],
    *,
    shared: bool,
    eligible_sides: tuple[str, ...] = (ELIGIBLE_SIDE,),
    max_capital_need_to_current_capital_ratio: Decimal = (
        MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
    ),
) -> tuple[ReinvestmentEpisode, ...]:
    """Chronological protected-only incremental seed replay.

    Research callers may supply a preregistered side set and reinvestment ratio.
    The default remains the frozen CIBO policy. No candidate outcome is used by
    the admission decision.
    """

    normalized_sides = tuple(side.lower() for side in eligible_sides)
    if not normalized_sides or any(
        side not in ("long", "short") for side in normalized_sides
    ):
        raise ValueError("eligible_sides must contain only long/short")
    if len(set(normalized_sides)) != len(normalized_sides):
        raise ValueError("eligible_sides must not contain duplicates")
    if (
        not isinstance(max_capital_need_to_current_capital_ratio, Decimal)
        or not max_capital_need_to_current_capital_ratio.is_finite()
        or max_capital_need_to_current_capital_ratio <= 0
    ):
        raise ValueError("reinvestment ratio must be finite positive Decimal")

    core_settlements = sorted(
        rows,
        key=lambda row: (
            _dt(row["settlement"]["capital_released_at"]),
            str(row["signal_fingerprint"]),
        ),
    )
    decisions = sorted(
        rows,
        key=lambda row: (
            _dt(row["market_decision_at"]),
            str(row["signal_fingerprint"]),
        ),
    )
    core_index = 0
    realized_account_capital = (
        FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL.initial_capital_usd
    )

    protected: dict[str, Decimal] = defaultdict(Decimal)
    shared_protected = Decimal(0)
    open_rows: dict[str, tuple[CandidateEconomics, str]] = {}
    inflow_since_episode: dict[str, Decimal] = defaultdict(Decimal)
    shared_inflow_since_episode = Decimal(0)
    episodes: list[ReinvestmentEpisode] = []

    def scope_key(trader: str) -> str:
        return "ACCOUNT_WIDE" if shared else trader

    def settle_incremental_until(clock: datetime) -> None:
        nonlocal shared_protected, realized_account_capital
        due = sorted(
            (
                (signal, item)
                for signal, item in open_rows.items()
                if item[0].exit_at <= clock
            ),
            key=lambda pair: (pair[1][0].exit_at, pair[0]),
        )
        for signal, (candidate, key) in due:
            del open_rows[signal]
            if shared:
                before = shared_protected
            else:
                before = protected[key]
            raw_after = before + candidate.incremental_pnl_usd
            breached = raw_after < 0
            after = max(Decimal(0), raw_after)
            if shared:
                shared_protected = after
            else:
                protected[key] = after
            protected_applied_pnl = max(
                candidate.incremental_pnl_usd,
                -before,
            )
            realized_account_capital += protected_applied_pnl

            for index in range(len(episodes) - 1, -1, -1):
                episode = episodes[index]
                if episode.signal_fingerprint == signal:
                    episodes[index] = replace(
                        episode,
                        protected_after_settlement_usd=after,
                        protected_pool_breach=breached,
                    )
                    break

    for row in decisions:
        candidate = _candidate(row)
        clock = candidate.decision_at
        settle_incremental_until(clock)

        while (
            core_index < len(core_settlements)
            and _dt(
                core_settlements[core_index]["settlement"]["capital_released_at"]
            )
            <= clock
        ):
            core = core_settlements[core_index]
            core_index += 1
            realized = _d(core["settlement"]["realized_net_pnl_usd"])
            realized_account_capital += realized
            if realized <= 0:
                # Core losses are irrelevant to Compound activation. They do not
                # create protected capital and are not counted as Compound loss.
                continue
            trader = str(core["trader_id"])
            if shared:
                shared_protected += realized
                shared_inflow_since_episode += realized
            else:
                protected[trader] += realized
                inflow_since_episode[trader] += realized

        if realized_account_capital <= 0:
            continue
        dynamic_limit = (
            realized_account_capital
            * max_capital_need_to_current_capital_ratio
        )
        if candidate.side not in normalized_sides:
            continue
        if candidate.capital_need_usd > dynamic_limit:
            continue

        key = scope_key(candidate.trader_id)
        available = shared_protected if shared else protected[key]
        committed = sum(
            item[0].capital_need_usd
            for item in open_rows.values()
            if shared or item[1] == key
        )
        free_protected = max(Decimal(0), available - committed)

        if candidate.stop_risk_usd > candidate.hard_risk_headroom_usd:
            continue
        if candidate.margin_usd > candidate.margin_headroom_usd:
            continue
        if candidate.capital_need_usd > free_protected:
            continue

        inflow = (
            shared_inflow_since_episode
            if shared
            else inflow_since_episode[key]
        )
        if shared:
            shared_inflow_since_episode = Decimal(0)
        else:
            inflow_since_episode[key] = Decimal(0)

        episode = ReinvestmentEpisode(
            episode_id=(
                ("portfolio" if shared else candidate.trader_id.lower())
                + ":"
                + candidate.signal_fingerprint
            ),
            decision_at=candidate.decision_at,
            exit_at=candidate.exit_at,
            signal_fingerprint=candidate.signal_fingerprint,
            trader_id=candidate.trader_id,
            side=candidate.side,
            protected_inflow_since_prior_episode_usd=inflow,
            protected_before_usd=available,
            committed_before_usd=committed,
            eligible_current_capital_usd=realized_account_capital,
            dynamic_capital_need_limit_usd=dynamic_limit,
            deployed_capital_usd=candidate.capital_need_usd,
            stop_risk_usd=candidate.stop_risk_usd,
            margin_usd=candidate.margin_usd,
            provider_cost_usd=candidate.provider_cost_usd,
            incremental_pnl_usd=candidate.incremental_pnl_usd,
            protected_after_settlement_usd=available,
            protected_pool_breach=False,
            source_scope=key,
        )
        episodes.append(episode)
        open_rows[candidate.signal_fingerprint] = (candidate, key)

    if open_rows:
        settle_incremental_until(max(item[0].exit_at for item in open_rows.values()))

    return tuple(
        sorted(
            episodes,
            key=lambda item: (
                item.decision_at,
                item.exit_at,
                item.episode_id,
            ),
        )
    )


def _metrics(
    episodes: tuple[ReinvestmentEpisode, ...],
    *,
    label: str,
) -> dict[str, Any]:
    if not episodes:
        return {
            "label": label,
            "episode_count": 0,
            "status": "NO_PROTECTED_REINVESTMENT",
        }

    pnl = [item.incremental_pnl_usd for item in episodes]
    deployed = [item.deployed_capital_usd for item in episodes]
    positives = sum((value for value in pnl if value > 0), Decimal(0))
    losses = -sum((value for value in pnl if value < 0), Decimal(0))
    weighted_roi = sum(pnl, Decimal(0)) / sum(deployed, Decimal(0))
    rois = [item.roi for item in episodes]

    running = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for item in sorted(episodes, key=lambda row: (row.exit_at, row.episode_id)):
        running += item.incremental_pnl_usd
        peak = max(peak, running)
        max_dd = max(max_dd, peak - running)

    by_trader: dict[str, Decimal] = defaultdict(Decimal)
    entries: dict[str, int] = defaultdict(int)
    by_side: dict[str, Decimal] = defaultdict(Decimal)
    side_entries: dict[str, int] = defaultdict(int)
    for item in episodes:
        by_trader[item.trader_id] += item.incremental_pnl_usd
        entries[item.trader_id] += 1
        by_side[item.side] += item.incremental_pnl_usd
        side_entries[item.side] += 1

    return {
        "label": label,
        "status": "MEASURED",
        "episode_count": len(episodes),
        "first_decision_at": min(item.decision_at for item in episodes).isoformat(),
        "last_exit_at": max(item.exit_at for item in episodes).isoformat(),
        "total_protected_inflow_usd": _fmt(
            sum(
                (
                    item.protected_inflow_since_prior_episode_usd
                    for item in episodes
                ),
                Decimal(0),
            )
        ),
        "total_deployed_protected_capital_usd": _fmt(sum(deployed, Decimal(0))),
        "incremental_realized_pnl_usd": _fmt(sum(pnl, Decimal(0))),
        "gross_profit_usd": _fmt(positives),
        "gross_loss_usd": _fmt(losses),
        "profit_factor": None if losses == 0 else _fmt(positives / losses),
        "max_incremental_drawdown_usd": _fmt(max_dd),
        "protected_pool_breach_count": sum(
            int(item.protected_pool_breach) for item in episodes
        ),
        "minimum_eligible_current_capital_usd": _fmt(
            min(item.eligible_current_capital_usd for item in episodes)
        ),
        "maximum_eligible_current_capital_usd": _fmt(
            max(item.eligible_current_capital_usd for item in episodes)
        ),
        "minimum_dynamic_capital_need_limit_usd": _fmt(
            min(item.dynamic_capital_need_limit_usd for item in episodes)
        ),
        "maximum_dynamic_capital_need_limit_usd": _fmt(
            max(item.dynamic_capital_need_limit_usd for item in episodes)
        ),
        "minimum_roi": _fmt(min(rois)),
        "maximum_roi": _fmt(max(rois)),
        "weighted_average_roi": _fmt(weighted_roi),
        "minimum_capital_multiplier": _fmt(
            min(item.capital_multiplier for item in episodes)
        ),
        "maximum_capital_multiplier": _fmt(
            max(item.capital_multiplier for item in episodes)
        ),
        "weighted_average_capital_multiplier": _fmt(
            Decimal(1) + weighted_roi
        ),
        "trader_incremental_pnl_usd": {
            trader: _fmt(value)
            for trader, value in sorted(by_trader.items())
        },
        "trader_reinvestment_entries": dict(sorted(entries.items())),
        "side_incremental_pnl_usd": {
            side: _fmt(value)
            for side, value in sorted(by_side.items())
        },
        "side_reinvestment_entries": dict(sorted(side_entries.items())),
    }


def _walk_forward(
    episodes: tuple[ReinvestmentEpisode, ...],
    *,
    label: str,
) -> dict[str, Any]:
    if not episodes:
        return {
            "label": label,
            "fold_count": 0,
            "folds": [],
            "measurement_only": True,
        }
    count = min(WFO_FOLDS, len(episodes))
    base = len(episodes) // count
    remainder = len(episodes) % count
    folds: list[dict[str, Any]] = []
    cursor = 0
    for index in range(count):
        size = base + (1 if index < remainder else 0)
        rows = episodes[cursor : cursor + size]
        cursor += size
        metric = _metrics(rows, label=f"{label}:WF{index + 1}")
        metric["fold_id"] = f"WF{index + 1}"
        folds.append(metric)
    weighted = (
        sum(
            (
                _d(item["incremental_realized_pnl_usd"])
                for item in folds
                if item["status"] == "MEASURED"
            ),
            Decimal(0),
        )
        / sum(
            (
                _d(item["total_deployed_protected_capital_usd"])
                for item in folds
                if item["status"] == "MEASURED"
            ),
            Decimal(0),
        )
    )
    return {
        "label": label,
        "fold_count": count,
        "folds": folds,
        "minimum_fold_roi": _fmt(
            min(_d(item["weighted_average_roi"]) for item in folds)
        ),
        "maximum_fold_roi": _fmt(
            max(_d(item["weighted_average_roi"]) for item in folds)
        ),
        "weighted_average_roi": _fmt(weighted),
        "measurement_only": True,
        "training_or_tuning_performed": False,
    }


def _block_bootstrap(
    episodes: tuple[ReinvestmentEpisode, ...],
    *,
    label: str,
) -> dict[str, Any]:
    if not episodes:
        return {
            "label": label,
            "simulation_count": 0,
            "status": "NO_PROTECTED_REINVESTMENT",
        }

    n = len(episodes)
    block = max(1, int(math.sqrt(n)))
    blocks = [
        episodes[index : min(n, index + block)]
        for index in range(0, n, block)
    ]

    endings: list[Decimal] = []
    pnls: list[Decimal] = []
    executed_counts: list[int] = []
    breach_paths = 0
    rng = random.Random(BASE_SEED + (17 if label == "COMPOUND_PORTFOLIO" else 0))

    for _simulation in range(SIMULATIONS):
        sample: list[ReinvestmentEpisode] = []
        while len(sample) < n:
            sample.extend(rng.choice(blocks))
        sample = sample[:n]

        protected = Decimal(0)
        pnl_total = Decimal(0)
        executed = 0
        breached = False
        for item in sample:
            protected += item.protected_inflow_since_prior_episode_usd
            if protected < item.deployed_capital_usd:
                continue
            executed += 1
            pnl_total += item.incremental_pnl_usd
            protected += item.incremental_pnl_usd
            if protected < 0:
                breached = True
                protected = Decimal(0)
        endings.append(protected)
        pnls.append(pnl_total)
        executed_counts.append(executed)
        breach_paths += int(breached)

    return {
        "label": label,
        "status": "MEASURED",
        "simulation_count": SIMULATIONS,
        "block_length": block,
        "minimum_ending_protected_capital_usd": _fmt(min(endings)),
        "p05_ending_protected_capital_usd": _fmt(_nearest_rank(endings, 5)),
        "median_ending_protected_capital_usd": _fmt(_nearest_rank(endings, 50)),
        "p95_ending_protected_capital_usd": _fmt(_nearest_rank(endings, 95)),
        "maximum_ending_protected_capital_usd": _fmt(max(endings)),
        "minimum_incremental_pnl_usd": _fmt(min(pnls)),
        "p05_incremental_pnl_usd": _fmt(_nearest_rank(pnls, 5)),
        "median_incremental_pnl_usd": _fmt(_nearest_rank(pnls, 50)),
        "p95_incremental_pnl_usd": _fmt(_nearest_rank(pnls, 95)),
        "maximum_incremental_pnl_usd": _fmt(max(pnls)),
        "minimum_executed_reinvestments": min(executed_counts),
        "maximum_executed_reinvestments": max(executed_counts),
        "protected_pool_breach_paths": breach_paths,
        "market_probability_claimed": False,
        "measurement_only": True,
    }


def _stress(
    episodes: tuple[ReinvestmentEpisode, ...],
    *,
    label: str,
) -> dict[str, Any]:
    if not episodes:
        return {"label": label, "scenario_count": 0, "scenarios": []}

    def run(
        rows: list[ReinvestmentEpisode],
        *,
        pnl_transform=lambda item: item.incremental_pnl_usd,
        need_multiplier: Decimal = Decimal(1),
        margin_multiplier: Decimal = Decimal(1),
    ) -> dict[str, Any]:
        protected = Decimal(0)
        pnl_total = Decimal(0)
        executed = 0
        rejected = 0
        breach = False
        for item in rows:
            protected += item.protected_inflow_since_prior_episode_usd
            need = item.deployed_capital_usd * need_multiplier
            if item.margin_usd * margin_multiplier > (
                item.margin_usd + item.protected_before_usd
            ):
                rejected += 1
                continue
            if protected < need:
                rejected += 1
                continue
            pnl = pnl_transform(item)
            executed += 1
            pnl_total += pnl
            protected += pnl
            if protected < 0:
                breach = True
                protected = Decimal(0)
        return {
            "ending_protected_capital_usd": _fmt(protected),
            "incremental_pnl_usd": _fmt(pnl_total),
            "executed_count": executed,
            "rejected_count": rejected,
            "protected_pool_breach": breach,
        }

    chronological = list(episodes)
    losses_first = sorted(
        episodes,
        key=lambda item: (
            item.incremental_pnl_usd >= 0,
            item.incremental_pnl_usd,
            item.decision_at,
        ),
    )
    gen_losses_early = sorted(
        episodes,
        key=lambda item: (
            item.incremental_pnl_usd >= 0,
            -abs(item.incremental_pnl_usd),
            item.decision_at,
        ),
    )

    scenarios = {
        "LOSSES_FIRST": run(losses_first),
        "WINNER_DROUGHT": run(
            chronological,
            pnl_transform=lambda item: min(
                Decimal(0), item.incremental_pnl_usd
            ),
        ),
        "CORRELATION_CONVERGENCE": run(
            chronological,
            need_multiplier=Decimal("2"),
        ),
        "MARGIN_HIKE_50PCT": run(
            chronological,
            margin_multiplier=Decimal("1.5"),
        ),
        "CAPITAL_LOCKUP_50PCT": run(
            chronological,
            need_multiplier=Decimal("1.5"),
        ),
        "GAP_AND_SLIPPAGE_25PCT_RISK": run(
            chronological,
            pnl_transform=lambda item: (
                item.incremental_pnl_usd
                - item.stop_risk_usd * Decimal("0.25")
            ),
        ),
        "GEN_N_LOSSES_EARLY": run(gen_losses_early),
    }
    return {
        "label": label,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "measurement_only": True,
        "market_probability_claimed": False,
    }


def _episode_payload(item: ReinvestmentEpisode) -> dict[str, Any]:
    raw = asdict(item)
    for key, value in tuple(raw.items()):
        if isinstance(value, Decimal):
            raw[key] = _fmt(value)
        elif isinstance(value, datetime):
            raw[key] = value.isoformat()
    raw["roi"] = _fmt(item.roi)
    raw["capital_multiplier"] = _fmt(item.capital_multiplier)
    return raw


def _surface(
    rows: tuple[dict[str, Any], ...],
    *,
    shared: bool,
    eligible_sides: tuple[str, ...] = (ELIGIBLE_SIDE,),
    max_capital_need_to_current_capital_ratio: Decimal = (
        MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
    ),
) -> dict[str, Any]:
    label = "COMPOUND_PORTFOLIO" if shared else "CIBO_COMPOUND"
    episodes = _simulate_observed(
        rows,
        shared=shared,
        eligible_sides=eligible_sides,
        max_capital_need_to_current_capital_ratio=(
            max_capital_need_to_current_capital_ratio
        ),
    )
    return {
        "surface": label,
        "trigger": "CAUSALLY_PRIOR_PROTECTED_REALIZED_CAPITAL_ONLY",
        "eligible_sides": list(eligible_sides),
        "max_capital_need_to_current_capital_ratio": _fmt(
            max_capital_need_to_current_capital_ratio
        ),
        "observed": _metrics(episodes, label=label),
        "walk_forward": _walk_forward(episodes, label=label),
        "monte_carlo": _block_bootstrap(episodes, label=label),
        "stress": _stress(episodes, label=label),
        "episodes": [_episode_payload(item) for item in episodes],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    rows = _settled_rows(trace)

    local = _surface(rows, shared=False)
    portfolio = _surface(rows, shared=True)
    report = {
        "schema": "qore.cibo.compound-protected-capital-reality-exam.v1",
        "source_trace_sha256": trace.get("trace_sha256"),
        "source_settled_core_rows": len(rows),
        "calibrated_reinvestment_policy": {
            "policy_id": POLICY_ID,
            "calibration_mode": CALIBRATION_MODE,
            "eligible_side": ELIGIBLE_SIDE,
            "max_capital_need_to_current_capital_ratio": _fmt(
                MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO
            ),
            "max_capital_need_to_base_ratio": _fmt(
                MAX_CAPITAL_NEED_TO_BASE_RATIO
            ),
            "ratio_basis": "CURRENT_REALIZED_ACCOUNT_CAPITAL_BEFORE_DECISION",
            "dynamic_scaling": True,
            "opening_balance_is_static_basis": False,
            "usd60_reference_max_capital_need_usd": _fmt(
                USD60_MAX_CAPITAL_NEED_USD
            ),
            "usd100_reference_max_capital_need_usd": _fmt(
                maximum_reinvestment_capital_need_usd(Decimal("100"))
            ),
            "population_gate_used": False,
            "outcome_used_at_decision": False,
            "forward_generalization_claimed": False,
        },
        "cibo_compound": local,
        "compound_portfolio": portfolio,
        "governance": {
            "measurement_only": True,
            "population_gate_used": False,
            "function_availability_conditioned_on_population": False,
            "core_losses_create_compound_capital": False,
            "protected_capital_required_before_reinvestment": True,
            "outcome_used_for_admission": False,
            "broker_mutation": False,
            "orders": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
            "merge_authority": False,
            "dynamic_current_capital_scaling": True,
            "opening_base_capital_used_as_static_reinvestment_basis": False,
            "owner_global_status": "REJECT",
        },
    }

    violations: list[str] = []
    for name, surface in (
        ("CIBO_COMPOUND", local),
        ("COMPOUND_PORTFOLIO", portfolio),
    ):
        observed = surface["observed"]
        if observed["status"] != "MEASURED":
            violations.append(f"{name}:NO_PROTECTED_REINVESTMENTS")
        if observed["episode_count"] <= 0:
            violations.append(f"{name}:ZERO_EPISODES")
        if surface["walk_forward"]["fold_count"] <= 0:
            violations.append(f"{name}:WFO_NOT_RUN")
        if surface["monte_carlo"]["simulation_count"] != SIMULATIONS:
            violations.append(f"{name}:MONTE_CARLO_COUNT_DRIFT")
        if surface["stress"]["scenario_count"] != 7:
            violations.append(f"{name}:STRESS_FAMILY_COUNT_DRIFT")
        if _d(observed["incremental_realized_pnl_usd"]) <= 0:
            violations.append(f"{name}:OBSERVED_PNL_NON_POSITIVE")
        if _d(observed["weighted_average_roi"]) <= 0:
            violations.append(f"{name}:OBSERVED_WEIGHTED_ROI_NON_POSITIVE")
        if observed["protected_pool_breach_count"] != 0:
            violations.append(f"{name}:OBSERVED_PROTECTED_POOL_BREACH")
        if any(
            _d(fold["weighted_average_roi"]) <= 0
            for fold in surface["walk_forward"]["folds"]
        ):
            violations.append(f"{name}:NON_POSITIVE_WFO_FOLD")
        if _d(surface["monte_carlo"]["median_incremental_pnl_usd"]) <= 0:
            violations.append(f"{name}:MONTE_CARLO_MEDIAN_NON_POSITIVE")
        if surface["monte_carlo"]["protected_pool_breach_paths"] != 0:
            violations.append(f"{name}:MONTE_CARLO_PROTECTED_POOL_BREACH")

    report["gate_verdict"] = {
        "status": "PASS" if not violations else "REJECT",
        "violations": violations,
        "artifact_emitted_before_failure": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "gate_verdict": report["gate_verdict"],
                "cibo_compound": local["observed"],
                "compound_portfolio": portfolio["observed"],
                "cibo_compound_mc": local["monte_carlo"],
                "compound_portfolio_mc": portfolio["monte_carlo"],
                "calibrated_reinvestment_policy": report[
                    "calibrated_reinvestment_policy"
                ],
            },
            sort_keys=True,
        )
    )
    if violations:
        raise RuntimeError("compound reality gate rejected: " + ", ".join(violations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
