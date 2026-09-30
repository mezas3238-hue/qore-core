from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    CALIBRATION_FREEZE_MANIFEST_ID,
    CiboCalibrationFreezeManifest,
    FrozenToolCalibration,
    FrozenToolCalibrationDisposition,
    build_calibration_freeze_manifest,
)
from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
)

T0 = datetime(2026, 9, 30, 21, 30, tzinfo=UTC)


def _tools() -> tuple[FrozenToolCalibration, ...]:
    provider_required = {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.provider_economics_required
    }
    result = []
    for index in range(1, 21):
        code = f"T{index:02d}"
        disabled = code in {"T16", "T17"}
        result.append(
            FrozenToolCalibration(
                tool_code=code,
                disposition=(
                    FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
                    if disabled
                    else FrozenToolCalibrationDisposition.CERTIFICATION_READY
                ),
                evidence_refs=(f"evidence:{code}",),
                oos_ready=not disabled,
                certification_ready=not disabled,
                structurally_disabled=disabled,
                provider_economics_bound=code in provider_required,
            )
        )
    return tuple(result)


def _manifest() -> CiboCalibrationFreezeManifest:
    return build_calibration_freeze_manifest(
        frozen_at=T0,
        phase20d_forward_manifest_sha256="sha256:" + "1" * 64,
        provider_economics_freeze_sha256="sha256:" + "2" * 64,
        tools=_tools(),
    )


def test_terminal_manifest_seals_active_tools_and_provider_disabled_tools() -> None:
    manifest = _manifest()

    assert manifest.manifest_id == CALIBRATION_FREEZE_MANIFEST_ID
    assert manifest.sealed is True
    assert manifest.structurally_disabled_tools == ("T16", "T17")
    assert len(manifest.active_certification_ready_tools) == 18
    assert manifest.holdout_outcomes_used is False
    assert manifest.holdout_market_data_read is False
    assert manifest.productive_authority is False
    assert manifest.fingerprint().startswith("sha256:")


def test_provider_dependent_tool_cannot_seal_without_provider_binding() -> None:
    tools = list(_tools())
    t03 = tools[2]
    tools[2] = replace(t03, provider_economics_bound=False)

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider-dependent tool is not bound",
    ):
        build_calibration_freeze_manifest(
            frozen_at=T0,
            phase20d_forward_manifest_sha256="sha256:" + "1" * 64,
            provider_economics_freeze_sha256="sha256:" + "2" * 64,
            tools=tuple(tools),
        )


def test_only_t16_t17_may_be_structurally_disabled() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="only T16/T17",
    ):
        FrozenToolCalibration(
            tool_code="T03",
            disposition=FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED,
            evidence_refs=("evidence:T03",),
            oos_ready=False,
            certification_ready=False,
            structurally_disabled=True,
            provider_economics_bound=True,
        )


def test_manifest_rejects_any_holdout_consumption() -> None:
    manifest = _manifest()

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot consume 2017H1",
    ):
        replace(manifest, holdout_market_data_read=True)
