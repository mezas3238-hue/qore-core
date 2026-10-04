#!/usr/bin/env python3
"""Evaluate MC-28 execution-quality deterioration from sealed real evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.execution_quality_deterioration_diagnostic import (
    IDENTITY,
    ExecutionQualityObservation,
    ExecutionQualityOutcome,
    ExecutionQualitySide,
    assess_execution_quality,
)


def _load(path: Path) -> tuple[ExecutionQualityObservation, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("execution-quality evidence must be a JSON list")
    rows: list[ExecutionQualityObservation] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("execution-quality row must be an object")
        row: dict[str, Any] = item
        rows.append(
            ExecutionQualityObservation(
                observation_id=str(row["observation_id"]),
                instrument=str(row["instrument"]),
                side=ExecutionQualitySide(str(row["side"])),
                outcome=ExecutionQualityOutcome(str(row["outcome"])),
                observed_at=datetime.fromisoformat(str(row["observed_at"])),
                quote_bid=Decimal(str(row["quote_bid"])),
                quote_ask=Decimal(str(row["quote_ask"])),
                fill_price=(
                    None
                    if row.get("fill_price") is None
                    else Decimal(str(row["fill_price"]))
                ),
                evidence_ref=str(row["evidence_ref"]),
            )
        )
    return tuple(rows)


def _metrics(value):
    if value is None:
        return None
    return {
        "attempt_count": value.attempt_count,
        "fill_count": value.fill_count,
        "rejection_count": value.rejection_count,
        "median_spread_bps": value.median_spread_bps,
        "p90_adverse_slippage_bps": value.p90_adverse_slippage_bps,
        "rejection_rate_bps": value.rejection_rate_bps,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--recent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    assessment = assess_execution_quality(
        baseline=_load(args.baseline),
        recent=_load(args.recent),
    )
    payload = {
        "identity": IDENTITY,
        "status": assessment.status.value,
        "instrument": assessment.instrument,
        "baseline": _metrics(assessment.baseline),
        "recent": _metrics(assessment.recent),
        "spread_ratio_bps": assessment.spread_ratio_bps,
        "spread_uplift_bps": assessment.spread_uplift_bps,
        "p90_slippage_uplift_bps": (
            assessment.p90_slippage_uplift_bps
        ),
        "rejection_rate_uplift_bps": (
            assessment.rejection_rate_uplift_bps
        ),
        "reason_codes": list(assessment.reason_codes),
        "execution_quality_completed_and_proven": (
            assessment.diagnostic_pass
        ),
        "mc28_completed_and_proven": assessment.diagnostic_pass,
        "real_execution_evidence_required": True,
        "synthetic_or_simulated_closure_allowed": False,
        "broker_mutation": False,
        "order_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "protected_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "status": payload["status"],
                "instrument": payload["instrument"],
                "execution_quality_completed_and_proven": (
                    payload["execution_quality_completed_and_proven"]
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
