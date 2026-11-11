"""Read-only authenticity probe of archived 2024/2025 broker native M5 evidence.

This does NOT replay Pine, trigger strategies or certify fresh OOS.
Reads original GitHub Actions artifact only inside ephemeral GitHub runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)
YEARS = (2024, 2025)
ALIASES = {"NAS100": "USTEC", "SP500": "US500"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(root: Path, symbol: str, cohort: str) -> dict[str, object]:
    found = list(root.rglob("symbol-consumption-manifest.json"))
    if len(found) != 1:
        raise ValueError(f"expected unique source manifest, got {len(found)}")
    manifest_path = found[0]
    folder = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provider = ALIASES.get(symbol, symbol) if cohort == "ATLAS_DEMO_BROKER_UNVERIFIED" else symbol
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError("canonical symbol mismatch")
    if manifest.get("provider_symbol") != provider:
        raise ValueError("provider alias mismatch")
    if manifest.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD":
        raise ValueError("source integrity status not clean")
    if type(manifest.get("provider_symbol_id")) is not int:
        raise ValueError("invalid provider symbol ID")
    output: dict[str, object] = {
        "symbol": symbol,
        "provider_symbol": provider,
        "cohort": cohort,
        "source_authentic": True,
        "pine_engine_parity": False,
        "broker_tradingview_parity": False,
        "is_fresh_holdout": False,
        "economic_result": "NOT_EVALUATED",
        "window_utc": ["2024-01-01", "2026-01-01_EXCLUSIVE"],
        "years": {},
    }
    counts = {}
    for year in YEARS:
        path = folder / "RAW_M5_LEDGER" / f"{year}.jsonl"
        mh = folder / "PARTITION_MANIFEST" / f"{year}.sha256"
        if not path.is_file() or not mh.is_file():
            raise ValueError(f"missing archived year {year}: RAW ledger or SHA manifest")
        sha_expected = None
        for line in mh.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[1].lstrip("*").strip() == f"RAW_M5_LEDGER/{year}.jsonl":
                sha_expected = parts[0].lower()
        if sha_expected is None or len(sha_expected) != 64:
            raise ValueError(f"original SHA missing for year {year}")
        if digest(path) != sha_expected:
            raise ValueError(f"original SHA mismatches year {year}")
        cnt = 0
        prev = None
        first = last = None
        with path.open("r", encoding="utf-8") as h:
            for line in h:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("canonical_symbol") != symbol or row.get("provider_symbol") != provider:
                    raise ValueError("row symbol provenance mismatch")
                if row.get("provider_symbol_id") != manifest["provider_symbol_id"]:
                    raise ValueError("row provider ID mismatch")
                minute = row.get("utc_timestamp_in_minutes")
                if type(minute) is not int or minute <= 0 or minute % 5:
                    raise ValueError("bad native M5 timestamp")
                if prev is not None and minute <= prev:
                    raise ValueError("non-monotone/duplicated M5")
                t = datetime.fromtimestamp(minute * 60, UTC)
                if t.year != year or not (START <= t < END):
                    raise ValueError("partition outside requested year")
                first = t if cnt == 0 else first
                prev, last = minute, t
                cnt += 1
        if cnt < 50000:
            raise ValueError(f"year {year} has too few M5: {cnt}")
        counts[str(year)] = cnt
        output["years"][str(year)] = {
            "partition_sha256_verified": True,
            "rows": cnt,
            "first_utc": first.isoformat() if first else None,
            "last_utc": last.isoformat() if last else None,
        }
    output["total_m5"] = sum(counts.values())
    output["status"] = "SOURCE_YEARS_SHA_OK_NOT_PINE_PARITY"
    return output


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--cohort", required=True)
    args = p.parse_args()
    result = inspect(args.root, args.symbol, args.cohort)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
