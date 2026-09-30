"""Perception bars-complete binding V2 for true-2R Capitalizer.

Consumes:
- the frozen tri-state Perception Evidence Binding V1;
- the nine-market historical native-M1 completeness audit;
- the AUDJPY provider tick absence revalidation.

This adapter promotes only the historical bars_complete fact:
- historical SUPPORTED_TRUE remains SUPPORTED_TRUE;
- historical SUPPORTED_FALSE remains SUPPORTED_FALSE;
- historical UNBOUND can become SUPPORTED_TRUE only when every absent minute for
  that exact trade span is revalidated as zero BID and zero ASK ticks.

quote_fresh remains UNBOUND because historical data cannot prove live feed age.
The runtime perception assessor is therefore still not called and full perception
status remains unsupported. No outcome fields are read.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_historical_bar_completeness_audit_2r_v1 as bars,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_evidence_binding_audit_2r_v1 as perception_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_provider_absence_tick_revalidation_2r_v1 as ticks,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PERCEPTION_BARS_COMPLETE_BINDING_2R_V2"
SOURCE_PERCEPTION_RUN_ID = 36087252085
SOURCE_PERCEPTION_SHA = "f28bf5238d84a1b5ea3bd61d2598ce465a537456"
SOURCE_BAR_RUN_ID = 36174145194
SOURCE_BAR_SHA = "0595c3b9e22c381aba04a5c69ea9eb97065b6aa8"


@dataclass(frozen=True, slots=True)
class PerceptionBarsCompleteV2Row:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    provenance: str
    quote_fresh: str
    bars_complete: str
    timestamps_ordered: str
    session_clock_valid: str
    provenance_valid: str
    microstructure_complete: str
    bars_complete_source: str
    known_hard_integrity_failure: bool
    full_perception_status_supported: bool = False
    current_trade_outcome_visible_to_binding: bool = False


def _load_perception(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(
        root.rglob(
            "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1.json"
        )
    )
    row_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1-rows.jsonl"
        )
    )
    if len(reports) != 1 or len(row_paths) != 1:
        raise ValueError("Perception V2 requires one Perception V1 artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != perception_v1.IDENTITY:
        raise ValueError("unexpected Perception V1 identity")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("Perception V1 row must be object")
                rows.append(raw)
    if len(rows) != int(report.get("control_trades", -1)):
        raise ValueError("Perception V1 row population mismatch")
    return report, tuple(rows)


def _load_bar_rows(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-historical-bar-completeness-audit-2r-v1-rows.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError("Perception V2 requires nine historical bar row ledgers")

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("historical bar row must be object")
                key = (str(raw["symbol"]), str(raw["entry_at"]))
                if key in result:
                    raise ValueError("historical bar row identity must be unique")
                result[key] = raw
    return result


def _load_tick_resolution(
    root: Path,
) -> tuple[dict[str, Any], dict[str, tuple[dict[str, Any], ...]]]:
    reports = sorted(
        root.rglob(
            "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1.json"
        )
    )
    row_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1-rows.jsonl"
        )
    )
    if len(reports) != 1 or len(row_paths) != 1:
        raise ValueError("Perception V2 requires one provider tick artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != ticks.IDENTITY:
        raise ValueError("unexpected tick revalidation identity")

    grouped: dict[str, list[dict[str, Any]]] = {}
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("tick revalidation row must be object")
            grouped.setdefault(str(raw["entry_at"]), []).append(raw)
    return report, {
        key: tuple(sorted(value, key=lambda item: str(item["minute"])))
        for key, value in grouped.items()
    }


def _resolved_unbound(
    *,
    bar_row: dict[str, Any],
    tick_report: dict[str, Any],
    tick_rows: dict[str, tuple[dict[str, Any], ...]],
) -> bool:
    if str(bar_row["symbol"]) != ticks.SYMBOL:
        return False
    entry_at = str(bar_row["entry_at"])
    evidence = tick_rows.get(entry_at, ())
    if len(evidence) != int(bar_row["missing_calendar_minutes"]):
        return False
    if tick_report.get("all_native_m1_absences_explained_by_no_ticks") is not True:
        return False
    return bool(evidence) and all(
        row.get("provider_no_ticks") is True
        and row.get("contradiction_ticks_without_trendbar") is False
        and row.get("bid_has_more") is False
        and row.get("ask_has_more") is False
        for row in evidence
    )


def build_report(
    perception_root: Path,
    bar_root: Path,
    tick_root: Path,
) -> tuple[dict[str, Any], tuple[PerceptionBarsCompleteV2Row, ...]]:
    perception_report, perception_rows = _load_perception(perception_root)
    bar_rows = _load_bar_rows(bar_root)
    tick_report, tick_rows = _load_tick_resolution(tick_root)

    result: list[PerceptionBarsCompleteV2Row] = []
    for row in perception_rows:
        key = (str(row["symbol"]), str(row["entry_at"]))
        bar_row = bar_rows.get(key)
        if bar_row is None:
            raise ValueError("Perception V2 missing historical bar counterpart")

        bar_state = str(bar_row["state"])
        if bar_state == bars.BarCompletenessState.SUPPORTED_TRUE.value:
            bars_complete = perception_v1.PerceptionEvidenceState.SUPPORTED_TRUE.value
            source = "HISTORICAL_NATIVE_M1_CONTIGUOUS"
        elif bar_state == bars.BarCompletenessState.SUPPORTED_FALSE.value:
            bars_complete = perception_v1.PerceptionEvidenceState.SUPPORTED_FALSE.value
            source = "HISTORICAL_NATIVE_M1_HARD_CONTRADICTION"
        elif (
            bar_state == bars.BarCompletenessState.UNBOUND.value
            and _resolved_unbound(
                bar_row=bar_row,
                tick_report=tick_report,
                tick_rows=tick_rows,
            )
        ):
            bars_complete = perception_v1.PerceptionEvidenceState.SUPPORTED_TRUE.value
            source = "PROVIDER_BID_ASK_NO_TICKS"
        else:
            bars_complete = perception_v1.PerceptionEvidenceState.UNBOUND.value
            source = "UNBOUND"

        known_hard_failure = bool(row["known_hard_integrity_failure"]) or (
            bars_complete
            == perception_v1.PerceptionEvidenceState.SUPPORTED_FALSE.value
        )
        result.append(
            PerceptionBarsCompleteV2Row(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                provenance=str(row["provenance"]),
                quote_fresh=str(row["quote_fresh"]),
                bars_complete=bars_complete,
                timestamps_ordered=str(row["timestamps_ordered"]),
                session_clock_valid=str(row["session_clock_valid"]),
                provenance_valid=str(row["provenance_valid"]),
                microstructure_complete=str(row["microstructure_complete"]),
                bars_complete_source=source,
                known_hard_integrity_failure=known_hard_failure,
            )
        )

    rows = tuple(result)
    bar_counts = Counter(row.bars_complete for row in rows)
    source_counts = Counter(row.bars_complete_source for row in rows)
    supported = perception_v1.PerceptionEvidenceState.SUPPORTED_TRUE.value
    unbound = perception_v1.PerceptionEvidenceState.UNBOUND.value
    fully_known_except_quote = sum(
        row.bars_complete == supported
        and row.timestamps_ordered == supported
        and row.session_clock_valid == supported
        and row.provenance_valid == supported
        and row.microstructure_complete == supported
        for row in rows
    )

    return {
        "identity": IDENTITY,
        "source_perception_run_id": SOURCE_PERCEPTION_RUN_ID,
        "source_perception_sha": SOURCE_PERCEPTION_SHA,
        "source_bar_run_id": SOURCE_BAR_RUN_ID,
        "source_bar_sha": SOURCE_BAR_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "bars_complete_state_counts": {
            state.value: bar_counts.get(state.value, 0)
            for state in perception_v1.PerceptionEvidenceState
        },
        "bars_complete_source_counts": dict(sorted(source_counts.items())),
        "known_hard_integrity_failure_trades": sum(
            row.known_hard_integrity_failure for row in rows
        ),
        "fully_known_integrity_except_quote_fresh_trades": fully_known_except_quote,
        "bars_complete_evidence_bound": bar_counts.get(unbound, 0) == 0,
        "quote_fresh_evidence_bound": False,
        "runtime_perception_assessor_called": False,
        "full_perception_status_supported_trades": 0,
        "provider_tick_resolution_used": True,
        "provider_tick_all_absences_explained": bool(
            tick_report.get("all_native_m1_absences_explained_by_no_ticks")
        ),
        "unknown_evidence_coerced_to_false": False,
        "current_trade_outcome_visible_to_binding": False,
        "missing_evidence_fabricated": False,
        "perception_v1_control_reproduced": (
            int(perception_report["control_trades"]) == len(rows)
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
            "QUOTE_FRESH_REMAINS_HISTORICALLY_UNBOUND; "
            "REPLAY_MASTER_COGNITION_WITH_BARS_COMPLETE_BOUND_ONLY"
        ),
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[PerceptionBarsCompleteV2Row, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-perception-bars-complete-binding-2r-v2.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-perception-bars-complete-binding-2r-v2-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("perception_root", type=Path)
    parser.add_argument("bar_root", type=Path)
    parser.add_argument("tick_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(
        args.perception_root,
        args.bar_root,
        args.tick_root,
    )
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
