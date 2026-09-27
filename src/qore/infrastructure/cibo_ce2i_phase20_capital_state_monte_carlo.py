"""Phase 20E capital-state Monte Carlo block-bootstrap contracts.

This module deliberately does NOT shuffle individual trades. It first builds
connected temporal components from normalized-capital opportunities, optionally
groups adjacent components into larger chronological blocks, then resamples
those blocks with replacement. Within every sampled block it preserves:

- Trader identity;
- decision -> entry -> exit timing;
- trade duration;
- normalized outcome;
- allocation risk budget and priority;
- same-timestamp entry-before-exit semantics;
- overlap/concurrency relationships;
- reservation/release behavior when replayed by the Phase-19 normalized ledger.

The result is research-only bootstrap evidence. It is not a market probability
model, historical provider replay, allocator certification, Risk authority or
execution authority.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalAllocation,
    Phase19NormalizedCapitalReplay,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)


@dataclass(frozen=True, slots=True)
class Phase20MonteCarloBlock:
    block_id: str
    trades: tuple[Phase19NormalizedReplayTrade, ...]

    def __post_init__(self) -> None:
        if not self.block_id or not self.trades:
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo block identity/trades are required"
            )
        fingerprints = tuple(
            item.opportunity.signal_fingerprint for item in self.trades
        )
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo block contains duplicate signals"
            )
        ordered = tuple(
            sorted(
                self.trades,
                key=lambda item: (
                    item.opportunity.entry_at,
                    item.allocation.allocation_priority,
                    item.opportunity.trader_id.value,
                    item.opportunity.signal_fingerprint,
                ),
            )
        )
        if ordered != self.trades:
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo block must be chronological"
            )

    @property
    def start_at(self) -> datetime:
        return min(item.allocation.decision_at for item in self.trades)

    @property
    def end_at(self) -> datetime:
        return max(item.opportunity.exit_at for item in self.trades)

    @property
    def opportunity_count(self) -> int:
        return len(self.trades)


@dataclass(frozen=True, slots=True)
class Phase20MonteCarloPath:
    simulation_id: str
    seed: int
    sampled_block_ids: tuple[str, ...]
    trades: tuple[Phase19NormalizedReplayTrade, ...]
    independent_trade_shuffle: bool = False
    market_probability_claimed: bool = False
    historical_provider_economics_claimed: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.simulation_id
            or not self.sampled_block_ids
            or not self.trades
        ):
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo path identity/contents are required"
            )
        if type(self.seed) is not int:
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo seed must be int"
            )
        if (
            self.independent_trade_shuffle
            or self.market_probability_claimed
            or self.historical_provider_economics_claimed
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo governance drift"
            )
        fingerprints = tuple(
            item.opportunity.signal_fingerprint for item in self.trades
        )
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError(
                "Phase20E sampled path fingerprints must be unique"
            )


@dataclass(frozen=True, slots=True)
class Phase20MonteCarloPathResult:
    simulation_id: str
    sampled_block_ids: tuple[str, ...]
    replay: Phase19NormalizedCapitalReplay

    def __post_init__(self) -> None:
        if not self.simulation_id or not self.sampled_block_ids:
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo result identity is required"
            )


@dataclass(frozen=True, slots=True)
class Phase20MonteCarloSummary:
    simulation_count: int
    source_block_count: int
    components_per_block: int
    draws_per_path: int
    base_seed: int
    min_ending_capital_ncu: Decimal
    max_ending_capital_ncu: Decimal
    p95_max_drawdown_ncu: Decimal
    positive_ending_delta_paths: int
    capacity_breach_paths: int
    max_rejected_opportunities: int
    path_results: tuple[Phase20MonteCarloPathResult, ...]
    independent_trade_shuffle: bool = False
    market_probability_claimed: bool = False
    policy_certified: bool = False

    def __post_init__(self) -> None:
        for name in (
            "simulation_count",
            "source_block_count",
            "components_per_block",
            "draws_per_path",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise CiboCapitalManagementError(
                    f"Phase20E {name} must be positive int"
                )
        if type(self.base_seed) is not int:
            raise CiboCapitalManagementError(
                "Phase20E base_seed must be int"
            )
        if self.simulation_count != len(self.path_results):
            raise CiboCapitalManagementError(
                "Phase20E simulation-count drift"
            )
        if not 0 <= self.positive_ending_delta_paths <= self.simulation_count:
            raise CiboCapitalManagementError(
                "Phase20E positive-path count drift"
            )
        if not 0 <= self.capacity_breach_paths <= self.simulation_count:
            raise CiboCapitalManagementError(
                "Phase20E capacity-breach count drift"
            )
        if self.max_rejected_opportunities < 0:
            raise CiboCapitalManagementError(
                "Phase20E rejected-opportunity count cannot be negative"
            )
        if (
            self.independent_trade_shuffle
            or self.market_probability_claimed
            or self.policy_certified
        ):
            raise CiboCapitalManagementError(
                "Phase20E Monte Carlo summary governance drift"
            )


def _ordered(
    trades: Iterable[Phase19NormalizedReplayTrade],
) -> tuple[Phase19NormalizedReplayTrade, ...]:
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                item.opportunity.entry_at,
                item.allocation.allocation_priority,
                item.opportunity.trader_id.value,
                item.opportunity.signal_fingerprint,
            ),
        )
    )
    if not ordered:
        raise CiboCapitalManagementError(
            "Phase20E Monte Carlo requires normalized trades"
        )
    fingerprints = tuple(
        item.opportunity.signal_fingerprint for item in ordered
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "Phase20E source population contains duplicate signals"
        )
    return ordered


def build_phase20e_temporal_blocks(
    *,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    components_per_block: int,
) -> tuple[Phase20MonteCarloBlock, ...]:
    """Build contiguous overlap-aware blocks without cutting open positions."""

    if type(components_per_block) is not int or components_per_block <= 0:
        raise CiboCapitalManagementError(
            "components_per_block must be positive int"
        )
    ordered = _ordered(trades)

    components: list[list[Phase19NormalizedReplayTrade]] = []
    current: list[Phase19NormalizedReplayTrade] = []
    current_end: datetime | None = None

    for item in ordered:
        entry_at = item.opportunity.entry_at
        exit_at = item.opportunity.exit_at
        if not current:
            current = [item]
            current_end = exit_at
            continue
        if current_end is None:
            raise CiboCapitalManagementError(
                "Phase20E component end-state drift"
            )
        # Equality is connected because normalized replay processes ENTRY
        # before EXIT at the same timestamp, so capacity is simultaneously
        # reserved for both events.
        if entry_at <= current_end:
            current.append(item)
            current_end = max(current_end, exit_at)
        else:
            components.append(current)
            current = [item]
            current_end = exit_at
    if current:
        components.append(current)

    blocks: list[Phase20MonteCarloBlock] = []
    for block_index in range(0, len(components), components_per_block):
        grouped = tuple(
            item
            for component in components[
                block_index : block_index + components_per_block
            ]
            for item in component
        )
        blocks.append(
            Phase20MonteCarloBlock(
                block_id=(
                    f"MC_BLOCK_{block_index // components_per_block:04d}"
                ),
                trades=grouped,
            )
        )
    return tuple(blocks)


def _shifted_trade(
    *,
    item: Phase19NormalizedReplayTrade,
    shift: timedelta,
    simulation_id: str,
    draw_index: int,
) -> Phase19NormalizedReplayTrade:
    source_opportunity = item.opportunity
    source_allocation = item.allocation
    fingerprint = (
        f"mc:{simulation_id}:{draw_index}:"
        f"{source_opportunity.signal_fingerprint}"
    )
    opportunity = Phase19ChronologicalOpportunity(
        trader_id=source_opportunity.trader_id,
        signal_fingerprint=fingerprint,
        qore_symbol=source_opportunity.qore_symbol,
        entry_at=source_opportunity.entry_at + shift,
        exit_at=source_opportunity.exit_at + shift,
    )
    cutoff = source_allocation.train_cutoff_at
    allocation = Phase19NormalizedCapitalAllocation(
        signal_fingerprint=fingerprint,
        trader_id=source_allocation.trader_id,
        decision_at=source_allocation.decision_at + shift,
        risk_budget_ncu=source_allocation.risk_budget_ncu,
        allocation_priority=source_allocation.allocation_priority,
        policy_id=source_allocation.policy_id,
        evidence_id=(
            f"{source_allocation.evidence_id}|mc:{simulation_id}:{draw_index}"
        ),
        train_cutoff_at=(cutoff + shift if cutoff is not None else None),
        outcome_aware=False,
    )
    return Phase19NormalizedReplayTrade(
        opportunity=opportunity,
        allocation=allocation,
        normalized_outcome_r=item.normalized_outcome_r,
        outcome_evidence_id=(
            f"{item.outcome_evidence_id}|mc:{simulation_id}:{draw_index}"
        ),
    )


def sample_phase20e_block_path(
    *,
    blocks: tuple[Phase20MonteCarloBlock, ...],
    draws_per_path: int,
    seed: int,
    simulation_id: str,
) -> Phase20MonteCarloPath:
    """Sample whole temporal blocks and rebase them without cross-block overlap."""

    if not blocks:
        raise CiboCapitalManagementError(
            "Phase20E block bootstrap requires source blocks"
        )
    if type(draws_per_path) is not int or draws_per_path <= 0:
        raise CiboCapitalManagementError(
            "draws_per_path must be positive int"
        )
    if type(seed) is not int or not simulation_id:
        raise CiboCapitalManagementError(
            "Phase20E path seed/identity is required"
        )

    rng = random.Random(seed)
    sampled = tuple(rng.choice(blocks) for _ in range(draws_per_path))
    synthetic: list[Phase19NormalizedReplayTrade] = []
    cursor: datetime | None = None

    for draw_index, block in enumerate(sampled):
        source_start = block.start_at
        source_end = block.end_at
        if cursor is None:
            target_start = source_start
        else:
            target_start = cursor + timedelta(microseconds=1)
        shift = target_start - source_start
        synthetic.extend(
            _shifted_trade(
                item=item,
                shift=shift,
                simulation_id=simulation_id,
                draw_index=draw_index,
            )
            for item in block.trades
        )
        cursor = source_end + shift

    return Phase20MonteCarloPath(
        simulation_id=simulation_id,
        seed=seed,
        sampled_block_ids=tuple(block.block_id for block in sampled),
        trades=tuple(synthetic),
    )


def _nearest_rank_p95(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "Phase20E p95 requires values"
        )
    ordered = sorted(values)
    rank = (95 * len(ordered) + 99) // 100
    return ordered[max(0, rank - 1)]


def run_phase20e_capital_state_monte_carlo(
    *,
    contract: Phase19CapitalNumeraireContract,
    initial_capital_ncu: Decimal,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    simulations: int,
    draws_per_path: int,
    components_per_block: int,
    base_seed: int,
) -> Phase20MonteCarloSummary:
    """Run deterministic block-bootstrap paths through the capital-state ledger."""

    if type(simulations) is not int or simulations <= 0:
        raise CiboCapitalManagementError(
            "Phase20E simulations must be positive int"
        )
    if type(base_seed) is not int:
        raise CiboCapitalManagementError(
            "Phase20E base_seed must be int"
        )
    blocks = build_phase20e_temporal_blocks(
        trades=trades,
        components_per_block=components_per_block,
    )
    path_results: list[Phase20MonteCarloPathResult] = []
    for index in range(simulations):
        simulation_id = f"PHASE20E_MC_{index:04d}"
        path = sample_phase20e_block_path(
            blocks=blocks,
            draws_per_path=draws_per_path,
            seed=base_seed + index,
            simulation_id=simulation_id,
        )
        replay = replay_phase19_normalized_capital(
            contract=contract,
            initial_capital_ncu=initial_capital_ncu,
            trades=path.trades,
        )
        path_results.append(
            Phase20MonteCarloPathResult(
                simulation_id=simulation_id,
                sampled_block_ids=path.sampled_block_ids,
                replay=replay,
            )
        )

    results = tuple(path_results)
    endings = tuple(item.replay.ending_capital_ncu for item in results)
    drawdowns = tuple(item.replay.max_drawdown_ncu for item in results)
    return Phase20MonteCarloSummary(
        simulation_count=simulations,
        source_block_count=len(blocks),
        components_per_block=components_per_block,
        draws_per_path=draws_per_path,
        base_seed=base_seed,
        min_ending_capital_ncu=min(endings),
        max_ending_capital_ncu=max(endings),
        p95_max_drawdown_ncu=_nearest_rank_p95(drawdowns),
        positive_ending_delta_paths=sum(
            item.replay.total_realized_delta_ncu > 0 for item in results
        ),
        capacity_breach_paths=sum(
            item.replay.capacity_breach_observed for item in results
        ),
        max_rejected_opportunities=max(
            item.replay.rejected_opportunities for item in results
        ),
        path_results=results,
    )
