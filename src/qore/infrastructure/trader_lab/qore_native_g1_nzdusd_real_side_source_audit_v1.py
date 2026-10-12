"""Independent NZDUSD cTrader native BID/ASK side source integrity (NO NET).

Consumes only exact original research artifact extracted by GitHub Actions. No
broker secrets, orders, OHLC returns, strategy labels, fills or fee inference.
This is post-acquisition SOURCE QA, not another independent alpha experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "QORE_NATIVE_G1_NZDUSD_REAL_SIDE_SOURCE_QA_V1"
SOURCE_RUN = 38279593236
SOURCE_ARTIFACT = 11760547215
SOURCE_HEAD = "ef69b1b6ea2dbbd689bc3e090f9581e15bbb7ad6"
SOURCE_ZIP_SHA256 = "e593ba684ae7073968371f4fa1d00673ce773e71a5fab000c80a672fbc33a64d"
SOURCE_G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
SOURCE_MANIFEST = "native-quote-source-PILOT-NOT-NET.json"
MAX_ASOF_AGE_MS = 5000
MICRO_PRICE_SCALE = Decimal(100000)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _readjson(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("source manifest not JSON object")
    return value


def _parse_source_sha(folder: Path) -> dict[str, str]:
    register = folder / "OUTPUT_SHA256SUMS.txt"
    if not register.is_file():
        raise ValueError("source SHA scope is absent")
    sha_rows: dict[str, str] = {}
    for line in register.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or len(fields[0]) != 64:
            raise ValueError("malformed source SHA witness")
        digest, name = fields
        if name in sha_rows or Path(name).name != name or name == "OUTPUT_SHA256SUMS.txt":
            raise ValueError("duplicate or unsafe source SHA file entry")
        if not all(x in "0123456789abcdef" for x in digest):
            raise ValueError("invalid SHA256 witness")
        sha_rows[name] = digest
    expected_files = {p.name for p in folder.iterdir() if p.is_file()} - {register.name}
    if set(sha_rows) != expected_files or len(expected_files) != 13:
        raise ValueError("unaccounted/extra side stream source files")
    for filename, expected in sha_rows.items():
        if sha((folder / filename).read_bytes()) != expected:
            raise ValueError("tampered source side stream or manifest")
    return sha_rows


def _time_ms(s: str) -> int:
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ValueError("source needs UTC event clock")
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo != UTC:
        raise ValueError("source clock not UTC")
    return int(dt.timestamp() * 1000)


def _read_side(
    folder: Path, meta: dict[str, Any], idx: int, side: str, start: int, end: int
) -> tuple[list[tuple[int, int]], int]:
    native_name = f"nzdusd-{idx}-{side}-integer.jsonl"
    decoded_name = f"nzdusd-{idx}-{side}-decoded.jsonl"
    if meta.get("native_int_file") != native_name or meta.get("decoded_file") != decoded_name:
        raise ValueError("source symbol, window or side name drift")
    raw_native = (folder / native_name).read_bytes()
    raw_decoded = (folder / decoded_name).read_bytes()
    if sha(raw_native) != meta.get("native_int_sha256") or sha(raw_decoded) != meta.get("decoded_sha256"):
        raise ValueError("source native/decoded SHA mismatch")
    native = [json.loads(x) for x in raw_native.splitlines()]
    normalized = [json.loads(x) for x in raw_decoded.splitlines()]
    if len(native) != meta.get("native_tick_count") or len(native) != len(normalized) or not native:
        raise ValueError("source native/decoded side row count mismatch or empty")
    if not (1 <= meta.get("historical_provider_requests", 0) <= 64):
        raise ValueError("provider pagination budget not attested")
    output: list[tuple[int, int]] = []
    equal_ms = 0
    for pos, (a, b) in enumerate(zip(native, normalized, strict=True)):
        at, value = a.get("epoch_ms"), a.get("integer_price_1e5")
        if type(at) is not int or type(value) is not int or not start <= at < end or value <= 0:
            raise ValueError("source native tick invalid or outside frozen interval")
        if b.get("native_sequence") != pos or _time_ms(b.get("event_time_utc")) != at:
            raise ValueError("source normalized event clock/sequence not native-equal")
        if Decimal(str(b.get("price"))) != Decimal(value) / MICRO_PRICE_SCALE:
            raise ValueError("source normalized decimal not native integer equal")
        if output and at < output[-1][0]:
            raise ValueError("source side chronology not monotonically ascending")
        if output and at == output[-1][0]:
            equal_ms += 1
            if value != output[-1][1]:
                raise ValueError("AMBIGUOUS_NATIVE_SAME_MILLISECOND_DIFFERENT_PRICES")
        output.append((at, value))
    return output, equal_ms


def _pct(sorted_values: list[Decimal], fraction: Decimal) -> Decimal:
    return sorted_values[max(0, math.ceil(len(sorted_values) * float(fraction)) - 1)]


def _round(v: Decimal) -> float:
    return round(float(v), 6)


def asof_spot_quality(
    bid: list[tuple[int, int]], ask: list[tuple[int, int]], *, max_age_ms: int = MAX_ASOF_AGE_MS
) -> dict[str, Any]:
    """Join *only last known* side at the same/prior event clock; no fills or NET."""
    if not bid or not ask or type(max_age_ms) is not int or max_age_ms <= 0:
        raise ValueError("both sides and positive staleness limit mandatory")
    times = sorted({t for t, _ in bid} | {t for t, _ in ask})
    i = j = 0
    last_bid: tuple[int, int] | None = None
    last_ask: tuple[int, int] | None = None
    missing, stale, zero, crossed = 0, 0, 0, 0
    spreads: list[Decimal] = []
    for decision in times:
        while i < len(bid) and bid[i][0] <= decision:
            last_bid = bid[i]
            i += 1
        while j < len(ask) and ask[j][0] <= decision:
            last_ask = ask[j]
            j += 1
        if last_bid is None or last_ask is None:
            missing += 1
            continue
        if decision - last_bid[0] > max_age_ms or decision - last_ask[0] > max_age_ms:
            stale += 1
            continue
        b, a = last_bid[1], last_ask[1]
        if a < b:
            crossed += 1
        elif a == b:
            zero += 1
        else:
            spreads.append(Decimal(20000) * Decimal(a - b) / Decimal(a + b))
    spreads.sort()
    if missing + stale + crossed + zero + len(spreads) != len(times):
        raise ValueError("spot quality partitions do not reconcile")
    return {
        "combined_distinct_source_instants": len(times),
        "incomplete_one_side": missing,
        "stale_side_quarantined": stale,
        "crossed_quote_quarantined": crossed,
        "zero_spread_quarantined_not_free": zero,
        "positive_spread_source_snapshots": len(spreads),
        "positive_spread_median_bps": _round(Decimal(statistics.median(spreads))) if spreads else None,
        "positive_spread_p95_bps": _round(_pct(spreads, Decimal(".95"))) if spreads else None,
        "positive_spread_max_bps": _round(spreads[-1]) if spreads else None,
        "NET_execution_cost_measured": False,
    }


def audit(folder: Path) -> dict[str, Any]:
    signed = _parse_source_sha(folder)
    source = _readjson(folder / SOURCE_MANIFEST)
    if (
        source.get("identity") != "QORE_NATIVE_ICMARKETS_G1_PRE_NZDUSD_NATIVE_TICKS_V1"
        or source.get("source_g0_sha256") != SOURCE_G0_SHA
        or source.get("source_m1_provenance_run") != 38262534602
        or source.get("symbol") != "NZDUSD"
        or source.get("verified_provider_symbol") != "NZDUSD"
        or source.get("provider") != "ICMARKETS_CTRADER_DEMO"
        or source.get("status") != "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
        or source.get("complete_bid_ask_windows") != 3
        or source.get("historical_NET_authorized") is not False
        or source.get("original_side_protobuf_attested_independently") is not False
        or source.get("historical_33_market_coverage_verified") is not False
        or source.get("trading_orders_submitted") != 0
        or source.get("token_refresh_attempts") != 0
        or source.get("traders_certified") != 0
    ):
        raise ValueError("source G1 native quote identity or safety state invalid")
    windows = source.get("windows")
    frozen = source.get("windows_frozen_utc")
    if not isinstance(windows, list) or len(windows) != 3 or len(frozen) != 3:
        raise ValueError("3 predeclared source windows must remain exact")
    results = []
    all_bid = all_ask = 0
    for idx, w in enumerate(windows, 1):
        if w.get("utc_range") != frozen[idx - 1] or w.get("both_sides_nonempty") is not True:
            raise ValueError("native timestamp range selection drift")
        start = int(datetime.fromisoformat(frozen[idx - 1][0]).timestamp() * 1000)
        end = int(datetime.fromisoformat(frozen[idx - 1][1]).timestamp() * 1000)
        bid, ties_bid = _read_side(folder, w["by_side"]["BID"], idx, "BID", start, end)
        ask, ties_ask = _read_side(folder, w["by_side"]["ASK"], idx, "ASK", start, end)
        all_bid += len(bid)
        all_ask += len(ask)
        result = asof_spot_quality(bid, ask)
        result.update({
            "source_window_utc": frozen[idx - 1],
            "source_bid_events": len(bid),
            "source_ask_events": len(ask),
            "identical_native_same_ms_bid": ties_bid,
            "identical_native_same_ms_ask": ties_ask,
        })
        results.append(result)
    return {
        "identity": IDENTITY,
        "status": "THREE_REAL_QUOTE_SOURCE_WINDOWS_SHA_AND_ASOF_QA_NO_NET",
        "source_run": SOURCE_RUN,
        "source_artifact_id": SOURCE_ARTIFACT,
        "source_head_sha": SOURCE_HEAD,
        "source_original_zip_expected_sha256": SOURCE_ZIP_SHA256,
        "source_zip_bytes_revalidated_here": False,
        "source_extracted_13_files_SHA_verified": len(signed),
        "source_original_manifest_sha256": signed[SOURCE_MANIFEST],
        "markets_tested": 1,
        "source_bid_ticks": all_bid,
        "source_ask_ticks": all_ask,
        "source_total_native_ticks": all_bid + all_ask,
        "window_quality": results,
        "historical_33_coverage_proven": False,
        "source_same_contract_as_original12_G0_proven": False,
        "historical_NET_authorized": False,
        "profit_factor_sharpe_sortino_drawdown_measured": False,
        "certified_traders": 0,
        "production_untouched": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("extracted_original_artifact_dir", type=Path)
    p.add_argument("out_dir", type=Path)
    args = p.parse_args()
    out = audit(args.extracted_original_artifact_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    file = args.out_dir / "source-qa-three-windows-nzdusd-NOT-NET.json"
    file.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "SHA256SUMS.txt").write_text(
        sha(file.read_bytes()) + "  " + file.name + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": out["status"], "total_ticks": out["source_total_native_ticks"],
        "windows": [{"bid": w["source_bid_events"], "ask": w["source_ask_events"],
                     "positive": w["positive_spread_source_snapshots"],
                     "zero_quarantined": w["zero_spread_quarantined_not_free"]}
                    for w in out["window_quality"]],
        "NET": False, "traders_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
