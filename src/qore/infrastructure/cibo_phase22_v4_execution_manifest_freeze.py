"""Fail-closed loader for the committed Phase22 V4 execution-manifest freeze."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_execution_manifest import (
    build_phase22_v4_execution_manifest,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID

SCHEMA = "qore.cibo.phase22.v4-execution-manifest-freeze.v1"
FREEZE_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V4-EXECUTION-MANIFEST.json"
)
SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def load_phase22_v4_execution_manifest_freeze(
    path: Path = Path(FREEZE_RELATIVE_PATH),
) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise CiboCapitalManagementError("V4 execution freeze schema drift")
    if _SHA1_RE.fullmatch(str(raw.get("source_head_sha", ""))) is None:
        raise CiboCapitalManagementError("V4 execution freeze source HEAD invalid")
    if raw.get("target_branch") != SOVEREIGN_BRANCH:
        raise CiboCapitalManagementError("V4 execution freeze branch drift")
    if raw.get("candidate_id") != V4_CANDIDATE_ID:
        raise CiboCapitalManagementError("V4 execution freeze candidate drift")

    manifest = build_phase22_v4_execution_manifest()
    if raw.get("execution_manifest_sha256") != manifest.fingerprint():
        raise CiboCapitalManagementError("V4 execution freeze manifest digest drift")
    if raw.get("execution_manifest") != manifest.payload():
        raise CiboCapitalManagementError("V4 execution freeze manifest payload drift")

    required_true = (
        "exact_seven_trader_bindings",
        "source_receipt_bound",
        "policy_frozen",
        "advanced_scientific_eligibility_frozen",
        "provider_calibration_bound",
        "provider_numeric_freeze_bound",
        "parity_manifest_bound",
        "vt31_six_field_abi_bound",
        "v4_store_namespace_required",
    )
    required_false = (
        "v2_store_reuse_authorized",
        "v3_store_reuse_authorized",
        "fresh_outcomes_executed",
        "owner_authorization_present",
        "broker_mutation_authorized",
        "live_authorized",
        "real_capital_authorized",
        "production_authorized",
        "merge_authorized",
        "productive_authority",
    )
    if any(raw.get(name) is not True for name in required_true):
        raise CiboCapitalManagementError("V4 execution freeze readiness flag drift")
    if any(raw.get(name) is not False for name in required_false):
        raise CiboCapitalManagementError("V4 execution freeze authority contamination")

    digest = str(raw.get("freeze_sha256", ""))
    if _SHA256_RE.fullmatch(digest) is None:
        raise CiboCapitalManagementError("V4 execution freeze digest invalid")
    material = dict(raw)
    material.pop("freeze_sha256", None)
    if digest != _canonical_sha(material):
        raise CiboCapitalManagementError("V4 execution freeze digest mismatch")
    return raw
