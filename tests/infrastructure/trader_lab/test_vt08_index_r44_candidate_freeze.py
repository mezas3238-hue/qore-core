from qore.infrastructure.trader_lab import (
    vt08_index_r44_candidate_freeze as mod,
)


def test_r44_freezes_passing_r43_identity() -> None:
    assert mod.CANDIDATE_ID == "VT08_INDEX_R43_SOURCE_COMPLETE_2448_001"
    assert mod.FIVE_YEAR_SAMPLE == 2448
    assert mod.SOURCE_RUN_ID == 35418460354
    assert mod.SOURCE_ARTIFACT_ID == 10576224564
    assert len(mod.RULE_FINGERPRINT) == 64


def test_r44_dependency_contract_is_exact() -> None:
    assert mod.dependency_contract_matches() is True
    assert mod.POI_OVERLAY["profile_id"] == "PO-W10-N5-C0.50-WEAK0.50-T0.05"
    assert mod.STRUCTURAL_PRIORS["nas100_market_multiplier"] == "0.50"
    assert mod.STRUCTURAL_PRIORS["nas100_short_total_multiplier"] == "0.2500"
    assert mod.STRUCTURAL_PRIORS["sp500_long_multiplier"] == "0.75"


def test_r44_freeze_grants_no_authority() -> None:
    g = mod.GOVERNANCE
    assert g["candidate_frozen"] is True
    assert g["two_year_retuning_permitted"] is False
    assert g["live_authorized"] is False
    assert g["real_capital_authorized"] is False
    assert g["production_authorized"] is False
