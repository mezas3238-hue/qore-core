"""Fail-closed Phase22 V2 pre-holdout governance seal.

The V2 source corpus is frozen and burn-clean, but fresh execution remains
locked until a canonical exact 7/7 Trader parity manifest exists. This module
does not execute Trader logic, inspect outcomes or grant productive authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_terminal_evidence import (
    build_terminal_calibration_readiness,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_COMPONENT_FREEZE_SHA256,
    PROVIDER_CORE_FREEZE_RECEIPT,
)
from qore.infrastructure.cibo_ce2i_shadow_certification_receipts import (
    PHASE21_FREEZE_ARTIFACT_DIGEST,
    PHASE21_FREEZE_HEAD,
    SHADOW_CERTIFICATION_RECEIPTS,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    phase22_v2_holdout_source_receipt_payload,
    phase22_v2_holdout_source_receipt_sha256,
    validate_phase22_v2_source_receipt,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
)

PARITY_BLOCKER = "PHASE22_V2_TRADER_PARITY_MANIFEST_NOT_FROZEN"


class CiboPhase22V2PreHoldoutState(StrEnum):
    LOCKED_PENDING_PARITY = "LOCKED_PENDING_PARITY"
    PRE_HOLDOUT_FROZEN = "PRE_HOLDOUT_FROZEN"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class CiboPhase22V2PreHoldoutReadiness:
    state: CiboPhase22V2PreHoldoutState
    candidate_id: str
    source_receipt_sha256: str
    phase21_policy_freeze_sha256: str
    phase21_policy_freeze_head_sha: str
    calibration_freeze_sha256: str
    provider_core_freeze_sha256: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    qualification_plan_sha256: str
    parity_manifest_sha256: str | None
    burn_clean: bool
    source_stage_outcomes_inspected: bool
    source_stage_trader_logic_executed: bool
    blockers: tuple[str, ...]
    ready_to_unseal_v2: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        expected_ready = (
            not self.blockers
            and self.parity_manifest_sha256 is not None
            and self.burn_clean
            and not self.source_stage_outcomes_inspected
            and not self.source_stage_trader_logic_executed
        )
        if self.ready_to_unseal_v2 != expected_ready:
            raise CiboCapitalManagementError(
                "Phase22 V2 pre-holdout readiness/blocker drift"
            )
        expected_state = (
            CiboPhase22V2PreHoldoutState.PRE_HOLDOUT_FROZEN
            if expected_ready
            else (
                CiboPhase22V2PreHoldoutState.LOCKED_PENDING_PARITY
                if self.blockers == (PARITY_BLOCKER,)
                else CiboPhase22V2PreHoldoutState.INVALID
            )
        )
        if self.state is not expected_state:
            raise CiboCapitalManagementError(
                "Phase22 V2 pre-holdout state drift"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 V2 pre-holdout cannot grant productive authority"
            )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


def evaluate_phase22_v2_pre_holdout_readiness(
) -> CiboPhase22V2PreHoldoutReadiness:
    blockers: list[str] = []
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE

    try:
        validate_phase22_v2_source_receipt()
    except CiboCapitalManagementError:
        blockers.append("PHASE22_V2_SOURCE_RECEIPT_INVALID")

    if candidate.candidate_id != CANDIDATE_ID:
        blockers.append("PHASE22_V2_CANDIDATE_IDENTITY_DRIFT")
    if candidate.status is not CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN:
        blockers.append("PHASE22_V2_CANDIDATE_NOT_ELIGIBLE_FROZEN")
    if not candidate.source_validation_complete:
        blockers.append("PHASE22_V2_SOURCE_VALIDATION_INCOMPLETE")

    burn_clean = candidate_is_burn_clean_for_all_lineages(candidate)
    if not burn_clean:
        blockers.append("PHASE22_V2_CONFIRMED_BURN_OVERLAP")

    source = phase22_v2_holdout_source_receipt_payload()
    source_outcomes_inspected = source["outcomes_inspected"] is True
    source_trader_logic = source["trader_logic_executed"] is True
    if source_outcomes_inspected:
        blockers.append("PHASE22_V2_SOURCE_OUTCOMES_INSPECTED")
    if source_trader_logic:
        blockers.append("PHASE22_V2_TRADER_LOGIC_ALREADY_EXECUTED")

    if not SHADOW_CERTIFICATION_RECEIPTS.phase21_policy_freeze_sealed:
        blockers.append("PHASE21_POLICY_FREEZE_NOT_SEALED")

    calibration = build_terminal_calibration_readiness()
    if calibration.calibration_manifest is None:
        blockers.append("CALIBRATION_FREEZE_MANIFEST_NOT_SEALED")
        calibration_sha = "sha256:" + "0" * 64
    else:
        calibration_sha = calibration.calibration_manifest.fingerprint()

    if not PROVIDER_CORE_FREEZE_RECEIPT.core_pre_holdout_ready:
        blockers.append("PROVIDER_CORE_FREEZE_NOT_READY")

    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    parity_sha: str | None = None
    if parity is None:
        blockers.append(PARITY_BLOCKER)
    else:
        parity_sha = parity.fingerprint()

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    state = (
        CiboPhase22V2PreHoldoutState.PRE_HOLDOUT_FROZEN
        if ready
        else (
            CiboPhase22V2PreHoldoutState.LOCKED_PENDING_PARITY
            if tuple(blockers) == (PARITY_BLOCKER,)
            else CiboPhase22V2PreHoldoutState.INVALID
        )
    )
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    return CiboPhase22V2PreHoldoutReadiness(
        state=state,
        candidate_id=candidate.candidate_id,
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        phase21_policy_freeze_sha256=PHASE21_FREEZE_ARTIFACT_DIGEST,
        phase21_policy_freeze_head_sha=PHASE21_FREEZE_HEAD,
        calibration_freeze_sha256=calibration_sha,
        provider_core_freeze_sha256=PROVIDER_COMPONENT_FREEZE_SHA256,
        candidate_code_sha=frozen.code_sha,
        candidate_parameter_sha256=frozen.parameter_sha256(),
        qualification_plan_sha256=phase22_holdout_qualification_plan_sha256(),
        parity_manifest_sha256=parity_sha,
        burn_clean=burn_clean,
        source_stage_outcomes_inspected=source_outcomes_inspected,
        source_stage_trader_logic_executed=source_trader_logic,
        blockers=tuple(blockers),
        ready_to_unseal_v2=ready,
    )
