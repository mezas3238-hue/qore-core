"""Integrity helpers for CIBO single-account Maximum Capability manifests.

The manifest digest covers the complete canonical payload except the digest field
itself. Any enrichment that changes causal predecision content must therefore
produce a new manifest_sha256 while retaining its parent digest in the
enrichment receipt.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def canonical_single_account_manifest_sha256(
    manifest: Mapping[str, Any],
) -> str:
    """Return the canonical digest for the manifest's current content."""

    if not isinstance(manifest, Mapping):
        raise CiboCapitalManagementError(
            "single-account manifest must be a mapping"
        )
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    raw = json.dumps(
        core,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_single_account_manifest_sha256(
    manifest: Mapping[str, Any],
) -> str:
    """Fail closed when a manifest digest does not match its payload."""

    claimed = manifest.get("manifest_sha256")
    if (
        not isinstance(claimed, str)
        or not claimed.startswith("sha256:")
        or len(claimed) != 71
    ):
        raise CiboCapitalManagementError(
            "single-account manifest digest is missing or invalid"
        )
    expected = canonical_single_account_manifest_sha256(manifest)
    if claimed != expected:
        raise CiboCapitalManagementError(
            "single-account manifest digest/content mismatch"
        )
    return claimed


def reseal_single_account_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a copy sealed to its current canonical content."""

    result = dict(manifest)
    result.pop("manifest_sha256", None)
    result["manifest_sha256"] = canonical_single_account_manifest_sha256(
        result
    )
    return result
