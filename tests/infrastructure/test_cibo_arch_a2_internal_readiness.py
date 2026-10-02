from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.cibo_arch_a2_internal_readiness import (
    evaluate_architect_a2_internal_readiness,
)
from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import LEDGER_PATH


def test_a2_internal_readiness_accepts_terminal_owned_surface() -> None:
    report = evaluate_architect_a2_internal_readiness()

    assert report.passed is True
    assert report.workstream_count == 17
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    expected_external = sum(
        1
        for row in payload["workstreams"]
        if row["id"] in A2_WORKSTREAM_IDS
        and row["terminal_disposition"] == "EXTERNAL_DEPENDENCY_BLOCKED"
    )
    assert report.externally_blocked_count == expected_external
    assert report.internally_open_ids == ()
    assert report.missing_ids == ()
    assert report.evidence_missing_ids == ()
    assert report.blocker_missing_ids == ()
    assert report.scientific_closure_claimed is False
    assert report.integration_authority is False
    assert report.productive_authority is False
    assert report.merge_authority is False


def test_a2_internal_readiness_fails_if_one_row_loses_external_blocker(
    tmp_path: Path,
) -> None:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    target = next(
        row
        for row in payload["workstreams"]
        if row["id"] == A2_WORKSTREAM_IDS[0]
    )
    target["blockers"] = []
    path = tmp_path / "ledger.json"
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = evaluate_architect_a2_internal_readiness(path)

    assert report.passed is False
    assert report.blocker_missing_ids == (A2_WORKSTREAM_IDS[0],)


def test_a2_internal_readiness_accepts_current_scientific_blockers(
    tmp_path: Path,
) -> None:
    payload = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    target = next(
        row
        for row in payload["workstreams"]
        if row["id"] == "GEN-C9"
    )
    assert target["terminal_disposition"] == "EXTERNAL_DEPENDENCY_BLOCKED"
    assert target["blockers"]
    path = tmp_path / "ledger.json"
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = evaluate_architect_a2_internal_readiness(path)

    assert report.passed is True
    assert report.externally_blocked_count > 0
