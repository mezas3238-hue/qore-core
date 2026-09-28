"""Phase19K burned temporal-concordance allocator research contract.

The candidate is intentionally a post-disclosure research hypothesis. Its
decision rule consumes only the already-frozen Phase19 TRAIN priors at runtime,
but Phase19J validation had already been disclosed before this hypothesis was
created. Therefore the old validation can diagnose the candidate but can never
be relabeled as independent OOS evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedCapitalAllocation,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    FROZEN_TRAIN_PRIORS,
    FrozenTraderExpectationPrior,
    prior_digest_sha256,
)

PHASE19K_FREEZE_AT = datetime.fromisoformat("2022-03-09T17:00:00+00:00")


@dataclass(frozen=True, slots=True)
class Phase19KTemporalConcordancePolicy:
    policy_id: str = "P19K_TEMPORAL_CONCORDANCE_025_V1"
    gross_initial_capital_ncu: Decimal = Decimal("10")
    risk_budget_ncu: Decimal = Decimal("0.25")
    post_validation_hypothesis: bool = True
    independent_validation_available: bool = False
    outcome_aware_at_decision: bool = False
    historical_provider_usd_claimed: bool = False
    holdout_2017h1_used: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise CiboCapitalManagementError(
                "Phase19K policy identity is required"
            )
        if self.gross_initial_capital_ncu != Decimal("10"):
            raise CiboCapitalManagementError(
                "Phase19K gross capital must retain Phase19I reference"
            )
        if self.risk_budget_ncu != Decimal("0.25"):
            raise CiboCapitalManagementError(
                "Phase19K must retain predeclared Phase19I 0.25 NCU risk"
            )
        if not self.post_validation_hypothesis:
            raise CiboCapitalManagementError(
                "Phase19K must disclose post-validation hypothesis status"
            )
        if (
            self.independent_validation_available
            or self.outcome_aware_at_decision
            or self.historical_provider_usd_claimed
            or self.holdout_2017h1_used
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase19K research governance drift"
            )


PHASE19K_POLICY = Phase19KTemporalConcordancePolicy()


def _prior_is_temporally_concordant(
    prior: FrozenTraderExpectationPrior,
) -> bool:
    return (
        prior.expected_structural_r > 0
        and prior.chronological_block_means_r[-1] > 0
    )


def _capital_velocity_score(
    prior: FrozenTraderExpectationPrior,
) -> Decimal:
    return prior.expected_structural_r / prior.expected_capital_minutes


def phase19k_eligible_traders() -> tuple[TraderLineage, ...]:
    """Return TRAIN-only positive-center + positive-recent-block Traders."""

    return tuple(
        prior.trader_id
        for prior in FROZEN_TRAIN_PRIORS
        if _prior_is_temporally_concordant(prior)
    )


def phase19k_priority_order() -> tuple[TraderLineage, ...]:
    """Rank eligible Traders by frozen TRAIN structural-R per capital-minute."""

    eligible = tuple(
        prior
        for prior in FROZEN_TRAIN_PRIORS
        if _prior_is_temporally_concordant(prior)
    )
    return tuple(
        prior.trader_id
        for prior in sorted(
            eligible,
            key=lambda item: (
                -_capital_velocity_score(item),
                item.trader_id.value,
            ),
        )
    )


def build_phase19k_candidate_allocation(
    *,
    opportunity: Phase19ChronologicalOpportunity,
    source_allocation: Phase19NormalizedCapitalAllocation,
) -> Phase19NormalizedCapitalAllocation | None:
    """Build a candidate allocation without receiving the trade outcome."""

    if not isinstance(opportunity, Phase19ChronologicalOpportunity):
        raise CiboCapitalManagementError(
            "Phase19K opportunity must be chronological opportunity"
        )
    if not isinstance(source_allocation, Phase19NormalizedCapitalAllocation):
        raise CiboCapitalManagementError(
            "Phase19K source allocation must be normalized allocation"
        )
    if opportunity.signal_fingerprint != source_allocation.signal_fingerprint:
        raise CiboCapitalManagementError(
            "Phase19K source allocation signal mismatch"
        )
    if opportunity.trader_id is not source_allocation.trader_id:
        raise CiboCapitalManagementError(
            "Phase19K source allocation Trader mismatch"
        )
    if source_allocation.decision_at < PHASE19K_FREEZE_AT:
        raise CiboCapitalManagementError(
            "Phase19K candidate cannot consume pre-freeze decision"
        )
    eligible = phase19k_eligible_traders()
    if opportunity.trader_id not in eligible:
        return None
    priority_order = phase19k_priority_order()
    priority = priority_order.index(opportunity.trader_id)
    return Phase19NormalizedCapitalAllocation(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        decision_at=source_allocation.decision_at,
        risk_budget_ncu=PHASE19K_POLICY.risk_budget_ncu,
        allocation_priority=priority,
        policy_id=PHASE19K_POLICY.policy_id,
        evidence_id=(
            f"phase19k:{prior_digest_sha256()}:"
            f"{opportunity.trader_id.value}:"
            f"{source_allocation.evidence_id}"
        ),
        train_cutoff_at=PHASE19K_FREEZE_AT,
        outcome_aware=False,
    )
