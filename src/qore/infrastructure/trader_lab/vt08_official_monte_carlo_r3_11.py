"""Official VT-08 R3.11 paired Monte Carlo over consumed evidence only.

The experiment freezes A, GBPJPY, and B before resampling.  It uses a common
20-business-day moving-block draw for all three portfolios, replays the frozen
50 bps fixed-loss / 150 bps heat policy chronologically, and refuses any trade
from the protected pre-2022-08-13 interval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import fmean

from qore.infrastructure.deterministic_random import DeterministicRandom
from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BASELINE_RUN_ID,
    CONSUMED_EVIDENCE_FLOOR,
    FRESH_RUN_ID,
    PRIMARY_PER_TRADE_RISK_BPS,
    PRIMARY_PORTFOLIO_HEAT_BPS,
    PRIMARY_STARTING_EQUITY_USD,
    BrokerVolumeConstraints,
    TradeObservation,
    _build_time_index,
    _gross_quote_pnl,
    broker_valid_fixed_risk_quantity,
    load_consumed_evidence,
    quote_to_usd_factor,
)

SCHEMA = "qore.vt08.r3.11.official-paired-monte-carlo.v1"
PATHS = 10_000
HORIZON_DAYS = 250
BLOCK_DAYS = 20
SEED = 20260912
PRIMARY_COST_BPS = Decimal("0.50")
PORTFOLIOS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "A_CORE": (("AUDJPY", "short"), ("GBPUSD", "short")),
    "GBPJPY_RETURN_ENHANCER": (("GBPJPY", "long"), ("GBPJPY", "short")),
    "B_COMBINED_PORTFOLIO": (
        ("AUDJPY", "short"),
        ("GBPUSD", "short"),
        ("GBPJPY", "long"),
        ("GBPJPY", "short"),
    ),
}
INPUT_ARTIFACTS: Mapping[int, tuple[tuple[int, str], ...]] = {
    BASELINE_RUN_ID: (
        (10298237222, "sha256:2dd0a04d158ecebd260b47b186d3f6623888a58c678f1c668c72c05d135cebf2"),
        (10298219011, "sha256:a9eddd96e6604088497a39f0d59f53505c0068c035b984543fd5d373624282ec"),
        (10297959191, "sha256:b7b1d4863a9a4f666297f7b5bbf934bd13918acf505c0e83b71227932bead1b1"),
        (10297938872, "sha256:a987c9a054b219b4a10035c184bc297d786bf10cbf0e75bf886b7f614127484c"),
        (10297919242, "sha256:6752051c9bfc4a046aeb6bb7d65634c0c793cc20e9e6fb227a90759708c99e3c"),
        (10297764571, "sha256:7111ef1a0a1ea8b237f5d4b30bd0e168253e8ed40ddb9ce7d7740082a3ee2659"),
        (10297429461, "sha256:df5cbda261aa742f077bd06125138b416bde5e7734fe7c98315f4c1bc9f7c117"),
        (10297393089, "sha256:5b321303d411bb897e7649a38cf47e98492c0a99955ac56709539eda2f85a430"),
    ),
    FRESH_RUN_ID: (
        (10302786854, "sha256:106b2023188dab11b6c3dcec31239cf5e1622d304f8799dba14db0d37615a03f"),
        (10302752090, "sha256:ef96426c592cdecdb4c84d8e287c26c83f4faede0ba2982291557c24e21814c0"),
        (10302581855, "sha256:63025f620850287f30a898775fcaf0da87b6a5ab6b64cf1af3808bd1fe262df0"),
        (10302398528, "sha256:bac5c18d7aa04c0627771f4a8f8b9852c9456e0a613ee526c259616cf79fb448"),
        (10302377545, "sha256:e5fa0719c714a3f764147b2a90433094e25d88dd3a04baa44302c26070db65bb"),
        (10302124333, "sha256:ee9f811254e21f4cceafaa8805dd12543bca8064cdc4028ad583ed90b5cbf9fa"),
        (10302054131, "sha256:8211dd0dd948b0618116ea9dcfcdc1f43eb91bb8feeea3aa0d89574aa72ed7d1"),
        (10302043747, "sha256:f7bd8c4c30dbed72f731d7a6650dd041c76ca47c6bc5ebb7cd29825072a4bdf3"),
        (10302024263, "sha256:9ebfaf78de8ab58e3af33e6e1da160a0f7ef495d62b9b4384593a9cf1571c7e5"),
    ),
}


class OfficialMonteCarloError(ValueError):
    """Raised when the frozen experiment or its evidence is invalid."""


@dataclass(frozen=True, slots=True)
class PreparedTrade:
    source: TradeObservation
    entry_offset: timedelta
    duration: timedelta
    per_unit_loss_usd: Decimal
    per_unit_net_pnl_usd: Decimal
    constraints: BrokerVolumeConstraints


@dataclass(frozen=True, slots=True)
class PreparedDay:
    source_day: date
    trades: tuple[PreparedTrade, ...]


@dataclass(frozen=True, slots=True)
class PathMetrics:
    terminal_return: float
    max_drawdown: float
    losing_streak: int
    underwater_days: int
    max_concurrency: int
    allow: int
    reduce: int
    reject: int
    heat_interactions: int
    heat_violations: int
    ruin: bool


@dataclass(slots=True)
class _Position:
    exit_at: datetime
    pnl_usd: Decimal
    bounded_loss_usd: Decimal


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _scope_membership(trade: TradeObservation, portfolio: str) -> bool:
    return (trade.symbol, trade.side) in PORTFOLIOS[portfolio]


def _business_days(start: date, end: date) -> tuple[date, ...]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def prepare_daily_evidence(
    trades: Sequence[TradeObservation],
    constraints: Mapping[str, BrokerVolumeConstraints],
    conversion_bars: Mapping[str, Mapping[datetime, Decimal]],
    *,
    cost_bps: Decimal,
) -> tuple[PreparedDay, ...]:
    selected = [trade for trade in trades if _scope_membership(trade, "B_COMBINED_PORTFOLIO")]
    if not selected:
        raise OfficialMonteCarloError("frozen portfolios have no consumed trades")
    if any(trade.signal_at < CONSUMED_EVIDENCE_FLOOR for trade in selected):
        raise OfficialMonteCarloError("protected holdout trade encountered")
    indices = {symbol: _build_time_index(rows) for symbol, rows in conversion_bars.items()}
    grouped: dict[date, list[PreparedTrade]] = {}
    for trade in selected:
        entry_factor = quote_to_usd_factor(
            trade.symbol,
            trade.signal_at,
            instrument_price=trade.entry,
            indices=indices,
        )
        exit_factor = quote_to_usd_factor(
            trade.symbol,
            trade.exited_at,
            instrument_price=trade.exit_price,
            indices=indices,
        )
        per_unit_loss = trade.risk_price * entry_factor
        per_unit_gross = _gross_quote_pnl(trade, Decimal(1)) * exit_factor
        per_unit_cost = trade.entry * cost_bps / Decimal(10_000) * entry_factor
        day = trade.signal_at.date()
        midnight = datetime.combine(day, datetime.min.time(), tzinfo=trade.signal_at.tzinfo)
        grouped.setdefault(day, []).append(
            PreparedTrade(
                source=trade,
                entry_offset=trade.signal_at - midnight,
                duration=trade.exited_at - trade.signal_at,
                per_unit_loss_usd=per_unit_loss,
                per_unit_net_pnl_usd=per_unit_gross - per_unit_cost,
                constraints=constraints[trade.symbol],
            )
        )
    first = min(grouped)
    last = max(grouped)
    return tuple(
        PreparedDay(
            source_day=day,
            trades=tuple(
                sorted(
                    grouped.get(day, ()),
                    key=lambda item: (item.entry_offset, item.source.symbol, item.source.side),
                )
            ),
        )
        for day in _business_days(first, last)
    )


def paired_block_indices(
    observed_days: int,
    *,
    paths: int,
    horizon_days: int,
    block_days: int,
    seed: int,
) -> tuple[tuple[int, ...], ...]:
    if paths <= 0 or horizon_days <= 0 or block_days <= 0:
        raise OfficialMonteCarloError("paths, horizon, and block must be positive")
    if block_days > observed_days:
        raise OfficialMonteCarloError("block exceeds consumed daily series")
    rng = DeterministicRandom(seed)
    last_start = observed_days - block_days
    result: list[tuple[int, ...]] = []
    for _ in range(paths):
        indices: list[int] = []
        while len(indices) < horizon_days:
            start = rng.randint(0, last_start)
            indices.extend(range(start, start + block_days))
        result.append(tuple(indices[:horizon_days]))
    return tuple(result)


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise OfficialMonteCarloError("distribution cannot be empty")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def simulate_portfolio_path(
    days: Sequence[PreparedDay],
    indices: Sequence[int],
    *,
    portfolio: str,
) -> PathMetrics:
    if portfolio not in PORTFOLIOS:
        raise OfficialMonteCarloError(f"unknown frozen portfolio: {portfolio}")
    starting = PRIMARY_STARTING_EQUITY_USD
    equity = starting
    peak = starting
    max_drawdown = Decimal(0)
    ruin = False
    open_positions: list[_Position] = []
    losing = 0
    max_losing = 0
    underwater = 0
    max_underwater = 0
    max_concurrency = 0
    counts = {"ALLOW": 0, "REDUCE": 0, "REJECT": 0}
    heat_interactions = 0
    heat_violations = 0
    epoch = datetime(2000, 1, 3, tzinfo=UTC)

    def close_due(cutoff: datetime) -> None:
        nonlocal equity, peak, losing, max_losing, open_positions, max_drawdown, ruin
        due = sorted(
            (item for item in open_positions if item.exit_at <= cutoff),
            key=lambda item: item.exit_at,
        )
        for item in due:
            equity += item.pnl_usd
            if item.pnl_usd < 0:
                losing += 1
                max_losing = max(max_losing, losing)
            elif item.pnl_usd > 0:
                losing = 0
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
            ruin = ruin or equity <= 0
        due_ids = {id(item) for item in due}
        open_positions = [item for item in open_positions if id(item) not in due_ids]

    for simulated_day, source_index in enumerate(indices):
        day_start = epoch + timedelta(days=simulated_day)
        for trade in days[source_index].trades:
            if not _scope_membership(trade.source, portfolio):
                continue
            entry_at = day_start + trade.entry_offset
            close_due(entry_at)
            desired = equity * Decimal(PRIMARY_PER_TRADE_RISK_BPS) / Decimal(10_000)
            heat_limit = equity * Decimal(PRIMARY_PORTFOLIO_HEAT_BPS) / Decimal(10_000)
            committed = sum((item.bounded_loss_usd for item in open_positions), Decimal(0))
            available = heat_limit - committed
            if available <= 0:
                counts["REJECT"] += 1
                heat_interactions += 1
                continue
            requested = min(desired, available)
            pre_reduced = requested < desired
            if pre_reduced:
                heat_interactions += 1
            outcome, quantity, bounded = broker_valid_fixed_risk_quantity(
                desired_loss_usd=requested,
                per_unit_loss_usd=trade.per_unit_loss_usd,
                constraints=trade.constraints,
            )
            if outcome == "REJECT":
                counts["REJECT"] += 1
                continue
            outcome = "REDUCE" if pre_reduced or outcome == "REDUCE" else "ALLOW"
            counts[outcome] += 1
            open_positions.append(
                _Position(entry_at + trade.duration, quantity * trade.per_unit_net_pnl_usd, bounded)
            )
            max_concurrency = max(max_concurrency, len(open_positions))
            total_heat = sum((item.bounded_loss_usd for item in open_positions), Decimal(0))
            if total_heat > heat_limit + Decimal("0.00000001"):
                heat_violations += 1
            adverse_equity = equity - total_heat
            max_drawdown = max(max_drawdown, (peak - adverse_equity) / peak)
            ruin = ruin or adverse_equity <= 0
        close_due(day_start + timedelta(days=1))
        if equity < peak:
            underwater += 1
            max_underwater = max(max_underwater, underwater)
        else:
            underwater = 0
    close_due(datetime.max.replace(tzinfo=epoch.tzinfo))
    return PathMetrics(
        terminal_return=float(equity / starting - Decimal(1)),
        max_drawdown=float(max_drawdown),
        losing_streak=max_losing,
        underwater_days=max_underwater,
        max_concurrency=max_concurrency,
        allow=counts["ALLOW"],
        reduce=counts["REDUCE"],
        reject=counts["REJECT"],
        heat_interactions=heat_interactions,
        heat_violations=heat_violations,
        ruin=ruin,
    )


def _distribution(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": fmean(values),
        "p05": _percentile(values, 0.05),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
    }


def _summarize(results: Sequence[PathMetrics]) -> dict[str, object]:
    terminal = [item.terminal_return for item in results]
    drawdown = [item.max_drawdown for item in results]
    concurrency = [float(item.max_concurrency) for item in results]
    return {
        "terminal_return": _distribution(terminal),
        "probability_terminal_positive": sum(value > 0 for value in terminal) / len(terminal),
        "terminal_equity_usd": _distribution([100_000.0 * (1.0 + value) for value in terminal]),
        "maximum_drawdown": _distribution(drawdown),
        "losing_streak": _distribution([float(item.losing_streak) for item in results]),
        "underwater_duration_days": _distribution(
            [float(item.underwater_days) for item in results]
        ),
        "max_concurrency": {**_distribution(concurrency), "maximum_observed": max(concurrency)},
        "risk_outcomes_total": {
            "ALLOW": sum(item.allow for item in results),
            "REDUCE": sum(item.reduce for item in results),
            "REJECT": sum(item.reject for item in results),
        },
        "heat_cap_interactions_total": sum(item.heat_interactions for item in results),
        "heat_violations_total": sum(item.heat_violations for item in results),
        "ruin_probability": sum(item.ruin for item in results) / len(results),
        "ruin_definition": "terminal or intrapath equity at or below zero",
        "account_containment_probability": None,
        "account_containment_definition": (
            "not reported: no additional account-containment threshold was frozen"
        ),
    }


def _file_digests(roots: Sequence[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.rglob("*.json")):
            key = f"{root.name}/{path.relative_to(root)}"
            result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _evidence_fingerprints(roots: Sequence[Path]) -> dict[str, list[str]]:
    methodology: set[str] = set()
    source: set[str] = set()
    for root in roots:
        for path in root.rglob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            for key in ("methodology_fingerprint", "parent_methodology_fingerprint"):
                value = payload.get(key)
                if isinstance(value, str):
                    methodology.add(value)
            value = payload.get("source_contract_fingerprint")
            if isinstance(value, str):
                source.add(value)
    return {"methodology": sorted(methodology), "source_contract": sorted(source)}


def build_official_report(
    baseline_root: Path,
    fresh_root: Path,
    *,
    git_sha: str,
    generated_at: str,
    paths: int = PATHS,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise OfficialMonteCarloError("git SHA must be exact")
    trades, constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    if len(trades) != 809:
        raise OfficialMonteCarloError(f"expected 809 consumed trades, found {len(trades)}")
    sample_counts = {
        name: sum(_scope_membership(trade, name) for trade in trades) for name in PORTFOLIOS
    }
    if sample_counts != {"A_CORE": 117, "GBPJPY_RETURN_ENHANCER": 112, "B_COMBINED_PORTFOLIO": 229}:
        raise OfficialMonteCarloError(f"frozen portfolio cardinality changed: {sample_counts}")
    prepared_primary = prepare_daily_evidence(trades, constraints, bars, cost_bps=PRIMARY_COST_BPS)
    prepared_gross = prepare_daily_evidence(trades, constraints, bars, cost_bps=Decimal(0))
    draws = paired_block_indices(
        len(prepared_primary),
        paths=paths,
        horizon_days=HORIZON_DAYS,
        block_days=BLOCK_DAYS,
        seed=SEED,
    )
    primary_raw: dict[str, list[PathMetrics]] = {name: [] for name in PORTFOLIOS}
    gross_raw: dict[str, list[PathMetrics]] = {name: [] for name in PORTFOLIOS}
    for indices in draws:
        for name in PORTFOLIOS:
            primary_raw[name].append(
                simulate_portfolio_path(prepared_primary, indices, portfolio=name)
            )
            gross_raw[name].append(
                simulate_portfolio_path(prepared_gross, indices, portfolio=name)
            )
    results: dict[str, object] = {}
    for name in PORTFOLIOS:
        primary = _summarize(primary_raw[name])
        gross = _summarize(gross_raw[name])
        primary_terminal = [item.terminal_return for item in primary_raw[name]]
        gross_terminal = [item.terminal_return for item in gross_raw[name]]
        results[name] = {
            "original_sample": sample_counts[name],
            "primary_0_50bp": primary,
            "gross_0bp": gross,
            "paired_cost_drag_terminal_return": _distribution(
                [
                    gross_value - net_value
                    for gross_value, net_value in zip(
                        gross_terminal, primary_terminal, strict=True
                    )
                ]
            ),
        }
    a = primary_raw["A_CORE"]
    b = primary_raw["B_COMBINED_PORTFOLIO"]
    marginal = {
        "terminal_return_B_minus_A": _distribution(
            [right.terminal_return - left.terminal_return for left, right in zip(a, b, strict=True)]
        ),
        "maximum_drawdown_B_minus_A": _distribution(
            [right.max_drawdown - left.max_drawdown for left, right in zip(a, b, strict=True)]
        ),
        "probability_positive_delta": (
            sum(item.terminal_return > 0 for item in b)
            - sum(item.terminal_return > 0 for item in a)
        ) / paths,
        "max_concurrency_B_minus_A": _distribution(
            [
                float(right.max_concurrency - left.max_concurrency)
                for left, right in zip(a, b, strict=True)
            ]
        ),
        "heat_interactions_delta_total": sum(item.heat_interactions for item in b)
        - sum(item.heat_interactions for item in a),
        "risk_reduce_delta_total": sum(item.reduce for item in b) - sum(item.reduce for item in a),
        "risk_reject_delta_total": sum(item.reject for item in b) - sum(item.reject for item in a),
    }
    file_digests = _file_digests((baseline_root, fresh_root))
    fingerprints = _evidence_fingerprints((baseline_root, fresh_root))
    risk_contract = {
        "starting_equity_usd": format(PRIMARY_STARTING_EQUITY_USD, "f"),
        "desired_per_trade_risk_bps": PRIMARY_PER_TRADE_RISK_BPS,
        "portfolio_heat_bps": PRIMARY_PORTFOLIO_HEAT_BPS,
        "broker_min_max_step_enforced": True,
        "allocation_order": "signal_at,symbol,side; exits at timestamp precede entries",
    }
    portfolio_material = {
        name: [list(member) for member in members]
        for name, members in PORTFOLIOS.items()
    }
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "repository": "mezas3238-hue/qore-core",
        "pull_request": 527,
        "branch": "agent/vt08-r3-11-profitability-forensics-001",
        "git_sha": git_sha,
        "classification": "CONSUMED-DATA RESEARCH ONLY",
        "independent_validation": False,
        "demo_eligible": False,
        "holdout_not_accessed": True,
        "protected_holdout_2020_2022_accessed": False,
        "consumed_trade_range": {
            "first_signal": min(trade.signal_at for trade in trades).isoformat(),
            "last_exit": max(trade.exited_at for trade in trades).isoformat(),
        },
        "consumed_run_ids": [FRESH_RUN_ID, BASELINE_RUN_ID],
        "input_artifacts": {
            str(run): [{"id": artifact, "digest": digest} for artifact, digest in artifacts]
            for run, artifacts in INPUT_ARTIFACTS.items()
        },
        "input_file_sha256": file_digests,
        "input_data_digest": _canonical_digest(file_digests),
        "methodology_fingerprints": fingerprints["methodology"],
        "source_contract_fingerprints": fingerprints["source_contract"],
        "risk_policy": risk_contract,
        "risk_policy_fingerprint": _canonical_digest(risk_contract),
        "portfolio_definitions": portfolio_material,
        "portfolio_fingerprints": {
            name: _canonical_digest(members) for name, members in portfolio_material.items()
        },
        "experiment": {
            "rng": "CPython random.Random MT19937 through DeterministicRandom",
            "rng_state_version": 3,
            "python_version": platform.python_version(),
            "seed": SEED,
            "paths": paths,
            "horizon_trading_days": HORIZON_DAYS,
            "resampling": "paired moving-block bootstrap over portfolio business days",
            "block_length_trading_days": BLOCK_DAYS,
            "within_block_chronology_preserved": True,
            "simultaneous_events_preserved": True,
            "primary_transaction_cost_bps_per_completed_trade": format(PRIMARY_COST_BPS, "f"),
            "actual_ctrader_cost_demonstrated": False,
        },
        "results": results,
        "GBPJPY_incremental_contribution": marginal,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args(argv)
    report = build_official_report(
        args.baseline_root,
        args.fresh_root,
        git_sha=args.git_sha,
        generated_at=args.generated_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
