"""Second audit of actual USTEC BID/ASK source; NAS100 contract NOT homologated."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_g1_ustec_candidate_bidask_v1 import (
    IDENTITY as SOURCE_IDENTITY,
    USTEC_PINNED_SYMBOL_ID,
    WINDOWS,
)

IDENTITY = "QORE_NATIVE_G1_USTEC_REAL_SOURCE_INDEPENDENT_QA_ALIAS_UNVERIFIED_V1"
SOURCE_RUN = 38285063753
SOURCE_ARTIFACT = 11762668603
SOURCE_SHA = "1626667cb8a2ac40702a021e8422d9fdec252e75"
ZIP_DIGEST = "402831fcf2ba60070bdcf92671a1470838bda44208bf40ff373d95dc066c5da4"
AGE_MS = 5000


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ms(text: Any) -> int:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise ValueError("SOURCE_UTC_REQUIRED")
    at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if at.tzinfo != UTC:
        raise ValueError("SOURCE_UTC_INVALID")
    return int(at.timestamp() * 1000)


def _files(folder: Path) -> dict[str, str]:
    witness = folder / "SHA256SUMS.txt"
    if not witness.is_file():
        raise ValueError("SOURCE_SHA_REGISTER_MISSING")
    rows = witness.read_text().splitlines()
    if len(rows) != 13:
        raise ValueError("SOURCE_SHA_REGISTER_COUNT_MISMATCH")
    record: dict[str, str] = {}
    for line in rows:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError("SOURCE_SHA_ENTRY_INVALID")
        digest, name = parts
        if (len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
                or name in record or Path(name).name != name):
            raise ValueError("SOURCE_SHA_ENTRY_UNSAFE")
        record[name] = digest
    if set(record) != {x.name for x in folder.iterdir() if x.is_file()} - {witness.name}:
        raise ValueError("SOURCE_FILE_SET_CHANGED")
    if any(_sha((folder / name).read_bytes()) != digest for name, digest in record.items()):
        raise ValueError("SOURCE_BYTES_SHA_MISMATCH")
    return record


def _side(folder: Path, meta: dict, number: int, side: str,
          start: int, end: int) -> list[tuple[int, int]]:
    prefix = f"USTEC-{number}-{side}"
    native = prefix + "-integer.jsonl"
    decoded = prefix + "-decoded.jsonl"
    if meta.get("integer_file") != native or meta.get("decoded_file") != decoded:
        raise ValueError("SOURCE_SIDE_FILE_DRIFT")
    nr = (folder / native).read_bytes()
    dr = (folder / decoded).read_bytes()
    if _sha(nr) != meta.get("integer_sha256") or _sha(dr) != meta.get("decoded_sha256"):
        raise ValueError("SOURCE_SIDE_HASH_DRIFT")
    nrows = [json.loads(line) for line in nr.splitlines()]
    drows = [json.loads(line) for line in dr.splitlines()]
    if not nrows or len(nrows) != len(drows) or len(nrows) != meta.get("count"):
        raise ValueError("SOURCE_SIDE_COUNT_INVALID")
    count = meta.get("requests")
    if type(count) is not int or not 1 <= count <= 64:
        raise ValueError("SOURCE_HASMORE_WITNESS_INVALID")
    output = []
    for index, (x, y) in enumerate(zip(nrows, drows, strict=True)):
        ts, px = x.get("epoch_ms"), x.get("integer_price_1e5")
        if type(ts) is not int or type(px) is not int or not start <= ts < end or px <= 0:
            raise ValueError("SOURCE_INTEGER_TICK_INVALID")
        if _ms(y.get("event_time_utc")) != ts or y.get("native_sequence") != index:
            raise ValueError("SOURCE_DECODED_TIME_SEQUENCE_DRIFT")
        if Decimal(str(y.get("price"))) != Decimal(px) / Decimal(100000):
            raise ValueError("SOURCE_DECODED_PRICE_MISMATCH")
        if output and ts < output[-1][0]:
            raise ValueError("SOURCE_SIDE_TIME_INVERTED")
        if output and ts == output[-1][0] and px != output[-1][1]:
            raise ValueError("SOURCE_SAME_MS_AMBIGUOUS_PRICE_SEQUENCE")
        output.append((ts, px))
    return output


def asof_qa(bids: list[tuple[int, int]], asks: list[tuple[int, int]]) -> dict[str, int]:
    if not bids or not asks:
        raise ValueError("SOURCE_BOTH_SIDES_REQUIRED")
    i = j = 0
    b = a = None
    counts: Counter[str] = Counter()
    instants = sorted({x[0] for x in bids} | {x[0] for x in asks})
    for t in instants:
        while i < len(bids) and bids[i][0] <= t:
            b = bids[i]
            i += 1
        while j < len(asks) and asks[j][0] <= t:
            a = asks[j]
            j += 1
        if b is None or a is None:
            counts["missing_side"] += 1
        elif t - b[0] > AGE_MS or t - a[0] > AGE_MS:
            counts["stale_side"] += 1
        elif a[1] < b[1]:
            counts["crossed_spread"] += 1
        elif a[1] == b[1]:
            counts["zero_spread"] += 1
        else:
            counts["positive_spread"] += 1
    keys = ("missing_side", "stale_side", "crossed_spread", "zero_spread", "positive_spread")
    r = {key: counts[key] for key in keys}
    if sum(r.values()) != len(instants):
        raise ValueError("SOURCE_ASOF_QA_COUNTERS_NOT_EXHAUSTIVE")
    return r


def audit(folder: Path) -> dict[str, Any]:
    verified = _files(folder)
    manifest = json.loads((folder / "USTEC-CANDIDATE-SOURCE-NOT-NET.json").read_bytes())
    if (
        manifest.get("identity") != SOURCE_IDENTITY
        or manifest.get("canonical_alias_candidate") != "NAS100"
        or manifest.get("actual_provider_symbol") != "USTEC"
        or manifest.get("provider") != "ICMARKETS_CTRADER_DEMO"
        or manifest.get("provider_symbol_id_pinned") != USTEC_PINNED_SYMBOL_ID
        or manifest.get("current_symbol_id_exact_match") is not True
        or manifest.get("source_state") != "USTEC_SOURCE_THREE_WINDOWS_AVAILABLE_ALIAS_UNVERIFIED_NOT_NET"
        or manifest.get("windows_frozen_utc") != [list(x) for x in WINDOWS]
        or manifest.get("complete_windows") != 3
        or manifest.get("nas100_original_CIBO_contract_equivalence_verified") is not False
        or manifest.get("historical_NET_authorized") is not False
        or manifest.get("certified_traders") != 0
        or manifest.get("order_submission_count") != 0
        or manifest.get("oauth_refresh_count") != 0
    ):
        raise ValueError("SOURCE_ALIAS_SCIENTIFIC_SCOPE_INVALID")
    windows = manifest.get("windows")
    if not isinstance(windows, list) or len(windows) != 3:
        raise ValueError("SOURCE_FROZEN_WINDOW_COUNT_INVALID")
    summaries = []
    for i, (entry, w) in enumerate(zip(windows, WINDOWS, strict=True), 1):
        if entry.get("utc_range") != list(w) or entry.get("both_nonempty") is not True:
            raise ValueError("SOURCE_FROZEN_WINDOW_CLOCK_DRIFT")
        start = int(datetime.fromisoformat(w[0]).timestamp() * 1000)
        end = int(datetime.fromisoformat(w[1]).timestamp() * 1000)
        bid = _side(folder, entry["by_side"]["BID"], i, "BID", start, end)
        ask = _side(folder, entry["by_side"]["ASK"], i, "ASK", start, end)
        summaries.append({
            "window": i, "bid": len(bid), "ask": len(ask),
            "asof_qa": asof_qa(bid, ask),
        })
    return {
        "identity": IDENTITY, "status": "USTEC_REAL_SOURCE_SHA_ASOF_PASS_ALIAS_UNVERIFIED_NO_NET",
        "source_artifact_id": SOURCE_ARTIFACT, "source_run": SOURCE_RUN,
        "original_source_head_sha": SOURCE_SHA, "source_zip_sha256_expected": ZIP_DIGEST,
        "source_file_sha_verified": len(verified),
        "source_bid_ticks": sum(x["bid"] for x in summaries),
        "source_ask_ticks": sum(x["ask"] for x in summaries),
        "quality": summaries,
        "original_NAS100_contract_equivalence_verified": False,
        "historical_10y_tick_coverage_proven": False,
        "historical_NET_authorized": False, "certified_traders": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_source", type=Path)
    p.add_argument("output_dir", type=Path)
    args = p.parse_args()
    r = audit(args.original_source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    file = args.output_dir / "USTEC-ALIAS-CANDIDATE-QA-NOT-NET.json"
    file.write_text(json.dumps(r, sort_keys=True, indent=2) + "\n")
    (args.output_dir / "SHA256SUMS.txt").write_text(_sha(file.read_bytes())+"  "+file.name+"\n")
    print(json.dumps({
        "source_only_alias_candidate": "USTEC",
        "bid": r["source_bid_ticks"], "ask": r["source_ask_ticks"],
        "asof_quality": [w["asof_qa"] for w in r["quality"]],
        "NET_authorized": False, "certified_traders": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
