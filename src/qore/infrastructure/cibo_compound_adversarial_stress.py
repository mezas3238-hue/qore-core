"""Preregistered adversarial Compound stress transforms for CIBO.

Stress transforms operate on already observed/research episodes. They are
diagnostic adversarial worlds, not production forecasts and not market
probabilities. The unchanged dependency-aware Compound Monte Carlo engine is
used after transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
    CompoundMonteCarloSummary,
    run_compound_path_monte_carlo,
)

COMPOUND_STRESS_POLICY_ID = "CIBO_COMPOUND_ADVERSARIAL_STRESS_MATRIX_V1"
COMPOUND_STRESS_POLICY_SHA256 = (
    "sha256:99ef9dbf2f6c98b161ee5d04568ba0b89bd6dc5d5f8b11cda2f10ef2f64ac46d"
)


class CompoundStressKind(StrEnum):
    LOSSES_FIRST = "LOSSES_FIRST"
    WINNER_DROUGHT = "WINNER_DROUGHT"
    CORRELATION_CONVERGENCE = "CORRELATION_CONVERGENCE"
    MARGIN_HIKE = "MARGIN_HIKE"
    CAPITAL_LOCKUP = "CAPITAL_LOCKUP"
    GAP_AND_SLIPPAGE = "GAP_AND_SLIPPAGE"
    GEN_N_LOSSES_EARLY = "GEN_N_LOSSES_EARLY"


@dataclass(frozen=True, slots=True)
class CompoundStressScenario:
    scenario_id: str
    kind: CompoundStressKind
    severity: Decimal
    evidence_sha256: str
    market_probability_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise CiboCompoundCapitalError(
                "compound stress scenario_id is required"
            )
        if type(self.kind) is not CompoundStressKind:
            raise CiboCompoundCapitalError(
                "compound stress kind is invalid"
            )
        if (
            not isinstance(self.severity, Decimal)
            or not self.severity.is_finite()
            or self.severity <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound stress severity must be positive Decimal"
            )
        if (
            not isinstance(self.evidence_sha256, str)
            or not self.evidence_sha256.startswith("sha256:")
            or len(self.evidence_sha256) != 71
        ):
            raise CiboCompoundCapitalError(
                "compound stress evidence SHA is invalid"
            )
        if self.market_probability_claimed or self.productive_authority:
            raise CiboCompoundCapitalError(
                "compound stress cannot claim probability/authority"
            )


@dataclass(frozen=True, slots=True)
class CompoundStressResult:
    scenario: CompoundStressScenario
    monte_carlo: CompoundMonteCarloSummary
    baseline_episode_count: int
    stressed_episode_count: int
    market_probability_claimed: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, CompoundStressScenario):
            raise CiboCompoundCapitalError(
                "compound stress result scenario is invalid"
            )
        if not isinstance(self.monte_carlo, CompoundMonteCarloSummary):
            raise CiboCompoundCapitalError(
                "compound stress result Monte Carlo is invalid"
            )
        if (
            self.baseline_episode_count <= 0
            or self.stressed_episode_count <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound stress episode counts must be positive"
            )
        if self.market_probability_claimed or self.certification_ready:
            raise CiboCompoundCapitalError(
                "compound stress result cannot claim certification"
            )


def run_compound_adversarial_stress(
    *,
    initial: CompoundMonteCarloInitialState,
    episodes: tuple[CompoundMonteCarloEpisode, ...],
    scenarios: tuple[CompoundStressScenario, ...],
    simulations: int,
    draws_per_path: int,
    components_per_block: int,
    base_seed: int,
) -> tuple[CompoundStressResult, ...]:
    """Run every preregistered stress through unchanged Compound MC mechanics."""

    if not episodes or not scenarios:
        raise CiboCompoundCapitalError(
            "compound stress requires episodes and scenarios"
        )
    ids = tuple(item.scenario_id for item in scenarios)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "compound stress scenario ids must be unique"
        )
    results: list[CompoundStressResult] = []
    for index, scenario in enumerate(scenarios):
        stressed = apply_compound_stress(
            episodes=episodes,
            scenario=scenario,
        )
        summary = run_compound_path_monte_carlo(
            initial=initial,
            episodes=stressed,
            simulations=simulations,
            draws_per_path=draws_per_path,
            components_per_block=components_per_block,
            base_seed=base_seed + index * 100_000,
        )
        results.append(
            CompoundStressResult(
                scenario=scenario,
                monte_carlo=summary,
                baseline_episode_count=len(episodes),
                stressed_episode_count=len(stressed),
                market_probability_claimed=False,
                certification_ready=False,
            )
        )
    return tuple(results)


def apply_compound_stress(
    *,
    episodes: tuple[CompoundMonteCarloEpisode, ...],
    scenario: CompoundStressScenario,
) -> tuple[CompoundMonteCarloEpisode, ...]:
    """Transform one observed episode surface into an explicit stress world."""

    if not episodes:
        raise CiboCompoundCapitalError(
            "compound stress requires non-empty episode surface"
        )
    if scenario.kind is CompoundStressKind.WINNER_DROUGHT:
        losing = tuple(item for item in episodes if item.realized_pnl_usd <= 0)
        return losing if losing else _zero_positive_pnl(episodes)

    if scenario.kind is CompoundStressKind.MARGIN_HIKE:
        return tuple(
            replace(
                item,
                margin_usd=item.margin_usd * (Decimal(1) + scenario.severity),
            )
            for item in episodes
        )

    if scenario.kind is CompoundStressKind.CAPITAL_LOCKUP:
        return tuple(
            replace(
                item,
                settled_at=item.settled_at
                + _scale_duration(_duration(item), scenario.severity),
            )
            for item in episodes
        )

    if scenario.kind is CompoundStressKind.GAP_AND_SLIPPAGE:
        return tuple(
            replace(
                item,
                realized_pnl_usd=_stressed_pnl(
                    item.realized_pnl_usd,
                    item.stop_risk_usd,
                    scenario.severity,
                ),
                protected_floor_graduation_usd=Decimal(0),
                floor_evidence_sha256=None,
            )
            for item in episodes
        )

    if scenario.kind is CompoundStressKind.CORRELATION_CONVERGENCE:
        anchor = min(item.deployed_at for item in episodes)
        return tuple(
            replace(
                item,
                deployed_at=anchor + timedelta(microseconds=index),
                settled_at=(
                    anchor
                    + timedelta(microseconds=index)
                    + _duration(item)
                ),
            )
            for index, item in enumerate(episodes)
        )

    ordered = _ordered_stress(episodes, scenario.kind)
    cursor = min(item.deployed_at for item in episodes)
    shifted: list[CompoundMonteCarloEpisode] = []
    for index, item in enumerate(ordered):
        duration = _duration(item)
        start = cursor + timedelta(microseconds=index)
        shifted.append(
            replace(
                item,
                deployed_at=start,
                settled_at=start + duration,
            )
        )
        cursor = start + duration
    return tuple(shifted)


def _ordered_stress(
    episodes: tuple[CompoundMonteCarloEpisode, ...],
    kind: CompoundStressKind,
) -> tuple[CompoundMonteCarloEpisode, ...]:
    if kind is CompoundStressKind.LOSSES_FIRST:
        return tuple(
            sorted(
                episodes,
                key=lambda item: (
                    item.realized_pnl_usd > 0,
                    item.deployed_at,
                    item.episode_id,
                ),
            )
        )
    if kind is CompoundStressKind.GEN_N_LOSSES_EARLY:
        return tuple(
            sorted(
                episodes,
                key=lambda item: (
                    not (
                        item.source_generation > 1
                        and item.realized_pnl_usd < 0
                    ),
                    -item.source_generation,
                    item.deployed_at,
                    item.episode_id,
                ),
            )
        )
    raise CiboCompoundCapitalError(
        "compound stress ordering kind is unsupported"
    )


def _duration(item: CompoundMonteCarloEpisode) -> timedelta:
    return item.settled_at - item.deployed_at


def _scale_duration(duration: timedelta, factor: Decimal) -> timedelta:
    total_microseconds = (
        (
            duration.days * 86_400
            + duration.seconds
        )
        * 1_000_000
        + duration.microseconds
    )
    scaled_microseconds = int(Decimal(total_microseconds) * factor)
    return timedelta(microseconds=scaled_microseconds)


def _stressed_pnl(
    pnl: Decimal,
    stop_risk_usd: Decimal,
    severity: Decimal,
) -> Decimal:
    if pnl > 0:
        haircut = min(pnl, stop_risk_usd * severity)
        return pnl - haircut
    return pnl - stop_risk_usd * severity


def _zero_positive_pnl(
    episodes: tuple[CompoundMonteCarloEpisode, ...],
) -> tuple[CompoundMonteCarloEpisode, ...]:
    return tuple(
        replace(
            item,
            realized_pnl_usd=(
                Decimal(0) if item.realized_pnl_usd > 0
                else item.realized_pnl_usd
            ),
            protected_floor_graduation_usd=Decimal(0),
            floor_evidence_sha256=None,
        )
        for item in episodes
    )
