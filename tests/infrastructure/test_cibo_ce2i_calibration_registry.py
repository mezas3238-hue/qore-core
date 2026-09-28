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
    assert (
        "USD_TRUE_STOP_RISK_REQUIRES_HISTORICAL_2017_"
        "TICK_VALUE_AND_CONVERSION"
        in record.blockers
    )


def test_t10_is_normalized_capital_time_only() -> None:
    record = calibration_record("T10")
    assert record.state is CiboCalibrationState.CALIBRATED_CAUSAL
    assert record.calibrated is True
    assert record.calibration_artifact_sha256
    assert record.provider_economics_required is True
    assert (
        "USD_OUTPUT_PER_CAPITAL_TIME_REQUIRES_HISTORICAL_"
        "EXECUTION_ECONOMICS"
        in record.blockers
    )


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


def test_lifecycle_tools_are_causally_calibrated_but_not_oos_ready() -> None:
    for code in ("T05", "T19", "T20"):
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.CALIBRATED_CAUSAL
        assert record.calibrated is True
        assert record.calibration_artifact_sha256
        assert record.oos_ready is False
        assert record.certification_ready is False
        assert record.blockers


def test_current_provider_terms_do_not_erase_historical_execution_blockers() -> None:
    assert "HISTORICAL_2017_PROVIDER_TERMS_NOT_PROVEN" in calibration_record(
        "T01"
    ).blockers
    assert "HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN" in calibration_record(
        "T03"
    ).blockers
    assert "EMPIRICAL_SLIPPAGE_AND_LATENCY_CALIBRATION_REQUIRED" in calibration_record(
        "T11"
    ).blockers


def test_phase19_negative_evidence_blocks_unreplicated_portfolio_policies() -> None:
    expected = {
        "T08": "FACTOR_MAP_NOT_CERTIFIED",
        "T09": "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
        "T12": "TEMPORAL_STABILITY_OBSERVATIONAL_ONLY",
        "T13": "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
        "T18": "ZERO_WALK_FORWARD_POLICY_SURVIVORS",
    }
    for code, blocker in expected.items():
        record = calibration_record(code)
        assert record.state is CiboCalibrationState.CALIBRATION_UNAVAILABLE
        assert record.calibrated is False
        assert blocker in record.blockers
        assert any(
            source.startswith("burned:phase19:non-promotion:sha256:")
            for source in record.calibration_sources
        )
