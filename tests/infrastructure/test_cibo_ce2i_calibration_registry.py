from qore.infrastructure.cibo_ce2i_calibration_registry import (
    CIBO_TOOL_CALIBRATION_REGISTRY,
    CiboCalibrationState,
    all_tools_certification_ready,
    all_tools_ready_for_fresh_oos,
    calibration_record,
    calibration_registry_complete,
)


def test_calibration_registry_covers_exact_t01_t20() -> None:
    assert calibration_registry_complete() is True
    assert tuple(row.tool_code for row in CIBO_TOOL_CALIBRATION_REGISTRY) == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert all(row.implemented for row in CIBO_TOOL_CALIBRATION_REGISTRY)


def test_contract_implementation_is_not_calibration_or_certification() -> None:
    assert all_tools_ready_for_fresh_oos() is False
    assert all_tools_certification_ready() is False
    assert not any(row.certification_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY)
    assert all(row.fail_closed for row in CIBO_TOOL_CALIBRATION_REGISTRY)


def test_registry_uses_only_canonical_non_ambiguous_states() -> None:
    allowed = {
        CiboCalibrationState.CALIBRATED_CAUSAL,
        CiboCalibrationState.CALIBRATED_ECONOMIC,
        CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED,
        CiboCalibrationState.CALIBRATION_UNAVAILABLE,
        CiboCalibrationState.OOS_READY,
        CiboCalibrationState.CERTIFICATION_READY,
        CiboCalibrationState.FAIL_CLOSED,
    }
    assert {row.state for row in CIBO_TOOL_CALIBRATION_REGISTRY} <= allowed


def test_provider_economics_blocks_exact_economic_tools() -> None:
    for code in ("T01", "T03", "T11", "T16"):
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED
        assert record.provider_economics_required is True
        assert record.certification_ready is False


def test_t04_explicitly_separates_r_normalized_from_usd_economic() -> None:
    record = calibration_record("T04")
    assert record.state is CiboCalibrationState.FAIL_CLOSED
    assert record.provider_economics_required is True
    assert record.blockers == (
        "T04_R_NORMALIZED_CALIBRATION_NOT_FROZEN",
        "T04_USD_ECONOMIC_REQUIRES_PROVIDER_ECONOMICS",
    )


def test_t16_t17_are_not_called_certified_without_instrument_support() -> None:
    assert "CERTIFIED_HEDGE_INSTRUMENT_UNIVERSE_NOT_AVAILABLE" in calibration_record(
        "T16"
    ).blockers
    t17 = calibration_record("T17")
    assert t17.state is CiboCalibrationState.CALIBRATION_UNAVAILABLE
    assert t17.fail_closed is True
    assert t17.certification_ready is False


def test_no_calibration_record_uses_holdout_outcomes_or_targets() -> None:
    assert all(
        not row.holdout_outcomes_used and not row.target_aware
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
