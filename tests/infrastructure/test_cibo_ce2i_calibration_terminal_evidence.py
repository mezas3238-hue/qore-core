from qore.infrastructure.cibo_ce2i_calibration_freeze_manifest import (
    FrozenToolCalibrationDisposition,
)
from qore.infrastructure.cibo_ce2i_calibration_terminal_evidence import (
    ACTIVE_CERTIFICATION_TOOLS,
    QUALIFICATION_FAILED_TOOLS,
    STRUCTURALLY_DISABLED_TOOLS,
    build_terminal_calibration_readiness,
    shadow_successor_manifest,
    terminal_tool_evidence,
)


def test_shadow_successor_is_consumable_and_holdout_safe() -> None:
    manifest = shadow_successor_manifest()
    assert manifest["ready_for_scientific_consumption"] is True
    assert manifest["evidence_kind"] == "HISTORICAL_SHADOW_QUALIFICATION"
    assert manifest["owner_authorized_forward_successor"] is True
    assert manifest["candidate_outcomes"] == 855
    assert manifest["decision_epochs"] == 775
    assert manifest["distinct_trading_days"] == 214
    assert manifest["represented_lineages"] == 7
    assert manifest["fold_count"] == 4
    assert manifest["holdout_2017h1_read"] is False


def test_terminal_tool_evidence_closes_all_twenty_without_promotion() -> None:
    rows = terminal_tool_evidence()
    by_code = {item.tool_code: item for item in rows}
    assert len(rows) == 20
    assert ACTIVE_CERTIFICATION_TOOLS == ("T01", "T05", "T11", "T19", "T20")
    assert STRUCTURALLY_DISABLED_TOOLS == ("T16", "T17")
    assert len(QUALIFICATION_FAILED_TOOLS) == 13
    assert (
        by_code["T03"].disposition
        is FrozenToolCalibrationDisposition.QUALIFICATION_FAILED_AND_DISABLED
    )
    assert by_code["T03"].structurally_disabled is True
    assert (
        by_code["T16"].disposition
        is FrozenToolCalibrationDisposition.STRUCTURALLY_DISABLED
    )
    assert (
        by_code["T11"].disposition
        is FrozenToolCalibrationDisposition.CERTIFICATION_READY
    )


def test_terminal_readiness_seals_manifest_without_holdout() -> None:
    report = build_terminal_calibration_readiness()
    assert report.ready_to_seal is True
    assert report.blockers == ()
    assert report.calibration_manifest is not None
    assert report.calibration_manifest.sealed is True
    assert report.calibration_manifest.holdout_outcomes_used is False
    assert report.calibration_manifest.holdout_market_data_read is False
