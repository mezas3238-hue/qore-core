"""Admit proven Architect-A2 scientific dependencies into the isolated A1 lane.

A1 may consume a small set of A2-owned mechanisms, but may never implement or
close those workstreams. This contract consumes the canonical Phase22
scientific disposition receipt shared by Architect A/A2 and binds it to the
same canonical Phase22 manifest already bridged by A1.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    A1Phase22CanonicalScientificManifestBridge,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

CONTRACT_ID = "CIBO_A1_A2_SCIENTIFIC_DEPENDENCY_ADMISSION_V1"
A1_ALLOWED_A2_DEPENDENCIES = (
    "COMPOUND_ENGINE",
    "INTERNAL_CAPITAL_MARKET",
    "PROTECTED_BASE_CAPITAL",
    "PROFIT_PROTECTION",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1A2ScientificDependencyAdmission:
    contract_id: str
    a2_workstream_id: str
    canonical_phase22_manifest_sha256: str
    a1_manifest_bridge_sha256: str
    a2_source_head: str
    a2_source_gate_id: str
    a2_source_gate_evidence_sha256: str
    a2_disposition_receipt_sha256: str
    recommended_disposition: str
    admitted_for_a1_consumption: bool
    a1_modifies_a2_workstream: bool = False
    a1_closes_a2_workstream: bool = False
    integration_authority: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != CONTRACT_ID:
            raise CiboCapitalManagementError(
                "A1/A2 dependency admission identity drift"
            )
        if self.a2_workstream_id not in A1_ALLOWED_A2_DEPENDENCIES:
            raise CiboCapitalManagementError(
                "A1/A2 dependency outside allowed cross-lane surface"
            )
        for name in (
            "canonical_phase22_manifest_sha256",
            "a1_manifest_bridge_sha256",
            "a2_source_gate_evidence_sha256",
            "a2_disposition_receipt_sha256",
        ):
            _sha(getattr(self, name), name)
        if _SHA1_RE.fullmatch(self.a2_source_head) is None:
            raise CiboCapitalManagementError(
                "A1/A2 dependency source HEAD invalid"
            )
        if not self.a2_source_gate_id:
            raise CiboCapitalManagementError(
                "A1/A2 dependency source gate identity required"
            )
        if self.recommended_disposition != "COMPLETED_AND_PROVEN":
            raise CiboCapitalManagementError(
                "A1 may consume only proven A2 scientific dependencies"
            )
        if not self.admitted_for_a1_consumption:
            raise CiboCapitalManagementError(
                "A1/A2 dependency admission must be explicit"
            )
        if (
            self.a1_modifies_a2_workstream
            or self.a1_closes_a2_workstream
            or self.integration_authority
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "A1/A2 dependency admission violates ownership/governance"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def admit_proven_a2_dependency_for_a1(
    *,
    bridge: A1Phase22CanonicalScientificManifestBridge,
    a2_source_head: str,
    receipt: ArchitectAPhase22V2ScientificDispositionReceipt,
) -> A1A2ScientificDependencyAdmission:
    """Admit one proven A2 workstream without transferring ownership to A1."""

    if not isinstance(
        bridge,
        A1Phase22CanonicalScientificManifestBridge,
    ):
        raise CiboCapitalManagementError(
            "A1/A2 dependency requires canonical A1 Phase22 bridge"
        )
    if not isinstance(
        receipt,
        ArchitectAPhase22V2ScientificDispositionReceipt,
    ):
        raise CiboCapitalManagementError(
            "A1/A2 dependency requires canonical A2 disposition receipt"
        )
    if receipt.schema != PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA:
        raise CiboCapitalManagementError(
            "A1/A2 dependency scientific receipt schema drift"
        )
    if receipt.workstream_id not in A1_ALLOWED_A2_DEPENDENCIES:
        raise CiboCapitalManagementError(
            "A1/A2 dependency workstream not consumable by A1"
        )
    if (
        receipt.phase22_manifest_sha256
        != bridge.canonical_phase22_manifest_sha256
    ):
        raise CiboCapitalManagementError(
            "A1/A2 dependency canonical Phase22 manifest drift"
        )
    if receipt.recommended_disposition != "COMPLETED_AND_PROVEN":
        raise CiboCapitalManagementError(
            "A1/A2 dependency is not scientifically proven"
        )
    if not receipt.passed or receipt.blockers or receipt.failed_dimensions:
        raise CiboCapitalManagementError(
            "A1/A2 dependency proven disposition has contradictory evidence"
        )
    if _SHA1_RE.fullmatch(a2_source_head) is None:
        raise CiboCapitalManagementError(
            "A1/A2 dependency source HEAD invalid"
        )

    return A1A2ScientificDependencyAdmission(
        contract_id=CONTRACT_ID,
        a2_workstream_id=receipt.workstream_id,
        canonical_phase22_manifest_sha256=receipt.phase22_manifest_sha256,
        a1_manifest_bridge_sha256=bridge.fingerprint(),
        a2_source_head=a2_source_head,
        a2_source_gate_id=receipt.source_gate_id,
        a2_source_gate_evidence_sha256=receipt.source_gate_evidence_sha256,
        a2_disposition_receipt_sha256=_receipt_sha256(receipt),
        recommended_disposition=receipt.recommended_disposition,
        admitted_for_a1_consumption=True,
    )


def _receipt_sha256(
    receipt: ArchitectAPhase22V2ScientificDispositionReceipt,
) -> str:
    raw = json.dumps(
        receipt.as_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"A1/A2 dependency {name} must be canonical SHA-256"
        )
