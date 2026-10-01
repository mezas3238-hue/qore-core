"""Architect-B Phase22 external-dependency evidence.

This assessment answers one narrow question: may the historical V2 one-shot be
consumed now and still satisfy the frozen economic protocol without fabricating
provider execution? The answer is derived from frozen contracts only.

The provider-core freeze is immutable. A separately bound post-freeze empirical
DEMO calibration may resolve the dependency without rewriting that older receipt
or claiming historical broker fills.
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
    assess_phase22_one_shot_guard,
)

_BLOCKED = "EXTERNAL_DEPENDENCY_BLOCKED"
_RESOLVED = "DEPENDENCY_RESOLVED_PRE_HOLDOUT"


@dataclass(frozen=True, slots=True)
class Phase22ExternalDependencyEvidence:
    disposition: str
    blockers: tuple[str, ...]
    authorized_to_emit_first_fresh_outcome: bool
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
        if self.disposition not in {_BLOCKED, _RESOLVED}:
            raise ValueError("Phase22 external dependency disposition drift")
        if self.disposition == _BLOCKED:
            if not self.blockers or self.authorized_to_emit_first_fresh_outcome:
                raise ValueError(
                    "Phase22 blocked dependency evidence is internally inconsistent"
                )
        else:
            if self.blockers or not self.authorized_to_emit_first_fresh_outcome:
                raise ValueError(
                    "Phase22 resolved dependency evidence is internally inconsistent"
                )
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
            "schema": "qore.cibo.phase22.external-dependency-evidence.v2",
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
                "Current DEMO provider calibration may bind counterfactual "
                "historical replay economics, but it never becomes a claim of "
                "2015-2016 broker fills, order/deal IDs, or terminal settlement."
            ),
        }


def build_phase22_external_dependency_evidence(
) -> Phase22ExternalDependencyEvidence:
    guard = assess_phase22_one_shot_guard()
    phase20 = FROZEN_PHASE20D_QUALIFICATION_PLAN
    phase22 = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    provider = PROVIDER_CORE_FREEZE_RECEIPT
    shadow = policy_invariants()

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

    resolved = guard.authorized_to_emit_first_fresh_outcome
    return Phase22ExternalDependencyEvidence(
        disposition=_RESOLVED if resolved else _BLOCKED,
        blockers=guard.blockers,
        authorized_to_emit_first_fresh_outcome=(
            guard.authorized_to_emit_first_fresh_outcome
        ),
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
            "PROCEED_TO_FROZEN_ONE_SHOT_WITHOUT_SYNTHETIC_EXECUTION_CLAIMS"
            if resolved
            else "KEEP_V2_SEALED_UNTIL_PROVIDER_EXECUTION_PLANE_IS_READY"
        ),
    )
