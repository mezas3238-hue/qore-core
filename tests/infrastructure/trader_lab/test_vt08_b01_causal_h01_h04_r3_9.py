from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_b01_causal_h01_h04_r3_9 import (
    compile_vt08_b01_causal_program_r3_9,
)

_EXPECTED_IDS = [
    "VT08-R3.8-FF-H01",
    "VT08-R3.8-FF-H02",
    "VT08-R3.8-FF-H03",
    "VT08-R3.8-FF-H04",
]


def _artifact() -> dict[str, object]:
    return {
        "schema": "qore.trader_lab.vt08_b01_failure_forensics.r3.8.v1",
        "trader_code": "vt-08",
        "baseline_run_id": 34693803930,
        "baseline_head": "a5b9b5a80a55314f74cc1e3ef632803a91972c3b",
        "baseline_frozen": True,
        "current_evidence_consumed": True,
        "independent_validation_reuse_prohibited": True,
        "demo_eligible": False,
        "methodology_fingerprint": "a" * 64,
        "hypothesis_register": [
            {
                "id": hypothesis_id,
                "family": f"family-{index}",
                "status": "research_hypothesis_only",
                "evidence": {"index": index},
                "forbidden_reuse": "run-34693803930",
            }
            for index, hypothesis_id in enumerate(_EXPECTED_IDS, start=1)
        ],
    }


def _write(tmp_path: Path) -> Path:
    path = tmp_path / "failure-forensics.json"
    path.write_text(json.dumps(_artifact()), encoding="utf-8")
    return path


def test_r39_closes_h01_source_adjudication_without_authorizing_mutation(
    tmp_path: Path,
) -> None:
    payload = compile_vt08_b01_causal_program_r3_9(_write(tmp_path))
    assert payload["schema"] == "qore.trader_lab.vt08_b01_causal_h01_h04.r3.9.v1"
    assert payload["source_contract_frozen"] is True
    assert payload["h01_source_status"] == "SOURCE_ADJUDICATED_NO_PERFORMANCE_MUTATION"
    assert payload["methodology_mutation_authorized"] is False
    assert payload["demo_eligible"] is False

    tracks = payload["tracks"]
    assert isinstance(tracks, list)
    h01 = next(item for item in tracks if item["hypothesis_id"] == "VT08-R3.8-FF-H01")
    assert h01["status"] == "SOURCE_ADJUDICATED_NO_PERFORMANCE_MUTATION"
    source = h01["source_adjudication"]
    assert source["protected_swing_core"] == "SOURCE_EXPLICIT"
    assert source["multiple_ps_selection"] == "FUNDAMENTALLY_UNRESOLVED"
    assert source["methodology_mutation_authorized"] is False


def test_r39_removes_13_as_source_entry_authority(tmp_path: Path) -> None:
    payload = compile_vt08_b01_causal_program_r3_9(_write(tmp_path))
    tracks = payload["tracks"]
    assert isinstance(tracks, list)
    h03 = next(item for item in tracks if item["hypothesis_id"] == "VT08-R3.8-FF-H03")

    boundary = " ".join(h03["source_boundary"])
    diagnostics = " ".join(h03["fresh_diagnostics"])
    prohibited = " ".join(h03["prohibited_inference"])
    assert "exactly 01/05/09" in boundary
    assert "13:00 is not a source-authorized" in boundary
    assert "13:00 entry cohort" in diagnostics
    assert "13:00 reconstruction-grid hour" in prohibited
    assert "source-complete Forex timing is 01/05/09/13" not in boundary


def test_r39_preserves_consumed_holdout_prohibition(tmp_path: Path) -> None:
    payload = compile_vt08_b01_causal_program_r3_9(_write(tmp_path))
    governance = payload["fresh_holdout_governance"]
    assert isinstance(governance, dict)
    assert governance["required"] is True
    assert governance["forbidden_reuse"] == "run-34693803930"
    assert governance["must_not_treat_overlapping_reacquisition_as_independent"] is True
    assert governance["independent_validation_authorized"] is False


def test_r39_grants_no_execution_authority(tmp_path: Path) -> None:
    payload = compile_vt08_b01_causal_program_r3_9(_write(tmp_path))
    assert payload["execution_authority"] == {
        "research_only": True,
        "demo_eligible": False,
        "live": False,
        "real_capital": False,
    }
