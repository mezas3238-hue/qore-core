from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_vt31_nas100_specialist_r1_contract_self_test() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/vt31_nas100_specialist_r1_candidate.py",
            "--self-test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["candidate_id"] == "VT31_NAS100_SPECIALIST_R1"
    assert len(payload["contract_fingerprint"]) == 64


def test_vt31_nas100_specialist_r1_freeze_contract_keeps_holdout_sealed() -> None:
    text = Path(
        "docs/research/VT31_NAS100_SPECIALIST_R1_FREEZE_CONTRACT.md"
    ).read_text(encoding="utf-8")
    assert "[2015-04-19, 2016-04-19)" in text
    assert "Opening permanently consumes the interval" in text
    assert "No post-open retuning" in text
    assert "date-level CIBO outcome lookup" in text
    assert "50% realized at 1.25R" in text
