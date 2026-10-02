from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FINAL_INTEGRATED_EXAM_ID,
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_entry_controls import (
    build_world_cup_entry_controls,
)

HEAD = "a" * 40
T0 = datetime(2026, 10, 1, 19, 0, tzinfo=UTC)


def _final() -> FinalIntegratedExamReport:
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=FinalIntegratedExamStatus.PASS,
        integrated_head_sha=HEAD,
        blockers=(),
    )


def test_world_cup_entry_builds_wc01_wc02_from_final_pass() -> None:
    wc01, wc02 = build_world_cup_entry_controls(
        integrated_git_sha=HEAD,
        final_integrated_exam=_final(),
        observed_at=T0,
    )
    assert wc01.receipt_id == "WC01_FINAL_INTEGRATED_EXAM_PASS"
    assert wc02.receipt_id == "WC02_PROTOCOL_FREEZE"
    assert wc01.integrated_git_sha == HEAD
    assert (
        wc01.final_integrated_exam_report_sha256
        == wc02.final_integrated_exam_report_sha256
    )


def test_world_cup_entry_requires_final_pass() -> None:
    final = replace(
        _final(),
        status=FinalIntegratedExamStatus.BLOCKED,
        blockers=("P7",),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="require Final Integrated PASS",
    ):
        build_world_cup_entry_controls(
            integrated_git_sha=HEAD,
            final_integrated_exam=final,
            observed_at=T0,
        )


def test_world_cup_entry_rejects_cross_head_final_report() -> None:
    with pytest.raises(CiboCapitalManagementError, match="HEAD drift"):
        build_world_cup_entry_controls(
            integrated_git_sha="b" * 40,
            final_integrated_exam=_final(),
            observed_at=T0,
        )
