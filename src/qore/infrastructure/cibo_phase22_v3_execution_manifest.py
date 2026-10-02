"""Immutable pre-outcome execution manifest for Phase22 V3.

The manifest binds the exact V3 market-source receipt, preregistered policy
bundle, scientific eligibility freeze, frozen Trader parity, and current
counterfactual provider execution calibration. It carries no fresh outcomes
and grants no broker, LIVE, real-capital, production, or merge authority.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)
from qore.infrastructure.cibo_phase22_next_exam_governance import (
    CURRENT_NEXT_PHASE22_READINESS,
    NEXT_CANDIDATE_ID,
    NextPhase22ReadinessStatus,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution_receipt import (
    PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v3_source_receipt import (
    phase22_v3_source_receipt_sha256,
)

SCHEMA = "qore.cibo.phase22.v3-execution-manifest.v1"


@dataclass(frozen=True, slots=True)
class Phase22V3ExecutionTraderBinding:
    trader_id: str
    methodology_git_sha: str
    replay_engine_sha256: str
    parameter_sha256: str
    parity_artifact_ref: str
    parity_artifact_digest: str

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "V3 execution Trader identity drift"
            )
        if len(self.methodology_git_sha) != 40:
            raise CiboCapitalManagementError(
                "V3 methodology Git SHA invalid"
            )
        for name in (
            "replay_engine_sha256",
            "parameter_sha256",
            "parity_artifact_digest",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"V3 execution {name} invalid"
                )
        if not self.parity_artifact_ref:
            raise CiboCapitalManagementError(
                "V3 parity artifact ref required"
            )


@dataclass(frozen=True, slots=True)
class Phase22V3ExecutionManifest:
    candidate_id: str
    source_receipt_sha256: str
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    provider_execution_calibration_receipt_sha256: str
    provider_numeric_execution_freeze_receipt_sha256: str
    parity_manifest_sha256: str
    trader_bindings: tuple[Phase22V3ExecutionTraderBinding, ...]
    fresh_outcomes_executed: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != NEXT_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "V3 execution candidate identity drift"
            )
        expected = (
            ("source_receipt_sha256", phase22_v3_source_receipt_sha256()),
            (
                "policy_bundle_sha256",
                NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint(),
            ),
            (
                "advanced_scientific_eligibility_sha256",
                NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint(),
            ),
            (
                "provider_execution_calibration_receipt_sha256",
                PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint(),
            ),
            (
                "provider_numeric_execution_freeze_receipt_sha256",
                PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT.fingerprint(),
            ),
        )
        for name, value in expected:
            if getattr(self, name) != value:
                raise CiboCapitalManagementError(
                    f"V3 execution manifest {name} drift"
                )
        parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
        if parity is None:
            raise CiboCapitalManagementError(
                "V3 execution parity manifest missing"
            )
        if self.parity_manifest_sha256 != parity.fingerprint():
            raise CiboCapitalManagementError(
                "V3 execution parity manifest drift"
            )
        ids = tuple(item.trader_id for item in self.trader_bindings)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "V3 execution requires exact ordered 7/7 Traders"
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
                    "V3 execution/parity binding drift"
                )
        if any(
            (
                self.fresh_outcomes_executed,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "V3 execution manifest carries forbidden authority/outcomes"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "candidate_id": self.candidate_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "policy_bundle_sha256": self.policy_bundle_sha256,
            "advanced_scientific_eligibility_sha256": (
                self.advanced_scientific_eligibility_sha256
            ),
            "provider_execution_calibration_receipt_sha256": (
                self.provider_execution_calibration_receipt_sha256
            ),
            "provider_numeric_execution_freeze_receipt_sha256": (
                self.provider_numeric_execution_freeze_receipt_sha256
            ),
            "parity_manifest_sha256": self.parity_manifest_sha256,
            "trader_bindings": [asdict(item) for item in self.trader_bindings],
            "fresh_outcomes_executed": False,
            "broker_mutation_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
            "productive_authority": False,
            "manifest_sha256": self.fingerprint(),
        }

    def fingerprint(self) -> str:
        payload = self.payload()
        payload.pop("manifest_sha256", None)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + sha256(raw).hexdigest()


def build_phase22_v3_execution_manifest() -> Phase22V3ExecutionManifest:
    readiness = CURRENT_NEXT_PHASE22_READINESS
    if readiness.status not in {
        NextPhase22ReadinessStatus.NOT_READY,
        NextPhase22ReadinessStatus.READY,
    }:
        raise CiboCapitalManagementError(
            "V3 execution manifest requires non-invalid readiness"
        )
    if tuple(readiness.blockers) not in {
        ("NEW_ONE_SHOT_OWNER_AUTHORIZATION_REQUIRED",),
        (),
    }:
        raise CiboCapitalManagementError(
            "V3 execution manifest has unresolved pre-outcome blockers"
        )
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError(
            "V3 execution manifest cannot build without parity"
        )
    bindings = tuple(
        Phase22V3ExecutionTraderBinding(
            trader_id=item.trader_id,
            methodology_git_sha=item.methodology_git_sha,
            replay_engine_sha256=item.replay_engine_sha256,
            parameter_sha256=item.parameter_sha256,
            parity_artifact_ref=item.parity_artifact_ref,
            parity_artifact_digest=item.parity_artifact_digest,
        )
        for item in parity.receipts
    )
    return Phase22V3ExecutionManifest(
        candidate_id=NEXT_CANDIDATE_ID,
        source_receipt_sha256=phase22_v3_source_receipt_sha256(),
        policy_bundle_sha256=NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint(),
        advanced_scientific_eligibility_sha256=(
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ),
        provider_execution_calibration_receipt_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
        provider_numeric_execution_freeze_receipt_sha256=(
            PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT.fingerprint()
        ),
        parity_manifest_sha256=parity.fingerprint(),
        trader_bindings=bindings,
    )
