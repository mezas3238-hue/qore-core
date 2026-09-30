"""Emit Phase20G structural ablation/interaction evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_interaction_ablation import (
    run_phase20g_structural_ablation,
)


def build_report() -> dict[str, Any]:
    with TemporaryDirectory(prefix="qore-cibo-phase20g-") as tmp:
        report = run_phase20g_structural_ablation(root=Path(tmp))
    return {
        "schema": "qore.cibo.phase20g.structural_ablation.v1",
        "identity": report.identity,
        "cases": [
            {
                "case_id": item.case_id,
                "mechanisms": list(item.mechanisms),
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in report.cases
        ],
        "summary": {
            "case_count": len(report.cases),
            "passed_case_count": sum(item.passed for item in report.cases),
        },
        "governance": {
            "synthetic_contract_evidence_only": (
                report.synthetic_contract_evidence_only
            ),
            "empirical_value_claimed": report.empirical_value_claimed,
            "historical_provider_economics_claimed": (
                report.historical_provider_economics_claimed
            ),
            "phase19j_burned_validation_reused": (
                report.phase19j_burned_validation_reused
            ),
            "policy_selected": report.policy_selected,
            "allocation_authority": report.allocation_authority,
            "risk_authority": report.risk_authority,
            "execution_authority": report.execution_authority,
            "live_authorized": report.live_authorized,
            "real_capital_authorized": report.real_capital_authorized,
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
