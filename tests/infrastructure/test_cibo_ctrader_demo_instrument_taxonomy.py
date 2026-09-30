from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
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
    assert_taxonomy_bound_to_capability,
    collect_ctrader_demo_instrument_taxonomy,
)
from qore.kernel.result import Success

T0 = datetime(2026, 9, 30, 22, 30, tzinfo=UTC)


def _capability(*, category_id: int = 10) -> CTraderDemoAccountCapabilityObservation:
    symbols = (
        CTraderDemoCatalogSymbol(
            symbol_id=1,
            symbol_name="EURUSD",
            enabled=True,
            symbol_category_id=category_id,
            description="Euro US Dollar",
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
    )


class _Client:
    is_ready = True
    account_id = 12345

    def __init__(self) -> None:
        self.calls: list[str] = []

    def connect_and_authenticate(self):
        raise AssertionError("ready client must not reconnect")

    def request(
        self,
        message_name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        assert fields["ctidTraderAccountId"] == self.account_id
        assert client_msg_id
        assert timeout_seconds == 10.0
        self.calls.append(message_name)
        if message_name == "ProtoOAAssetClassListReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=self.account_id,
                    assetClass=(
                        SimpleNamespace(id=1, name="Forex"),
                        SimpleNamespace(id=2, name="Options"),
                    ),
                )
            )
        if message_name == "ProtoOASymbolCategoryListReq":
            return Success(
                SimpleNamespace(
                    ctidTraderAccountId=self.account_id,
                    symbolCategory=(
                        SimpleNamespace(id=10, assetClassId=1, name="Majors"),
                        SimpleNamespace(
                            id=20,
                            assetClassId=2,
                            name="Index Options",
                        ),
                    ),
                )
            )
        raise AssertionError(message_name)

    def wait_for_event(self, *args, **kwargs):
        raise AssertionError("taxonomy observation uses no event stream")

    def close(self) -> None:
        return None


def test_taxonomy_binds_symbol_categories_to_provider_asset_classes() -> None:
    client = _Client()

    result = collect_ctrader_demo_instrument_taxonomy(
        client,
        capability=_capability(),
        observed_at=T0,
    )

    assert result.account_ref == "12345"
    assert result.catalog_binding_complete is True
    assert result.symbol_catalog_sha256 == _capability().catalog_sha256
    assert tuple(item.asset_class_id for item in result.asset_classes) == (1, 2)
    assert tuple(item.category_id for item in result.symbol_categories) == (10, 20)
    assert result.option_taxonomy_candidates == ("Index Options", "Options")
    assert result.t16_economic_hedge_certified is False
    assert result.t17_option_structure_certified is False
    assert result.productive_authority is False
    assert result.taxonomy_sha256.startswith("sha256:")
    assert result.fingerprint().startswith("sha256:")
    assert client.calls == [
        "ProtoOAAssetClassListReq",
        "ProtoOASymbolCategoryListReq",
    ]


def test_taxonomy_candidate_label_never_certifies_t17() -> None:
    result = collect_ctrader_demo_instrument_taxonomy(
        _Client(),
        capability=_capability(),
        observed_at=T0,
    )

    assert result.option_taxonomy_candidates
    assert result.t17_option_structure_certified is False


def test_unresolved_symbol_category_keeps_binding_incomplete() -> None:
    result = collect_ctrader_demo_instrument_taxonomy(
        _Client(),
        capability=_capability(category_id=999),
        observed_at=T0,
    )

    assert result.catalog_binding_complete is False
    assert result.t17_option_structure_certified is False


def test_taxonomy_rejects_account_binding_mismatch() -> None:
    capability = _capability()
    bad = CTraderDemoAccountCapabilityObservation(
        account_ref="99999",
        observed_at=capability.observed_at,
        account_type=capability.account_type,
        account_type_field_present=capability.account_type_field_present,
        same_symbol_opposite_positions_supported=(
            capability.same_symbol_opposite_positions_supported
        ),
        symbols=capability.symbols,
        catalog_sha256=capability.catalog_sha256,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="account/capability binding mismatch",
    ):
        collect_ctrader_demo_instrument_taxonomy(
            _Client(),
            capability=bad,
            observed_at=T0,
        )


def test_consumer_binding_rejects_forged_complete_flag() -> None:
    capability = _capability(category_id=999)
    asset_classes = (
        CTraderDemoAssetClassEvidence(asset_class_id=1, name="Forex"),
    )
    categories = (
        CTraderDemoSymbolCategoryEvidence(
            category_id=10,
            asset_class_id=1,
            name="Majors",
        ),
    )
    taxonomy = CTraderDemoInstrumentTaxonomyObservation(
        account_ref=capability.account_ref,
        observed_at=T0,
        symbol_catalog_sha256=capability.catalog_sha256,
        asset_classes=asset_classes,
        symbol_categories=categories,
        taxonomy_sha256=_taxonomy_sha256(asset_classes, categories),
        catalog_binding_complete=True,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="completeness flag drift",
    ):
        assert_taxonomy_bound_to_capability(
            capability=capability,
            taxonomy=taxonomy,
        )
