"""L8 Seven-Trader control/treatment reality for QORE Shared Lab.

This harness proves causal consumption, not merely aggregate metric uplift.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TraderMetricVector:
    pf: float
    expectancy_r: float
    drawdown_r: float
    sharpe: float
    sortino: float
    payoff: float
    post_cost_pf: float
    winner_preservation: float
    trade_count: int

    def __post_init__(self) -> None:
        if self.trade_count < 0:
            raise ValueError("trade_count cannot be negative")
        if not (0.0 <= self.winner_preservation <= 1.0):
            raise ValueError("winner_preservation must be in [0,1]")


@dataclass(frozen=True, slots=True)
class TraderControlTreatmentReceipt:
    trader_id: str
    control: TraderMetricVector
    treatment: TraderMetricVector
    shared_signal_count: int
    shared_consumed_count: int
    changed_decision_count: int
    false_veto_count: int
    false_opportunity_count: int
    causal_lineage_exact: bool
    no_sizing_authority: bool

    def __post_init__(self) -> None:
        counts = (
            self.shared_signal_count,
            self.shared_consumed_count,
            self.changed_decision_count,
            self.false_veto_count,
            self.false_opportunity_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("L8 counts cannot be negative")
        if self.shared_consumed_count > self.shared_signal_count:
            raise ValueError("consumed signals cannot exceed emitted signals")
        if self.changed_decision_count > self.shared_consumed_count:
            raise ValueError("changed decisions cannot exceed consumed signals")

    @property
    def mechanism_proven(self) -> bool:
        return (
            self.shared_signal_count > 0
            and self.shared_consumed_count > 0
            and self.changed_decision_count > 0
            and self.causal_lineage_exact
            and self.no_sizing_authority
        )


@dataclass(frozen=True, slots=True)
class SevenTraderRealityAssessment:
    trader_count: int
    failed_trader_ids: tuple[str, ...]
    all_traders_mechanism_proven: bool
    pooled_rescue_forbidden: bool
    l8_proven: bool


def assess_seven_trader_reality(
    receipts: tuple[TraderControlTreatmentReceipt, ...],
    *,
    expected_trader_ids: frozenset[str],
) -> SevenTraderRealityAssessment:
    if not receipts:
        raise ValueError("L8 requires trader control/treatment receipts")
    ids = tuple(item.trader_id for item in receipts)
    if len(ids) != len(set(ids)):
        raise ValueError("trader ids must be unique")
    missing = expected_trader_ids.difference(ids)
    unexpected = set(ids).difference(expected_trader_ids)
    if missing:
        raise ValueError(f"missing trader receipts: {sorted(missing)}")
    if unexpected:
        raise ValueError(f"unexpected trader receipts: {sorted(unexpected)}")

    failed = tuple(
        sorted(item.trader_id for item in receipts if not item.mechanism_proven)
    )
    return SevenTraderRealityAssessment(
        trader_count=len(receipts),
        failed_trader_ids=failed,
        all_traders_mechanism_proven=not failed,
        pooled_rescue_forbidden=True,
        l8_proven=not failed and len(receipts) == len(expected_trader_ids),
    )
