"""Exact Git-blob lineage for the next CIBO policy generation.

A single historical code_sha is insufficient to reproduce the full CE2I policy
surface because the candidate declaration, regime selector, advanced engines,
full-surface coordinator and allocator evolved in separate commits.  The next
Phase22 generation therefore freezes an exact ordered Git-blob bundle before
any new holdout source access.

This manifest is code lineage only. It grants no execution or source-read
authority and is not a certification claim.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

BUNDLE_ID = "CIBO_NEXT_POLICY_CODE_BUNDLE_LINEAGE_V1"
ASSEMBLED_FROM_COMMIT = "1f75e4f03e48ecdb7cb86e64339eabbe626f8035"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class PolicyCodeBlobBinding:
    path: str
    git_blob_sha: str

    def __post_init__(self) -> None:
        if not self.path.startswith("src/qore/infrastructure/"):
            raise CiboCapitalManagementError(
                "next policy bundle path outside infrastructure"
            )
        if _GIT_SHA_RE.fullmatch(self.git_blob_sha) is None:
            raise CiboCapitalManagementError(
                "next policy bundle Git blob SHA invalid"
            )


@dataclass(frozen=True, slots=True)
class NextPolicyCodeBundleLineage:
    bundle_id: str
    assembled_from_commit: str
    files: tuple[PolicyCodeBlobBinding, ...]
    frozen_before_next_holdout_source_access: bool
    legacy_single_code_sha_sufficient: bool = False
    v2_economic_outcomes_used_for_bundle_selection: bool = False
    source_outcomes_inspected: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.bundle_id != BUNDLE_ID:
            raise CiboCapitalManagementError(
                "next policy code bundle identity drift"
            )
        if _GIT_SHA_RE.fullmatch(self.assembled_from_commit) is None:
            raise CiboCapitalManagementError(
                "next policy bundle assembly commit invalid"
            )
        if not self.files:
            raise CiboCapitalManagementError(
                "next policy bundle files required"
            )
        paths = tuple(item.path for item in self.files)
        if len(paths) != len(set(paths)) or paths != tuple(sorted(paths)):
            raise CiboCapitalManagementError(
                "next policy bundle paths must be unique/sorted"
            )
        required = {
            "src/qore/infrastructure/cibo_account_capital_mission.py",
            "src/qore/infrastructure/cibo_ce2i_advanced_capital_tools.py",
            "src/qore/infrastructure/cibo_ce2i_full_surface.py",
            "src/qore/infrastructure/cibo_ce2i_phase20_mpc.py",
            "src/qore/infrastructure/cibo_ce2i_phase20_policy_candidate.py",
            "src/qore/infrastructure/cibo_ce2i_phase20_robust_allocator.py",
            "src/qore/infrastructure/cibo_ce2i_phase20_train_prior.py",
            "src/qore/infrastructure/cibo_ce2i_regime_selector.py",
            "src/qore/infrastructure/cibo_next_policy_advanced_scientific_eligibility.py",
        }
        if set(paths) != required:
            raise CiboCapitalManagementError(
                "next policy bundle exact file surface drift"
            )
        if not self.frozen_before_next_holdout_source_access:
            raise CiboCapitalManagementError(
                "next policy bundle must predate holdout source access"
            )
        if any(
            (
                self.legacy_single_code_sha_sufficient,
                self.v2_economic_outcomes_used_for_bundle_selection,
                self.source_outcomes_inspected,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "next policy bundle governance contamination"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.next-policy.code-bundle-lineage.v1",
            "bundle_id": self.bundle_id,
            "assembled_from_commit": self.assembled_from_commit,
            "files": [
                {
                    "path": item.path,
                    "git_blob_sha": item.git_blob_sha,
                }
                for item in self.files
            ],
            "legacy_single_code_sha_sufficient": False,
            "frozen_before_next_holdout_source_access": True,
            "v2_economic_outcomes_used_for_bundle_selection": False,
            "source_outcomes_inspected": False,
            "broker_mutation_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


NEXT_POLICY_CODE_BUNDLE_LINEAGE = NextPolicyCodeBundleLineage(
    bundle_id=BUNDLE_ID,
    assembled_from_commit=ASSEMBLED_FROM_COMMIT,
    files=tuple(
        PolicyCodeBlobBinding(path=path, git_blob_sha=blob)
        for path, blob in (
            (
                "src/qore/infrastructure/cibo_account_capital_mission.py",
                "42416fde2729daaa40e48806c98d56cd7b371f01",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_advanced_capital_tools.py",
                "224db3d0a53de036f0a5777cd33f434f3631b5d5",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_full_surface.py",
                "e68b97eee72f32dcacabbaf601d3c111b35c701e",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_phase20_mpc.py",
                "7fccf6620d58014e3e65a19f1e793da4ad3e2991",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_phase20_policy_candidate.py",
                "dd6a3c4fef61eeada24a2c7b0bf14a0446510321",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_phase20_robust_allocator.py",
                "aca720ff9bcf45a31bcfbbff6c38e1609e8be485",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_phase20_train_prior.py",
                "58d62b8bfded5cf46e0a90aad1f8f7cf43057a4a",
            ),
            (
                "src/qore/infrastructure/cibo_ce2i_regime_selector.py",
                "23d8c5a0bdcafefad7419d41620378e79c0d99ac",
            ),
            (
                "src/qore/infrastructure/cibo_next_policy_advanced_scientific_eligibility.py",
                "9b21cafdac8fccbcd4da48719d7dfc3ab31b7710",
            ),
        )
    ),
    frozen_before_next_holdout_source_access=True,
)
