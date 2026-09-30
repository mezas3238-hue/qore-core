from scripts.cibo_t17_limited_risk_capability_probe import build_report


def _account(*, limited: bool | None = True) -> dict[str, object]:
    return {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "a" * 64,
        "is_limited_risk": limited,
        "limited_risk_margin_calculation_strategy": 1 if limited is True else None,
    }


def _provider(*, eurusd: bool | None, nas100: bool | None) -> dict[str, object]:
    return {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "a" * 64,
        "symbols": {
            "EURUSD": {"guaranteed_stop_loss": eurusd},
            "NAS100": {"guaranteed_stop_loss": nas100},
        },
    }


def test_export_identifies_gsl_candidate_but_never_promotes_t17() -> None:
    report = build_report(
        account_report=_account(),
        provider_report=_provider(eurusd=True, nas100=True),
    )

    assert report["limited_risk_candidate_identified"] is True
    assert report["provider_universe_gsl_coverage_complete"] is True
    assert report["gsl_supported_symbols"] == ["EURUSD", "NAS100"]
    assert report["option_structure_proven"] is False
    assert report["defined_risk_spread_proven"] is False
    assert report["gsl_execution_economics_proven"] is False
    assert report["fresh_oos_utility_demonstrated"] is False
    assert report["t17_policy_ready"] is False
    assert report["productive_authority"] is False


def test_export_fails_closed_on_unknown_gsl_coverage() -> None:
    report = build_report(
        account_report=_account(),
        provider_report=_provider(eurusd=True, nas100=None),
    )

    assert report["limited_risk_candidate_identified"] is False
    assert report["provider_universe_gsl_coverage_complete"] is False
    assert report["gsl_unknown_symbols"] == ["NAS100"]
    assert (
        "T17_GSL_PROVIDER_UNIVERSE_COVERAGE_INCOMPLETE"
        in report["blockers"]
    )


def test_export_requires_same_account_fingerprint() -> None:
    provider = _provider(eurusd=True, nas100=True)
    provider["account_fingerprint_sha256"] = "b" * 64

    try:
        build_report(
            account_report=_account(),
            provider_report=provider,
        )
    except ValueError as error:
        assert "fingerprint binding mismatch" in str(error)
    else:
        raise AssertionError("mismatched provider account must fail closed")
