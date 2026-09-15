"""R5-only runtime adapter that admits cTrader historical tick messages."""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_probe import (
    collect_r5_classic_tick_evidence,
)


def _admit_historical_tick_messages(client: SpotwareCTraderOpenApiClient) -> None:
    """Admit only the official read-only historical tick request/response pair."""

    messages = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
    for name in ("ProtoOAGetTickDataReq", "ProtoOAGetTickDataRes"):
        message_type = getattr(messages, name, None)
        if not isinstance(message_type, type):
            raise CTraderDemoLabProbeError(
                f"official cTrader SDK is missing required historical tick message {name}"
            )
        client._bindings.messages[name] = message_type  # noqa: SLF001


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

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
    _admit_historical_tick_messages(client)
    try:
        payload = collect_r5_classic_tick_evidence(
            client,
            symbol_name=args.symbol,
            software_sha=args.software_sha,
        )
    finally:
        client.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
