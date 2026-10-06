from qore.infrastructure.cibo_ce2i_burned_t01_calibration import (
    SOURCE_PHASE18_ARTIFACTS,
    T01_MINIMAL_SEED_RULES,
    burned_t01_source_calibration_payload,
    burned_t01_source_calibration_sha256,
)


def test_t01_calibration_binds_all_seven_canonical_lineages() -> None:
    payload = burned_t01_source_calibration_payload()

    assert payload["classification"] == "CALIBRATED_CAUSAL"
    assert len(SOURCE_PHASE18_ARTIFACTS) == 7
    assert len({item[0] for item in SOURCE_PHASE18_ARTIFACTS}) == 7
    assert (
        "TRADER_REQUESTED_VOLUME_IS_NOT_RUNTIME_AUTHORITY"
        in T01_MINIMAL_SEED_RULES
    )
    assert (
        "MINIMUM_SEED_USES_PROVIDER_MINIMUM_AND_VOLUME_STEP"
        in T01_MINIMAL_SEED_RULES
    )
    assert (
        "VT31_REQUIRES_FOUR_MINIMUM_EXECUTION_STEPS"
        in T01_MINIMAL_SEED_RULES
    )


def test_t01_calibration_does_not_claim_historical_provider_economics() -> None:
    payload = burned_t01_source_calibration_payload()
    governance = payload["governance"]

    assert payload["historical_2017_provider_terms_calibrated"] is False
    assert payload["exact_execution_cost_calibrated"] is False
    assert payload["slippage_empirically_calibrated"] is False
    assert payload["incremental_economic_utility_calibrated"] is False
    assert governance["provider_economics_required"] is True
    assert governance["holdout_2017h1_used"] is False
    assert governance["historical_usd_execution_economics_claimed"] is False
    assert governance["target_aware"] is False
    assert governance["oos_ready"] is False
    assert governance["certification_ready"] is False


def test_t01_calibration_hash_is_stable() -> None:
    first = burned_t01_source_calibration_sha256()
    second = burned_t01_source_calibration_sha256()

    assert first == second
    assert len(first) == 64
