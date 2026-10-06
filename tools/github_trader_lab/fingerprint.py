#!/usr/bin/env python3
"""Stable fingerprints for independent GitHub Trader Lab caches.

Prepared-ledger identity depends only on:
- subject files that participate in preparation,
- the declared preparation command/configuration,
- immutable evidence identity.

Experiment variants, reporting metrics, profile naming/versioning and science
thresholds do not invalidate prepared causal ledgers.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _evidence_payload(profile: dict[str, Any]) -> dict[str, dict[str, object]]:
    return {
        lane: {
            "artifact_id": spec["artifact_id"],
            "artifact_path": spec["artifact_path"],
            "sha256": spec["sha256"],
        }
        for lane, spec in sorted(profile["lanes"].items())
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    args = parser.parse_args()

    profile: dict[str, Any] = json.loads(
        args.profile.read_text(encoding="utf-8")
    )
    prep = profile["preparation"]
    paths: set[Path] = set()
    for pattern in prep["dependency_globs"]:
        for raw in glob.glob(
            str(args.subject_root / pattern),
            recursive=True,
        ):
            path = Path(raw)
            if path.is_file():
                paths.add(path)
    if not paths:
        raise SystemExit("preparation dependency globs matched no files")

    subject_hash = hashlib.sha256()
    for path in sorted(paths):
        rel = path.relative_to(args.subject_root).as_posix()
        subject_hash.update(rel.encode())
        subject_hash.update(b"\0")
        subject_hash.update(path.read_bytes())
        subject_hash.update(b"\0")
    subject_digest = subject_hash.hexdigest()

    # Preserve the previous fingerprint so existing v1 caches can be migrated
    # without paying another cold reconstruction.
    legacy = hashlib.sha256()
    for path in sorted(paths):
        rel = path.relative_to(args.subject_root).as_posix()
        legacy.update(rel.encode())
        legacy.update(b"\0")
        legacy.update(path.read_bytes())
        legacy.update(b"\0")
    legacy.update(_canonical(prep))
    legacy_digest = legacy.hexdigest()

    evidence = _evidence_payload(profile)
    evidence_digest = hashlib.sha256(_canonical(evidence)).hexdigest()

    prepared_identity = {
        "schema": "qore.github-trader-lab.prepared-cache.v2",
        "subject_dependencies_sha256": subject_digest,
        "preparation": prep,
        "evidence": evidence,
    }
    prepared_digest = hashlib.sha256(
        _canonical(prepared_identity)
    ).hexdigest()

    print(f"fingerprint={prepared_digest}")
    print(f"legacy_fingerprint={legacy_digest}")
    print(f"evidence_fingerprint={evidence_digest}")
    print(f"subject_dependencies_fingerprint={subject_digest}")
    print(f"file_count={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
