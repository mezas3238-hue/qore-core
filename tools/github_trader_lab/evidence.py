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
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    profile: dict[str, Any] = json.loads(args.profile.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for lane, spec in profile["lanes"].items():
        target = args.output_dir / f"{lane}.json"
        expected = str(spec["sha256"])
        if target.is_file() and sha256(target) == expected:
            print(f"QORE_TRADER_LAB_EVIDENCE lane={lane} cache=hit sha256={expected}", flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix=f"qore-{lane}-") as raw:
            root = Path(raw)
            archive = root / "artifact.zip"
            command = [
                "gh",
                "api",
                f"/repos/{profile['repository']}/actions/artifacts/{spec['artifact_id']}/zip",
            ]
            with archive.open("wb") as handle:
                subprocess.run(command, stdout=handle, check=True)
            unpacked = root / "unpacked"
            unpacked.mkdir()
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(unpacked)
            source = unpacked / str(spec["artifact_path"])
            if not source.is_file():
                raise FileNotFoundError(f"{lane}: {source}")
            actual = sha256(source)
            if actual != expected:
                raise ValueError(f"{lane}: evidence sha mismatch {actual} != {expected}")
            shutil.copy2(source, target)
            print(f"QORE_TRADER_LAB_EVIDENCE lane={lane} cache=miss sha256={actual}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
