"""Immutable Phase22 V2 execution manifest.

This manifest binds every prerequisite that may be known before fresh outcomes.
It grants no execution authority by itself.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_pre_holdout_freeze_v2 import (
    CiboPhase22V2PreHoldoutState,
    evaluate_phase22_v2_pre_holdout_readiness,
)
from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_COMPONENT_FREEZE_SHA256,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    CANONICAL_PHASE22_TRADER_IDS,
)

SCHEMA = "qore.cibo.phase22.execution-manifest.v2"


@dataclass(frozen=True, slots=True)
class Phase22ExecutionTraderBinding:
    trader_id: str
    methodology_git_sha: str
    replay_engine_sha256: str
    parameter_sha256: str
    parity_artifact_ref: str
    parity_artifact_digest: str

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 execution Trader identity drift"
            )
        if len(self.methodology_git_sha) != 40:
            raise CiboCapitalManagementError(
                "Phase22 execution methodology Git SHA invalid"
            )
        for name in (
            "replay_engine_sha256",
            "parameter_sha256",
            "parity_artifact_digest",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"Phase22 execution {name} invalid"
                )
        if not self.parity_artifact_ref:
            raise CiboCapitalManagementError(
                "Phase22 execution parity artifact ref required"
            )


@dataclass(frozen=True, slots=True)
class CiboPhase22ExecutionManifest:
    candidate_id: str
    source_receipt_sha256: str
    pre_holdout_source_receipt_sha256: str
    phase21_policy_freeze_sha256: str
    calibration_freeze_sha256: str
    provider_core_freeze_sha256: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    qualification_plan_sha256: str
    parity_manifest_sha256: str
    trader_bindings: tuple[Phase22ExecutionTraderBinding, ...]
    fresh_outcomes_executed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        readiness = evaluate_phase22_v2_pre_holdout_readiness()
        if readiness.state is not CiboPhase22V2PreHoldoutState.PRE_HOLDOUT_FROZEN:
            raise CiboCapitalManagementError(
                "Phase22 execution manifest requires frozen pre-holdout"
            )
        if not readiness.ready_to_unseal_v2:
            raise CiboCapitalManagementError(
                "Phase22 execution manifest requires ready pre-holdout"
            )
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 execution candidate identity drift"
            )
        expected = (
            (
                "source_receipt_sha256",
                phase22_v2_holdout_source_receipt_sha256(),
            ),
            (
                "pre_holdout_source_receipt_sha256",
                readiness.source_receipt_sha256,
            ),
            (
                "phase21_policy_freeze_sha256",
                readiness.phase21_policy_freeze_sha256,
            ),
            (
                "calibration_freeze_sha256",
                readiness.calibration_freeze_sha256,
            ),
            (
                "provider_core_freeze_sha256",
                PROVIDER_COMPONENT_FREEZE_SHA256,
            ),
            ("candidate_code_sha", readiness.candidate_code_sha),
            (
                "candidate_parameter_sha256",
                readiness.candidate_parameter_sha256,
            ),
            (
                "qualification_plan_sha256",
                readiness.qualification_plan_sha256,
            ),
            (
                "parity_manifest_sha256",
                readiness.parity_manifest_sha256,
            ),
        )
        for name, value in expected:
            if getattr(self, name) != value:
                raise CiboCapitalManagementError(
                    f"Phase22 execution manifest {name} drift"
                )
        ids = tuple(item.trader_id for item in self.trader_bindings)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 execution manifest requires exact ordered 7/7 surface"
            )
        parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
        if parity is None:
            raise CiboCapitalManagementError(
                "Phase22 execution parity manifest missing"
            )
        for binding, receipt in zip(
            self.trader_bindings,
            parity.receipts,
            strict=True,
        ):
            if (
                binding.trader_id != receipt.trader_id
                or binding.methodology_git_sha != receipt.methodology_git_sha
                or binding.replay_engine_sha256 != receipt.replay_engine_sha256
                or binding.parameter_sha256 != receipt.parameter_sha256
                or binding.parity_artifact_ref != receipt.parity_artifact_ref
                or binding.parity_artifact_digest
                != receipt.parity_artifact_digest
            ):
                raise CiboCapitalManagementError(
                    "Phase22 execution/parity binding drift"
                )
        if self.fresh_outcomes_executed or self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 execution manifest cannot carry outcomes/authority"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "candidate_id": self.candidate_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "pre_holdout_source_receipt_sha256": (
                self.pre_holdout_source_receipt_sha256
            ),
            "phase21_policy_freeze_sha256": self.phase21_policy_freeze_sha256,
            "calibration_freeze_sha256": self.calibration_freeze_sha256,
            "provider_core_freeze_sha256": self.provider_core_freeze_sha256,
            "candidate_code_sha": self.candidate_code_sha,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "qualification_plan_sha256": self.qualification_plan_sha256,
            "parity_manifest_sha256": self.parity_manifest_sha256,
            "trader_bindings": [
                asdict(item) for item in self.trader_bindings
            ],
            "fresh_outcomes_executed": False,
            "productive_authority": False,
            "manifest_sha256": self.fingerprint(),
        }

    def fingerprint(self) -> str:
        payload = {
            "schema": SCHEMA,
            "candidate_id": self.candidate_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "pre_holdout_source_receipt_sha256": (
                self.pre_holdout_source_receipt_sha256
            ),
            "phase21_policy_freeze_sha256": self.phase21_policy_freeze_sha256,
            "calibration_freeze_sha256": self.calibration_freeze_sha256,
            "provider_core_freeze_sha256": self.provider_core_freeze_sha256,
            "candidate_code_sha": self.candidate_code_sha,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "qualification_plan_sha256": self.qualification_plan_sha256,
            "parity_manifest_sha256": self.parity_manifest_sha256,
            "trader_bindings": [
                asdict(item) for item in self.trader_bindings
            ],
            "fresh_outcomes_executed": False,
            "productive_authority": False,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


def build_phase22_execution_manifest() -> CiboPhase22ExecutionManifest:
    readiness = evaluate_phase22_v2_pre_holdout_readiness()
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError(
            "Phase22 execution manifest cannot build without parity"
        )
    bindings = tuple(
        Phase22ExecutionTraderBinding(
            trader_id=item.trader_id,
            methodology_git_sha=item.methodology_git_sha,
            replay_engine_sha256=item.replay_engine_sha256,
            parameter_sha256=item.parameter_sha256,
            parity_artifact_ref=item.parity_artifact_ref,
            parity_artifact_digest=item.parity_artifact_digest,
        )
        for item in parity.receipts
    )
    assert readiness.parity_manifest_sha256 is not None
    return CiboPhase22ExecutionManifest(
        candidate_id=CANDIDATE_ID,
        source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
        pre_holdout_source_receipt_sha256=readiness.source_receipt_sha256,
        phase21_policy_freeze_sha256=readiness.phase21_policy_freeze_sha256,
        calibration_freeze_sha256=readiness.calibration_freeze_sha256,
        provider_core_freeze_sha256=PROVIDER_COMPONENT_FREEZE_SHA256,
        candidate_code_sha=readiness.candidate_code_sha,
        candidate_parameter_sha256=readiness.candidate_parameter_sha256,
        qualification_plan_sha256=readiness.qualification_plan_sha256,
        parity_manifest_sha256=readiness.parity_manifest_sha256,
        trader_bindings=bindings,
    )
