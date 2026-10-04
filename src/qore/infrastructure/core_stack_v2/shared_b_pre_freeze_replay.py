"""Deterministic replay of sealed Architect-B6 pre-freeze evidence bundles.

This replays the evidence layer only. It proves that the sealed B-16 frontier
and B-21 provenance manifest are internally hash-consistent and deterministic.
It does not claim that upstream B4/B5 scientific work is terminal and cannot
authorize B-22, B-24, certification, production, trading, Risk, CIBO or
Execution.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

B16_JSON = "shared-b-sensor-qualification-frontier.json"
B21_MANIFEST_JSON = "shared-b-provenance-manifest.json"
B21_COVERAGE_JSON = "shared-b-provenance-coverage.json"


class SharedBPreFreezeReplayError(ValueError):
    """Sealed B6 evidence failed deterministic replay."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(payload: object) -> str:
    return _sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )


def _parse_sha256s(raw: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            digest, name = line.split(maxsplit=1)
        except ValueError as exc:
            raise SharedBPreFreezeReplayError(
                "invalid SHA256SUMS row"
            ) from exc
        normalized = name.strip().removeprefix("*").removeprefix("./")
        if len(digest) != 64:
            raise SharedBPreFreezeReplayError("invalid SHA256SUMS digest")
        int(digest, 16)
        if normalized in rows:
            raise SharedBPreFreezeReplayError("duplicate SHA256SUMS entry")
        rows[normalized] = digest
    if not rows:
        raise SharedBPreFreezeReplayError("empty SHA256SUMS")
    return rows


def _read_verified_zip(path: Path) -> dict[str, bytes]:
    if not path.is_file():
        raise SharedBPreFreezeReplayError(f"missing artifact zip: {path}")
    with zipfile.ZipFile(path) as archive:
        names = tuple(archive.namelist())
        if "SHA256SUMS" not in names:
            raise SharedBPreFreezeReplayError("artifact lacks SHA256SUMS")
        checks = _parse_sha256s(
            archive.read("SHA256SUMS").decode("utf-8")
        )
        payloads: dict[str, bytes] = {}
        for name, expected in checks.items():
            if name not in names:
                raise SharedBPreFreezeReplayError(
                    f"SHA256SUMS references missing file: {name}"
                )
            raw = archive.read(name)
            if _sha256(raw) != expected:
                raise SharedBPreFreezeReplayError(
                    f"artifact digest mismatch: {name}"
                )
            payloads[name] = raw
        return payloads


def _json(payloads: dict[str, bytes], name: str) -> dict[str, Any]:
    if name not in payloads:
        raise SharedBPreFreezeReplayError(f"missing sealed JSON: {name}")
    value = json.loads(payloads[name].decode("utf-8"))
    if not isinstance(value, dict):
        raise SharedBPreFreezeReplayError(f"{name} must contain object")
    return value


def _verify_embedded_fingerprint(
    payload: dict[str, Any],
    *,
    key: str,
) -> str:
    stored = payload.get(key)
    if not isinstance(stored, str) or len(stored) != 64:
        raise SharedBPreFreezeReplayError(
            f"invalid embedded fingerprint: {key}"
        )
    clone = dict(payload)
    del clone[key]
    calculated = _canonical_hash(clone)
    if calculated != stored:
        raise SharedBPreFreezeReplayError(
            f"embedded fingerprint mismatch: {key}"
        )
    return stored


@dataclass(frozen=True, slots=True)
class SharedBPreFreezeReplayReceipt:
    b16_frontier_fingerprint_sha256: str
    b21_manifest_fingerprint_sha256: str
    b16_artifact_zip_sha256: str
    b21_artifact_zip_sha256: str
    provenance_covered_count: int
    provenance_missing_ids: tuple[str, ...]
    pre_freeze_provenance_complete: bool
    deterministic_replay_verified: bool
    replay_fingerprint_sha256: str
    fresh_holdout_opened: bool = False
    broker_mutation: bool = False
    productive_authority: bool = False
    certification_authority: bool = False


def _replay_once(
    b16_zip: Path,
    b21_zip: Path,
) -> tuple[dict[str, Any], str]:
    b16_payloads = _read_verified_zip(b16_zip)
    b21_payloads = _read_verified_zip(b21_zip)

    b16 = _json(b16_payloads, B16_JSON)
    manifest = _json(b21_payloads, B21_MANIFEST_JSON)
    coverage = _json(b21_payloads, B21_COVERAGE_JSON)

    if b16.get("identity") != "SHARED_B_SENSOR_QUALIFICATION_FRONTIER_001":
        raise SharedBPreFreezeReplayError("unexpected B16 identity")
    if (
        manifest.get("identity")
        != "SHARED_B_GLOBAL_WORLD_PERCEPTION_PROVENANCE_MANIFEST_001"
    ):
        raise SharedBPreFreezeReplayError("unexpected B21 manifest identity")
    if coverage.get("identity") != "SHARED_INTEGRATOR_B_PROVENANCE_COVERAGE_002":
        raise SharedBPreFreezeReplayError("unexpected B21 coverage identity")

    b16_fp = _verify_embedded_fingerprint(
        b16,
        key="frontier_fingerprint_sha256",
    )
    b21_fp = _verify_embedded_fingerprint(
        manifest,
        key="manifest_fingerprint_sha256",
    )

    covered_count = coverage.get("covered_count")
    missing_ids = coverage.get("missing_ids")
    if covered_count != 22:
        raise SharedBPreFreezeReplayError("expected exact 22/24 provenance")
    if missing_ids != ["B-22", "B-24"]:
        raise SharedBPreFreezeReplayError(
            "pre-freeze provenance may miss only B-22/B-24"
        )
    if coverage.get("missing_terminal_ids") != []:
        raise SharedBPreFreezeReplayError(
            "terminal B workstream missing provenance"
        )
    if coverage.get("missing_external_blocked_ids") != []:
        raise SharedBPreFreezeReplayError(
            "externally blocked B workstream missing provenance"
        )
    if coverage.get("coverage_complete") is not False:
        raise SharedBPreFreezeReplayError(
            "24/24 final provenance cannot exist pre-freeze"
        )

    for payload, label in ((b16, "B16"), (manifest, "B21")):
        if payload.get("fresh_holdout_opened") is not False:
            raise SharedBPreFreezeReplayError(f"{label} opened holdout")
        if payload.get("broker_mutation") is not False:
            raise SharedBPreFreezeReplayError(f"{label} mutated broker")
        if payload.get("productive_authority") is not False:
            raise SharedBPreFreezeReplayError(
                f"{label} carries productive authority"
            )

    snapshot: dict[str, Any] = {
        "identity": "SHARED_B_PRE_FREEZE_EVIDENCE_REPLAY_SNAPSHOT_001",
        "b16_frontier_fingerprint_sha256": b16_fp,
        "b21_manifest_fingerprint_sha256": b21_fp,
        "b16_sensor_count": b16.get("sensor_count"),
        "b16_admitted_count": b16.get("admitted_count"),
        "b16_causal_qualification_complete_count": b16.get(
            "causal_qualification_complete_count"
        ),
        "b21_evidence_pointer_count": manifest.get("evidence_pointer_count"),
        "provenance_covered_count": covered_count,
        "provenance_missing_ids": tuple(missing_ids),
        "pre_freeze_provenance_complete": True,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "certification_authority": False,
    }
    return snapshot, _canonical_hash(snapshot)


def replay_pre_freeze_evidence(
    *,
    b16_zip: Path,
    b21_zip: Path,
) -> SharedBPreFreezeReplayReceipt:
    """Replay sealed B6 evidence twice and require byte-derived identity."""

    first_snapshot, first_fp = _replay_once(b16_zip, b21_zip)
    second_snapshot, second_fp = _replay_once(b16_zip, b21_zip)
    deterministic = first_snapshot == second_snapshot and first_fp == second_fp
    if not deterministic:
        raise SharedBPreFreezeReplayError(
            "pre-freeze evidence replay is non-deterministic"
        )
    return SharedBPreFreezeReplayReceipt(
        b16_frontier_fingerprint_sha256=str(
            first_snapshot["b16_frontier_fingerprint_sha256"]
        ),
        b21_manifest_fingerprint_sha256=str(
            first_snapshot["b21_manifest_fingerprint_sha256"]
        ),
        b16_artifact_zip_sha256=_sha256(b16_zip.read_bytes()),
        b21_artifact_zip_sha256=_sha256(b21_zip.read_bytes()),
        provenance_covered_count=int(
            first_snapshot["provenance_covered_count"]
        ),
        provenance_missing_ids=tuple(
            first_snapshot["provenance_missing_ids"]
        ),
        pre_freeze_provenance_complete=bool(
            first_snapshot["pre_freeze_provenance_complete"]
        ),
        deterministic_replay_verified=True,
        replay_fingerprint_sha256=first_fp,
    )
