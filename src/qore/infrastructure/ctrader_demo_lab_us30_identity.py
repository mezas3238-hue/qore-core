"""Exact fail-closed cTrader DEMO identity binding for the US30 closeout.

This module exists for the provider descriptor observed by the isolated Trader Lab
closeout.  It deliberately does *not* teach the generic index resolver that an
arbitrary ``IA`` token means ``Industrial Average``.  Certification requires the
single enabled provider symbol to be exactly ``US30`` and the provider-authored
description, after whitespace/punctuation normalization, to be exactly
``USA DOW JONES IA INDEX``.  Exact symbol details must then bind to the same id.

The boundary is read-only and DEMO-only.  It grants no execution authority.
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

_SCHEMA = "qore.ctrader_demo.us30_exact_provider_identity.v1"
_BINDING_BASIS = "exact-us30-symbol+exact-provider-description+exact-symbol-details-v1"
_EXPECTED_SYMBOL = "US30"
_EXPECTED_DESCRIPTION = "USA DOW JONES IA INDEX"


def _normalize_description(value: str) -> str:
    return " ".join(re.findall(r"[A-Z0-9]+", value.upper()))


def exact_us30_provider_descriptor_matches(
    symbol_name: object,
    description: object,
) -> bool:
    """Return true only for the observed, independently identified provider pair."""
    return (
        type(symbol_name) is str
        and symbol_name.strip().upper() == _EXPECTED_SYMBOL
        and type(description) is str
        and _normalize_description(description) == _EXPECTED_DESCRIPTION
    )


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


@dataclass(frozen=True, slots=True)
class CTraderDemoUs30ExactIdentity:
    """One provider US30 symbol proven by the exact observed provider descriptor."""

    provider_symbol: CTraderDemoLabSymbolEvidence
    provider_description: str
    provider_symbol_category_id: int
    account_fingerprint: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if type(self.provider_symbol) is not CTraderDemoLabSymbolEvidence:
            raise CTraderDemoLabProbeError(
                "provider_symbol must use exact symbol evidence"
            )
        self.provider_symbol.__post_init__()
        if not exact_us30_provider_descriptor_matches(
            self.provider_symbol.symbol_name,
            self.provider_description,
        ):
            raise CTraderDemoLabProbeError(
                "provider symbol/description does not prove exact US30 identity"
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

    def payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "account_is_live": False,
            "economic_target": "US30",
            "economic_identity_certified": True,
            "execution_authority": False,
            "binding_basis": _BINDING_BASIS,
            "provider_symbol": self.provider_symbol.payload(),
            "provider_description": self.provider_description,
            "provider_symbol_category_id": self.provider_symbol_category_id,
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


def certify_exact_us30_identity(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    checked_at: datetime,
    timeout_seconds: float = 15.0,
) -> CTraderDemoUs30ExactIdentity:
    """Resolve exactly one enabled US30 with the exact provider descriptor."""
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
        message_id="qore-us30-exact-symbol-list",
        timeout_seconds=timeout_seconds,
    )
    if getattr(listed, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError("cTrader symbol-list account mismatch")

    candidates: list[object] = []
    for item in tuple(getattr(listed, "symbol", ())):
        if (
            getattr(item, "enabled", None) is True
            and exact_us30_provider_descriptor_matches(
                getattr(item, "symbolName", None),
                getattr(item, "description", None),
            )
        ):
            candidates.append(item)
    if len(candidates) != 1:
        raise CTraderDemoLabProbeError(
            "US30 requires exactly one enabled exact provider candidate; "
            f"observed={len(candidates)}"
        )

    light = candidates[0]
    symbol_id = _positive_int(
        getattr(light, "symbolId", None), field_name="symbolId"
    )
    description = getattr(light, "description", None)
    if type(description) is not str:
        raise CTraderDemoLabProbeError("provider description must be text")
    category_id = _positive_int(
        getattr(light, "symbolCategoryId", None),
        field_name="symbolCategoryId",
    )

    details_res = _request(
        client,
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
        message_id="qore-us30-exact-symbol-details",
        timeout_seconds=timeout_seconds,
    )
    if getattr(details_res, "ctidTraderAccountId", None) != account_id:
        raise CTraderDemoLabProbeError("cTrader symbol-details account mismatch")
    details = tuple(getattr(details_res, "symbol", ()))
    if len(details) != 1:
        raise CTraderDemoLabProbeError(
            "exact US30 symbol details are absent or ambiguous"
        )
    detail = details[0]
    if _positive_int(
        getattr(detail, "symbolId", None), field_name="detail symbolId"
    ) != symbol_id:
        raise CTraderDemoLabProbeError("US30 detail symbol id mismatch")

    symbol = CTraderDemoLabSymbolEvidence(
        symbol_id=symbol_id,
        symbol_name=_EXPECTED_SYMBOL,
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
    return CTraderDemoUs30ExactIdentity(
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
    if args:
        print(
            "usage: python -m qore.infrastructure.ctrader_demo_lab_us30_identity",
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
        identity = certify_exact_us30_identity(
            client,
            checked_at=datetime.now(UTC),
        )
        print(identity.sanitized_json())
        return 0
    except CTraderDemoLabProbeError as error:
        print(
            f"US30 exact economic identity validation blocked: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
