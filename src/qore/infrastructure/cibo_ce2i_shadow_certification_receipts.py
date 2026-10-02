"""Immutable receipts for the owner-authorized CIBO shadow certification lane."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PHASE20_SHADOW_RUN_ID = 36857676494
PHASE20_SHADOW_ARTIFACT_ID = 11160430022
PHASE20_SHADOW_ARTIFACT_DIGEST = (
    "sha256:cb5991afd27d2b73f4854c4105699744e2aa3c173a58262305d37d4ad083ddce"
)
PHASE21_SCREEN_RUN_ID = 36865828999
PHASE21_SCREEN_ARTIFACT_ID = 11164600745
PHASE21_SCREEN_ARTIFACT_DIGEST = (
    "sha256:0b3d0b892207ec3f5873240175eb08dc15cebd31c23d8621472933e691a2990c"
)
PHASE21_FREEZE_RUN_ID = 36866691855
PHASE21_FREEZE_ARTIFACT_ID = 11163637528
PHASE21_FREEZE_ARTIFACT_DIGEST = (
    "sha256:5fe57ffb75d66c8f7e4ab4c2523a875e12f9be905bc43a36722aa3e0f9c5cd45"
)
PHASE21_FREEZE_HEAD = "867c676ac6ad8950bf9fa3debaa52e02efeebec8"


@dataclass(frozen=True, slots=True)
class CiboShadowCertificationReceipts:
    phase20_shadow_passed: bool
    phase21_screen_passed: bool
    phase21_policy_freeze_sealed: bool
    final_holdout_2017h1_read: bool

    def __post_init__(self) -> None:
        if (
            not self.phase20_shadow_passed
            or not self.phase21_screen_passed
            or not self.phase21_policy_freeze_sealed
            or self.final_holdout_2017h1_read
        ):
            raise CiboCapitalManagementError(
                "shadow certification receipt state is not terminal-safe"
            )


SHADOW_CERTIFICATION_RECEIPTS = CiboShadowCertificationReceipts(
    phase20_shadow_passed=True,
    phase21_screen_passed=True,
    phase21_policy_freeze_sealed=True,
    final_holdout_2017h1_read=False,
)


def shadow_receipt_payload() -> dict[str, object]:
    return {
        "phase20_shadow": {
            "run_id": PHASE20_SHADOW_RUN_ID,
            "artifact_id": PHASE20_SHADOW_ARTIFACT_ID,
            "artifact_digest": PHASE20_SHADOW_ARTIFACT_DIGEST,
            "passed": True,
        },
        "phase21_screen": {
            "run_id": PHASE21_SCREEN_RUN_ID,
            "artifact_id": PHASE21_SCREEN_ARTIFACT_ID,
            "artifact_digest": PHASE21_SCREEN_ARTIFACT_DIGEST,
            "passed": True,
        },
        "phase21_policy_freeze": {
            "run_id": PHASE21_FREEZE_RUN_ID,
            "artifact_id": PHASE21_FREEZE_ARTIFACT_ID,
            "artifact_digest": PHASE21_FREEZE_ARTIFACT_DIGEST,
            "head_sha": PHASE21_FREEZE_HEAD,
            "sealed": True,
        },
        "governance": {
            "final_holdout_2017h1_read": False,
            "historical_provider_economics_claimed": False,
            "productive_authority": False,
        },
    }
