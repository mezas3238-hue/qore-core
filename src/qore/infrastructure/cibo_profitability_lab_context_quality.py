"""Universal causal context-quality gate for burned CIBO research.

The gate is deliberately narrow.  It consumes only Trader-owned decision_context
facts that already exist before the market decision and never reads the current
trade outcome.  The three vetoes were retained only because the same adverse
relationship appeared independently in all three burned 1Y research groups.

This is NON_CERTIFYING_REUSED_HOLDOUT_ADAPTIVE_RESEARCH.  It has no Trader
identity predicates, no sizing authority, no QORE Risk authority, no execution
authority and no broker mutation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)

POLICY_ID = "CIBO_BURNED_3X1Y_CONTEXT_QUALITY_GATE_V1"
RESEARCH_MODE = "NON_CERTIFYING_REUSED_HOLDOUT_ADAPTIVE_RESEARCH"


class ContextQualityDisposition(StrEnum):
    ALLOW = "ALLOW"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class ContextQualityRule:
    rule_id: str
    context_key: str
    adverse_value: str

    def __post_init__(self) -> None:
        if not self.rule_id or not self.context_key or not self.adverse_value:
            raise CiboCapitalManagementError(
                "context-quality rule identity/key/value required"
            )


ADVERSE_CONTEXT_RULES: tuple[ContextQualityRule, ...] = (
    ContextQualityRule(
        rule_id="LOW_PROJECTED_R_BUCKET",
        context_key="ctx_strategy_projected_r_bucket",
        adverse_value="q1:<=0.5",
    ),
    ContextQualityRule(
        rule_id="LOW_TARGET_DISTANCE_BUCKET",
        context_key="ctx_strategy_target_distance_range_bucket",
        adverse_value="q1:<=0.5",
    ),
    ContextQualityRule(
        rule_id="H1_PRIOR_CANDLE_DIRECTIONAL_TARGET",
        context_key="target_route",
        adverse_value="PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
    ),
)


@dataclass(frozen=True, slots=True)
class ContextQualityDecision:
    policy_id: str
    research_mode: str
    signal_fingerprint: str
    decision_at: datetime
    disposition: ContextQualityDisposition
    matched_rule_ids: tuple[str, ...]
    observed_context: tuple[tuple[str, str | None], ...]
    reason: str
    causal_predecision: bool = True
    identity_predicate_used: bool = False
    outcome_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    broker_mutation: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if self.policy_id != POLICY_ID or self.research_mode != RESEARCH_MODE:
            raise CiboCapitalManagementError(
                "context-quality policy/research identity drift"
            )
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "context-quality signal fingerprint required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "context-quality decision_at must be timezone-aware"
            )
        if type(self.disposition) is not ContextQualityDisposition:
            raise CiboCapitalManagementError(
                "context-quality disposition must be canonical"
            )
        if not self.reason:
            raise CiboCapitalManagementError(
                "context-quality decision reason required"
            )
        expected_abstain = bool(self.matched_rule_ids)
        if expected_abstain != (
            self.disposition is ContextQualityDisposition.ABSTAIN
        ):
            raise CiboCapitalManagementError(
                "context-quality disposition/rule match drift"
            )
        if len(self.matched_rule_ids) != len(set(self.matched_rule_ids)):
            raise CiboCapitalManagementError(
                "context-quality matched rules must be unique"
            )
        for name in (
            "causal_predecision",
            "identity_predicate_used",
            "outcome_used",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "broker_mutation",
            "certification_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"context-quality {name} must be bool"
                )
        if (
            not self.causal_predecision
            or self.identity_predicate_used
            or self.outcome_used
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
            or self.broker_mutation
            or self.certification_claimed
        ):
            raise CiboCapitalManagementError(
                "context-quality governance boundary violated"
            )

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "research_mode": self.research_mode,
            "signal_fingerprint": self.signal_fingerprint,
            "decision_at": self.decision_at.isoformat(),
            "disposition": self.disposition.value,
            "matched_rule_ids": list(self.matched_rule_ids),
            "observed_context": [
                [key, value] for key, value in self.observed_context
            ],
            "reason": self.reason,
            "causal_predecision": self.causal_predecision,
            "identity_predicate_used": self.identity_predicate_used,
            "outcome_used": self.outcome_used,
            "sizing_authority": self.sizing_authority,
            "risk_authority": self.risk_authority,
            "execution_authority": self.execution_authority,
            "broker_mutation": self.broker_mutation,
            "certification_claimed": self.certification_claimed,
        }


def evaluate_context_quality(
    *,
    opportunity: TraderOpportunityEnvelope,
    decision_at: datetime,
) -> ContextQualityDecision:
    """Apply the universal burned-research vetoes to one causal opportunity."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "context-quality gate requires TraderOpportunityEnvelope"
        )
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "context-quality decision_at must be timezone-aware"
        )

    observed = tuple(
        (rule.context_key, opportunity.context_value(rule.context_key))
        for rule in ADVERSE_CONTEXT_RULES
    )
    matched = tuple(
        rule.rule_id
        for rule in ADVERSE_CONTEXT_RULES
        if opportunity.context_value(rule.context_key) == rule.adverse_value
    )
    disposition = (
        ContextQualityDisposition.ABSTAIN
        if matched
        else ContextQualityDisposition.ALLOW
    )
    return ContextQualityDecision(
        policy_id=POLICY_ID,
        research_mode=RESEARCH_MODE,
        signal_fingerprint=opportunity.signal_fingerprint,
        decision_at=decision_at,
        disposition=disposition,
        matched_rule_ids=matched,
        observed_context=observed,
        reason=(
            "universal causal context matched a cross-holdout adverse veto"
            if matched
            else "no preregistered adverse context veto matched"
        ),
    )
