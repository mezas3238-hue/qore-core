"""Absolute pre-holdout seal for the CIBO USD60 six-month examination."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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
    anti_leakage_passed: bool
    all_calibrations_frozen: bool
    provider_economics_frozen: bool

    def __post_init__(self) -> None:
        for name in (
            "head_sha",
            "config_sha256",
            "calibration_sha256",
            "dataset_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"pre-holdout freeze {name} is required"
                )
        for name in (
            "anti_leakage_passed",
            "all_calibrations_frozen",
            "provider_economics_frozen",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"pre-holdout freeze {name} must be bool"
                )


# Deliberately None until calibration and provider-economics work is complete.
ACTIVE_PRE_HOLDOUT_FREEZE: CiboPreHoldoutFreezeManifest | None = None
CURRENT_HOLDOUT_SEAL_STATE = CiboHoldoutSealState.SEALED_UNTOUCHED


def pre_holdout_freeze_ready() -> bool:
    manifest = ACTIVE_PRE_HOLDOUT_FREEZE
    return (
        CURRENT_HOLDOUT_SEAL_STATE
        is CiboHoldoutSealState.PRE_HOLDOUT_FROZEN
        and manifest is not None
        and manifest.anti_leakage_passed
        and manifest.all_calibrations_frozen
        and manifest.provider_economics_frozen
    )


def require_pre_holdout_freeze_before_2017h1_access() -> None:
    if not pre_holdout_freeze_ready():
        raise CiboCapitalManagementError(
            "2017H1 SEALED_UNTOUCHED until CIBO PRE-HOLDOUT FREEZE is active"
        )
