"""Immutable receipt for the CIBO Core provider-economics freeze."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_provider_economics_component_freeze import (
    CiboProviderEconomicsComponentFreeze,
    freeze_current_ctrader_demo_provider_economics,
)
from qore.infrastructure.cibo_ce2i_provider_stress_bound_freeze import (
    CiboProviderStressBoundFreeze,
    build_provider_stress_bound_freeze,
)

PROVIDER_CORE_FREEZE_RUN_ID = 36874074682
PROVIDER_CORE_FREEZE_ARTIFACT_ID = 11168043616
PROVIDER_CORE_FREEZE_ARTIFACT_DIGEST = (
    "sha256:4512f736823bb43274f99bd01fb0114d93ba533b301b8ec6fa75512f59ae0462"
)
PROVIDER_CORE_FREEZE_HEAD_SHA = "f2295007d0b725bcf8404afedcebef8929236be1"
PROVIDER_CORE_FREEZE_FROZEN_AT = datetime.fromisoformat(
    "2026-10-01T14:09:28.673672+00:00"
)
PROVIDER_COMPONENT_FREEZE_SHA256 = (
    "sha256:92ffd332c73af5ba1592a2fb1433a3e3e24eca7e74b3cfe20760bc48c0fc27f9"
)
PROVIDER_STRESS_BOUND_SHA256 = (
    "sha256:cbbbb217ffea5fd8c3002493fa6a9f23617de4db40eb04c340f0d409e253de8d"
)
PROVIDER_STRESS_MATRIX_SHA256 = (
    "sha256:6ddbfc83127463a2068805d0cfe61aca43798ee947fb9c0c5a6bedfb4668a3da"
)


@dataclass(frozen=True, slots=True)
class CiboProviderCoreFreezeReceipt:
    core_pre_holdout_ready: bool
    provider_deployment_ready: bool
    empirical_slippage_claimed: bool
    historical_provider_economics_claimed: bool
    holdout_outcomes_used: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        if (
            not self.core_pre_holdout_ready
            or self.provider_deployment_ready
            or self.empirical_slippage_claimed
            or self.historical_provider_economics_claimed
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "provider core-freeze receipt governance drift"
            )


PROVIDER_CORE_FREEZE_RECEIPT = CiboProviderCoreFreezeReceipt(
    core_pre_holdout_ready=True,
    provider_deployment_ready=False,
    empirical_slippage_claimed=False,
    historical_provider_economics_claimed=False,
    holdout_outcomes_used=False,
    productive_authority=False,
)


def build_provider_core_stress_bound() -> CiboProviderStressBoundFreeze:
    inventory = {
        "schema": "qore.cibo.ctrader_demo.empirical_slippage.v1",
        "status": "EMPIRICAL_SLIPPAGE_NOT_READY",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_entry_deals_found": 3,
        "market_entry_deals_found": 1,
        "qore_deals_found": 1,
        "empirical_slippage_calibrated": False,
        "execution_model_ready": False,
        "broker_mutation_performed": False,
        "holdout_outcomes_used": False,
        "historical_2017_exact_claimed": False,
        "target_aware": False,
        "productive_authority": False,
    }
    stress = build_provider_stress_bound_freeze(
        empirical_inventory=inventory,
        frozen_at=PROVIDER_CORE_FREEZE_FROZEN_AT,
    )
    if stress.fingerprint() != PROVIDER_STRESS_BOUND_SHA256:
        raise CiboCapitalManagementError(
            "provider stress-bound receipt fingerprint drift"
        )
    return stress


def build_provider_core_component_freeze(
) -> CiboProviderEconomicsComponentFreeze:
    component = freeze_current_ctrader_demo_provider_economics(
        frozen_at=PROVIDER_CORE_FREEZE_FROZEN_AT,
        stress_bound=build_provider_core_stress_bound(),
    )
    if component.fingerprint() != PROVIDER_COMPONENT_FREEZE_SHA256:
        raise CiboCapitalManagementError(
            "provider component receipt fingerprint drift"
        )
    return component


def provider_core_freeze_receipt_payload() -> dict[str, object]:
    return {
        "run_id": PROVIDER_CORE_FREEZE_RUN_ID,
        "artifact_id": PROVIDER_CORE_FREEZE_ARTIFACT_ID,
        "artifact_digest": PROVIDER_CORE_FREEZE_ARTIFACT_DIGEST,
        "head_sha": PROVIDER_CORE_FREEZE_HEAD_SHA,
        "frozen_at": PROVIDER_CORE_FREEZE_FROZEN_AT.isoformat(),
        "provider_component_freeze_sha256": PROVIDER_COMPONENT_FREEZE_SHA256,
        "provider_stress_bound_sha256": PROVIDER_STRESS_BOUND_SHA256,
        "provider_stress_matrix_sha256": PROVIDER_STRESS_MATRIX_SHA256,
        "certification_lane": "PREDECLARED_STRESS_BOUND",
        "core_pre_holdout_ready": True,
        "provider_deployment_ready": False,
        "empirical_slippage_claimed": False,
        "historical_provider_economics_claimed": False,
        "holdout_outcomes_used": False,
        "productive_authority": False,
    }
