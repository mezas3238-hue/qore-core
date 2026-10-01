"""Phase21 empirical screen on the owner-authorized historical shadow.

The nine-month common population replaces the physical wait.  This screen uses
only the post-TRAIN Phase19 validation segment so the frozen TRAIN priors are
not evaluated on their own estimation rows.  Results remain R/NCU denominated:
historical provider USD economics are never fabricated and 2017H1 is not read.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19CapitalNumeraireContract,
    Phase19NormalizedCapitalReplay,
    Phase19NormalizedReplayTrade,
    replay_phase19_normalized_capital,
)
from qore.infrastructure.cibo_ce2i_phase20_capital_state_monte_carlo import (
    build_phase20e_temporal_blocks,
    sample_phase20e_block_path,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    FROZEN_TRAIN_PRIORS,
    frozen_train_prior_for,
)

PHASE21_SHADOW_SCREEN_ID = "CIBO_PHASE21_HISTORICAL_SHADOW_SCREEN_V1"
VALIDATION_START = datetime(2022, 3, 9, 17, 0, tzinfo=UTC)
VALIDATION_END = datetime(2022, 6, 29, 9, 0, tzinfo=UTC)
INITIAL_CAPITAL_NCU = Decimal("100")
FOLD_COUNT = 4
MINIMUM_SELECTED_OUTCOMES = 60
MINIMUM_FOLD_OUTCOMES = 40
MONTE_CARLO_SIMULATIONS = 1000
MONTE_CARLO_BASE_SEED = 21021
EXPECTED_ROWS_BY_TRADER = {
    TraderLineage.R34_XAUUSD: 47,
    TraderLineage.R38_EURUSD: 55,
    TraderLineage.R38_GBPJPY: 55,
    TraderLineage.R42_AUDJPY: 52,
    TraderLineage.R43_GBPUSD: 63,
    TraderLineage.VT08_FOREX: 21,
    TraderLineage.VT31_NAS100: 39,
}
EXPECTED_VALIDATION_ROWS = sum(EXPECTED_ROWS_BY_TRADER.values())


@dataclass(frozen=True, slots=True)
class Phase21ShadowReplayMetrics:
    opportunity_count: int
    realized_delta_ncu: Decimal
    max_drawdown_ncu: Decimal
    risk_capacity_minutes_ncu: Decimal
    capital_productivity_ncu_per_risk_minute: Decimal
    capacity_breach_observed: bool


@dataclass(frozen=True, slots=True)
class Phase21ShadowFold:
    fold_id: str
    decision_epochs: int
    baseline_outcomes: int
    selected_outcomes: int
    represented_lineages: int
    baseline_delta_ncu: Decimal
    policy_delta_ncu: Decimal


@dataclass(frozen=True, slots=True)
class Phase21ShadowMonteCarlo:
    simulation_count: int
    source_block_count: int
    policy_median_ending_delta_ncu: Decimal
    baseline_median_ending_delta_ncu: Decimal
    policy_p95_drawdown_ncu: Decimal
    baseline_p95_drawdown_ncu: Decimal
    policy_positive_paths: int
    baseline_positive_paths: int
    policy_capacity_breach_paths: int
    baseline_capacity_breach_paths: int


@dataclass(frozen=True, slots=True)
class Phase21HistoricalShadowScreen:
    screen_id: str
    passed: bool
    reasons: tuple[str, ...]
    validation_rows: int
    decision_epochs: int
    distinct_trading_days: int
    represented_lineages: int
    selected_outcomes: int
    selected_lineages: tuple[str, ...]
    baseline: Phase21ShadowReplayMetrics
    policy: Phase21ShadowReplayMetrics
    folds: tuple[Phase21ShadowFold, ...]
    monte_carlo: Phase21ShadowMonteCarlo
    fold_positive_count: int
    fold_positivity_is_diagnostic_only: bool
    provider_economics_claimed: bool = False
    historical_usd_claimed: bool = False
    final_holdout_2017h1_read: bool = False
    policy_retuned_from_shadow_outcomes: bool = False

    def __post_init__(self) -> None:
        if self.screen_id != PHASE21_SHADOW_SCREEN_ID:
            raise CiboCapitalManagementError("Phase21 shadow screen identity drift")
        if (
            self.provider_economics_claimed
            or self.historical_usd_claimed
            or self.final_holdout_2017h1_read
            or self.policy_retuned_from_shadow_outcomes
        ):
            raise CiboCapitalManagementError(
                "Phase21 historical shadow governance violation"
            )
        if self.passed != (not self.reasons):
            raise CiboCapitalManagementError("Phase21 shadow PASS/reason drift")


def frozen_v3_structural_selection(trader_id: TraderLineage) -> bool:
    """Use only the frozen TRAIN prior sign; no shadow outcome enters selection."""

    prior = frozen_train_prior_for(trader_id)
    return prior.expected_structural_r > 0


def evaluate_phase21_historical_shadow(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase21HistoricalShadowScreen:
    if not trades:
        raise CiboCapitalManagementError("Phase21 shadow requires validation trades")
    ordered = tuple(
        sorted(
            trades,
            key=lambda item: (
                item.allocation.decision_at,
                item.opportunity.entry_at,
                item.opportunity.trader_id.value,
                item.opportunity.signal_fingerprint,
            ),
        )
    )
    fingerprints = tuple(item.opportunity.signal_fingerprint for item in ordered)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError("Phase21 shadow duplicate signals")
    if any(
        item.allocation.decision_at < VALIDATION_START
        or item.opportunity.exit_at > VALIDATION_END
        for item in ordered
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow row outside post-TRAIN validation window"
        )
    if any(item.allocation.outcome_aware for item in ordered):
        raise CiboCapitalManagementError(
            "Phase21 shadow allocation cannot be outcome-aware"
        )

    lineage_counts = Counter(item.opportunity.trader_id for item in ordered)
    reasons: list[str] = []
    if len(ordered) != EXPECTED_VALIDATION_ROWS:
        reasons.append("VALIDATION_ROW_COUNT_DRIFT")
    for trader, expected in EXPECTED_ROWS_BY_TRADER.items():
        if lineage_counts.get(trader, 0) != expected:
            reasons.append(f"LINEAGE_ROW_COUNT_DRIFT:{trader.value}")

    selected = tuple(
        item
        for item in ordered
        if frozen_v3_structural_selection(item.opportunity.trader_id)
    )
    baseline_replay = _replay(ordered)
    policy_replay = _replay(selected)
    baseline = _metrics(baseline_replay, len(ordered))
    policy = _metrics(policy_replay, len(selected))

    decision_times = tuple(
        sorted({item.allocation.decision_at for item in ordered})
    )
    trading_days = {
        item.allocation.decision_at.date()
        for item in ordered
    }
    folds = _folds(ordered, decision_times)
    monte_carlo = _paired_monte_carlo(ordered)

    if len(decision_times) < 80:
        reasons.append("MINIMUM_DECISION_EPOCHS_NOT_MET")
    if len(ordered) < 200:
        reasons.append("MINIMUM_CANDIDATE_OUTCOMES_NOT_MET")
    if len(selected) < MINIMUM_SELECTED_OUTCOMES:
        reasons.append("MINIMUM_SELECTED_OUTCOMES_NOT_MET")
    if len(trading_days) < 20:
        reasons.append("MINIMUM_TRADING_DAYS_NOT_MET")
    if len(lineage_counts) != 7:
        reasons.append("SEVEN_LINEAGES_NOT_REPRESENTED")
    if any(item.baseline_outcomes < MINIMUM_FOLD_OUTCOMES for item in folds):
        reasons.append("MINIMUM_FOLD_OUTCOMES_NOT_MET")
    if any(item.represented_lineages < 4 for item in folds):
        reasons.append("MINIMUM_FOLD_LINEAGES_NOT_MET")
    if policy.realized_delta_ncu <= 0:
        reasons.append("POLICY_AGGREGATE_DELTA_NOT_POSITIVE")
    if policy.realized_delta_ncu < baseline.realized_delta_ncu:
        reasons.append("POLICY_AGGREGATE_DELTA_BELOW_BASELINE")
    if policy.max_drawdown_ncu > baseline.max_drawdown_ncu:
        reasons.append("POLICY_DRAWDOWN_ABOVE_BASELINE")
    if (
        policy.capital_productivity_ncu_per_risk_minute
        <= baseline.capital_productivity_ncu_per_risk_minute
    ):
        reasons.append("POLICY_CAPITAL_PRODUCTIVITY_NOT_ABOVE_BASELINE")
    if policy.capacity_breach_observed or baseline.capacity_breach_observed:
        reasons.append("CAPITAL_CAPACITY_BREACH")
    if (
        monte_carlo.policy_median_ending_delta_ncu
        < monte_carlo.baseline_median_ending_delta_ncu
    ):
        reasons.append("MC_POLICY_MEDIAN_BELOW_BASELINE")
    if (
        monte_carlo.policy_p95_drawdown_ncu
        > monte_carlo.baseline_p95_drawdown_ncu
    ):
        reasons.append("MC_POLICY_P95_DRAWDOWN_ABOVE_BASELINE")
    if (
        monte_carlo.policy_capacity_breach_paths
        or monte_carlo.baseline_capacity_breach_paths
    ):
        reasons.append("MC_CAPACITY_BREACH_PATH")

    selected_lineages = tuple(
        prior.trader_id.value
        for prior in FROZEN_TRAIN_PRIORS
        if prior.expected_structural_r > 0
    )
    fold_positive_count = sum(
        item.policy_delta_ncu > 0 for item in folds
    )
    return Phase21HistoricalShadowScreen(
        screen_id=PHASE21_SHADOW_SCREEN_ID,
        passed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        validation_rows=len(ordered),
        decision_epochs=len(decision_times),
        distinct_trading_days=len(trading_days),
        represented_lineages=len(lineage_counts),
        selected_outcomes=len(selected),
        selected_lineages=selected_lineages,
        baseline=baseline,
        policy=policy,
        folds=folds,
        monte_carlo=monte_carlo,
        fold_positive_count=fold_positive_count,
        fold_positivity_is_diagnostic_only=True,
    )


def _replay(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase19NormalizedCapitalReplay:
    contract = Phase19CapitalNumeraireContract(
        contract_id="CIBO_PHASE21_SHADOW_STRUCTURAL_STOP_NCU_V1"
    )
    return replay_phase19_normalized_capital(
        contract=contract,
        initial_capital_ncu=INITIAL_CAPITAL_NCU,
        trades=trades,
    )


def _metrics(
    replay: Phase19NormalizedCapitalReplay,
    count: int,
) -> Phase21ShadowReplayMetrics:
    minutes = replay.risk_capacity_minutes_ncu
    productivity = (
        replay.total_realized_delta_ncu / minutes
        if minutes > 0
        else Decimal(0)
    )
    return Phase21ShadowReplayMetrics(
        opportunity_count=count,
        realized_delta_ncu=replay.total_realized_delta_ncu,
        max_drawdown_ncu=replay.max_drawdown_ncu,
        risk_capacity_minutes_ncu=minutes,
        capital_productivity_ncu_per_risk_minute=productivity,
        capacity_breach_observed=replay.capacity_breach_observed,
    )


def _folds(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
    decision_times: tuple[datetime, ...],
) -> tuple[Phase21ShadowFold, ...]:
    base, remainder = divmod(len(decision_times), FOLD_COUNT)
    cursor = 0
    result: list[Phase21ShadowFold] = []
    for index in range(FOLD_COUNT):
        size = base + (1 if index < remainder else 0)
        times = set(decision_times[cursor : cursor + size])
        cursor += size
        baseline = tuple(
            item for item in trades if item.allocation.decision_at in times
        )
        policy = tuple(
            item
            for item in baseline
            if frozen_v3_structural_selection(item.opportunity.trader_id)
        )
        baseline_replay = _replay(baseline)
        policy_replay = _replay(policy)
        result.append(
            Phase21ShadowFold(
                fold_id=f"WF{index + 1}",
                decision_epochs=len(times),
                baseline_outcomes=len(baseline),
                selected_outcomes=len(policy),
                represented_lineages=len(
                    {item.opportunity.trader_id for item in baseline}
                ),
                baseline_delta_ncu=baseline_replay.total_realized_delta_ncu,
                policy_delta_ncu=policy_replay.total_realized_delta_ncu,
            )
        )
    return tuple(result)


def _paired_monte_carlo(
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> Phase21ShadowMonteCarlo:
    blocks = build_phase20e_temporal_blocks(
        trades=trades,
        components_per_block=1,
    )
    policy_deltas: list[Decimal] = []
    baseline_deltas: list[Decimal] = []
    policy_drawdowns: list[Decimal] = []
    baseline_drawdowns: list[Decimal] = []
    policy_positive = 0
    baseline_positive = 0
    policy_breaches = 0
    baseline_breaches = 0

    for index in range(MONTE_CARLO_SIMULATIONS):
        path = sample_phase20e_block_path(
            blocks=blocks,
            draws_per_path=len(blocks),
            seed=MONTE_CARLO_BASE_SEED + index,
            simulation_id=f"PHASE21_SHADOW_MC_{index:04d}",
        )
        baseline_replay = _replay(path.trades)
        policy_trades = tuple(
            item
            for item in path.trades
            if frozen_v3_structural_selection(item.opportunity.trader_id)
        )
        policy_replay = _replay(policy_trades)
        baseline_delta = baseline_replay.total_realized_delta_ncu
        policy_delta = policy_replay.total_realized_delta_ncu
        baseline_deltas.append(baseline_delta)
        policy_deltas.append(policy_delta)
        baseline_drawdowns.append(baseline_replay.max_drawdown_ncu)
        policy_drawdowns.append(policy_replay.max_drawdown_ncu)
        baseline_positive += int(baseline_delta > 0)
        policy_positive += int(policy_delta > 0)
        baseline_breaches += int(baseline_replay.capacity_breach_observed)
        policy_breaches += int(policy_replay.capacity_breach_observed)

    return Phase21ShadowMonteCarlo(
        simulation_count=MONTE_CARLO_SIMULATIONS,
        source_block_count=len(blocks),
        policy_median_ending_delta_ncu=_median(tuple(policy_deltas)),
        baseline_median_ending_delta_ncu=_median(tuple(baseline_deltas)),
        policy_p95_drawdown_ncu=_p95(tuple(policy_drawdowns)),
        baseline_p95_drawdown_ncu=_p95(tuple(baseline_drawdowns)),
        policy_positive_paths=policy_positive,
        baseline_positive_paths=baseline_positive,
        policy_capacity_breach_paths=policy_breaches,
        baseline_capacity_breach_paths=baseline_breaches,
    )


def _median(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    size = len(ordered)
    midpoint = size // 2
    if size % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def _p95(values: tuple[Decimal, ...]) -> Decimal:
    ordered = sorted(values)
    rank = (95 * len(ordered) + 99) // 100
    return ordered[max(0, rank - 1)]
