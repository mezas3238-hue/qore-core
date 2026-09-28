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
    assert all(row.implemented for row in CIBO_TOOL_CALIBRATION_REGISTRY)


def test_contract_implementation_is_not_empirical_readiness() -> None:
    assert all_tools_ready_for_fresh_oos() is False
    assert all(not row.oos_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY)
    assert all(not row.certification_ready for row in CIBO_TOOL_CALIBRATION_REGISTRY)


def test_only_canonical_unambiguous_states_are_used() -> None:
    allowed = {
        "CALIBRATED_CAUSAL",
        "CALIBRATED_ECONOMIC",
        "PROVIDER_ECONOMICS_REQUIRED",
        "CALIBRATION_UNAVAILABLE",
        "OOS_READY",
        "CERTIFICATION_READY",
        "FAIL_CLOSED",
    }
    assert {row.state.value for row in CIBO_TOOL_CALIBRATION_REGISTRY} <= allowed


def test_provider_economics_blocks_t01_t03_t11() -> None:
    for code in ("T01", "T03", "T11"):
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.PROVIDER_ECONOMICS_REQUIRED
        assert record.provider_economics_required is True


def test_t16_t17_are_fail_closed_not_certified() -> None:
    for code in ("T16", "T17"):
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.FAIL_CLOSED
        assert record.fail_closed is True
        assert record.oos_ready is False
        assert record.certification_ready is False
        assert record.provider_economics_required is True


def test_t04_separates_normalized_from_usd_economics() -> None:
    record = calibration_record("T04")
    assert record.state is CiboCalibrationState.CALIBRATED_CAUSAL
    assert record.calibrated is True
    assert record.calibration_artifact_sha256
    assert record.provider_economics_required is True
    assert "USD_TRUE_STOP_RISK_REQUIRES_PROVIDER_ECONOMICS" in record.blockers


def test_t10_is_normalized_capital_time_only() -> None:
    record = calibration_record("T10")
    assert record.state is CiboCalibrationState.CALIBRATED_CAUSAL
    assert record.calibrated is True
    assert record.calibration_artifact_sha256
    assert record.provider_economics_required is True
    assert "USD_OUTPUT_PER_CAPITAL_TIME_PENDING_PROVIDER_ECONOMICS" in record.blockers


def test_no_calibration_record_uses_holdout_outcomes_or_targets() -> None:
    assert all(
        not row.holdout_outcomes_used and not row.target_aware
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
    )
    assert all(
        "2017H1" not in source
        for row in CIBO_TOOL_CALIBRATION_REGISTRY
        for source in row.calibration_sources
    )
