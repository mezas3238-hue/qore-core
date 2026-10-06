from qore.infrastructure.cibo_ce2i_burned_t06_calibration import (
    T06_PROFIT_FUNDED_RULES,
    burned_t06_source_calibration_payload,
    burned_t06_source_calibration_sha256,
)


def test_t06_only_uses_reconciled_realized_profit_as_expansion_source() -> None:
    payload = burned_t06_source_calibration_payload()

    assert payload["classification"] == "CALIBRATED_CAUSAL"
    assert (
        "ONLY_RECONCILED_REALIZED_PROFIT_IS_EXPANSION_FUNDING"
        in T06_PROFIT_FUNDED_RULES
    )
    assert "POSITIVE_FLOATING_PNL_IS_NOT_SPENDABLE_CAPITAL" in T06_PROFIT_FUNDED_RULES
    assert (
        "ORIGINAL_BASE_CAPITAL_IS_NOT_SELF_FINANCING_EXPANSION_SOURCE"
        in T06_PROFIT_FUNDED_RULES
    )
    assert payload["expansion_multiplier_calibrated"] is False
    assert payload["incremental_economic_utility_calibrated"] is False


def test_t06_calibration_does_not_touch_holdout_or_claim_usd_execution() -> None:
    governance = burned_t06_source_calibration_payload()["governance"]

    assert governance["holdout_2017h1_used"] is False
    assert governance["floating_pnl_as_cash"] is False
    assert governance["historical_usd_execution_economics_claimed"] is False
    assert governance["target_aware"] is False
    assert governance["oos_ready"] is False
    assert governance["certification_ready"] is False


def test_t06_calibration_hash_is_stable() -> None:
    first = burned_t06_source_calibration_sha256()
    second = burned_t06_source_calibration_sha256()

    assert first == second
    assert len(first) == 64
