from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t17_limited_risk_capability import (
    assess_t17_limited_risk_capability,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    CTraderDemoAccountType,
    CTraderDemoCatalogSymbol,
    _catalog_sha256,
)
from qore.infrastructure.cibo_ctrader_demo_instrument_taxonomy import (
    CTraderDemoAssetClassEvidence,
    CTraderDemoInstrumentTaxonomyObservation,
    CTraderDemoSymbolCategoryEvidence,
    _taxonomy_sha256,
)
from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    CTraderExpectedMarginQuote,
    CTraderNativeCommissionTerms,
    CTraderProviderEconomicsProbe,
    CTraderProviderEconomicsSymbolEvidence,
)
from qore.infrastructure.cibo_t17_provider_capability_receipt import (
    bind_t17_provider_capability_receipt,
    build_t17_provider_capability_source_artifact,
)

T0 = datetime(2026, 9, 30, 23, 45, tzinfo=UTC)
HEAD = "a" * 40
POLICY = "sha256:" + "b" * 64


def _account() -> CTraderDemoAccountCapabilityObservation:
    symbols = (
        CTraderDemoCatalogSymbol(
            symbol_id=1,
            symbol_name="EURUSD",
            enabled=True,
            symbol_category_id=10,
            description="Euro US Dollar",
        ),
        CTraderDemoCatalogSymbol(
            symbol_id=2,
            symbol_name="NAS100",
            enabled=True,
            symbol_category_id=10,
            description="Nasdaq 100",
        ),
    )
    return CTraderDemoAccountCapabilityObservation(
        account_ref="12345",
        observed_at=T0,
        account_type=CTraderDemoAccountType.HEDGED,
        account_type_field_present=True,
        same_symbol_opposite_positions_supported=True,
        symbols=symbols,
        catalog_sha256=_catalog_sha256(symbols),
        is_limited_risk=True,
        limited_risk_margin_calculation_strategy=1,
    )


def _taxonomy(
    account: CTraderDemoAccountCapabilityObservation,
) -> CTraderDemoInstrumentTaxonomyObservation:
    classes = (
        CTraderDemoAssetClassEvidence(
            asset_class_id=1,
            name="CFD",
        ),
    )
    categories = (
        CTraderDemoSymbolCategoryEvidence(
            category_id=10,
            asset_class_id=1,
            name="Indices and FX",
        ),
    )
    return CTraderDemoInstrumentTaxonomyObservation(
        account_ref=account.account_ref,
        observed_at=T0,
        symbol_catalog_sha256=account.catalog_sha256,
        asset_classes=classes,
        symbol_categories=categories,
        taxonomy_sha256=_taxonomy_sha256(classes, categories),
        catalog_binding_complete=True,
    )


def _symbol(name: str, symbol_id: int) -> CTraderProviderEconomicsSymbolEvidence:
    return CTraderProviderEconomicsSymbolEvidence(
        qore_symbol=name,
        provider_symbol=name,
        symbol_id=symbol_id,
        observed_at=T0,
        digits=5,
        bid=Decimal("100"),
        ask=Decimal("101"),
        min_volume_cents=1,
        max_volume_cents=100,
        step_volume_cents=1,
        lot_size_cents=100,
        commission=CTraderNativeCommissionTerms(
            precise_rate_raw=1,
            commission_type=1,
            precise_minimum_raw=1,
            minimum_type=1,
            minimum_asset="USD",
        ),
        expected_margin=(
            CTraderExpectedMarginQuote(
                native_volume_cents=1,
                buy_margin_usd=Decimal("1"),
                sell_margin_usd=Decimal("1"),
            ),
        ),
        margin_native_ready=True,
        spread_native_ready=True,
        guaranteed_stop_loss=True,
        gsl_distance=10,
        gsl_charge_raw=5,
    )


def _provider() -> CTraderProviderEconomicsProbe:
    return CTraderProviderEconomicsProbe(
        account_ref="12345",
        observed_at=T0,
        symbols=(
            _symbol("EURUSD", 1),
            _symbol("NAS100", 2),
        ),
    )


def test_t17_receipt_binds_account_provider_taxonomy_and_assessment() -> None:
    account = _account()
    provider = _provider()
    taxonomy = _taxonomy(account)
    assessment = assess_t17_limited_risk_capability(
        account=account,
        provider=provider,
    )

    receipt = bind_t17_provider_capability_receipt(
        account=account,
        provider=provider,
        taxonomy=taxonomy,
        assessment=assessment,
        integrated_git_sha=HEAD,
        policy_identity_sha256=POLICY,
    )
    payload = json.loads(receipt.source_artifact_json)

    assert receipt.integrated_git_sha == HEAD
    assert receipt.policy_identity_sha256 == POLICY
    assert payload["status"] == "PASS"
    assert payload["limited_risk_candidate_identified"] is True
    assert payload["t17_policy_ready"] is False
    assert payload["option_structure_proven"] is False
    assert payload["defined_risk_spread_proven"] is False
    assert payload["gsl_execution_economics_proven"] is False
    assert payload["fresh_oos_utility_demonstrated"] is False
    assert payload["productive_authority"] is False
    assert receipt.fingerprint().startswith("sha256:")


def test_noncanonical_assessment_is_rejected_even_when_types_are_valid() -> None:
    account = _account()
    provider = _provider()
    assessment = assess_t17_limited_risk_capability(
        account=account,
        provider=provider,
    )
    forged = replace(assessment, blockers=())

    with pytest.raises(
        CiboCapitalManagementError,
        match="assessment does not match canonical recomputation",
    ):
        build_t17_provider_capability_source_artifact(
            account=account,
            provider=provider,
            taxonomy=_taxonomy(account),
            assessment=forged,
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_provider_universe_must_exist_in_enabled_account_catalog() -> None:
    account = _account()
    provider = _provider()
    bad_rows = (
        replace(provider.symbols[0], provider_symbol="EURUSD"),
        replace(provider.symbols[1], provider_symbol="US100"),
    )
    bad_provider = replace(provider, symbols=bad_rows)
    assessment = assess_t17_limited_risk_capability(
        account=account,
        provider=bad_provider,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="provider universe not contained in enabled account catalog",
    ):
        build_t17_provider_capability_source_artifact(
            account=account,
            provider=bad_provider,
            taxonomy=_taxonomy(account),
            assessment=assessment,
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )


def test_taxonomy_catalog_drift_is_rejected() -> None:
    account = _account()
    provider = _provider()
    taxonomy = _taxonomy(account)
    bad_taxonomy = replace(
        taxonomy,
        symbol_catalog_sha256="sha256:" + "c" * 64,
    )
    assessment = assess_t17_limited_risk_capability(
        account=account,
        provider=provider,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="symbol catalog binding mismatch",
    ):
        build_t17_provider_capability_source_artifact(
            account=account,
            provider=provider,
            taxonomy=bad_taxonomy,
            assessment=assessment,
            integrated_git_sha=HEAD,
            policy_identity_sha256=POLICY,
        )
