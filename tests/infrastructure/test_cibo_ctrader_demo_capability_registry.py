from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    CTraderDemoAccountType,
    CTraderDemoCatalogSymbol,
)
from qore.infrastructure.cibo_ctrader_demo_instrument_taxonomy import (
    CTraderDemoAssetClassEvidence,
    CTraderDemoInstrumentTaxonomyObservation,
    CTraderDemoSymbolCategoryEvidence,
    _taxonomy_sha256,
)
from qore.infrastructure.cibo_ctrader_demo_capability_registry import (
    reconcile_ctrader_demo_capability_registry,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 9, 30, 18, 0, tzinfo=UTC)


def _identity(account_ref: str = "12345") -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _observation(
    account_type: CTraderDemoAccountType,
    *,
    name: str = "US100_OPTION_LOOKING_NAME",
) -> CTraderDemoAccountCapabilityObservation:
    symbol = CTraderDemoCatalogSymbol(
        symbol_id=1,
        symbol_name=name,
        enabled=True,
        symbol_category_id=1,
        description="name alone is not product-class evidence",
    )
    same_symbol = {
        CTraderDemoAccountType.HEDGED: True,
        CTraderDemoAccountType.NETTED: False,
        CTraderDemoAccountType.SPREAD_BETTING: None,
        CTraderDemoAccountType.UNKNOWN: None,
    }[account_type]
    from qore.infrastructure.cibo_ctrader_demo_account_capability import (
        _catalog_sha256,
    )

    return CTraderDemoAccountCapabilityObservation(
        account_ref="12345",
        observed_at=T0,
        account_type=account_type,
        account_type_field_present=(
            account_type is not CTraderDemoAccountType.UNKNOWN
        ),
        same_symbol_opposite_positions_supported=same_symbol,
        symbols=(symbol,),
        catalog_sha256=_catalog_sha256((symbol,)),
    )



def _taxonomy(
    observation: CTraderDemoAccountCapabilityObservation,
    *,
    option_candidate: bool,
) -> CTraderDemoInstrumentTaxonomyObservation:
    asset_classes = (
        CTraderDemoAssetClassEvidence(
            asset_class_id=1,
            name="Options" if option_candidate else "Indices",
        ),
    )
    categories = (
        CTraderDemoSymbolCategoryEvidence(
            category_id=1,
            asset_class_id=1,
            name="Index Options" if option_candidate else "US Indices",
        ),
    )
    return CTraderDemoInstrumentTaxonomyObservation(
        account_ref=observation.account_ref,
        observed_at=T0,
        symbol_catalog_sha256=observation.catalog_sha256,
        asset_classes=asset_classes,
        symbol_categories=categories,
        taxonomy_sha256=_taxonomy_sha256(asset_classes, categories),
        catalog_binding_complete=True,
    )

def test_hedged_account_does_not_promote_t16_or_t17() -> None:
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=_observation(CTraderDemoAccountType.HEDGED),
    )

    assert report.netting_status is CapabilityStatus.UNAVAILABLE
    assert report.t16_hedge_status is CapabilityStatus.UNKNOWN
    assert report.t17_option_status is CapabilityStatus.UNKNOWN
    assert (
        report.t17_defined_risk_spread_status
        is CapabilityStatus.UNKNOWN
    )
    assert report.runtime_authority is False
    assert report.registry.status(
        capability=InstrumentCapability.HEDGE,
        at=T0,
    ) is CapabilityStatus.UNKNOWN


def test_netted_account_proves_only_netting_semantics() -> None:
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=_observation(CTraderDemoAccountType.NETTED),
    )

    assert report.netting_status is CapabilityStatus.SUPPORTED
    assert report.registry.status(
        capability=InstrumentCapability.NETTING,
        at=T0,
    ) is CapabilityStatus.SUPPORTED
    assert report.t16_hedge_status is CapabilityStatus.UNKNOWN


def test_symbol_name_never_infers_option_or_defined_risk_spread() -> None:
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=_observation(
            CTraderDemoAccountType.HEDGED,
            name="OPTION_CALL_SPREAD_CFD",
        ),
    )

    assert report.t17_option_status is CapabilityStatus.UNKNOWN
    assert (
        report.t17_defined_risk_spread_status
        is CapabilityStatus.UNKNOWN
    )


def test_unknown_account_type_stays_fail_closed() -> None:
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=_observation(CTraderDemoAccountType.UNKNOWN),
    )

    assert report.netting_status is CapabilityStatus.UNKNOWN
    assert report.t16_hedge_status is CapabilityStatus.UNKNOWN


def test_account_binding_mismatch_is_rejected() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="account identity mismatch",
    ):
        reconcile_ctrader_demo_capability_registry(
            account_identity=_identity("other"),
            observation=_observation(CTraderDemoAccountType.HEDGED),
        )


def test_provider_taxonomy_is_bound_without_promoting_t17() -> None:
    observation = _observation(CTraderDemoAccountType.HEDGED)
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=observation,
        taxonomy=_taxonomy(observation, option_candidate=True),
    )

    assert report.taxonomy_binding_complete is True
    assert report.option_taxonomy_candidates == ("Index Options", "Options")
    assert report.t17_option_status is CapabilityStatus.UNKNOWN
    assert report.t17_defined_risk_spread_status is CapabilityStatus.UNKNOWN
    assert (
        "T17_OPTION_TAXONOMY_CANDIDATE_REQUIRES_INSTRUMENT_EXECUTION_PROOF"
        in report.blockers
    )


def test_complete_taxonomy_without_option_label_remains_fail_closed() -> None:
    observation = _observation(CTraderDemoAccountType.HEDGED)
    report = reconcile_ctrader_demo_capability_registry(
        account_identity=_identity(),
        observation=observation,
        taxonomy=_taxonomy(observation, option_candidate=False),
    )

    assert report.taxonomy_binding_complete is True
    assert report.option_taxonomy_candidates == ()
    assert report.t17_option_status is CapabilityStatus.UNKNOWN
    assert "T17_NO_EXPLICIT_OPTION_TAXONOMY_CANDIDATE" in report.blockers
