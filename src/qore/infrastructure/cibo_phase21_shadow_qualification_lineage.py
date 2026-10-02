"""Immutable Phase21 shadow-freeze lineage accepted by Phase22 V2.

This receipt does not relabel the owner-authorized historical shadow lane as
FORWARD_EMPIRICAL. It binds the exact Phase20 shadow, Phase21 screen and Phase21
policy-freeze artifacts that were actually produced and keeps their evidence
class explicit.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_shadow_certification_receipts import (
    PHASE20_SHADOW_ARTIFACT_DIGEST,
    PHASE20_SHADOW_ARTIFACT_ID,
    PHASE20_SHADOW_RUN_ID,
    PHASE21_FREEZE_ARTIFACT_DIGEST,
    PHASE21_FREEZE_ARTIFACT_ID,
    PHASE21_FREEZE_HEAD,
    PHASE21_FREEZE_RUN_ID,
    PHASE21_SCREEN_ARTIFACT_DIGEST,
    PHASE21_SCREEN_ARTIFACT_ID,
    PHASE21_SCREEN_RUN_ID,
)

EVIDENCE_CLASS = "OWNER_AUTHORIZED_HISTORICAL_SHADOW"
PHASE20_SHADOW_FILE_SHA256 = (
    "sha256:c9d9bd745b491d53a526b7293fde20b6d86564e49480b4714618049434770f72"
)
PHASE21_SCREEN_FILE_SHA256 = (
    "sha256:693ca7434fa59c9ad75b6f7876ba0a2f039d513bc99265c3f7e3abee67fa005d"
)
PHASE21_FREEZE_FILE_SHA256 = (
    "sha256:cc95619fee25eecf1420adfebfa384a252d74d2f9e683a46086f2bb62ccea920"
)
PHASE21_SHADOW_FREEZE_FINGERPRINT = (
    "sha256:7e5889e49ae89515091af0a611a054ca4ba056874f945573a670c45dde59bb90"
)
PHASE21_SHADOW_SOURCE_HEAD = "072b6b7494eed0ed0a2d881b6526bdeb779e28f7"
PHASE21_SHADOW_FROZEN_AT = datetime.fromisoformat(
    "2026-10-01T13:10:21.797074+00:00"
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase21ShadowQualificationLineageReceipt:
    evidence_class: str
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    frozen_at: datetime
    phase20_shadow_run_id: int
    phase20_shadow_artifact_id: int
    phase20_shadow_artifact_digest: str
    phase20_shadow_file_sha256: str
    phase21_screen_run_id: int
    phase21_screen_artifact_id: int
    phase21_screen_artifact_digest: str
    phase21_screen_file_sha256: str
    phase21_screen_head_sha: str
    phase21_freeze_run_id: int
    phase21_freeze_artifact_id: int
    phase21_freeze_artifact_digest: str
    phase21_freeze_file_sha256: str
    phase21_freeze_head_sha: str
    phase21_shadow_freeze_fingerprint: str
    forward_empirical_claimed: bool
    provider_economics_claimed: bool
    final_holdout_2017h1_read: bool
    policy_retuned_after_outcomes: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        if self.evidence_class != EVIDENCE_CLASS:
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage evidence class drift"
            )
        if (
            self.candidate_id != candidate.candidate_id
            or self.candidate_code_sha != candidate.code_sha
            or self.candidate_parameter_sha256 != candidate.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage candidate drift"
            )
        if self.frozen_at != PHASE21_SHADOW_FROZEN_AT:
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage frozen_at drift"
            )
        expected_ids = (
            (self.phase20_shadow_run_id, PHASE20_SHADOW_RUN_ID),
            (self.phase20_shadow_artifact_id, PHASE20_SHADOW_ARTIFACT_ID),
            (self.phase21_screen_run_id, PHASE21_SCREEN_RUN_ID),
            (self.phase21_screen_artifact_id, PHASE21_SCREEN_ARTIFACT_ID),
            (self.phase21_freeze_run_id, PHASE21_FREEZE_RUN_ID),
            (self.phase21_freeze_artifact_id, PHASE21_FREEZE_ARTIFACT_ID),
        )
        if any(actual != expected for actual, expected in expected_ids):
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage run/artifact identity drift"
            )
        expected_digests = (
            (self.phase20_shadow_artifact_digest, PHASE20_SHADOW_ARTIFACT_DIGEST),
            (self.phase20_shadow_file_sha256, PHASE20_SHADOW_FILE_SHA256),
            (self.phase21_screen_artifact_digest, PHASE21_SCREEN_ARTIFACT_DIGEST),
            (self.phase21_screen_file_sha256, PHASE21_SCREEN_FILE_SHA256),
            (self.phase21_freeze_artifact_digest, PHASE21_FREEZE_ARTIFACT_DIGEST),
            (self.phase21_freeze_file_sha256, PHASE21_FREEZE_FILE_SHA256),
            (
                self.phase21_shadow_freeze_fingerprint,
                PHASE21_SHADOW_FREEZE_FINGERPRINT,
            ),
        )
        for actual, expected in expected_digests:
            if actual != expected or _SHA256_RE.fullmatch(actual) is None:
                raise CiboCapitalManagementError(
                    "Phase21 shadow lineage digest drift"
                )
        if (
            self.phase21_screen_head_sha != PHASE21_SHADOW_SOURCE_HEAD
            or self.phase21_freeze_head_sha != PHASE21_FREEZE_HEAD
            or _SHA1_RE.fullmatch(self.phase21_screen_head_sha) is None
            or _SHA1_RE.fullmatch(self.phase21_freeze_head_sha) is None
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage Git SHA drift"
            )
        if (
            self.forward_empirical_claimed
            or self.provider_economics_claimed
            or self.final_holdout_2017h1_read
            or self.policy_retuned_after_outcomes
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow lineage governance contamination"
            )

    @property
    def protected_source_digests(self) -> tuple[str, ...]:
        return (
            self.phase20_shadow_artifact_digest,
            self.phase20_shadow_file_sha256,
            self.phase21_screen_artifact_digest,
            self.phase21_screen_file_sha256,
            self.phase21_freeze_artifact_digest,
            self.phase21_freeze_file_sha256,
            self.phase21_shadow_freeze_fingerprint,
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["frozen_at"] = self.frozen_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT = (
    Phase21ShadowQualificationLineageReceipt(
        evidence_class=EVIDENCE_CLASS,
        candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        candidate_code_sha=FROZEN_PHASE20_POLICY_CANDIDATE.code_sha,
        candidate_parameter_sha256=(
            FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
        ),
        frozen_at=PHASE21_SHADOW_FROZEN_AT,
        phase20_shadow_run_id=PHASE20_SHADOW_RUN_ID,
        phase20_shadow_artifact_id=PHASE20_SHADOW_ARTIFACT_ID,
        phase20_shadow_artifact_digest=PHASE20_SHADOW_ARTIFACT_DIGEST,
        phase20_shadow_file_sha256=PHASE20_SHADOW_FILE_SHA256,
        phase21_screen_run_id=PHASE21_SCREEN_RUN_ID,
        phase21_screen_artifact_id=PHASE21_SCREEN_ARTIFACT_ID,
        phase21_screen_artifact_digest=PHASE21_SCREEN_ARTIFACT_DIGEST,
        phase21_screen_file_sha256=PHASE21_SCREEN_FILE_SHA256,
        phase21_screen_head_sha=PHASE21_SHADOW_SOURCE_HEAD,
        phase21_freeze_run_id=PHASE21_FREEZE_RUN_ID,
        phase21_freeze_artifact_id=PHASE21_FREEZE_ARTIFACT_ID,
        phase21_freeze_artifact_digest=PHASE21_FREEZE_ARTIFACT_DIGEST,
        phase21_freeze_file_sha256=PHASE21_FREEZE_FILE_SHA256,
        phase21_freeze_head_sha=PHASE21_FREEZE_HEAD,
        phase21_shadow_freeze_fingerprint=PHASE21_SHADOW_FREEZE_FINGERPRINT,
        forward_empirical_claimed=False,
        provider_economics_claimed=False,
        final_holdout_2017h1_read=False,
        policy_retuned_after_outcomes=False,
        productive_authority=False,
    )
)
