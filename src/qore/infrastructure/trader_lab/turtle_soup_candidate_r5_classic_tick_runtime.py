"""R5-only runtime adapter for cTrader historical tick evidence."""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _native_int,
    _normalized_price,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import turtle_soup_candidate_r5_classic_tick_probe as tick_probe


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


def _decode_tick_page_with_signed_deltas(
    native_ticks: tuple[object, ...], *, digits: int
) -> tuple[tick_probe.TurtleSoupR5HistoricalTick, ...]:
    """Decode cTrader newest-first ticks without assuming delta sign convention.

    The official response contract says the first timestamp is absolute and all
    subsequent values are the difference between the previous and current tick.
    Observed provider responses encode that difference as a signed negative
    delta, while older QORE fixtures used a positive magnitude. Both encodings
    represent the same elapsed time, so chronology is reconstructed by moving
    backward by the delta magnitude. A zero delta deliberately preserves equal
    timestamps for fail-closed causal handling downstream.
    """

    decoded: list[tick_probe.TurtleSoupR5HistoricalTick] = []
    previous_ms: int | None = None
    for response_order, native in enumerate(native_ticks):
        raw_timestamp = _native_int(native, "timestamp")
        raw_tick = _native_int(native, "tick")
        if response_order == 0:
            if raw_timestamp < 0:
                raise CTraderDemoLabProbeError(
                    "first historical tick timestamp is negative"
                )
            timestamp_ms = raw_timestamp
        else:
            if previous_ms is None:  # pragma: no cover - guarded by loop state
                raise CTraderDemoLabProbeError("lost historical tick timestamp state")
            timestamp_ms = previous_ms - abs(raw_timestamp)
            if timestamp_ms < 0 or timestamp_ms > previous_ms:
                raise CTraderDemoLabProbeError(
                    "historical tick delta violates newest-first chronology"
                )
        decoded.append(
            tick_probe.TurtleSoupR5HistoricalTick(
                timestamp_ms=timestamp_ms,
                price=_normalized_price(raw_tick, digits=digits),
                response_order=response_order,
            )
        )
        previous_ms = timestamp_ms
    return tuple(decoded)


def _install_r5_tick_decoder() -> None:
    """Install the protocol-faithful R5 decoder without widening Core runtime."""

    setattr(tick_probe, "_decode_tick_page", _decode_tick_page_with_signed_deltas)


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
    _install_r5_tick_decoder()
    try:
        payload = tick_probe.collect_r5_classic_tick_evidence(
            cast(tick_probe.CTraderOpenApiMessageClientBoundary, client),
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
