"""Pre-outcome policy-lineage freeze for the Phase22 V4 successor.

V4 may repair the VT31 source adapter ABI discovered by the claimed V3 run,
but it may not change CE2I policy, advanced eligibility, Trader methodology,
parameters, thresholds, or selection logic based on V3 fresh outcomes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID

V3_CLAIM_RUN_ID = 37047009381
V3_CLAIM_RUN_ATTEMPT = 1
V3_CLAIM_COMMIT_SHA = "203fa1bbb342b147af47064511e0b7e7d092fe58"
V3_FORENSIC_COMMIT_SHA = "5198754c997910149f3e69c7fc2e9cc86665700d"
VT31_FROZEN_METHODOLOGY_GIT_SHA = (
    "cac38ed14f20e066536910145027426fd23f5939"
)
VT31_SOURCE_ABI_RECOVERY_BUILD_RUN_ID = 37048042164
VT31_SOURCE_ABI_RECOVERY_BUILD_HEAD_SHA = (
    "aa6d1a3101b1d53a31120694b690cce761fca862"
)


@dataclass(frozen=True, slots=True)
class Phase22V4PolicyLineageFreeze:
    candidate_id: str
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    vt31_methodology_git_sha: str
    v3_claim_run_id: int
    v3_claim_run_attempt: int
    v3_claim_commit_sha: str
    v3_forensic_commit_sha: str
    vt31_source_abi_recovery_build_run_id: int
    vt31_source_abi_recovery_build_head_sha: str
    v3_lane_artifact_contents_used_for_policy_selection: bool
    policy_retuned_after_v3: bool
    advanced_eligibility_changed_after_v3: bool
    trader_methodology_changed_after_v3: bool
    trader_parameters_changed_after_v3: bool
    selection_thresholds_changed_after_v3: bool
    vt31_source_abi_repair_authorized: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != V4_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "V4 policy lineage candidate drift"
            )
        if self.policy_bundle_sha256 != (
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V4 policy lineage bundle drift"
            )
        if self.advanced_scientific_eligibility_sha256 != (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V4 advanced eligibility drift"
            )
        if self.vt31_methodology_git_sha != VT31_FROZEN_METHODOLOGY_GIT_SHA:
            raise CiboCapitalManagementError(
                "V4 VT31 methodology drift"
            )
        if (
            self.v3_claim_run_id != V3_CLAIM_RUN_ID
            or self.v3_claim_run_attempt != V3_CLAIM_RUN_ATTEMPT
            or self.v3_claim_commit_sha != V3_CLAIM_COMMIT_SHA
            or self.v3_forensic_commit_sha != V3_FORENSIC_COMMIT_SHA
        ):
            raise CiboCapitalManagementError(
                "V4 predecessor forensic lineage drift"
            )
        if (
            self.vt31_source_abi_recovery_build_run_id
            != VT31_SOURCE_ABI_RECOVERY_BUILD_RUN_ID
            or self.vt31_source_abi_recovery_build_head_sha
            != VT31_SOURCE_ABI_RECOVERY_BUILD_HEAD_SHA
        ):
            raise CiboCapitalManagementError(
                "V4 VT31 ABI proof lineage drift"
            )
        if any(
            (
                self.v3_lane_artifact_contents_used_for_policy_selection,
                self.policy_retuned_after_v3,
                self.advanced_eligibility_changed_after_v3,
                self.trader_methodology_changed_after_v3,
                self.trader_parameters_changed_after_v3,
                self.selection_thresholds_changed_after_v3,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "V4 policy lineage is outcome-contaminated"
            )
        if not self.vt31_source_abi_repair_authorized:
            raise CiboCapitalManagementError(
                "V4 must explicitly bind the pre-outcome VT31 ABI repair"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.v4-policy-lineage-freeze.v1",
            **asdict(self),
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_V4_POLICY_LINEAGE_FREEZE = Phase22V4PolicyLineageFreeze(
    candidate_id=V4_CANDIDATE_ID,
    policy_bundle_sha256=NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint(),
    advanced_scientific_eligibility_sha256=(
        NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
    ),
    vt31_methodology_git_sha=VT31_FROZEN_METHODOLOGY_GIT_SHA,
    v3_claim_run_id=V3_CLAIM_RUN_ID,
    v3_claim_run_attempt=V3_CLAIM_RUN_ATTEMPT,
    v3_claim_commit_sha=V3_CLAIM_COMMIT_SHA,
    v3_forensic_commit_sha=V3_FORENSIC_COMMIT_SHA,
    vt31_source_abi_recovery_build_run_id=(
        VT31_SOURCE_ABI_RECOVERY_BUILD_RUN_ID
    ),
    vt31_source_abi_recovery_build_head_sha=(
        VT31_SOURCE_ABI_RECOVERY_BUILD_HEAD_SHA
    ),
    v3_lane_artifact_contents_used_for_policy_selection=False,
    policy_retuned_after_v3=False,
    advanced_eligibility_changed_after_v3=False,
    trader_methodology_changed_after_v3=False,
    trader_parameters_changed_after_v3=False,
    selection_thresholds_changed_after_v3=False,
    vt31_source_abi_repair_authorized=True,
)
