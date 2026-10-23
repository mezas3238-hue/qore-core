"""QORE-alpha five-market GitHub existing M5 source reuse gate.

NO PnL, NO broker, NO M3 interpolation, NO sealed 7Y. File existence,
provider epoch and SHA256 of native M5 ledgers are independently checked
against the producer partition manifests.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

FIVE = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
REQUIRED_YEARS = ("2022", "2023")
SCHEMA = "qore.alpha.v1.existing5.2022_original_m5_provenance_only"


def _object(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"expected object: {path.name}")
    return obj


def _sha(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as stream:
        while chunk := stream.read(2**20):
            h.update(chunk)
    return h.hexdigest()


def _read_sha256s(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        pieces = line.split(maxsplit=1)
        if len(pieces) != 2 or len(pieces[0]) != 64:
            raise ValueError("invalid producer SHA256 manifest")
        key = pieces[1].lstrip(" *")
        if key in values:
            raise ValueError("duplicate SHA ledger path")
        values[key] = pieces[0]
    return values


def audit_existing_m5_source(root: Path, *, symbol: str) -> dict[str, object]:
    if symbol not in FIVE:
        raise ValueError("outside frozen five markets")
    top = _object(root / "symbol-consumption-manifest.json")
    if top.get("canonical_symbol") != symbol:
        raise ValueError("symbol manifest mismatch")
    if top.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD":
        raise ValueError("producer did not report clean M5")
    if top.get("read_only") is not True or top.get("production_authorized") is not False:
        raise ValueError("not research-only native market source")
    if datetime.fromisoformat(top["target_start"]).date() > date(2022, 1, 1):
        raise ValueError("2022 target excluded from producer source")
    if datetime.fromisoformat(top["target_end_exclusive"]).date() < date(2023, 12, 31):
        raise ValueError("2023 target incomplete")
    partitions = top.get("partitions")
    if not isinstance(partitions, list):
        raise ValueError("missing producer partitions")
    by_year = {p["partition"]: p for p in partitions}
    seen: dict[str, dict[str, object]] = {}
    for year in REQUIRED_YEARS:
        if year not in by_year:
            raise ValueError(f"missing {year} M5 original partition")
        meta = by_year[year]
        if (
            meta.get("canonical_symbol") != symbol
            or meta.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"
            or meta.get("retained_bars", 0) <= 0
            or not str(meta.get("first_observed_m5", "")).startswith(year)
            or not str(meta.get("last_observed_m5", "")).startswith(year)
        ):
            raise ValueError(f"invalid original {year} source manifest")
        raw_relative = f"RAW_M5_LEDGER/{year}.jsonl"
        raw = root / raw_relative
        p_json = root / "PARTITION_MANIFEST" / f"{year}.json"
        p_sha = root / "PARTITION_MANIFEST" / f"{year}.sha256"
        if not raw.is_file() or not p_json.is_file() or not p_sha.is_file():
            raise ValueError(f"missing {year} original M5 raw or attestation files")
        sha = _read_sha256s(p_sha)
        if sha.get(raw_relative) != _sha(raw):
            raise ValueError(f"{year} RAW M5 differs from original producer SHA")
        if sha.get(f"PARTITION_MANIFEST/{year}.json") != _sha(p_json):
            raise ValueError(f"{year} M5 partition manifest tampered")
        independent = _object(p_json)
        if independent != meta:
            raise ValueError(f"{year} partition metadata vs root disagreement")
        seen[year] = {
            "first_observed_native_m5": meta["first_observed_m5"],
            "last_observed_native_m5": meta["last_observed_m5"],
            "native_m5_bars": int(meta["retained_bars"]),
            "producer_original_raw_m5_sha256": sha[raw_relative],
            "original_raw_m5_bytes": raw.stat().st_size,
        }
    return {
        "schema": SCHEMA,
        "market": symbol,
        "provider_raw_integrity": top["raw_integrity_status"],
        "original_m5_total_bars": top["retained_bars"],
        "original_m5_2022_and_2023_verified": True,
        "source_years": seen,
        "2022_m3_source_verified": False,
        "m3_reconstructed_from_m5": False,
        "2022_m15_independent_verified": False,
        "bid_ask_and_fees_verified": False,
        "can_run_frozen_qore_alpha_96": False,
        "blockers": [
            "NATIVE_M3_2022_INDEPENDENTLY_MISSING",
            "EXECUTION_BID_ASK_FEES_UNVERIFIED",
        ],
        "trading_features_modified": False,
        "trading_pnl_accessed": False,
        "holdout_7y_accessed": False,
        "live_or_vps_accessed": False,
    }
