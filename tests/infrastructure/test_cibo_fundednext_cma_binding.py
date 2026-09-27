from pathlib import Path

from qore.infrastructure.fundednext_cibo_risk_certification import build_certification
from qore.infrastructure.fundednext_pilot_manifest import build_manifest


def test_fundednext_manifest_binds_cibo_cma_and_risk_governor() -> None:
    payload = build_manifest(root=Path.cwd(), git_sha="a" * 40)

    assert payload["schema"] == (
        "qore.fundednext.stellar-instant-2k-pilot-readiness.v3"
    )

    cibo = payload["cibo_capital_management"]
    assert isinstance(cibo, dict)
    assert cibo["capital_management_authority"] is True
    assert cibo["runtime_sizing_authority"] is True
    assert cibo["legacy_trader_sizing_authority"] is False
    assert cibo["account_mission"] == "FUNDED_SURVIVAL_COMPOUND"
    assert cibo["provider"] == "FUNDEDNEXT"
    assert cibo["provider_program"] == "STELLAR_INSTANT"

    risk = payload["qore_internal_risk_policy"]
    assert isinstance(risk, dict)
    assert risk["risk_is_hard_survivability_governor"] is True
    assert risk["risk_is_capital_management_strategy_authority"] is False
    assert risk["risk_is_runtime_sizing_authority"] is False

    topology = payload["topology"]
    assert isinstance(topology, dict)
    assert topology["signal_flow"] == (
        "TRADER_OPPORTUNITY -> CIBO_CMA_SIZING -> ACCOUNT_WIDE_RISK -> "
        "RiskAuthorization -> LIVE_RISK_RECHECK -> MT5"
    )


def test_fundednext_component_certification_and_manifest_agree_on_authority() -> None:
    cert = build_certification(git_sha="b" * 40)
    manifest = build_manifest(root=Path.cwd(), git_sha="b" * 40)

    cibo = cert["cibo"]
    manifest_cibo = manifest["cibo_capital_management"]
    risk = cert["account_wide_risk"]
    manifest_risk = manifest["qore_internal_risk_policy"]

    assert isinstance(cibo, dict)
    assert isinstance(manifest_cibo, dict)
    assert isinstance(risk, dict)
    assert isinstance(manifest_risk, dict)

    assert (
        cibo["capital_management_authority"]
        == manifest_cibo["capital_management_authority"]
        is True
    )
    assert (
        cibo["runtime_sizing_authority"]
        == manifest_cibo["runtime_sizing_authority"]
        is True
    )
    assert (
        risk["hard_survivability_governor"]
        == manifest_risk["risk_is_hard_survivability_governor"]
        is True
    )
