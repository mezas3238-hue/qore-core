"""Read-only account-bound cTrader instrument taxonomy for CIBO T16/T17.

The cTrader light-symbol catalog exposes only symbolCategoryId. This module
resolves those ids through the provider's own account-scoped symbol-category
and asset-class endpoints. The result is evidence about provider taxonomy only:
it never infers an option/defined-risk instrument from a symbol name, never
certifies T16/T17 economic utility, and performs no broker mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure


@dataclass(frozen=True, slots=True)
class CTraderDemoAssetClassEvidence:
    asset_class_id: int
    name: str

    def __post_init__(self) -> None:
        if type(self.asset_class_id) is not int or self.asset_class_id <= 0:
            raise CiboCapitalManagementError(
                "cTrader taxonomy asset_class_id must be positive int"
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise CiboCapitalManagementError(
                "cTrader taxonomy asset-class name is required"
            )


@dataclass(frozen=True, slots=True)
class CTraderDemoSymbolCategoryEvidence:
    category_id: int
    asset_class_id: int
    name: str

    def __post_init__(self) -> None:
        if type(self.category_id) is not int or self.category_id <= 0:
            raise CiboCapitalManagementError(
                "cTrader taxonomy category_id must be positive int"
            )
        if type(self.asset_class_id) is not int or self.asset_class_id <= 0:
            raise CiboCapitalManagementError(
                "cTrader taxonomy category asset_class_id must be positive int"
            )
        if not isinstance(self.name, str) or not self.name.strip():
            raise CiboCapitalManagementError(
                "cTrader taxonomy category name is required"
            )


@dataclass(frozen=True, slots=True)
class CTraderDemoInstrumentTaxonomyObservation:
    account_ref: str
    observed_at: datetime
    symbol_catalog_sha256: str
    asset_classes: tuple[CTraderDemoAssetClassEvidence, ...]
    symbol_categories: tuple[CTraderDemoSymbolCategoryEvidence, ...]
    taxonomy_sha256: str
    catalog_binding_complete: bool
    broker_mutation_performed: bool = False
    t16_economic_hedge_certified: bool = False
    t17_option_structure_certified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.account_ref, str) or not self.account_ref:
            raise CiboCapitalManagementError(
                "cTrader taxonomy account_ref is required"
            )
        _aware(self.observed_at, "observed_at")
        _sha(self.symbol_catalog_sha256, "symbol_catalog_sha256")
        _sha(self.taxonomy_sha256, "taxonomy_sha256")
        class_ids = tuple(item.asset_class_id for item in self.asset_classes)
        category_ids = tuple(item.category_id for item in self.symbol_categories)
        if class_ids != tuple(sorted(class_ids)) or len(class_ids) != len(
            set(class_ids)
        ):
            raise CiboCapitalManagementError(
                "cTrader taxonomy asset classes must be sorted unique"
            )
        if category_ids != tuple(sorted(category_ids)) or len(
            category_ids
        ) != len(set(category_ids)):
            raise CiboCapitalManagementError(
                "cTrader taxonomy categories must be sorted unique"
            )
        known_classes = set(class_ids)
        if any(
            item.asset_class_id not in known_classes
            for item in self.symbol_categories
        ):
            raise CiboCapitalManagementError(
                "cTrader taxonomy category references unknown asset class"
            )
        expected_sha = _taxonomy_sha256(
            self.asset_classes,
            self.symbol_categories,
        )
        if self.taxonomy_sha256 != expected_sha:
            raise CiboCapitalManagementError(
                "cTrader taxonomy digest drift"
            )
        if type(self.catalog_binding_complete) is not bool:
            raise CiboCapitalManagementError(
                "cTrader taxonomy binding flag must be bool"
            )
        if (
            self.broker_mutation_performed
            or self.t16_economic_hedge_certified
            or self.t17_option_structure_certified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "cTrader taxonomy observation cannot promote T16/T17/runtime authority"
            )

    @property
    def option_taxonomy_candidates(self) -> tuple[str, ...]:
        """Return provider taxonomy labels containing the explicit option token."""

        labels = {
            item.name.strip()
            for item in self.asset_classes
            if _contains_option_token(item.name)
        }
        labels.update(
            item.name.strip()
            for item in self.symbol_categories
            if _contains_option_token(item.name)
        )
        return tuple(sorted(labels))

    def fingerprint(self) -> str:
        return _digest(
            {
                **asdict(self),
                "option_taxonomy_candidates": list(
                    self.option_taxonomy_candidates
                ),
            }
        )


def collect_ctrader_demo_instrument_taxonomy(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    capability: CTraderDemoAccountCapabilityObservation,
    observed_at: datetime | None = None,
) -> CTraderDemoInstrumentTaxonomyObservation:
    """Resolve the account's symbol-category and asset-class taxonomy read-only."""

    if not isinstance(capability, CTraderDemoAccountCapabilityObservation):
        raise CiboCapitalManagementError(
            "cTrader taxonomy requires canonical account capability observation"
        )
    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(str(connected.error))
    account_id = client.account_id
    if type(account_id) is not int or account_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader taxonomy account id must be positive int"
        )
    if capability.account_ref != str(account_id):
        raise CiboCapitalManagementError(
            "cTrader taxonomy account/capability binding mismatch"
        )

    asset_response = _request(
        client,
        "ProtoOAAssetClassListReq",
        {"ctidTraderAccountId": account_id},
        "qore-cibo-instrument-taxonomy-asset-classes",
    )
    category_response = _request(
        client,
        "ProtoOASymbolCategoryListReq",
        {"ctidTraderAccountId": account_id},
        "qore-cibo-instrument-taxonomy-symbol-categories",
    )
    _response_account(asset_response, account_id, "asset-class")
    _response_account(category_response, account_id, "symbol-category")

    raw_classes = getattr(asset_response, "assetClass", None)
    raw_categories = getattr(category_response, "symbolCategory", None)
    if raw_classes is None or raw_categories is None:
        raise CiboCapitalManagementError(
            "cTrader taxonomy response omitted required collections"
        )

    asset_classes = tuple(
        sorted(
            (_asset_class(item) for item in tuple(raw_classes)),
            key=lambda item: item.asset_class_id,
        )
    )
    symbol_categories = tuple(
        sorted(
            (_symbol_category(item) for item in tuple(raw_categories)),
            key=lambda item: item.category_id,
        )
    )
    if not asset_classes or not symbol_categories:
        raise CiboCapitalManagementError(
            "cTrader taxonomy collections cannot be empty"
        )

    class_ids = {item.asset_class_id for item in asset_classes}
    category_by_id = {item.category_id: item for item in symbol_categories}
    enabled_symbols = tuple(item for item in capability.symbols if item.enabled)
    complete = bool(enabled_symbols) and all(
        item.symbol_category_id is not None
        and item.symbol_category_id in category_by_id
        and category_by_id[item.symbol_category_id].asset_class_id in class_ids
        for item in enabled_symbols
    )

    observed = observed_at or datetime.now(UTC)
    _aware(observed, "observed_at")
    if observed < capability.observed_at:
        raise CiboCapitalManagementError(
            "cTrader taxonomy observation cannot predate account capability"
        )

    return CTraderDemoInstrumentTaxonomyObservation(
        account_ref=str(account_id),
        observed_at=observed,
        symbol_catalog_sha256=capability.catalog_sha256,
        asset_classes=asset_classes,
        symbol_categories=symbol_categories,
        taxonomy_sha256=_taxonomy_sha256(asset_classes, symbol_categories),
        catalog_binding_complete=complete,
    )


def _asset_class(value: object) -> CTraderDemoAssetClassEvidence:
    asset_class_id = getattr(value, "id", None)
    name = getattr(value, "name", None)
    if type(asset_class_id) is not int or asset_class_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader taxonomy asset-class id invalid"
        )
    if not isinstance(name, str) or not name.strip():
        raise CiboCapitalManagementError(
            "cTrader taxonomy asset-class name invalid"
        )
    return CTraderDemoAssetClassEvidence(
        asset_class_id=asset_class_id,
        name=name.strip(),
    )


def _symbol_category(value: object) -> CTraderDemoSymbolCategoryEvidence:
    category_id = getattr(value, "id", None)
    asset_class_id = getattr(value, "assetClassId", None)
    name = getattr(value, "name", None)
    if type(category_id) is not int or category_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader taxonomy symbol-category id invalid"
        )
    if type(asset_class_id) is not int or asset_class_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader taxonomy symbol-category asset-class id invalid"
        )
    if not isinstance(name, str) or not name.strip():
        raise CiboCapitalManagementError(
            "cTrader taxonomy symbol-category name invalid"
        )
    return CTraderDemoSymbolCategoryEvidence(
        category_id=category_id,
        asset_class_id=asset_class_id,
        name=name.strip(),
    )


def _request(
    client: CTraderOpenApiMessageClientBoundary,
    name: str,
    fields: dict[str, object],
    message_id: str,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=message_id,
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise CiboCapitalManagementError(str(result.error))
    return result.value


def _response_account(value: object, account_id: int, label: str) -> None:
    if getattr(value, "ctidTraderAccountId", None) != account_id:
        raise CiboCapitalManagementError(
            f"cTrader taxonomy {label} response account mismatch"
        )


def _contains_option_token(value: str) -> bool:
    normalized = "".join(
        char.lower() if char.isalnum() else " " for char in value
    )
    return "option" in normalized.split() or "options" in normalized.split()


def _taxonomy_sha256(
    asset_classes: tuple[CTraderDemoAssetClassEvidence, ...],
    symbol_categories: tuple[CTraderDemoSymbolCategoryEvidence, ...],
) -> str:
    return _digest(
        {
            "asset_classes": [asdict(item) for item in asset_classes],
            "symbol_categories": [asdict(item) for item in symbol_categories],
        }
    )


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"cTrader taxonomy {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"cTrader taxonomy {name} must be timezone-aware"
        )
