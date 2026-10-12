"""QORE Native GROSS-04: one preregistered structural range sweep on all 33.

Read-only M5 source, G0 SHA audited before price access, strict 2024+ OHLC
embargo. Equal market weights and synchronized UTC-week cluster bootstrap.
No real BID/ASK, news-as-of, executable stops, paper/live or trader certification.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0
from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as new_source
from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as final33
from qore.infrastructure.trader_lab import qore_native_market33_source_census_v1 as census33

IDENTITY = "QORE_NATIVE_GROSS04_ALL33_SWEEP_RECLAIM_PANEL_V1"
PREREG_SHA = "9b147f0a385213dd4b0183b3205c6c9d467581ad"
PANEL_SOURCE_33_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
PANEL_SOURCE_33_CODE_SHA = "dba0e0c3b61e430d3ed51abab562ebd92060a0ff"
ORIGINAL_12_RUN = g0.SOURCE_RUN
NEW_21_RUN = new_source.NEW_SOURCE_RUN
START = date(2016, 9, 17)
DEV_END = date(2022, 9, 17)
EMBARGO_DATE = date(2024, 9, 17)
BLOCKS = {"PRE": (8, 48), "PROBE": (12, 12), "TARGET": (13, 24)}
MIN_EVENT_DEV = 40
MIN_EVENT_DIAG = 12
MIN_WEEKS_DEV = 12
MIN_WEEKS_DIAG = 6
BOOTSTRAP_COUNT = 2000
BOOTSTRAP_SEED = 20261012
BOOTSTRAP_NULL_CAP = 20
COSTS_RT_HYPOTHETICAL_BPS = (0, 1, 3, 5, 10, 20)
STATUS = "GROSS_PANEL_NEWS_UNFILTERED_NOT_TRADABLE"


def sign(x: int) -> int:
    return (x > 0) - (x < 0)


@dataclass(slots=True)
class ClockBlock:
    first_open: int
    last_close: int
    max_high: int
    min_low: int
    first_at: datetime
    last_at: datetime
    count: int = 1
    contiguous: bool = True

    def append(self, at: datetime, hi: int, lo: int, close: int) -> None:
        if at - self.last_at != timedelta(minutes=5):
            self.contiguous = False
        self.max_high = max(self.max_high, hi)
        self.min_low = min(self.min_low, lo)
        self.last_close = close
        self.last_at = at
        self.count += 1


def block_of_timestamp(at: datetime) -> str | None:
    if at.weekday() >= 5:
        return None
    if 8 <= at.hour < 12:
        return "PRE"
    if at.hour == 12:
        return "PROBE"
    if 13 <= at.hour < 15:
        return "TARGET"
    return None


def collect_blocks(root: Path, symbol: str, original: bool) -> tuple[dict[date, dict[str, ClockBlock]], dict[str, int]]:
    """Only reads price values from first 8 years; never from post-embargo."""
    expected_identity = g0.PRODUCER if original else new_source.NEW_CAPTURE_IDENTITY
    expected_schema = g0.RAW_SCHEMA if original else new_source.NEW_RAW_SCHEMA
    calendar: dict[date, dict[str, ClockBlock]] = {}
    prev: datetime | None = None
    counters = {
        "source_m5_timestamps_before_embargo": 0,
        "required_slot_m5_bars": 0,
        "weekday_with_any_required_slot": 0,
    }
    for year in range(2016, 2025):
        with (root / "RAW_M5_LEDGER" / f"{year}.jsonl").open(encoding="utf-8") as stream:
            for text in stream:
                row = json.loads(text)
                at = datetime.fromisoformat(row["opened_at"])
                if at.tzinfo is None or at.utcoffset() is None:
                    raise ValueError("source M5 naive UTC time")
                utc = at.astimezone(UTC)
                if utc.date() < START or utc.date() >= EMBARGO_DATE:
                    continue  # no 2024-09-17 or later OHLC values read
                if (prev is not None and utc <= prev) or utc.second or utc.microsecond or utc.minute % 5:
                    raise ValueError("original M5 chronological timestamp contract broken")
                prev = utc
                counters["source_m5_timestamps_before_embargo"] += 1
                slot = block_of_timestamp(utc)
                if slot is None:
                    continue
                if (row.get("schema") != expected_schema
                        or row.get("identity") != expected_identity
                        or row.get("canonical_symbol") != symbol
                        or (not original and row.get("provider_symbol") != symbol)
                        or any(type(row.get(k)) is not int for k in (
                            "open_relative", "close_relative", "high_relative", "low_relative"
                        ))):
                    raise ValueError("signed original M5 source identity or OHLC malformed")
                op, cl, hi, lo = (
                    row["open_relative"], row["close_relative"],
                    row["high_relative"], row["low_relative"],
                )
                if lo <= 0 or lo > min(op, cl) or hi < max(op, cl):
                    raise ValueError("signed source M5 OHLC prices not coherent")
                blocks = calendar.setdefault(utc.date(), {})
                if slot in blocks:
                    blocks[slot].append(utc, hi, lo, cl)
                else:
                    blocks[slot] = ClockBlock(op, cl, hi, lo, utc, utc)
                counters["required_slot_m5_bars"] += 1
    counters["weekday_with_any_required_slot"] = len(calendar)
    return calendar, counters


def valid_contiguous_three(day: date, blocks: dict[str, ClockBlock]) -> bool:
    for name, (hour, n) in BLOCKS.items():
        b = blocks.get(name)
        if b is None:
            return False
        start = datetime(day.year, day.month, day.day, hour, tzinfo=UTC)
        if (not b.contiguous or b.count != n or b.first_at != start
                or b.last_at != start + timedelta(minutes=(n - 1) * 5)):
            return False
    return True


def event_from_day(day: date, blocks: dict[str, ClockBlock]) -> tuple[dict[str, Any] | None, str]:
    if not valid_contiguous_three(day, blocks):
        return None, "INCOMPLETE_UTC_BLOCKS"
    pre = blocks["PRE"]
    probe = blocks["PROBE"]
    target = blocks["TARGET"]
    swept_high = probe.max_high > pre.max_high
    swept_low = probe.min_low < pre.min_low
    if swept_high == swept_low:
        return None, "BOTH_OR_NO_BREACH"
    if not pre.min_low <= probe.last_close <= pre.max_high:
        return None, "FAILED_RECLAIM"
    direction = -1 if swept_high else 1
    baseline = -sign(probe.last_close - probe.first_open)
    if baseline == 0:
        return None, "ZERO_BASELINE"
    if target.first_open <= 0:
        raise ValueError("nonpositive reference entry price")
    ret_bps = 10000 * (target.last_close - target.first_open) / target.first_open
    iso = day.isocalendar()
    return {
        "utc_date": day.isoformat(),
        "iso_week": f"{iso.year}-W{iso.week:02d}",
        "pattern": "SWEEP_UP_RECLAIM" if swept_high else "SWEEP_DOWN_RECLAIM",
        "signal": direction,
        "baseline_signal": baseline,
        "strategy_gross_bps": direction * ret_bps,
        "baseline_gross_bps": baseline * ret_bps,
        "paired_delta_bps": (direction - baseline) * ret_bps,
        "reference_open_close_not_executable": True,
    }, "EVENT"


def source33_parent_manifest(root: Path) -> dict[str, Any]:
    name = "qore-native-complete33-source-m5.json"
    witness = new_source._hash_scope(
        root / "OUTPUT_SHA256SUMS.txt", {name, "exact-code-head-sha.txt"}
    )
    manifest = g0.verified_file(root, witness, name)
    head = g0.verified_file(root, witness, "exact-code-head-sha.txt")
    sidecar = new_source._hash_scope(root / (name + ".sha256"), {name})
    if (
        witness[name] != PANEL_SOURCE_33_SHA
        or sidecar[name] != PANEL_SOURCE_33_SHA
        or head.read_text(encoding="utf-8").strip() != PANEL_SOURCE_33_CODE_SHA
    ):
        raise ValueError("signed full 33 original source manifest SHA drift")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    census33.census(data)  # require complete exact 33 signed source, all four families
    return data


def verify_original(symbol: str, original_root: Path, source_aggregate: Path | None) -> dict[str, Any]:
    if symbol not in final33.FROZEN_UNIVERSE_33:
        raise ValueError("symbol excluded from pre-frozen 33")
    if symbol in new_source.EXISTING:
        if source_aggregate is None:
            raise ValueError("original 12 aggregate SHA required")
        expected = g0.aggregate_index(source_aggregate)
        evidence = g0.audit_symbol(symbol, original_root, expected[symbol])
        if evidence["status"] != "G0_M5_SOURCE_INTEGRITY_PASS":
            raise ValueError("original twelve raw SHA failed")
        return {
            "source_cohort": "ORIGINAL12_DEMO",
            "provider_source_run": ORIGINAL_12_RUN,
            "native_m5_original_bars": evidence["native_m5_bars"],
            "source_manifest_sha256": evidence["symbol_manifest_sha256"],
            "original_raw_11_year_sha_checked": True,
        }
    witness = new_source.audit_new_symbol(symbol, original_root, allowed_symbols=(symbol,))
    if (witness["status"] != "G0_NEW_PROVIDER_M5_SHA_PASS"
            or witness["g1_net_authorized"] is not False
            or witness["ohlc_prices_returns_or_pnl_analyzed"] is not False):
        raise ValueError("new 21 original source SHA failed")
    return {
        "source_cohort": "NEW21_ICMARKETS_DEMO",
        "provider_source_run": NEW_21_RUN,
        "native_m5_original_bars": witness["m5_bars"],
        "source_manifest_sha256": witness["manifest_sha256"],
        "original_raw_11_year_sha_checked": True,
    }


def run_symbol(
    symbol: str, source_root: Path, source33_root: Path,
    original_12_aggregate: Path | None,
) -> dict[str, Any]:
    panel = source33_parent_manifest(source33_root)
    row = next((x for x in panel["market_roster"] if x["symbol"] == symbol), None)
    if row is None:
        raise ValueError("symbol not in 33 signed source roster")
    proof = verify_original(symbol, source_root, original_12_aggregate)
    if proof["native_m5_original_bars"] != row["m5_bars"]:
        raise ValueError("source 33 manifest and original ledger bar count drift")
    if symbol not in new_source.EXISTING:
        signed_manifest_sha = row.get("manifest_sha256", row.get("source_manifest_sha256"))
        if signed_manifest_sha != proof["source_manifest_sha256"]:
            raise ValueError("21 original source manifest SHA differs from signed 33 roster")
    calendar, counters = collect_blocks(source_root, symbol, symbol in new_source.EXISTING)
    events: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for day, blocks in sorted(calendar.items()):
        event, reason = event_from_day(day, blocks)
        reasons[reason] += 1
        if event is not None:
            events.append(event)
    family = next(k for k, v in census33.FAMILIES.items() if symbol in v)
    return {
        "identity": IDENTITY,
        "status": "GROSS04_ONE_SYMBOL_SHA_SOURCE_COMPLETE_NO_NET",
        "prereg_sha": PREREG_SHA,
        "panel33_source_json_sha": PANEL_SOURCE_33_SHA,
        "source_symbol": symbol,
        "source_family": family,
        "source_provenance": proof,
        "research_clock": "UTC 08-12 12-13 13-15 exact M5",
        "embargo_2024_09_17_ohlc_untouched": True,
        "source_data_counts": counters,
        "observability_reasons": dict(sorted(reasons.items())),
        "events": events,
        "no_bidask_spread_history": True,
        "news_pit_not_verified": True,
        "production_untouched": True,
        "net_certified": False,
    }


def sample_panel_weeks(
    witness_by_symbol: dict[str, list[dict[str, Any]]], field: str
) -> dict[str, Any]:
    """Whole-week bootstrap synchronized for every asset, no independence fiction."""
    weekly: dict[str, dict[str, tuple[float, int]]] = {}
    all_weeks: set[str] = set()
    for symbol, events in sorted(witness_by_symbol.items()):
        grouped: dict[str, list[float]] = defaultdict(list)
        for row in events:
            grouped[row["iso_week"]].append(row[field])
        weekly[symbol] = {k: (sum(v), len(v)) for k, v in grouped.items()}
        all_weeks |= set(grouped)
    if not all_weeks:
        return {"ci": None, "null_resamples": BOOTSTRAP_COUNT, "whole_week_clusters": 0}
    week_labels = sorted(all_weeks)
    rng = random.Random(BOOTSTRAP_SEED)
    values: list[float] = []
    missing = 0
    for _ in range(BOOTSTRAP_COUNT):
        sampled = Counter(week_labels[rng.randrange(len(week_labels))] for _ in week_labels)
        means: list[float] = []
        for symbol in sorted(witness_by_symbol):
            total = count = 0
            for week, count_of_week in sampled.items():
                pair = weekly[symbol].get(week)
                if pair:
                    total += count_of_week * pair[0]
                    count += count_of_week * pair[1]
            if not count:
                missing += 1
                break
            means.append(total / count)
        else:
            values.append(mean(means))
    values.sort()
    ci = None
    if len(values) >= 2:
        ci = {
            "low98_75": values[max(0, min(int(0.00625 * BOOTSTRAP_COUNT), len(values) - 1))],
            "high98_75": values[max(0, min(int(0.99375 * BOOTSTRAP_COUNT), len(values) - 1))],
        }
    return {
        "ci": ci,
        "null_resamples": missing,
        "non_null_resamples": len(values),
        "whole_week_clusters": len(week_labels),
        "bootstrap_count": BOOTSTRAP_COUNT,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def summarize_all33(data: dict[str, list[dict[str, Any]]], name: str) -> dict[str, Any]:
    if set(data) != final33.FROZEN_UNIVERSE_33:
        raise ValueError("not full frozen 33 population")
    needs_dev = name == "DEVELOPMENT"
    n_floor = MIN_EVENT_DEV if needs_dev else MIN_EVENT_DIAG
    w_floor = MIN_WEEKS_DEV if needs_dev else MIN_WEEKS_DIAG
    by_market = {}
    for symbol in sorted(data):
        events = data[symbol]
        gross = [x["strategy_gross_bps"] for x in events]
        ctrl = [x["baseline_gross_bps"] for x in events]
        delta = [x["paired_delta_bps"] for x in events]
        weeks = {x["iso_week"] for x in events}
        by_market[symbol] = {
            "n_days": len(events), "n_weeks": len(weeks),
            "gross_mean_bps": mean(gross) if gross else None,
            "baseline_mean_bps": mean(ctrl) if ctrl else None,
            "paired_delta_mean_bps": mean(delta) if delta else None,
            "long_events": sum(x["signal"] == 1 for x in events),
            "short_events": sum(x["signal"] == -1 for x in events),
            "panel_coverage_gate": len(events) >= n_floor and len(weeks) >= w_floor,
        }
    coverage_ok = all(r["panel_coverage_gate"] for r in by_market.values())
    strat_ci = sample_panel_weeks(data, "strategy_gross_bps")
    delta_ci = sample_panel_weeks(data, "paired_delta_bps")
    gross_mean = mean(r["gross_mean_bps"] for r in by_market.values() if r["gross_mean_bps"] is not None) if all(r["gross_mean_bps"] is not None for r in by_market.values()) else None
    baseline_mean = mean(r["baseline_mean_bps"] for r in by_market.values()) if all(r["baseline_mean_bps"] is not None for r in by_market.values()) else None
    paired_mean = mean(r["paired_delta_mean_bps"] for r in by_market.values()) if all(r["paired_delta_mean_bps"] is not None for r in by_market.values()) else None
    bootstrap_valid = (
        strat_ci["null_resamples"] <= BOOTSTRAP_NULL_CAP
        and delta_ci["null_resamples"] <= BOOTSTRAP_NULL_CAP
        and delta_ci["ci"] is not None and strat_ci["ci"] is not None
    )
    if not coverage_ok or not bootstrap_valid:
        verdict = "PANEL_UNDERPOWERED_NO_SYMBOL_EXCLUSION"
    elif (paired_mean is not None and paired_mean > 0
          and delta_ci["ci"]["low98_75"] > 0
          and gross_mean is not None and gross_mean > 0):
        verdict = "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
    else:
        verdict = "NO_SUPPORT_FOR_FROZEN_ALL33_SWEEP_RECLAIM"
    by_family = {}
    for family, symbols in census33.FAMILIES.items():
        rows = [by_market[s] for s in symbols]
        by_family[family] = {
            "markets": len(rows),
            "total_events": sum(r["n_days"] for r in rows),
            "gross_mean_bps_descriptive": (
                mean(r["gross_mean_bps"] for r in rows) if all(r["gross_mean_bps"] is not None for r in rows) else None
            ),
            "delta_mean_bps_descriptive": (
                mean(r["paired_delta_mean_bps"] for r in rows) if all(r["paired_delta_mean_bps"] is not None for r in rows) else None
            ),
            "family_significance_test_performed": False,
        }
    return {
        "name": name,
        "market_count": 33,
        "total_events": sum(r["n_days"] for r in by_market.values()),
        "markets_passing_n_gate": sum(r["panel_coverage_gate"] for r in by_market.values()),
        "all_market_coverage_gate": coverage_ok,
        "equal_market_strategy_gross_mean_bps": gross_mean,
        "equal_market_control_gross_mean_bps": baseline_mean,
        "equal_market_paired_delta_mean_bps": paired_mean,
        "delta_synchronized_week_CI98_75": delta_ci,
        "gross_synchronized_week_CI98_75": strat_ci,
        "break_even_equal_market_total_RT_bps_gross_only": gross_mean,
        "hypothetical_RT_assumptions_not_broker": [
            {"RT_bps": c, "gross_minus_assumed_cost": None if gross_mean is None else gross_mean - c}
            for c in COSTS_RT_HYPOTHETICAL_BPS
        ],
        "families_descriptive_no_selection": by_family,
        "all_33_symbols_including_nulls": by_market,
        "net_certified": False,
        "verdict": verdict,
    }


def aggregate_33(source33_root: Path, witnesses_root: Path) -> dict[str, Any]:
    panel = source33_parent_manifest(source33_root)
    paths = sorted(witnesses_root.rglob("qore-native-gross04-symbol-*.json"))
    if len(paths) != 33:
        raise ValueError("exactly 33 independent signed source+gross witnesses required")
    all_events: dict[str, list[dict[str, Any]]] = {}
    for p in paths:
        sha_file = p.with_name(p.name + ".sha256")
        signed = new_source._hash_scope(sha_file, {p.name})
        g0.verified_file(p.parent, signed, p.name)
        x = json.loads(p.read_text(encoding="utf-8"))
        symbol = x.get("source_symbol")
        row = next((m for m in panel["market_roster"] if m["symbol"] == symbol), None)
        if (row is None
                or x.get("identity") != IDENTITY
                or x.get("status") != "GROSS04_ONE_SYMBOL_SHA_SOURCE_COMPLETE_NO_NET"
                or x.get("prereg_sha") != PREREG_SHA
                or x.get("panel33_source_json_sha") != PANEL_SOURCE_33_SHA
                or x.get("embargo_2024_09_17_ohlc_untouched") is not True
                or x.get("news_pit_not_verified") is not True
                or x.get("net_certified") is not False
                or x.get("production_untouched") is not True
                or x.get("source_provenance", {}).get("native_m5_original_bars") != row["m5_bars"]
                or symbol in all_events):
            raise ValueError("bad or duplicate signed symbol provenance")
        evs = x.get("events")
        if not isinstance(evs, list):
            raise ValueError("missing individual event ledger")
        for e in evs:
            d = date.fromisoformat(e["utc_date"])
            iso = d.isocalendar()
            if (not START <= d < EMBARGO_DATE
                    or d.weekday() >= 5
                    or e.get("iso_week") != f"{iso.year}-W{iso.week:02d}"
                    or e.get("signal") not in (-1, 1)
                    or e.get("baseline_signal") not in (-1, 1)
                    or e.get("pattern") not in ("SWEEP_UP_RECLAIM", "SWEEP_DOWN_RECLAIM")
                    or (e["signal"] == -1) != (e["pattern"] == "SWEEP_UP_RECLAIM")
                    or e.get("reference_open_close_not_executable") is not True
                    or any(not isinstance(e[k], (int, float)) or not math.isfinite(e[k])
                           for k in ("strategy_gross_bps", "baseline_gross_bps", "paired_delta_bps"))
                    or abs((e["strategy_gross_bps"] - e["baseline_gross_bps"]) - e["paired_delta_bps"]) > 1e-7):
                raise ValueError("event ledger time or paired metric drift")
        all_events[symbol] = evs
    if set(all_events) != final33.FROZEN_UNIVERSE_33:
        raise ValueError("33 fixed symbols not all individually re-audited")
    dev = {
        symbol: [x for x in all_events[symbol] if date.fromisoformat(x["utc_date"]) < DEV_END]
        for symbol in all_events
    }
    diag = {
        symbol: [x for x in all_events[symbol] if date.fromisoformat(x["utc_date"]) >= DEV_END]
        for symbol in all_events
    }
    a = summarize_all33(dev, "DEVELOPMENT")
    b = summarize_all33(diag, "TEMPORAL_DIAGNOSTIC")
    supported = (
        a["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
        and b["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
    )
    return {
        "identity": IDENTITY,
        "status": STATUS,
        "prereg_sha_before_market_outcomes": PREREG_SHA,
        "full33_source_manifest_sha256": PANEL_SOURCE_33_SHA,
        "market_count": 33,
        "source_run_original_12": ORIGINAL_12_RUN,
        "source_run_new_21": NEW_21_RUN,
        "development": a, "temporal_diagnostic": b,
        "gross_panel_hypothesis_exploratory_support_both": supported,
        "three_prior_attempts_NO_SUPPORT": [
            "EURUSD_H4_GROSS01", "XAUUSD_H4_GROSS02", "NAS100_NY_OPEN03"
        ],
        "family_winners_not_selected": True,
        "future_2024_onward_OHLC_not_opened": True,
        "news_known_asof_calendar_not_verified": True,
        "bidask_broker_history_not_available": True,
        "net_execution_certified": False,
        "broker_origin_12_vs_21_equivalent_proven": False,
        "traders_certified": 0,
        "production_untouched": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    one = sub.add_parser("symbol")
    one.add_argument("symbol", choices=sorted(final33.FROZEN_UNIVERSE_33))
    one.add_argument("raw_original", type=Path)
    one.add_argument("frozen_33_source_artifact", type=Path)
    one.add_argument("output", type=Path)
    one.add_argument("--original12-aggregate", type=Path, default=None)
    two = sub.add_parser("aggregate")
    two.add_argument("frozen_33_source_artifact", type=Path)
    two.add_argument("signed_witnesses33", type=Path)
    two.add_argument("output", type=Path)
    args = ap.parse_args()
    if args.mode == "symbol":
        result = run_symbol(
            args.symbol, args.raw_original,
            args.frozen_33_source_artifact, args.original12_aggregate,
        )
        dest = args.output / f"qore-native-gross04-symbol-{args.symbol}.json"
    else:
        result = aggregate_33(args.frozen_33_source_artifact, args.signed_witnesses33)
        dest = args.output / "qore-native-gross04-panel33-result.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dest.with_name(dest.name + ".sha256").write_text(
        g0.sha256(dest) + f"  {dest.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "symbol": result.get("source_symbol"),
        "n_events": len(result.get("events", [])),
        "market_count": result.get("market_count"),
        "dev_verdict": result.get("development", {}).get("verdict"),
        "diag_verdict": result.get("temporal_diagnostic", {}).get("verdict"),
        "net_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
