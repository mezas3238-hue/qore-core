"""Only tiny invented ZIP-byte fixtures: no real historical prices or broker access."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from qore.research.alpha2_p0_private_restore_sha import (
    PASS_STATUS,
    validate_source_inventory,
    verify_local_restore,
)
from qore.research.alpha2_source33_artifact_expiry_inventory import (
    ATLAS_PREFIX,
    ATLAS_RUN,
    HEADS,
    IDENTITY,
    NEW21,
    NEW21_PREFIX,
    NEW21_RUN,
    ORIGINAL12,
    SOURCE33_RUN,
)


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def synthetic_35(tmp_path: Path) -> tuple[dict, Path]:
    root = tmp_path / "private-restored"
    rows = {}
    for cohort, symbols, run, prefix in (
        ("ATLAS_ORIGINAL12", ORIGINAL12, ATLAS_RUN, ATLAS_PREFIX),
        ("ICMARKETS_NEW21", NEW21, NEW21_RUN, NEW21_PREFIX),
    ):
        folder = root / cohort
        folder.mkdir(parents=True)
        for index, symbol in enumerate(symbols):
            data = f"synthetic-zip-{cohort}-{index}-{symbol}".encode()
            (folder / f"{symbol}.zip").write_bytes(data)
            rows[symbol] = {
                "run_id": run,
                "name": prefix + symbol + "-" + HEADS[run],
                "id": 10000 + len(rows),
                "bytes": len(data),
                "zip_sha256_from_github": sha(data),
            }
    meta = root / "META"
    meta.mkdir()
    aggregate = b"synthetic-atlas-aggregate-no-real-prices"
    manifest = b"synthetic-33-manifest-no-real-prices"
    (meta / "atlas-aggregate.zip").write_bytes(aggregate)
    (meta / "source33-manifest.zip").write_bytes(manifest)
    report = {
        "identity": IDENTITY,
        "original_code_heads": {str(run): head for run, head in HEADS.items()},
        "original_source_33_sha256_previously_frozen":
            "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85",
        "original_m5_source_markets_verified": 33,
        "original12_aggregate_manifest_available": True,
        "per_original_market_artifact_ids_digests_expiry": rows,
        "total_compressed_original33_m5_bytes":
            sum(row["bytes"] for row in rows.values()),
        "cohorts": {
            "ATLAS_ORIGINAL12": {
                "archive_bytes": sum(rows[s]["bytes"] for s in ORIGINAL12),
                "aggregate_sha": sha(aggregate),
            },
            "ICMARKETS_NEW21": {
                "archive_bytes": sum(rows[s]["bytes"] for s in NEW21),
            },
        },
        "original_source_manifest_sha256": sha(manifest),
    }
    return report, root


def test_synthetic_full_35_rehash_never_certifies_backup_or_trader(tmp_path):
    report, root = synthetic_35(tmp_path)
    assert len(validate_source_inventory(report)) == 33
    result = verify_local_restore(report, root)
    assert result["status"] == PASS_STATUS
    assert result["total_local_zips_hashed"] == 35
    assert result["local_original_m5_zips_sha_and_size_matched"] == 33
    assert result["SOURCE_ARCHIVED_PERMANENTLY"] is False
    assert result["private_vault_authorized_and_durable_verified"] is False
    assert result["broker_retention_license_verified"] is False
    assert result["independent_offsite_reader_verified"] is False
    assert result["source_inventory_authenticated_by_this_local_verifier"] is False
    assert result["UTC001_certified"] is False
    assert result["trade_orders_sent"] == 0


def test_original_same_length_byte_change_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    path = root / "ATLAS_ORIGINAL12" / "AUDJPY.zip"
    before = path.read_bytes()
    path.write_bytes(bytes([before[0] ^ 1]) + before[1:])
    with pytest.raises(ValueError, match="SHA256_MISMATCH"):
        verify_local_restore(report, root)


def test_original_truncation_denied_before_sha(tmp_path):
    report, root = synthetic_35(tmp_path)
    (root / "ICMARKETS_NEW21" / f"{NEW21[0]}.zip").write_bytes(b"x")
    with pytest.raises(ValueError, match="SIZE_MISMATCH"):
        verify_local_restore(report, root)


@pytest.mark.parametrize("name", ["atlas-aggregate.zip", "source33-manifest.zip"])
def test_meta_tamper_rejected(tmp_path, name):
    report, root = synthetic_35(tmp_path)
    (root / "META" / name).write_bytes(b"changed-meta")
    with pytest.raises(ValueError, match="SHA256_MISMATCH"):
        verify_local_restore(report, root)


def test_missing_or_extra_zip_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    (root / "ATLAS_ORIGINAL12" / "AUDJPY.zip").unlink()
    with pytest.raises(ValueError, match="MISSING_OR_EXTRA_FILE"):
        verify_local_restore(report, root)
    report, root = synthetic_35(tmp_path)
    (root / "META" / "unregistered.zip").write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="MISSING_OR_EXTRA_FILE"):
        verify_local_restore(report, root)


def test_symlink_file_denied_even_if_sha_identical(tmp_path):
    report, root = synthetic_35(tmp_path)
    expected = root / "ATLAS_ORIGINAL12" / "AUDJPY.zip"
    shadow = tmp_path / "shadow"
    shadow.write_bytes(expected.read_bytes())
    expected.unlink()
    expected.symlink_to(shadow)
    with pytest.raises(ValueError, match="ZIP_UNSAFE_OR_ABSENT"):
        verify_local_restore(report, root)


def test_symlink_cohort_directory_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    source = root / "ICMARKETS_NEW21"
    shadow = tmp_path / "separate-directory"
    source.rename(shadow)
    source.symlink_to(shadow, target_is_directory=True)
    with pytest.raises(ValueError, match="FOLDER_UNSAFE_OR_ABSENT"):
        verify_local_restore(report, root)


def test_hardlink_file_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    source = root / "ATLAS_ORIGINAL12" / "AUDJPY.zip"
    target = root / "ATLAS_ORIGINAL12" / "AUDUSD.zip"
    target.unlink()
    os.link(source, target)
    with pytest.raises(ValueError, match="ZIP_NOT_UNIQUE"):
        verify_local_restore(report, root)


def test_forged_run_sha_and_partial_symbols_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    report["original_code_heads"][str(SOURCE33_RUN)] = "f" * 40
    with pytest.raises(ValueError, match="PROVENANCE_DRIFT"):
        verify_local_restore(report, root)
    report, root = synthetic_35(tmp_path)
    report["per_original_market_artifact_ids_digests_expiry"].pop("AUDJPY")
    with pytest.raises(ValueError, match="NOT_EXACT33"):
        verify_local_restore(report, root)


def test_replayed_digest_or_boolean_byte_count_denied(tmp_path):
    report, root = synthetic_35(tmp_path)
    rows = report["per_original_market_artifact_ids_digests_expiry"]
    rows["AUDUSD"]["zip_sha256_from_github"] = rows["AUDJPY"][
        "zip_sha256_from_github"
    ]
    with pytest.raises(ValueError, match="DUPLICATE_OR_IDENTITY_DRIFT"):
        verify_local_restore(report, root)
    report, root = synthetic_35(tmp_path)
    report["per_original_market_artifact_ids_digests_expiry"]["AUDJPY"][
        "bytes"
    ] = True
    with pytest.raises(ValueError, match="DUPLICATE_OR_IDENTITY_DRIFT"):
        verify_local_restore(report, root)


def test_provider_alias_not_accepted(tmp_path):
    report, root = synthetic_35(tmp_path)
    atlas = root / "ATLAS_ORIGINAL12"
    (atlas / "NAS100.zip").rename(atlas / "USTEC.zip")
    with pytest.raises(ValueError, match="MISSING_OR_EXTRA_FILE"):
        verify_local_restore(report, root)
