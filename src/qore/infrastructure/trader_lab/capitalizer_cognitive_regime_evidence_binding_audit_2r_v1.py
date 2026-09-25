"""Causal regime-evidence binding audit for the true-2R Capitalizer set.

This adapter joins the frozen 948-trade true-2R cognitive rebase to the earlier
outcome-free V3 M3/M5 microstructure-context laboratory.

The join is deliberately narrow:
- symbol must match;
- the exact M5 closeback timestamp from the trade's causal source evidence must
  match a microstructure-context decision timestamp;
- the context timestamp must be at or before entry.

This lab binds descriptive regime evidence only. It does NOT invent a market
family, call the regime SUPPORTED, select a rule, or grant entry/capital authority.
Recovery-family trades lacking an admissible M5 closeback token remain UNBOUND.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_REGIME_EVIDENCE_BINDING_AUDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_MICRO_RUN_ID = 35805397236
SOURCE_MICRO_SHA = "e3be1ed5dda60ab3a53257287c9471ce247d2554"
SOURCE_MICRO_IDENTITY = "QORE_CAPITALIZER_V3_M3_MICROSTRUCTURE_CONTEXT_2Y_V1"


@dataclass(frozen=True, slots=True)
class RegimeEvidenceBindingRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    provenance: str
    source_family: str | None
    m5_closeback_at: str | None
    micro_context_match_found: bool
    micro_context_causal: bool
    regime_evidence_bound: bool
    microstructure_signature: str | None
    body_fraction: str | None
    close_location: str | None
    previous_range_ratio: str | None
    regime_family_id: str | None = None
    regime_intelligence_supported: bool = False
    outcome_visible_to_binding: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _token_map(row: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in row.get("microstructure_observations", ()):
        token = str(raw)
        if ":" not in token:
            continue
        key, value = token.split(":", 1)
        if key in result and result[key] != value:
            raise ValueError(f"conflicting microstructure token: {key}")
        result[key] = value
    return result


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("regime binding requires one true-2R rebase artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected true-2R rebase identity")
    if str(report.get("target_r")) != "2.00":
        raise ValueError("regime binding requires target_r=2.00")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("rebase row must be object")
                rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("regime binding rebase population mismatch")
    return report, tuple(rows)


def _load_micro_context(
    root: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    summaries = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(summaries) != 9 or len(row_paths) != 9:
        raise ValueError(
            "regime binding requires nine microstructure context ledgers"
        )

    summary_by_symbol: dict[str, dict[str, Any]] = {}
    for path in summaries:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("microstructure summary must be object")
        if payload.get("identity") != SOURCE_MICRO_IDENTITY:
            raise ValueError("unexpected microstructure context identity")
        if payload.get("outcome_used_for_selection") is not False:
            raise ValueError("regime source cannot use outcomes for selection")
        if payload.get("coverage") != "1":
            raise ValueError("regime source requires full closeback coverage")
        if int(payload.get("missing_microstructure_rows", -1)) != 0:
            raise ValueError("regime source cannot have missing context rows")
        symbol = str(payload["symbol"])
        if symbol in summary_by_symbol:
            raise ValueError("duplicate microstructure market summary")
        summary_by_symbol[symbol] = payload

    result: dict[tuple[str, str], dict[str, Any]] = {}
    row_count: Counter[str] = Counter()
    for path in row_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("microstructure context row must be object")
                if raw.get("outcome_used_for_selection") is not False:
                    raise ValueError("microstructure context row cannot use outcome")
                symbol = str(raw["symbol"])
                closeback_at = str(raw["closeback_at"])
                key = (symbol, closeback_at)
                if key in result:
                    raise ValueError("duplicate microstructure context identity")
                result[key] = raw
                row_count[symbol] += 1

    if set(row_count) != set(summary_by_symbol):
        raise ValueError("microstructure context market coverage drifted")
    for symbol, summary in summary_by_symbol.items():
        if row_count[symbol] != int(summary["context_rows"]):
            raise ValueError("microstructure row count disagrees with summary")
    return result


def _bind_rows(
    rebase_rows: tuple[dict[str, Any], ...],
    micro_index: dict[tuple[str, str], dict[str, Any]],
) -> tuple[RegimeEvidenceBindingRow, ...]:
    result: list[RegimeEvidenceBindingRow] = []
    for row in rebase_rows:
        tokens = _token_map(row)
        closeback_at = tokens.get("M5_CLOSEBACK_AT")
        entry_at = _aware(row["entry_at"], field="entry_at")
        micro = (
            None
            if closeback_at is None
            else micro_index.get((str(row["symbol"]), closeback_at))
        )
        match = micro is not None
        causal = False
        if micro is not None:
            causal = _aware(
                micro["closeback_at"],
                field="closeback_at",
            ) <= entry_at

        bound = match and causal
        result.append(
            RegimeEvidenceBindingRow(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                provenance=str(row["provenance"]),
                source_family=(
                    None
                    if row.get("source_microstructure_family") is None
                    else str(row["source_microstructure_family"])
                ),
                m5_closeback_at=closeback_at,
                micro_context_match_found=match,
                micro_context_causal=causal,
                regime_evidence_bound=bound,
                microstructure_signature=(
                    None if not bound else str(micro["microstructure_signature"])
                ),
                body_fraction=(
                    None if not bound else str(micro["body_fraction"])
                ),
                close_location=(
                    None if not bound else str(micro["close_location"])
                ),
                previous_range_ratio=(
                    None
                    if not bound or micro["previous_range_ratio"] is None
                    else str(micro["previous_range_ratio"])
                ),
            )
        )
    return tuple(result)


def build_report(
    rebase_root: Path,
    micro_root: Path,
) -> tuple[dict[str, Any], tuple[RegimeEvidenceBindingRow, ...]]:
    rebase_report, rebase_rows = _load_rebase(rebase_root)
    micro_index = _load_micro_context(micro_root)
    rows = _bind_rows(rebase_rows, micro_index)

    by_provenance: dict[str, dict[str, int]] = {}
    provenances = sorted({row.provenance for row in rows})
    for provenance in provenances:
        subset = tuple(row for row in rows if row.provenance == provenance)
        by_provenance[provenance] = {
            "trades": len(subset),
            "m5_closeback_token": sum(
                row.m5_closeback_at is not None for row in subset
            ),
            "regime_evidence_bound": sum(
                row.regime_evidence_bound for row in subset
            ),
        }

    bound = tuple(row for row in rows if row.regime_evidence_bound)
    future_violations = sum(
        row.micro_context_match_found and not row.micro_context_causal
        for row in rows
    )
    signature_counts = Counter(
        row.microstructure_signature for row in bound
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_micro_run_id": SOURCE_MICRO_RUN_ID,
        "source_micro_sha": SOURCE_MICRO_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "regime_evidence_bound_trades": len(bound),
        "regime_evidence_unbound_trades": len(rows) - len(bound),
        "regime_evidence_coverage": str(
            len(bound) / len(rows) if rows else 0
        ),
        "by_provenance": by_provenance,
        "bound_signature_counts": dict(
            sorted(
                (
                    str(key),
                    value,
                )
                for key, value in signature_counts.items()
            )
        ),
        "future_evidence_violations": future_violations,
        "micro_context_rows_available": len(micro_index),
        "micro_context_outcome_free": True,
        "regime_family_id_selected": False,
        "regime_intelligence_supported": False,
        "descriptive_regime_evidence_only": True,
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
        "next_phase": "FALSIFY_BOUND_MICRO_CONTEXT_INFORMATION_VALUE_WITHOUT_NAMING_REGIMES",
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[RegimeEvidenceBindingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("micro_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.rebase_root, args.micro_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
