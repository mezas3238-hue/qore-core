from __future__ import annotations

import copy
from hashlib import sha256

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_claimed_recovery import (
    EXPECTED_VT31_CENSORED_ROWS,
    EXPECTED_VT31_EMITTED_ROWS,
    EXPECTED_VT31_EXECUTABLE_ROWS,
    SOURCE_RUN_ATTEMPT,
    SOURCE_RUN_ID,
    VT31_ARTIFACT_ID,
    VT31_ARTIFACT_SHA256,
    canonicalize_claimed_native_opportunity_order,
    recover_vt31_claimed_payload,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import CANDIDATE_ID


def _fingerprint(index: int) -> str:
    return "sha256:" + sha256(f"signal-{index}".encode()).hexdigest()


def _row(index: int, *, censored: bool) -> dict[str, object]:
    return {
        "trader_id": "VT31_NAS100",
        "symbol": "NAS100",
        "signal_fingerprint": _fingerprint(index),
        "signal_at": f"2016-01-{(index % 28) + 1:02d}T15:00:00+00:00",
        "entry_at": f"2016-01-{(index % 28) + 1:02d}T15:01:00+00:00",
        "exit_at": f"2016-01-{(index % 28) + 1:02d}T15:10:00+00:00",
        "side": "long",
        "entry": None if censored else "100",
        "stop": None if censored else "99",
        "target": None if censored else "102",
        "exit_reason": "initial-stop",
        "realized_r": "999" if censored else "2",
        "methodology_sha256": "sha256:" + "1" * 64,
    }


def _payload() -> dict[str, object]:
    rows = [
        _row(i, censored=i < EXPECTED_VT31_CENSORED_ROWS)
        for i in range(EXPECTED_VT31_EMITTED_ROWS)
    ]
    return {
        "candidate_id": CANDIDATE_ID,
        "trader_id": "VT31_NAS100",
        "opportunities": rows,
        "opportunity_count": len(rows),
        "fresh_outcomes_executed": True,
        "methodology_changed": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
        "binding_diagnostics": {
            "path_causal_diagnostics": {
                "capacity_diagnostics": {
                    "censored_geometry_count": EXPECTED_VT31_CENSORED_ROWS,
                }
            }
        },
    }


def _recover(payload: dict[str, object]):
    return recover_vt31_claimed_payload(
        payload,
        source_artifact_id=VT31_ARTIFACT_ID,
        source_artifact_sha256=VT31_ARTIFACT_SHA256,
        source_run_id=SOURCE_RUN_ID,
        source_run_attempt=SOURCE_RUN_ATTEMPT,
    )


def test_recovery_excludes_exact_triple_null_geometry_without_outcome_selection() -> None:
    recovered, receipt = _recover(_payload())

    assert len(recovered["opportunities"]) == EXPECTED_VT31_EXECUTABLE_ROWS
    assert receipt.censored_excluded_count == EXPECTED_VT31_CENSORED_ROWS
    assert receipt.selection_uses_realized_r is False
    assert receipt.geometry_reconstructed is False
    assert receipt.fresh_lane_population_regenerated is False
    assert receipt.second_fresh_execution is False


def test_recovery_selection_is_invariant_to_censored_realized_r() -> None:
    first = _payload()
    second = copy.deepcopy(first)
    rows = second["opportunities"]
    assert isinstance(rows, list)
    for row in rows[:EXPECTED_VT31_CENSORED_ROWS]:
        assert isinstance(row, dict)
        row["realized_r"] = "-123456789"

    first_recovered, first_receipt = _recover(first)
    second_recovered, second_receipt = _recover(second)

    assert [
        row["signal_fingerprint"] for row in first_recovered["opportunities"]
    ] == [
        row["signal_fingerprint"] for row in second_recovered["opportunities"]
    ]
    assert (
        first_receipt.excluded_signal_fingerprints
        == second_receipt.excluded_signal_fingerprints
    )


def test_recovery_fails_closed_on_partial_geometry() -> None:
    payload = _payload()
    rows = payload["opportunities"]
    assert isinstance(rows, list)
    row = rows[0]
    assert isinstance(row, dict)
    row["entry"] = "100"

    with pytest.raises(CiboCapitalManagementError, match="partial geometry"):
        _recover(payload)


def test_recovery_fails_closed_if_runner_diagnostic_does_not_match_projection() -> None:
    payload = _payload()
    binding = payload["binding_diagnostics"]
    assert isinstance(binding, dict)
    path = binding["path_causal_diagnostics"]
    assert isinstance(path, dict)
    capacity = path["capacity_diagnostics"]
    assert isinstance(capacity, dict)
    capacity["censored_geometry_count"] = 19

    with pytest.raises(CiboCapitalManagementError, match="population mismatch"):
        _recover(payload)


def test_recovery_is_bound_to_original_burned_run_artifact() -> None:
    with pytest.raises(CiboCapitalManagementError, match="source identity drift"):
        recover_vt31_claimed_payload(
            _payload(),
            source_artifact_id=VT31_ARTIFACT_ID + 1,
            source_artifact_sha256=VT31_ARTIFACT_SHA256,
            source_run_id=SOURCE_RUN_ID,
            source_run_attempt=SOURCE_RUN_ATTEMPT,
        )


def test_native_order_canonicalization_changes_order_not_population() -> None:
    payload = _payload()
    rows = payload["opportunities"]
    assert isinstance(rows, list)
    rows.reverse()
    before = {
        str(row["signal_fingerprint"]): str(row["realized_r"])
        for row in rows
        if isinstance(row, dict)
    }

    projected = canonicalize_claimed_native_opportunity_order(payload)
    projected_rows = projected["opportunities"]
    assert isinstance(projected_rows, list)
    after = {
        str(row["signal_fingerprint"]): str(row["realized_r"])
        for row in projected_rows
        if isinstance(row, dict)
    }

    assert before == after
    assert [str(row["signal_at"]) for row in projected_rows] == sorted(
        str(row["signal_at"]) for row in projected_rows
    )
