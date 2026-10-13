"""Append-only, hash-chained experiment memory. Git history is the external audit root."""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.research_accelerator.core import ResearchDataError, canonical, digest

GENESIS = "0" * 64


def read_ledger(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    previous = GENESIS
    result: list[dict[str, object]] = []
    for line in path.read_bytes().splitlines():
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ResearchDataError("corrupted research memory line") from exc
        if not isinstance(item, dict) or item.get("previous") != previous:
            raise ResearchDataError("append-only chain was modified")
        signed = {k: v for k, v in item.items() if k != "chain_sha256"}
        expected = digest(signed)
        if item.get("chain_sha256") != expected:
            raise ResearchDataError("research record SHA256 mismatch")
        payload = item.get("payload")
        if not isinstance(payload, dict) or payload.get("config_sha256") is None:
            raise ResearchDataError("missing registered experiment identity")
        result.append(item)
        previous = expected
    return result


def register(path: Path, payload: dict[str, object]) -> dict[str, object]:
    """Refuse duplicate config fingerprints. POSIX advisory lock for concurrent GitHub runners."""
    import fcntl  # Linux CI and research runner; no cross-platform promise

    config = payload.get("config_sha256")
    artifact = payload.get("artifact_sha256")
    if not isinstance(config, str) or not isinstance(artifact, str):
        raise ResearchDataError("config and artifact SHA256 required")
    if any(len(x) != 64 or any(c not in "0123456789abcdef" for c in x) for x in (config, artifact)):
        raise ResearchDataError("invalid experiment SHA256")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        data = stream.read()
        # Verify current chain without allowing mutation during the lock.
        previous = GENESIS
        for line in data.splitlines():
            try:
                item = json.loads(line)
            except ValueError as exc:
                raise ResearchDataError("corrupted append-only memory") from exc
            if not isinstance(item, dict) or item.get("previous") != previous:
                raise ResearchDataError("research memory previous digest mismatch")
            signed = {k: v for k, v in item.items() if k != "chain_sha256"}
            if digest(signed) != item.get("chain_sha256"):
                raise ResearchDataError("research memory chain digest mismatch")
            old = item.get("payload")
            if isinstance(old, dict) and old.get("config_sha256") == config:
                raise ResearchDataError("equivalent experiment already registered")
            previous = item["chain_sha256"]
        if data and not data.endswith(b"\n"):
            raise ResearchDataError("truncated last record")
        entry: dict[str, object] = {
            "schema": "qore.research-memory.v1",
            "previous": previous,
            "payload": payload,
        }
        entry["chain_sha256"] = digest(entry)
        stream.seek(0, os.SEEK_END)
        stream.write(canonical(entry) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
        return entry


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
