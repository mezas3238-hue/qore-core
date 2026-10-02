"""Immutable execution lineage for the Architect-2 T11 provider experiment.

The frozen T11 protocol admits one technical replacement only because the first
run was cancelled by a non-outcome-aware workflow-contract change and produced
no terminal artifact.  No scientific result from the cancelled run was
consumed to authorize the replacement.

Initial run:
- run 36945327912
- HEAD f239059c34897d395bf5503bea522c1795192bec
- cancelled before artifact publication
- artifact_count = 0

Admissible technical replacement:
- run 36946792349
- HEAD c23483e9bb333b856c6a996bc9f6bde6a5ee6df3
- trigger changed only workflow contract/readiness coverage
- no model, gate, threshold or outcome-dependent selection change

Any further rerun requires a new explicitly versioned research cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    T11_NONLINEAR_INPUT_FREEZE,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

CLAIM_ID = "CIBO_ARCH2_T11_MARKET_IMPACT_EXECUTION_LINEAGE_V2"

INITIAL_RUN_ID = 36945327912
INITIAL_RUN_ATTEMPT = 1
INITIAL_HEAD_SHA = "f239059c34897d395bf5503bea522c1795192bec"

REPLACEMENT_TRIGGER_SHA = "c23483e9bb333b856c6a996bc9f6bde6a5ee6df3"
CANONICAL_RUN_ID = 36946792349
CANONICAL_RUN_ATTEMPT = 1
CANONICAL_HEAD_SHA = REPLACEMENT_TRIGGER_SHA

TECHNICAL_REPLACEMENT_REASON = (
    "NON_OUTCOME_AWARE_WORKFLOW_CONTRACT_BINDING_WITH_ZERO_TERMINAL_ARTIFACTS"
)


@dataclass(frozen=True, slots=True)
class T11MarketImpactExecutionClaim:
    claim_id: str
    protocol_sha256: str
    experiment_plan_sha256: str

    initial_run_id: int
    initial_run_attempt: int
    initial_head_sha: str
    initial_run_cancelled: bool
    initial_terminal_artifact_count: int
    initial_outcome_evidence_consumed: bool

    replacement_trigger_sha: str
    replacement_reason: str
    replacement_changed_scientific_model: bool
    replacement_changed_thresholds: bool
    replacement_outcome_aware: bool

    canonical_run_id: int
    canonical_run_attempt: int
    canonical_head_sha: str

    further_silent_rerun_allowed: bool
    further_replacement_requires_new_versioned_cycle: bool

    phase22_v2_consumed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.claim_id != CLAIM_ID:
            raise CiboCapitalManagementError("T11 execution lineage identity drift")
        if self.protocol_sha256 != T11_NONLINEAR_INPUT_FREEZE.fingerprint():
            raise CiboCapitalManagementError("T11 execution lineage protocol drift")
        if (
            self.experiment_plan_sha256
            != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint()
        ):
            raise CiboCapitalManagementError("T11 execution lineage plan drift")

        if (
            self.initial_run_id != INITIAL_RUN_ID
            or self.initial_run_attempt != INITIAL_RUN_ATTEMPT
            or self.initial_head_sha != INITIAL_HEAD_SHA
            or not self.initial_run_cancelled
            or self.initial_terminal_artifact_count != 0
            or self.initial_outcome_evidence_consumed
        ):
            raise CiboCapitalManagementError(
                "T11 initial cancelled-run lineage drift"
            )

        if (
            self.replacement_trigger_sha != REPLACEMENT_TRIGGER_SHA
            or self.replacement_reason != TECHNICAL_REPLACEMENT_REASON
            or self.replacement_changed_scientific_model
            or self.replacement_changed_thresholds
            or self.replacement_outcome_aware
        ):
            raise CiboCapitalManagementError(
                "T11 technical replacement justification drift"
            )

        if (
            self.canonical_run_id != CANONICAL_RUN_ID
            or self.canonical_run_attempt != CANONICAL_RUN_ATTEMPT
            or self.canonical_head_sha != CANONICAL_HEAD_SHA
        ):
            raise CiboCapitalManagementError(
                "T11 canonical replacement run identity drift"
            )

        if (
            self.further_silent_rerun_allowed
            or not self.further_replacement_requires_new_versioned_cycle
        ):
            raise CiboCapitalManagementError(
                "T11 post-replacement anti-rerun governance drift"
            )

        if (
            self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 execution lineage exceeded Architect-2 authority"
            )


T11_MARKET_IMPACT_EXECUTION_CLAIM = T11MarketImpactExecutionClaim(
    claim_id=CLAIM_ID,
    protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
    experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
    initial_run_id=INITIAL_RUN_ID,
    initial_run_attempt=INITIAL_RUN_ATTEMPT,
    initial_head_sha=INITIAL_HEAD_SHA,
    initial_run_cancelled=True,
    initial_terminal_artifact_count=0,
    initial_outcome_evidence_consumed=False,
    replacement_trigger_sha=REPLACEMENT_TRIGGER_SHA,
    replacement_reason=TECHNICAL_REPLACEMENT_REASON,
    replacement_changed_scientific_model=False,
    replacement_changed_thresholds=False,
    replacement_outcome_aware=False,
    canonical_run_id=CANONICAL_RUN_ID,
    canonical_run_attempt=CANONICAL_RUN_ATTEMPT,
    canonical_head_sha=CANONICAL_HEAD_SHA,
    further_silent_rerun_allowed=False,
    further_replacement_requires_new_versioned_cycle=True,
)
