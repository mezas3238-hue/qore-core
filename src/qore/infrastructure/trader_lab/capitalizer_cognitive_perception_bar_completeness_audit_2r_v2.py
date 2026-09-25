"""Bind historical M1 bar completeness for true-2R Capitalizer Perception.

Perception V1 intentionally left ``bars_complete`` and ``quote_fresh`` UNBOUND.
This V2 audit binds only ``bars_complete`` from the immutable native-M1 clone.
For every frozen true-2R trade, each exact M1 open from H1 source-open
(inclusive) to entry (exclusive) must exist once. The native reader validates
schema, OHLC, timestamps and monotonic chronology. Historical OHLC never proves
live quote freshness, so ``quote_fresh`` remains UNBOUND.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_evidence_binding_audit_2r_v1 as v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PERCEPTION_BAR_COMPLETENESS_AUDIT_2R_V2"
MATRIX_IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PERCEPTION_BAR_COMPLETENESS_MATRIX_2R_V2"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_PERCEPTION_V1_RUN_ID = 36087252085
SOURCE_PERCEPTION_V1_SHA = "f28bf5238d84a1b5ea3bd61d2598ce465a537456"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"


@dataclass(frozen=True, slots=True)
class PerceptionBarCompletenessRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    h1_open: str
    expected_m1_bars: int
    observed_m1_bars: int
    missing_m1_bars: int
    bars_complete: str
    quote_fresh: str = v1.PerceptionEvidenceState.UNBOUND.value
    current_trade_outcome_visible_to_binding: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _load_v1(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-cognitive-perception-evidence-binding-audit-2r-v1.json"))
    if len(paths) != 1:
        raise ValueError("Perception V2 requires exactly one V1 report")
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != v1.IDENTITY:
        raise ValueError("unexpected Perception V1 identity")
    facts = report.get("fact_state_counts")
    if not isinstance(facts, dict):
        raise ValueError("Perception V1 fact counts missing")
    control = int(report.get("control_trades", -1))
    for field in ("bars_complete", "quote_fresh"):
        states = facts.get(field)
        if not isinstance(states, dict) or int(states.get("UNBOUND", -1)) != control:
            raise ValueError(f"Perception V1 {field} must remain fully UNBOUND")
    return report


def _required_opens(start: datetime, entry: datetime) -> tuple[datetime, ...]:
    seconds = (entry - start).total_seconds()
    if seconds <= 0 or seconds % 60 != 0:
        raise ValueError("H1-open-to-entry window must contain exact positive minutes")
    return tuple(start + timedelta(minutes=i) for i in range(int(seconds // 60)))


def build_market_report(
    rebase_root: Path,
    perception_v1_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[PerceptionBarCompletenessRow, ...]]:
    normalized = symbol.upper()
    rebase_report, rebase_rows = regime_binding._load_rebase(rebase_root)
    v1_report = _load_v1(perception_v1_root)
    market_rows = tuple(row for row in rebase_rows if str(row["symbol"]) == normalized)
    requirements: dict[tuple[str, str], tuple[datetime, ...]] = {}
    needed: set[datetime] = set()
    for row in market_rows:
        start = _aware(row["h1_open"], field="h1_open")
        entry = _aware(row["entry_at"], field="entry_at")
        opens = _required_opens(start, entry)
        key = (normalized, str(row["entry_at"]))
        if key in requirements:
            raise ValueError("trade identity must be unique")
        requirements[key] = opens
        needed.update(opens)

    observed: Counter[datetime] = Counter()
    for bar in iter_cibo_m1(m1_root):
        if bar.symbol != normalized:
            raise ValueError("native M1 artifact symbol mismatch")
        if bar.opened_at in needed:
            observed[bar.opened_at] += 1

    result: list[PerceptionBarCompletenessRow] = []
    for row in market_rows:
        key = (normalized, str(row["entry_at"]))
        opens = requirements[key]
        present = sum(observed[item] == 1 for item in opens)
        missing = sum(observed[item] == 0 for item in opens)
        duplicate = any(observed[item] > 1 for item in opens)
        complete = missing == 0 and not duplicate and present == len(opens)
        result.append(
            PerceptionBarCompletenessRow(
                symbol=normalized,
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                h1_open=str(row["h1_open"]),
                expected_m1_bars=len(opens),
                observed_m1_bars=present,
                missing_m1_bars=missing,
                bars_complete=(
                    v1.PerceptionEvidenceState.SUPPORTED_TRUE.value
                    if complete
                    else v1.PerceptionEvidenceState.SUPPORTED_FALSE.value
                ),
            )
        )

    rows = tuple(result)
    true_count = sum(row.bars_complete == "SUPPORTED_TRUE" for row in rows)
    false_count = len(rows) - true_count
    report = {
        "identity": IDENTITY,
        "symbol": normalized,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_perception_v1_run_id": SOURCE_PERCEPTION_V1_RUN_ID,
        "source_perception_v1_sha": SOURCE_PERCEPTION_V1_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_trades": len(rows),
        "bars_complete_supported_true": true_count,
        "bars_complete_supported_false": false_count,
        "total_expected_m1_bars": sum(row.expected_m1_bars for row in rows),
        "total_observed_m1_bars": sum(row.observed_m1_bars for row in rows),
        "total_missing_m1_bars": sum(row.missing_m1_bars for row in rows),
        "bars_complete_evidence_bound": True,
        "quote_fresh_evidence_bound": False,
        "quote_fresh_inferred_from_ohlc": False,
        "current_trade_outcome_visible_to_binding": False,
        "native_m1_full_artifact_schema_and_chronology_validated": True,
        "h1_open_to_entry_exact_minute_grid_required": True,
        "rebase_control_reproduced": int(rebase_report["control_trades"]) == len(rebase_rows),
        "perception_v1_control_reproduced": int(v1_report["control_trades"]) == len(rebase_rows),
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
    }
    return report, rows


def build_matrix(input_root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(input_root.rglob("capitalizer-*-perception-bar-completeness-audit-2r-v2.json"))
    row_paths = sorted(input_root.rglob("capitalizer-*-perception-bar-completeness-audit-2r-v2-rows.jsonl"))
    if len(reports) != 9 or len(row_paths) != 9:
        raise ValueError("Perception V2 matrix requires nine market artifacts")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    if any(not isinstance(item, dict) or item.get("identity") != IDENTITY for item in payloads):
        raise ValueError("unexpected Perception V2 market identity")
    rows: list[dict[str, Any]] = []
    for path in row_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise ValueError("Perception V2 row must be object")
                    rows.append(raw)
    if len({str(item["symbol"]) for item in payloads}) != 9:
        raise ValueError("Perception V2 matrix requires nine unique markets")
    if len({(str(row["symbol"]), str(row["entry_at"])) for row in rows}) != len(rows):
        raise ValueError("Perception V2 matrix trade identity must be unique")
    states = Counter(str(row["bars_complete"]) for row in rows)
    if states["SUPPORTED_TRUE"] + states["SUPPORTED_FALSE"] != len(rows):
        raise ValueError("bars_complete must be fully bound")
    true_count = states["SUPPORTED_TRUE"]
    false_count = states["SUPPORTED_FALSE"]
    report = {
        "identity": MATRIX_IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_perception_v1_run_id": SOURCE_PERCEPTION_V1_RUN_ID,
        "source_perception_v1_sha": SOURCE_PERCEPTION_V1_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_count": 9,
        "control_trades": len(rows),
        "bars_complete_state_counts": {
            "SUPPORTED_TRUE": true_count,
            "SUPPORTED_FALSE": false_count,
            "UNBOUND": 0,
        },
        "bars_complete_evidence_bound": True,
        "quote_fresh_evidence_bound": False,
        "quote_fresh_inferred_from_ohlc": False,
        "full_perception_status_bad_due_bar_integrity_trades": false_count,
        "perception_status_pending_quote_freshness_trades": true_count,
        "by_market": {
            str(item["symbol"]): {
                "trades": int(item["market_trades"]),
                "bars_complete_supported_true": int(item["bars_complete_supported_true"]),
                "bars_complete_supported_false": int(item["bars_complete_supported_false"]),
                "missing_m1_bars": int(item["total_missing_m1_bars"]),
            }
            for item in sorted(payloads, key=lambda item: str(item["symbol"]))
        },
        "total_expected_m1_bars": sum(int(item["total_expected_m1_bars"]) for item in payloads),
        "total_observed_m1_bars": sum(int(item["total_observed_m1_bars"]) for item in payloads),
        "total_missing_m1_bars": sum(int(item["total_missing_m1_bars"]) for item in payloads),
        "native_m1_full_artifact_schema_and_chronology_validated": True,
        "h1_open_to_entry_exact_minute_grid_required": True,
        "current_trade_outcome_visible_to_binding": False,
        "unknown_quote_freshness_coerced_to_false": False,
        "missing_evidence_fabricated": False,
        "runtime_perception_assessor_called": False,
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
            "CENSUS_QUOTE_FRESHNESS_EXECUTION_BOUNDARY_AND_REMAINING_COGNITIVE_BLOCKERS"
            if false_count == 0
            else "REPAIR_OR_EXCLUDE_HISTORICAL_BAR_GAPS_BEFORE_COGNITIVE_ENFORCEMENT"
        ),
    }
    return report, tuple(sorted(rows, key=lambda row: (str(row["entry_at"]), str(row["symbol"]))))


def _write_market(report: dict[str, Any], rows: tuple[PerceptionBarCompletenessRow, ...], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    (output / f"capitalizer-{symbol}-perception-bar-completeness-audit-2r-v2.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output / f"capitalizer-{symbol}-perception-bar-completeness-audit-2r-v2-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _write_matrix(report: dict[str, Any], rows: tuple[dict[str, Any], ...], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-perception-bar-completeness-matrix-2r-v2.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output / "capitalizer-nine-market-perception-bar-completeness-matrix-2r-v2-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("rebase_root", type=Path)
    market.add_argument("perception_v1_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(args.rebase_root, args.perception_v1_root, args.m1_root, symbol=str(args.symbol))
        _write_market(report, rows, args.output)
    else:
        report, rows = build_matrix(args.input_root)
        _write_matrix(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
