"""Tri-state Perception evidence binding for true-2R Capitalizer.

The runtime perception assessor accepts booleans, but historical research cannot
legitimately coerce missing evidence into False. This audit therefore records
each perception fact as SUPPORTED_TRUE, SUPPORTED_FALSE, or UNBOUND.

Facts that can be verified from the frozen true-2R causal ledger:
- timestamps_ordered: source timestamps were proven causal by Evidence Binding V2;
- session_clock_valid: entry timestamp maps to the frozen DST-aware session;
- provenance_valid: exact source provenance is complete;
- microstructure_complete: the source microstructure binding is complete.

Facts deliberately left UNBOUND in historical replay:
- quote_fresh: live feed age/latency was not recorded in the historical corpus;
- bars_complete: source ledgers prove causal observations, not a no-gap contract
  for every raw bar required by runtime perception.

The audit never calls assess_perception_integrity with fabricated booleans.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_regime_evidence_binding_audit_2r_v1 as regime_binding,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PERCEPTION_EVIDENCE_BINDING_AUDIT_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"


class PerceptionEvidenceState(StrEnum):
    SUPPORTED_TRUE = "SUPPORTED_TRUE"
    SUPPORTED_FALSE = "SUPPORTED_FALSE"
    UNBOUND = "UNBOUND"


@dataclass(frozen=True, slots=True)
class PerceptionEvidenceBindingRow:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    provenance: str
    quote_fresh: PerceptionEvidenceState
    bars_complete: PerceptionEvidenceState
    timestamps_ordered: PerceptionEvidenceState
    session_clock_valid: PerceptionEvidenceState
    provenance_valid: PerceptionEvidenceState
    microstructure_complete: PerceptionEvidenceState
    known_hard_integrity_failure: bool
    full_perception_status_supported: bool = False
    current_trade_outcome_visible_to_binding: bool = False


def _state(value: bool) -> PerceptionEvidenceState:
    return (
        PerceptionEvidenceState.SUPPORTED_TRUE
        if value
        else PerceptionEvidenceState.SUPPORTED_FALSE
    )


def _build_rows(
    rebase_rows: tuple[dict[str, Any], ...],
) -> tuple[PerceptionEvidenceBindingRow, ...]:
    result: list[PerceptionEvidenceBindingRow] = []
    for row in rebase_rows:
        entry_at = regime_binding._aware(row["entry_at"], field="entry_at")
        session = CapitalizerSession(str(row["session"]))
        classified = capitalizer_session_at(entry_at)

        timestamps_ordered = _state(bool(row["source_timestamps_causal"]))
        session_clock_valid = _state(classified is session)
        provenance_valid = _state(bool(row["evidence_provenance_complete"]))
        microstructure_complete = _state(bool(row["source_microstructure_bound"]))

        known_hard_failure = any(
            state is PerceptionEvidenceState.SUPPORTED_FALSE
            for state in (
                timestamps_ordered,
                session_clock_valid,
                provenance_valid,
            )
        )

        result.append(
            PerceptionEvidenceBindingRow(
                symbol=str(row["symbol"]),
                session=session.value,
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                provenance=str(row["provenance"]),
                quote_fresh=PerceptionEvidenceState.UNBOUND,
                bars_complete=PerceptionEvidenceState.UNBOUND,
                timestamps_ordered=timestamps_ordered,
                session_clock_valid=session_clock_valid,
                provenance_valid=provenance_valid,
                microstructure_complete=microstructure_complete,
                known_hard_integrity_failure=known_hard_failure,
            )
        )
    return tuple(result)


def _counts(
    rows: tuple[PerceptionEvidenceBindingRow, ...],
    field: str,
) -> dict[str, int]:
    values = Counter(str(getattr(row, field)) for row in rows)
    return {
        state.value: values.get(state.value, 0)
        for state in PerceptionEvidenceState
    }


def build_report(
    rebase_root: Path,
) -> tuple[dict[str, Any], tuple[PerceptionEvidenceBindingRow, ...]]:
    rebase_report, rebase_rows = regime_binding._load_rebase(rebase_root)
    rows = _build_rows(rebase_rows)

    facts = (
        "quote_fresh",
        "bars_complete",
        "timestamps_ordered",
        "session_clock_valid",
        "provenance_valid",
        "microstructure_complete",
    )
    by_fact = {field: _counts(rows, field) for field in facts}

    known_hard_failures = sum(row.known_hard_integrity_failure for row in rows)
    all_known_causal_integrity_true = sum(
        row.timestamps_ordered is PerceptionEvidenceState.SUPPORTED_TRUE
        and row.session_clock_valid is PerceptionEvidenceState.SUPPORTED_TRUE
        and row.provenance_valid is PerceptionEvidenceState.SUPPORTED_TRUE
        and row.microstructure_complete is PerceptionEvidenceState.SUPPORTED_TRUE
        for row in rows
    )

    by_market: dict[str, dict[str, int]] = {}
    for symbol in sorted({row.symbol for row in rows}):
        subset = tuple(row for row in rows if row.symbol == symbol)
        by_market[symbol] = {
            "trades": len(subset),
            "known_hard_integrity_failures": sum(
                row.known_hard_integrity_failure for row in subset
            ),
            "known_causal_integrity_true": sum(
                row.timestamps_ordered is PerceptionEvidenceState.SUPPORTED_TRUE
                and row.session_clock_valid is PerceptionEvidenceState.SUPPORTED_TRUE
                and row.provenance_valid is PerceptionEvidenceState.SUPPORTED_TRUE
                and row.microstructure_complete
                is PerceptionEvidenceState.SUPPORTED_TRUE
                for row in subset
            ),
        }

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "fact_state_counts": by_fact,
        "known_hard_integrity_failure_trades": known_hard_failures,
        "known_causal_integrity_true_trades": all_known_causal_integrity_true,
        "by_market": by_market,
        "quote_fresh_evidence_bound": False,
        "bars_complete_evidence_bound": False,
        "timestamps_ordered_evidence_bound": True,
        "session_clock_evidence_bound": True,
        "provenance_evidence_bound": True,
        "microstructure_complete_evidence_bound": True,
        "runtime_perception_assessor_called": False,
        "full_perception_status_supported_trades": 0,
        "unknown_evidence_coerced_to_false": False,
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
            "BIND_HISTORICAL_BAR_COMPLETENESS_OR_CENSUS_REMAINING_COGNITIVE_BLOCKERS"
        ),
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[PerceptionEvidenceBindingRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.rebase_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
