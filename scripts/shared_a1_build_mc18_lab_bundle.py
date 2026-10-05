#!/usr/bin/env python3
"""Build the sealed consumed-development MC18 Shared Lab dataset bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

IDENTITY = "QORE_SHARED_A1_MC18_SHARED_LAB_BUNDLE_BUILDER_001"
DEFAULT_CONTRACT = Path(
    "docs/shared/evidence/QORE_SHARED_A1_MC18_SHARED_LAB_DATASET_CONTRACT_001.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = PurePosixPath(info.filename)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not relative.parts
            ):
                raise ValueError(f"unsafe ZIP member: {info.filename!r}")
            if info.is_dir():
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f"artifact path collision: {relative}")
            with archive.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)


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


def build_bundle(
    *,
    contract_path: Path,
    r6_zip: Path,
    r5_zip: Path,
    staging_dir: Path,
    output: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    if contract.get("identity") != (
        "QORE_SHARED_A1_MC18_SHARED_LAB_DATASET_CONTRACT_001"
    ):
        raise ValueError("unexpected MC18 dataset contract identity")
    if staging_dir.exists():
        raise FileExistsError(
            f"staging directory must not already exist: {staging_dir}"
        )
    staging_dir.mkdir(parents=True)

    source = contract["source_lineage"]
    inputs = {
        "r6": (
            r6_zip,
            source["R6_CONSUMED_ONLY"],
        ),
        "r5": (
            r5_zip,
            source["R5_CONSUMED_ONLY"],
        ),
    }
    receipts: dict[str, dict[str, object]] = {}
    for partition, (archive_path, frozen) in inputs.items():
        actual_zip_hash = _sha256(archive_path)
        expected_zip_hash = str(frozen["artifact_zip_sha256"])
        if actual_zip_hash != expected_zip_hash:
            raise ValueError(
                f"{partition}: artifact ZIP SHA-256 mismatch: "
                f"expected {expected_zip_hash}, got {actual_zip_hash}"
            )
        extracted = staging_dir / f"_{partition}_raw"
        _safe_extract(archive_path, extracted)
        copied: dict[str, dict[str, object]] = {}
        for market, expected_hash in dict(frozen["evidence"]).items():
            source_path = extracted / "fresh" / market / "market-evidence.json"
            if not source_path.is_file():
                raise ValueError(f"{partition}/{market}: evidence file missing")
            actual_hash = _sha256(source_path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"{partition}/{market}: evidence SHA-256 mismatch"
                )
            destination = staging_dir / partition / f"{market}.json"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            copied[market] = {
                "path": destination.relative_to(staging_dir).as_posix(),
                "sha256": actual_hash,
                "size_in_bytes": destination.stat().st_size,
            }
        shutil.rmtree(extracted)
        receipts[partition] = {
            "artifact_id": int(frozen["artifact_id"]),
            "artifact_zip_sha256": actual_zip_hash,
            "markets": copied,
        }

    manifest: dict[str, Any] = {
        "identity": "QORE_SHARED_A1_MC18_SHARED_LAB_DATASET_BUNDLE_001",
        "builder_identity": IDENTITY,
        "contract_identity": contract["identity"],
        "dataset_id": contract["bundle_contract"]["dataset_id"],
        "dataset_version": contract["bundle_contract"]["dataset_version"],
        "sources": receipts,
        "frozen_scientific_protocol": contract["frozen_scientific_protocol"],
        "scientific_firewall": {
            "future_oos_used_for_fit": False,
            "future_oos_used_for_validation": False,
            "protected_final_holdout_opened": False,
            "post_outcome_retuning": False,
        },
    }
    manifest_path = staging_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    _deterministic_zip(staging_dir, output)
    return {
        "identity": IDENTITY,
        "status": "BUNDLE_MATERIALIZED_AND_HASHES_VERIFIED",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "bundle_path": str(output),
        "bundle_sha256": _sha256(output),
        "bundle_size_in_bytes": output.stat().st_size,
        "r6_artifact_id": receipts["r6"]["artifact_id"],
        "r5_artifact_id": receipts["r5"]["artifact_id"],
        "outcome_evaluation_executed": False,
        "protected_final_holdout_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--r6-artifact-zip", type=Path, required=True)
    parser.add_argument("--r5-artifact-zip", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_bundle(
        contract_path=args.contract,
        r6_zip=args.r6_artifact_zip,
        r5_zip=args.r5_artifact_zip,
        staging_dir=args.staging_dir,
        output=args.output,
    )
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
