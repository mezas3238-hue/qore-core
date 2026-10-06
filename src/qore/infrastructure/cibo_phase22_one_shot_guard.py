"""Fail-closed guard for the single Phase22 V2 fresh execution.

The guard distinguishes source/trader readiness, provider economics readiness,
and durable one-shot consumption state. A committed execution claim is a
one-way barrier: a crashed run may require forensic recovery, but it can never
silently make the same fresh holdout executable again.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_CORE_FREEZE_RECEIPT,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
    load_phase22_execution_consumption_receipt,
)
from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
)

EXECUTION_ECONOMICS_BLOCKER = (
    "HISTORICAL_HOLDOUT_HAS_NO_REALIZED_PROVIDER_EXECUTION_SETTLEMENT_EVIDENCE"
)
SYNTHETIC_FORBIDDEN_BLOCKER = (
    "PHASE22_SYNTHETIC_EXECUTION_EVIDENCE_FORBIDDEN"
)
DUAL_EVIDENCE_NOT_READY_BLOCKER = (
    "PHASE22_DUAL_EVIDENCE_PROVIDER_PLANE_NOT_READY"
)
PROVIDER_COST_BOUND_NOT_READY_BLOCKER = (
    "PHASE22_PREDECLARED_PROVIDER_COST_BOUND_NOT_READY"
)
DURABLE_CLAIM_BLOCKER = "PHASE22_V2_EXECUTION_ALREADY_DURABLY_CLAIMED"


@runtime_checkable
class Phase22DurableClaimEvidence(Protocol):
    source_head_sha: str
    durable_claim_proven: bool


class Phase22OneShotGuardStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    CLAIMED = "CLAIMED"
    CONSUMED = "CONSUMED"


@dataclass(frozen=True, slots=True)
class Phase22OneShotGuardAssessment:
    status: Phase22OneShotGuardStatus
    execution_manifest_sha256: str
    store_paths: tuple[str, ...]
    blockers: tuple[str, ...]
    execution_claimed: bool
    fresh_outcomes_already_emitted: bool
    durable_claim_proven: bool
    authorized_to_create_durable_claim: bool
    authorized_to_emit_first_fresh_outcome: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        preclaim_ready = (
            not self.blockers
            and not self.execution_claimed
            and not self.fresh_outcomes_already_emitted
        )
        expected_create_claim = preclaim_ready
        expected_emit = (
            self.execution_claimed
            and self.durable_claim_proven
            and not self.fresh_outcomes_already_emitted
        )
        if self.authorized_to_create_durable_claim != expected_create_claim:
            raise ValueError("Phase22 one-shot claim authorization drift")
        if self.authorized_to_emit_first_fresh_outcome != expected_emit:
            raise ValueError("Phase22 one-shot fresh authorization drift")
        if self.fresh_outcomes_already_emitted:
            expected_status = Phase22OneShotGuardStatus.CONSUMED
        elif self.execution_claimed:
            expected_status = Phase22OneShotGuardStatus.CLAIMED
        elif preclaim_ready:
            expected_status = Phase22OneShotGuardStatus.READY
        else:
            expected_status = Phase22OneShotGuardStatus.BLOCKED
        if self.status is not expected_status:
            raise ValueError("Phase22 one-shot status drift")
        if self.durable_claim_proven and not self.execution_claimed:
            raise ValueError("Phase22 durable proof requires committed claim")
        if self.productive_authority:
            raise ValueError("Phase22 one-shot guard has no productive authority")

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def assess_phase22_one_shot_guard(
    *,
    consumption_receipt: Phase22ExecutionConsumptionReceipt | None = None,
    durable_claim_evidence: Phase22DurableClaimEvidence | None = None,
) -> Phase22OneShotGuardAssessment:
    manifest = build_phase22_execution_manifest()
    manifest_sha = manifest.fingerprint()
    blockers: list[str] = []

    if consumption_receipt is None:
        consumption_receipt = load_phase22_execution_consumption_receipt()

    claimed = False
    already_emitted = False
    durable_claim_proven = False
    if consumption_receipt is not None:
        if consumption_receipt.candidate_id != manifest.candidate_id:
            blockers.append("PHASE22_CONSUMPTION_CANDIDATE_DRIFT")
        if consumption_receipt.execution_manifest_sha256 != manifest_sha:
            blockers.append("PHASE22_CONSUMPTION_MANIFEST_DRIFT")
        claimed = consumption_receipt.claim_committed
        already_emitted = consumption_receipt.outcomes_emitted
        if claimed:
            blockers.append(DURABLE_CLAIM_BLOCKER)
        if already_emitted:
            blockers.append("PHASE22_V2_FRESH_OUTCOMES_ALREADY_EMITTED")

    if durable_claim_evidence is not None:
        if not isinstance(
            durable_claim_evidence,
            Phase22DurableClaimEvidence,
        ):
            raise TypeError("Phase22 durable claim evidence must be canonical")
        if consumption_receipt is None or not claimed:
            blockers.append("PHASE22_DURABLE_CLAIM_PROOF_WITHOUT_COMMITTED_CLAIM")
        elif durable_claim_evidence.source_head_sha != (
            consumption_receipt.claim_head_sha
        ):
            blockers.append("PHASE22_DURABLE_CLAIM_SOURCE_HEAD_DRIFT")
        elif not durable_claim_evidence.durable_claim_proven:
            blockers.append("PHASE22_DURABLE_CLAIM_NOT_PROVEN")
        else:
            durable_claim_proven = True

    phase20 = FROZEN_PHASE20D_QUALIFICATION_PLAN
    phase22 = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    provider = PROVIDER_CORE_FREEZE_RECEIPT

    if phase20.realized_execution_economics_required:
        dual = PHASE22_DUAL_EVIDENCE_PLAN
        if not dual.activation_ready:
            blockers.append(DUAL_EVIDENCE_NOT_READY_BLOCKER)
        if (
            not provider.core_pre_holdout_ready
            or not dual.require_predeclared_provider_cost_application
        ):
            blockers.append(PROVIDER_COST_BOUND_NOT_READY_BLOCKER)
        if (
            not dual.forbid_historical_provider_fill_claims
            or not dual.forbid_historical_provider_order_refs
            or not dual.forbid_historical_provider_deal_refs
            or not dual.forbid_historical_provider_settlement_claims
        ):
            blockers.append(EXECUTION_ECONOMICS_BLOCKER)
    if (
        not phase20.synthetic_evidence_allowed
        or not phase22.allow_synthetic_evidence
    ):
        if (
            EXECUTION_ECONOMICS_BLOCKER in blockers
            or DUAL_EVIDENCE_NOT_READY_BLOCKER in blockers
            or PROVIDER_COST_BOUND_NOT_READY_BLOCKER in blockers
        ):
            blockers.append(SYNTHETIC_FORBIDDEN_BLOCKER)

    paths = tuple(item.relative_path for item in PHASE22_STORE_IDENTITIES)
    if len(paths) != 5 or len(paths) != len(set(paths)):
        blockers.append("PHASE22_STORE_SURFACE_INVALID")

    blockers = list(dict.fromkeys(blockers))
    if already_emitted:
        status = Phase22OneShotGuardStatus.CONSUMED
    elif claimed:
        status = Phase22OneShotGuardStatus.CLAIMED
    elif blockers:
        status = Phase22OneShotGuardStatus.BLOCKED
    else:
        status = Phase22OneShotGuardStatus.READY
    return Phase22OneShotGuardAssessment(
        status=status,
        execution_manifest_sha256=manifest_sha,
        store_paths=paths,
        blockers=tuple(blockers),
        execution_claimed=claimed,
        fresh_outcomes_already_emitted=already_emitted,
        durable_claim_proven=durable_claim_proven,
        authorized_to_create_durable_claim=(
            not blockers and not claimed and not already_emitted
        ),
        authorized_to_emit_first_fresh_outcome=(
            claimed and durable_claim_proven and not already_emitted
        ),
    )
