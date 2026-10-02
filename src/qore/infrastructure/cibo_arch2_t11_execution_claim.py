"""Immutable execution claim for the first Architect-2 T11 provider experiment.

The scientific protocol was frozen before this run.  This claim prevents
silent reruns or result shopping after any part of the DEMO population has
been observed.

Run 36945327912 at HEAD f239059c... is the only first-cycle execution whose
outcome may be used by the frozen T11 market-impact protocol.  A technical or
scientific failure does not authorize a replacement run.  Any replacement
requires an explicitly versioned new research cycle and cannot overwrite this
claim.

This receipt grants no broker, ledger, Phase22 or productive authority.
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

CLAIM_ID = "CIBO_ARCH2_T11_MARKET_IMPACT_FIRST_EXECUTION_CLAIM_V1"
RUN_ID = 36945327912
RUN_ATTEMPT = 1
HEAD_SHA = "f239059c34897d395bf5503bea522c1795192bec"


@dataclass(frozen=True, slots=True)
class T11MarketImpactExecutionClaim:
    claim_id: str
    run_id: int
    run_attempt: int
    head_sha: str
    protocol_sha256: str
    experiment_plan_sha256: str
    first_cycle_run: bool
    silent_rerun_allowed: bool
    replacement_requires_new_versioned_cycle: bool
    phase22_v2_consumed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.claim_id != CLAIM_ID:
            raise CiboCapitalManagementError("T11 execution claim identity drift")
        if self.run_id != RUN_ID or self.run_attempt != RUN_ATTEMPT:
            raise CiboCapitalManagementError("T11 execution claim run identity drift")
        if self.head_sha != HEAD_SHA or len(self.head_sha) != 40:
            raise CiboCapitalManagementError("T11 execution claim HEAD drift")
        if self.protocol_sha256 != T11_NONLINEAR_INPUT_FREEZE.fingerprint():
            raise CiboCapitalManagementError("T11 execution claim protocol drift")
        if (
            self.experiment_plan_sha256
            != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint()
        ):
            raise CiboCapitalManagementError("T11 execution claim plan drift")
        if (
            not self.first_cycle_run
            or self.silent_rerun_allowed
            or not self.replacement_requires_new_versioned_cycle
        ):
            raise CiboCapitalManagementError(
                "T11 execution claim anti-rerun governance drift"
            )
        if (
            self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 execution claim exceeded Architect-2 authority"
            )


T11_MARKET_IMPACT_EXECUTION_CLAIM = T11MarketImpactExecutionClaim(
    claim_id=CLAIM_ID,
    run_id=RUN_ID,
    run_attempt=RUN_ATTEMPT,
    head_sha=HEAD_SHA,
    protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
    experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
    first_cycle_run=True,
    silent_rerun_allowed=False,
    replacement_requires_new_versioned_cycle=True,
)
