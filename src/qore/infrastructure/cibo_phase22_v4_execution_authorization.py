"""Explicit Owner authorization contract for Phase22 V4.

Defining this contract does not authorize execution. A canonical authorization
receipt must be committed later from an exact GREEN parent HEAD.
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
from qore.infrastructure.cibo_phase22_v4_execution_manifest import (
    build_phase22_v4_execution_manifest,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID

AUTHORIZATION_SCHEMA = "qore.cibo.phase22.v4-execution-authorization.v1"
AUTHORIZATION_ID = "CIBO_PHASE22_V4_ONE_SHOT_OWNER_AUTHORIZATION_V1"
AUTHORIZATION_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V4-EXECUTION-AUTHORIZATION.json"
)
SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22V4ExecutionAuthorization:
    authorization_id: str
    owner_authorization_id: str
    candidate_id: str
    authorized_parent_head_sha: str
    target_branch: str
    execution_manifest_sha256: str
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
            raise CiboCapitalManagementError("V4 authorization identity drift")
        if (
            not self.owner_authorization_id
            or not self.owner_authorization_id.startswith("OWNER_")
        ):
            raise CiboCapitalManagementError(
                "V4 requires explicit Owner authorization identity"
            )
        if self.candidate_id != V4_CANDIDATE_ID:
            raise CiboCapitalManagementError("V4 authorization candidate drift")
        if _SHA1_RE.fullmatch(self.authorized_parent_head_sha) is None:
            raise CiboCapitalManagementError("V4 authorization parent invalid")
        if self.target_branch != SOVEREIGN_BRANCH:
            raise CiboCapitalManagementError("V4 authorization branch drift")
        if _SHA256_RE.fullmatch(self.execution_manifest_sha256) is None:
            raise CiboCapitalManagementError("V4 manifest digest invalid")
        if (
            self.execution_manifest_sha256
            != build_phase22_v4_execution_manifest().fingerprint()
        ):
            raise CiboCapitalManagementError(
                "V4 authorization manifest drift"
            )
        if not self.fresh_holdout_execution_authorized or not self.one_shot_only:
            raise CiboCapitalManagementError(
                "V4 authorization must be explicit one-shot"
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
                "V4 authorization governance contamination"
            )

    def payload(self) -> dict[str, object]:
        return {"schema": AUTHORIZATION_SCHEMA, **asdict(self)}

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase22_v4_execution_authorization(
    *,
    owner_authorization_id: str,
    authorized_parent_head_sha: str,
) -> Phase22V4ExecutionAuthorization:
    manifest = build_phase22_v4_execution_manifest()
    return Phase22V4ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        owner_authorization_id=owner_authorization_id,
        candidate_id=V4_CANDIDATE_ID,
        authorized_parent_head_sha=authorized_parent_head_sha,
        target_branch=SOVEREIGN_BRANCH,
        execution_manifest_sha256=manifest.fingerprint(),
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


def load_phase22_v4_execution_authorization(
    path: Path = Path(AUTHORIZATION_RELATIVE_PATH),
) -> Phase22V4ExecutionAuthorization:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != AUTHORIZATION_SCHEMA:
        raise CiboCapitalManagementError("V4 authorization schema drift")
    fields = dict(raw)
    fields.pop("schema", None)
    return Phase22V4ExecutionAuthorization(**fields)
