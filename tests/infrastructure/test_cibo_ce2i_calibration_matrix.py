from qore.infrastructure.cibo_ce2i_calibration_matrix import (
    CIBO_T01_T20_CALIBRATION_MATRIX,
    CiboCalibrationClassification,
    validate_calibration_matrix,
)


def test_calibration_matrix_is_canonical_and_pre_holdout_conservative() -> None:
    validate_calibration_matrix()
    assert tuple(row.tool_code for row in CIBO_T01_T20_CALIBRATION_MATRIX) == tuple(
        f"T{index:02d}" for index in range(1, 21)
    )
    assert all(row.implemented for row in CIBO_T01_T20_CALIBRATION_MATRIX)
    assert {
        row.tool_code
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.calibrated
    } == {"T04", "T05", "T06", "T10", "T19", "T20"}
    assert not any(row.oos_ready for row in CIBO_T01_T20_CALIBRATION_MATRIX)
    assert not any(row.certification_ready for row in CIBO_T01_T20_CALIBRATION_MATRIX)


def test_provider_bound_tools_are_explicit_and_fail_closed() -> None:
    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    provider_bound = {
        "T01",
        "T03",
        "T04",
        "T07",
        "T10",
        "T11",
        "T16",
        "T17",
    }
    assert {
        code for code, row in rows.items() if row.provider_economics_required
    } == provider_bound
    assert all(rows[code].fail_closed for code in provider_bound)
    assert all(
        rows[code].fail_closed
        for code in {"T01", "T03", "T11", "T16", "T17"}
    )
    assert rows["T04"].classification is CiboCalibrationClassification.CALIBRATED_CAUSAL
    assert rows["T10"].classification is CiboCalibrationClassification.CALIBRATED_CAUSAL


def test_fail_closed_never_implies_certification_ready() -> None:
    assert all(
        not row.certification_ready
        for row in CIBO_T01_T20_CALIBRATION_MATRIX
        if row.fail_closed
    )


def test_t04_t10_are_causal_only_and_not_usd_certified() -> None:
    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    for code in ("T04", "T10"):
        row = rows[code]
        assert row.classification is CiboCalibrationClassification.CALIBRATED_CAUSAL
        assert row.provider_economics_required is True
        assert row.oos_ready is False
        assert row.certification_ready is False
        assert row.blocker


def test_lifecycle_calibration_is_causal_not_certified() -> None:
    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    for code in ("T05", "T19", "T20"):
        row = rows[code]
        assert row.calibrated is True
        assert row.classification is CiboCalibrationClassification.CALIBRATED_CAUSAL
        assert row.provider_economics_required is False
        assert row.oos_ready is False
        assert row.certification_ready is False
        assert row.calibration_artifact_sha256


def test_t06_is_causal_source_calibration_not_expansion_certification() -> None:
    rows = {row.tool_code: row for row in CIBO_T01_T20_CALIBRATION_MATRIX}
    row = rows["T06"]

    assert row.calibrated is True
    assert row.classification is CiboCalibrationClassification.CALIBRATED_CAUSAL
    assert row.provider_economics_required is False
    assert row.oos_ready is False
    assert row.certification_ready is False
    assert row.calibration_artifact_sha256
    assert (
        "EXPANSION_MULTIPLIER_AND_INCREMENTAL_UTILITY_REQUIRE_FRESH_OOS"
        in row.blocker
    )
