"""Phase 19F overlap-conditioned dependence evidence without historical sizing.

This module measures post-trade outcome dependence only after the overlap pairs
are fixed from causal chronology. It deliberately avoids USD PnL and historical
Trader sizing.

The evidence is descriptive research only. It cannot change capital allocation,
QORE Risk, sizing or execution until a later causal WFO/falsification layer
authorizes a specific use.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)

_PAIR_KEYS = tuple(
    tuple(sorted((left, right), key=lambda trader: trader.value))
    for index, left in enumerate(PHASE19_REQUIRED_TRADERS)
    for right in PHASE19_REQUIRED_TRADERS[index + 1 :]
)


def _finite(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


@dataclass(frozen=True, slots=True)
class Phase19GeometryOutcome:
    opportunity: Phase19ChronologicalOpportunity
    normalized_outcome_r: Decimal
    evidence_id: str

    def __post_init__(self) -> None:
        _finite(self.normalized_outcome_r, name="normalized_outcome_r")
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase 19 geometry outcome evidence_id is required"
            )


@dataclass(frozen=True, slots=True)
class Phase19PairDependenceEvidence:
    left_trader: TraderLineage
    right_trader: TraderLineage
    overlapping_pairs: int
    left_loss_pairs: int
    right_loss_pairs: int
    joint_loss_pairs: int
    same_nonzero_sign_pairs: int
    left_loss_rate: Decimal | None
    right_loss_rate: Decimal | None
    joint_loss_rate: Decimal | None
    independent_joint_loss_rate: Decimal | None
    joint_loss_excess: Decimal | None
    same_nonzero_sign_rate: Decimal | None

    def __post_init__(self) -> None:
        for trader in (self.left_trader, self.right_trader):
            if trader not in PHASE19_REQUIRED_TRADERS:
                raise CiboCapitalManagementError(
                    "Phase 19 dependence pair outside supported Traders"
                )
        if self.left_trader is self.right_trader:
            raise CiboCapitalManagementError(
                "Phase 19 dependence pair requires distinct Traders"
            )
        for name in (
            "overlapping_pairs",
            "left_loss_pairs",
            "right_loss_pairs",
            "joint_loss_pairs",
            "same_nonzero_sign_pairs",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCapitalManagementError(
                    f"Phase 19 dependence {name} must be non-negative int"
                )
        if any(
            value > self.overlapping_pairs
            for value in (
                self.left_loss_pairs,
                self.right_loss_pairs,
                self.joint_loss_pairs,
                self.same_nonzero_sign_pairs,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase 19 dependence count exceeds overlap sample"
            )
        rates = (
            self.left_loss_rate,
            self.right_loss_rate,
            self.joint_loss_rate,
            self.independent_joint_loss_rate,
            self.joint_loss_excess,
            self.same_nonzero_sign_rate,
        )
        if self.overlapping_pairs == 0:
            if any(value is not None for value in rates):
                raise CiboCapitalManagementError(
                    "zero-overlap dependence evidence cannot carry rates"
                )
        else:
            if any(value is None for value in rates):
                raise CiboCapitalManagementError(
                    "nonzero-overlap dependence evidence requires rates"
                )
            for value in rates:
                assert value is not None
                _finite(value, name="dependence rate")
            for value in (
                self.left_loss_rate,
                self.right_loss_rate,
                self.joint_loss_rate,
                self.independent_joint_loss_rate,
                self.same_nonzero_sign_rate,
            ):
                assert value is not None
                if not Decimal(0) <= value <= Decimal(1):
                    raise CiboCapitalManagementError(
                        "Phase 19 dependence probability outside [0, 1]"
                    )

    @property
    def unordered_key(self) -> tuple[TraderLineage, TraderLineage]:
        left, right = sorted(
            (self.left_trader, self.right_trader),
            key=lambda trader: trader.value,
        )
        return left, right


@dataclass(frozen=True, slots=True)
class Phase19DependenceAtlas:
    pair_evidence: tuple[Phase19PairDependenceEvidence, ...]
    total_cross_trader_overlap_pairs: int
    outcomes_used: bool = True
    historical_sizing_used: bool = False
    usd_pnl_used: bool = False
    provider_economics_used: bool = False
    descriptive_only: bool = True
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if type(self.total_cross_trader_overlap_pairs) is not int:
            raise CiboCapitalManagementError(
                "Phase 19 dependence total overlap must be int"
            )
        if self.total_cross_trader_overlap_pairs < 0:
            raise CiboCapitalManagementError(
                "Phase 19 dependence total overlap cannot be negative"
            )
        keys = tuple(item.unordered_key for item in self.pair_evidence)
        if len(keys) != len(set(keys)) or set(keys) != set(_PAIR_KEYS):
            raise CiboCapitalManagementError(
                "Phase 19 dependence requires complete seven-Trader matrix"
            )
        if sum(item.overlapping_pairs for item in self.pair_evidence) != (
            self.total_cross_trader_overlap_pairs
        ):
            raise CiboCapitalManagementError(
                "Phase 19 dependence overlap total drift"
            )
        if not self.outcomes_used or not self.descriptive_only:
            raise CiboCapitalManagementError(
                "Phase 19 dependence evidence semantics drift"
            )
        if (
            self.historical_sizing_used
            or self.usd_pnl_used
            or self.provider_economics_used
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase 19 dependence governance drift"
            )


def measure_phase19_overlap_dependence(
    observations: tuple[Phase19GeometryOutcome, ...],
) -> Phase19DependenceAtlas:
    """Measure overlap-conditioned joint-loss evidence without sizing."""

    if not observations:
        raise CiboCapitalManagementError(
            "Phase 19 dependence requires observations"
        )
    fingerprints = tuple(
        (
            item.opportunity.trader_id,
            item.opportunity.signal_fingerprint,
        )
        for item in observations
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate Phase 19 geometry outcome"
        )
    population = {
        item.opportunity.trader_id for item in observations
    }
    if population != set(PHASE19_REQUIRED_TRADERS):
        raise CiboCapitalManagementError(
            "Phase 19 dependence requires complete seven-Trader population"
        )

    by_trader = {
        trader: tuple(
            item
            for item in observations
            if item.opportunity.trader_id is trader
        )
        for trader in PHASE19_REQUIRED_TRADERS
    }
    pair_evidence: list[Phase19PairDependenceEvidence] = []

    for left_trader, right_trader in _PAIR_KEYS:
        overlap_count = 0
        left_loss = 0
        right_loss = 0
        joint_loss = 0
        same_nonzero_sign = 0

        left_items = sorted(
            by_trader[left_trader],
            key=lambda item: item.opportunity.entry_at,
        )
        right_items = sorted(
            by_trader[right_trader],
            key=lambda item: item.opportunity.entry_at,
        )
        for left in left_items:
            for right in right_items:
                if right.opportunity.entry_at >= left.opportunity.exit_at:
                    break
                if (
                    left.opportunity.entry_at < right.opportunity.exit_at
                    and right.opportunity.entry_at < left.opportunity.exit_at
                ):
                    overlap_count += 1
                    left_is_loss = left.normalized_outcome_r < 0
                    right_is_loss = right.normalized_outcome_r < 0
                    left_loss += int(left_is_loss)
                    right_loss += int(right_is_loss)
                    joint_loss += int(left_is_loss and right_is_loss)
                    same_nonzero_sign += int(
                        (
                            left.normalized_outcome_r > 0
                            and right.normalized_outcome_r > 0
                        )
                        or (
                            left.normalized_outcome_r < 0
                            and right.normalized_outcome_r < 0
                        )
                    )

        if overlap_count == 0:
            pair_evidence.append(
                Phase19PairDependenceEvidence(
                    left_trader=left_trader,
                    right_trader=right_trader,
                    overlapping_pairs=0,
                    left_loss_pairs=0,
                    right_loss_pairs=0,
                    joint_loss_pairs=0,
                    same_nonzero_sign_pairs=0,
                    left_loss_rate=None,
                    right_loss_rate=None,
                    joint_loss_rate=None,
                    independent_joint_loss_rate=None,
                    joint_loss_excess=None,
                    same_nonzero_sign_rate=None,
                )
            )
            continue

        denominator = Decimal(overlap_count)
        left_rate = Decimal(left_loss) / denominator
        right_rate = Decimal(right_loss) / denominator
        joint_rate = Decimal(joint_loss) / denominator
        independent_rate = left_rate * right_rate
        pair_evidence.append(
            Phase19PairDependenceEvidence(
                left_trader=left_trader,
                right_trader=right_trader,
                overlapping_pairs=overlap_count,
                left_loss_pairs=left_loss,
                right_loss_pairs=right_loss,
                joint_loss_pairs=joint_loss,
                same_nonzero_sign_pairs=same_nonzero_sign,
                left_loss_rate=left_rate,
                right_loss_rate=right_rate,
                joint_loss_rate=joint_rate,
                independent_joint_loss_rate=independent_rate,
                joint_loss_excess=joint_rate - independent_rate,
                same_nonzero_sign_rate=(
                    Decimal(same_nonzero_sign) / denominator
                ),
            )
        )

    return Phase19DependenceAtlas(
        pair_evidence=tuple(pair_evidence),
        total_cross_trader_overlap_pairs=sum(
            item.overlapping_pairs for item in pair_evidence
        ),
    )
