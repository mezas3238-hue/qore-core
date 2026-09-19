"""Execution-cost stress perturbations for Capitalizer Behavior Lab.

The stress is specification data, not a claim about any broker. It applies additional explicit
cost in R to already-observed research outcomes while preserving the original causal snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_behavior_lab import (
    CapitalizerBehaviorEpisode,
    CapitalizerBehaviorOutcome,
    canonical_behavior_episodes,
)


def _validate_cost(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field_name} must be finite non-negative Decimal")


@dataclass(frozen=True, slots=True)
class CapitalizerCostStressSpec:
    additional_spread_r: Decimal = Decimal("0")
    additional_commission_r: Decimal = Decimal("0")
    additional_slippage_r: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        _validate_cost(self.additional_spread_r, field_name="additional_spread_r")
        _validate_cost(self.additional_commission_r, field_name="additional_commission_r")
        _validate_cost(self.additional_slippage_r, field_name="additional_slippage_r")

    @property
    def total_additional_cost_r(self) -> Decimal:
        return (
            self.additional_spread_r
            + self.additional_commission_r
            + self.additional_slippage_r
        )


def apply_cost_stress(
    episodes: tuple[CapitalizerBehaviorEpisode, ...],
    *,
    spec: CapitalizerCostStressSpec,
) -> tuple[CapitalizerBehaviorEpisode, ...]:
    """Apply deterministic per-trade cost stress without changing pre-entry state."""

    ordered = canonical_behavior_episodes(episodes)
    additional = spec.total_additional_cost_r
    stressed: list[CapitalizerBehaviorEpisode] = []
    for episode in ordered:
        outcome = episode.outcome
        stressed_cost = outcome.explicit_cost_r + additional
        stressed.append(
            CapitalizerBehaviorEpisode(
                snapshot=episode.snapshot,
                outcome=CapitalizerBehaviorOutcome(
                    episode_id=outcome.episode_id,
                    closed_at=outcome.closed_at,
                    gross_r=outcome.gross_r,
                    explicit_cost_r=stressed_cost,
                    net_r=outcome.gross_r - stressed_cost,
                    exit_reason=outcome.exit_reason,
                    loss_cause_tags=(
                        outcome.loss_cause_tags
                        if outcome.gross_r - stressed_cost < 0
                        else ()
                    ),
                ),
            )
        )
    return tuple(stressed)
