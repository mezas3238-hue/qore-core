"""Immutable pre-outcome execution manifest for Phase22 V4."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    FROZEN_V4_ADVANCED_ELIGIBILITY_SHA256,
    FROZEN_V4_POLICY_BUNDLE_SHA256,
    load_phase22_v4_source_receipt,
)
from qore.infrastructure.cibo_phase22_v4_vt31_abi import (
    v4_vt31_source_abi_sha256,
)

SOURCE_RECEIPT_PATH = Path(
    "docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json"
)
SCHEMA = "qore.cibo.phase22.v4-execution-manifest.v1"


@dataclass(frozen=True, slots=True)
class Phase22V4ExecutionTraderBinding:
    trader_id: str
    methodology_git_sha: str
    replay_engine_sha256: str
    parameter_sha256: str
    parity_artifact_ref: str
    parity_artifact_digest: str

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError("V4 Trader identity drift")
        if len(self.methodology_git_sha) != 40:
            raise CiboCapitalManagementError("V4 methodology SHA invalid")
        for name in (
            "replay_engine_sha256",
            "parameter_sha256",
            "parity_artifact_digest",
        ):
            value = getattr(self, name)
            if not value.startswith("sha256:") or len(value) != 71:
                raise CiboCapitalManagementError(
                    f"V4 execution {name} invalid"
                )


@dataclass(frozen=True, slots=True)
class Phase22V4ExecutionManifest:
    candidate_id: str
    source_receipt_sha256: str
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    provider_execution_calibration_receipt_sha256: str
    provider_numeric_execution_freeze_receipt_sha256: str
    parity_manifest_sha256: str
    vt31_source_abi_sha256: str
    trader_bindings: tuple[Phase22V4ExecutionTraderBinding, ...]
    fresh_outcomes_executed: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False
    merge_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        source = load_phase22_v4_source_receipt(SOURCE_RECEIPT_PATH)
        if self.candidate_id != V4_CANDIDATE_ID:
            raise CiboCapitalManagementError("V4 execution candidate drift")
        expected = (
            ("source_receipt_sha256", source.fingerprint()),
            ("policy_bundle_sha256", FROZEN_V4_POLICY_BUNDLE_SHA256),
            (
                "advanced_scientific_eligibility_sha256",
                FROZEN_V4_ADVANCED_ELIGIBILITY_SHA256,
            ),
            (
                "provider_execution_calibration_receipt_sha256",
                PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint(),
            ),
            (
                "provider_numeric_execution_freeze_receipt_sha256",
                PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT.fingerprint(),
            ),
            ("vt31_source_abi_sha256", v4_vt31_source_abi_sha256()),
        )
        for name, value in expected:
            if getattr(self, name) != value:
                raise CiboCapitalManagementError(
                    f"V4 execution manifest {name} drift"
                )
        parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
        if parity is None or self.parity_manifest_sha256 != parity.fingerprint():
            raise CiboCapitalManagementError("V4 parity manifest drift")
        ids = tuple(item.trader_id for item in self.trader_bindings)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "V4 execution requires exact ordered 7/7 Traders"
            )
        for binding, receipt in zip(
            self.trader_bindings, parity.receipts, strict=True
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
                    "V4 execution/parity binding drift"
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
                "V4 manifest carries forbidden authority/outcomes"
            )

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            **asdict(self),
            "trader_bindings": [asdict(item) for item in self.trader_bindings],
        }
        raw = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        payload["manifest_sha256"] = "sha256:" + sha256(raw).hexdigest()
        return payload

    def fingerprint(self) -> str:
        return str(self.payload()["manifest_sha256"])


def build_phase22_v4_execution_manifest() -> Phase22V4ExecutionManifest:
    source = load_phase22_v4_source_receipt(SOURCE_RECEIPT_PATH)
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError("V4 parity manifest missing")
    bindings = tuple(
        Phase22V4ExecutionTraderBinding(
            trader_id=item.trader_id,
            methodology_git_sha=item.methodology_git_sha,
            replay_engine_sha256=item.replay_engine_sha256,
            parameter_sha256=item.parameter_sha256,
            parity_artifact_ref=item.parity_artifact_ref,
            parity_artifact_digest=item.parity_artifact_digest,
        )
        for item in parity.receipts
    )
    return Phase22V4ExecutionManifest(
        candidate_id=V4_CANDIDATE_ID,
        source_receipt_sha256=source.fingerprint(),
        policy_bundle_sha256=FROZEN_V4_POLICY_BUNDLE_SHA256,
        advanced_scientific_eligibility_sha256=(
            FROZEN_V4_ADVANCED_ELIGIBILITY_SHA256
        ),
        provider_execution_calibration_receipt_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
        provider_numeric_execution_freeze_receipt_sha256=(
            PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT.fingerprint()
        ),
        parity_manifest_sha256=parity.fingerprint(),
        vt31_source_abi_sha256=v4_vt31_source_abi_sha256(),
        trader_bindings=bindings,
    )
