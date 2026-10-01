from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_t17_governed_provider_disposition import (
    TERMINAL_DISPOSITION,
    assess_t17_governed_provider_disposition,
)

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / (
    "docs/research/"
    "CIBO-B-CTRADER-DEMO-PROVIDER-EVIDENCE-2026-10-01.json"
)
STRUCTURAL = ROOT / "docs/research/CIBO-B-T17-STRUCTURAL-DISPOSITION-V1.json"


def _documents() -> tuple[dict, dict]:
    return (
        json.loads(PROVIDER.read_text(encoding="utf-8")),
        json.loads(STRUCTURAL.read_text(encoding="utf-8")),
    )


def test_current_governed_provider_universe_closes_t17_as_ineligible() -> None:
    provider, structural = _documents()

    report = assess_t17_governed_provider_disposition(
        provider_evidence=provider,
        structural_disposition=structural,
    )

    assert report.provider_ineligible is True
    assert report.terminal_disposition == TERMINAL_DISPOSITION
    assert report.global_market_claim is False
    assert report.productive_authority is False
    assert report.reopen_conditions


def test_any_ctrader_gsl_support_reopens_t17() -> None:
    provider, structural = _documents()
    provider = copy.deepcopy(provider)
    universe = provider["governed_universe"]
    universe["gsl_supported_symbols"] = ["NAS100"]
    universe["gsl_unsupported_symbols"] = [
        item for item in universe["symbols"] if item != "NAS100"
    ]

    with pytest.raises(
        CiboCapitalManagementError,
        match="cTrader provider-ineligibility not proven",
    ):
        assess_t17_governed_provider_disposition(
            provider_evidence=provider,
            structural_disposition=structural,
        )


def test_fundednext_option_listing_reopens_t17() -> None:
    provider, structural = _documents()
    structural = copy.deepcopy(structural)
    row = structural["fundednext_stellar_instant_cfd"]
    row["option_or_defined_risk_instrument_class_listed"] = True

    with pytest.raises(
        CiboCapitalManagementError,
        match="FundedNext provider-ineligibility not proven",
    ):
        assess_t17_governed_provider_disposition(
            provider_evidence=provider,
            structural_disposition=structural,
        )


def test_global_market_claim_is_rejected() -> None:
    provider, structural = _documents()
    structural = copy.deepcopy(structural)
    structural["conclusion"]["global_market_claim"] = True

    with pytest.raises(
        CiboCapitalManagementError,
        match="global market claim",
    ):
        assess_t17_governed_provider_disposition(
            provider_evidence=provider,
            structural_disposition=structural,
        )
