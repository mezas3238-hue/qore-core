from qore.infrastructure.cibo_ce2i_t16_preregistered_hedge_universe import (
    PREREGISTERED_T16_HEDGE_CANDIDATES,
    T16_ACCOUNT_FINGERPRINT_SHA256,
    T16_DECLARED_AT,
    T16_PROVIDER_CATALOG_OBSERVED_AT,
    T16_PROVIDER_CATALOG_SHA256,
    preregistered_t16_hedge_declarations,
)


def test_t16_candidate_universe_is_fixed_before_pair_outcomes() -> None:
    candidates = PREREGISTERED_T16_HEDGE_CANDIDATES

    assert len(candidates) == 2
    assert {item.declaration.hedge_symbol for item in candidates} == {
        "US30",
        "US500",
    }
    assert {item.declaration.target_symbol for item in candidates} == {
        "NAS100"
    }
    assert {item.target_provider_symbol for item in candidates} == {"USTEC"}
    assert T16_PROVIDER_CATALOG_OBSERVED_AT < T16_DECLARED_AT

    for item in candidates:
        assert item.provider_catalog_sha256 == T16_PROVIDER_CATALOG_SHA256
        assert (
            item.account_fingerprint_sha256
            == T16_ACCOUNT_FINGERPRINT_SHA256
        )
        assert item.declaration.evidence_sha256 == T16_PROVIDER_CATALOG_SHA256
        assert item.declaration.productive_authority is False
        assert item.returns_inspected_at_selection is False
        assert item.correlation_inspected_at_selection is False
        assert item.basis_risk_inspected_at_selection is False
        assert item.hedge_cost_inspected_at_selection is False
        assert item.productive_authority is False


def test_t16_preregistered_declarations_are_unique_and_provider_bound() -> None:
    declarations = preregistered_t16_hedge_declarations()

    assert len(declarations) == 2
    assert len({item.declaration_id for item in declarations}) == 2
    assert {item.provider_key for item in declarations} == {"ctrader-demo"}
    assert {item.hedge_symbol for item in declarations} == {"US30", "US500"}
