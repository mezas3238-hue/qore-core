from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CIBO_TOOL_CALIBRATION_REGISTRY,
    CiboCalibrationState,
    all_tools_ready_for_fresh_oos,
    calibration_record,
    calibration_registry_complete,
)


def test_calibration_registry_covers_exact_t01_t20() -> None:
    assert calibration_registry_complete() is True
    assert tuple(row.tool_code for row in CIBO_TOOL_CALIBRATION_REGISTRY) == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )


def test_contract_implementation_is_not_empirical_readiness() -> None:
    assert all_tools_ready_for_fresh_oos() is False
    assert any(
        row.state is CiboCalibrationState.CALIBRATION_BLOCKED
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
    assert any(
        row.state is CiboCalibrationState.SOURCE_IDENTIFIED
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )


def test_provider_economics_blocks_t01_t03_t11() -> None:
    for code in ("T01", "T03", "T11"):
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.CALIBRATION_BLOCKED
        assert "CALIBRATED_EXECUTION_ECONOMICS_REQUIRED" in record.blockers


def test_t16_t17_remain_blocked_without_certified_instrument_universe() -> None:
    assert calibration_record("T16").blockers == (
        "CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",
    )
    assert calibration_record("T17").blockers == (
        "CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE",
    )


def test_no_calibration_record_uses_holdout_outcomes_or_targets() -> None:
    assert all(
        not row.holdout_outcomes_used and not row.target_aware
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
