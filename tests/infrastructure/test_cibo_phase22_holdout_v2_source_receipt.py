from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    CiboHoldoutCandidateStatus,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    V2_SOURCE_BINDINGS,
    VT08_REQUIRED_MARKETS,
    phase22_v2_holdout_source_receipt_payload,
)


def test_v2_registry_is_promoted_only_after_source_validation() -> None:
    candidate = ACTIVE_USD60_HOLDOUT_CANDIDATE

    assert candidate.candidate_id == CANDIDATE_ID
    assert candidate.status is CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN
    assert candidate.source_validation_complete is True


def test_v2_receipt_binds_nine_m5_archives_and_nas100_m1() -> None:
    m5 = tuple(item for item in V2_SOURCE_BINDINGS if item.timeframe == "M5")
    m1 = tuple(item for item in V2_SOURCE_BINDINGS if item.timeframe == "M1")

    assert len(m5) == 9
    assert len(m1) == 1
    assert m1[0].symbol == "NAS100"
    assert m1[0].retained_bars == 170396
    assert m1[0].first_observed_at == "2015-10-19T00:00:00+00:00"
    assert m1[0].last_observed_at == "2016-04-18T23:59:00+00:00"
    assert set(VT08_REQUIRED_MARKETS).issubset({item.symbol for item in m5})
    assert all(
        item.artifact_digest.startswith("sha256:")
        for item in V2_SOURCE_BINDINGS
    )


def test_v2_receipt_payload_is_source_only() -> None:
    payload = phase22_v2_holdout_source_receipt_payload()

    assert payload["schema"] == "qore.cibo.phase22.holdout-source-receipt.v2"
    assert payload["candidate_id"] == CANDIDATE_ID
    assert payload["status"] == "ELIGIBLE_FROZEN"
    assert payload["scientifically_consumable"] is True
    assert len(payload["source_archives"]) == 10
    assert payload["trader_logic_executed"] is False
    assert payload["outcomes_inspected"] is False
    assert payload["productive_authority"] is False
