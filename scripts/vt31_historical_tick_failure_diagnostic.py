"""Sanitized one-window diagnostic for VT-31 consumed historical tick requests.

Research only. It never opens fresh evidence and never prints credentials, account ids,
or raw provider prices. It isolates request-id, BID/ASK and delta-decode behavior before
changing the canonical historical tick probe.
"""
from __future__ import annotations

import json
import time

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import _connect_and_resolve_market
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

from vt31_historical_tick_probe import (
    _decode_page,
    _enable_research_tick_messages,
    _int_env,
)


def _request_case(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    quote_value: int,
    quote_name: str,
    opened_ms: int,
    closed_ms: int,
    client_msg_id: str,
) -> dict[str, object]:
    response = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": account_id,
            "symbolId": symbol_id,
            "type": quote_value,
            "fromTimestamp": opened_ms,
            "toTimestamp": closed_ms,
        },
        client_msg_id=client_msg_id,
        timeout_seconds=10.0,
    )
    if isinstance(response, Failure):
        return {
            "status": "failure",
            "quote": quote_name,
            "client_msg_id_length": len(client_msg_id),
            "error_type": type(response.error).__name__,
            "error_message": str(response.error),
        }
    value = response.value
    native_ticks = getattr(value, "tickData", ())
    try:
        decoded = _decode_page(native_ticks)
    except Exception as error:
        return {
            "status": "decode_failure",
            "quote": quote_name,
            "client_msg_id_length": len(client_msg_id),
            "response_type": type(value).__name__,
            "tick_count": len(native_ticks),
            "has_more": getattr(value, "hasMore", False),
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    return {
        "status": "success",
        "quote": quote_name,
        "client_msg_id_length": len(client_msg_id),
        "response_type": type(value).__name__,
        "tick_count": len(native_ticks),
        "decoded_count": len(decoded),
        "has_more": getattr(value, "hasMore", False),
        "first_timestamp_ms": decoded[0].timestamp_ms if decoded else None,
        "last_timestamp_ms": decoded[-1].timestamp_ms if decoded else None,
        "within_requested_window": all(
            opened_ms <= tick.timestamp_ms <= closed_ms for tick in decoded
        ),
    }


def main() -> None:
    market = _required_env("QORE_DEMO_LAB_SYMBOL")
    opened_ms = _int_env("QORE_TICK_WINDOW_OPEN_MS")
    closed_ms = _int_env("QORE_TICK_WINDOW_CLOSE_MS")
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
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
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        _enable_research_tick_messages(client)
        account_id, _fingerprint, symbol, provider_symbol = _connect_and_resolve_market(
            client, market=market, timeout_seconds=10.0
        )
        cases: list[dict[str, object]] = []
        cases.append(
            _request_case(
                client,
                account_id=account_id,
                symbol_id=symbol.symbol_id,
                quote_value=1,
                quote_name="BID",
                opened_ms=opened_ms,
                closed_ms=closed_ms,
                client_msg_id="vt31-tick-diag",
            )
        )
        time.sleep(0.25)
        cases.append(
            _request_case(
                client,
                account_id=account_id,
                symbol_id=symbol.symbol_id,
                quote_value=1,
                quote_name="BID",
                opened_ms=opened_ms,
                closed_ms=closed_ms,
                client_msg_id=(
                    f"vt31-ticks:{symbol.symbol_id}:BID:{opened_ms}:{closed_ms}:1"
                ),
            )
        )
        time.sleep(0.25)
        cases.append(
            _request_case(
                client,
                account_id=account_id,
                symbol_id=symbol.symbol_id,
                quote_value=2,
                quote_name="ASK",
                opened_ms=opened_ms,
                closed_ms=closed_ms,
                client_msg_id=(
                    f"vt31-ticks:{symbol.symbol_id}:ASK:{opened_ms}:{closed_ms}:1"
                ),
            )
        )
        print(
            json.dumps(
                {
                    "schema": "qore.vt31.consumed_historical_tick_failure_diagnostic.v2",
                    "research_only": True,
                    "opens_new_holdout": False,
                    "market": market,
                    "provider_symbol": provider_symbol,
                    "cases": cases,
                },
                sort_keys=True,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
