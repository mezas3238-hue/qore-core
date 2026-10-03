"""Causal T03 predecision adapter for the CIBO Profitability Lab.

The adapter transports an already-predeclared, provider-verified equivalent
expression into the generic CE2I margin-evidence contract.  It deliberately
keeps economic policy authority disabled until a separate Fresh OOS utility
decision exists.  It performs no broker mutation and no outcome-aware tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    MarginEfficiencyEvidence,
    MarginExpression,
)
from qore.infrastructure.cibo_ce2i_t03_equivalent_expression import (
    T03EquivalentExpressionAudit,
    T03EquivalentExpressionDeclaration,
    T03ExpressionEconomics,
    assess_t03_equivalent_expression,
)


class T03ShadowAdapterStatus(StrEnum):
    SHADOW_AVAILABLE = "SHADOW_AVAILABLE"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class T03PredecisionShadowAdapterResult:
    signal_fingerprint: str
    decision_at: datetime
    status: T03ShadowAdapterStatus
    audit: T03EquivalentExpressionAudit
    evidence: MarginEfficiencyEvidence | None
    economic_authority: bool = False

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "T03 shadow adapter signal fingerprint required"
            )
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T03 shadow adapter decision_at must be timezone-aware"
            )
        if type(self.status) is not T03ShadowAdapterStatus:
            raise CiboCapitalManagementError(
                "T03 shadow adapter status must use canonical enum"
            )
        if type(self.economic_authority) is not bool or self.economic_authority:
            raise CiboCapitalManagementError(
                "T03 shadow adapter cannot grant economic authority"
            )
        expected_evidence = self.status is T03ShadowAdapterStatus.SHADOW_AVAILABLE
        if expected_evidence != (self.evidence is not None):
            raise CiboCapitalManagementError(
                "T03 shadow adapter status/evidence drift"
            )


def adapt_t03_predecision_shadow(
    *,
    signal_fingerprint: str,
    declaration: T03EquivalentExpressionDeclaration,
    target: T03ExpressionEconomics,
    candidate: T03ExpressionEconomics,
    decision_at: datetime,
) -> T03PredecisionShadowAdapterResult:
    """Transport causal T03 measurement while keeping policy authority off."""

    audit = assess_t03_equivalent_expression(
        declaration=declaration,
        target=target,
        candidate=candidate,
        decision_at=decision_at,
    )
    if not audit.mechanically_eligible:
        return T03PredecisionShadowAdapterResult(
            signal_fingerprint=signal_fingerprint,
            decision_at=decision_at,
            status=T03ShadowAdapterStatus.FAIL_CLOSED,
            audit=audit,
            evidence=None,
        )

    # Use known_at rather than raw provider observed_at as the CE2I timestamp.
    # This is conservative: evidence cannot become available before the latest
    # source datum was actually knowable by the decision process.
    available_at = max(target.known_at, candidate.known_at)
    if available_at > decision_at:
        raise CiboCapitalManagementError(
            "T03 shadow adapter contains future-known evidence"
        )

    target_exposure = _absolute_exposure_scale(target)
    candidate_exposure = _absolute_exposure_scale(candidate)
    if target_exposure != candidate_exposure:
        raise CiboCapitalManagementError(
            "T03 shadow adapter exposure scale drift after vector equivalence"
        )

    evidence = MarginEfficiencyEvidence(
        evidence_id=f"t03-shadow:{declaration.declaration_id}",
        observed_at=available_at,
        baseline_expression_id=target.provider_symbol,
        expressions=(
            MarginExpression(
                expression_id=target.provider_symbol,
                normalized_exposure=target_exposure,
                stop_risk_usd=target.stop_risk_usd,
                margin_usd=target.margin_occupancy_usd,
                all_in_cost_usd=target.execution_cost_usd,
                executable=target.execution_supported,
                economics_verified=target.provider_verified,
            ),
            MarginExpression(
                expression_id=candidate.provider_symbol,
                normalized_exposure=candidate_exposure,
                stop_risk_usd=candidate.stop_risk_usd,
                margin_usd=candidate.margin_occupancy_usd,
                all_in_cost_usd=candidate.execution_cost_usd,
                executable=candidate.execution_supported,
                economics_verified=candidate.provider_verified,
            ),
        ),
        fresh_oos_utility_demonstrated=False,
        policy_authorized=False,
    )
    return T03PredecisionShadowAdapterResult(
        signal_fingerprint=signal_fingerprint,
        decision_at=decision_at,
        status=T03ShadowAdapterStatus.SHADOW_AVAILABLE,
        audit=audit,
        evidence=evidence,
    )


def _absolute_exposure_scale(expression: T03ExpressionEconomics) -> Decimal:
    value = sum(
        (abs(item.signed_exposure_usd) for item in expression.normalized_exposure),
        Decimal(0),
    )
    if value <= 0:
        raise CiboCapitalManagementError(
            "T03 shadow adapter normalized exposure scale must be positive"
        )
    return value
