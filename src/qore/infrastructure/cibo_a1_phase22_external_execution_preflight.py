"""Pinned external Phase22 V2 execution-preflight receipt consumed by A1.

Evidence source:
- Integrator branch HEAD 049c7e8dfba2b0333df6ac23e91c168df1290bcd
- GitHub Actions artifact 11202555722
- artifact archive digest sha256:3f9bd77c11b6203699b49ddee54c968e03a4bb54afa20be94330b70e235eb579

The artifact contains the frozen execution manifest and one-shot preflight. It
authorizes emission of the first fresh outcome but explicitly records that no
fresh outcome has yet been executed. This receipt therefore anchors A1
pre-outcome identity only; it cannot be used as scientific-outcome evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from qore.infrastructure.cibo_a1_phase22_canonical_manifest_bridge import (
    A1Phase22ExecutionManifestIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)

RECEIPT_ID = "CIBO_A1_PHASE22_EXTERNAL_EXECUTION_PREFLIGHT_RECEIPT_V1"
INTEGRATOR_HEAD_SHA = "049c7e8dfba2b0333df6ac23e91c168df1290bcd"
GITHUB_ARTIFACT_ID = 11202555722
GITHUB_ARTIFACT_DIGEST = (
    "sha256:3f9bd77c11b6203699b49ddee54c968e03a4bb54afa20be94330b70e235eb579"
)
EXECUTION_MANIFEST_SHA256 = (
    "sha256:6c54051112f2ce190bf3ed20c3e5d1ee0b4d7a7b4cffb0d2b01d590500000a54"
)
CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
CANDIDATE_CODE_SHA = "edf96722fd0505711aa88bc1d15296b09e6dba6f"
CANDIDATE_PARAMETER_SHA256 = (
    "sha256:1bfab7bd6ca86201ca6010d5ec72448d318ee6e38d051eb0d126bf76ddec85fb"
)
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1Phase22ExternalExecutionPreflightReceipt:
    receipt_id: str
    integrator_head_sha: str
    github_artifact_id: int
    github_artifact_digest: str
    execution_manifest_sha256: str
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    trader_ids: tuple[str, ...]
    preflight_status: str
    authorized_to_emit_first_fresh_outcome: bool
    execution_claimed: bool
    fresh_outcomes_already_emitted: bool
    execution_manifest_fresh_outcomes_executed: bool
    productive_authority: bool = False
    scientific_outcome_evidence: bool = False

    def __post_init__(self) -> None:
        if self.receipt_id != RECEIPT_ID:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight receipt identity drift"
            )
        if _GIT_SHA_RE.fullmatch(self.integrator_head_sha) is None:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight Integrator HEAD invalid"
            )
        if (
            not isinstance(self.github_artifact_id, int)
            or isinstance(self.github_artifact_id, bool)
            or self.github_artifact_id <= 0
        ):
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight artifact id invalid"
            )
        for name in (
            "github_artifact_digest",
            "execution_manifest_sha256",
            "candidate_parameter_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"A1 external Phase22 preflight {name} invalid"
                )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight candidate required"
            )
        if _GIT_SHA_RE.fullmatch(self.candidate_code_sha) is None:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight candidate code SHA invalid"
            )
        expected_traders = tuple(
            item.value for item in PHASE19_REQUIRED_TRADERS
        )
        if self.trader_ids != expected_traders:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight requires canonical ordered 7/7"
            )
        if self.preflight_status != "READY":
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight must be READY"
            )
        if not self.authorized_to_emit_first_fresh_outcome:
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight lacks first-outcome authorization"
            )
        prohibited = (
            self.execution_claimed,
            self.fresh_outcomes_already_emitted,
            self.execution_manifest_fresh_outcomes_executed,
            self.productive_authority,
            self.scientific_outcome_evidence,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "A1 external Phase22 preflight cannot claim executed/outcome authority"
            )

    def execution_identity(self) -> A1Phase22ExecutionManifestIdentity:
        return A1Phase22ExecutionManifestIdentity(
            execution_manifest_sha256=self.execution_manifest_sha256,
            candidate_id=self.candidate_id,
            candidate_code_sha=self.candidate_code_sha,
            candidate_parameter_sha256=self.candidate_parameter_sha256,
            trader_ids=self.trader_ids,
            fresh_outcomes_executed=False,
            productive_authority=False,
        )


def frozen_a1_phase22_external_execution_preflight(
) -> A1Phase22ExternalExecutionPreflightReceipt:
    """Return the exact verified pre-outcome receipt from Integrator HEAD."""

    return A1Phase22ExternalExecutionPreflightReceipt(
        receipt_id=RECEIPT_ID,
        integrator_head_sha=INTEGRATOR_HEAD_SHA,
        github_artifact_id=GITHUB_ARTIFACT_ID,
        github_artifact_digest=GITHUB_ARTIFACT_DIGEST,
        execution_manifest_sha256=EXECUTION_MANIFEST_SHA256,
        candidate_id=CANDIDATE_ID,
        candidate_code_sha=CANDIDATE_CODE_SHA,
        candidate_parameter_sha256=CANDIDATE_PARAMETER_SHA256,
        trader_ids=tuple(item.value for item in PHASE19_REQUIRED_TRADERS),
        preflight_status="READY",
        authorized_to_emit_first_fresh_outcome=True,
        execution_claimed=False,
        fresh_outcomes_already_emitted=False,
        execution_manifest_fresh_outcomes_executed=False,
    )
