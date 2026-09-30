from qore.infrastructure.cibo_ce2i_burned_t07_calibration import (
    T07_PROTECTED_CAPACITY_RULES,
    burned_t07_source_calibration_payload,
    burned_t07_source_calibration_sha256,
)


def test_t07_freezes_only_protected_capacity_causal_eligibility() -> None:
    payload = burned_t07_source_calibration_payload()

    assert payload["classification"] == "CALIBRATED_CAUSAL"
    assert (
        "PROTECTED_CAPACITY_REQUIRES_RECONCILED_POSITION_AND_PROTECTION"
        in T07_PROTECTED_CAPACITY_RULES
    )
    assert (
        "POSITIVE_FLOATING_PNL_ALONE_IS_NOT_PROTECTED_CAPACITY"
        in T07_PROTECTED_CAPACITY_RULES
    )
    assert (
        "FUTURE_COST_AND_SLIPPAGE_RESERVES_DEDUCT_BEFORE_CAPACITY"
        in T07_PROTECTED_CAPACITY_RULES
    )
    assert payload["protected_economic_floor_amount_calibrated"] is False
    assert payload["expansion_multiplier_calibrated"] is False
    assert payload["incremental_economic_utility_calibrated"] is False


def test_t07_keeps_provider_usd_floor_and_holdout_fail_closed() -> None:
    governance = burned_t07_source_calibration_payload()["governance"]

    assert governance["provider_economics_required"] is True
    assert governance["holdout_2017h1_used"] is False
    assert governance["floating_pnl_as_cash"] is False
    assert governance["historical_2017_usd_floor_claimed"] is False
    assert governance["historical_usd_execution_economics_claimed"] is False
    assert governance["target_aware"] is False
    assert governance["oos_ready"] is False
    assert governance["certification_ready"] is False


def test_t07_calibration_hash_is_stable() -> None:
    first = burned_t07_source_calibration_sha256()
    second = burned_t07_source_calibration_sha256()

    assert first == second
    assert len(first) == 64
