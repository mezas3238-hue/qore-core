#!/usr/bin/env python3
"""Execute the single governed MC14 B04 replay from a sealed Shared Lab bundle."""

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

IDENTITY = "QORE_SHARED_A1_MC14_SHARED_LAB_REPLAY_RUNNER_001"
BUNDLE_IDENTITY = "QORE_SHARED_A1_MC14_SHARED_LAB_DATASET_BUNDLE_001"
ALLOWED_XAUUSD_DISPOSITIONS = {
    "TEMPORALLY_REPLICATED_RESEARCH_RELATION_FOUND",
    "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM",
    "INSUFFICIENT_DO_NOT_INFER",
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
                raise ValueError(f"unsafe dataset bundle member: {info.filename!r}")
            if info.is_dir():
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f"duplicate dataset bundle path: {relative}")
            with archive.open(info) as source, target.open("wb") as sink:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)


def _verify_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("MC14 dataset bundle missing manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("identity") != BUNDLE_IDENTITY:
        raise ValueError("unexpected MC14 dataset bundle identity")

    seen: set[str] = set()
    for record in manifest.get("content", []):
        relative = str(record["path"])
        if relative in seen:
            raise ValueError(f"duplicate manifest content path: {relative}")
        seen.add(relative)
        path = root / relative
        if not path.is_file():
            raise ValueError(f"manifest content missing from bundle: {relative}")
        expected_size = int(record["size_in_bytes"])
        if path.stat().st_size != expected_size:
            raise ValueError(f"manifest size mismatch: {relative}")
        expected_hash = str(record["sha256"])
        if _sha256(path) != expected_hash:
            raise ValueError(f"manifest SHA-256 mismatch: {relative}")

    required = {
        "targets/NAS100.json",
        "targets/SP500.json",
        "targets/US30.json",
    }
    if not required.issubset(seen):
        raise ValueError(
            "MC14 dataset bundle lacks one or more frozen R8 target files"
        )
    excluded = dict(manifest.get("excluded_source_families", {}))
    us2000 = dict(excluded.get("US2000_BREADTH_PROXY", {}))
    if us2000.get("status") != "INSUFFICIENT_DO_NOT_INFER":
        raise ValueError(
            "MC14 bundle must preserve US2000 as frozen INSUFFICIENT"
        )
    if us2000.get("target_evaluation_executed") is not False:
        raise ValueError("MC14 bundle attempted US2000 target evaluation")
    return manifest


def run_replay(bundle: Path) -> dict[str, Any]:
    bundle_hash = _sha256(bundle)
    with tempfile.TemporaryDirectory(prefix="qore-a1-mc14-") as temp:
        root = Path(temp)
        _safe_extract(bundle, root)
        manifest = _verify_manifest(root)

        output = root / "mc14_replay_output.json"
        command = (
            sys.executable,
            "scripts/shared_mc14_b04_new_information_causal_replay.py",
            "--xauusd-only",
            "--xauusd-root",
            str(root / "sources" / "XAUUSD_DEFENSIVE_PROXY"),
            "--r8-nas",
            str(root / "targets" / "NAS100.json"),
            "--r8-sp",
            str(root / "targets" / "SP500.json"),
            "--r8-us",
            str(root / "targets" / "US30.json"),
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
                "MC14 governed replay failed: "
                f"returncode={completed.returncode}; stderr={completed.stderr[-4000:]}"
            )
        if not output.is_file():
            raise RuntimeError("MC14 governed replay produced no evidence file")
        replay = json.loads(output.read_text())

    family_results = dict(replay["family_results"])
    us2000 = dict(family_results["US2000_BREADTH_PROXY"])
    xauusd = dict(family_results["XAUUSD_DEFENSIVE_PROXY"])
    if us2000.get("status") != "INSUFFICIENT_DO_NOT_INFER":
        raise RuntimeError(
            "MC14 governance violation: frozen US2000 insufficiency changed"
        )
    if xauusd.get("status") not in ALLOWED_XAUUSD_DISPOSITIONS:
        raise RuntimeError(
            f"MC14 XAUUSD returned invalid disposition: {xauusd.get('status')}"
        )
    if replay.get("protected_certification_holdout_opened") is not False:
        raise RuntimeError("MC14 replay opened protected certification holdout")
    if replay.get("r6_r5_read") is not False:
        raise RuntimeError("MC14 replay unexpectedly read R6/R5")

    return {
        "identity": IDENTITY,
        "status": "GOVERNED_REPLAY_EXECUTION_COMPLETE",
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
        "scientific_disposition": {
            "US2000_BREADTH_PROXY": us2000.get("status"),
            "XAUUSD_DEFENSIVE_PROXY": xauusd.get("status"),
            "xauusd_reason": xauusd.get("reason"),
            "xauusd_replicated_relation_count": xauusd.get(
                "replicated_relation_count", 0
            ),
        },
        "lab_task_pass_means_only_execution_integrity": True,
        "mc14_completed_and_proven": bool(
            xauusd.get("status")
            == "TEMPORALLY_REPLICATED_RESEARCH_RELATION_FOUND"
        ),
        "knowledge_auto_promotion": False,
        "protected_final_holdout_opened": False,
        "productive_authority": False,
        "raw_replay": replay,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = run_replay(args.dataset_bundle)
    rendered = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
