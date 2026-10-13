"""Pure offline categorizer of existing QORE cTrader Failure objects (NO I/O).

No broker source requests, no logs of raw errors, no account data, no orders.
Old historical V1/V2/V3 failures remain UNKNOWN; no retroactive attribution.
"""
from __future__ import annotations

import re
from typing import Any

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError,
    CTraderOpenApiDependencyError,
    CTraderOpenApiProtocolError,
)
from qore.kernel.result import Failure

CATEGORIES = frozenset({
    "LOCAL_REQUEST_NOT_WHITELISTED",
    "LOCAL_SDK_REQ_UNADMITTED",
    "LOCAL_PROTO_FIELD_INVALID",
    "LOCAL_RESPONSE_DECODE_FAILURE",
    "BROKER_PROTOCOL_REJECTED_CODE_ONLY",
    "TRANSPORT_TIMEOUT",
    "TRANSPORT_OR_SESSION_FAILURE",
    "UNKNOWN_FAILURE",
    "NOT_A_FAILURE",
})
PROVIDER = re.compile(r"cTrader request rejected: [A-Z0-9_]{1,64}\Z")


def classify_failure(result: Any) -> str:
    """Return ONLY fixed labels; never return an exception or provider text."""
    if not isinstance(result, Failure):
        return "NOT_A_FAILURE"
    error = result.error
    if isinstance(error, CTraderOpenApiDependencyError):
        return "LOCAL_SDK_REQ_UNADMITTED"
    if isinstance(error, CTraderOpenApiConnectionError):
        message = str(error)
        return (
            "TRANSPORT_TIMEOUT"
            if message in {"cTrader request timed out", "cTrader DEMO TLS connect timed out"}
            else "TRANSPORT_OR_SESSION_FAILURE"
        )
    if isinstance(error, CTraderOpenApiProtocolError):
        message = str(error)
        if message == "HISTORY_ONLY_MESSAGE_NOT_ALLOWED":
            return "LOCAL_REQUEST_NOT_WHITELISTED"
        if message == "cTrader request message is not admitted by this runtime":
            return "LOCAL_SDK_REQ_UNADMITTED"
        if message.startswith("invalid cTrader request field: "):
            return "LOCAL_PROTO_FIELD_INVALID"
        if message == "cTrader response could not be decoded":
            return "LOCAL_RESPONSE_DECODE_FAILURE"
        if PROVIDER.fullmatch(message) is not None:
            return "BROKER_PROTOCOL_REJECTED_CODE_ONLY"
    return "UNKNOWN_FAILURE"
