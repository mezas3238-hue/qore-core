from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b01_causal_h01_h04_r3_8 import (
    Vt08B01CausalProgramError,
    compile_vt08_b01_causal_program,
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


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "failure-forensics.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_causal_program_opens_all_four_tracks_without_mutation(
    tmp_path: Path,
) -> None:
    payload = compile_vt08_b01_causal_program(_write(tmp_path, _artifact()))
    assert payload["causal_phase_open"] is True
    assert payload["source_adjudication_required"] is True
    assert payload["methodology_mutation_authorized"] is False
    assert payload["demo_eligible"] is False
    assert payload["forbidden_reuse"] == "run-34693803930"

    tracks = payload["tracks"]
    assert isinstance(tracks, list)
    assert [track["hypothesis_id"] for track in tracks] == _EXPECTED_IDS
    for track in tracks:
        assert track["status"] == "OPEN_CAUSAL_ADJUDICATION"
        assert track["fresh_holdout_required"] is True
        assert track["methodology_mutation_authorized"] is False
        assert track["forbidden_reuse"] == "run-34693803930"
        assert track["competing_mechanisms"]
        assert track["falsification_gate"]
        assert track["prohibited_inference"]


def test_causal_program_rejects_missing_hypothesis(tmp_path: Path) -> None:
    artifact = _artifact()
    hypotheses = artifact["hypothesis_register"]
    assert isinstance(hypotheses, list)
    artifact["hypothesis_register"] = hypotheses[:-1]
    with pytest.raises(Vt08B01CausalProgramError):
        compile_vt08_b01_causal_program(_write(tmp_path, artifact))


def test_causal_program_rejects_forbidden_reuse_loss(tmp_path: Path) -> None:
    artifact = _artifact()
    hypotheses = artifact["hypothesis_register"]
    assert isinstance(hypotheses, list)
    first = hypotheses[0]
    assert isinstance(first, dict)
    first["forbidden_reuse"] = "none"
    with pytest.raises(Vt08B01CausalProgramError):
        compile_vt08_b01_causal_program(_write(tmp_path, artifact))


def test_causal_program_rejects_demo_promotion(tmp_path: Path) -> None:
    artifact = _artifact()
    artifact["demo_eligible"] = True
    with pytest.raises(Vt08B01CausalProgramError):
        compile_vt08_b01_causal_program(_write(tmp_path, artifact))
