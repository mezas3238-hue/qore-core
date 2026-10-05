#!/usr/bin/env python3
"""Run preregistered MC18 consumed-development calibration from a sealed Lab bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

IDENTITY = "QORE_SHARED_A1_MC18_SHARED_LAB_CALIBRATION_RUNNER_001"
BUNDLE_IDENTITY = "QORE_SHARED_A1_MC18_SHARED_LAB_DATASET_BUNDLE_001"
ALLOWED_STATUSES = {
    "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_PASS",
    "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_FALSIFIED",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(bundle: Path, destination: Path) -> None:
    with zipfile.ZipFile(bundle) as archive:
        for info in archive.infolist():
            relative = PurePosixPath(info.filename)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not relative.parts
            ):
                raise ValueError(f"unsafe MC18 dataset member: {info.filename!r}")
            if info.is_dir():
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f"duplicate MC18 dataset path: {relative}")
            with archive.open(info) as source, target.open("wb") as sink:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)


def _verify_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.is_file():
        raise ValueError("MC18 dataset bundle missing manifest.json")
    manifest = json.loads(path.read_text())
    if manifest.get("identity") != BUNDLE_IDENTITY:
        raise ValueError("unexpected MC18 dataset bundle identity")
    for partition in ("r6", "r5"):
        partition_record = dict(manifest["sources"][partition])
        for market, record in dict(partition_record["markets"]).items():
            target = root / str(record["path"])
            if not target.is_file():
                raise ValueError(f"{partition}/{market}: bundle evidence missing")
            if target.stat().st_size != int(record["size_in_bytes"]):
                raise ValueError(f"{partition}/{market}: bundle size mismatch")
            if _sha256(target) != str(record["sha256"]):
                raise ValueError(f"{partition}/{market}: bundle SHA-256 mismatch")
    return manifest


def run_calibration(bundle: Path) -> dict[str, Any]:
    bundle_hash = _sha256(bundle)
    with tempfile.TemporaryDirectory(prefix="qore-a1-mc18-") as temp:
        root = Path(temp)
        _safe_extract(bundle, root)
        manifest = _verify_manifest(root)
        output = root / "mc18_calibration_output.json"
        command = (
            sys.executable,
            "scripts/shared_mc18_counterfactual_failure_calibration.py",
            "--r6-nas",
            str(root / "r6" / "NAS100.json"),
            "--r6-sp",
            str(root / "r6" / "SP500.json"),
            "--r6-us",
            str(root / "r6" / "US30.json"),
            "--r5-nas",
            str(root / "r5" / "NAS100.json"),
            "--r5-sp",
            str(root / "r5" / "SP500.json"),
            "--r5-us",
            str(root / "r5" / "US30.json"),
            "--output",
            str(output),
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "MC18 calibration execution failed: "
                f"returncode={completed.returncode}; stderr={completed.stderr[-4000:]}"
            )
        if not output.is_file():
            raise RuntimeError("MC18 calibration produced no evidence file")
        calibration = json.loads(output.read_text())

    status = str(calibration.get("status"))
    if status not in ALLOWED_STATUSES:
        raise RuntimeError(f"MC18 returned invalid calibration status: {status}")
    if calibration.get("future_oos_used_for_fit") is not False:
        raise RuntimeError("MC18 calibration used future OOS for fit")
    if calibration.get("future_oos_used_for_validation") is not False:
        raise RuntimeError("MC18 calibration used future OOS for validation")
    if calibration.get("protected_final_holdout_opened") is not False:
        raise RuntimeError("MC18 calibration opened protected final holdout")
    if calibration.get("mc18_completed_and_proven") is not False:
        raise RuntimeError("MC18 calibration overclaimed completion")

    return {
        "identity": IDENTITY,
        "status": "GOVERNED_CALIBRATION_EXECUTION_COMPLETE",
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "dataset_version": manifest["dataset_version"],
            "bundle_sha256": bundle_hash,
        },
        "shared_lab_provenance": {
            "run_id": os.environ.get("QORE_SHARED_LAB_RUN_ID"),
            "target_sha": os.environ.get("QORE_SHARED_LAB_TARGET_SHA"),
            "harness_sha": os.environ.get("QORE_SHARED_LAB_HARNESS_SHA"),
            "execution_origin": os.environ.get("QORE_SHARED_LAB_EXECUTION_ORIGIN"),
            "dataset_hash": os.environ.get("QORE_SHARED_LAB_DATASET_HASH"),
        },
        "scientific_disposition": status,
        "frozen_calibration": calibration.get("frozen_calibration"),
        "gates": calibration.get("gates"),
        "raw_validation": calibration.get("raw_validation"),
        "calibrated_validation": calibration.get("calibrated_validation"),
        "lab_task_pass_means_only_execution_integrity": True,
        "mc18_completed_and_proven": False,
        "next_gate": (
            "FREEZE_FOR_FUTURE_INDEPENDENT_MC27_EVALUATION"
            if status == "MC18_CONSUMED_DEVELOPMENT_CALIBRATION_PASS"
            else "FALSIFIED_AND_KEEP_RAW_ENGINE_UNCALIBRATED"
        ),
        "protected_final_holdout_opened": False,
        "productive_authority": False,
        "raw_calibration": calibration,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_calibration(args.dataset_bundle)
    rendered = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
