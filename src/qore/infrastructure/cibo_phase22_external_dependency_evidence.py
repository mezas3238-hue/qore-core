"""Architect-B Phase22 external-dependency evidence.

This assessment answers one narrow question: may the historical V2 one-shot be
consumed now and still satisfy the frozen economic protocol without fabricating
provider execution? The answer is derived from frozen contracts only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_ce2i_phase20_historical_shadow import (
    policy_invariants,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_CORE_FREEZE_RECEIPT,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    EXECUTION_ECONOMICS_BLOCKER,
    SYNTHETIC_FORBIDDEN_BLOCKER,
    assess_phase22_one_shot_guard,
)


@dataclass(frozen=True, slots=True)
class Phase22ExternalDependencyEvidence:
    disposition: str
    blockers: tuple[str, ...]
    phase20_realized_execution_economics_required: bool
    phase20_synthetic_evidence_allowed: bool
    phase22_synthetic_evidence_allowed: bool
    historical_provider_economics_claimed: bool
    provider_deployment_ready: bool
    historical_shadow_provider_usd_imputation_allowed: bool
    fresh_holdout_consumed: bool
    recommendation: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.disposition != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise ValueError("Phase22 external dependency disposition drift")
        if (
            EXECUTION_ECONOMICS_BLOCKER not in self.blockers
            or SYNTHETIC_FORBIDDEN_BLOCKER not in self.blockers
        ):
            raise ValueError("Phase22 external dependency blockers incomplete")
        if self.fresh_holdout_consumed:
            raise ValueError(
                "Phase22 provider dependency evidence cannot consume holdout"
            )
        if self.productive_authority:
            raise ValueError(
                "Phase22 provider dependency evidence has no authority"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.external-dependency-evidence.v1",
            **asdict(self),
            "affected_arch_b_workstreams": [
                "PROVIDER_ECONOMICS",
                "FORWARD_QUALIFICATION",
                "FRESH_OOS",
                "USD60_CAPABILITY_PROGRAM",
                "INTEGRATED_CAPITAL_TRUTH",
                "T20_EMPIRICAL_RELEASE",
                "AS_IS_ECONOMIC_BASELINE",
            ],
            "causal_statement": (
                "Historical bars may produce Trader outcomes, but they cannot "
                "supply provider order refs, actual fills, position/deal IDs, "
                "terminal cTrader DEMO settlement, or observed T20 releases. "
                "Those facts may not be synthesized under the frozen plans."
            ),
        }


def build_phase22_external_dependency_evidence(
) -> Phase22ExternalDependencyEvidence:
    guard = assess_phase22_one_shot_guard()
    phase20 = FROZEN_PHASE20D_QUALIFICATION_PLAN
    phase22 = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    provider = PROVIDER_CORE_FREEZE_RECEIPT
    shadow = policy_invariants()

    if guard.authorized_to_emit_first_fresh_outcome:
        raise ValueError(
            "Phase22 external dependency assessment is stale: guard is READY"
        )
    if phase20.synthetic_evidence_allowed:
        raise ValueError("Phase20 synthetic-evidence policy unexpectedly changed")
    if not phase20.realized_execution_economics_required:
        raise ValueError(
            "Phase20 realized-execution requirement unexpectedly changed"
        )
    if phase22.allow_synthetic_evidence:
        raise ValueError("Phase22 synthetic-evidence policy unexpectedly changed")
    if bool(shadow["provider_usd_execution_imputation_allowed"]):
        raise ValueError(
            "Historical-shadow provider imputation policy unexpectedly changed"
        )

    return Phase22ExternalDependencyEvidence(
        disposition="EXTERNAL_DEPENDENCY_BLOCKED",
        blockers=guard.blockers,
        phase20_realized_execution_economics_required=(
            phase20.realized_execution_economics_required
        ),
        phase20_synthetic_evidence_allowed=phase20.synthetic_evidence_allowed,
        phase22_synthetic_evidence_allowed=phase22.allow_synthetic_evidence,
        historical_provider_economics_claimed=(
            provider.historical_provider_economics_claimed
        ),
        provider_deployment_ready=provider.provider_deployment_ready,
        historical_shadow_provider_usd_imputation_allowed=bool(
            shadow["provider_usd_execution_imputation_allowed"]
        ),
        fresh_holdout_consumed=False,
        recommendation=(
            "KEEP_V2_SEALED_UNTIL_REAL_PROVIDER_BOUND_EXECUTION_"
            "SETTLEMENT_AND_RELEASE_EVIDENCE_EXISTS"
        ),
    )
