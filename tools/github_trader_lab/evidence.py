#!/usr/bin/env python3
"""Recover and verify immutable evidence declared by a Trader Lab profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_archive(repository: str, artifact_id: int, target: Path) -> None:
    with target.open("wb") as handle:
        subprocess.run(
            [
                "gh",
                "api",
                f"/repos/{repository}/actions/artifacts/{artifact_id}/zip",
            ],
            stdout=handle,
            check=True,
        )


def _safe_extract(archive: Path, target: Path) -> None:
    target_resolved = target.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            candidate = (target / member.filename).resolve()
            if target_resolved not in candidate.parents and candidate != target_resolved:
                raise ValueError(f"unsafe archive member: {member.filename}")
        zf.extractall(target)


def recover_one(
    repository: str,
    lane: str,
    spec: dict[str, Any],
    output_dir: Path,
) -> tuple[str, str, str]:
    target = output_dir / f"{lane}.json"
    expected = str(spec["sha256"]).removeprefix("sha256:")
    if target.is_file() and sha256(target) == expected:
        return lane, "hit", expected

    with tempfile.TemporaryDirectory(prefix=f"qore-evidence-{lane}-") as raw:
        root = Path(raw)
        archive = root / "artifact.zip"
        _download_archive(repository, int(spec["artifact_id"]), archive)
        unpacked = root / "unpacked"
        unpacked.mkdir()
        _safe_extract(archive, unpacked)
        source = unpacked / str(spec["artifact_path"])
        if not source.is_file():
            raise FileNotFoundError(f"{lane}: {source}")
        actual = sha256(source)
        if actual != expected:
            raise ValueError(
                f"{lane}: evidence sha mismatch {actual} != {expected}"
            )
        shutil.copy2(source, target)
        return lane, "miss", actual


def recover_bundle(
    repository: str,
    name: str,
    spec: dict[str, Any],
    output_dir: Path,
) -> tuple[str, str, str]:
    """Recover a whole immutable artifact once for shared suite inputs."""

    target = output_dir / "assets" / name
    marker = target / ".archive-sha256"
    expected = str(spec["archive_sha256"]).removeprefix("sha256:")
    if target.is_dir() and marker.is_file():
        if marker.read_text(encoding="utf-8").strip() == expected:
            return name, "hit", expected

    with tempfile.TemporaryDirectory(prefix=f"qore-asset-{name}-") as raw:
        root = Path(raw)
        archive = root / "artifact.zip"
        _download_archive(repository, int(spec["artifact_id"]), archive)
        actual = sha256(archive)
        if actual != expected:
            raise ValueError(
                f"{name}: artifact zip sha mismatch {actual} != {expected}"
            )
        unpacked = root / "unpacked"
        unpacked.mkdir()
        _safe_extract(archive, unpacked)
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(unpacked, target)
        marker.write_text(expected + "\n", encoding="utf-8")
        return name, "miss", actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    profile: dict[str, Any] = json.loads(
        args.profile.read_text(encoding="utf-8")
    )
    lanes = profile["lanes"]
    bundles = profile.get("auxiliary_artifacts", {})
    if not isinstance(bundles, dict):
        raise ValueError("auxiliary_artifacts must be a mapping")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    requested_workers = int(
        profile.get(
            "max_parallel_evidence_downloads",
            max(1, len(lanes) + len(bundles)),
        )
    )
    workers = max(1, min(len(lanes) + len(bundles), requested_workers))

    with ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix="qore-evidence",
    ) as pool:
        futures = {}
        for lane, spec in lanes.items():
            future = pool.submit(
                recover_one,
                profile["repository"],
                lane,
                spec,
                args.output_dir,
            )
            futures[future] = ("lane", lane)
        for name, spec in bundles.items():
            future = pool.submit(
                recover_bundle,
                profile["repository"],
                name,
                spec,
                args.output_dir,
            )
            futures[future] = ("asset", name)

        for future in as_completed(futures):
            kind, _name = futures[future]
            name, cache, digest = future.result()
            if kind == "lane":
                print(
                    f"QORE_TRADER_LAB_EVIDENCE lane={name} "
                    f"cache={cache} sha256={digest}",
                    flush=True,
                )
            else:
                print(
                    f"QORE_TRADER_LAB_ASSET name={name} "
                    f"cache={cache} archive_sha256={digest}",
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
