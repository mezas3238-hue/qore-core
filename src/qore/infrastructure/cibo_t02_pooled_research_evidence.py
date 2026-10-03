"""Research-only pooled causal evidence for CE2I T02 structural leverage.

This evidence was selected on burned Phase18 TRAIN only and then frozen before
untouched burned VALIDATION. It is intentionally separate from the canonical
T02 runtime binding and grants no LIVE, Production, certification, real-capital,
broker, Risk, sizing-policy, or merge authority.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    StructuralLeverageEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)

POOLED_T02_RESEARCH_EVIDENCE_ID = (
    "T02_POOLED_BURNED_TRAIN_VALIDATE_ROR0050_D1_NONEXT_V1"
)
POOLED_T02_SELECTOR_RUN_ID = 37143533072
POOLED_T02_SELECTOR_ARTIFACT_ID = 11281615963
POOLED_T02_SELECTOR_ARTIFACT_DIGEST = (
    "sha256:8c224f6cc8a13bcf7f89aa774141193ad025626f6fa8de5f53911b5d46ae4b3b"
)
POOLED_T02_SELECTED_RULE_ID = "ROR_0050_D1_NOT_EXTREME"
POOLED_T02_MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK = Decimal("0.05")
POOLED_T02_VALIDATION_ROWS = 367
POOLED_T02_VALIDATION_BASELINE_STOP_RATE = Decimal(
    "0.3836633663366336633663366337"
)
POOLED_T02_VALIDATION_CANDIDATE_STOP_RATE = Decimal(
    "0.3814713896457765667574931880"
)
POOLED_T02_VALIDATION_BASELINE_P95_LOSS_R = Decimal("1.10")
POOLED_T02_VALIDATION_CANDIDATE_P95_LOSS_R = Decimal("1.10")
POOLED_T02_VALIDATION_BOOTSTRAP_P05_TOTAL_R = Decimal(
    "21.710049506778283"
)
POOLED_T02_VALIDATION_SUM_R = Decimal(
    "70.53908453771076591037172506"
)


def build_pooled_t02_research_evidence(
    opportunity: TraderOpportunityEnvelope,
    observed_at: datetime,
    released_risk_capacity_usd: Decimal,
) -> StructuralLeverageEvidence | None:
    """Bind a predecision opportunity to the pooled burned VALIDATION rule."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "pooled T02 research evidence requires TraderOpportunityEnvelope"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "pooled T02 research observed_at must be timezone-aware"
        )
    if (
        not isinstance(released_risk_capacity_usd, Decimal)
        or not released_risk_capacity_usd.is_finite()
        or released_risk_capacity_usd < 0
    ):
        raise CiboCapitalManagementError(
            "pooled T02 released risk capacity must be finite non-negative"
        )

    if opportunity.side != "long":
        return None
    d1_range_state = opportunity.context_value("reg_d1_range_state")
    if d1_range_state is None or d1_range_state == "extreme":
        return None

    minimum_risk = (
        minimum_seed_volume(opportunity)
        * opportunity.stop_loss_per_volume
    )
    if minimum_risk <= 0:
        return None
    expectation = build_frozen_train_expectation(
        trader_id=opportunity.trader_id,
        stop_risk_usd=minimum_risk,
        as_of=observed_at,
    )
    train_return_on_risk = (
        expectation.expected_net_value_usd / minimum_risk
    )
    if train_return_on_risk < POOLED_T02_MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK:
        return None

    return StructuralLeverageEvidence(
        evidence_id=(
            f"{POOLED_T02_RESEARCH_EVIDENCE_ID}:"
            f"artifact:{POOLED_T02_SELECTOR_ARTIFACT_ID}:"
            f"{opportunity.signal_fingerprint}"
        ),
        structural_invalidation_id=(
            f"{opportunity.signal_fingerprint}:pooled-d1-nonext-structural-stop"
        ),
        observed_at=observed_at,
        sample_size=POOLED_T02_VALIDATION_ROWS,
        baseline_stop_rate=POOLED_T02_VALIDATION_BASELINE_STOP_RATE,
        candidate_stop_rate=POOLED_T02_VALIDATION_CANDIDATE_STOP_RATE,
        baseline_tail_loss_r=POOLED_T02_VALIDATION_BASELINE_P95_LOSS_R,
        candidate_tail_loss_r=POOLED_T02_VALIDATION_CANDIDATE_P95_LOSS_R,
        released_risk_capacity_usd=released_risk_capacity_usd,
        protected_capacity_usd=Decimal(0),
        evidence_oos=True,
        structural_stop_verified=True,
        stop_geometry_unchanged=True,
    )
