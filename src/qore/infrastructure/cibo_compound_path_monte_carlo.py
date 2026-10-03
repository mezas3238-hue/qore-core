"""GEN-C9 compound path-dependent Monte Carlo adapter.

This adapter block-bootstraps whole overlapping compound-deployment episodes.
It preserves Trader identity, duration, ICM lineage, source generation,
stop-risk, margin, settlement, T19 release and explicitly attributed protected
floor graduation. It never remaps a missing GEN-N dependency to a different
generation: impossible paths are recorded as dependency/capacity breaches.

Research only. Empirical path frequencies are not market probabilities.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    TraderIdentity,
    canonical_trader_lineage,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_cycle_state import CiboCompoundCycleState
from qore.infrastructure.cibo_robust_growth_ruin_capacity import (
    Genc9Numeraire,
    Genc9PathEvidence,
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound Monte Carlo {name} must be timezone-aware"
        )


def _money(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or (value <= 0 if positive else value < 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise CiboCompoundCapitalError(
            f"compound Monte Carlo {name} must be finite {qualifier} Decimal"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"compound Monte Carlo {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloFloorAttribution:
    deployment_id: str
    occurred_at: datetime
    amount_usd: Decimal
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.deployment_id:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo floor attribution deployment is required"
            )
        _aware(self.occurred_at, "floor attribution occurred_at")
        _money(self.amount_usd, "floor attribution amount", positive=True)
        _sha(self.evidence_sha256, "floor attribution evidence_sha256")


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloEpisode:
    episode_id: str
    deployment_id: str
    market_event_id: str
    decision_id: str
    candidate_id: str
    trader_id: TraderIdentity
    signal_fingerprint: str
    deployed_at: datetime
    settled_at: datetime
    source_generation: int
    deployed_capital_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    realized_pnl_usd: Decimal
    protected_floor_graduation_usd: Decimal
    floor_evidence_sha256: str | None
    market_record_present: bool
    terminal_release_present: bool
    future_leakage_used: bool = False

    def __post_init__(self) -> None:
        for name in (
            "episode_id",
            "deployment_id",
            "market_event_id",
            "decision_id",
            "candidate_id",
            "signal_fingerprint",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo episode {name} is required"
                )
        object.__setattr__(
            self,
            "trader_id",
            canonical_trader_lineage(self.trader_id),
        )
        _aware(self.deployed_at, "episode deployed_at")
        _aware(self.settled_at, "episode settled_at")
        if self.settled_at <= self.deployed_at:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo settlement must follow deployment"
            )
        if (
            not isinstance(self.source_generation, int)
            or isinstance(self.source_generation, bool)
            or self.source_generation < 1
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo source generation must be positive int"
            )
        for name in (
            "deployed_capital_usd",
            "stop_risk_usd",
            "margin_usd",
        ):
            _money(getattr(self, name), name, positive=True)
        if (
            not isinstance(self.realized_pnl_usd, Decimal)
            or not self.realized_pnl_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo realized PnL must be finite Decimal"
            )
        _money(
            self.protected_floor_graduation_usd,
            "protected floor graduation",
        )
        if self.protected_floor_graduation_usd > max(
            Decimal(0),
            self.realized_pnl_usd,
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo floor graduation exceeds realized profit"
            )
        if self.protected_floor_graduation_usd > 0:
            if self.floor_evidence_sha256 is None:
                raise CiboCompoundCapitalError(
                    "compound Monte Carlo floor graduation requires evidence"
                )
            _sha(
                self.floor_evidence_sha256,
                "floor evidence_sha256",
            )
        elif self.floor_evidence_sha256 is not None:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo zero floor graduation cannot carry evidence"
            )
        for name in (
            "market_record_present",
            "terminal_release_present",
            "future_leakage_used",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo episode {name} must be bool"
                )
        if (
            not self.market_record_present
            or not self.terminal_release_present
            or self.future_leakage_used
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo episode provenance/governance drift"
            )


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloBlock:
    block_id: str
    episodes: tuple[CompoundMonteCarloEpisode, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.block_id, str)
            or not self.block_id
            or not isinstance(self.episodes, tuple)
            or not self.episodes
            or any(
                not isinstance(item, CompoundMonteCarloEpisode)
                for item in self.episodes
            )
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo block identity/episodes are required"
            )
        episode_ids = tuple(item.episode_id for item in self.episodes)
        deployment_ids = tuple(item.deployment_id for item in self.episodes)
        if (
            len(episode_ids) != len(set(episode_ids))
            or len(deployment_ids) != len(set(deployment_ids))
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo block cannot duplicate episode/deployment"
            )
        ordered = tuple(
            sorted(
                self.episodes,
                key=lambda item: (
                    item.deployed_at,
                    item.settled_at,
                    item.deployment_id,
                ),
            )
        )
        if ordered != self.episodes:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo block must be chronological"
            )

    @property
    def start_at(self) -> datetime:
        return min(item.deployed_at for item in self.episodes)

    @property
    def end_at(self) -> datetime:
        return max(item.settled_at for item in self.episodes)


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloInitialState:
    original_base_usd: Decimal
    generation_capacity_usd: tuple[tuple[int, Decimal], ...]
    protected_floor_usd: Decimal
    total_stop_risk_capacity_usd: Decimal
    total_margin_capacity_usd: Decimal

    def __post_init__(self) -> None:
        for name in (
            "original_base_usd",
            "protected_floor_usd",
            "total_stop_risk_capacity_usd",
            "total_margin_capacity_usd",
        ):
            _money(
                getattr(self, name),
                name,
                positive=name == "original_base_usd",
            )
        generations = tuple(item[0] for item in self.generation_capacity_usd)
        if len(generations) != len(set(generations)):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo initial generations must be unique"
            )
        for generation, amount in self.generation_capacity_usd:
            if (
                not isinstance(generation, int)
                or isinstance(generation, bool)
                or generation < 1
            ):
                raise CiboCompoundCapitalError(
                    "compound Monte Carlo generation id must be positive int"
                )
            _money(amount, "initial generation capacity")


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloPathResult:
    simulation_id: str
    sampled_block_ids: tuple[str, ...]
    ending_original_base_usd: Decimal
    ending_generation_capacity_usd: tuple[tuple[int, Decimal], ...]
    protected_floor_usd: Decimal
    ending_realized_capital_usd: Decimal
    minimum_realized_capital_usd: Decimal
    max_drawdown_usd: Decimal
    peak_stop_risk_usd: Decimal
    peak_margin_usd: Decimal
    dependency_breach_count: int
    capacity_breach_count: int
    rejected_episode_count: int
    accepted_episode_count: int
    future_leakage_used: bool = False
    market_probability_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.simulation_id or not self.sampled_block_ids:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo result identity is required"
            )
        for name in (
            "ending_original_base_usd",
            "protected_floor_usd",
            "ending_realized_capital_usd",
            "minimum_realized_capital_usd",
            "max_drawdown_usd",
            "peak_stop_risk_usd",
            "peak_margin_usd",
        ):
            _money(getattr(self, name), name)
        generations = tuple(
            generation for generation, _amount in self.ending_generation_capacity_usd
        )
        if len(generations) != len(set(generations)):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo ending generations must be unique"
            )
        for generation, amount in self.ending_generation_capacity_usd:
            if (
                not isinstance(generation, int)
                or isinstance(generation, bool)
                or generation < 1
            ):
                raise CiboCompoundCapitalError(
                    "compound Monte Carlo ending generation id must be positive int"
                )
            _money(amount, "ending generation capacity")
        expected_ending = (
            self.ending_original_base_usd
            + self.protected_floor_usd
            + sum(
                (amount for _, amount in self.ending_generation_capacity_usd),
                Decimal(0),
            )
        )
        if self.ending_realized_capital_usd != expected_ending:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo ending realized-capital identity drift"
            )
        if self.minimum_realized_capital_usd > self.ending_realized_capital_usd:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo minimum realized capital exceeds ending capital"
            )

        for name in (
            "dependency_breach_count",
            "capacity_breach_count",
            "rejected_episode_count",
            "accepted_episode_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo {name} must be non-negative int"
                )
        if self.rejected_episode_count < self.dependency_breach_count:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo dependency breaches exceed rejections"
            )
        for name in (
            "future_leakage_used",
            "market_probability_claimed",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo result {name} must be bool"
                )
        if (
            self.future_leakage_used
            or self.market_probability_claimed
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo result governance drift"
            )


@dataclass(frozen=True, slots=True)
class CompoundMonteCarloSummary:
    simulation_count: int
    source_block_count: int
    draws_per_path: int
    components_per_block: int
    base_seed: int
    minimum_ending_realized_capital_usd: Decimal
    p95_max_drawdown_usd: Decimal
    dependency_breach_paths: int
    capacity_breach_paths: int
    positive_ending_delta_paths: int
    results: tuple[CompoundMonteCarloPathResult, ...]
    market_probability_claimed: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.results, tuple)
            or not self.results
            or any(
                not isinstance(item, CompoundMonteCarloPathResult)
                for item in self.results
            )
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo summary requires canonical results"
            )
        if self.simulation_count != len(self.results):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo summary count drift"
            )
        for name in (
            "simulation_count",
            "source_block_count",
            "draws_per_path",
            "components_per_block",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo {name} must be positive int"
                )
        if type(self.base_seed) is not int:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo base seed must be int"
            )
        simulation_ids = tuple(item.simulation_id for item in self.results)
        if len(simulation_ids) != len(set(simulation_ids)):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo simulation ids must be unique"
            )
        for name in (
            "dependency_breach_paths",
            "capacity_breach_paths",
            "positive_ending_delta_paths",
        ):
            value = getattr(self, name)
            if (
                type(value) is not int
                or value < 0
                or value > self.simulation_count
            ):
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo summary {name} is invalid"
                )
        if self.dependency_breach_paths != sum(
            item.dependency_breach_count > 0 for item in self.results
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo dependency breach aggregate drift"
            )
        if self.capacity_breach_paths != sum(
            item.capacity_breach_count > 0 for item in self.results
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo capacity breach aggregate drift"
            )
        _money(
            self.minimum_ending_realized_capital_usd,
            "minimum_ending_realized_capital_usd",
        )
        _money(self.p95_max_drawdown_usd, "p95_max_drawdown_usd")
        if self.minimum_ending_realized_capital_usd != min(
            item.ending_realized_capital_usd for item in self.results
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo minimum ending capital drift"
            )
        if self.p95_max_drawdown_usd != _nearest_rank(
            tuple(item.max_drawdown_usd for item in self.results),
            95,
        ):
            raise CiboCompoundCapitalError(
                "compound Monte Carlo p95 drawdown drift"
            )
        for name in ("market_probability_claimed", "certification_ready"):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound Monte Carlo summary {name} must be bool"
                )
        if self.market_probability_claimed or self.certification_ready:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo summary cannot claim certification"
            )


@dataclass(frozen=True, slots=True)
class _SyntheticEvent:
    occurred_at: datetime
    entry_first: bool
    episode: CompoundMonteCarloEpisode


def extract_compound_monte_carlo_episodes(
    *,
    state: CiboCompoundCycleState,
    floor_attributions: tuple[
        CompoundMonteCarloFloorAttribution, ...
    ] = (),
) -> tuple[CompoundMonteCarloEpisode, ...]:
    """Extract settled compound deployments with exact ICM/T19 lineage."""

    if not isinstance(state, CiboCompoundCycleState):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo requires canonical cycle state"
        )
    floor_by_deployment = {
        item.deployment_id: item for item in floor_attributions
    }
    if len(floor_by_deployment) != len(floor_attributions):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo floor attribution ids must be unique"
        )
    deployment_ids = {item.deployment_id for item in state.deployments}
    if not set(floor_by_deployment).issubset(deployment_ids):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo floor attribution deployment is unknown"
        )

    episodes: list[CompoundMonteCarloEpisode] = []
    for deployment in state.deployments:
        if not deployment.settled:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo cannot extract open deployment"
            )
        settlements = tuple(
            item
            for item in state.settlements
            if item.deployment_id == deployment.deployment_id
        )
        if len(settlements) != 1:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo deployment settlement is not unique"
            )
        markets = tuple(
            item
            for item in state.market_records
            if item.event_id == deployment.market_event_id
            and item.decision_id == deployment.decision_id
        )
        if len(markets) != 1:
            raise CiboCompoundCapitalError(
                "compound Monte Carlo deployment lacks unique ICM record"
            )
        settlement = settlements[0]
        floor = floor_by_deployment.get(deployment.deployment_id)
        graduation = Decimal(0)
        floor_sha: str | None = None
        if floor is not None:
            if floor.occurred_at < settlement.occurred_at:
                raise CiboCompoundCapitalError(
                    "compound Monte Carlo floor attribution predates settlement"
                )
            graduation = floor.amount_usd
            floor_sha = floor.evidence_sha256
        episodes.append(
            CompoundMonteCarloEpisode(
                episode_id=deployment.deployment_id,
                deployment_id=deployment.deployment_id,
                market_event_id=deployment.market_event_id,
                decision_id=deployment.decision_id,
                candidate_id=deployment.candidate_id,
                trader_id=deployment.trader_id,
                signal_fingerprint=deployment.signal_fingerprint,
                deployed_at=deployment.deployed_at,
                settled_at=settlement.occurred_at,
                source_generation=deployment.source_generation,
                deployed_capital_usd=deployment.amount_usd,
                stop_risk_usd=deployment.stop_risk_usd,
                margin_usd=deployment.margin_usd,
                realized_pnl_usd=settlement.realized_net_pnl_usd,
                protected_floor_graduation_usd=graduation,
                floor_evidence_sha256=floor_sha,
                market_record_present=True,
                terminal_release_present=True,
                future_leakage_used=False,
            )
        )
    return tuple(
        sorted(
            episodes,
            key=lambda item: (
                item.deployed_at,
                item.settled_at,
                item.deployment_id,
            ),
        )
    )


def build_compound_monte_carlo_blocks(
    *,
    episodes: tuple[CompoundMonteCarloEpisode, ...],
    components_per_block: int,
) -> tuple[CompoundMonteCarloBlock, ...]:
    """Build connected temporal components, then group adjacent components."""

    if not episodes:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo requires episodes"
        )
    if (
        not isinstance(components_per_block, int)
        or isinstance(components_per_block, bool)
        or components_per_block <= 0
    ):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo components_per_block must be positive int"
        )
    ordered = tuple(
        sorted(
            episodes,
            key=lambda item: (
                item.deployed_at,
                item.settled_at,
                item.deployment_id,
            ),
        )
    )
    components: list[list[CompoundMonteCarloEpisode]] = []
    current: list[CompoundMonteCarloEpisode] = []
    current_end: datetime | None = None
    for episode in ordered:
        if not current:
            current = [episode]
            current_end = episode.settled_at
            continue
        assert current_end is not None
        if episode.deployed_at <= current_end:
            current.append(episode)
            current_end = max(current_end, episode.settled_at)
        else:
            components.append(current)
            current = [episode]
            current_end = episode.settled_at
    if current:
        components.append(current)

    blocks: list[CompoundMonteCarloBlock] = []
    for index in range(0, len(components), components_per_block):
        grouped = tuple(
            item
            for component in components[index : index + components_per_block]
            for item in component
        )
        blocks.append(
            CompoundMonteCarloBlock(
                block_id=f"COMPOUND_MC_BLOCK_{index // components_per_block:04d}",
                episodes=grouped,
            )
        )
    return tuple(blocks)


def run_compound_path_monte_carlo(
    *,
    initial: CompoundMonteCarloInitialState,
    episodes: tuple[CompoundMonteCarloEpisode, ...],
    simulations: int,
    draws_per_path: int,
    components_per_block: int,
    base_seed: int,
) -> CompoundMonteCarloSummary:
    """Run deterministic block-bootstrap paths through generation constraints."""

    if (
        not isinstance(simulations, int)
        or isinstance(simulations, bool)
        or simulations <= 0
    ):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo simulations must be positive int"
        )
    if (
        not isinstance(draws_per_path, int)
        or isinstance(draws_per_path, bool)
        or draws_per_path <= 0
    ):
        raise CiboCompoundCapitalError(
            "compound Monte Carlo draws_per_path must be positive int"
        )
    if type(base_seed) is not int:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo base_seed must be int"
        )
    blocks = build_compound_monte_carlo_blocks(
        episodes=episodes,
        components_per_block=components_per_block,
    )
    results: list[CompoundMonteCarloPathResult] = []
    for index in range(simulations):
        simulation_id = f"COMPOUND_MC_{index:04d}"
        sampled = _sample_blocks(
            blocks=blocks,
            draws_per_path=draws_per_path,
            seed=base_seed + index,
            simulation_id=simulation_id,
        )
        results.append(
            _simulate(
                simulation_id=simulation_id,
                initial=initial,
                blocks=sampled,
            )
        )
    rows = tuple(results)
    drawdowns = tuple(item.max_drawdown_usd for item in rows)
    initial_total = _initial_total(initial)
    return CompoundMonteCarloSummary(
        simulation_count=simulations,
        source_block_count=len(blocks),
        draws_per_path=draws_per_path,
        components_per_block=components_per_block,
        base_seed=base_seed,
        minimum_ending_realized_capital_usd=min(
            item.ending_realized_capital_usd for item in rows
        ),
        p95_max_drawdown_usd=_nearest_rank(drawdowns, 95),
        dependency_breach_paths=sum(
            item.dependency_breach_count > 0 for item in rows
        ),
        capacity_breach_paths=sum(
            item.capacity_breach_count > 0 for item in rows
        ),
        positive_ending_delta_paths=sum(
            item.ending_realized_capital_usd > initial_total for item in rows
        ),
        results=rows,
        market_probability_claimed=False,
        certification_ready=False,
    )


def genc9_path_from_compound_monte_carlo(
    *,
    candidate_id: str,
    scenario_id: str,
    evaluated_at: datetime,
    scenario_evidence_sha256: str,
    provider_economics_sha256: str,
    initial: CompoundMonteCarloInitialState,
    result: CompoundMonteCarloPathResult,
    ruin_boundary_usd: Decimal,
    horizon_minutes: Decimal,
) -> Genc9PathEvidence:
    """Convert one dependency-aware compound path into GEN-C9 evidence."""

    _aware(evaluated_at, "GEN-C9 evaluated_at")
    _sha(scenario_evidence_sha256, "scenario_evidence_sha256")
    _sha(provider_economics_sha256, "provider_economics_sha256")
    _money(ruin_boundary_usd, "ruin boundary")
    _money(horizon_minutes, "horizon", positive=True)
    initial_total = _initial_total(initial)
    if ruin_boundary_usd > initial_total:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo ruin boundary exceeds initial capital"
        )
    return Genc9PathEvidence(
        candidate_id=candidate_id,
        scenario_id=scenario_id,
        evaluated_at=evaluated_at,
        numeraire=Genc9Numeraire.PROVIDER_VALID_USD,
        initial_capital=initial_total,
        ending_capital=result.ending_realized_capital_usd,
        minimum_capital=result.minimum_realized_capital_usd,
        max_drawdown=result.max_drawdown_usd,
        max_time_underwater_minutes=Decimal(0),
        max_recovery_minutes=Decimal(0),
        peak_plausible_loss=max(
            result.peak_stop_risk_usd,
            Decimal("0.00000001"),
        ),
        ruin_boundary=ruin_boundary_usd,
        ruin_occurred=(
            result.minimum_realized_capital_usd <= ruin_boundary_usd
        ),
        capacity_breach=result.capacity_breach_count > 0,
        horizon_minutes=horizon_minutes,
        scenario_evidence_sha256=scenario_evidence_sha256,
        causal_replay_sha256=_result_sha256(result),
        provider_economics_sha256=provider_economics_sha256,
        future_leakage_used=False,
        market_probability_claimed=False,
        productive_authority=False,
    )


def _sample_blocks(
    *,
    blocks: tuple[CompoundMonteCarloBlock, ...],
    draws_per_path: int,
    seed: int,
    simulation_id: str,
) -> tuple[CompoundMonteCarloBlock, ...]:
    rng = random.Random(seed)
    sampled = tuple(rng.choice(blocks) for _ in range(draws_per_path))
    shifted: list[CompoundMonteCarloBlock] = []
    cursor: datetime | None = None
    for draw_index, block in enumerate(sampled):
        target_start = block.start_at if cursor is None else (
            cursor + timedelta(microseconds=1)
        )
        shift = target_start - block.start_at
        episodes = tuple(
            _shift_episode(
                item=item,
                shift=shift,
                simulation_id=simulation_id,
                draw_index=draw_index,
            )
            for item in block.episodes
        )
        shifted.append(
            CompoundMonteCarloBlock(
                block_id=f"{block.block_id}:draw:{draw_index}",
                episodes=episodes,
            )
        )
        cursor = block.end_at + shift
    return tuple(shifted)


def _shift_episode(
    *,
    item: CompoundMonteCarloEpisode,
    shift: timedelta,
    simulation_id: str,
    draw_index: int,
) -> CompoundMonteCarloEpisode:
    suffix = f"{simulation_id}:{draw_index}:{item.episode_id}"
    return CompoundMonteCarloEpisode(
        episode_id=f"mc:{suffix}",
        deployment_id=f"mc:{suffix}:deployment",
        market_event_id=f"mc:{suffix}:market",
        decision_id=f"mc:{suffix}:decision",
        candidate_id=item.candidate_id,
        trader_id=item.trader_id,
        signal_fingerprint=f"mc:{suffix}:{item.signal_fingerprint}",
        deployed_at=item.deployed_at + shift,
        settled_at=item.settled_at + shift,
        source_generation=item.source_generation,
        deployed_capital_usd=item.deployed_capital_usd,
        stop_risk_usd=item.stop_risk_usd,
        margin_usd=item.margin_usd,
        realized_pnl_usd=item.realized_pnl_usd,
        protected_floor_graduation_usd=(
            item.protected_floor_graduation_usd
        ),
        floor_evidence_sha256=item.floor_evidence_sha256,
        market_record_present=True,
        terminal_release_present=True,
        future_leakage_used=False,
    )


def _simulate(
    *,
    simulation_id: str,
    initial: CompoundMonteCarloInitialState,
    blocks: tuple[CompoundMonteCarloBlock, ...],
) -> CompoundMonteCarloPathResult:
    episodes = tuple(
        item for block in blocks for item in block.episodes
    )
    events = sorted(
        (
            *(
                _SyntheticEvent(
                    occurred_at=item.deployed_at,
                    entry_first=True,
                    episode=item,
                )
                for item in episodes
            ),
            *(
                _SyntheticEvent(
                    occurred_at=item.settled_at,
                    entry_first=False,
                    episode=item,
                )
                for item in episodes
            ),
        ),
        key=lambda event: (
            event.occurred_at,
            0 if event.entry_first else 1,
            event.episode.episode_id,
        ),
    )
    generation = dict(initial.generation_capacity_usd)
    original_base = initial.original_base_usd
    protected_floor = initial.protected_floor_usd
    active: dict[str, CompoundMonteCarloEpisode] = {}
    used_risk = Decimal(0)
    used_margin = Decimal(0)
    peak_risk = Decimal(0)
    peak_margin = Decimal(0)
    initial_total = _initial_total(initial)
    current_total = initial_total
    minimum_total = initial_total
    peak_total = initial_total
    max_drawdown = Decimal(0)
    dependency_breaches = 0
    capacity_breaches = 0
    rejected = 0
    accepted = 0

    for event in events:
        episode = event.episode
        if event.entry_first:
            available = generation.get(
                episode.source_generation,
                Decimal(0),
            )
            generation_ok = available >= episode.deployed_capital_usd
            risk_ok = (
                used_risk + episode.stop_risk_usd
                <= initial.total_stop_risk_capacity_usd
            )
            margin_ok = (
                used_margin + episode.margin_usd
                <= initial.total_margin_capacity_usd
            )
            if not generation_ok or not risk_ok or not margin_ok:
                rejected += 1
                capacity_breaches += 1
                if not generation_ok:
                    dependency_breaches += 1
                continue
            generation[episode.source_generation] = (
                available - episode.deployed_capital_usd
            )
            used_risk += episode.stop_risk_usd
            used_margin += episode.margin_usd
            peak_risk = max(peak_risk, used_risk)
            peak_margin = max(peak_margin, used_margin)
            active[episode.episode_id] = episode
            accepted += 1
            continue

        if episode.episode_id not in active:
            continue
        active.pop(episode.episode_id)
        used_risk -= episode.stop_risk_usd
        used_margin -= episode.margin_usd
        pnl = episode.realized_pnl_usd
        loss = -pnl if pnl < 0 else Decimal(0)
        consumed = min(loss, episode.deployed_capital_usd)
        returned = episode.deployed_capital_usd - consumed
        generation[episode.source_generation] = (
            generation.get(episode.source_generation, Decimal(0))
            + returned
        )
        excess = max(Decimal(0), loss - episode.deployed_capital_usd)
        if excess > original_base:
            capacity_breaches += 1
            original_base = Decimal(0)
        else:
            original_base -= excess
        if pnl > 0:
            next_generation = episode.source_generation + 1
            productive_profit = (
                pnl - episode.protected_floor_graduation_usd
            )
            generation[next_generation] = (
                generation.get(next_generation, Decimal(0))
                + productive_profit
            )
            protected_floor += episode.protected_floor_graduation_usd

        current_total += pnl
        minimum_total = min(minimum_total, current_total)
        peak_total = max(peak_total, current_total)
        max_drawdown = max(max_drawdown, peak_total - current_total)

    if active:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo synthetic path ended with open deployments"
        )
    ending_generation = tuple(
        sorted(
            (
                key,
                value,
            )
            for key, value in generation.items()
            if value > 0
        )
    )
    ending_total = original_base + protected_floor + sum(
        (amount for _, amount in ending_generation),
        Decimal(0),
    )
    if ending_total != current_total:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo realized-capital identity drift"
        )
    return CompoundMonteCarloPathResult(
        simulation_id=simulation_id,
        sampled_block_ids=tuple(block.block_id for block in blocks),
        ending_original_base_usd=original_base,
        ending_generation_capacity_usd=ending_generation,
        protected_floor_usd=protected_floor,
        ending_realized_capital_usd=ending_total,
        minimum_realized_capital_usd=minimum_total,
        max_drawdown_usd=max_drawdown,
        peak_stop_risk_usd=peak_risk,
        peak_margin_usd=peak_margin,
        dependency_breach_count=dependency_breaches,
        capacity_breach_count=capacity_breaches,
        rejected_episode_count=rejected,
        accepted_episode_count=accepted,
        future_leakage_used=False,
        market_probability_claimed=False,
        productive_authority=False,
    )


def _initial_total(initial: CompoundMonteCarloInitialState) -> Decimal:
    return (
        initial.original_base_usd
        + initial.protected_floor_usd
        + sum(
            (amount for _, amount in initial.generation_capacity_usd),
            Decimal(0),
        )
    )


def _nearest_rank(
    values: tuple[Decimal, ...],
    percentile: int,
) -> Decimal:
    if not values or percentile <= 0 or percentile > 100:
        raise CiboCompoundCapitalError(
            "compound Monte Carlo nearest-rank input is invalid"
        )
    ordered = sorted(values)
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[max(0, rank - 1)]


def _result_sha256(result: CompoundMonteCarloPathResult) -> str:
    payload = {
        "simulation_id": result.simulation_id,
        "sampled_block_ids": list(result.sampled_block_ids),
        "ending_original_base_usd": format(
            result.ending_original_base_usd,
            "f",
        ),
        "ending_generation_capacity_usd": [
            [generation, format(amount, "f")]
            for generation, amount in result.ending_generation_capacity_usd
        ],
        "protected_floor_usd": format(result.protected_floor_usd, "f"),
        "ending_realized_capital_usd": format(
            result.ending_realized_capital_usd,
            "f",
        ),
        "minimum_realized_capital_usd": format(
            result.minimum_realized_capital_usd,
            "f",
        ),
        "max_drawdown_usd": format(result.max_drawdown_usd, "f"),
        "dependency_breach_count": result.dependency_breach_count,
        "capacity_breach_count": result.capacity_breach_count,
        "accepted_episode_count": result.accepted_episode_count,
        "rejected_episode_count": result.rejected_episode_count,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
