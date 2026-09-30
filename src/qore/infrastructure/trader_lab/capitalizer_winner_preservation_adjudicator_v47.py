"""UTC-001 winner-preservation adjudicator for frozen interventions.

Outcomes are consumed strictly as research adjudication labels. This module
cannot discover a rule or make a productive/runtime decision.

Frozen in PR #623 comment 5902008845.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    universal_trader_certification_standard_001 as utc,
)

IDENTITY = "QORE_CAPITALIZER_WINNER_PRESERVATION_ADJUDICATOR_V47"
PREDECLARATION_COMMENT_ID = 5902008845


@dataclass(frozen=True, slots=True)
class PreservationTrade:
    trade_id: str
    realized_r: Decimal

    def __post_init__(self) -> None:
        if not self.trade_id:
            raise ValueError("winner-preservation trade_id required")
        if not self.realized_r.is_finite():
            raise ValueError("winner-preservation realized_r must be finite")


@dataclass(frozen=True, slots=True)
class WinnerPreservationReport:
    identity: str
    baseline_trades: int
    selected_trades: int
    density_preservation: Decimal
    baseline_winners: int
    selected_winners: int
    winner_count_preservation: Decimal | None
    baseline_winner_r: Decimal
    selected_winner_r: Decimal
    winner_r_preservation: Decimal | None
    removed_winners: int
    removed_losers_or_flats: int
    retained_winners: int
    retained_losers_or_flats: int
    winner_count_gate_passed: bool | None
    winner_r_gate_passed: bool | None
    passed: bool
    outcome_used_for_productive_selection: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("winner-preservation identity drift")
        if not Decimal("0") <= self.density_preservation <= Decimal("1"):
            raise ValueError("density preservation outside [0,1]")
        if self.winner_count_preservation is not None and not (
            Decimal("0") <= self.winner_count_preservation <= Decimal("1")
        ):
            raise ValueError("winner-count preservation outside [0,1]")
        if self.winner_r_preservation is not None and self.winner_r_preservation < 0:
            raise ValueError("winner-R preservation cannot be negative")
        if (
            self.outcome_used_for_productive_selection
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("winner-preservation governance drift")
        expected = (
            self.winner_count_gate_passed is True
            and self.winner_r_gate_passed is True
        )
        if self.passed != expected:
            raise ValueError("winner-preservation pass state drift")


def adjudicate_winner_preservation(
    baseline: tuple[PreservationTrade, ...],
    selected_trade_ids: frozenset[str],
) -> WinnerPreservationReport:
    if not baseline:
        raise ValueError("winner-preservation requires non-empty baseline")
    ids = [row.trade_id for row in baseline]
    if len(ids) != len(set(ids)):
        raise ValueError("winner-preservation baseline trade_id collision")
    unknown = selected_trade_ids - set(ids)
    if unknown:
        raise ValueError("winner-preservation selected ids outside baseline")

    selected = tuple(row for row in baseline if row.trade_id in selected_trade_ids)
    baseline_winners = tuple(row for row in baseline if row.realized_r > 0)
    selected_winners = tuple(row for row in selected if row.realized_r > 0)
    baseline_winner_r = sum(
        (row.realized_r for row in baseline_winners),
        Decimal("0"),
    )
    selected_winner_r = sum(
        (row.realized_r for row in selected_winners),
        Decimal("0"),
    )

    count_ratio = (
        None
        if not baseline_winners
        else Decimal(len(selected_winners)) / Decimal(len(baseline_winners))
    )
    r_ratio = (
        None
        if baseline_winner_r <= 0
        else selected_winner_r / baseline_winner_r
    )
    count_pass = (
        None
        if count_ratio is None
        else count_ratio >= utc.WINNER_COUNT_PRESERVATION_MIN
    )
    r_pass = (
        None
        if r_ratio is None
        else r_ratio >= utc.WINNER_R_PRESERVATION_MIN
    )

    selected_ids = {row.trade_id for row in selected}
    removed = tuple(row for row in baseline if row.trade_id not in selected_ids)
    return WinnerPreservationReport(
        identity=IDENTITY,
        baseline_trades=len(baseline),
        selected_trades=len(selected),
        density_preservation=Decimal(len(selected)) / Decimal(len(baseline)),
        baseline_winners=len(baseline_winners),
        selected_winners=len(selected_winners),
        winner_count_preservation=count_ratio,
        baseline_winner_r=baseline_winner_r,
        selected_winner_r=selected_winner_r,
        winner_r_preservation=r_ratio,
        removed_winners=sum(row.realized_r > 0 for row in removed),
        removed_losers_or_flats=sum(row.realized_r <= 0 for row in removed),
        retained_winners=len(selected_winners),
        retained_losers_or_flats=sum(row.realized_r <= 0 for row in selected),
        winner_count_gate_passed=count_pass,
        winner_r_gate_passed=r_pass,
        passed=count_pass is True and r_pass is True,
    )
