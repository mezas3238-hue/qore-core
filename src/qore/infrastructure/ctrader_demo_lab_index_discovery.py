"""Read-only discovery of the three index targets used by Trader Lab.

This module authenticates against the existing cTrader DEMO boundary, reads the
provider's enabled symbol catalog, and resolves exactly one provider symbol for
each requested economic target: S&P 500, US30/Dow 30, and Nasdaq 100.

Resolution is intentionally conservative and versioned. A provider symbol-name
match is retained as discovery evidence; it is not a claim of universal
economic-identity certification. The module never submits, amends, or cancels
an order.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.ctrader_demo.index_symbol_discovery.v1"
_SYMBOL_SYNTAX = re.compile(r"[A-Z0-9][A-Z0-9._/-]{1,31}")
_BINDING_BASIS = "enabled-provider-symbol-name-alias-v1"

_INDEX_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "SP500",
        (
            "SP500",
            "SPX500",
            "US500",
            "USA500",
            "US500USD",
            "SPX500USD",
        ),
    ),
    (
        "US30",
        (
            "US30",
            "USA30",
            "DJ30",
            "DOW30",
            "WS30",
            "US30USD",
        ),
    ),
    (
        "NAS100",
        (
            "NAS100",
            "NASDAQ100",
            "US100",
            "USTEC",
            "USTECH",
            "USTEC100",
            "NAS100USD",
            "US100USD",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class CTraderDemoIndexSymbolTarget:
    """One exact enabled provider symbol mapped to a requested index target."""

    economic_target: str
    symbol: CTraderDemoLabSymbolEvidence
    binding_basis: str = _BINDING_BASIS

    def __post_init__(self) -> None:
        if self.economic_target not in {item[0] for item in _INDEX_ALIASES}:
            raise CTraderDemoLabProbeError("unknown index economic target")
        if type(self.symbol) is not CTraderDemoLabSymbolEvidence:
            raise CTraderDemoLabProbeError(
                "index target symbol must be exact symbol evidence"
            )
        self.symbol.__post_init__()
        if self.binding_basis != _BINDING_BASIS:
            raise CTraderDemoLabProbeError("unsupported index binding basis")

    def payload(self) -> dict[str, object]:
        return {
            "economic_target": self.economic_target,
            "provider_symbol": self.symbol.payload(),
            "binding_basis": self.binding_basis,
            "economic_identity_certified": False,
        }


@dataclass(frozen=True, slots=True)
class CTraderDemoIndexDiscovery:
    """Sanitized read-only discovery evidence for the requested index targets."""

    account_fingerprint: str
    checked_at: datetime
    targets: tuple[CTraderDemoIndexSymbolTarget, ...]

    def __post_init__(self) -> None:
        if (
            type(self.account_fingerprint) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.account_fingerprint) is None
        ):
            raise CTraderDemoLabProbeError(
                "account_fingerprint must be sha256 hex"
            )
        if (
            type(self.checked_at) is not datetime
            or self.checked_at.tzinfo is None
            or self.checked_at.utcoffset() is None
        ):
            raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
        if type(self.targets) is not tuple or len(self.targets) != len(
            _INDEX_ALIASES
        ):
            raise CTraderDemoLabProbeError(
                "index discovery requires exactly three targets"
            )
        if any(
            type(item) is not CTraderDemoIndexSymbolTarget
            for item in self.targets
        ):
            raise CTraderDemoLabProbeError(
                "index targets must use exact target evidence"
            )
        expected = tuple(item[0] for item in _INDEX_ALIASES)
        observed = tuple(item.economic_target for item in self.targets)
        if observed != expected:
            raise CTraderDemoLabProbeError(
                "index targets must use canonical target order"
            )
        symbol_ids = tuple(item.symbol.symbol_id for item in self.targets)
        symbol_names = tuple(item.symbol.symbol_name for item in self.targets)
        if len(set(symbol_ids)) != len(symbol_ids) or len(
            set(symbol_names)
        ) != len(symbol_names):
            raise CTraderDemoLabProbeError(
                "index targets must bind distinct provider symbols"
            )

    def sanitized_payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "account_is_live": False,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "target_count": len(self.targets),
            "targets": [item.payload() for item in self.targets],
            "limitation": (
                "provider symbol-name alias binding is discovery evidence only; "
                "it is not universal economic-identity certification"
            ),
        }

    def sanitized_json(self) -> str:
        return json.dumps(
            self.sanitized_payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(
        f"missing required environment input: {name}"
    )


def _normalized_symbol_name(value: object) -> str:
    if type(value) is not str or _SYMBOL_SYNTAX.fullmatch(value) is None:
        raise CTraderDemoLabProbeError(
            "cTrader enabled symbol name is invalid"
        )
    return re.sub(r"[^A-Z0-9]", "", value)


def _positive_native_int(value: object, name: str) -> int:
    result = getattr(value, name, None)
    if type(result) is not int or result <= 0:
        raise CTraderDemoLabProbeError(
            f"cTrader {name} must be a positive int"
        )
    return result


def resolve_index_light_symbols(
    native_symbols: tuple[object, ...],
) -> tuple[tuple[str, int, str], ...]:
    """Resolve one enabled light symbol per target and reject ambiguity."""

    if type(native_symbols) is not tuple or not native_symbols:
        raise CTraderDemoLabProbeError(
            "cTrader DEMO symbol list must be non-empty"
        )
    enabled: list[tuple[int, str, str]] = []
    for item in native_symbols:
        if getattr(item, "enabled", None) is not True:
            continue
        symbol_id = _positive_native_int(item, "symbolId")
        symbol_name_value = getattr(item, "symbolName", None)
        normalized = _normalized_symbol_name(symbol_name_value)
        if type(symbol_name_value) is not str:
            raise CTraderDemoLabProbeError(
                "cTrader enabled symbol name must be str"
            )
        enabled.append((symbol_id, symbol_name_value, normalized))

    resolved: list[tuple[str, int, str]] = []
    for target, aliases in _INDEX_ALIASES:
        normalized_aliases = {
            re.sub(r"[^A-Z0-9]", "", item) for item in aliases
        }
        candidates = [
            (symbol_id, symbol_name)
            for symbol_id, symbol_name, normalized in enabled
            if normalized in normalized_aliases
        ]
        if len(candidates) != 1:
            candidate_names = ",".join(
                sorted(item[1] for item in candidates)
            )
            raise CTraderDemoLabProbeError(
                f"index target {target} requires exactly one enabled alias "
                f"match; observed={len(candidates)} "
                f"candidates={candidate_names or 'none'}"
            )
        symbol_id, symbol_name = candidates[0]
        resolved.append((target, symbol_id, symbol_name))

    ids = tuple(item[1] for item in resolved)
    names = tuple(item[2] for item in resolved)
    if len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise CTraderDemoLabProbeError(
            "index targets resolved to duplicate provider symbols"
        )
    return tuple(resolved)


def discover_ctrader_demo_index_symbols(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> CTraderDemoIndexDiscovery:
    """Read exact provider metadata for all three requested index targets."""

    if (
        type(checked_at) is not datetime
        or checked_at.tzinfo is None
        or checked_at.utcoffset() is None
    ):
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    if type(timeout_seconds) is not float or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError(
            "timeout_seconds must be positive float"
        )
    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CTraderDemoLabProbeError(
                "cTrader DEMO authentication failed: "
                f"{type(connected.error).__name__}"
            )

    account_id = client.account_id
    listed = client.request(
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id="qore-index-lab-symbol-list",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(listed, Failure):
        raise CTraderDemoLabProbeError(
            "cTrader DEMO index symbol-list read failed"
        )
    if getattr(listed.value, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError(
            "cTrader DEMO index symbol-list account mismatch"
        )
    native_symbols_value = getattr(listed.value, "symbol", None)
    if native_symbols_value is None:
        raise CTraderDemoLabProbeError(
            "cTrader DEMO symbol list is missing"
        )
    resolved = resolve_index_light_symbols(
        cast(tuple[object, ...], tuple(native_symbols_value))
    )

    ids = [item[1] for item in resolved]
    details = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": ids},
        client_msg_id="qore-index-lab-symbol-details",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(details, Failure):
        raise CTraderDemoLabProbeError(
            "cTrader DEMO index symbol-details read failed"
        )
    if getattr(details.value, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError(
            "cTrader DEMO index symbol-details account mismatch"
        )
    native_details_value = getattr(details.value, "symbol", None)
    if native_details_value is None:
        raise CTraderDemoLabProbeError(
            "cTrader DEMO index symbol details are missing"
        )
    detail_by_id = {
        _positive_native_int(item, "symbolId"): item
        for item in cast(tuple[object, ...], tuple(native_details_value))
    }

    targets: list[CTraderDemoIndexSymbolTarget] = []
    for target, symbol_id, symbol_name in resolved:
        detail = detail_by_id.get(symbol_id)
        if detail is None:
            raise CTraderDemoLabProbeError(
                "cTrader DEMO exact index details are absent"
            )
        if getattr(detail, "enabled", True) is False:
            raise CTraderDemoLabProbeError(
                "cTrader DEMO index details are disabled"
            )
        symbol = CTraderDemoLabSymbolEvidence(
            symbol_id=symbol_id,
            symbol_name=symbol_name,
            digits=_positive_native_int(detail, "digits"),
            min_volume_units=_positive_native_int(detail, "minVolume"),
            max_volume_units=_positive_native_int(detail, "maxVolume"),
            step_volume_units=_positive_native_int(detail, "stepVolume"),
        )
        targets.append(
            CTraderDemoIndexSymbolTarget(
                economic_target=target,
                symbol=symbol,
            )
        )

    return CTraderDemoIndexDiscovery(
        account_fingerprint=compute_ctrader_demo_lab_account_fingerprint(
            account_id
        ),
        checked_at=checked_at.astimezone(UTC),
        targets=tuple(targets),
    )


def main() -> None:
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        discovery = discover_ctrader_demo_index_symbols(
            client,
            checked_at=datetime.now(UTC),
        )
        print(discovery.sanitized_json())
    finally:
        client.close()


if __name__ == "__main__":
    main()
