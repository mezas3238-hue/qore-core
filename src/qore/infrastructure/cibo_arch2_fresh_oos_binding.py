"""Cross-boundary Phase22 outcome/qualification binding for Architect-2.

Architect-2 is not allowed to execute or independently reopen the Phase22 V2
one-shot.  A terminal fresh-OOS decision therefore requires an Integrator
receipt that binds the durable consumption claim and exact outcome bundle to
the qualification stores/artifact consumed by the qualification report.

This module defines the fail-closed intake contract.  It does not read the
holdout, create a one-shot claim, rerun Phase22, or grant productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationReport,
    Phase22HoldoutQualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)

BINDING_ID = "CIBO_ARCH2_PHASE22_V2_OUTCOME_QUALIFICATION_BINDING_V1"
SOURCE_KIND = "INTEGRATOR_PHASE22_V2_OUTCOME_TO_QUALIFICATION_BINDING"


@dataclass(frozen=True, slots=True)
class Phase22OutcomeQualificationBindingReceipt:
    binding_id: str
    source_kind: str
    candidate_id: str
    execution_manifest_sha256: str
    claim_head_sha: str
    claim_run_id: int
    claim_run_attempt: int
    outcome_bundle_sha256: str
    holdout_evidence_store_sha256: str
    holdout_policy_store_sha256: str
    outcome_to_store_binding_sha256: str
    qualification_plan_sha256: str
    qualification_report_sha256: str
    qualification_artifact_sha256: str
    qualification_status: str
    lineage_valid: bool
    rerun_used: bool = False
    holdout_mining_used: bool = False
    outcome_aware_refit: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_id != BINDING_ID:
            raise CiboCapitalManagementError(
                "Fresh-OOS binding identity drift"
            )
        if self.source_kind != SOURCE_KIND:
            raise CiboCapitalManagementError(
                "Fresh-OOS binding source kind drift"
            )
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Fresh-OOS binding candidate identity drift"
            )
        for name in (
            "execution_manifest_sha256",
            "outcome_bundle_sha256",
            "holdout_evidence_store_sha256",
            "holdout_policy_store_sha256",
            "outcome_to_store_binding_sha256",
            "qualification_plan_sha256",
            "qualification_report_sha256",
            "qualification_artifact_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.qualification_plan_sha256 != (
            phase22_holdout_qualification_plan_sha256()
        ):
            raise CiboCapitalManagementError(
                "Fresh-OOS binding qualification plan drift"
            )
        if (
            not isinstance(self.claim_head_sha, str)
            or len(self.claim_head_sha) != 40
            or any(ch not in "0123456789abcdef" for ch in self.claim_head_sha)
        ):
            raise CiboCapitalManagementError(
                "Fresh-OOS binding claim HEAD invalid"
            )
        for name in ("claim_run_id", "claim_run_attempt"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Fresh-OOS binding {name} invalid"
                )
        statuses = {item.value for item in Phase22HoldoutQualificationStatus}
        if self.qualification_status not in statuses:
            raise CiboCapitalManagementError(
                "Fresh-OOS binding qualification status invalid"
            )
        for name in (
            "lineage_valid",
            "rerun_used",
            "holdout_mining_used",
            "outcome_aware_refit",
            "canonical_ledger_modified",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Fresh-OOS binding {name} must be bool"
                )
        if (
            self.rerun_used
            or self.holdout_mining_used
            or self.outcome_aware_refit
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Fresh-OOS binding governance contamination"
            )

    def fingerprint(self) -> str:
        payload = {
            field.name: _canonical(getattr(self, field.name))
            for field in fields(self)
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def phase22_report_fingerprint(
    report: Phase22HoldoutQualificationReport,
) -> str:
    if not isinstance(report, Phase22HoldoutQualificationReport):
        raise CiboCapitalManagementError(
            "Fresh-OOS report fingerprint requires canonical qualification"
        )
    raw = json.dumps(
        _canonical(report),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    if hasattr(value, "__dict__"):
        return {
            str(key): _canonical(item)
            for key, item in sorted(vars(value).items())
        }
    raise CiboCapitalManagementError(
        f"Fresh-OOS report contains unsupported value: {type(value).__name__}"
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Fresh-OOS binding {name} must be canonical SHA-256"
        )
