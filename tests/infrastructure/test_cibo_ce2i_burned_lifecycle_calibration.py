from qore.infrastructure.cibo_ce2i_burned_lifecycle_calibration import (
    T05_RECYCLE_RULES,
    T19_RESERVATION_RULES,
    T20_RELEASE_RULES,
    burned_lifecycle_calibration_payload,
    burned_lifecycle_calibration_sha256,
)


def test_burned_lifecycle_calibration_is_holdout_clean_and_non_economic() -> None:
    payload = burned_lifecycle_calibration_payload()

    assert payload["governance"]["holdout_2017h1_used"] is False
    assert payload["governance"]["provider_usd_economics_claimed"] is False
    assert payload["governance"]["target_aware"] is False
    assert payload["governance"]["oos_ready"] is False
    assert payload["governance"]["certification_ready"] is False


def test_t05_recycling_requires_release_and_reconciliation() -> None:
    assert "CAPACITY_REUSABLE_ONLY_AFTER_AUTHORITATIVE_RELEASE" in T05_RECYCLE_RULES
    assert "RECONCILIATION_PRECEDES_REDEPLOYMENT" in T05_RECYCLE_RULES
    assert (
        "NO_SAME_TIMESTAMP_EXIT_RECYCLING_WITHOUT_SETTLEMENT_EVIDENCE"
        in T05_RECYCLE_RULES
    )


def test_t19_reservation_forbids_double_spend_and_requires_cas() -> None:
    assert "RESERVE_BEFORE_DEPLOYMENT" in T19_RESERVATION_RULES
    assert "DUPLICATE_RESERVATION_FORBIDDEN" in T19_RESERVATION_RULES
    assert "CAPACITY_CONSERVATION_REQUIRED" in T19_RESERVATION_RULES
    assert "GENERATION_CAS_REQUIRED_FOR_DURABLE_UPDATE" in T19_RESERVATION_RULES


def test_t20_release_requires_valid_reconciled_lifecycle() -> None:
    assert "RELEASE_REQUIRES_VALID_LIFECYCLE_EVENT" in T20_RELEASE_RULES
    assert "PREMATURE_RELEASE_FORBIDDEN" in T20_RELEASE_RULES
    assert (
        "DEPLOYED_CAPACITY_NOT_REUSABLE_BEFORE_RECONCILIATION"
        in T20_RELEASE_RULES
    )


def test_burned_lifecycle_calibration_hash_is_stable() -> None:
    first = burned_lifecycle_calibration_sha256()
    second = burned_lifecycle_calibration_sha256()

    assert first == second
    assert len(first) == 64
