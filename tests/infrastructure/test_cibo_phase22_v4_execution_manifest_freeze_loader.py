from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_execution_manifest_freeze import (
    load_phase22_v4_execution_manifest_freeze,
)
from scripts.cibo_phase22_v4_materialize_execution_manifest import (
    build_freeze_payload,
)


def test_v4_execution_manifest_freeze_loader_roundtrip(tmp_path: Path) -> None:
    payload = build_freeze_payload(source_head_sha="a" * 40)
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_phase22_v4_execution_manifest_freeze(path)

    assert loaded["source_head_sha"] == "a" * 40
    assert loaded["fresh_outcomes_executed"] is False
    assert loaded["owner_authorization_present"] is False


def test_v4_execution_manifest_freeze_loader_rejects_authority(
    tmp_path: Path,
) -> None:
    payload = build_freeze_payload(source_head_sha="a" * 40)
    payload["live_authorized"] = True
    material = dict(payload)
    material.pop("freeze_sha256", None)
    from scripts.cibo_phase22_v4_materialize_execution_manifest import (
        canonical_sha256,
    )
    payload["freeze_sha256"] = canonical_sha256(material)
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CiboCapitalManagementError, match="authority contamination"):
        load_phase22_v4_execution_manifest_freeze(path)
