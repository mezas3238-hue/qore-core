"""Verify exact immutable QORE CRT RADAR PRO R4-A Pine source bytes.

This does not certify runtime parity or strategy profitability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_BLOB = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
EXPECTED_MIN_BYTES = 200_000
EXPECTED_MAX_BYTES = 240_000
PINE_MARKERS = (
    "f_engine() =>",
    "f_engine_snapshot() =>",
    "barstate.islast ? state : na",
    "qaTrue3CConfirmed",
    "CRT_2C_RETURN",
    "qaNativeSourcePhaseMin",
    "bool validIndependent15 =",
    "qaCatalogMask",
    "bool extraMss5Causal =",
)


def git_blob_sha(contents: bytes) -> str:
    header = b"blob " + str(len(contents)).encode() + b"\0"
    return hashlib.sha1(header + contents).hexdigest()


def inspect(path: Path) -> dict[str, object]:
    blob = path.read_bytes()
    observed = git_blob_sha(blob)
    if observed != EXPECTED_BLOB:
        raise ValueError(f"R4-A PIN MISMATCH: {observed} != {EXPECTED_BLOB}")
    if not EXPECTED_MIN_BYTES <= len(blob) <= EXPECTED_MAX_BYTES:
        raise ValueError("R4-A SOURCE SIZE OUTSIDE EXPECTED LIMITS")
    code = blob.decode("utf-8")
    if any(marker not in code for marker in PINE_MARKERS):
        raise ValueError("required R4-A detector markers missing or ambiguous")
    if code.count("f_engine() =>") != 1:
        raise ValueError("source does not contain unique R4-A engine")
    engine = code.split("f_engine() =>", 1)[1].split(
        "f_engine_snapshot() =>", 1
    )[0]
    if not engine.strip():
        raise ValueError("R4-A engine empty")
    return {
        "status": "EXACT_R4_A_SOURCE_VERIFIED",
        "pin_sha1_git_blob": EXPECTED_BLOB,
        "source_bytes": len(blob),
        "source_lines": len(code.splitlines()),
        "engine_sha256": hashlib.sha256(engine.encode("utf-8")).hexdigest(),
        "instrument_count_expected": 34,
        "parity_certified": False,
        "holdout_certified": False,
        "trading_orders_permitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pine", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    result = inspect(a.pine)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
