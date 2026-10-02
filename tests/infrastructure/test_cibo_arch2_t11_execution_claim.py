from qore.infrastructure.cibo_arch2_t11_execution_claim import (
    HEAD_SHA,
    RUN_ATTEMPT,
    RUN_ID,
    T11_MARKET_IMPACT_EXECUTION_CLAIM,
)


def test_t11_first_execution_claim_is_exact_and_nonrerunnable() -> None:
    claim = T11_MARKET_IMPACT_EXECUTION_CLAIM

    assert claim.run_id == RUN_ID == 36945327912
    assert claim.run_attempt == RUN_ATTEMPT == 1
    assert claim.head_sha == HEAD_SHA == (
        "f239059c34897d395bf5503bea522c1795192bec"
    )
    assert claim.first_cycle_run is True
    assert claim.silent_rerun_allowed is False
    assert claim.replacement_requires_new_versioned_cycle is True
    assert claim.phase22_v2_consumed is False
    assert claim.canonical_ledger_modified is False
    assert claim.productive_authority is False
