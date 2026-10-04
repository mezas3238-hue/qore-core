from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_b_pre_freeze_replay import (
    SharedBPreFreezeReplayError,
    replay_pre_freeze_evidence,
)


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _zip(path: Path, files: dict[str, bytes]) -> None:
    sums = "".join(
        f"{hashlib.sha256(raw).hexdigest()}  ./{name}\n"
        for name, raw in sorted(files.items())
    ).encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
        archive.writestr("SHA256SUMS", sums)


def _artifacts(tmp_path: Path) -> tuple[Path, Path]:
    b16 = {
        "identity": "SHARED_B_SENSOR_QUALIFICATION_FRONTIER_001",
        "sensor_count": 177,
        "admitted_count": 0,
        "causal_qualification_complete_count": 0,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    b16["frontier_fingerprint_sha256"] = _canonical_hash(b16)

    manifest = {
        "identity": "SHARED_B_GLOBAL_WORLD_PERCEPTION_PROVENANCE_MANIFEST_001",
        "evidence_pointer_count": 42,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    manifest["manifest_fingerprint_sha256"] = _canonical_hash(manifest)

    coverage = {
        "identity": "SHARED_INTEGRATOR_B_PROVENANCE_COVERAGE_002",
        "covered_count": 22,
        "missing_ids": ["B-22", "B-24"],
        "missing_terminal_ids": [],
        "missing_external_blocked_ids": [],
        "coverage_complete": False,
    }

    b16_zip = tmp_path / "b16.zip"
    b21_zip = tmp_path / "b21.zip"
    _zip(
        b16_zip,
        {
            "shared-b-sensor-qualification-frontier.json": (
                json.dumps(b16, sort_keys=True).encode()
            )
        },
    )
    _zip(
        b21_zip,
        {
            "shared-b-provenance-manifest.json": (
                json.dumps(manifest, sort_keys=True).encode()
            ),
            "shared-b-provenance-coverage.json": (
                json.dumps(coverage, sort_keys=True).encode()
            ),
        },
    )
    return b16_zip, b21_zip


def test_replay_is_deterministic_and_preserves_pre_freeze_topology(
    tmp_path: Path,
) -> None:
    b16_zip, b21_zip = _artifacts(tmp_path)
    receipt = replay_pre_freeze_evidence(
        b16_zip=b16_zip,
        b21_zip=b21_zip,
    )
    assert receipt.deterministic_replay_verified is True
    assert receipt.pre_freeze_provenance_complete is True
    assert receipt.provenance_covered_count == 22
    assert receipt.provenance_missing_ids == ("B-22", "B-24")
    assert len(receipt.replay_fingerprint_sha256) == 64
    assert receipt.fresh_holdout_opened is False
    assert receipt.productive_authority is False


def test_replay_rejects_tampered_bundle(tmp_path: Path) -> None:
    b16_zip, b21_zip = _artifacts(tmp_path)
    with zipfile.ZipFile(b16_zip, "a") as archive:
        archive.writestr(
            "shared-b-sensor-qualification-frontier.json",
            b'{"tampered":true}',
        )
    with pytest.raises(
        SharedBPreFreezeReplayError,
        match="artifact digest mismatch",
    ):
        replay_pre_freeze_evidence(
            b16_zip=b16_zip,
            b21_zip=b21_zip,
        )


def test_replay_rejects_future_downstream_provenance_shape(
    tmp_path: Path,
) -> None:
    b16_zip, b21_zip = _artifacts(tmp_path)
    with zipfile.ZipFile(b21_zip, "r") as archive:
        manifest = archive.read("shared-b-provenance-manifest.json")
    bad_coverage = {
        "identity": "SHARED_INTEGRATOR_B_PROVENANCE_COVERAGE_002",
        "covered_count": 23,
        "missing_ids": ["B-24"],
        "missing_terminal_ids": [],
        "missing_external_blocked_ids": [],
        "coverage_complete": False,
    }
    _zip(
        b21_zip,
        {
            "shared-b-provenance-manifest.json": manifest,
            "shared-b-provenance-coverage.json": (
                json.dumps(bad_coverage, sort_keys=True).encode()
            ),
        },
    )
    with pytest.raises(
        SharedBPreFreezeReplayError,
        match="expected exact 22/24 provenance",
    ):
        replay_pre_freeze_evidence(
            b16_zip=b16_zip,
            b21_zip=b21_zip,
        )
