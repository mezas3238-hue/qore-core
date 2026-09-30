from __future__ import annotations

import json
import re
from pathlib import Path

LEDGER = Path("docs/shared/integration/SHARED_CONTINUOUS_INTEGRATION_LEDGER_001.json")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_IDS = {"INT-B-001", "INT-B-002", "INT-A-001", "INT-A-002", "INT-A-003"}


def _load() -> dict[str, object]:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_continuous_integration_ledger_invariants() -> None:
    payload = _load()
    assert payload["schema"] == "QORE_SHARED_CONTINUOUS_INTEGRATION_LEDGER_001"
    assert payload["certification_authority"] is False
    assert payload["production_authority"] is False

    entries = payload["entries"]
    assert isinstance(entries, list)
    ids = [entry["integration_id"] for entry in entries]
    assert len(ids) == len(set(ids))
    assert REQUIRED_IDS.issubset(set(ids))

    admitted_workstreams: list[str] = []
    for entry in entries:
        assert SHA40.fullmatch(entry["source_cut_sha"])
        assert SHA40.fullmatch(entry["master_merge_sha"])
        assert entry["partial_work_admitted"] is False
        assert entry["source_evidence"]
        if "protected_holdout_opened" in entry:
            assert entry["protected_holdout_opened"] is False
        if "master_mc28_closed" in entry:
            assert entry["master_mc28_closed"] is False

        disposition = entry["disposition"]
        regression = entry["master_regression_status"]
        if disposition == "INTEGRATED_AND_PROVEN":
            assert regression.startswith("PASSED")
            assert entry["master_regression_evidence"]
        elif disposition == "MERGED_PENDING_MASTER_REGRESSION":
            assert regression == "RUNNING"
        else:
            raise AssertionError(f"unsupported integration disposition: {disposition}")

        workstreams = entry["workstreams"]
        assert workstreams
        admitted_workstreams.extend(workstreams)

    assert len(admitted_workstreams) == len(set(admitted_workstreams))


def test_mc26_remains_dependency_blocked() -> None:
    payload = _load()
    next_integrations = payload["next_integrations"]
    mc26 = next(
        row for row in next_integrations
        if row.get("lane") == "A" and "MC-26" in row.get("workstreams", [])
    )
    assert mc26["status"] == "DEPENDENCY_BLOCKED"
    assert any("MC-18" in blocker for blocker in mc26["blockers"])
    assert any("MC-23" in blocker for blocker in mc26["blockers"])
