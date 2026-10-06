from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
)
from scripts.cibo_build_walk_forward_expectation_manifest import (
    build_walk_forward_manifest,
)

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _row(index: int) -> dict[str, object]:
    decision_at = START + timedelta(minutes=index * 2)
    entry_at = decision_at + timedelta(seconds=10)
    exit_at = decision_at + timedelta(minutes=1)
    signal = f"signal-{index}"
    return {
        "decision_epoch_id": f"epoch-{index}",
        "market_decision_at": decision_at.isoformat(),
        "trader_id": "UNIVERSAL_TRADER_001",
        "qore_symbol": "BTCUSD",
        "signal_fingerprint": signal,
        "trader_opportunity": {
            "signal_fingerprint": signal,
            "trader_id": "UNIVERSAL_TRADER_001",
            "qore_symbol": "BTCUSD",
            "provider_symbol": "BTC-USD",
            "side": "long",
            "entry_type": "market",
            "intended_entry": "100",
            "stop_loss": "99",
            "take_profit": "102",
            "stop_loss_per_volume": "2",
            "margin_per_volume": "10",
            "volume_step": "0.01",
            "minimum_volume": "0.01",
            "maximum_volume": "100",
            "minimum_execution_steps": 1,
            "decision_context": [
                ["cibo_native_perception_complete", "true"],
                ["cibo_native_perception_version", "universal-v1"],
                ["source_context_causal", "true"],
            ],
        },
        "context_quality": {
            "disposition": "ALLOW",
            "causal_predecision": True,
            "identity_predicate_used": False,
            "outcome_used": False,
            "sizing_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "broker_mutation": False,
            "certification_claimed": False,
        },
        "settlement_outcome_research_only": {
            "entry_at": entry_at.isoformat(),
            "exit_at": exit_at.isoformat(),
            "gross_structural_outcome_r": str(index),
            "exit_reason": "TARGET",
            "not_available_to_predecision": True,
            "used_for_decision": False,
        },
        "outcome_available_to_predecision": False,
    }


def test_builder_requires_five_completed_signals_before_forecast() -> None:
    rows = [_row(index) for index in range(1, 27)]
    manifest = reseal_single_account_manifest(
        {
            "schema": "test.walk-forward-source.v1",
            "initial_capital_usd": "60",
            "account_count": 1,
            "account_reset_count": 0,
            "economic_era_reset_count": 0,
            "target_capital_used_for_tuning": False,
            "opportunity_decision_count": 26,
            "decision_epoch_count": 26,
            "trader_ids": ["UNIVERSAL_TRADER_001"],
            "trader_opportunity_counts": {
                "UNIVERSAL_TRADER_001": 26,
            },
            "first_market_decision_at": rows[0]["market_decision_at"],
            "last_market_decision_at": rows[-1]["market_decision_at"],
            "opportunities": rows,
            "governance": {
                "outcome_aware_tuning": False,
                "certification_claimed": False,
            },
        }
    )

    transformed, receipt = build_walk_forward_manifest(manifest)
    expectations = [
        row["expectation"] for row in transformed["opportunities"]
    ]

    assert [item["basis"] for item in expectations[:5]] == [
        "COLD_START_NO_FORECAST"
    ] * 5
    assert expectations[5]["basis"] == "WALK_FORWARD_EMPIRICAL_FORECAST"
    assert expectations[5]["walk_forward_observation_count"] == 5
    assert expectations[5]["walk_forward_maturity"] == "PROVISIONAL"
    assert (
        expectations[5]["walk_forward_mature_for_capital_consideration"]
        is False
    )
    assert expectations[5]["walk_forward_expected_structural_r"] == "3"
    assert expectations[5]["expected_net_value_usd"] == format(
        Decimal("3") * Decimal("0.02"),
        "f",
    )
    assert expectations[5]["uncertainty_penalty_usd"] == "0.02"
    assert (
        expectations[5]["walk_forward_duration_estimator"]
        == "UPPER_QUARTILE_PRIOR_ONLY"
    )
    assert expectations[25]["walk_forward_observation_count"] == 25
    assert expectations[25]["walk_forward_maturity"] == "MATURE"
    assert (
        expectations[25]["walk_forward_mature_for_capital_consideration"]
        is True
    )
    assert receipt["minimum_observations"] == 5
    assert receipt["mature_observation_count"] == 25
    assert receipt["cold_start_decision_count"] == 5
    assert receipt["forecast_decision_count"] == 21
    assert receipt["decoded_before_exit_count"] == 0
    assert receipt["future_outcome_used"] is False
