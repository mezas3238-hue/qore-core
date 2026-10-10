"""Information-value atlas for strict departure-time Destination evidence at true 2R.

Consumes the true-2R cognitive rebase and the strict Destination Departure Binding
Audit. Only trades with an exact causal Target V2 departure context are assigned
Destination feature cells.

Important governance:
- UNBOUND never means "no destination";
- touch/result fields remain unused;
- no distance threshold or target optimization is introduced;
- destination persistence to the later M1 entry remains unproven;
- cells are descriptive consumed-window diagnostics only.

The atlas tests categorical facts already present in the bound context:
candidate-family signature, timeframe signature, exact active-candidate count,
family count, and timeframe count.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_destination_departure_binding_audit_2r_v1 as binding,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_DESTINATION_DEPARTURE_INFORMATION_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_DESTINATION_RUN_ID = 36085887285
SOURCE_DESTINATION_SHA = "c0529ca61dfd57cc7f3168bcee68751ef5651335"

MIN_DESCRIPTIVE_SUPPORT = 5
DD_CEILING = Decimal("6")
MIN_DENSITY = Decimal("0.95")


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_destination_binding(
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
        raise ValueError("Destination information atlas requires one binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding.IDENTITY:
        raise ValueError("unexpected Destination binding identity")
    if report.get("target_result_fields_read") is not False:
        raise ValueError("Destination information atlas rejects result-field reads")
    if report.get("target_touch_fields_used") is not False:
        raise ValueError("Destination information atlas rejects touch-field use")
    if report.get("destination_current_at_entry_supported") is not False:
        raise ValueError("Destination information atlas requires departure-only evidence")
    if report.get("destination_available_at_entry_supported") is not False:
        raise ValueError("Destination information atlas cannot assume entry availability")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("Destination information atlas rejects future evidence")

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
        raise ValueError("Destination binding row count mismatch")
    return report, tuple(rows)


def _trade(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(row["symbol"]),
        "session": str(row["session"]),
        "operating_date": str(row["operating_date"]),
        "side": str(row["side"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["post_audit_exit_at"]),
        "realized_gross_r": str(row["post_audit_realized_gross_r"]),
        "exit_reason": str(row["post_audit_exit_reason"]),
    }


def _bound_cells(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    if row.get("destination_departure_evidence_bound") is not True:
        return ()
    families = tuple(str(item) for item in row["candidate_families"])
    timeframes = tuple(str(item) for item in row["candidate_timeframes"])
    count = int(row["active_candidate_count"])
    if count <= 0 or not families or not timeframes:
        raise ValueError("bound Destination row requires categorical evidence")
    return (
        ("CANDIDATE_FAMILY_SIGNATURE", "+".join(families)),
        ("CANDIDATE_TIMEFRAME_SIGNATURE", "+".join(timeframes)),
        ("ACTIVE_CANDIDATE_COUNT", str(count)),
        ("CANDIDATE_FAMILY_COUNT", str(len(families))),
        ("CANDIDATE_TIMEFRAME_COUNT", str(len(timeframes))),
    )


def build_report(
    rebase_root: Path,
    destination_root: Path,
) -> dict[str, Any]:
    rebase_report, rebase_rows = regime_binding._load_rebase(rebase_root)
    destination_report, destination_rows = _load_destination_binding(
        destination_root
    )

    control = tuple(_trade(row) for row in rebase_rows)
    trade_by_key = {_join_key(row): row for row in control}
    destination_by_key = {_join_key(row): row for row in destination_rows}
    if len(trade_by_key) != len(control):
        raise ValueError("Destination information trade identity not unique")
    if len(destination_by_key) != len(destination_rows):
        raise ValueError("Destination information binding identity not unique")
    if set(trade_by_key) != set(destination_by_key):
        raise ValueError("rebase/Destination identities differ")

    bound_keys = frozenset(
        key
        for key, row in destination_by_key.items()
        if row.get("destination_departure_evidence_bound") is True
    )
    unbound_keys = frozenset(set(trade_by_key) - set(bound_keys))
    bound_trades = tuple(
        row for row in control if _join_key(row) in bound_keys
    )
    unbound_trades = tuple(
        row for row in control if _join_key(row) in unbound_keys
    )

    members: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for key in bound_keys:
        for cell in _bound_cells(destination_by_key[key]):
            members[cell].add(key)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(
        Decimal(str(row["realized_gross_r"])) > 0 for row in control
    )

    cells_by_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (feature, value), keys in sorted(members.items()):
        cohort = tuple(row for row in control if _join_key(row) in keys)
        kept = tuple(row for row in control if _join_key(row) not in keys)
        stops = sum(str(row["exit_reason"]) == "STOP" for row in cohort)
        wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in cohort
        )
        density = Decimal(len(kept)) / Decimal(len(control))
        cell_metrics = stoprisk_2r._metrics(cohort)
        counterfactual = stoprisk_2r._metrics(kept)
        cells_by_feature[feature].append(
            {
                "value": value,
                "trades": len(cohort),
                "descriptive_support_met": len(cohort) >= MIN_DESCRIPTIVE_SUPPORT,
                "stops": stops,
                "wins": wins,
                "cell_metrics": cell_metrics,
                "counterfactual_if_abstained_metrics": counterfactual,
                "stop_capture_rate": (
                    "0"
                    if total_stops == 0
                    else str(Decimal(stops) / Decimal(total_stops))
                ),
                "winner_sacrifice_rate": (
                    "0"
                    if total_wins == 0
                    else str(Decimal(wins) / Decimal(total_wins))
                ),
                "density_retention_if_abstained": str(density),
                "counterfactual_at_or_below_6r_dd": (
                    Decimal(str(counterfactual["max_drawdown_r"])) <= DD_CEILING
                ),
                "counterfactual_density_at_least_95pct": density >= MIN_DENSITY,
            }
        )

    supported = tuple(
        row
        for feature_rows in cells_by_feature.values()
        for row in feature_rows
        if row["descriptive_support_met"]
    )
    useful = tuple(
        row
        for row in supported
        if row["counterfactual_at_or_below_6r_dd"]
        and row["counterfactual_density_at_least_95pct"]
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_destination_run_id": SOURCE_DESTINATION_RUN_ID,
        "source_destination_sha": SOURCE_DESTINATION_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "destination_bound_trades": len(bound_trades),
        "destination_unbound_trades": len(unbound_trades),
        "bound_metrics": stoprisk_2r._metrics(bound_trades),
        "unbound_metrics": stoprisk_2r._metrics(unbound_trades),
        "feature_count": len(cells_by_feature),
        "minimum_descriptive_support": MIN_DESCRIPTIVE_SUPPORT,
        "feature_cells": {
            feature: sorted(rows, key=lambda row: str(row["value"]))
            for feature, rows in sorted(cells_by_feature.items())
        },
        "supported_cell_count": len(supported),
        "supported_cells_at_or_below_6r_with_95pct_density": len(useful),
        "unbound_is_not_destination_absent": True,
        "nearest_distance_not_used_for_cell_selection": True,
        "numeric_destination_thresholds_added": False,
        "target_result_fields_read": False,
        "target_touch_fields_used": False,
        "destination_current_at_entry_supported": False,
        "destination_available_at_entry_supported": False,
        "destination_intelligence_supported": False,
        "current_outcome_used_to_define_cells": False,
        "current_outcome_used_for_post_cell_metrics": True,
        "automatic_cell_selection": False,
        "runtime_rule_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
        ),
        "destination_binding_control_reproduced": (
            int(destination_report["control_trades"]) == len(control)
            and int(destination_report["destination_departure_evidence_bound_trades"])
            == len(bound_trades)
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
            "IF_DEPARTURE_CONTEXT_HAS_VALUE_REVALIDATE_PERSISTENCE_TO_ENTRY_ELSE_BIND_PERCEPTION"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-destination-departure-information-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("destination_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.rebase_root, args.destination_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
