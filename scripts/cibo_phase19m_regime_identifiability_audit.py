"""Audit whether burned Phase-19 evidence can causally identify CE2I T12.

The audit is schema/observability only. It never consumes trade outcomes and
therefore cannot tune or promote a regime policy.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_regime_identifiability import (
    CANONICAL_REGIME_FIELDS,
    VT31_BESPOKE_REGIME_FIELDS,
    audit_phase19_regime_rows,
    build_phase19_regime_identifiability,
)

EXPECTED_CANONICAL_LINEAGES = (
    TraderLineage.R38_GBPJPY,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R42_AUDJPY,
)
EXPECTED_BESPOKE_UNMAPPED_LINEAGES = (TraderLineage.VT31_NAS100,)
EXPECTED_MISSING_LINEAGES = (
    TraderLineage.R38_EURUSD,
    TraderLineage.R34_XAUUSD,
    TraderLineage.VT08_FOREX,
)


def _common_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    selected: list[dict[str, Any]] = []
    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        if signal_at > entry_at:
            raise ValueError("Phase19M signal occurs after entry")
        if entry_at >= common_start and exit_at <= common_end:
            selected.append(row)
    return tuple(selected)


def run(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase19M source set drift")

    audits = []
    source_evidence: dict[str, Any] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19M source row-count drift"
            )
        common = _common_rows(rows)
        if len(common) != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19M common row-count drift"
            )
        audits.append(
            audit_phase19_regime_rows(
                trader_id=spec.trader_id,
                rows=common,
            )
        )
        source_evidence[key] = {
            "trader_id": spec.trader_id.value,
            "artifact_id": spec.artifact_id,
            "artifact_digest": spec.artifact_digest,
            "common_rows": len(common),
        }

    evidence = build_phase19_regime_identifiability(tuple(audits))
    if tuple(evidence.canonical_lineages) != EXPECTED_CANONICAL_LINEAGES:
        raise ValueError("Phase19M canonical regime lineage drift")
    if (
        tuple(evidence.bespoke_unmapped_lineages)
        != EXPECTED_BESPOKE_UNMAPPED_LINEAGES
    ):
        raise ValueError("Phase19M bespoke regime lineage drift")
    if tuple(evidence.missing_lineages) != EXPECTED_MISSING_LINEAGES:
        raise ValueError("Phase19M missing regime lineage drift")
    if evidence.portfolio_regime_state_identified:
        raise ValueError("Phase19M must not silently identify portfolio T12")

    by_trader = {
        item.trader_id.value: {
            "row_count": item.row_count,
            "canonical_regime_rows": item.canonical_regime_rows,
            "bespoke_regime_rows": item.bespoke_regime_rows,
            "missing_regime_rows": item.missing_regime_rows,
            "evidence_class": item.evidence_class.value,
        }
        for item in evidence.lineages
    }

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19m.regime_identifiability.v1",
        "identity": "CIBO_PHASE19M_REGIME_IDENTIFIABILITY_AUDIT_V1",
        "status": "PORTFOLIO_REGIME_IDENTIFIABILITY_BLOCKED_PARTIAL_3_OF_7",
        "common_window": {
            "start": EXPECTED_COMMON_START,
            "end": EXPECTED_COMMON_END,
            "fully_observed_intervals_only": True,
        },
        "canonical_shared_schema": {
            "fields": list(CANONICAL_REGIME_FIELDS),
            "lineages": [
                item.value for item in evidence.canonical_lineages
            ],
            "lineage_count": len(evidence.canonical_lineages),
        },
        "bespoke_unmapped_schema": {
            "fields": list(VT31_BESPOKE_REGIME_FIELDS),
            "lineages": [
                item.value for item in evidence.bespoke_unmapped_lineages
            ],
            "lineage_count": len(evidence.bespoke_unmapped_lineages),
        },
        "missing_shared_schema": {
            "lineages": [item.value for item in evidence.missing_lineages],
            "lineage_count": len(evidence.missing_lineages),
        },
        "lineage_audit": by_trader,
        "t12_required_evidence": {
            "causal_regime_state": "PARTIAL_CANONICAL_COVERAGE_3_OF_7",
            "tool_eligibility_contract": "IMPLEMENTED_NOT_EMPIRICALLY_CALIBRATED",
            "account_state": "RECONSTRUCTIBLE_BUT_NOT_BOUND_TO_SHARED_REGIME_SCHEMA",
            "provider_condition": "HISTORICAL_PROVIDER_STATE_NOT_BOUND",
        },
        "source_evidence": source_evidence,
        "interpretation": {
            "portfolio_regime_state_identified": False,
            "t12_calibration_promotion_from_this_report": False,
            "canonical_mapping_for_vt31_required": True,
            "shared_predecision_regime_schema_for_missing_lineages_required": True,
            "account_state_join_required": True,
            "fresh_oos_regime_generalization_required": True,
        },
        "governance": {
            "trade_outcomes_read": False,
            "outcome_fields_used": [],
            "holdout_2017h1_used": False,
            "historical_provider_usd_claimed": False,
            "regime_thresholds_fit": False,
            "policy_certified": False,
            "oos_ready": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        paths={key: getattr(args, key) for key in SOURCE_SPECS},
        output_path=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
