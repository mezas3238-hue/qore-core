from __future__ import annotations

import hashlib
from pathlib import Path

from qore.infrastructure.cibo_next_policy_code_bundle_lineage import (
    ASSEMBLED_FROM_COMMIT,
    NEXT_POLICY_CODE_BUNDLE_LINEAGE,
)


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode()
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def test_next_policy_bundle_binds_exact_current_git_blobs() -> None:
    bundle = NEXT_POLICY_CODE_BUNDLE_LINEAGE

    assert bundle.assembled_from_commit == ASSEMBLED_FROM_COMMIT
    assert bundle.legacy_single_code_sha_sufficient is False
    assert bundle.v2_economic_outcomes_used_for_bundle_selection is False
    assert bundle.source_outcomes_inspected is False
    assert bundle.fingerprint().startswith("sha256:")

    for item in bundle.files:
        assert _git_blob_sha(Path(item.path)) == item.git_blob_sha


def test_next_policy_bundle_grants_no_productive_authority() -> None:
    bundle = NEXT_POLICY_CODE_BUNDLE_LINEAGE

    assert bundle.broker_mutation_authorized is False
    assert bundle.live_authorized is False
    assert bundle.real_capital_authorized is False
    assert bundle.production_authorized is False
