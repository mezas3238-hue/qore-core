"""Semantic preimage gate for CIBO Scientific Closure 41."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.cibo_scientific_closure_41_adapters import (
    scientific_closure_41_dependency_manifest,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_HOLDOUT_ID,
    CANONICAL_POLICY_IDENTITY,
    CANONICAL_PROVIDER_IDENTITY,
    PACKAGE_SCHEMA,
    validate_scientific_closure_41_preimage,
)

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
ARTIFACT_PATH = Path(
    "artifacts/cibo_scientific_closure_41_semantic_gate_v1.json"
)


def main() -> int:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    summary = validate_scientific_closure_41_preimage(ledger)
    payload = {
        "schema": "QORE_CIBO_SCIENTIFIC_CLOSURE_41_SEMANTIC_GATE_V1",
        "closure_package_schema": PACKAGE_SCHEMA,
        "status": "READY_TO_CONSUME_TERMINAL_IMMUTABLE_EVIDENCE",
        "holdout_id": CANONICAL_HOLDOUT_ID,
        "policy_identity": CANONICAL_POLICY_IDENTITY,
        "provider_identity": CANONICAL_PROVIDER_IDENTITY,
        **summary,
        "dependency_manifest": scientific_closure_41_dependency_manifest(),
        "phase22_execution_authority": False,
        "canonical_ledger_write_authority": False,
        "final_exam_authority": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
