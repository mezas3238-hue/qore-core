"""Bridge A1 scientific consumption to the canonical Phase22 V2 intake manifest.

Architect A2 scientific receipts are keyed by the canonical
ArchitectAPhase22V2ScientificIntakeReport.manifest_sha256. A1 additionally
maintains a detailed local consumption manifest for exact decision/policy/fold
population binding. This bridge proves both refer to the same completed Phase22
V2 examination before A1 terminal dispositions can be handed to the Integrator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

BRIDGE_ID = "CIBO_A1_PHASE22_CANONICAL_SCIENTIFIC_MANIFEST_BRIDGE_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1Phase22ExecutionManifestIdentity:
    execution_manifest_sha256: str
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    trader_ids: tuple[str, ...]
    fresh_outcomes_executed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.execution_manifest_sha256) is None:
            raise CiboCapitalManagementError(
                "A1 Phase22 execution manifest digest invalid"
            )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "A1 Phase22 execution candidate identity required"
            )
        if _GIT_SHA_RE.fullmatch(self.candidate_code_sha) is None:
            raise CiboCapitalManagementError(
                "A1 Phase22 execution code SHA invalid"
            )
        if _SHA256_RE.fullmatch(self.candidate_parameter_sha256) is None:
            raise CiboCapitalManagementError(
                "A1 Phase22 execution parameter SHA invalid"
            )
        if not self.trader_ids or len(self.trader_ids) != len(set(self.trader_ids)):
            raise CiboCapitalManagementError(
                "A1 Phase22 execution Trader lineage invalid"
            )
        if self.fresh_outcomes_executed or self.productive_authority:
            raise CiboCapitalManagementError(
                "A1 Phase22 execution identity must remain pre-outcome/non-productive"
            )


@dataclass(frozen=True, slots=True)
class A1Phase22CanonicalScientificManifestBridge:
    bridge_id: str
    canonical_phase22_manifest_sha256: str
    canonical_execution_manifest_sha256: str
    a1_consumption_manifest_sha256: str
    candidate_id: str
    decision_epochs: int
    trader_ids: tuple[str, ...]
    fold_ids: tuple[str, ...]
    qualification_status: str
    ready_for_scientific_reentry: bool
    exact_candidate_binding: bool
    exact_execution_identity_binding: bool
    exact_decision_population_count: bool
    exact_trader_lineage: bool
    exact_fold_lineage: bool
    a2_compatible_manifest_identity: bool
    integration_authority: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.bridge_id != BRIDGE_ID:
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge identity drift"
            )
        for name in (
            "canonical_phase22_manifest_sha256",
            "canonical_execution_manifest_sha256",
            "a1_consumption_manifest_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"A1 Phase22 canonical bridge {name} invalid"
                )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge candidate required"
            )
        if (
            not isinstance(self.decision_epochs, int)
            or isinstance(self.decision_epochs, bool)
            or self.decision_epochs <= 0
        ):
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge decision count invalid"
            )
        if self.fold_ids != _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge requires WF1..WF4"
            )
        if self.qualification_status not in {"PASS", "FAIL"}:
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge qualification must be terminal"
            )
        required_true = (
            self.ready_for_scientific_reentry,
            self.exact_candidate_binding,
            self.exact_execution_identity_binding,
            self.exact_decision_population_count,
            self.exact_trader_lineage,
            self.exact_fold_lineage,
            self.a2_compatible_manifest_identity,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge is not scientifically admissible"
            )
        if (
            self.integration_authority
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "A1 Phase22 canonical bridge grants no authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def bridge_a1_to_canonical_phase22_intake(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    execution_identity: A1Phase22ExecutionManifestIdentity,
) -> A1Phase22CanonicalScientificManifestBridge:
    """Bind the A1 local population manifest to the canonical Phase22 intake."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge requires A1 consumption manifest"
        )
    if not isinstance(intake, ArchitectAPhase22V2ScientificIntakeReport):
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge requires canonical scientific intake"
        )
    if not isinstance(execution_identity, A1Phase22ExecutionManifestIdentity):
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge requires execution manifest identity"
        )
    receipt_refs = dict(intake.receipt_refs)
    execution_receipt_sha = receipt_refs.get("execution_manifest_sha256")
    execution_bound = (
        execution_receipt_sha == execution_identity.execution_manifest_sha256
        and execution_identity.candidate_id == manifest.candidate_id
        and execution_identity.candidate_code_sha == manifest.code_sha
        and execution_identity.candidate_parameter_sha256
        == manifest.parameter_sha256
        and execution_identity.trader_ids == manifest.trader_ids
    )
    candidate_bound = manifest.candidate_id == intake.candidate_id
    decision_bound = manifest.decision_count == intake.decision_epochs
    trader_bound = manifest.trader_ids == intake.trader_ids
    fold_ids = tuple(item.fold_id for item in manifest.folds)
    fold_bound = fold_ids == intake.fold_ids == _CANONICAL_FOLDS
    if not candidate_bound:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge candidate drift"
        )
    if not execution_bound:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge execution identity drift"
        )
    if not decision_bound:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge decision-population count drift"
        )
    if not trader_bound:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge Trader lineage drift"
        )
    if not fold_bound:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge fold lineage drift"
        )
    if not intake.ready_for_scientific_reentry:
        raise CiboCapitalManagementError(
            "A1 Phase22 canonical bridge requires admissible terminal intake"
        )

    return A1Phase22CanonicalScientificManifestBridge(
        bridge_id=BRIDGE_ID,
        canonical_phase22_manifest_sha256=intake.manifest_sha256,
        canonical_execution_manifest_sha256=(
            execution_identity.execution_manifest_sha256
        ),
        a1_consumption_manifest_sha256=manifest.fingerprint(),
        candidate_id=intake.candidate_id,
        decision_epochs=intake.decision_epochs,
        trader_ids=intake.trader_ids,
        fold_ids=intake.fold_ids,
        qualification_status=intake.qualification_status,
        ready_for_scientific_reentry=True,
        exact_candidate_binding=True,
        exact_execution_identity_binding=True,
        exact_decision_population_count=True,
        exact_trader_lineage=True,
        exact_fold_lineage=True,
        a2_compatible_manifest_identity=True,
    )
