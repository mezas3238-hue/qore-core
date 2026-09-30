"""Strict departure-time Destination evidence binding for true-2R Capitalizer.

This consumed-window audit joins the frozen 948-trade true-2R cognitive rebase
to the immutable CIBO Target Destination V2 ledgers.

The join is deliberately strict:
- symbol and side must match;
- the exact M5_CLOSEBACK_AT token must equal Target V2 departure_at;
- Target V2 candidates must have been known and structurally opened no later
  than departure_at;
- departure_at must be no later than the trade entry timestamp.

The audit reads only causal Target V2 fields. Touch/result fields are ignored.
Therefore this lab proves only that a departure-time destination context was
known before entry. It does NOT claim that the same destination remained
untouched/current at the later M1 entry, and it does not feed destination
availability into the cognitive gate yet.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    TARGET_IDENTITY,
    TARGET_SCHEMA,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_DESTINATION_DEPARTURE_BINDING_AUDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_TARGET_RUN_ID = 35204892665
SOURCE_TARGET_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"


@dataclass(frozen=True, slots=True)
class DestinationDepartureBindingRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    provenance: str
    m5_closeback_at: str | None
    target_context_match_found: bool
    target_context_causal: bool
    destination_departure_evidence_bound: bool
    active_candidate_count: int
    nearest_distance_ticks: str | None
    candidate_families: tuple[str, ...]
    candidate_timeframes: tuple[str, ...]
    departure_to_entry_seconds: str | None
    departure_context_known_by_entry: bool
    destination_current_at_entry_supported: bool = False
    destination_available_at_entry_supported: bool = False
    target_result_fields_read: bool = False
    current_trade_outcome_visible_to_binding: bool = False


@dataclass(frozen=True, slots=True)
class _TargetContextEvidence:
    symbol: str
    side: str
    departure_at: str
    candidate_ids: frozenset[str]
    distances: tuple[Decimal, ...]
    families: tuple[str, ...]
    timeframes: tuple[str, ...]


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _target_key(
    *,
    symbol: object,
    side: object,
    departure_at: object,
) -> tuple[str, str, str]:
    return str(symbol).upper(), str(side).lower(), str(departure_at)


def _requested_keys(
    rows: tuple[dict[str, Any], ...],
) -> set[tuple[str, str, str]]:
    result: set[tuple[str, str, str]] = set()
    for row in rows:
        tokens = regime_binding._token_map(row)
        closeback = tokens.get("M5_CLOSEBACK_AT")
        if closeback is None:
            continue
        result.add(
            _target_key(
                symbol=row["symbol"],
                side=row["side"],
                departure_at=closeback,
            )
        )
    return result


def _extract_json_string(line: str, field: str) -> str | None:
    marker = f'"{field}": "'
    start = line.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = line.find('"', start)
    if end < 0:
        return None
    return line[start:end]


def _load_target_context_evidence(
    root: Path,
    *,
    requested: set[tuple[str, str, str]],
) -> tuple[
    dict[tuple[str, str, str], _TargetContextEvidence],
    dict[str, int],
]:
    ledgers = sorted(root.rglob("TARGET_DESTINATION_LEDGER_V2.jsonl"))
    if not ledgers:
        raise ValueError("destination binding found no Target V2 ledgers")

    candidates: dict[
        tuple[str, str, str],
        dict[str, Any],
    ] = {}
    symbols_seen: set[str] = set()
    causal_candidate_rows = 0
    requested_departures = {key[2] for key in requested}

    for path in ledgers:
        file_symbol: str | None = None
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                if file_symbol is None:
                    file_symbol = _extract_json_string(line, "symbol")
                    if file_symbol is not None:
                        symbols_seen.add(file_symbol.upper())

                departure_hint = _extract_json_string(line, "departure_at")
                if departure_hint not in requested_departures:
                    continue
                symbol_hint = _extract_json_string(line, "symbol")
                side_hint = _extract_json_string(line, "side")
                if symbol_hint is None or side_hint is None:
                    raise ValueError("Target V2 row missing join identity")

                key = _target_key(
                    symbol=symbol_hint,
                    side=side_hint,
                    departure_at=departure_hint,
                )
                if key not in requested:
                    continue

                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("Target V2 row must be object")
                symbol = str(raw.get("symbol", "")).upper()
                if not symbol:
                    raise ValueError("Target V2 row missing symbol")

                if raw.get("identity") != TARGET_IDENTITY:
                    raise ValueError("unexpected Target V2 identity")
                if raw.get("schema") != TARGET_SCHEMA:
                    raise ValueError("unexpected Target V2 schema")
                if raw.get("causal_feature") is not True:
                    raise ValueError("Target V2 matched row must be causal")
                if raw.get("outcome_only") is not False:
                    raise ValueError("Target V2 matched row cannot be outcome-only")
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
                distance = Decimal(str(raw["candidate_distance_ticks"]))
                if not candidate_id or not family:
                    raise ValueError("Target V2 candidate identity/family missing")
                if timeframe not in {"H1", "H4", "D1"}:
                    raise ValueError("Target V2 timeframe outside H1/H4/D1")
                if distance < 0:
                    raise ValueError("Target V2 candidate distance cannot be negative")

                bucket = candidates.setdefault(
                    key,
                    {
                        "candidate_ids": set(),
                        "distances": [],
                        "families": set(),
                        "timeframes": set(),
                    },
                )
                bucket["candidate_ids"].add(candidate_id)
                bucket["distances"].append(distance)
                bucket["families"].add(family)
                bucket["timeframes"].add(timeframe)
                causal_candidate_rows += 1

    result: dict[tuple[str, str, str], _TargetContextEvidence] = {}
    for key, bucket in candidates.items():
        symbol, side, departure_at = key
        result[key] = _TargetContextEvidence(
            symbol=symbol,
            side=side,
            departure_at=departure_at,
            candidate_ids=frozenset(str(item) for item in bucket["candidate_ids"]),
            distances=tuple(Decimal(item) for item in bucket["distances"]),
            families=tuple(sorted(str(item) for item in bucket["families"])),
            timeframes=tuple(sorted(str(item) for item in bucket["timeframes"])),
        )

    stats = {
        "target_ledger_files": len(ledgers),
        "target_symbols_seen": len(symbols_seen),
        "matched_causal_candidate_rows": causal_candidate_rows,
    }
    return result, stats


def _bind_rows(
    rebase_rows: tuple[dict[str, Any], ...],
    target_index: dict[tuple[str, str, str], _TargetContextEvidence],
) -> tuple[DestinationDepartureBindingRow, ...]:
    result: list[DestinationDepartureBindingRow] = []
    for row in rebase_rows:
        tokens = regime_binding._token_map(row)
        closeback = tokens.get("M5_CLOSEBACK_AT")
        entry = _aware(row["entry_at"], field="entry_at")

        context: _TargetContextEvidence | None = None
        if closeback is not None:
            context = target_index.get(
                _target_key(
                    symbol=row["symbol"],
                    side=row["side"],
                    departure_at=closeback,
                )
            )

        match = context is not None
        causal = False
        gap_seconds: str | None = None
        if context is not None:
            departure = _aware(context.departure_at, field="departure_at")
            causal = departure <= entry
            if causal:
                gap_seconds = str(
                    Decimal(str((entry - departure).total_seconds()))
                )

        bound = bool(
            match
            and causal
            and context is not None
            and context.candidate_ids
        )
        count = 0
        nearest: str | None = None
        families: tuple[str, ...] = ()
        timeframes: tuple[str, ...] = ()
        if bound:
            if context is None:
                raise AssertionError("bound destination context unexpectedly missing")
            count = len(context.candidate_ids)
            nearest = str(min(context.distances))
            families = context.families
            timeframes = context.timeframes

        result.append(
            DestinationDepartureBindingRow(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                provenance=str(row["provenance"]),
                m5_closeback_at=closeback,
                target_context_match_found=match,
                target_context_causal=causal,
                destination_departure_evidence_bound=bound,
                active_candidate_count=count,
                nearest_distance_ticks=nearest,
                candidate_families=families,
                candidate_timeframes=timeframes,
                departure_to_entry_seconds=gap_seconds,
                departure_context_known_by_entry=bound,
            )
        )
    return tuple(result)


def build_report(
    rebase_root: Path,
    target_root: Path,
) -> tuple[dict[str, Any], tuple[DestinationDepartureBindingRow, ...]]:
    rebase_report, rebase_rows = regime_binding._load_rebase(rebase_root)
    requested = _requested_keys(rebase_rows)
    target_index, target_stats = _load_target_context_evidence(
        target_root,
        requested=requested,
    )
    rows = _bind_rows(rebase_rows, target_index)

    bound = tuple(row for row in rows if row.destination_departure_evidence_bound)
    future_violations = sum(
        row.target_context_match_found and not row.target_context_causal
        for row in rows
    )

    by_provenance: dict[str, dict[str, int]] = {}
    for provenance in sorted({row.provenance for row in rows}):
        subset = tuple(row for row in rows if row.provenance == provenance)
        by_provenance[provenance] = {
            "trades": len(subset),
            "m5_closeback_token": sum(
                row.m5_closeback_at is not None for row in subset
            ),
            "destination_departure_evidence_bound": sum(
                row.destination_departure_evidence_bound for row in subset
            ),
        }

    by_market: dict[str, dict[str, int]] = {}
    for symbol in sorted({row.symbol for row in rows}):
        subset = tuple(row for row in rows if row.symbol == symbol)
        by_market[symbol] = {
            "trades": len(subset),
            "m5_closeback_token": sum(
                row.m5_closeback_at is not None for row in subset
            ),
            "destination_departure_evidence_bound": sum(
                row.destination_departure_evidence_bound for row in subset
            ),
        }

    family_signatures = Counter(
        "+".join(row.candidate_families) if row.candidate_families else "NONE"
        for row in bound
    )
    timeframe_signatures = Counter(
        "+".join(row.candidate_timeframes) if row.candidate_timeframes else "NONE"
        for row in bound
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "requested_exact_departure_keys": len(requested),
        "destination_departure_evidence_bound_trades": len(bound),
        "destination_departure_evidence_unbound_trades": len(rows) - len(bound),
        "destination_departure_evidence_coverage": (
            "0"
            if not rows
            else str(Decimal(len(bound)) / Decimal(len(rows)))
        ),
        "by_provenance": by_provenance,
        "by_market": by_market,
        "candidate_family_signature_counts": dict(sorted(family_signatures.items())),
        "candidate_timeframe_signature_counts": dict(
            sorted(timeframe_signatures.items())
        ),
        "future_evidence_violations": future_violations,
        **target_stats,
        "target_result_fields_read": False,
        "target_touch_fields_used": False,
        "departure_context_known_by_entry_supported": True,
        "destination_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "destination_intelligence_supported": False,
        "current_trade_outcome_visible_to_binding": False,
        "missing_evidence_fabricated": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(rows)
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
        "next_phase": (
            "MEASURE_DEPARTURE_DESTINATION_INFORMATION_VALUE_THEN_REVALIDATE_TO_ENTRY"
        ),
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[DestinationDepartureBindingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-destination-departure-binding-audit-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.rebase_root, args.target_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
