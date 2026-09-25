"""Historical native-M1 bar-completeness audit for true-2R Capitalizer.

This audit resolves one explicit blocker in the Perception evidence chain without
inventing data quality.  For each frozen true-2R trade it inspects the immutable
provider-native M1 clone across the exact H1-open -> entry decision span.

A fully observed minute grid is positive evidence that bars_complete can be
SUPPORTED_TRUE for that historical span.  A missing provider minute is not
automatically a data defect because the retained cTrader trendbar corpus cannot
distinguish "no provider bar/no ticks" from an upstream omission.  Such spans
therefore remain UNBOUND.  A missing entry bar is a hard contradiction because
the frozen trade entry is sourced from native M1 and is SUPPORTED_FALSE.

No outcome, PF, DD, stop/target result, or future bar is used.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_HISTORICAL_BAR_COMPLETENESS_AUDIT_2R_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_"
    "HISTORICAL_BAR_COMPLETENESS_AUDIT_2R_V1"
)
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"

EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
}


class BarCompletenessState(StrEnum):
    SUPPORTED_TRUE = "SUPPORTED_TRUE"
    SUPPORTED_FALSE = "SUPPORTED_FALSE"
    UNBOUND = "UNBOUND"


@dataclass(frozen=True, slots=True)
class HistoricalBarCompletenessRow:
    symbol: str
    session: str
    operating_date: str
    h1_open: str
    entry_at: str
    expected_minutes: int
    observed_minutes: int
    missing_calendar_minutes: int
    first_missing_minute: str | None
    last_missing_minute: str | None
    entry_bar_present: bool
    state: BarCompletenessState
    provider_native_m1: bool = True
    current_trade_outcome_visible_to_binding: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    if parsed.second != 0 or parsed.microsecond != 0:
        raise ValueError(f"{field} must be minute-aligned")
    return parsed


def _minute(value: datetime) -> int:
    return int(value.timestamp() // 60)


def _iso_minute(value: int, *, template: datetime) -> str:
    return datetime.fromtimestamp(value * 60, tz=template.tzinfo).isoformat()


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json"))
    rows_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(reports) != 1 or len(rows_paths) != 1:
        raise ValueError("bar completeness requires one true-2R rebase artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected true-2R rebase identity")
    if str(report.get("target_r")) != "2.00":
        raise ValueError("bar completeness requires true 2R")
    rows: list[dict[str, Any]] = []
    with rows_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("rebase row must be an object")
            if raw.get("source_timestamps_causal") is not True:
                raise ValueError("bar completeness rejects non-causal source rows")
            if raw.get("source_microstructure_bound") is not True:
                raise ValueError("bar completeness requires source-bound rows")
            rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("bar completeness rebase population mismatch")
    return report, tuple(rows)


def _resolve_m1_root(root: Path, *, symbol: str) -> tuple[Path, dict[str, Any]]:
    manifests = sorted(root.rglob("m1-clone-manifest.json"))
    if len(manifests) != 1:
        raise ValueError("bar completeness requires one native-M1 clone manifest")
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("native-M1 manifest must be an object")
    if str(manifest.get("canonical_symbol")) != symbol:
        raise ValueError("native-M1 symbol mismatch")
    if manifest.get("provider_native_m1") is not True:
        raise ValueError("bar completeness requires provider-native M1")
    if manifest.get("synthetic_m1") is not False:
        raise ValueError("synthetic M1 is forbidden")
    if manifest.get("interpolated_m1") is not False:
        raise ValueError("interpolated M1 is forbidden")
    if int(manifest.get("contradictory_m1", -1)) != 0:
        raise ValueError("contradictory native-M1 evidence")
    return manifests[0].parent, manifest


def _classify(
    *,
    symbol: str,
    session: str,
    operating_date: str,
    h1_open: datetime,
    entry_at: datetime,
    observed_minutes: set[int],
) -> HistoricalBarCompletenessRow:
    start = _minute(h1_open)
    end = _minute(entry_at)
    if end < start:
        raise ValueError("entry cannot precede H1 causal window")
    expected = end - start + 1
    missing = [minute for minute in range(start, end + 1) if minute not in observed_minutes]
    observed = expected - len(missing)
    entry_present = end in observed_minutes

    if not entry_present:
        state = BarCompletenessState.SUPPORTED_FALSE
    elif not missing:
        state = BarCompletenessState.SUPPORTED_TRUE
    else:
        state = BarCompletenessState.UNBOUND

    return HistoricalBarCompletenessRow(
        symbol=symbol,
        session=session,
        operating_date=operating_date,
        h1_open=h1_open.isoformat(),
        entry_at=entry_at.isoformat(),
        expected_minutes=expected,
        observed_minutes=observed,
        missing_calendar_minutes=len(missing),
        first_missing_minute=(
            None if not missing else _iso_minute(missing[0], template=h1_open)
        ),
        last_missing_minute=(
            None if not missing else _iso_minute(missing[-1], template=h1_open)
        ),
        entry_bar_present=entry_present,
        state=state,
    )


def build_market_report(
    rebase_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[HistoricalBarCompletenessRow, ...]]:
    if symbol not in EXPECTED_SYMBOLS:
        raise ValueError("symbol outside frozen Capitalizer universe")
    rebase_report, all_rows = _load_rebase(rebase_root)
    source_rows = tuple(row for row in all_rows if str(row["symbol"]) == symbol)
    if not source_rows:
        raise ValueError("bar completeness found no frozen trades for symbol")

    native_root, manifest = _resolve_m1_root(m1_root, symbol=symbol)
    observed_minutes = {_minute(bar.opened_at) for bar in iter_cibo_m1(native_root)}
    if not observed_minutes:
        raise ValueError("native-M1 clone is empty")

    target_start = _aware(manifest["target_start"], field="target_start")
    target_end = _aware(manifest["target_end_exclusive"], field="target_end_exclusive")

    rows: list[HistoricalBarCompletenessRow] = []
    for source in source_rows:
        h1_open = _aware(source["h1_open"], field="h1_open")
        entry_at = _aware(source["entry_at"], field="entry_at")
        if h1_open < target_start or entry_at >= target_end:
            raise ValueError("trade lies outside retained native-M1 window")
        rows.append(
            _classify(
                symbol=symbol,
                session=str(source["session"]),
                operating_date=str(source["operating_date"]),
                h1_open=h1_open,
                entry_at=entry_at,
                observed_minutes=observed_minutes,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.entry_at))
    counts = Counter(row.state.value for row in ordered)
    missing_total = sum(row.missing_calendar_minutes for row in ordered)
    entry_missing = sum(not row.entry_bar_present for row in ordered)

    report: dict[str, Any] = {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "symbol": symbol,
        "control_trades": len(ordered),
        "state_counts": {
            state.value: counts.get(state.value, 0) for state in BarCompletenessState
        },
        "calendar_contiguous_trades": counts.get(
            BarCompletenessState.SUPPORTED_TRUE.value, 0
        ),
        "calendar_gap_unbound_trades": counts.get(
            BarCompletenessState.UNBOUND.value, 0
        ),
        "hard_missing_entry_bar_trades": entry_missing,
        "missing_calendar_minutes_total": missing_total,
        "provider_native_m1": True,
        "synthetic_m1_used": False,
        "interpolated_m1_used": False,
        "provider_absence_interpreted_as_data_failure": False,
        "unknown_evidence_coerced_to_false": False,
        "current_trade_outcome_visible_to_binding": False,
        "rebase_control_reproduced": int(rebase_report["control_trades"]) == len(all_rows),
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[HistoricalBarCompletenessRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-historical-bar-completeness-audit-2r-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(
        path
        for path in root.rglob(
            "capitalizer-*-cognitive-historical-bar-completeness-audit-2r-v1.json"
        )
        if "nine-market" not in path.name
    )
    if len(paths) != 9:
        raise ValueError(f"bar completeness matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    symbols = {str(item["symbol"]) for item in reports}
    if symbols != EXPECTED_SYMBOLS:
        raise ValueError("bar completeness market universe mismatch")

    counts = Counter()
    for item in reports:
        for state, value in dict(item["state_counts"]).items():
            counts[str(state)] += int(value)

    control = sum(int(item["control_trades"]) for item in reports)
    if control != rebase.EXPECTED_TRADES:
        raise ValueError("bar completeness matrix population mismatch")

    supported = counts[BarCompletenessState.SUPPORTED_TRUE.value]
    false = counts[BarCompletenessState.SUPPORTED_FALSE.value]
    unbound = counts[BarCompletenessState.UNBOUND.value]
    bindable = false == 0 and unbound == 0 and supported == control

    return {
        "identity": MATRIX_IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_count": 9,
        "control_trades": control,
        "state_counts": {
            state.value: counts.get(state.value, 0) for state in BarCompletenessState
        },
        "missing_calendar_minutes_total": sum(
            int(item["missing_calendar_minutes_total"]) for item in reports
        ),
        "hard_missing_entry_bar_trades": sum(
            int(item["hard_missing_entry_bar_trades"]) for item in reports
        ),
        "historical_bars_complete_globally_bindable": bindable,
        "provider_native_m1": True,
        "provider_absence_interpreted_as_data_failure": False,
        "unknown_evidence_coerced_to_false": False,
        "current_trade_outcome_visible_to_binding": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "PROMOTE_BARS_COMPLETE_BINDING_IN_PERCEPTION_AUDIT"
            if bindable
            else "RESOLVE_PROVIDER_ABSENCE_SEMANTICS_OR_KEEP_BARS_COMPLETE_UNBOUND"
        ),
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-nine-market-cognitive-historical-bar-completeness-audit-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("rebase_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True, choices=sorted(EXPECTED_SYMBOLS))

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.rebase_root,
            args.m1_root,
            symbol=args.symbol,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
