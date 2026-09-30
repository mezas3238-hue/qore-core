"""Emit Phase20J-A adversarial failure-engineering contract evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_failure_engineering import (
    run_phase20j_failure_engineering,
)


def build_report() -> dict[str, Any]:
    with TemporaryDirectory(prefix="qore-cibo-phase20j-a-") as tmp:
        report = run_phase20j_failure_engineering(root=Path(tmp))

    dispositions: dict[str, int] = {}
    for item in report.probes:
        dispositions[item.disposition.value] = (
            dispositions.get(item.disposition.value, 0) + 1
        )

    return {
        "schema": "qore.cibo.phase20j_a.failure_engineering.v1",
        "identity": report.identity,
        "status": (
            "CONTRACT_GREEN"
            if all(item.passed for item in report.probes)
            else "CONTRACT_FAILED"
        ),
        "summary": {
            "probe_count": len(report.probes),
            "passed_probe_count": sum(item.passed for item in report.probes),
            "disposition_counts": dispositions,
        },
        "probes": [
            {
                "probe_id": item.probe_id,
                "disposition": item.disposition.value,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in report.probes
        ],
        "governance": {
            "synthetic_contract_evidence_only": (
                report.synthetic_contract_evidence_only
            ),
            "market_probability_claimed": report.market_probability_claimed,
            "historical_provider_economics_claimed": (
                report.historical_provider_economics_claimed
            ),
            "phase19j_burned_validation_reused": (
                report.phase19j_burned_validation_reused
            ),
            "policy_certified": report.policy_certified,
            "allocation_authority": report.allocation_authority,
            "risk_authority": report.risk_authority,
            "execution_authority": report.execution_authority,
            "demo_execution_authorized": report.demo_execution_authorized,
            "live_authorized": report.live_authorized,
            "real_capital_authorized": report.real_capital_authorized,
            "merge_authorized": report.merge_authorized,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
