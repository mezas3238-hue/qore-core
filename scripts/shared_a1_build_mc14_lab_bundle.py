#!/usr/bin/env python3
"""Build the sealed MC14 B04 Shared Lab dataset bundle.

This is an assembly tool only. It never evaluates MC14 outcomes. It verifies
the already-consumed source artifacts against the frozen A1 contract before
creating one content-addressable ZIP suitable for Shared Lab DatasetStore.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

IDENTITY = "QORE_SHARED_A1_MC14_SHARED_LAB_BUNDLE_BUILDER_001"
DEFAULT_CONTRACT = Path(
    "docs/shared/evidence/QORE_SHARED_A1_MC14_SHARED_LAB_DATASET_CONTRACT_001.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_zip(root: Path, artifact_id: int) -> Path:
    exact = root / f"{artifact_id}.zip"
    if exact.is_file():
        return exact
    matches = sorted(root.glob(f"*{artifact_id}*.zip"))
    if len(matches) != 1:
        raise ValueError(
            f"artifact {artifact_id}: expected exactly one ZIP under {root}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        name = PurePosixPath(info.filename)
        if (
            name.is_absolute()
            or ".." in name.parts
            or not name.parts
        ):
            raise ValueError(f"unsafe ZIP member: {info.filename!r}")
        if info.is_dir():
            continue
        members.append(info)
    return members


def _extract_verified_zip(archive_path: Path, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with zipfile.ZipFile(archive_path) as archive:
        for info in _safe_members(archive):
            relative = PurePosixPath(info.filename)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f"bundle assembly path collision: {target}")
            with archive.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            written.append(target)
    return written


def _tree_manifest(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_in_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return records


def _deterministic_zip(source_root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in sorted(item for item in source_root.rglob("*") if item.is_file()):
            relative = path.relative_to(source_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def _verify_artifact(path: Path, expected_sha256: str, artifact_id: int) -> None:
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(
            f"artifact {artifact_id}: SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual}"
        )


def build_bundle(
    *,
    contract_path: Path,
    artifact_dir: Path,
    staging_dir: Path,
    output: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    if contract.get("identity") != (
        "QORE_SHARED_A1_MC14_SHARED_LAB_DATASET_CONTRACT_001"
    ):
        raise ValueError("unexpected MC14 dataset contract identity")
    if staging_dir.exists():
        raise FileExistsError(
            f"staging directory must not already exist: {staging_dir}"
        )
    staging_dir.mkdir(parents=True)

    input_receipts: list[dict[str, object]] = []
    sources_root = staging_dir / "sources"
    family = "XAUUSD_DEFENSIVE_PROXY"
    family_contract = contract["source_artifacts"][family]
    shards = list(family_contract["shards"])
    if len(shards) != int(family_contract["required_shard_count"]):
        raise ValueError(f"{family}: frozen shard count mismatch")
    for ordinal, shard in enumerate(shards):
        artifact_id = int(shard["artifact_id"])
        archive = _artifact_zip(artifact_dir, artifact_id)
        _verify_artifact(archive, str(shard["sha256"]), artifact_id)
        shard_root = sources_root / family / f"shard_{ordinal:02d}"
        files = _extract_verified_zip(archive, shard_root)
        if not files:
            raise ValueError(f"artifact {artifact_id}: empty source ZIP")
        input_receipts.append(
            {
                "artifact_id": artifact_id,
                "family": family,
                "source_zip": archive.name,
                "sha256": str(shard["sha256"]),
                "extracted_file_count": len(files),
            }
        )

    target_contract = contract["r8_target"]
    target_id = int(target_contract["artifact_id"])
    target_archive = _artifact_zip(artifact_dir, target_id)
    _verify_artifact(
        target_archive,
        str(target_contract["artifact_zip_sha256"]),
        target_id,
    )
    target_raw = staging_dir / "_target_raw"
    target_files = _extract_verified_zip(target_archive, target_raw)
    expected_targets = dict(target_contract["extracted_sha256"])
    found_targets: dict[str, Path] = {}
    for path in target_files:
        digest = _sha256(path)
        for market, expected in expected_targets.items():
            if digest == expected:
                if market in found_targets:
                    raise ValueError(f"duplicate target hash match for {market}")
                found_targets[market] = path
    if set(found_targets) != set(expected_targets):
        missing = sorted(set(expected_targets) - set(found_targets))
        raise ValueError(f"R8 target artifact missing frozen targets: {missing}")

    targets_root = staging_dir / "targets"
    targets_root.mkdir()
    target_receipts: dict[str, dict[str, object]] = {}
    for market, source in sorted(found_targets.items()):
        destination = targets_root / f"{market}.json"
        shutil.copy2(source, destination)
        target_receipts[market] = {
            "path": destination.relative_to(staging_dir).as_posix(),
            "sha256": _sha256(destination),
            "size_in_bytes": destination.stat().st_size,
        }
    shutil.rmtree(target_raw)

    manifest: dict[str, Any] = {
        "identity": "QORE_SHARED_A1_MC14_SHARED_LAB_DATASET_BUNDLE_001",
        "builder_identity": IDENTITY,
        "contract_identity": contract["identity"],
        "dataset_id": contract["bundle_contract"]["dataset_id"],
        "dataset_version": contract["bundle_contract"]["dataset_version"],
        "b04_run_id": contract["scientific_contract"]["b04_run_id"],
        "b04_git_sha": contract["scientific_contract"]["b04_git_sha"],
        "source_artifacts": input_receipts,
        "excluded_source_families": {
            "US2000_BREADTH_PROXY": {
                "status": "INSUFFICIENT_DO_NOT_INFER",
                "target_evaluation_executed": False,
                "reason": "FROZEN_SOURCE_PREFLIGHT_INCOMPLETE",
            }
        },
        "target_artifact": {
            "artifact_id": target_id,
            "sha256": target_contract["artifact_zip_sha256"],
        },
        "targets": target_receipts,
        "scientific_firewall": {
            "target_blind_source_features": True,
            "gate_retuning": False,
            "missing_data_imputation": False,
            "r6_r5_read": False,
            "protected_final_holdout_opened": False,
        },
    }
    manifest["content"] = _tree_manifest(staging_dir)
    manifest_path = staging_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )

    _deterministic_zip(staging_dir, output)
    receipt = {
        "identity": IDENTITY,
        "status": "BUNDLE_MATERIALIZED_AND_INPUT_HASHES_VERIFIED",
        "bundle_path": str(output),
        "bundle_sha256": _sha256(output),
        "bundle_size_in_bytes": output.stat().st_size,
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "source_artifact_count": len(input_receipts),
        "target_market_count": len(target_receipts),
        "outcome_evaluation_executed": False,
        "protected_final_holdout_opened": False,
    }
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    receipt = build_bundle(
        contract_path=args.contract,
        artifact_dir=args.artifact_dir,
        staging_dir=args.staging_dir,
        output=args.output,
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
