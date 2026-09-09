"""Fail-closed cTrader DEMO economic identity binding for index research.

The existing QORE cTrader runtime admits symbol-list and exact symbol-detail
messages.  This module therefore certifies a provider index target only when
three independent facts agree inside that admitted read-only boundary:

* one enabled provider alias resolves uniquely;
* the provider-authored description identifies the requested economic target;
* exact symbol details return the same provider symbol id and trading metadata.

A loose alias match is never enough.  If the provider description is absent or
ambiguous the index is VALIDATION_BLOCKED upstream rather than guessed.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

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

_SCHEMA = "qore.ctrader_demo.index_economic_identity.v1"
_BINDING_BASIS = "enabled-alias+provider-target-description+exact-symbol-details-v1"
_ALIASES: dict[str, frozenset[str]] = {
    "US30": frozenset({"US30", "USA30", "DJ30", "DOW30", "WS30", "US30USD"}),
    "NAS100": frozenset(
        {
            "NAS100",
            "NASDAQ100",
            "US100",
            "USTEC",
            "USTECH",
            "USTEC100",
            "NAS100USD",
            "US100USD",
        }
    ),
    "SP500": frozenset(
        {"SP500", "SPX500", "US500", "USA500", "US500USD", "SPX500USD"}
    ),
}
_DESCRIPTION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "US30": (
        re.compile(r"\bDOW\s+JONES\b.*\b(?:30|INDUSTRIAL\s+AVERAGE)\b", re.I),
        re.compile(r"\bDJIA\b", re.I),
        re.compile(r"\bWALL\s+STREET\b.*\b30\b", re.I),
    ),
    "NAS100": (
        re.compile(r"\bNASDAQ\b.*\b100\b", re.I),
        re.compile(r"\bUS\s*TECH(?:NOLOGY)?\b.*\b100\b", re.I),
    ),
    "SP500": (
        re.compile(r"\bS\s*&?\s*P\b.*\b500\b", re.I),
        re.compile(r"\bSTANDARD\b.*\bPOOR(?:S|'S)?\b.*\b500\b", re.I),
    ),
}


def _normalize_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _positive_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise CTraderDemoLabProbeError(f"{field_name} must be a positive int")
    return value


def _nonnegative_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise CTraderDemoLabProbeError(
            f"{field_name} must be a non-negative int"
        )
    return value


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CTraderDemoLabProbeError(f"{field_name} must be non-empty text")
    return value.strip()


def _description_binds_target(target: str, description: str) -> bool:
    return any(
        pattern.search(description) is not None
        for pattern in _DESCRIPTION_PATTERNS[target]
    )


@dataclass(frozen=True, slots=True)
class CTraderDemoIndexEconomicIdentity:
    """One exact provider symbol bound to one requested index target."""

    economic_target: str
    provider_symbol: CTraderDemoLabSymbolEvidence
    provider_description: str
    provider_symbol_category_id: int
    account_fingerprint: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.economic_target not in _ALIASES:
            raise CTraderDemoLabProbeError("unsupported index target")
        if type(self.provider_symbol) is not CTraderDemoLabSymbolEvidence:
            raise CTraderDemoLabProbeError(
                "provider_symbol must use exact symbol evidence"
            )
        self.provider_symbol.__post_init__()
        description = _text(
            self.provider_description,
            field_name="provider_description",
        )
        _positive_int(
            self.provider_symbol_category_id,
            field_name="provider_symbol_category_id",
        )
        if re.fullmatch(r"[0-9a-f]{64}", self.account_fingerprint) is None:
            raise CTraderDemoLabProbeError(
                "account_fingerprint must be sha256 hex"
            )
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise CTraderDemoLabProbeError("checked_at must be timezone-aware")

        aliases = {
            _normalize_symbol(item) for item in _ALIASES[self.economic_target]
        }
        if _normalize_symbol(self.provider_symbol.symbol_name) not in aliases:
            raise CTraderDemoLabProbeError(
                "provider alias does not bind requested economic target"
            )
        if not _description_binds_target(self.economic_target, description):
            raise CTraderDemoLabProbeError(
                "provider description does not prove requested economic target"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "account_is_live": False,
            "economic_target": self.economic_target,
            "economic_identity_certified": True,
            "binding_basis": _BINDING_BASIS,
            "provider_symbol": self.provider_symbol.payload(),
            "provider_description": self.provider_description,
            "provider_symbol_category_id": self.provider_symbol_category_id,
            "category_semantics_resolved": False,
            "category_semantics_used_for_certification": False,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
        }

    def sanitized_json(self) -> str:
        return json.dumps(
            self.payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _request(
    client: CTraderOpenApiMessageClientBoundary,
    message: str,
    payload: dict[str, object],
    *,
    message_id: str,
    timeout_seconds: float,
) -> object:
    response = client.request(
        message,
        payload,
        client_msg_id=message_id,
        timeout_seconds=timeout_seconds,
    )
    if isinstance(response, Failure):
        raise CTraderDemoLabProbeError(f"cTrader DEMO {message} read failed")
    return response.value


def certify_index_economic_identity(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    economic_target: str,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> CTraderDemoIndexEconomicIdentity:
    """Resolve and prove one exact enabled provider index identity."""
    if economic_target not in _ALIASES:
        raise CTraderDemoLabProbeError("unsupported index target")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    if type(timeout_seconds) is not float or timeout_seconds <= 0:
        raise CTraderDemoLabProbeError("timeout_seconds must be positive float")
    if not client.is_ready:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise CTraderDemoLabProbeError("cTrader DEMO authentication failed")

    account_id = client.account_id
    listed = _request(
        client,
        "ProtoOASymbolsListReq",
        {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
        message_id=f"qore-index-symbol-list-{economic_target.lower()}",
        timeout_seconds=timeout_seconds,
    )
    if getattr(listed, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError("cTrader symbol-list account mismatch")

    aliases = {_normalize_symbol(item) for item in _ALIASES[economic_target]}
    candidates: list[object] = []
    for item in tuple(getattr(listed, "symbol", ())):
        name = getattr(item, "symbolName", None)
        if (
            getattr(item, "enabled", None) is True
            and type(name) is str
            and _normalize_symbol(name) in aliases
        ):
            candidates.append(item)
    if len(candidates) != 1:
        raise CTraderDemoLabProbeError(
            "index target requires exactly one enabled alias candidate; "
            f"observed={len(candidates)}"
        )

    light = candidates[0]
    symbol_id = _positive_int(
        getattr(light, "symbolId", None), field_name="symbolId"
    )
    symbol_name = _text(
        getattr(light, "symbolName", None), field_name="symbolName"
    )
    description = _text(
        getattr(light, "description", None), field_name="description"
    )
    category_id = _positive_int(
        getattr(light, "symbolCategoryId", None),
        field_name="symbolCategoryId",
    )
    if not _description_binds_target(economic_target, description):
        raise CTraderDemoLabProbeError(
            "provider description does not prove requested economic target"
        )

    details_res = _request(
        client,
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        message_id=f"qore-index-details-{economic_target.lower()}",
        timeout_seconds=timeout_seconds,
    )
    if getattr(details_res, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError("cTrader symbol-details account mismatch")
    details = tuple(getattr(details_res, "symbol", ()))
    if len(details) != 1:
        raise CTraderDemoLabProbeError(
            "exact index symbol details are absent or ambiguous"
        )
    detail = details[0]
    if _positive_int(
        getattr(detail, "symbolId", None), field_name="detail symbolId"
    ) != symbol_id:
        raise CTraderDemoLabProbeError("index detail symbol id mismatch")

    symbol = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=symbol_name,
        digits=_nonnegative_int(
            getattr(detail, "digits", None), field_name="digits"
        ),
        min_volume_units=_positive_int(
            getattr(detail, "minVolume", None), field_name="minVolume"
        ),
        max_volume_units=_positive_int(
            getattr(detail, "maxVolume", None), field_name="maxVolume"
        ),
        step_volume_units=_positive_int(
            getattr(detail, "stepVolume", None), field_name="stepVolume"
        ),
    )
    return CTraderDemoIndexEconomicIdentity(
        economic_target=economic_target,
        provider_symbol=symbol,
        provider_description=description,
        provider_symbol_category_id=category_id,
        account_fingerprint=compute_ctrader_demo_lab_account_fingerprint(account_id),
        checked_at=checked_at.astimezone(UTC),
    )


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(
        f"missing required environment input: {name}"
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in _ALIASES:
        print(
            "usage: python -m "
            "qore.infrastructure.ctrader_demo_lab_index_identity "
            "{US30|NAS100|SP500}",
            file=sys.stderr,
        )
        return 2
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID"
            )
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        identity = certify_index_economic_identity(
            client,
            economic_target=args[0],
            checked_at=datetime.now(UTC),
        )
        print(identity.sanitized_json())
        return 0
    except CTraderDemoLabProbeError as error:
        print(
            f"index economic identity validation blocked: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
