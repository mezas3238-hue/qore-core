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


def recover_one(
    repository: str,
    lane: str,
    spec: dict[str, Any],
    output_dir: Path,
) -> tuple[str, str, str]:
    target = output_dir / f"{lane}.json"
    expected = str(spec["sha256"])
    if target.is_file() and sha256(target) == expected:
        return lane, "hit", expected

    with tempfile.TemporaryDirectory(prefix=f"qore-evidence-{lane}-") as raw:
        root = Path(raw)
        archive = root / "artifact.zip"
        with archive.open("wb") as handle:
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"/repos/{repository}/actions/artifacts/{spec['artifact_id']}/zip",
                ],
                stdout=handle,
                check=True,
            )
        unpacked = root / "unpacked"
        unpacked.mkdir()
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(unpacked)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    profile: dict[str, Any] = json.loads(
        args.profile.read_text(encoding="utf-8")
    )
    lanes = profile["lanes"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    workers = min(
        len(lanes),
        int(profile.get("max_parallel_lanes", len(lanes))),
    )

    with ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix="qore-evidence",
    ) as pool:
        futures = {
            pool.submit(
                recover_one,
                profile["repository"],
                lane,
                spec,
                args.output_dir,
            ): lane
            for lane, spec in lanes.items()
        }
        for future in as_completed(futures):
            lane, cache, digest = future.result()
            print(
                f"QORE_TRADER_LAB_EVIDENCE lane={lane} "
                f"cache={cache} sha256={digest}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
