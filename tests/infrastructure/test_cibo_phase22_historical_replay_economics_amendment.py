from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_historical_replay_economics_amendment import (
    AMENDMENT_ID,
    EXECUTION_ECONOMICS_KIND,
    Phase22ProviderCalibrationReceipt,
    freeze_phase22_historical_replay_economics_amendment,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _calibration() -> Phase22ProviderCalibrationReceipt:
    return Phase22ProviderCalibrationReceipt(
        artifact_sha256=_sha("calibration-artifact"),
        git_sha="a" * 40,
        account_fingerprint_sha256=sha256(b"account").hexdigest(),
        observed_at=datetime(2026, 10, 1, 20, 40, tzinfo=UTC),
        status="READY",
        required_symbols=(
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        ),
        distinct_entry_orders_by_symbol=(
            ("AUDJPY", 8),
            ("EURUSD", 8),
            ("GBPJPY", 8),
            ("GBPUSD", 8),
            ("NAS100", 8),
            ("XAUUSD", 8),
        ),
        empirical_slippage_calibrated=True,
        execution_model_ready=True,
        execution_population_ready=True,
        created_positions_closed=True,
        minimum_volume_only=True,
        historical_provider_economics_claimed=False,
        historical_holdout_execution_claimed=False,
        holdout_outcomes_used=False,
        fundednext_touched=False,
        vps_touched=False,
        live_authorized=False,
        real_capital_authorized=False,
        productive_authority=False,
        blockers=(),
    )


def test_freeze_preserves_policy_thresholds_and_prohibits_historical_fill_claim() -> None:
    amendment = freeze_phase22_historical_replay_economics_amendment(
        provider_calibration=_calibration(),
        fresh_outcomes_emitted=False,
        holdout_outcomes_inspected=False,
    )
    assert amendment.amendment_id == AMENDMENT_ID
    assert amendment.execution_economics_kind == EXECUTION_ECONOMICS_KIND
    assert amendment.policy_changed is False
    assert amendment.thresholds_changed is False
    assert amendment.historical_broker_fills_claimed is False
    assert amendment.current_demo_fills_relabelled_as_historical is False
    assert amendment.fabricated_execution_evidence_allowed is False
    assert amendment.downstream_replay_settlement_adapter_required is True
    assert amendment.fingerprint().startswith("sha256:")


def test_amendment_cannot_be_frozen_after_v2_outcomes() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="pre-outcome governance",
    ):
        freeze_phase22_historical_replay_economics_amendment(
            provider_calibration=_calibration(),
            fresh_outcomes_emitted=True,
            holdout_outcomes_inspected=False,
        )


def test_calibration_cannot_claim_historical_holdout_execution() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        replace(
            _calibration(),
            historical_holdout_execution_claimed=True,
        )


def test_calibration_requires_all_six_symbols_and_eight_orders() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="population below minimum",
    ):
        replace(
            _calibration(),
            distinct_entry_orders_by_symbol=(
                ("AUDJPY", 8),
                ("EURUSD", 8),
                ("GBPJPY", 8),
                ("GBPUSD", 8),
                ("NAS100", 7),
                ("XAUUSD", 8),
            ),
        )
