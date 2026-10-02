"""Explicit authorization contract for the Phase22 V3 one-shot.

This module does not create an authorization. It defines the only admissible
shape for an Owner authorization after all V3 pre-outcome evidence is frozen.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

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
    NEXT_CANDIDATE_ID,
)
from qore.infrastructure.cibo_phase22_v3_source_receipt import (
    phase22_v3_source_receipt_sha256,
)

AUTHORIZATION_SCHEMA = "qore.cibo.phase22.v3-execution-authorization.v1"
AUTHORIZATION_ID = "CIBO_PHASE22_V3_ONE_SHOT_OWNER_AUTHORIZATION_V1"
AUTHORIZATION_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V3-EXECUTION-AUTHORIZATION.json"
)
SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22V3ExecutionAuthorization:
    authorization_id: str
    owner_authorization_id: str
    candidate_id: str
    authorized_parent_head_sha: str
    target_branch: str
    source_receipt_sha256: str
    policy_bundle_sha256: str
    advanced_scientific_eligibility_sha256: str
    fresh_holdout_execution_authorized: bool
    one_shot_only: bool
    second_execution_authorized: bool
    broker_mutation_authorized: bool
    live_authorized: bool
    real_capital_authorized: bool
    production_authorized: bool
    merge_authorized: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        if self.authorization_id != AUTHORIZATION_ID:
            raise CiboCapitalManagementError(
                "V3 execution authorization identity drift"
            )
        if (
            not self.owner_authorization_id
            or not self.owner_authorization_id.startswith("OWNER_")
        ):
            raise CiboCapitalManagementError(
                "V3 execution requires explicit Owner authorization identity"
            )
        if self.candidate_id != NEXT_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "V3 execution authorization candidate drift"
            )
        if _GIT_SHA_RE.fullmatch(self.authorized_parent_head_sha) is None:
            raise CiboCapitalManagementError(
                "V3 execution authorization parent SHA invalid"
            )
        if self.target_branch != SOVEREIGN_BRANCH:
            raise CiboCapitalManagementError(
                "V3 execution authorization branch drift"
            )
        for name in (
            "source_receipt_sha256",
            "policy_bundle_sha256",
            "advanced_scientific_eligibility_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V3 execution authorization {name} invalid"
                )
        if self.source_receipt_sha256 != phase22_v3_source_receipt_sha256():
            raise CiboCapitalManagementError(
                "V3 execution authorization source receipt drift"
            )
        if self.policy_bundle_sha256 != (
            NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V3 execution authorization policy bundle drift"
            )
        if self.advanced_scientific_eligibility_sha256 != (
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V3 execution authorization eligibility freeze drift"
            )
        if (
            not self.fresh_holdout_execution_authorized
            or not self.one_shot_only
        ):
            raise CiboCapitalManagementError(
                "V3 execution authorization must be explicit and one-shot"
            )
        if any(
            (
                self.second_execution_authorized,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
                self.merge_authorized,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "V3 execution authorization governance contamination"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": AUTHORIZATION_SCHEMA,
            **asdict(self),
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase22_v3_execution_authorization(
    *,
    owner_authorization_id: str,
    authorized_parent_head_sha: str,
) -> Phase22V3ExecutionAuthorization:
    return Phase22V3ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        owner_authorization_id=owner_authorization_id,
        candidate_id=NEXT_CANDIDATE_ID,
        authorized_parent_head_sha=authorized_parent_head_sha,
        target_branch=SOVEREIGN_BRANCH,
        source_receipt_sha256=phase22_v3_source_receipt_sha256(),
        policy_bundle_sha256=NEXT_POLICY_CODE_BUNDLE_LINEAGE.fingerprint(),
        advanced_scientific_eligibility_sha256=(
            NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY.fingerprint()
        ),
        fresh_holdout_execution_authorized=True,
        one_shot_only=True,
        second_execution_authorized=False,
        broker_mutation_authorized=False,
        live_authorized=False,
        real_capital_authorized=False,
        production_authorized=False,
        merge_authorized=False,
        productive_authority=False,
    )


def load_phase22_v3_execution_authorization(
    path: Path = Path(AUTHORIZATION_RELATIVE_PATH),
) -> Phase22V3ExecutionAuthorization:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != AUTHORIZATION_SCHEMA:
        raise CiboCapitalManagementError(
            "V3 execution authorization schema drift"
        )
    fields = dict(raw)
    fields.pop("schema", None)
    return Phase22V3ExecutionAuthorization(**fields)
