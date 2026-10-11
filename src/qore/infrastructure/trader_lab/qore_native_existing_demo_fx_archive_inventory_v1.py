"""Read-only inventory of the already-acquired DEMO 7Y FX archives.

This module reads only source metadata before the huge OHLC arrays. It does not
inspect market outcomes, produce signals, or change holdout status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 36079229139
SOURCE_COMMIT = "6958ea0c4f183020b5248b413af998065c6662da"
SOURCE_SCOPE = "VT08_COGNITIVE_EXPANSION_M3_UNSEEN_VALIDATION"
SYMBOLS = ("EURJPY", "USDCHF")
IDENTITY = "QORE_NATIVE_VERIFIED_CTRADER_DEMO_7Y_EXISTING_FX_ARCHIVE_V1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def metadata_prefix(path: Path) -> dict[str, Any]:
    """Parse metadata prefix only; do not load or scan retained market observations."""
    with path.open(encoding="utf-8") as stream:
        prefix = stream.read(16_384)
    delimiter = ',"periods":{'
    position = prefix.find(delimiter)
    if position < 0:
        raise ValueError("7Y provider archive metadata prefix missing/oversized")
    data = json.loads(prefix[:position] + "}")
    if not isinstance(data, dict):
        raise ValueError("7Y archive metadata must be an object")
    return data


def build_inventory(symbol: str, base_file: Path) -> dict[str, Any]:
    if symbol not in SYMBOLS:
        raise ValueError("only preregistered EURJPY/USDCHF permitted")
    if not base_file.is_file():
        raise ValueError("existing archive RAW source missing")
    raw = metadata_prefix(base_file)
    if raw.get("environment") != "demo" or raw.get("account_is_live") is not False:
        raise ValueError("not independently identified as DEMO historical archive")
    if raw.get("account_discovered") is not True:
        raise ValueError("account discovery not verified in original capture")
    if raw.get("intended_future_use") != SOURCE_SCOPE:
        raise ValueError("archive reserved use does not match signed source")
    coverage = raw.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("original source coverage missing")
    for period in ("M1", "M5", "M15", "H4"):
        entry = coverage.get(period)
        if not isinstance(entry, dict) or type(entry.get("bar_count")) is not int:
            raise ValueError(f"source {period} bar count unavailable")
        if entry["bar_count"] <= 0:
            raise ValueError(f"no verified {period} coverage")
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_run_id": SOURCE_RUN_ID,
        "source_commit": SOURCE_COMMIT,
        "source_artifact": f"qore-vt08-expansion-7y-{symbol}-{SOURCE_COMMIT}",
        "source_sha256": sha256_file(base_file),
        "account_is_live": False,
        "environment": "demo",
        "coverage": coverage,
        "research_archive_existing": True,
        "original_reserved_scope": SOURCE_SCOPE,
        "research_pnl_computed": False,
        "virgin_oos_claimed": False,
        "capture_repeated": False,
        "cTrader_auth_required_for_reuse": False,
        "broker_identity_not_rediscovered": True,
        "admission_to_new_trader_not_authorized": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=SYMBOLS)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = build_inventory(args.symbol, args.root / "raw-7y-base.json")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"symbol": args.symbol, "status": "EXISTING_DEMO_ARCHIVE_VERIFIED",
                      "M5_bars": payload["coverage"]["M5"]["bar_count"],
                      "M1_bars": payload["coverage"]["M1"]["bar_count"]}))


if __name__ == "__main__":
    main()
