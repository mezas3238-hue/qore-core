"""Temporal replication harness for Compound/GEN-C9 research.

The harness requires contiguous, non-overlapping folds and one explicit
account-local initial state per fold. It runs the same frozen Compound Monte
Carlo mechanics in every fold. It does not pool outcomes across folds and does
not claim economic replication without a separately preregistered gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
    CompoundMonteCarloSummary,
    run_compound_path_monte_carlo,
)

COMPOUND_TEMPORAL_REPLICATION_ID = "CIBO_COMPOUND_TEMPORAL_REPLICATION_V1"
COMPOUND_TEMPORAL_REPLICATION_SHA256 = (
    "sha256:792db6db7efbc0a8427d475f5b72e178efdb0069ea31d0bdac3444fc9b13c5d2"
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound temporal replication {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CompoundTemporalFold:
    fold_id: str
    start_at: datetime
    end_at: datetime
    initial_state: CompoundMonteCarloInitialState
    episodes: tuple[CompoundMonteCarloEpisode, ...]
    provider_economics_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.fold_id:
            raise CiboCompoundCapitalError(
                "compound temporal fold identity is required"
            )
        _aware(self.start_at, "start_at")
        _aware(self.end_at, "end_at")
        if self.end_at <= self.start_at:
            raise CiboCompoundCapitalError(
                "compound temporal fold end must follow start"
            )
        if not isinstance(
            self.initial_state,
            CompoundMonteCarloInitialState,
        ):
            raise CiboCompoundCapitalError(
                "compound temporal fold initial state is invalid"
            )
        if not self.episodes:
            raise CiboCompoundCapitalError(
                "compound temporal fold requires episodes"
            )
        for item in self.episodes:
            if item.deployed_at < self.start_at or item.settled_at > self.end_at:
                raise CiboCompoundCapitalError(
                    "compound temporal fold episode escapes fold boundary"
                )
        if self.provider_economics_sha256 is not None:
            if (
                not self.provider_economics_sha256.startswith("sha256:")
                or len(self.provider_economics_sha256) != 71
            ):
                raise CiboCompoundCapitalError(
                    "compound temporal provider economics SHA is invalid"
                )


@dataclass(frozen=True, slots=True)
class CompoundTemporalFoldResult:
    fold_id: str
    start_at: datetime
    end_at: datetime
    summary: CompoundMonteCarloSummary

    def __post_init__(self) -> None:
        if not self.fold_id:
            raise CiboCompoundCapitalError(
                "compound temporal fold result identity is required"
            )
        if not isinstance(self.summary, CompoundMonteCarloSummary):
            raise CiboCompoundCapitalError(
                "compound temporal fold result summary is invalid"
            )


@dataclass(frozen=True, slots=True)
class CompoundTemporalReplicationReport:
    research_id: str
    fold_count: int
    fold_results: tuple[CompoundTemporalFoldResult, ...]
    minimum_ending_capital_across_folds_usd: Decimal
    maximum_p95_drawdown_across_folds_usd: Decimal
    dependency_breach_fold_count: int
    capacity_breach_fold_count: int
    same_policy_mechanics_all_folds: bool = True
    outcomes_pooled_across_folds: bool = False
    economic_replication_claimed: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.research_id:
            raise CiboCompoundCapitalError(
                "compound temporal report identity is required"
            )
        if self.fold_count != len(self.fold_results) or self.fold_count < 2:
            raise CiboCompoundCapitalError(
                "compound temporal report fold count is invalid"
            )
        if (
            not self.same_policy_mechanics_all_folds
            or self.outcomes_pooled_across_folds
            or self.economic_replication_claimed
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "compound temporal report governance drift"
            )


def run_compound_temporal_replication(
    *,
    research_id: str,
    folds: tuple[CompoundTemporalFold, ...],
    simulations_per_fold: int,
    draws_per_path: int,
    components_per_block: int,
    base_seed: int,
) -> CompoundTemporalReplicationReport:
    """Run the unchanged Compound MC engine on strictly separated folds."""

    if not research_id:
        raise CiboCompoundCapitalError(
            "compound temporal research_id is required"
        )
    if len(folds) < 2:
        raise CiboCompoundCapitalError(
            "compound temporal replication requires at least two folds"
        )
    ordered = tuple(sorted(folds, key=lambda item: item.start_at))
    if ordered != folds:
        raise CiboCompoundCapitalError(
            "compound temporal folds must be chronological"
        )
    ids = tuple(item.fold_id for item in folds)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "compound temporal fold ids must be unique"
        )
    for left, right in zip(folds, folds[1:], strict=False):
        if left.end_at > right.start_at:
            raise CiboCompoundCapitalError(
                "compound temporal folds must not overlap"
            )

    results: list[CompoundTemporalFoldResult] = []
    for index, fold in enumerate(folds):
        summary = run_compound_path_monte_carlo(
            initial=fold.initial_state,
            episodes=fold.episodes,
            simulations=simulations_per_fold,
            draws_per_path=draws_per_path,
            components_per_block=components_per_block,
            base_seed=base_seed + index * 1_000_000,
        )
        results.append(
            CompoundTemporalFoldResult(
                fold_id=fold.fold_id,
                start_at=fold.start_at,
                end_at=fold.end_at,
                summary=summary,
            )
        )
    rows = tuple(results)
    return CompoundTemporalReplicationReport(
        research_id=research_id,
        fold_count=len(rows),
        fold_results=rows,
        minimum_ending_capital_across_folds_usd=min(
            item.summary.minimum_ending_realized_capital_usd
            for item in rows
        ),
        maximum_p95_drawdown_across_folds_usd=max(
            item.summary.p95_max_drawdown_usd for item in rows
        ),
        dependency_breach_fold_count=sum(
            item.summary.dependency_breach_paths > 0 for item in rows
        ),
        capacity_breach_fold_count=sum(
            item.summary.capacity_breach_paths > 0 for item in rows
        ),
        same_policy_mechanics_all_folds=True,
        outcomes_pooled_across_folds=False,
        economic_replication_claimed=False,
        certification_ready=False,
    )
