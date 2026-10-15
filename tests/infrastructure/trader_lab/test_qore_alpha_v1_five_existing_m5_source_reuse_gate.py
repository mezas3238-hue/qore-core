"""QORE-alpha 2022 source M5 evidence only, anti-tamper failclosed."""
import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.qore_alpha_v1_five_existing_m5_source_reuse_gate import (
    audit_existing_m5_source,
)


def make_source(path: Path, symbol: str = "EURJPY") -> None:
    parts = []
    for y in (2022, 2023):
        yr = str(y)
        raw = path / "RAW_M5_LEDGER" / f"{yr}.jsonl"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(
            json.dumps({"opened_at": f"{yr}-06-01T00:00:00+00:00"}) + "\n",
            encoding="utf-8",
        )
        part = {
            "canonical_symbol": symbol,
            "partition": yr,
            "raw_integrity_status": "CLEAN_PROVIDER_PAYLOAD",
            "retained_bars": 1,
            "first_observed_m5": f"{yr}-06-01T00:00:00+00:00",
            "last_observed_m5": f"{yr}-06-01T00:00:00+00:00",
        }
        parts.append(part)
        att = path / "PARTITION_MANIFEST" / f"{yr}.json"
        att.parent.mkdir(parents=True, exist_ok=True)
        att.write_text(json.dumps(part), encoding="utf-8")
        sha = path / "PARTITION_MANIFEST" / f"{yr}.sha256"
        sha.write_text(
            f"{hashlib.sha256(raw.read_bytes()).hexdigest()}  RAW_M5_LEDGER/{yr}.jsonl\n"
            f"{hashlib.sha256(att.read_bytes()).hexdigest()}  PARTITION_MANIFEST/{yr}.json\n",
            encoding="utf-8",
        )
    main = {
        "canonical_symbol": symbol,
        "raw_integrity_status": "CLEAN_PROVIDER_PAYLOAD",
        "read_only": True,
        "production_authorized": False,
        "target_start": "2016-09-17T00:00:00+00:00",
        "target_end_exclusive": "2026-09-17T00:00:00+00:00",
        "retained_bars": 2,
        "partitions": parts,
    }
    (path / "symbol-consumption-manifest.json").write_text(
        json.dumps(main), encoding="utf-8",
    )


def test_five_have_2022_m5_evidence_but_never_allow_m3(tmp_path):
    for symbol in ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"):
        d = tmp_path / symbol
        d.mkdir()
        make_source(d, symbol)
        r = audit_existing_m5_source(d, symbol=symbol)
        assert r["original_m5_2022_and_2023_verified"]
        assert not r["2022_m3_source_verified"]
        assert not r["can_run_frozen_qore_alpha_96"]
        assert r["source_years"]["2022"]["native_m5_bars"] == 1
        assert r["trading_pnl_accessed"] is False


def test_2022_raw_m5_sha_cannot_be_forged(tmp_path):
    make_source(tmp_path)
    with (tmp_path / "RAW_M5_LEDGER" / "2022.jsonl").open(
        "a", encoding="utf-8"
    ) as f:
        f.write("forged\n")
    with pytest.raises(ValueError, match="differs"):
        audit_existing_m5_source(tmp_path, symbol="EURJPY")


def test_m5_partition_manifest_tamper_rejected(tmp_path):
    make_source(tmp_path)
    f = tmp_path / "PARTITION_MANIFEST" / "2022.json"
    f.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="tampered"):
        audit_existing_m5_source(tmp_path, symbol="EURJPY")


def test_unproven_or_unfrozen_symbol_rejected(tmp_path):
    make_source(tmp_path)
    with pytest.raises(ValueError, match="outside frozen"):
        audit_existing_m5_source(tmp_path, symbol="GBPJPY")
    manifest = tmp_path / "symbol-consumption-manifest.json"
    obj = json.loads(manifest.read_text(encoding="utf-8"))
    obj["canonical_symbol"] = "CADJPY"
    manifest.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        audit_existing_m5_source(tmp_path, symbol="EURJPY")


def test_missing_2022_m5_is_not_2022_coverage(tmp_path):
    make_source(tmp_path)
    (tmp_path / "RAW_M5_LEDGER" / "2022.jsonl").unlink()
    with pytest.raises(ValueError, match="missing 2022"):
        audit_existing_m5_source(tmp_path, symbol="EURJPY")


def test_source_2023_only_not_considered_complete(tmp_path):
    make_source(tmp_path)
    f = tmp_path / "symbol-consumption-manifest.json"
    obj = json.loads(f.read_text(encoding="utf-8"))
    obj["partitions"] = obj["partitions"][1:]
    f.write_text(json.dumps(obj), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 2022"):
        audit_existing_m5_source(tmp_path, symbol="EURJPY")
