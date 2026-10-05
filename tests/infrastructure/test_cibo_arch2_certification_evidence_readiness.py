from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cibo_arch2_certification_evidence_readiness.py"

spec = importlib.util.spec_from_file_location(
    "cibo_arch2_certification_evidence_readiness", SCRIPT
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _load(relative: str) -> dict:
    with (ROOT / relative).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_certification_evidence_readiness_remains_fail_closed() -> None:
    report = module.build_readiness(
        _load("artifacts/arch2/CIBO_ARCH2_EXTERNAL_DEPENDENCY_COLLAPSE_V1.json"),
        _load(
            "artifacts/arch2/"
            "CIBO_ARCH2_CERTIFICATION_BLOCKER_RECONCILIATION_V1.json"
        ),
    )

    assert report["family_count"] == 7
    assert report["certification_ready_family_count"] == 0
    assert report["partial_family_count"] == 1
    assert report["blocked_family_count"] == 6
    assert report["external_dependency_blocked_row_count"] == 40
    assert report["architect2_internal_repair_count"] == 0

    assert report["fresh_oos_owner_authorization_present"] is False
    assert report["fresh_outcomes_executed"] is False
    assert report["certification_execution_ready"] is False

    families = {item["family"]: item for item in report["families"]}
    assert families["PROVIDER_EXECUTION_ECONOMICS"]["status"] == (
        "PARTIAL_EMPIRICAL_CLOSURE"
    )
    assert families["PATH_STRESS_TEMPORAL_MC"]["status"] == (
        "RESEARCH_ONLY_NOT_CERTIFYING"
    )
    assert families["COMPOUND_PORTFOLIO_CAPITAL"]["status"] == (
        "RESEARCH_ONLY_NOT_CERTIFYING"
    )
    assert report["governance"]["functional_completeness_is_not_certification"]
    assert report["governance"]["burned_research_is_not_fresh_oos"]
