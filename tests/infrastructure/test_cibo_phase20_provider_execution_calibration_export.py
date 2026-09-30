from datetime import UTC, datetime
from pathlib import Path

from scripts.cibo_phase20_provider_execution_calibration import (
    calibration_payload,
    load_provider_execution_calibration,
)


def test_empty_durable_population_exports_fail_closed_calibration(
    tmp_path: Path,
) -> None:
    calibration = load_provider_execution_calibration(
        forward_store_path=tmp_path / "forward.json",
        policy_store_path=tmp_path / "policy.json",
        executed_risk_store_path=tmp_path / "risk.json",
        settlement_store_path=tmp_path / "settlement.json",
        release_store_path=tmp_path / "release.json",
        frozen_at=datetime(2026, 9, 30, 21, 0, tzinfo=UTC),
    )
    payload = calibration_payload(calibration)

    assert calibration.empirical_slippage_calibrated is False
    assert calibration.execution_model_ready is False
    assert calibration.total_observations == 0
    assert calibration.productive_authority is False
    assert "FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY" in calibration.blockers
    assert str(payload["calibration_sha256"]).startswith("sha256:")
    assert payload["observations"] == []
