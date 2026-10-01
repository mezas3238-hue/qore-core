"""Fail-closed guard for the single Phase22 V2 fresh execution.

The guard intentionally distinguishes source/trader readiness from execution
economics readiness. It must never turn missing broker/provider evidence into
synthetic fills, settlements or releases.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_CORE_FREEZE_RECEIPT,
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


class Phase22OneShotGuardStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    CONSUMED = "CONSUMED"


@dataclass(frozen=True, slots=True)
class Phase22ExecutionConsumptionReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    outcomes_emitted: bool

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("Phase22 consumption candidate is required")
        if (
            not self.execution_manifest_sha256.startswith("sha256:")
            or len(self.execution_manifest_sha256) != 71
        ):
            raise ValueError("Phase22 consumption manifest digest invalid")
        if type(self.outcomes_emitted) is not bool:
            raise ValueError("Phase22 outcomes_emitted must be bool")


@dataclass(frozen=True, slots=True)
class Phase22OneShotGuardAssessment:
    status: Phase22OneShotGuardStatus
    execution_manifest_sha256: str
    store_paths: tuple[str, ...]
    blockers: tuple[str, ...]
    fresh_outcomes_already_emitted: bool
    authorized_to_emit_first_fresh_outcome: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        expected_ready = (
            not self.blockers
            and not self.fresh_outcomes_already_emitted
        )
        if self.authorized_to_emit_first_fresh_outcome != expected_ready:
            raise ValueError("Phase22 one-shot authorization drift")
        expected_status = (
            Phase22OneShotGuardStatus.CONSUMED
            if self.fresh_outcomes_already_emitted
            else Phase22OneShotGuardStatus.READY
            if expected_ready
            else Phase22OneShotGuardStatus.BLOCKED
        )
        if self.status is not expected_status:
            raise ValueError("Phase22 one-shot status drift")
        if self.productive_authority:
            raise ValueError("Phase22 one-shot guard has no productive authority")

    def payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def assess_phase22_one_shot_guard(
    *,
    consumption_receipt: Phase22ExecutionConsumptionReceipt | None = None,
) -> Phase22OneShotGuardAssessment:
    manifest = build_phase22_execution_manifest()
    manifest_sha = manifest.fingerprint()
    blockers: list[str] = []

    already_emitted = False
    if consumption_receipt is not None:
        if consumption_receipt.candidate_id != manifest.candidate_id:
            blockers.append("PHASE22_CONSUMPTION_CANDIDATE_DRIFT")
        if consumption_receipt.execution_manifest_sha256 != manifest_sha:
            blockers.append("PHASE22_CONSUMPTION_MANIFEST_DRIFT")
        already_emitted = consumption_receipt.outcomes_emitted
        if already_emitted:
            blockers.append("PHASE22_V2_FRESH_OUTCOMES_ALREADY_EMITTED")

    phase20 = FROZEN_PHASE20D_QUALIFICATION_PLAN
    phase22 = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    provider = PROVIDER_CORE_FREEZE_RECEIPT

    if phase20.realized_execution_economics_required:
        if (
            not provider.historical_provider_economics_claimed
            and not provider.provider_deployment_ready
        ):
            blockers.append(EXECUTION_ECONOMICS_BLOCKER)
    if not phase20.synthetic_evidence_allowed or not phase22.allow_synthetic_evidence:
        if EXECUTION_ECONOMICS_BLOCKER in blockers:
            blockers.append(SYNTHETIC_FORBIDDEN_BLOCKER)

    paths = tuple(item.relative_path for item in PHASE22_STORE_IDENTITIES)
    if len(paths) != 5 or len(paths) != len(set(paths)):
        blockers.append("PHASE22_STORE_SURFACE_INVALID")

    blockers = list(dict.fromkeys(blockers))
    if already_emitted:
        status = Phase22OneShotGuardStatus.CONSUMED
    elif blockers:
        status = Phase22OneShotGuardStatus.BLOCKED
    else:
        status = Phase22OneShotGuardStatus.READY
    return Phase22OneShotGuardAssessment(
        status=status,
        execution_manifest_sha256=manifest_sha,
        store_paths=paths,
        blockers=tuple(blockers),
        fresh_outcomes_already_emitted=already_emitted,
        authorized_to_emit_first_fresh_outcome=(not blockers and not already_emitted),
    )
