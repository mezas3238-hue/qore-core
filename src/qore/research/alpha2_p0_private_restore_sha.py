"""Offline SHA verifier for an already authorized/private restore of Alpha2 originals.

NO backup, network, source ZIP extraction, market prices, or custody certification.
See QORE_ALPHA2_P0_PRIVATE_RESTORE_SHA_VERIFIER_CONTRACT_2026-10-12.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from qore.research.alpha2_source33_artifact_expiry_inventory import (
    ATLAS_PREFIX,
    ATLAS_RUN,
    HEADS,
    IDENTITY,
    NEW21,
    NEW21_PREFIX,
    NEW21_RUN,
    ORIGINAL12,
    SIGNED33_PREFIX,
    SOURCE33_RUN,
)

HEX256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
FROZEN_ORIGINAL33 = (
    "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
)
PASS_STATUS = "LOCAL_RESTORED_35_ZIPS_SHA_MATCH_SOURCE_INVENTORY_ONLY"
SUBDIRS = ("ATLAS_ORIGINAL12", "ICMARKETS_NEW21", "META")


def _require_digest(value: Any) -> str:
    if type(value) is not str or HEX256.fullmatch(value) is None:
        raise ValueError("P0_RESTORE_INVENTORY_SHA_INVALID")
    return value


def validate_source_inventory(report: Any) -> dict[str, dict]:
    """Validate shape and immutable provenance claims, not authenticity of input JSON.

    Authenticity REQUIRES an external GitHub API/source witness, not self-reporting.
    """
    if type(report) is not dict:
        raise ValueError("P0_RESTORE_INVENTORY_INVALID")
    expected_heads = {str(run): sha for run, sha in HEADS.items()}
    if (
        report.get("identity") != IDENTITY
        or report.get("original_code_heads") != expected_heads
        or report.get("original_source_33_sha256_previously_frozen")
        != FROZEN_ORIGINAL33
        or report.get("original_m5_source_markets_verified") != 33
        or report.get("original12_aggregate_manifest_available") is not True
    ):
        raise ValueError("P0_RESTORE_INVENTORY_ORIGINAL_PROVENANCE_DRIFT")

    markets = report.get("per_original_market_artifact_ids_digests_expiry")
    if type(markets) is not dict or set(markets) != set(ORIGINAL12) | set(NEW21):
        raise ValueError("P0_RESTORE_INVENTORY_NOT_EXACT33")
    ids: set[int] = set()
    digests: set[str] = set()
    total = 0
    for symbol, row in markets.items():
        if type(row) is not dict:
            raise ValueError("P0_RESTORE_INVENTORY_ROW_INVALID")
        atlas = symbol in ORIGINAL12
        run = ATLAS_RUN if atlas else NEW21_RUN
        prefix = ATLAS_PREFIX if atlas else NEW21_PREFIX
        artifact_id = row.get("id")
        size = row.get("bytes")
        digest = _require_digest(row.get("zip_sha256_from_github"))
        if (
            row.get("run_id") != run
            or row.get("name") != prefix + symbol + "-" + HEADS[run]
            or type(artifact_id) is not int
            or artifact_id <= 0
            or type(size) is not int
            or size <= 0
            or artifact_id in ids
            or digest in digests
        ):
            raise ValueError("P0_RESTORE_INVENTORY_DUPLICATE_OR_IDENTITY_DRIFT")
        ids.add(artifact_id)
        digests.add(digest)
        total += size
    if (
        report.get("total_compressed_original33_m5_bytes") != total
        or report.get("cohorts", {}).get("ATLAS_ORIGINAL12", {}).get("archive_bytes")
        != sum(markets[s]["bytes"] for s in ORIGINAL12)
        or report.get("cohorts", {}).get("ICMARKETS_NEW21", {}).get("archive_bytes")
        != sum(markets[s]["bytes"] for s in NEW21)
    ):
        raise ValueError("P0_RESTORE_INVENTORY_BYTE_TOTAL_DRIFT")
    aggregate = _require_digest(
        report["cohorts"]["ATLAS_ORIGINAL12"].get("aggregate_sha")
    )
    signed = _require_digest(report.get("original_source_manifest_sha256"))
    if aggregate in digests or signed in digests or aggregate == signed:
        raise ValueError("P0_RESTORE_INVENTORY_META_SHA_DUPLICATE")
    return markets


def _open_folder(name: str | os.PathLike[str], *, dir_fd: int | None = None) -> int:
    """Prevent symlinked directories, fail closed on platforms without NOFOLLOW."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ValueError("P0_RESTORE_POSIX_NOFOLLOW_REQUIRED")
    try:
        fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd
        )
    except OSError as error:
        raise ValueError("P0_RESTORE_FOLDER_UNSAFE_OR_ABSENT") from error
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("P0_RESTORE_FOLDER_NOT_DIRECTORY")
    return fd


def _exact_names(fd: int, expected: set[str]) -> None:
    if set(os.listdir(fd)) != expected:
        raise ValueError("P0_RESTORE_MISSING_OR_EXTRA_FILE")


def _verify_zip(
    directory_fd: int,
    filename: str,
    digest: str,
    size: int | None,
    inode_keys: set[tuple[int, int]],
) -> None:
    try:
        fd = os.open(
            filename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd
        )
    except OSError as error:
        raise ValueError("P0_RESTORE_ZIP_UNSAFE_OR_ABSENT") from error
    with os.fdopen(fd, "rb") as source:
        meta = os.fstat(source.fileno())
        ident = (meta.st_dev, meta.st_ino)
        if (
            not stat.S_ISREG(meta.st_mode)
            or meta.st_nlink != 1
            or meta.st_size <= 0
            or (size is not None and meta.st_size != size)
            or ident in inode_keys
        ):
            raise ValueError("P0_RESTORE_ZIP_NOT_UNIQUE_REGULAR_OR_SIZE_MISMATCH")
        inode_keys.add(ident)
        hasher = hashlib.sha256()
        while chunk := source.read(1024 * 1024):
            hasher.update(chunk)
        if "sha256:" + hasher.hexdigest() != digest:
            raise ValueError("P0_RESTORE_SHA256_MISMATCH")


def verify_local_restore(report: Any, restored_root: Path) -> dict:
    """Hash 35 already-restored private ZIPs; NEVER declare durable custody."""
    rows = validate_source_inventory(report)
    root_fd = _open_folder(restored_root)
    inode_keys: set[tuple[int, int]] = set()
    try:
        _exact_names(root_fd, set(SUBDIRS))
        for cohort, symbols in (
            ("ATLAS_ORIGINAL12", ORIGINAL12),
            ("ICMARKETS_NEW21", NEW21),
        ):
            fd = _open_folder(cohort, dir_fd=root_fd)
            try:
                _exact_names(fd, {symbol + ".zip" for symbol in symbols})
                for symbol in sorted(symbols):
                    row = rows[symbol]
                    _verify_zip(
                        fd, symbol + ".zip", row["zip_sha256_from_github"],
                        row["bytes"], inode_keys
                    )
            finally:
                os.close(fd)
        fd = _open_folder("META", dir_fd=root_fd)
        try:
            _exact_names(fd, {"atlas-aggregate.zip", "source33-manifest.zip"})
            _verify_zip(
                fd, "atlas-aggregate.zip",
                report["cohorts"]["ATLAS_ORIGINAL12"]["aggregate_sha"],
                None, inode_keys
            )
            _verify_zip(
                fd, "source33-manifest.zip",
                report["original_source_manifest_sha256"],
                None, inode_keys
            )
        finally:
            os.close(fd)
    finally:
        os.close(root_fd)
    return {
        "identity": "QORE_ALPHA2_P0_OFFLINE_PRIVATE_RESTORE_SHA_ONLY_V1",
        "status": PASS_STATUS,
        "local_original_m5_zips_sha_and_size_matched": 33,
        "local_aggregate_and_manifest_zips_sha_matched": 2,
        "total_local_zips_hashed": 35,
        "source_inventory_authenticated_by_this_local_verifier": False,
        "broker_retention_license_verified": False,
        "private_vault_authorized_and_durable_verified": False,
        "independent_offsite_reader_verified": False,
        "yearly_raw_quality_partition_sha_verified": False,
        "SOURCE_ARCHIVED_PERMANENTLY": False,
        "UTC001_certified": False,
        "trade_orders_sent": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline restored ZIP SHA check; never grants durable custody"
    )
    parser.add_argument("original_github_inventory_json", type=Path)
    parser.add_argument("private_local_restore_directory", type=Path)
    args = parser.parse_args()
    inventory = json.loads(
        args.original_github_inventory_json.read_text(encoding="utf-8")
    )
    print(json.dumps(
        verify_local_restore(inventory, args.private_local_restore_directory),
        sort_keys=True
    ))


if __name__ == "__main__":
    main()
