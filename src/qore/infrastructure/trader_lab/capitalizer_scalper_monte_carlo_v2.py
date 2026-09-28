"""Deterministic Monte Carlo tail-risk diagnostics for Capitalizer Scalper.

This module is research evidence only. It resamples an already-realized trade-R
sequence and never changes entries, exits, sizing, or runtime decisions.

Core scenario families:
- exact multiset reshuffling;
- circular block bootstrap at frozen short and medium block lengths;
- circular block bootstrap plus one injected copy of the worst historical
  contiguous loss cluster.

When explicit provider/broker cost evidence is supplied, the same returns may be
stressed by a fixed additional cost in R per trade. No cost is invented when
provider economics are absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)

IDENTITY = "QORE_CAPITALIZER_SCALPER_MONTE_CARLO_V2"
MC_POSITIVE_GATE = Decimal("0.90")
MC_P95_DD_GATE_R = Decimal("15")
_MASK64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class MonteCarloScenario:
    scenario: str
    replicates: int
    block_length: int | None
    worst_loss_cluster_length: int
    worst_loss_cluster_r: str
    additional_cost_r_per_trade: str
    positive_probability: str
    p05_total_r: str
    median_total_r: str
    p95_drawdown_r: str
    p99_drawdown_r: str
    max_drawdown_r: str


@dataclass(frozen=True, slots=True)
class MonteCarloReport:
    identity: str
    population_role: str
    trades: int
    source_total_r: str
    source_max_drawdown_r: str
    seed: int
    replicates_per_scenario: int
    block_lengths: tuple[int, ...]
    scenarios: tuple[MonteCarloScenario, ...]
    conservative_positive_probability: str
    conservative_p95_drawdown_r: str
    mc_positive_gate: str
    mc_p95_dd_gate_r: str
    mc_gate_passed: bool
    provider_cost_evidence_bound: bool
    cost_stress_status: str
    outcome_resampling_only: bool = True
    runtime_policy_candidate: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False


def _source_values(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, ...]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: (milestone._aware(row.entry_at), row.symbol),
        )
    )
    keys = tuple((row.symbol, row.entry_at) for row in ordered)
    if len(set(keys)) != len(keys):
        raise ValueError("Monte Carlo requires unique entrant identities")
    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
    if not values:
        raise ValueError("Monte Carlo requires non-empty trade sequence")
    return values


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal("0")
    peak = Decimal("0")
    maximum = Decimal("0")
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _loss_clusters(
    values: tuple[Decimal, ...],
) -> tuple[tuple[Decimal, ...], ...]:
    clusters: list[tuple[Decimal, ...]] = []
    active: list[Decimal] = []
    for value in values:
        if value < 0:
            active.append(value)
        elif active:
            clusters.append(tuple(active))
            active.clear()
    if active:
        clusters.append(tuple(active))
    return tuple(clusters)


def _worst_cluster(
    values: tuple[Decimal, ...],
) -> tuple[Decimal, ...]:
    clusters = _loss_clusters(values)
    if not clusters:
        return ()
    return min(
        clusters,
        key=lambda row: (
            sum(row, Decimal("0")),
            -len(row),
        ),
    )


def _seed_state(seed: int, scenario: str, replicate: int) -> int:
    if seed < 0:
        raise ValueError("Monte Carlo seed must be non-negative")
    payload = f"{IDENTITY}:{seed}:{scenario}:{replicate}".encode()
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return value or 0x9E3779B97F4A7C15


def _next_u64(state: int) -> tuple[int, int]:
    state ^= (state >> 12) & _MASK64
    state ^= (state << 25) & _MASK64
    state ^= (state >> 27) & _MASK64
    state &= _MASK64
    value = (state * 2685821657736338717) & _MASK64
    return state, value


def _randbelow(state: int, bound: int) -> tuple[int, int]:
    if bound <= 0:
        raise ValueError("randbelow bound must be positive")
    state, value = _next_u64(state)
    return state, value % bound


def _reshuffle(
    values: tuple[Decimal, ...],
    *,
    seed: int,
    replicate: int,
) -> tuple[Decimal, ...]:
    items = list(values)
    state = _seed_state(seed, "RESHUFFLE", replicate)
    for index in range(len(items) - 1, 0, -1):
        state, swap = _randbelow(state, index + 1)
        items[index], items[swap] = items[swap], items[index]
    return tuple(items)


def _circular_block(
    values: tuple[Decimal, ...],
    *,
    seed: int,
    replicate: int,
    block_length: int,
    scenario: str,
) -> tuple[Decimal, ...]:
    sample_size = len(values)
    if block_length < 2 or block_length > sample_size:
        raise ValueError("block length must be in [2, sample_size]")
    state = _seed_state(seed, scenario, replicate)
    result: list[Decimal] = []
    while len(result) < sample_size:
        state, start = _randbelow(state, sample_size)
        for offset in range(block_length):
            result.append(values[(start + offset) % sample_size])
            if len(result) == sample_size:
                break
    return tuple(result)


def _inject_worst_cluster(
    values: tuple[Decimal, ...],
    *,
    cluster: tuple[Decimal, ...],
    seed: int,
    replicate: int,
) -> tuple[Decimal, ...]:
    if not cluster:
        return values
    items = list(values)
    state = _seed_state(seed, "LOSS_CLUSTER_INJECTION", replicate)
    state, start = _randbelow(state, len(items))
    del state
    for offset, value in enumerate(cluster):
        items[(start + offset) % len(items)] = value
    return tuple(items)


def _quantile(
    values: tuple[Decimal, ...],
    probability: Decimal,
) -> Decimal:
    if not values:
        raise ValueError("quantile requires observations")
    if not Decimal("0") <= probability <= Decimal("1"):
        raise ValueError("quantile probability must be in [0, 1]")
    ordered = sorted(values)
    if probability == 0:
        return ordered[0]
    rank = (
        int(
            (probability * Decimal(len(ordered))).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        - 1
    )
    return ordered[min(max(rank, 0), len(ordered) - 1)]


def _summarize(
    *,
    name: str,
    source: tuple[Decimal, ...],
    replicates: int,
    seed: int,
    block_length: int | None,
    inject_worst_cluster: bool,
    additional_cost_r_per_trade: Decimal,
) -> MonteCarloScenario:
    if replicates <= 0:
        raise ValueError("replicates must be positive")
    adjusted = tuple(
        value - additional_cost_r_per_trade for value in source
    )
    worst = _worst_cluster(adjusted)
    totals: list[Decimal] = []
    drawdowns: list[Decimal] = []

    for replicate in range(replicates):
        if name.startswith("RESHUFFLE"):
            path = _reshuffle(
                adjusted,
                seed=seed,
                replicate=replicate,
            )
        else:
            if block_length is None:
                raise ValueError("block scenario requires block length")
            path = _circular_block(
                adjusted,
                seed=seed,
                replicate=replicate,
                block_length=block_length,
                scenario=name,
            )
        if inject_worst_cluster:
            path = _inject_worst_cluster(
                path,
                cluster=worst,
                seed=seed,
                replicate=replicate,
            )
        totals.append(sum(path, Decimal("0")))
        drawdowns.append(_max_drawdown(path))

    positive = Decimal(sum(total > 0 for total in totals)) / Decimal(
        replicates
    )
    return MonteCarloScenario(
        scenario=name,
        replicates=replicates,
        block_length=block_length,
        worst_loss_cluster_length=len(worst),
        worst_loss_cluster_r=str(sum(worst, Decimal("0"))),
        additional_cost_r_per_trade=str(additional_cost_r_per_trade),
        positive_probability=str(positive),
        p05_total_r=str(_quantile(tuple(totals), Decimal("0.05"))),
        median_total_r=str(_quantile(tuple(totals), Decimal("0.50"))),
        p95_drawdown_r=str(
            _quantile(tuple(drawdowns), Decimal("0.95"))
        ),
        p99_drawdown_r=str(
            _quantile(tuple(drawdowns), Decimal("0.99"))
        ),
        max_drawdown_r=str(max(drawdowns)),
    )


def build_monte_carlo_report(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    population_role: str,
    seed: int = 240917,
    replicates: int = 5000,
    block_lengths: tuple[int, ...] = (5, 20),
    provider_cost_evidence_bound: bool = False,
    additional_cost_r_per_trade: Decimal | None = None,
) -> MonteCarloReport:
    if not population_role:
        raise ValueError("population_role must be non-empty")
    source = _source_values(rows)
    if provider_cost_evidence_bound != (
        additional_cost_r_per_trade is not None
    ):
        raise ValueError(
            "cost stress requires both bound provider evidence and explicit cost"
        )
    if additional_cost_r_per_trade is not None and (
        not additional_cost_r_per_trade.is_finite()
        or additional_cost_r_per_trade < 0
    ):
        raise ValueError("additional cost must be finite non-negative Decimal")
    if not block_lengths:
        raise ValueError("at least one block length is required")
    if any(length < 2 or length > len(source) for length in block_lengths):
        raise ValueError("invalid block length")

    scenarios: list[MonteCarloScenario] = [
        _summarize(
            name="RESHUFFLE",
            source=source,
            replicates=replicates,
            seed=seed,
            block_length=None,
            inject_worst_cluster=False,
            additional_cost_r_per_trade=Decimal("0"),
        )
    ]
    for block_length in block_lengths:
        scenarios.append(
            _summarize(
                name=f"CIRCULAR_BLOCK_{block_length}",
                source=source,
                replicates=replicates,
                seed=seed,
                block_length=block_length,
                inject_worst_cluster=False,
                additional_cost_r_per_trade=Decimal("0"),
            )
        )
    stress_block = max(block_lengths)
    scenarios.append(
        _summarize(
            name=f"LOSS_CLUSTER_STRESS_BLOCK_{stress_block}",
            source=source,
            replicates=replicates,
            seed=seed,
            block_length=stress_block,
            inject_worst_cluster=True,
            additional_cost_r_per_trade=Decimal("0"),
        )
    )

    if additional_cost_r_per_trade is not None:
        scenarios.extend(
            [
                _summarize(
                    name=f"CIRCULAR_BLOCK_{stress_block}_COST",
                    source=source,
                    replicates=replicates,
                    seed=seed,
                    block_length=stress_block,
                    inject_worst_cluster=False,
                    additional_cost_r_per_trade=additional_cost_r_per_trade,
                ),
                _summarize(
                    name=(
                        f"LOSS_CLUSTER_STRESS_BLOCK_{stress_block}_COST"
                    ),
                    source=source,
                    replicates=replicates,
                    seed=seed,
                    block_length=stress_block,
                    inject_worst_cluster=True,
                    additional_cost_r_per_trade=additional_cost_r_per_trade,
                ),
            ]
        )

    conservative_positive = min(
        Decimal(row.positive_probability) for row in scenarios
    )
    conservative_p95_dd = max(
        Decimal(row.p95_drawdown_r) for row in scenarios
    )
    gate_passed = (
        conservative_positive >= MC_POSITIVE_GATE
        and conservative_p95_dd <= MC_P95_DD_GATE_R
    )
    source_total = sum(source, Decimal("0"))
    source_dd = _max_drawdown(source)
    return MonteCarloReport(
        identity=IDENTITY,
        population_role=population_role,
        trades=len(source),
        source_total_r=str(source_total),
        source_max_drawdown_r=str(source_dd),
        seed=seed,
        replicates_per_scenario=replicates,
        block_lengths=block_lengths,
        scenarios=tuple(scenarios),
        conservative_positive_probability=str(conservative_positive),
        conservative_p95_drawdown_r=str(conservative_p95_dd),
        mc_positive_gate=str(MC_POSITIVE_GATE),
        mc_p95_dd_gate_r=str(MC_P95_DD_GATE_R),
        mc_gate_passed=gate_passed,
        provider_cost_evidence_bound=provider_cost_evidence_bound,
        cost_stress_status=(
            "RUN_WITH_BOUND_PROVIDER_COST_EVIDENCE"
            if provider_cost_evidence_bound
            else "NOT_RUN_NO_BOUND_PROVIDER_COST_EVIDENCE"
        ),
    )


def _load_rows(
    path: Path,
) -> tuple[milestone.SimulatedTrade, ...]:
    rows: list[milestone.SimulatedTrade] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw: Any = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("Monte Carlo ledger row must be object")
                rows.append(milestone.SimulatedTrade(**raw))
    return tuple(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--population-role", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=240917)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument(
        "--block-length",
        type=int,
        action="append",
        dest="block_lengths",
    )
    parser.add_argument("--provider-cost-evidence-bound", action="store_true")
    parser.add_argument("--additional-cost-r-per-trade")
    args = parser.parse_args()

    cost = (
        None
        if args.additional_cost_r_per_trade is None
        else Decimal(args.additional_cost_r_per_trade)
    )
    report = build_monte_carlo_report(
        _load_rows(args.ledger),
        population_role=args.population_role,
        seed=args.seed,
        replicates=args.replicates,
        block_lengths=(
            tuple(args.block_lengths)
            if args.block_lengths
            else (5, 20)
        ),
        provider_cost_evidence_bound=args.provider_cost_evidence_bound,
        additional_cost_r_per_trade=cost,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "capitalizer-scalper-monte-carlo-v2.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
