"""Read-only account-bound capability observation for cTrader DEMO.

This probe intentionally separates *account mode* from CE2I T16/T17
instrument capability. A HEDGED account proves only that the connected account
can keep opposite same-symbol positions. It does not prove that a valid hedge
instrument, basis-risk model, option structure, or economically useful risk
transfer exists.

The probe reads only ProtoOATraderReq and ProtoOASymbolsListReq. It performs no
broker mutation and never upgrades an absent/ambiguous provider field into
support.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure


class CTraderDemoAccountType(StrEnum):
    HEDGED = "HEDGED"
    NETTED = "NETTED"
    SPREAD_BETTING = "SPREAD_BETTING"
    UNKNOWN = "UNKNOWN"


_ACCOUNT_TYPE_BY_NATIVE = {
    0: CTraderDemoAccountType.HEDGED,
    1: CTraderDemoAccountType.NETTED,
    2: CTraderDemoAccountType.SPREAD_BETTING,
}


@dataclass(frozen=True, slots=True)
class CTraderDemoCatalogSymbol:
    symbol_id: int
    symbol_name: str
    enabled: bool
    symbol_category_id: int | None
    description: str | None

    def __post_init__(self) -> None:
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CiboCapitalManagementError(
                "cTrader capability symbol_id must be positive int"
            )
        if not isinstance(self.symbol_name, str) or not self.symbol_name:
            raise CiboCapitalManagementError(
                "cTrader capability symbol_name is required"
            )
        if type(self.enabled) is not bool:
            raise CiboCapitalManagementError(
                "cTrader capability enabled must be bool"
            )
        if self.symbol_category_id is not None and (
            type(self.symbol_category_id) is not int
            or self.symbol_category_id <= 0
        ):
            raise CiboCapitalManagementError(
                "cTrader capability symbol_category_id must be positive int/null"
            )
        if self.description is not None and (
            not isinstance(self.description, str) or not self.description
        ):
            raise CiboCapitalManagementError(
                "cTrader capability description must be non-empty string/null"
            )


@dataclass(frozen=True, slots=True)
class CTraderDemoAccountCapabilityObservation:
    account_ref: str
    observed_at: datetime
    account_type: CTraderDemoAccountType
    account_type_field_present: bool
    same_symbol_opposite_positions_supported: bool | None
    symbols: tuple[CTraderDemoCatalogSymbol, ...]
    catalog_sha256: str
    broker_mutation_performed: bool = False
    t16_hedge_instrument_certified: bool = False
    t17_option_structure_certified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.account_ref, str) or not self.account_ref:
            raise CiboCapitalManagementError(
                "cTrader capability account_ref is required"
            )
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "cTrader capability observed_at must be timezone-aware"
            )
        if type(self.account_type) is not CTraderDemoAccountType:
            raise CiboCapitalManagementError(
                "cTrader capability account_type invalid"
            )
        if type(self.account_type_field_present) is not bool:
            raise CiboCapitalManagementError(
                "cTrader capability account-type presence must be bool"
            )
        expected_same_symbol = {
            CTraderDemoAccountType.HEDGED: True,
            CTraderDemoAccountType.NETTED: False,
            CTraderDemoAccountType.SPREAD_BETTING: None,
            CTraderDemoAccountType.UNKNOWN: None,
        }[self.account_type]
        if self.same_symbol_opposite_positions_supported is not expected_same_symbol:
            raise CiboCapitalManagementError(
                "cTrader capability same-symbol account-mode drift"
            )
        if self.account_type_field_present != (
            self.account_type is not CTraderDemoAccountType.UNKNOWN
        ):
            raise CiboCapitalManagementError(
                "cTrader capability account-type evidence drift"
            )
        if not isinstance(self.symbols, tuple):
            raise CiboCapitalManagementError(
                "cTrader capability symbols must be tuple"
            )
        ids = tuple(item.symbol_id for item in self.symbols)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "cTrader capability symbol ids must be unique"
            )
        if tuple(sorted(ids)) != ids:
            raise CiboCapitalManagementError(
                "cTrader capability symbol catalog must be ordered by id"
            )
        _sha(self.catalog_sha256, "catalog_sha256")
        if self.catalog_sha256 != _catalog_sha256(self.symbols):
            raise CiboCapitalManagementError(
                "cTrader capability catalog digest drift"
            )
        if (
            self.broker_mutation_performed
            or self.t16_hedge_instrument_certified
            or self.t17_option_structure_certified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "cTrader capability observation cannot promote CE2I/runtime authority"
            )

    @property
    def enabled_symbol_count(self) -> int:
        return sum(1 for item in self.symbols if item.enabled)

    def fingerprint(self) -> str:
        return _digest(
            {
                **asdict(self),
                "account_type": self.account_type.value,
            }
        )


def collect_ctrader_demo_account_capability(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    observed_at: datetime | None = None,
) -> CTraderDemoAccountCapabilityObservation:
    """Read the actual DEMO account mode and complete active symbol catalog."""

    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CiboCapitalManagementError(str(connected.error))
    account_id = client.account_id
    if type(account_id) is not int or account_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader capability account id must be positive int"
        )

    trader_res = _request(
        client,
        "ProtoOATraderReq",
        {"ctidTraderAccountId": account_id},
        "qore-cibo-account-capability-trader",
    )
    if getattr(trader_res, "ctidTraderAccountId", None) != account_id:
        raise CiboCapitalManagementError(
            "cTrader capability trader response account mismatch"
        )
    trader = getattr(trader_res, "trader", None)
    if trader is None:
        raise CiboCapitalManagementError(
            "cTrader capability trader response missing account"
        )
    account_type_present = _field_present(trader, "accountType")
    native_type = getattr(trader, "accountType", None) if account_type_present else None
    account_type = (
        _ACCOUNT_TYPE_BY_NATIVE.get(native_type, CTraderDemoAccountType.UNKNOWN)
        if type(native_type) is int
        else CTraderDemoAccountType.UNKNOWN
    )
    if account_type_present and account_type is CTraderDemoAccountType.UNKNOWN:
        raise CiboCapitalManagementError(
            "cTrader capability accountType value is unsupported/unknown"
        )

    listed = _request(
        client,
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": account_id,
            "includeArchivedSymbols": False,
        },
        "qore-cibo-account-capability-symbols",
    )
    if getattr(listed, "ctidTraderAccountId", account_id) != account_id:
        raise CiboCapitalManagementError(
            "cTrader capability symbol-list account mismatch"
        )
    raw_symbols = getattr(listed, "symbol", None)
    if raw_symbols is None:
        raise CiboCapitalManagementError(
            "cTrader capability symbol list missing"
        )
    symbols = tuple(
        sorted(
            (_symbol(item) for item in tuple(raw_symbols)),
            key=lambda item: item.symbol_id,
        )
    )
    if not symbols:
        raise CiboCapitalManagementError(
            "cTrader capability symbol catalog cannot be empty"
        )

    same_symbol: bool | None
    if account_type is CTraderDemoAccountType.HEDGED:
        same_symbol = True
    elif account_type is CTraderDemoAccountType.NETTED:
        same_symbol = False
    else:
        same_symbol = None

    return CTraderDemoAccountCapabilityObservation(
        account_ref=str(account_id),
        observed_at=observed_at or datetime.now(UTC),
        account_type=account_type,
        account_type_field_present=account_type_present,
        same_symbol_opposite_positions_supported=same_symbol,
        symbols=symbols,
        catalog_sha256=_catalog_sha256(symbols),
    )


def _symbol(value: object) -> CTraderDemoCatalogSymbol:
    symbol_id = getattr(value, "symbolId", None)
    if type(symbol_id) is not int or symbol_id <= 0:
        raise CiboCapitalManagementError(
            "cTrader capability symbol id invalid"
        )
    name = getattr(value, "symbolName", None)
    if not isinstance(name, str) or not name:
        raise CiboCapitalManagementError(
            "cTrader capability symbol name invalid"
        )
    enabled_raw = getattr(value, "enabled", False)
    if type(enabled_raw) is not bool:
        raise CiboCapitalManagementError(
            "cTrader capability symbol enabled flag invalid"
        )
    category = (
        getattr(value, "symbolCategoryId", None)
        if _field_present(value, "symbolCategoryId")
        else None
    )
    if type(category) is not int:
        category = None
    description = (
        getattr(value, "description", None)
        if _field_present(value, "description")
        else None
    )
    if not isinstance(description, str) or not description:
        description = None
    return CTraderDemoCatalogSymbol(
        symbol_id=symbol_id,
        symbol_name=name,
        enabled=enabled_raw,
        symbol_category_id=category,
        description=description,
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


def _field_present(message: object, name: str) -> bool:
    has_field = getattr(message, "HasField", None)
    if callable(has_field):
        try:
            return bool(has_field(name))
        except (ValueError, KeyError):
            pass
    list_fields = getattr(message, "ListFields", None)
    if callable(list_fields):
        try:
            return any(
                getattr(descriptor, "name", None) == name
                for descriptor, _ in list_fields()
            )
        except (TypeError, ValueError):
            return False
    return hasattr(message, name)


def _catalog_sha256(
    symbols: tuple[CTraderDemoCatalogSymbol, ...],
) -> str:
    return _digest(
        [
            {
                "symbol_id": item.symbol_id,
                "symbol_name": item.symbol_name,
                "enabled": item.enabled,
                "symbol_category_id": item.symbol_category_id,
                "description": item.description,
            }
            for item in symbols
        ]
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
            f"cTrader capability {name} must be canonical SHA-256"
        )
