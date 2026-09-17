from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vt31_nas100_r1_contract_self_test() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/vt31_nas100_r1_candidate.py", "--self-test"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["candidate_id"] == "VT31_NAS100_R1"
    assert len(payload["contract_fingerprint"]) == 64


def test_vt31_nas100_r1_freeze_contract_preserves_one_shot_order() -> None:
    text = Path("docs/research/VT31_NAS100_R1_FREEZE_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    assert "R1 is frozen before opening the holdout" in text
    assert "permanently consumed" in text
    assert "no post-open retuning" in text
    assert "Fixed 2R is retired" in text
    assert "M1 protected-swing trailing is removed" in text
