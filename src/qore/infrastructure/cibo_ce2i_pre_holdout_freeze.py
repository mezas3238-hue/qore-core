"""Absolute pre-holdout seal for the CIBO USD60 six-month examination."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PRE_HOLDOUT_CHECKPOINT_RUN_ID = 36877118070
PRE_HOLDOUT_CHECKPOINT_ARTIFACT_ID = 11169417941
PRE_HOLDOUT_CHECKPOINT_ARTIFACT_DIGEST = (
    "sha256:33c2969e8b63f8869d1b391ff1e35f3c81bf963785b52418ce06d634b713d85d"
)
PRE_HOLDOUT_CHECKPOINT_HEAD_SHA = (
    "b09b1d38b757651a56059193a092268e71d16f4f"
)
CALIBRATION_FREEZE_RUN_ID = 36876893953
CALIBRATION_FREEZE_ARTIFACT_ID = 11169022417
CALIBRATION_FREEZE_ARTIFACT_DIGEST = (
    "sha256:bd98780b1d2ebddf0b1232d9d545f3eb4eb03fa04836fee99d7d033a24d7bc17"
)
CALIBRATION_MANIFEST_FINGERPRINT = (
    "sha256:81efc3f466f7856c14eb3a44db04b9f73f9a8b50b520498be4e728479e4b5955"
)


class CiboHoldoutSealState(StrEnum):
    SEALED_UNTOUCHED = "SEALED_UNTOUCHED"
    PRE_HOLDOUT_FROZEN = "PRE_HOLDOUT_FROZEN"
    UNSEALED_FOR_EXAM = "UNSEALED_FOR_EXAM"
    BURNED = "BURNED"


@dataclass(frozen=True, slots=True)
class CiboPreHoldoutFreezeManifest:
    head_sha: str
    config_sha256: str
    calibration_sha256: str
    dataset_sha256: str
    phase20d_qualification_sha256: str
    phase21_policy_freeze_sha256: str
    anti_leakage_passed: bool
    phase20d_causal_tool_gate_passed: bool
    phase21_policy_freeze_sealed: bool
    all_calibrations_frozen: bool
    provider_economics_frozen: bool

    def __post_init__(self) -> None:
        for name in (
            "head_sha",
            "config_sha256",
            "calibration_sha256",
            "dataset_sha256",
            "phase20d_qualification_sha256",
            "phase21_policy_freeze_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"pre-holdout freeze {name} is required"
                )
        for name in (
            "anti_leakage_passed",
            "phase20d_causal_tool_gate_passed",
            "phase21_policy_freeze_sealed",
            "all_calibrations_frozen",
            "provider_economics_frozen",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"pre-holdout freeze {name} must be bool"
                )


ACTIVE_PRE_HOLDOUT_FREEZE: CiboPreHoldoutFreezeManifest | None = (
    CiboPreHoldoutFreezeManifest(
        head_sha=PRE_HOLDOUT_CHECKPOINT_HEAD_SHA,
        config_sha256=(
            "1166add8e3d2fc00c1a981f0f21879bf492a77b5f296a44bf7d4369b5f279c0d"
        ),
        calibration_sha256=CALIBRATION_MANIFEST_FINGERPRINT,
        dataset_sha256=(
            "sha256:f3dc5027a2f35983a7bee2a33f0400139e212b4b578618be7baba523da09507e"
        ),
        phase20d_qualification_sha256=(
            "sha256:cb5991afd27d2b73f4854c4105699744e2aa3c173a58262305d37d4ad083ddce"
        ),
        phase21_policy_freeze_sha256=(
            "sha256:5fe57ffb75d66c8f7e4ab4c2523a875e12f9be905bc43a36722aa3e0f9c5cd45"
        ),
        anti_leakage_passed=True,
        phase20d_causal_tool_gate_passed=True,
        phase21_policy_freeze_sealed=True,
        all_calibrations_frozen=True,
        provider_economics_frozen=True,
    )
)
CURRENT_HOLDOUT_SEAL_STATE = CiboHoldoutSealState.PRE_HOLDOUT_FROZEN


def pre_holdout_freeze_ready() -> bool:
    manifest = ACTIVE_PRE_HOLDOUT_FREEZE
    return (
        CURRENT_HOLDOUT_SEAL_STATE
        is CiboHoldoutSealState.PRE_HOLDOUT_FROZEN
        and manifest is not None
        and manifest.anti_leakage_passed
        and manifest.phase20d_causal_tool_gate_passed
        and manifest.phase21_policy_freeze_sealed
        and manifest.all_calibrations_frozen
        and manifest.provider_economics_frozen
    )


def pre_holdout_freeze_receipt_payload() -> dict[str, object]:
    manifest = ACTIVE_PRE_HOLDOUT_FREEZE
    if manifest is None:
        raise CiboCapitalManagementError(
            "pre-holdout freeze receipt unavailable"
        )
    return {
        "seal_state": CURRENT_HOLDOUT_SEAL_STATE.value,
        "ready": pre_holdout_freeze_ready(),
        "manifest": asdict(manifest),
        "checkpoint": {
            "run_id": PRE_HOLDOUT_CHECKPOINT_RUN_ID,
            "artifact_id": PRE_HOLDOUT_CHECKPOINT_ARTIFACT_ID,
            "artifact_digest": PRE_HOLDOUT_CHECKPOINT_ARTIFACT_DIGEST,
        },
        "calibration_freeze": {
            "run_id": CALIBRATION_FREEZE_RUN_ID,
            "artifact_id": CALIBRATION_FREEZE_ARTIFACT_ID,
            "artifact_digest": CALIBRATION_FREEZE_ARTIFACT_DIGEST,
            "manifest_fingerprint": CALIBRATION_MANIFEST_FINGERPRINT,
        },
        "governance": {
            "holdout_outcomes_inspected": False,
            "holdout_market_data_read_before_freeze": False,
            "productive_authority": False,
        },
    }


def require_pre_holdout_freeze_before_2017h1_access() -> None:
    if not pre_holdout_freeze_ready():
        raise CiboCapitalManagementError(
            "2017H1 SEALED_UNTOUCHED until CIBO PRE-HOLDOUT FREEZE is active"
        )
