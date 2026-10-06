from qore.infrastructure.cibo_arch2_t16_terminal_falsification import (
    ARTIFACT_DIGEST,
    ARTIFACT_ID,
    PAYLOAD_SHA256,
    RUN_HEAD_SHA,
    RUN_ID,
    T16_TERMINAL_FALSIFICATION_RECEIPT,
)


def test_t16_terminal_receipt_exhausts_frozen_hedge_universe() -> None:
    receipt = T16_TERMINAL_FALSIFICATION_RECEIPT

    assert RUN_ID == 36941142280
    assert RUN_HEAD_SHA == "f8c6409af5893ca8189a7aa13a3d406c4d19b649"
    assert ARTIFACT_ID == 11199498760
    assert ARTIFACT_DIGEST.startswith("sha256:")
    assert PAYLOAD_SHA256.startswith("sha256:")
    assert receipt.recommendation == "FALSIFIED_AND_CLOSED"
    assert receipt.target_symbol == "NAS100"
    assert receipt.provider_target_symbol == "USTEC"
    assert receipt.candidate_passes == ()
    assert receipt.all_preregistered_candidates_exhausted is True
    assert tuple(item.hedge_symbol for item in receipt.candidates) == (
        "US30",
        "US500",
    )
    assert all(
        item.fold_passes == (False, False, False, False)
        for item in receipt.candidates
    )
    assert all(
        all(value < 0 for value in item.net_protection_fraction_by_fold)
        for item in receipt.candidates
    )
    assert receipt.broker_mutation_performed is False
    assert receipt.holdout_outcomes_used is False
    assert receipt.phase22_v2_consumed is False
    assert receipt.canonical_ledger_modified is False
    assert receipt.productive_authority is False
    assert receipt.fingerprint().startswith("sha256:")
