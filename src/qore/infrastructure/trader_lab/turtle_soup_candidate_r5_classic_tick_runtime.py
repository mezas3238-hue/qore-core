"""R5-only runtime adapter for cTrader historical tick evidence."""

from __future__ import annotations

import argparse
import json
from importlib import import_module
from pathlib import Path

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
    """Decode the provider's newest-first cumulative tick delta stream.

    cTrader transmits the first timestamp and price as absolute values. Every
    subsequent timestamp and price is a signed delta from the immediately
    preceding tick. Because the response is newest-first, timestamp deltas must
    be non-positive. Zero timestamp deltas are preserved so downstream causal
    resolution can fail closed when two price events have no observable order.
    """

    decoded: list[tick_probe.TurtleSoupR5HistoricalTick] = []
    previous_ms: int | None = None
    previous_tick_units: int | None = None
    for response_order, native in enumerate(native_ticks):
        raw_timestamp = _native_int(native, "timestamp")
        raw_tick = _native_int(native, "tick")
        if response_order == 0:
            if raw_timestamp < 0:
                raise CTraderDemoLabProbeError(
                    "first historical tick timestamp is negative"
                )
            if raw_tick <= 0:
                raise CTraderDemoLabProbeError(
                    "first historical tick price must be absolute and positive"
                )
            timestamp_ms = raw_timestamp
            tick_units = raw_tick
        else:
            if previous_ms is None or previous_tick_units is None:  # pragma: no cover
                raise CTraderDemoLabProbeError("lost historical tick decoder state")
            if raw_timestamp > 0:
                raise CTraderDemoLabProbeError(
                    "historical timestamp delta violates newest-first chronology"
                )
            timestamp_ms = previous_ms + raw_timestamp
            tick_units = previous_tick_units + raw_tick
            if timestamp_ms < 0 or timestamp_ms > previous_ms:
                raise CTraderDemoLabProbeError(
                    "historical tick timestamp reconstruction is invalid"
                )
            if tick_units <= 0:
                raise CTraderDemoLabProbeError(
                    "historical tick price reconstruction is non-positive"
                )
        decoded.append(
            tick_probe.TurtleSoupR5HistoricalTick(
                timestamp_ms=timestamp_ms,
                price=_normalized_price(tick_units, digits=digits),
                response_order=response_order,
            )
        )
        previous_ms = timestamp_ms
        previous_tick_units = tick_units
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
