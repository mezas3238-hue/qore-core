"""R8 SHA-verified original Atlas producer quality-gap witness (research-only).

No price outcomes, filling missing bars, trades, PnL, risk or sizing. Original
producer's market_open_expected=None cannot certify a broker weekly schedule.
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    PRODUCER_IDENTITY,
    PRODUCER_SHA,
    _ledger,
    _verified,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt.original_atlas_producer_quality_custody.r8.v1"
ORIGINAL_QUALITY_SCHEMA = "qore.cibo_market_atlas.data_quality.v1"
GAP_KIND = "UNRESOLVED_CLOSURE_OR_MISSING_DATA"
M5 = timedelta(minutes=5)
FROZEN_GAPS: dict[CrtPureMarket, dict[str, str]] = {
    CrtPureMarket.AUDUSD: {
        "2025-04-25T21:00:00+00:00": "bfc66b2457f3e3ec93ae",
    },
    CrtPureMarket.USDJPY: {
        "2025-02-12T22:30:00+00:00": "11a7c3cdb30a9eabdbbe",
        "2026-06-19T21:00:00+00:00": "a63b7073af8d33e8963a",
    },
}


def _clock(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("original quality gap clock missing")
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("original quality gap clock timezone missing")
    return stamp.astimezone(UTC)


def audit_original_producer_quality_gaps(
    market: CrtPureMarket,
    original_atlas_root: Path,
    source_m5: tuple[ReplayBar, ...],
    r7_gap_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Require independent original producer gap witness for all R7 missing M5.

    Caller must first invoke load_atlas_vt08_m5: it independently verifies the
    raw, quality and manifest SHA chain. Here we recheck quality before reading.
    """
    if market not in FROZEN_GAPS:
        raise ValueError("market outside frozen original Atlas source")
    targets = FROZEN_GAPS[market]
    if {
        row["original_m5_missing_at_utc"]: row["source_event_id"]
        for row in r7_gap_rows
    } != targets or len(r7_gap_rows) != len(targets):
        raise ValueError("R7 producer/source identity or gap count mismatch")
    stamps = sorted(bar.opened_at.astimezone(UTC) for bar in source_m5)
    if len(set(stamps)) != len(stamps) or not stamps:
        raise ValueError("original M5 chronology invalid")
    manifest_sha = _ledger(original_atlas_root / "MANIFEST_SHA256SUMS.txt")
    results: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    evidence_quality_files: dict[str, dict[str, str]] = {}

    for raw_missing, event_id in sorted(targets.items()):
        missing = _clock(raw_missing)
        year = str(missing.year)
        if year not in evidence_quality_files:
            partition_checksum_file = _verified(
                original_atlas_root, manifest_sha, f"PARTITION_MANIFEST/{year}.sha256"
            )
            annual = _ledger(partition_checksum_file)
            quality_name = f"DATA_QUALITY_LEDGER/{year}.jsonl"
            quality_file = _verified(original_atlas_root, annual, quality_name)
            # Records' year quality file is SHA-backed by published annual ledger.
            evidence_quality_files[year] = {
                "file": str(quality_file),
                "sha": annual[quality_name],
            }
        quality_file = Path(evidence_quality_files[year]["file"])
        pos = bisect_left(stamps, missing)
        if pos == 0 or pos == len(stamps) or stamps[pos] == missing:
            raise ValueError("original M5 missing slot has no causal neighbor")
        earlier, later = stamps[pos - 1], stamps[pos]
        candidates: list[dict[str, Any]] = []
        with quality_file.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                if row.get("kind") != GAP_KIND:
                    continue
                start = _clock(row["gap_start"])
                end = _clock(row["gap_end_exclusive"])
                if start <= missing < end:
                    candidates.append(row)
        if len(candidates) != 1:
            raise ValueError("original producer quality ledger absent or ambiguous")
        witness = candidates[0]
        if (
            witness.get("schema") != ORIGINAL_QUALITY_SCHEMA
            or witness.get("identity") != PRODUCER_IDENTITY
            or witness.get("canonical_symbol") != market.value
            or witness.get("kind") != GAP_KIND
            or witness.get("outcome_only") is not False
            or witness.get("market_open_expected") is not None
            or _clock(witness["previous_bar_at"]) != earlier
            or _clock(witness["next_bar_at"]) != later
            or _clock(witness["gap_start"]) != earlier + M5
            or _clock(witness["gap_end_exclusive"]) != later
            or type(witness.get("calendar_slots_without_bars")) is not int
            or witness["calendar_slots_without_bars"] != (later - earlier) // M5 - 1
            or (later - earlier) % M5 != timedelta()
        ):
            raise ValueError("original producer gap incompatible with raw M5 ledger")
        expected_weekend = any(
            (earlier + M5 + i * timedelta(days=1)).weekday() >= 5
            for i in range((later - earlier).days + 2)
            if earlier + M5 + i * timedelta(days=1) <= later
        )
        if witness.get("spans_weekend") is not expected_weekend:
            raise ValueError("producer gap weekend marker contradicts interval")
        midweek = missing.weekday() == 2
        if midweek and not (
            earlier == missing - M5
            and later == missing + M5
            and witness["calendar_slots_without_bars"] == 1
            and not witness["spans_weekend"]
        ):
            raise ValueError("isolated midweek source M5 gap not single-slot")
        canonical = json.dumps(
            witness, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        record = {
            "schema": SCHEMA,
            "market": market.value,
            "source_event_id": event_id,
            "missing_original_m5_opened_at_utc": missing.isoformat(),
            "producer_quality_kind": witness["kind"],
            "producer_quality_record_sha256": hashlib.sha256(canonical).hexdigest(),
            "producer_quality_annual_ledger_sha256": evidence_quality_files[year]["sha"],
            "producer_sha": PRODUCER_SHA,
            "producer_gap_previous_m5_utc": earlier.isoformat(),
            "producer_gap_next_m5_utc": later.isoformat(),
            "producer_calendar_slots_without_bars": witness["calendar_slots_without_bars"],
            "producer_spans_weekend": witness["spans_weekend"],
            "producer_market_open_expected": None,
            "quality_ledger_sha_verified": True,
            "broker_historical_calendar_authenticated": False,
            "underlying_missing_m5_recovered": False,
            "source_GM4_terminal_still_UNKNOWN": True,
            "terminal_adjudicated": False,
            "G_M4_PASS": False,
            "G_M5_ISSUED": False,
            "GLOBAL_CERTIFIED": False,
            "not_a_trade": True,
            "no_sizing": True,
        }
        results.append(record)
        counts["PRODUCER_GAP_WITNESSED"] += 1
        counts["PRODUCER_GAP_SPANS_WEEKEND"] += int(witness["spans_weekend"])
        counts["PRODUCER_ONE_M5_INTERIOR_GAP"] += int(midweek)

    return {
        "schema": SCHEMA, "market": market.value,
        "original_m5": len(source_m5),
        "original_gap_cases_matched": len(results),
        "counts": dict(sorted(counts.items())),
        "source_producer_sha": PRODUCER_SHA,
        "quality_ledger_sha_verified": True,
        "broker_historical_calendar_authenticated": False,
        "underlying_missing_m5_recovered": False,
        "GM4_UNKNOWN_STILL_NOT_TERMINAL": True,
        "G_M4_PASS": False, "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False, "not_a_trade": True,
        "no_sizing": True, "no_orders": True,
    }, tuple(results)
