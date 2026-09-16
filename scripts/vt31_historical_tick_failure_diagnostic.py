"""Sanitized one-window diagnostic for VT-31 consumed historical tick requests.

Research only. It never opens fresh evidence and never prints credentials, account ids,
or raw provider payloads. It exists only to distinguish transport/protocol failures from
historical-retention absence before changing the canonical tick probe.
"""
from __future__ import annotations

import json

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import _connect_and_resolve_market
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

from vt31_historical_tick_probe import _enable_research_tick_messages, _int_env


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
        response = client.request(
            "ProtoOAGetTickDataReq",
            {
                "ctidTraderAccountId": account_id,
                "symbolId": symbol.symbol_id,
                "type": 1,
                "fromTimestamp": opened_ms,
                "toTimestamp": closed_ms,
            },
            client_msg_id="vt31-tick-diag",
            timeout_seconds=10.0,
        )
        if isinstance(response, Failure):
            print(
                json.dumps(
                    {
                        "schema": "qore.vt31.consumed_historical_tick_failure_diagnostic.v1",
                        "research_only": True,
                        "opens_new_holdout": False,
                        "market": market,
                        "provider_symbol": provider_symbol,
                        "status": "failure",
                        "error_type": type(response.error).__name__,
                        "error_message": str(response.error),
                    },
                    sort_keys=True,
                )
            )
            return
        value = response.value
        ticks = getattr(value, "tickData", ())
        print(
            json.dumps(
                {
                    "schema": "qore.vt31.consumed_historical_tick_failure_diagnostic.v1",
                    "research_only": True,
                    "opens_new_holdout": False,
                    "market": market,
                    "provider_symbol": provider_symbol,
                    "status": "success",
                    "tick_count": len(ticks),
                    "has_more": getattr(value, "hasMore", False),
                    "response_type": type(value).__name__,
                },
                sort_keys=True,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
