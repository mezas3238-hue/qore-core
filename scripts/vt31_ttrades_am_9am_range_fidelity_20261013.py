#!/usr/bin/env python3
"""Source-only TTrades 2025 NY-AM fidelity census against frozen old VT31 candidates.

NO economic replay: checks only 09:00 H1 prior-high/low raids before FVG,
directional reversal, and opposite target identity. Never backtests this as a
new strategy; NAS100 CFD OHLC != TTrades NQ futures price series.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
MARKET_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
SOURCE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
MARKET_ARTIFACT = 11459859004
LEDGER_ARTIFACT = 11657461650
OLD_TOTAL = 2140
AM_TOTAL = 721
TOTAL_M1 = 1059784


def utc_stamp(v: str) -> datetime:
    dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(UTC)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(2**20):
            h.update(chunk)
    return h.hexdigest()


def select_am_events(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if (
        ledger.get("source_fvg_hypothesis_count") != OLD_TOTAL
        or ledger.get("market_m1_count") != TOTAL_M1
        or ledger.get("trader_id") != "VT31"
        or ledger.get("paper_fills_proven") != 0
        or ledger.get("live_fills_proven") != 0
    ):
        raise ValueError("old source-identity contract broken")
    entries = ledger.get("events")
    if not isinstance(entries, list) or len(entries) != OLD_TOTAL:
        raise ValueError("original 2140 events required")
    ids: set[str] = set()
    selected = []
    for x in entries:
        ident = x["client_order_id"]
        if ident in ids or not isinstance(ident, str):
            raise ValueError("duplicate event identity")
        ids.add(ident)
        if x["session_window"] != "VT31_NY_AM":
            continue
        formed = utc_stamp(x["formed_at"])
        c1 = utc_stamp(x["source_first_m1_open"])
        local = formed.astimezone(NY)
        if formed - c1 != timedelta(minutes=3) or local.hour != 10:
            raise ValueError("bad NY AM formation chronology")
        side = x["side"]
        if side not in ("LONG", "SHORT"):
            raise ValueError("bad side")
        selected.append({
            "id": ident,
            "day": local.date().isoformat(),
            "formed": formed,
            "c1": c1,
            "side": side,
            "old_dol": float(x["draw_target"]),
        })
    if len(selected) != AM_TOTAL:
        raise ValueError("expected exact 721 old NY AM candidates")
    return selected


def source_rows(path: Path) -> Iterable[dict[str, Any]]:
    import ijson
    with path.open("rb") as handle:
        for field, expected in (
            ("base_id", SOURCE_ID),
            ("market", "NAS100"),
            ("base_start_at", "2023-10-01T00:00:00+00:00"),
            ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
        ):
            handle.seek(0)
            if next(ijson.items(handle, field), None) != expected:
                raise ValueError(f"market provenance drift: {field}")
        handle.seek(0)
        yield from ijson.items(handle, "periods.M1.item")


def collect_9_10(
    rows: Iterable[dict[str, Any]], dates: set[str], *,
    expected: int = TOTAL_M1,
) -> dict[str, dict[str, list[tuple[datetime, float, float]]]]:
    days: dict[str, dict[str, list[tuple[datetime, float, float]]]] = defaultdict(
        lambda: {"nine": [], "ten": []}
    )
    prev = None
    total = 0
    for row in rows:
        start = utc_stamp(row["opened_at"])
        end = utc_stamp(row["closed_at"])
        if end - start != timedelta(minutes=1):
            raise ValueError("source contains non-M1")
        if prev is not None and start <= prev:
            raise ValueError("M1 source unsorted")
        prev = start
        total += 1
        local = start.astimezone(NY)
        day = local.date().isoformat()
        if day not in dates or local.hour not in (9, 10):
            continue
        hi, lo = float(row["high"]), float(row["low"])
        if not 1000 < lo <= hi < 1_000_000:
            raise ValueError("bad price bar")
        days[day]["nine" if local.hour == 9 else "ten"].append((start, hi, lo))
    if total != expected:
        raise ValueError("frozen M1 source count drift")
    return days


def full_9am_hour(
    bars: list[tuple[datetime, float, float]],
) -> tuple[float, float] | None:
    if len(bars) != 60:
        return None
    start = bars[0][0].astimezone(NY)
    if start.hour != 9 or start.minute != 0:
        return None
    if any(
        bars[k][0] != bars[0][0] + timedelta(minutes=k)
        for k in range(60)
    ):
        return None
    return (max(b[1] for b in bars), min(b[2] for b in bars))


def sweep_state(
    side: str, ref_hi: float, ref_lo: float,
    observed: list[tuple[datetime, float, float]],
) -> str:
    high = any(b[1] > ref_hi for b in observed)
    low = any(b[2] < ref_lo for b in observed)
    if high and low:
        return "BOTH_SIDES_AMBIGUOUS"
    if side == "LONG" and low and not high:
        return "DIRECTIONAL_CORRECT"
    if side == "SHORT" and high and not low:
        return "DIRECTIONAL_CORRECT"
    if high or low:
        return "WRONG_SIDE_ONLY"
    return "NO_SWEEP"


def evaluate(
    events: list[dict[str, Any]],
    by_day: dict[str, dict[str, list[tuple[datetime, float, float]]]],
) -> dict[str, Any]:
    if len(events) != AM_TOTAL:
        raise ValueError("wrong NY AM old population")
    stats = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for e in events:
        day = by_day.get(e["day"], {"nine": [], "ten": []})
        rng = full_9am_hour(day["nine"])
        if rng is None:
            stats["MISSING_COMPLETE_PRIOR_9AM_H1"] += 1
            continue
        hi, lo = rng
        stats["COMPLETE_9AM_REFERENCE"] += 1
        # C1=first gap candle. Before C1 is stricter than TTrades.
        before_c1 = [b for b in day["ten"] if b[0] < e["c1"]]
        # The source FVG only exists on C3 close. Exclude C3 intrabar.
        before_c3 = [
            b for b in day["ten"]
            if b[0] < e["c1"] + timedelta(minutes=2)
        ]
        until_signal = [b for b in day["ten"] if b[0] < e["formed"]]
        state_early = sweep_state(e["side"], hi, lo, before_c1)
        state_c3 = sweep_state(e["side"], hi, lo, before_c3)
        state_inclusive = sweep_state(e["side"], hi, lo, until_signal)
        stats["PRE_C1_" + state_early] += 1
        stats["PRE_C3_" + state_c3] += 1
        stats["THROUGH_C3_" + state_inclusive] += 1
        intended = hi if e["side"] == "LONG" else lo
        target_same = abs(e["old_dol"] - intended) <= 0.00000001
        if target_same:
            stats["OLD_DOL_EXACTLY_TTRADES_OPPOSITE_9AM_EXTREME"] += 1
        else:
            stats["OLD_DOL_DIFFERENT_FROM_TTRADES_TARGET"] += 1
        if state_c3 == "DIRECTIONAL_CORRECT":
            stats["PRE_C3_SWEEP_DIRECTION_ALIGNED"] += 1
            if target_same:
                stats["PRE_C3_SWEEP_AND_TARGET_BOTH_ALIGNED_UPPER_BOUND"] += 1
        if len(examples[state_c3]) < 3:
            examples[state_c3].append(e["id"])
    stats["OLD_NY_AM_TOTAL"] = len(events)
    if stats["COMPLETE_9AM_REFERENCE"] + stats[
        "MISSING_COMPLETE_PRIOR_9AM_H1"
    ] != len(events):
        raise ValueError("prior H1 census partition broken")
    for label in ("PRE_C1_", "PRE_C3_", "THROUGH_C3_"):
        if sum(
            stats[label + cat]
            for cat in (
                "BOTH_SIDES_AMBIGUOUS", "DIRECTIONAL_CORRECT",
                "WRONG_SIDE_ONLY", "NO_SWEEP",
            )
        ) != stats["COMPLETE_9AM_REFERENCE"]:
            raise ValueError("sweep census partition broken")
    return {
        "schema": "qore.vt31.ttrades_2025_nyam_doctrine_gap_census.v1",
        "not_ict_universal_and_not_new_g3_v1": True,
        "source": "old_2026_cleanroom_2140_source_only_first_fvg",
        "TTrades_2025_NY_AM_reference": (
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/"
        ),
        "complete_counts": dict(sorted(stats.items())),
        "examples_id_by_pre_C3_class_for_replay_manual_validation": dict(
            sorted(examples.items())
        ),
        "exclusion_of_C3_intrabar_for_preC3": True,
        "target_exact_identity_NOT_actual_FVG_entry_economics": True,
        "NQ_futures_equivalence_with_NAS100_CFD": "UNVERIFIED",
        "structural_confirmation_equivalence_with_TTrades": "UNVERIFIED",
        "market_execution_or_fills": 0,
        "PF_DD_edge": None,
        "G3_frozen": False,
        "holdout_opened": False,
        "no_LIVE": True,
    }


def selftest() -> None:
    start = datetime(2025, 4, 7, 13, 0, tzinfo=UTC)
    hour = [(start + timedelta(minutes=i), 105. + i/1000, 95.) for i in range(60)]
    assert full_9am_hour(hour) == (105.059, 95.)
    assert sweep_state("LONG", 105, 95, [(start, 104, 94)]) == "DIRECTIONAL_CORRECT"
    assert sweep_state("SHORT", 105, 95, [(start, 106, 96)]) == "DIRECTIONAL_CORRECT"
    assert sweep_state("LONG", 105, 95, [(start, 106, 94)]) == "BOTH_SIDES_AMBIGUOUS"
    assert sweep_state("LONG", 105, 95, [(start, 106, 96)]) == "WRONG_SIDE_ONLY"
    assert sweep_state("LONG", 105, 95, [(start, 104, 96)]) == "NO_SWEEP"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
        print("TTrades NY AM source conformance selftest PASS")
        return
    if args.market is None or args.ledger is None or args.out is None:
        parser.error("market + ledger + out required")
    if sha256(args.market) != MARKET_SHA:
        raise ValueError("frozen market source SHA256 mismatch")
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    entries = select_am_events(ledger)
    dates = {e["day"] for e in entries}
    data = collect_9_10(source_rows(args.market), dates)
    report = evaluate(entries, data)
    report["original_m1_sha256"] = MARKET_SHA
    report["original_ledger_sha256"] = sha256(args.ledger)
    report["original_m1_artifact"] = MARKET_ARTIFACT
    report["original_ledger_artifact"] = LEDGER_ARTIFACT
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["complete_counts"], sort_keys=True))


if __name__ == "__main__":
    main()
