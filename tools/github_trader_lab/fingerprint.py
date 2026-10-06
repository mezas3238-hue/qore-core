#!/usr/bin/env python3
"""Fingerprint only the subject files that invalidate prepared Trader Lab data."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text(encoding="utf-8"))
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

    h = hashlib.sha256()
    for path in sorted(paths):
        rel = path.relative_to(args.subject_root).as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")

    prep_payload = json.dumps(
        prep,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    h.update(prep_payload)
    digest = h.hexdigest()
    print(f"fingerprint={digest}")
    print(f"file_count={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
