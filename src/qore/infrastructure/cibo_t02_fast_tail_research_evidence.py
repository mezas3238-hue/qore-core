"""Research-only CE2I T02 evidence selected by Trader Lab fast-tail V5.

The decision rule was selected on burned TRAIN only, frozen, and then passed
sealed burned VALIDATION. It is not Fresh OOS and grants no LIVE, Production,
certification, real-capital, broker, Risk, sizing-policy, or merge authority.
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

T02_FAST_TAIL_RESEARCH_EVIDENCE_ID = (
    "T02_FAST_TAIL_V5_FVG_EXCLUDE_NY_LOW_EFF_LARGE_WICK"
)
T02_FAST_TAIL_RUN_ID = 37145609158
T02_FAST_TAIL_ARTIFACT_ID = 11281824086
T02_FAST_TAIL_ARTIFACT_DIGEST = (
    "sha256:13ebf0a5b6a6691ceb0e68f1dee93172ed95cb717e9fef0b7fad8d329da375ca"
)
T02_FAST_TAIL_SELECTED_RULE_ID = "FVG_EXCLUDE_NY_LOW_EFF_LARGE_WICK"
T02_FAST_TAIL_MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK = Decimal("0.05")

T02_FAST_TAIL_VALIDATION_ROWS = 208
T02_FAST_TAIL_VALIDATION_SUM_R = Decimal(
    "64.07436510426978662197394258"
)
T02_FAST_TAIL_VALIDATION_BOOTSTRAP_P05_TOTAL_R = Decimal(
    "21.084873662471068"
)
T02_FAST_TAIL_BASELINE_STOP_RATE = Decimal(
    "0.3836633663366336633663366337"
)
T02_FAST_TAIL_CANDIDATE_STOP_RATE = Decimal(
    "0.3701923076923076923076923077"
)
T02_FAST_TAIL_BASELINE_P95_LOSS_R = Decimal("1.10")
T02_FAST_TAIL_CANDIDATE_P95_LOSS_R = Decimal("1.10")


def build_fast_tail_t02_research_evidence(
    opportunity: TraderOpportunityEnvelope,
    observed_at: datetime,
    released_risk_capacity_usd: Decimal,
) -> StructuralLeverageEvidence | None:
    """Return V5 evidence only when the frozen causal admission rule passes."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "fast-tail T02 evidence requires TraderOpportunityEnvelope"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "fast-tail T02 observed_at must be timezone-aware"
        )
    if (
        not isinstance(released_risk_capacity_usd, Decimal)
        or not released_risk_capacity_usd.is_finite()
        or released_risk_capacity_usd < 0
    ):
        raise CiboCapitalManagementError(
            "fast-tail T02 released capacity must be finite non-negative"
        )

    if opportunity.side != "long":
        return None
    session = opportunity.context_value("ctx_session")
    if session is None or session == "asia":
        return None
    if opportunity.context_value("ctx_fvg_before_entry") != "yes":
        return None

    adverse_ny_low_eff_large_wick = (
        session == "new-york"
        and opportunity.context_value("reg_m5_efficiency_state") == "low"
        and opportunity.context_value("ctx_rejection_wick_bucket") == "q4:>0.50"
    )
    if adverse_ny_low_eff_large_wick:
        return None

    minimum_risk = (
        minimum_seed_volume(opportunity) * opportunity.stop_loss_per_volume
    )
    if minimum_risk <= 0:
        return None
    expectation = build_frozen_train_expectation(
        trader_id=opportunity.trader_id,
        stop_risk_usd=minimum_risk,
        as_of=observed_at,
    )
    if (
        expectation.expected_net_value_usd / minimum_risk
        < T02_FAST_TAIL_MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK
    ):
        return None

    return StructuralLeverageEvidence(
        evidence_id=(
            f"{T02_FAST_TAIL_RESEARCH_EVIDENCE_ID}:"
            f"artifact:{T02_FAST_TAIL_ARTIFACT_ID}:"
            f"{opportunity.signal_fingerprint}"
        ),
        structural_invalidation_id=(
            f"{opportunity.signal_fingerprint}:"
            "fast-tail-v5-structural-stop"
        ),
        observed_at=observed_at,
        sample_size=T02_FAST_TAIL_VALIDATION_ROWS,
        baseline_stop_rate=T02_FAST_TAIL_BASELINE_STOP_RATE,
        candidate_stop_rate=T02_FAST_TAIL_CANDIDATE_STOP_RATE,
        baseline_tail_loss_r=T02_FAST_TAIL_BASELINE_P95_LOSS_R,
        candidate_tail_loss_r=T02_FAST_TAIL_CANDIDATE_P95_LOSS_R,
        released_risk_capacity_usd=released_risk_capacity_usd,
        protected_capacity_usd=Decimal(0),
        evidence_oos=True,
        structural_stop_verified=True,
        stop_geometry_unchanged=True,
    )
