"""Fail-closed Phase 21 policy-freeze contract for CIBO.

Phase 21 may freeze the CIBO policy only after the frozen Phase20 candidate
passes fresh-forward qualification and the required empirical validations.
This module grants no DEMO, LIVE, execution, Risk, merge or real-capital
authority; it only creates a cryptographically bound research freeze manifest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Phase21EmpiricalValidationKind(StrEnum):
    CAPITAL_STATE_MONTE_CARLO = "CAPITAL_STATE_MONTE_CARLO"
    PROVIDER_STRESS = "PROVIDER_STRESS"
    INTERACTION_ABLATION = "INTERACTION_ABLATION"


_REQUIRED_EMPIRICAL_VALIDATIONS = frozenset(Phase21EmpiricalValidationKind)


@dataclass(frozen=True, slots=True)
class Phase21QualificationReceipt:
    candidate_id: str
    candidate_parameter_sha256: str
    plan_id: str
    plan_sha256: str
    evidence_store_sha256: str
    policy_store_sha256: str
    qualification_artifact_sha256: str
    qualified_at: datetime
    passed: bool

    def __post_init__(self) -> None:
        if self.candidate_id != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 qualification candidate identity drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 qualification parameter digest drift"
            )
        if self.plan_id != FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id:
            raise CiboCapitalManagementError(
                "Phase21 qualification plan identity drift"
            )
        if self.plan_sha256 != phase20d_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase21 qualification plan digest drift"
            )
        for name in (
            "evidence_store_sha256",
            "policy_store_sha256",
            "qualification_artifact_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        _require_aware(self.qualified_at, "qualified_at")
        if not self.passed:
            raise CiboCapitalManagementError(
                "Phase21 requires Phase20D PASS qualification"
            )


@dataclass(frozen=True, slots=True)
class Phase21EmpiricalValidationReceipt:
    kind: Phase21EmpiricalValidationKind
    candidate_id: str
    candidate_parameter_sha256: str
    qualification_artifact_sha256: str
    evidence_class: str
    artifact_sha256: str
    observed_at: datetime
    passed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, Phase21EmpiricalValidationKind):
            raise CiboCapitalManagementError(
                "Phase21 empirical validation kind is invalid"
            )
        if self.candidate_id != FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 empirical candidate identity drift"
            )
        if (
            self.candidate_parameter_sha256
            != FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 empirical parameter digest drift"
            )
        _require_sha256(
            self.qualification_artifact_sha256,
            "qualification_artifact_sha256",
        )
        _require_sha256(self.artifact_sha256, "artifact_sha256")
        _require_aware(self.observed_at, "observed_at")
        if self.evidence_class != "FORWARD_EMPIRICAL":
            raise CiboCapitalManagementError(
                "Phase21 empirical receipt must be FORWARD_EMPIRICAL"
            )
        if not self.passed:
            raise CiboCapitalManagementError(
                "Phase21 empirical validation must PASS"
            )


@dataclass(frozen=True, slots=True)
class Phase21PolicySurfaceDigests:
    state_machine_sha256: str
    tool_registry_sha256: str
    eligibility_sha256: str
    source_ledger_sha256: str
    trader_adapters_sha256: str
    provider_profiles_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "state_machine_sha256",
            "tool_registry_sha256",
            "eligibility_sha256",
            "source_ledger_sha256",
            "trader_adapters_sha256",
            "provider_profiles_sha256",
        ):
            _require_sha256(getattr(self, name), name)

    def payload(self) -> dict[str, str]:
        return {
            "state_machine_sha256": self.state_machine_sha256,
            "tool_registry_sha256": self.tool_registry_sha256,
            "eligibility_sha256": self.eligibility_sha256,
            "source_ledger_sha256": self.source_ledger_sha256,
            "trader_adapters_sha256": self.trader_adapters_sha256,
            "provider_profiles_sha256": self.provider_profiles_sha256,
        }


@dataclass(frozen=True, slots=True)
class Phase21PolicyFreezeManifest:
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    qualification: Phase21QualificationReceipt
    empirical_validations: tuple[Phase21EmpiricalValidationReceipt, ...]
    policy_surface: Phase21PolicySurfaceDigests
    frozen_at: datetime
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        if self.candidate_id != candidate.candidate_id:
            raise CiboCapitalManagementError(
                "Phase21 manifest candidate identity drift"
            )
        if self.candidate_code_sha != candidate.code_sha:
            raise CiboCapitalManagementError(
                "Phase21 manifest code SHA drift"
            )
        if _SHA1_RE.fullmatch(self.candidate_code_sha) is None:
            raise CiboCapitalManagementError(
                "Phase21 manifest code SHA must be lowercase 40-hex"
            )
        if self.candidate_parameter_sha256 != candidate.parameter_sha256():
            raise CiboCapitalManagementError(
                "Phase21 manifest parameter digest drift"
            )
        _require_aware(self.frozen_at, "frozen_at")
        if self.frozen_at <= self.qualification.qualified_at:
            raise CiboCapitalManagementError(
                "Phase21 freeze must follow Phase20D qualification"
            )
        kinds = tuple(item.kind for item in self.empirical_validations)
        if len(kinds) != len(set(kinds)):
            raise CiboCapitalManagementError(
                "Phase21 empirical validation kinds must be unique"
            )
        if frozenset(kinds) != _REQUIRED_EMPIRICAL_VALIDATIONS:
            raise CiboCapitalManagementError(
                "Phase21 requires MC, provider stress and interaction ablation"
            )
        for receipt in self.empirical_validations:
            if (
                receipt.qualification_artifact_sha256
                != self.qualification.qualification_artifact_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase21 empirical receipt qualification lineage mismatch"
                )
            if receipt.observed_at <= self.qualification.qualified_at:
                raise CiboCapitalManagementError(
                    "Phase21 empirical validation must follow qualification"
                )
            if self.frozen_at <= receipt.observed_at:
                raise CiboCapitalManagementError(
                    "Phase21 freeze must follow empirical validation"
                )
        if (
            self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase21 research freeze cannot grant operational authority"
            )

    def canonical_payload(self) -> dict[str, object]:
        validations = sorted(
            self.empirical_validations,
            key=lambda item: item.kind.value,
        )
        return {
            "schema": "qore.cibo.phase21.policy-freeze.v1",
            "candidate_id": self.candidate_id,
            "candidate_code_sha": self.candidate_code_sha,
            "candidate_parameter_sha256": self.candidate_parameter_sha256,
            "qualification": {
                "plan_id": self.qualification.plan_id,
                "plan_sha256": self.qualification.plan_sha256,
                "evidence_store_sha256": (
                    self.qualification.evidence_store_sha256
                ),
                "policy_store_sha256": (
                    self.qualification.policy_store_sha256
                ),
                "qualification_artifact_sha256": (
                    self.qualification.qualification_artifact_sha256
                ),
                "qualified_at": self.qualification.qualified_at.isoformat(),
            },
            "empirical_validations": [
                {
                    "kind": item.kind.value,
                    "evidence_class": item.evidence_class,
                    "artifact_sha256": item.artifact_sha256,
                    "observed_at": item.observed_at.isoformat(),
                }
                for item in validations
            ],
            "policy_surface": self.policy_surface.payload(),
            "frozen_at": self.frozen_at.isoformat(),
            "governance": {
                "demo_execution_authorized": False,
                "live_authorized": False,
                "real_capital_authorized": False,
                "merge_authorized": False,
            },
        }

    def manifest_sha256(self) -> str:
        raw = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


def build_phase21_policy_freeze(
    *,
    qualification: Phase21QualificationReceipt,
    empirical_validations: tuple[Phase21EmpiricalValidationReceipt, ...],
    policy_surface: Phase21PolicySurfaceDigests,
    frozen_at: datetime,
) -> Phase21PolicyFreezeManifest:
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    return Phase21PolicyFreezeManifest(
        candidate_id=candidate.candidate_id,
        candidate_code_sha=candidate.code_sha,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        qualification=qualification,
        empirical_validations=empirical_validations,
        policy_surface=policy_surface,
        frozen_at=frozen_at,
    )


def _require_sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Phase21 {name} must be sha256: plus 64 lowercase hex"
        )


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase21 {name} must be timezone-aware"
        )
