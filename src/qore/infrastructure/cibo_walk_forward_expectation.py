"""Universal causal walk-forward expectations for CIBO capital decisions.

This module learns only from signal outcomes whose exit timestamp is at or
before the current decision timestamp. It is market/provider/platform neutral:
history is keyed by canonical Trader identity, while current provider economics
and stop geometry remain downstream current-state facts.

The estimator is causal and conservative:
- structural R: median of five chronological block means;
- capital duration: upper quartile of previously completed signal durations.

The duration change is a structural capital-lockup safeguard, not an
outcome-tuned threshold: velocity must not be optimized against a median that
systematically ignores the slower half of already-observed capital occupancy.

Cold start is explicit and non-authoritative. No future outcome, PnL, sizing,
Risk, order or execution authority is present here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext

from qore.infrastructure.account_wide_risk import TraderIdentity
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    CiboManifestShadowOutcomeObservation,
)

_BLOCK_COUNT = 5
_MINIMUM_OBSERVATIONS = 5
_IDENTITY = "CIBO_WALK_FORWARD_EMPIRICAL_V2"


def _median(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "walk-forward median requires observations"
        )
    ordered = tuple(sorted(values))
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    with localcontext() as context:
        context.prec = 100
        return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _upper_quartile(values: tuple[Decimal, ...]) -> Decimal:
    """Return the causal nearest-rank 75th percentile."""

    if not values:
        raise CiboCapitalManagementError(
            "walk-forward upper quartile requires observations"
        )
    ordered = tuple(sorted(values))
    # nearest-rank percentile: ceil(0.75 * n), converted to zero-based index.
    rank = (3 * len(ordered) + 3) // 4
    return ordered[rank - 1]


def _chronological_blocks(
    observations: tuple[CiboManifestShadowOutcomeObservation, ...],
) -> tuple[tuple[CiboManifestShadowOutcomeObservation, ...], ...]:
    if len(observations) < _BLOCK_COUNT:
        raise CiboCapitalManagementError(
            "walk-forward block estimator requires at least five observations"
        )
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (item.exit_at, item.signal_fingerprint),
        )
    )
    base, remainder = divmod(len(ordered), _BLOCK_COUNT)
    blocks: list[tuple[CiboManifestShadowOutcomeObservation, ...]] = []
    cursor = 0
    for index in range(_BLOCK_COUNT):
        size = base + (1 if index < remainder else 0)
        block = ordered[cursor : cursor + size]
        if not block:
            raise CiboCapitalManagementError(
                "walk-forward chronological block cannot be empty"
            )
        blocks.append(block)
        cursor += size
    if cursor != len(ordered):
        raise CiboCapitalManagementError(
            "walk-forward chronological block accounting drift"
        )
    return tuple(blocks)


def _block_mean_r(
    block: tuple[CiboManifestShadowOutcomeObservation, ...],
) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return sum(
            (item.gross_structural_outcome_r for item in block),
            Decimal(0),
        ) / Decimal(len(block))


def _history_sha256(
    observations: tuple[CiboManifestShadowOutcomeObservation, ...],
) -> str:
    payload = [
        {
            "signal_fingerprint": item.signal_fingerprint,
            "trader_id": item.trader_id,
            "decision_at": item.decision_at.isoformat(),
            "entry_at": item.entry_at.isoformat(),
            "exit_at": item.exit_at.isoformat(),
            "gross_structural_outcome_r": format(
                item.gross_structural_outcome_r,
                "f",
            ),
            "capital_minutes": format(item.capital_minutes, "f"),
        }
        for item in sorted(
            observations,
            key=lambda row: (row.exit_at, row.signal_fingerprint),
        )
    ]
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CiboWalkForwardExpectationSnapshot:
    trader_id: TraderIdentity
    decision_at: datetime
    evidence_available_at: datetime
    observation_count: int
    history_sha256: str
    expected_structural_r: Decimal | None
    expected_capital_minutes: Decimal | None
    chronological_block_means_r: tuple[Decimal, ...]
    expectation: CausalOpportunityExpectation
    cold_start: bool
    future_market_used: bool = False
    outcome_used_before_available: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "walk-forward snapshot decision_at must be timezone-aware"
            )
        if (
            self.evidence_available_at.tzinfo is None
            or self.evidence_available_at.utcoffset() is None
            or self.evidence_available_at > self.decision_at
        ):
            raise CiboCapitalManagementError(
                "walk-forward evidence availability exceeds decision time"
            )
        if (
            not isinstance(self.observation_count, int)
            or isinstance(self.observation_count, bool)
            or self.observation_count < 0
        ):
            raise CiboCapitalManagementError(
                "walk-forward observation_count must be non-negative int"
            )
        if (
            not isinstance(self.history_sha256, str)
            or not self.history_sha256.startswith("sha256:")
        ):
            raise CiboCapitalManagementError(
                "walk-forward history digest invalid"
            )
        if type(self.cold_start) is not bool:
            raise CiboCapitalManagementError(
                "walk-forward cold_start must be bool"
            )
        if self.cold_start:
            if (
                self.expected_structural_r is not None
                or self.expected_capital_minutes is not None
                or self.chronological_block_means_r
                or self.expectation.basis
                is not CausalExpectationBasis.COLD_START_NO_FORECAST
            ):
                raise CiboCapitalManagementError(
                    "walk-forward cold-start semantics drift"
                )
        else:
            if self.observation_count < _MINIMUM_OBSERVATIONS:
                raise CiboCapitalManagementError(
                    "walk-forward forecast lacks minimum observations"
                )
            if (
                self.expected_structural_r is None
                or self.expected_capital_minutes is None
                or self.expected_capital_minutes <= 0
                or len(self.chronological_block_means_r) != _BLOCK_COUNT
                or self.expectation.basis
                is not CausalExpectationBasis.WALK_FORWARD_EMPIRICAL_FORECAST
            ):
                raise CiboCapitalManagementError(
                    "walk-forward forecast semantics drift"
                )
        if (
            self.future_market_used
            or self.outcome_used_before_available
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "walk-forward expectation governance violated"
            )


def build_walk_forward_expectation(
    *,
    trader_id: TraderIdentity,
    decision_at: datetime,
    stop_risk_usd: Decimal,
    completed_observations: tuple[
        CiboManifestShadowOutcomeObservation, ...
    ],
) -> CiboWalkForwardExpectationSnapshot:
    """Build one expectation from information available by decision time only."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "walk-forward decision_at must be timezone-aware"
        )
    if (
        not isinstance(stop_risk_usd, Decimal)
        or not stop_risk_usd.is_finite()
        or stop_risk_usd <= 0
    ):
        raise CiboCapitalManagementError(
            "walk-forward stop risk must be finite positive Decimal"
        )
    relevant = tuple(
        sorted(
            (
                item
                for item in completed_observations
                if item.trader_id == trader_id.value
            ),
            key=lambda item: (item.exit_at, item.signal_fingerprint),
        )
    )
    if any(item.exit_at > decision_at for item in relevant):
        raise CiboCapitalManagementError(
            "walk-forward forecast received unavailable future outcome"
        )
    history_sha = _history_sha256(relevant)
    evidence_available_at = (
        relevant[-1].exit_at if relevant else decision_at
    )

    if len(relevant) < _MINIMUM_OBSERVATIONS:
        expectation = CausalOpportunityExpectation(
            evidence_id=(
                f"{_IDENTITY}:COLD_START:{history_sha}:{trader_id.value}"
            ),
            as_of=decision_at,
            basis=CausalExpectationBasis.COLD_START_NO_FORECAST,
            expected_net_value_usd=Decimal(0),
            # Placeholder only; cold-start basis cannot be used for velocity.
            expected_capital_minutes=Decimal(1),
        )
        return CiboWalkForwardExpectationSnapshot(
            trader_id=trader_id,
            decision_at=decision_at,
            evidence_available_at=evidence_available_at,
            observation_count=len(relevant),
            history_sha256=history_sha,
            expected_structural_r=None,
            expected_capital_minutes=None,
            chronological_block_means_r=(),
            expectation=expectation,
            cold_start=True,
        )

    blocks = _chronological_blocks(relevant)
    block_means = tuple(_block_mean_r(block) for block in blocks)
    expected_structural_r = _median(block_means)
    expected_minutes = _upper_quartile(
        tuple(item.capital_minutes for item in relevant)
    )
    with localcontext() as context:
        context.prec = 100
        expected_net_value_usd = expected_structural_r * stop_risk_usd

    expectation = CausalOpportunityExpectation(
        evidence_id=(
            f"{_IDENTITY}:{history_sha}:{trader_id.value}"
        ),
        as_of=decision_at,
        basis=CausalExpectationBasis.WALK_FORWARD_EMPIRICAL_FORECAST,
        expected_net_value_usd=expected_net_value_usd,
        expected_capital_minutes=expected_minutes,
    )
    return CiboWalkForwardExpectationSnapshot(
        trader_id=trader_id,
        decision_at=decision_at,
        evidence_available_at=evidence_available_at,
        observation_count=len(relevant),
        history_sha256=history_sha,
        expected_structural_r=expected_structural_r,
        expected_capital_minutes=expected_minutes,
        chronological_block_means_r=block_means,
        expectation=expectation,
        cold_start=False,
    )


def walk_forward_minimum_observations() -> int:
    return _MINIMUM_OBSERVATIONS
