from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cibo_arch2_external_dependency_collapse.py"

spec = importlib.util.spec_from_file_location("cibo_arch2_external_dependency_collapse", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _load(relative: str) -> dict:
    with (ROOT / relative).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_external_dependency_collapse_preserves_scientific_blockers() -> None:
    report = module.build_report(
        _load("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json"),
        _load(
            "artifacts/arch2/"
            "CIBO_ARCH2_CERTIFICATION_BLOCKER_RECONCILIATION_V1.json"
        ),
    )

    assert report["architect2_internal_functional_closure"] is True
    assert report["architect2_internal_blocker_count"] == 0
    assert report["actionable_architect2_internal_repair_count"] == 0

    assert report["external_dependency_blocked_row_count"] == 40
    assert report["unique_external_blocker_atom_count"] == 67
    assert report["semantic_dependency_family_count"] == 7
    assert report["unclassified_external_blocker_atom_count"] == 0
    assert report["certification_execution_ready"] is False

    families = report["dependency_families"]
    assert families["FRESH_FORWARD_CAUSAL"]["row_count"] == 32
    assert families["PROVIDER_EXECUTION_ECONOMICS"]["row_count"] == 7
    assert families["SCARCITY_CONCENTRATION"]["row_count"] == 4
    assert families["PATH_STRESS_TEMPORAL_MC"]["row_count"] == 18
    assert families["COMPOUND_PORTFOLIO_CAPITAL"]["row_count"] == 18
    assert families["POST_OUTCOME_MEMORY_GOVERNANCE"]["row_count"] == 2
    assert families["EXAM_GOVERNANCE"]["row_count"] == 3

    rows = {row["id"]: row for row in report["rows"]}
    assert rows["T11"]["reconciliation_disposition"] == (
        "EMPIRICAL_PROVIDER_PARTIAL_CLOSURE__"
        "FRESH_GROSS_EDGE_MARKET_IMPACT_PENDING"
    )
    assert rows["T13"]["reconciliation_disposition"] == (
        "FUNCTIONAL_REDUNDANCY_CLASSIFIED__"
        "SCIENTIFIC_UTILITY_EVIDENCE_PENDING"
    )
    assert rows["T15"]["reconciliation_disposition"] == (
        "FUNCTIONAL_REDUNDANCY_CLASSIFIED__"
        "SCIENTIFIC_UTILITY_EVIDENCE_PENDING"
    )

    assert report["canonical_ledger_mutated"] is False
    assert report["fresh_oos_opened"] is False
    assert report["governance"]["reused_research_promoted_to_certification"] is False
