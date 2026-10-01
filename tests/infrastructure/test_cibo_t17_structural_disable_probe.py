import pytest

from scripts.cibo_t17_structural_disable_probe import build_report


def _account() -> dict[str, object]:
    return {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "b" * 64,
        "taxonomy_binding_complete": True,
        "option_taxonomy_candidates": [],
    }


def _limited() -> dict[str, object]:
    return {
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": "b" * 64,
        "account_limited_risk": False,
        "observed_symbols": 2,
        "gsl_supported_symbols": [],
        "gsl_unsupported_symbols": ["EURUSD", "NAS100"],
        "gsl_unknown_symbols": [],
        "provider_universe_gsl_coverage_complete": True,
        "limited_risk_candidate_identified": False,
    }


def test_probe_emits_scoped_structural_disable_evidence() -> None:
    report = build_report(
        account_report=_account(),
        limited_risk_report=_limited(),
    )

    assert report["schema"] == "qore.cibo.t17.structural_disable.v1"
    assert report["structurally_disabled_for_current_account"] is True
    assert report["blockers"] == ()
    assert report["broker_mutation_performed"] is False
    assert report["holdout_outcomes_used"] is False
    assert report["productive_authority"] is False
    assert str(report["evidence_sha256"]).startswith("sha256:")


def test_probe_keeps_t17_open_when_option_taxonomy_exists() -> None:
    account = _account()
    account["option_taxonomy_candidates"] = ["Options"]

    report = build_report(
        account_report=account,
        limited_risk_report=_limited(),
    )

    assert report["structurally_disabled_for_current_account"] is False
    assert "T17_STRUCTURAL_DISABLE_OPTION_TAXONOMY_PRESENT" in report["blockers"]


def test_probe_rejects_truthy_non_boolean_taxonomy_flag() -> None:
    account = _account()
    account["taxonomy_binding_complete"] = "true"

    with pytest.raises(ValueError, match="taxonomy flag invalid"):
        build_report(
            account_report=account,
            limited_risk_report=_limited(),
        )
