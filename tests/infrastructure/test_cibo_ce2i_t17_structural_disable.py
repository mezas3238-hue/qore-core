from qore.infrastructure.cibo_ce2i_t17_structural_disable import (
    assess_t17_structural_disable,
)


def _assessment(**overrides):
    values = {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "a" * 64,
        "taxonomy_binding_complete": True,
        "option_taxonomy_candidates": (),
        "account_limited_risk": False,
        "observed_symbols": 6,
        "gsl_supported_symbols": (),
        "gsl_unsupported_symbols": (
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        ),
        "gsl_unknown_symbols": (),
        "provider_universe_gsl_coverage_complete": True,
        "limited_risk_candidate_identified": False,
    }
    values.update(overrides)
    return assess_t17_structural_disable(**values)


def test_complete_provider_unavailability_structurally_disables_current_account() -> None:
    evidence = _assessment()

    assert evidence.structurally_disabled_for_current_account is True
    assert evidence.blockers == ()
    assert evidence.broker_mutation_performed is False
    assert evidence.holdout_outcomes_used is False
    assert evidence.productive_authority is False
    assert evidence.fingerprint().startswith("sha256:")


def test_option_taxonomy_candidate_keeps_t17_open() -> None:
    evidence = _assessment(option_taxonomy_candidates=("Options",))

    assert evidence.structurally_disabled_for_current_account is False
    assert "T17_STRUCTURAL_DISABLE_OPTION_TAXONOMY_PRESENT" in evidence.blockers


def test_limited_risk_account_keeps_t17_open() -> None:
    evidence = _assessment(account_limited_risk=True)

    assert evidence.structurally_disabled_for_current_account is False
    assert (
        "T17_STRUCTURAL_DISABLE_LIMITED_RISK_NOT_EXPLICITLY_FALSE"
        in evidence.blockers
    )


def test_any_gsl_support_keeps_t17_open() -> None:
    evidence = _assessment(
        gsl_supported_symbols=("EURUSD",),
        gsl_unsupported_symbols=(
            "AUDJPY",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        ),
    )

    assert evidence.structurally_disabled_for_current_account is False
    assert "T17_STRUCTURAL_DISABLE_GSL_SUPPORT_PRESENT" in evidence.blockers


def test_unknown_gsl_keeps_t17_open() -> None:
    evidence = _assessment(
        gsl_unsupported_symbols=(
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
        ),
        gsl_unknown_symbols=("XAUUSD",),
        provider_universe_gsl_coverage_complete=False,
    )

    assert evidence.structurally_disabled_for_current_account is False
    assert (
        "T17_STRUCTURAL_DISABLE_GSL_COVERAGE_INCOMPLETE"
        in evidence.blockers
    )
