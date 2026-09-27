"""Emit Phase20F independent accounting-core certification evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_mechanism_certification import (
    run_phase20f_accounting_core_certification,
)


def build_report() -> dict[str, Any]:
    with TemporaryDirectory(prefix="qore-cibo-phase20f-") as tmp:
        report = run_phase20f_accounting_core_certification(
            root=Path(tmp),
        )

    return {
        "schema": "qore.cibo.phase20f.accounting_core_certification.v1",
        "identity": report.identity,
        "scope": [item.tool_code for item in report.certifications],
        "certifications": [
            {
                "tool_code": item.tool_code,
                "tool_name": item.tool_name,
                "status": item.status.value,
                "proof_ids": list(item.proof_ids),
            }
            for item in report.certifications
        ],
        "proofs": [
            {
                "tool_code": item.tool_code,
                "invariant_id": item.invariant_id,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in report.proofs
        ],
        "summary": {
            "tool_count": len(report.certifications),
            "proof_count": len(report.proofs),
            "certified_tool_count": sum(
                item.status.value == "CONTRACT_CERTIFIED"
                for item in report.certifications
            ),
            "passed_proof_count": sum(item.passed for item in report.proofs),
        },
        "governance": {
            "synthetic_contract_evidence_only": (
                report.synthetic_contract_evidence_only
            ),
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
