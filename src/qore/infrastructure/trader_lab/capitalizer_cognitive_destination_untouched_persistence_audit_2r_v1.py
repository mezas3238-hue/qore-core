"""Untouched-persistence audit for true-2R Capitalizer Destination evidence.

Consumes:
- the true-2R cognitive economic rebase;
- the strict departure-time Destination binding audit;
- immutable CIBO Target Destination V2 causal candidate rows;
- immutable Capitalizer native-M1 data.

For each trade with an exact departure-time Target V2 context, this audit asks a
single causal question: was each departure candidate still *untouched by price*
through the last fully closed M1 bar before the trade entry?

Important boundaries:
- Target V2 touch/result fields are NEVER read;
- current-trade outcomes are NEVER read;
- only M1 bars opened at/after departure and closed at/before entry are used;
- incomplete M1 windows fail closed as persistence-UNBOUND;
- "untouched through entry" does NOT prove that the structural destination
  definition itself remained current. Structural revalidation remains separate.

No cognitive rule, strategy rule, entry, stop, target or MAX3 contract changes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_binding_audit_2r_v1 as departure_binding,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    _bar_from_row,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    TARGET_IDENTITY,
    TARGET_SCHEMA,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_DESTINATION_UNTOUCHED_PERSISTENCE_AUDIT_2R_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_COGNITIVE_DESTINATION_UNTOUCHED_PERSISTENCE_MATRIX_2R_V1"
)
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_DEPARTURE_RUN_ID = 36085887285
SOURCE_DEPARTURE_SHA = "c0529ca61dfd57cc7f3168bcee68751ef5651335"
SOURCE_TARGET_RUN_ID = 35204892665
SOURCE_TARGET_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"


@dataclass(frozen=True, slots=True)
class _TargetCandidate:
    candidate_id: str
    family: str
    timeframe: str
    price: Decimal


@dataclass(frozen=True, slots=True)
class DestinationUntouchedPersistenceRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    departure_at: str
    provenance: str
    departure_candidate_count: int
    expected_m1_bars: int
    observed_m1_bars: int
    m1_window_complete: bool
    touched_before_entry_count: int
    untouched_through_entry_count: int
    untouched_candidate_families: tuple[str, ...]
    untouched_candidate_timeframes: tuple[str, ...]
    at_least_one_candidate_untouched_through_entry: bool
    untouched_persistence_supported: bool
    destination_structural_current_at_entry_supported: bool = False
    destination_available_at_entry_supported: bool = False
    target_result_fields_read: bool = False
    target_touch_fields_read: bool = False
    current_trade_outcome_visible_to_audit: bool = False


@dataclass(frozen=True, slots=True)
class _Window:
    key: tuple[str, str]
    symbol: str
    side: str
    departure_at: datetime
    entry_at: datetime
    candidates: tuple[_TargetCandidate, ...]


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _extract_json_string(line: str, field: str) -> str | None:
    for marker in (f'"{field}": "', f'"{field}":"'):
        start = line.find(marker)
        if start < 0:
            continue
        start += len(marker)
        end = line.find('"', start)
        if end >= 0:
            return line[start:end]
    return None


def _load_departure_binding(
    root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-destination-departure-binding-audit-2r-v1.json"
        )
    )
    row_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-destination-departure-binding-audit-2r-v1-rows.jsonl"
        )
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("persistence audit requires one Destination binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != departure_binding.IDENTITY:
        raise ValueError("unexpected Destination departure binding identity")
    if report.get("target_result_fields_read") is not False:
        raise ValueError("persistence audit rejects prior Target result-field reads")
    if report.get("target_touch_fields_used") is not False:
        raise ValueError("persistence audit rejects prior Target touch-field reads")
    if report.get("destination_current_at_entry_supported") is not False:
        raise ValueError("persistence audit requires departure-only source state")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("persistence audit rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("Destination binding row must be object")
            rows.append(raw)
    if len(rows) != int(report.get("control_trades", -1)):
        raise ValueError("Destination binding population mismatch")
    return report, tuple(rows)


def _requested_target_keys(
    bound_rows: tuple[dict[str, Any], ...],
    rebase_by_key: dict[tuple[str, str], dict[str, Any]],
    *,
    symbol: str,
) -> dict[tuple[str, str, str], tuple[str, str]]:
    result: dict[tuple[str, str, str], tuple[str, str]] = {}
    for row in bound_rows:
        if str(row["symbol"]) != symbol:
            continue
        if row.get("destination_departure_evidence_bound") is not True:
            continue
        rebase_row = rebase_by_key.get(_join_key(row))
        if rebase_row is None:
            raise ValueError("Destination binding row missing rebase counterpart")
        departure = row.get("m5_closeback_at")
        if not isinstance(departure, str):
            raise ValueError("bound Destination row requires departure timestamp")
        side = str(rebase_row["side"]).lower()
        key = (symbol, side, departure)
        trade_key = _join_key(row)
        if key in result and result[key] != trade_key:
            raise ValueError("departure key maps to multiple trade identities")
        result[key] = trade_key
    return result


def _load_target_candidates(
    root: Path,
    *,
    requested: dict[tuple[str, str, str], tuple[str, str]],
) -> dict[tuple[str, str], tuple[_TargetCandidate, ...]]:
    ledgers = sorted(root.rglob("TARGET_DESTINATION_LEDGER_V2.jsonl"))
    if len(ledgers) != 1:
        raise ValueError("market persistence audit requires one Target V2 ledger")

    requested_departures = {key[2] for key in requested}
    candidates: dict[tuple[str, str], dict[str, _TargetCandidate]] = {}
    for path in ledgers:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                departure_hint = _extract_json_string(line, "departure_at")
                if departure_hint not in requested_departures:
                    continue
                symbol_hint = _extract_json_string(line, "symbol")
                side_hint = _extract_json_string(line, "side")
                if symbol_hint is None or side_hint is None:
                    raise ValueError("Target V2 row missing join identity")
                target_key = (
                    symbol_hint.upper(),
                    side_hint.lower(),
                    str(departure_hint),
                )
                trade_key = requested.get(target_key)
                if trade_key is None:
                    continue

                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("Target V2 row must be object")
                if raw.get("identity") != TARGET_IDENTITY:
                    raise ValueError("unexpected Target V2 identity")
                if raw.get("schema") != TARGET_SCHEMA:
                    raise ValueError("unexpected Target V2 schema")
                if raw.get("causal_feature") is not True:
                    raise ValueError("Target V2 candidate must be causal")
                if raw.get("outcome_only") is not False:
                    raise ValueError("Target V2 candidate cannot be outcome-only")
                if raw.get("result_fields_outcome_only") is not True:
                    raise ValueError("Target V2 result fields must remain outcome-only")
                if raw.get("active_untouched_at_departure") is not True:
                    continue

                departure = _aware(raw["departure_at"], field="departure_at")
                known = _aware(raw["candidate_known_at"], field="candidate_known_at")
                structural = _aware(
                    raw["candidate_structural_opened_at"],
                    field="candidate_structural_opened_at",
                )
                if known > departure or structural > departure:
                    raise ValueError("Target V2 candidate contains future departure evidence")

                candidate_id = str(raw["candidate_id"])
                family = str(raw["candidate_type"])
                timeframe = str(raw["source_timeframe"])
                price = Decimal(str(raw["candidate_price"]))
                if not candidate_id or not family:
                    raise ValueError("Target V2 candidate identity/family missing")
                if timeframe not in {"H1", "H4", "D1"}:
                    raise ValueError("Target V2 candidate timeframe invalid")
                if price <= 0:
                    raise ValueError("Target V2 candidate price must be positive")

                bucket = candidates.setdefault(trade_key, {})
                existing = bucket.get(candidate_id)
                candidate = _TargetCandidate(
                    candidate_id=candidate_id,
                    family=family,
                    timeframe=timeframe,
                    price=price,
                )
                if existing is not None and existing != candidate:
                    raise ValueError("Target V2 candidate identity collision")
                bucket[candidate_id] = candidate

    result = {
        key: tuple(
            sorted(
                bucket.values(),
                key=lambda item: (
                    item.price,
                    item.timeframe,
                    item.family,
                    item.candidate_id,
                ),
            )
        )
        for key, bucket in candidates.items()
    }
    if set(result) != set(requested.values()):
        missing = sorted(set(requested.values()) - set(result))
        raise ValueError(f"persistence audit missing Target candidates: {missing}")
    return result


def _windows(
    bound_rows: tuple[dict[str, Any], ...],
    rebase_by_key: dict[tuple[str, str], dict[str, Any]],
    candidates_by_trade: dict[tuple[str, str], tuple[_TargetCandidate, ...]],
    *,
    symbol: str,
) -> tuple[_Window, ...]:
    result: list[_Window] = []
    for row in bound_rows:
        if str(row["symbol"]) != symbol:
            continue
        if row.get("destination_departure_evidence_bound") is not True:
            continue
        key = _join_key(row)
        rebase_row = rebase_by_key[key]
        departure = _aware(row["m5_closeback_at"], field="departure_at")
        entry = _aware(row["entry_at"], field="entry_at")
        if departure > entry:
            raise ValueError("Destination departure cannot be after entry")
        delta_seconds = Decimal(str((entry - departure).total_seconds()))
        if delta_seconds % Decimal("60") != 0:
            raise ValueError("departure-to-entry window must align to exact minutes")
        candidates = candidates_by_trade[key]
        if len(candidates) != int(row["active_candidate_count"]):
            raise ValueError("Target candidate count drifted from departure binding")
        result.append(
            _Window(
                key=key,
                symbol=symbol,
                side=str(rebase_row["side"]).upper(),
                departure_at=departure,
                entry_at=entry,
                candidates=candidates,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.entry_at, item.key)))


def _dates_for_window(window: _Window) -> set[str]:
    if window.departure_at == window.entry_at:
        return {window.departure_at.date().isoformat()}
    result: set[str] = set()
    cursor = window.departure_at.date()
    end = (window.entry_at - timedelta(microseconds=1)).date()
    while cursor <= end:
        result.add(cursor.isoformat())
        cursor += timedelta(days=1)
    return result


def _load_relevant_m1(
    root: Path,
    *,
    windows: tuple[_Window, ...],
) -> tuple[CapitalizerM1Bar, ...]:
    if not windows:
        return ()
    wanted_dates = set().union(*(_dates_for_window(window) for window in windows))
    wanted_years = sorted({int(value[:4]) for value in wanted_dates})
    bars: list[CapitalizerM1Bar] = []

    ledger = root / "RAW_M1_LEDGER"
    if not ledger.exists():
        raise ValueError("native M1 RAW_M1_LEDGER not found")

    for year in wanted_years:
        path = ledger / f"{year}.jsonl"
        if not path.exists():
            raise ValueError(f"native M1 year partition missing: {year}")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                opened_hint = _extract_json_string(line, "opened_at")
                if opened_hint is None or opened_hint[:10] not in wanted_dates:
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("native M1 row must be object")
                bar = _bar_from_row(raw)
                if any(
                    window.departure_at <= bar.opened_at < window.entry_at
                    for window in windows
                ):
                    bars.append(bar)

    return tuple(sorted(bars, key=lambda item: item.opened_at))


def _touched(
    bar: CapitalizerM1Bar,
    *,
    side: str,
    price: Decimal,
) -> bool:
    if side == "LONG":
        return bar.high >= price
    if side == "SHORT":
        return bar.low <= price
    raise ValueError("trade side must be LONG/SHORT")


def _evaluate_window(
    window: _Window,
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[
    bool,
    int,
    tuple[_TargetCandidate, ...],
    tuple[_TargetCandidate, ...],
]:
    relevant = tuple(
        bar
        for bar in bars
        if window.departure_at <= bar.opened_at < window.entry_at
    )
    expected_count = int(
        (window.entry_at - window.departure_at).total_seconds() // 60
    )
    expected_opens = {
        window.departure_at + timedelta(minutes=index)
        for index in range(expected_count)
    }
    observed_opens = {bar.opened_at for bar in relevant}
    complete = observed_opens == expected_opens

    touched: list[_TargetCandidate] = []
    untouched: list[_TargetCandidate] = []
    for candidate in window.candidates:
        if any(
            _touched(bar, side=window.side, price=candidate.price)
            for bar in relevant
        ):
            touched.append(candidate)
        else:
            untouched.append(candidate)

    return complete, len(relevant), tuple(touched), tuple(untouched)


def build_market_report(
    rebase_root: Path,
    departure_root: Path,
    target_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[DestinationUntouchedPersistenceRow, ...]]:
    normalized = symbol.upper()
    rebase_report, rebase_rows = regime_binding._load_rebase(rebase_root)
    departure_report, departure_rows = _load_departure_binding(departure_root)
    rebase_by_key = {_join_key(row): row for row in rebase_rows}
    if len(rebase_by_key) != len(rebase_rows):
        raise ValueError("persistence rebase identity not unique")
    if {_join_key(row) for row in departure_rows} != set(rebase_by_key):
        raise ValueError("persistence rebase/Departure identities differ")

    requested = _requested_target_keys(
        departure_rows,
        rebase_by_key,
        symbol=normalized,
    )
    candidates_by_trade = _load_target_candidates(
        target_root,
        requested=requested,
    )
    windows = _windows(
        departure_rows,
        rebase_by_key,
        candidates_by_trade,
        symbol=normalized,
    )
    bars = _load_relevant_m1(m1_root, windows=windows)

    rows: list[DestinationUntouchedPersistenceRow] = []
    for window in windows:
        departure_row = next(
            row for row in departure_rows if _join_key(row) == window.key
        )
        complete, observed_count, touched, untouched = _evaluate_window(
            window,
            bars,
        )
        expected_count = int(
            (window.entry_at - window.departure_at).total_seconds() // 60
        )
        supported = complete
        rows.append(
            DestinationUntouchedPersistenceRow(
                symbol=normalized,
                session=str(departure_row["session"]),
                operating_date=str(departure_row["operating_date"]),
                side=window.side,
                entry_at=window.entry_at.isoformat(),
                departure_at=window.departure_at.isoformat(),
                provenance=str(departure_row["provenance"]),
                departure_candidate_count=len(window.candidates),
                expected_m1_bars=expected_count,
                observed_m1_bars=observed_count,
                m1_window_complete=complete,
                touched_before_entry_count=(
                    len(touched) if supported else 0
                ),
                untouched_through_entry_count=(
                    len(untouched) if supported else 0
                ),
                untouched_candidate_families=(
                    tuple(sorted({item.family for item in untouched}))
                    if supported
                    else ()
                ),
                untouched_candidate_timeframes=(
                    tuple(sorted({item.timeframe for item in untouched}))
                    if supported
                    else ()
                ),
                at_least_one_candidate_untouched_through_entry=(
                    supported and bool(untouched)
                ),
                untouched_persistence_supported=supported,
            )
        )

    result = tuple(rows)
    complete_rows = tuple(row for row in result if row.m1_window_complete)
    survivor_rows = tuple(
        row
        for row in complete_rows
        if row.at_least_one_candidate_untouched_through_entry
    )
    all_touched_rows = tuple(
        row
        for row in complete_rows
        if not row.at_least_one_candidate_untouched_through_entry
    )

    return {
        "identity": IDENTITY,
        "symbol": normalized,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_departure_run_id": SOURCE_DEPARTURE_RUN_ID,
        "source_departure_sha": SOURCE_DEPARTURE_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "departure_bound_trades": len(result),
        "m1_window_complete_trades": len(complete_rows),
        "m1_window_incomplete_trades": len(result) - len(complete_rows),
        "at_least_one_candidate_untouched_through_entry_trades": len(
            survivor_rows
        ),
        "all_candidates_touched_before_entry_trades": len(all_touched_rows),
        "candidate_rows_at_departure": sum(
            row.departure_candidate_count for row in result
        ),
        "candidate_rows_touched_before_entry": sum(
            row.touched_before_entry_count for row in complete_rows
        ),
        "candidate_rows_untouched_through_entry": sum(
            row.untouched_through_entry_count for row in complete_rows
        ),
        "m1_touch_reconstruction_only": True,
        "target_result_fields_read": False,
        "target_touch_fields_read": False,
        "current_trade_outcome_visible_to_audit": False,
        "untouched_persistence_supported": bool(complete_rows),
        "destination_structural_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "destination_intelligence_supported": False,
        "missing_evidence_fabricated": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(rebase_rows)
        ),
        "departure_binding_control_reproduced": (
            int(departure_report["control_trades"]) == len(departure_rows)
        ),
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
    }, result


def write_market(
    report: dict[str, Any],
    rows: tuple[DestinationUntouchedPersistenceRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-destination-untouched-persistence-audit-2r-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(
        root.rglob(
            "capitalizer-*-destination-untouched-persistence-audit-2r-v1.json"
        )
    )
    row_paths = sorted(
        root.rglob(
            "capitalizer-*-destination-untouched-persistence-audit-2r-v1-rows.jsonl"
        )
    )
    if len(reports) != 9 or len(row_paths) != 9:
        raise ValueError("persistence matrix requires nine market reports/ledgers")

    payloads = [
        dict(json.loads(path.read_text(encoding="utf-8"))) for path in reports
    ]
    symbols = [str(item["symbol"]) for item in payloads]
    if len(set(symbols)) != 9:
        raise ValueError("persistence matrix market identity must be unique")
    if any(item.get("identity") != IDENTITY for item in payloads):
        raise ValueError("persistence matrix received unexpected market identity")

    rows: list[dict[str, Any]] = []
    for path in row_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("persistence matrix row must be object")
                    rows.append(raw)

    complete = tuple(row for row in rows if row["m1_window_complete"] is True)
    survivors = tuple(
        row
        for row in complete
        if row["at_least_one_candidate_untouched_through_entry"] is True
    )
    all_touched = tuple(
        row
        for row in complete
        if row["at_least_one_candidate_untouched_through_entry"] is False
    )
    family_counts = Counter(
        "+".join(str(item) for item in row["untouched_candidate_families"])
        for row in survivors
    )
    timeframe_counts = Counter(
        "+".join(str(item) for item in row["untouched_candidate_timeframes"])
        for row in survivors
    )

    report = {
        "identity": MATRIX_IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_departure_run_id": SOURCE_DEPARTURE_RUN_ID,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_count": 9,
        "departure_bound_trades": len(rows),
        "m1_window_complete_trades": len(complete),
        "m1_window_incomplete_trades": len(rows) - len(complete),
        "at_least_one_candidate_untouched_through_entry_trades": len(survivors),
        "all_candidates_touched_before_entry_trades": len(all_touched),
        "candidate_rows_at_departure": sum(
            int(row["departure_candidate_count"]) for row in rows
        ),
        "candidate_rows_touched_before_entry": sum(
            int(row["touched_before_entry_count"]) for row in complete
        ),
        "candidate_rows_untouched_through_entry": sum(
            int(row["untouched_through_entry_count"]) for row in complete
        ),
        "survivor_family_signature_counts": dict(sorted(family_counts.items())),
        "survivor_timeframe_signature_counts": dict(
            sorted(timeframe_counts.items())
        ),
        "by_market": {
            str(item["symbol"]): {
                "departure_bound_trades": int(item["departure_bound_trades"]),
                "m1_window_complete_trades": int(item["m1_window_complete_trades"]),
                "at_least_one_candidate_untouched_through_entry_trades": int(
                    item["at_least_one_candidate_untouched_through_entry_trades"]
                ),
                "all_candidates_touched_before_entry_trades": int(
                    item["all_candidates_touched_before_entry_trades"]
                ),
            }
            for item in sorted(payloads, key=lambda value: str(value["symbol"]))
        },
        "m1_touch_reconstruction_only": True,
        "target_result_fields_read": False,
        "target_touch_fields_read": False,
        "current_trade_outcome_visible_to_audit": False,
        "destination_structural_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "destination_intelligence_supported": False,
        "missing_evidence_fabricated": False,
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
        "next_phase": (
            "MEASURE_UNTOUCHED_DESTINATION_INFORMATION_VALUE_THEN_BIND_PERCEPTION"
        ),
    }
    return report, tuple(rows)


def write_matrix(
    report: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-nine-market-destination-untouched-persistence-matrix-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-nine-market-destination-untouched-persistence-matrix-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("rebase_root", type=Path)
    market.add_argument("departure_root", type=Path)
    market.add_argument("target_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.rebase_root,
            args.departure_root,
            args.target_root,
            args.m1_root,
            symbol=str(args.symbol),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report, rows = build_matrix(args.input_root)
    write_matrix(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
