"""Causal destination-evidence binding audit for true-2R Capitalizer.

This lab joins the frozen true-2R trade set to the immutable CIBO Target
Destination V2 ledgers.

The binding point is the trade's causal M5 closeback timestamp. Target V2 only
exposes candidates that were known, active and untouched at that departure
timestamp; its post-departure result/touch fields are never read by the
Capitalizer target-context adapter.

Important boundary:
- a bound context proves destination evidence existed at M5 departure;
- it does NOT prove every destination remained untouched until the later M1
  entry;
- therefore full entry-time Destination Intelligence remains unsupported until
  causal between-departure-and-entry consumption is reconstructed.

No target, entry, stop, MAX3 rule or target family is selected here.
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
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)
from qore.infrastructure.trader_lab.capitalizer_target_context import (
    CapitalizerTargetContext,
    load_target_contexts,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_DESTINATION_EVIDENCE_BINDING_AUDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_TARGET_RUN_ID = 35204892665
SOURCE_TARGET_SHA = "2f510461b3360e91d5ee70a72716a76cd6561f16"


@dataclass(frozen=True, slots=True)
class DestinationEvidenceBindingRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    provenance: str
    m5_closeback_at: str | None
    target_context_match_found: bool
    target_context_causal: bool
    destination_evidence_at_departure_bound: bool
    active_candidate_count_at_departure: int
    nearest_distance_ticks_at_departure: str | None
    candidate_families_at_departure: tuple[str, ...]
    candidate_timeframes_at_departure: tuple[str, ...]
    post_departure_result_fields_used: bool = False
    destination_intelligence_at_entry_supported: bool = False
    current_trade_outcome_visible_to_binding: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _side(value: object) -> CapitalizerSide:
    raw = str(value)
    if raw == "LONG":
        return CapitalizerSide.LONG
    if raw == "SHORT":
        return CapitalizerSide.SHORT
    raise ValueError("Capitalizer side must be LONG/SHORT")


def _token_map(row: dict[str, Any]) -> dict[str, str]:
    return regime_binding._token_map(row)


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    return regime_binding._load_rebase(root)


def _load_all_target_contexts(root: Path) -> tuple[CapitalizerTargetContext, ...]:
    ledgers = sorted(root.rglob("TARGET_DESTINATION_LEDGER_V2.jsonl"))
    if not ledgers:
        raise ValueError("destination binding found no Target V2 ledgers")

    contexts: list[CapitalizerTargetContext] = []
    seen_sources: set[Path] = set()
    for ledger in ledgers:
        parent = ledger.parent
        if parent in seen_sources:
            continue
        seen_sources.add(parent)
        for context in load_target_contexts(parent):
            if context.symbol in NINE_MARKET_UNIVERSE:
                contexts.append(context)

    keys: set[tuple[str, CapitalizerSide, datetime]] = set()
    for context in contexts:
        key = (context.symbol, context.side, context.departure_at)
        if key in keys:
            raise ValueError("duplicate Target V2 context across downloaded artifacts")
        keys.add(key)
    return tuple(
        sorted(
            contexts,
            key=lambda item: (
                item.departure_at,
                item.symbol,
                item.side.value,
            ),
        )
    )


def _bind_rows(
    rebase_rows: tuple[dict[str, Any], ...],
    contexts: tuple[CapitalizerTargetContext, ...],
) -> tuple[DestinationEvidenceBindingRow, ...]:
    context_index = {
        (context.symbol, context.side, context.departure_at): context
        for context in contexts
    }
    if len(context_index) != len(contexts):
        raise ValueError("destination context identity must be unique")

    result: list[DestinationEvidenceBindingRow] = []
    for row in rebase_rows:
        tokens = _token_map(row)
        closeback_raw = tokens.get("M5_CLOSEBACK_AT")
        entry_at = _aware(row["entry_at"], field="entry_at")
        side = _side(row["side"])

        context: CapitalizerTargetContext | None = None
        departure_at: datetime | None = None
        if closeback_raw is not None:
            departure_at = _aware(closeback_raw, field="M5_CLOSEBACK_AT")
            context = context_index.get(
                (str(row["symbol"]), side, departure_at)
            )

        match = context is not None
        causal = bool(
            context is not None
            and departure_at is not None
            and departure_at <= entry_at
            and all(
                candidate.known_at <= departure_at
                for candidate in context.candidates
            )
        )
        bound = match and causal

        candidate_count = 0
        nearest: str | None = None
        families: tuple[str, ...] = ()
        timeframes: tuple[str, ...] = ()
        if bound:
            if context is None:
                raise AssertionError("bound target context unexpectedly missing")
            candidate_count = context.active_candidate_count
            nearest_value = context.nearest_distance_ticks
            nearest = None if nearest_value is None else str(nearest_value)
            families = context.families
            timeframes = context.timeframes

        result.append(
            DestinationEvidenceBindingRow(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                side=str(row["side"]),
                entry_at=str(row["entry_at"]),
                provenance=str(row["provenance"]),
                m5_closeback_at=closeback_raw,
                target_context_match_found=match,
                target_context_causal=causal,
                destination_evidence_at_departure_bound=bound,
                active_candidate_count_at_departure=candidate_count,
                nearest_distance_ticks_at_departure=nearest,
                candidate_families_at_departure=families,
                candidate_timeframes_at_departure=timeframes,
            )
        )
    return tuple(result)


def build_report(
    rebase_root: Path,
    target_root: Path,
) -> tuple[dict[str, Any], tuple[DestinationEvidenceBindingRow, ...]]:
    rebase_report, rebase_rows = _load_rebase(rebase_root)
    contexts = _load_all_target_contexts(target_root)
    rows = _bind_rows(rebase_rows, contexts)

    bound = tuple(
        row for row in rows if row.destination_evidence_at_departure_bound
    )
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
            "destination_evidence_bound": sum(
                row.destination_evidence_at_departure_bound
                for row in subset
            ),
        }

    by_symbol: dict[str, dict[str, int]] = {}
    for symbol in sorted({row.symbol for row in rows}):
        subset = tuple(row for row in rows if row.symbol == symbol)
        by_symbol[symbol] = {
            "trades": len(subset),
            "destination_evidence_bound": sum(
                row.destination_evidence_at_departure_bound
                for row in subset
            ),
        }

    family_counts = Counter(
        family
        for row in bound
        for family in row.candidate_families_at_departure
    )
    timeframe_counts = Counter(
        timeframe
        for row in bound
        for timeframe in row.candidate_timeframes_at_departure
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
        "target_contexts_loaded": len(contexts),
        "destination_evidence_bound_trades": len(bound),
        "destination_evidence_unbound_trades": len(rows) - len(bound),
        "destination_evidence_coverage": (
            "0"
            if not rows
            else str(Decimal(len(bound)) / Decimal(len(rows)))
        ),
        "by_provenance": by_provenance,
        "by_symbol": by_symbol,
        "candidate_family_presence_counts": dict(sorted(family_counts.items())),
        "candidate_timeframe_presence_counts": dict(
            sorted(timeframe_counts.items())
        ),
        "future_evidence_violations": future_violations,
        "target_v2_causal_non_outcome_loader_used": True,
        "post_departure_result_fields_used": False,
        "destination_context_bound_at_m5_departure_only": True,
        "between_departure_and_entry_consumption_reconstructed": False,
        "destination_intelligence_at_entry_supported": False,
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
            "MEASURE_DEPARTURE_DESTINATION_COVERAGE_THEN_RECONSTRUCT_ENTRY_TIME_CONSUMPTION"
        ),
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[DestinationEvidenceBindingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-destination-evidence-binding-audit-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-destination-evidence-binding-audit-2r-v1-rows.jsonl"
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
