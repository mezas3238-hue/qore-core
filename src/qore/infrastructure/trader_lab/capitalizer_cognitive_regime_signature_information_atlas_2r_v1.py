"""Information-value atlas for outcome-free M5 regime evidence at true 2R.

Consumes the true-2R economic rebase and the successful Regime Evidence Binding
Audit. The only new causal feature tested here is the already-observed categorical
M5 microstructure signature. No regime family is named and no numeric threshold is
invented.

For each bound signature the atlas reports:
- cohort economics;
- full-portfolio counterfactual if that signature were abstained;
- stop capture, winner sacrifice and density retention.

The current trade outcome is attached only after signature membership is frozen.
No signature is selected or promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_REGIME_SIGNATURE_INFORMATION_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_REGIME_BINDING_RUN_ID = 36084861252
SOURCE_REGIME_BINDING_SHA = "d1dae0c77512b49ba8817a3ba896ec73801e30da"

MIN_DESCRIPTIVE_SUPPORT = 20
DD_CEILING = Decimal("6")
MIN_DENSITY = Decimal("0.95")


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    return regime_binding._load_rebase(root)


def _load_regime_binding(
    root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1.json"
        )
    )
    row_paths = sorted(
        root.rglob(
            "capitalizer-cognitive-regime-evidence-binding-audit-2r-v1-rows.jsonl"
        )
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("signature atlas requires one regime binding artifact")

    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != regime_binding.IDENTITY:
        raise ValueError("unexpected regime binding identity")
    if report.get("regime_family_id_selected") is not False:
        raise ValueError("signature atlas requires unnamed regimes")
    if report.get("regime_intelligence_supported") is not False:
        raise ValueError("signature atlas requires descriptive evidence only")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("signature atlas rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("regime binding row must be object")
                rows.append(raw)
    if len(rows) != int(report.get("control_trades", -1)):
        raise ValueError("regime binding row count mismatch")
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


def build_report(
    rebase_root: Path,
    regime_root: Path,
) -> dict[str, Any]:
    rebase_report, rebase_rows = _load_rebase(rebase_root)
    regime_report, regime_rows = _load_regime_binding(regime_root)

    control = tuple(_trade(row) for row in rebase_rows)
    trade_by_key = {_join_key(row): row for row in control}
    regime_by_key = {_join_key(row): row for row in regime_rows}
    if len(trade_by_key) != len(control) or len(regime_by_key) != len(regime_rows):
        raise ValueError("signature atlas requires unique trade identities")
    if set(trade_by_key) != set(regime_by_key):
        raise ValueError("rebase/regime identities differ")

    bound_keys = frozenset(
        key
        for key, row in regime_by_key.items()
        if row.get("regime_evidence_bound") is True
    )
    unbound_keys = frozenset(set(trade_by_key) - set(bound_keys))

    members: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for key in bound_keys:
        signature = regime_by_key[key].get("microstructure_signature")
        if not isinstance(signature, str) or not signature:
            raise ValueError("bound regime row requires microstructure signature")
        members[signature].add(key)

    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(
        Decimal(str(row["realized_gross_r"])) > 0 for row in control
    )

    cells: list[dict[str, Any]] = []
    for signature, keys in sorted(members.items()):
        cohort = tuple(row for row in control if _join_key(row) in keys)
        kept = tuple(row for row in control if _join_key(row) not in keys)
        stops = sum(str(row["exit_reason"]) == "STOP" for row in cohort)
        wins = sum(
            Decimal(str(row["realized_gross_r"])) > 0 for row in cohort
        )
        metrics = stoprisk_2r._metrics(cohort)
        counterfactual = stoprisk_2r._metrics(kept)
        density = Decimal(len(kept)) / Decimal(len(control))
        cells.append(
            {
                "signature": signature,
                "trades": len(cohort),
                "descriptive_support_met": len(cohort) >= MIN_DESCRIPTIVE_SUPPORT,
                "stops": stops,
                "wins": wins,
                "cell_metrics": metrics,
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

    bound_trades = tuple(
        row for row in control if _join_key(row) in bound_keys
    )
    unbound_trades = tuple(
        row for row in control if _join_key(row) in unbound_keys
    )

    supported_cells = tuple(
        row for row in cells if row["descriptive_support_met"]
    )
    useful_cells = tuple(
        row
        for row in cells
        if row["descriptive_support_met"]
        and row["counterfactual_at_or_below_6r_dd"]
        and row["counterfactual_density_at_least_95pct"]
    )

    unmatched_token_rows = sum(
        row.get("m5_closeback_at") is not None
        and row.get("micro_context_match_found") is False
        for row in regime_rows
    )
    no_token_rows = sum(
        row.get("m5_closeback_at") is None for row in regime_rows
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_regime_binding_run_id": SOURCE_REGIME_BINDING_RUN_ID,
        "source_regime_binding_sha": SOURCE_REGIME_BINDING_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "regime_evidence_bound_trades": len(bound_trades),
        "regime_evidence_unbound_trades": len(unbound_trades),
        "bound_metrics": stoprisk_2r._metrics(bound_trades),
        "unbound_metrics": stoprisk_2r._metrics(unbound_trades),
        "unbound_reason_counts": {
            "NO_M5_CLOSEBACK_TOKEN": no_token_rows,
            "TOKEN_WITHOUT_EXACT_CONTEXT_MATCH": unmatched_token_rows,
        },
        "signature_cell_count": len(cells),
        "minimum_descriptive_support": MIN_DESCRIPTIVE_SUPPORT,
        "supported_signature_cell_count": len(supported_cells),
        "cells": cells,
        "supported_cells_at_or_below_6r_with_95pct_density": len(useful_cells),
        "signature_membership_known_by_entry": True,
        "numeric_microstructure_thresholds_added": False,
        "regime_family_id_selected": False,
        "regime_intelligence_supported": False,
        "current_outcome_used_to_define_signature": False,
        "current_outcome_used_for_post_signature_metrics": True,
        "automatic_signature_selection": False,
        "runtime_rule_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
        ),
        "regime_binding_control_reproduced": (
            int(regime_report["control_trades"]) == len(control)
            and int(regime_report["regime_evidence_bound_trades"])
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
            "IF_SIGNATURE_INFORMATION_VALUE_IS_INSUFFICIENT_BIND_DESTINATION_OR_PERCEPTION"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-regime-signature-information-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("regime_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.rebase_root, args.regime_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
