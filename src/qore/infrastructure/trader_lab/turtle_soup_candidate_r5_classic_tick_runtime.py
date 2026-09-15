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
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_wave1b_targets import (
    frozen_wave1b_tick_target_manifest,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r5_classic_tick_wave2_targets import (
    frozen_wave2_tick_target_manifest,
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


def _decode_tick_page_with_signed_deltas(
    native_ticks: tuple[object, ...], *, digits: int
) -> tuple[tick_probe.TurtleSoupR5HistoricalTick, ...]:
    """Decode the provider's newest-first cumulative tick delta stream."""

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


def _install_target_wave(target_wave: str) -> None:
    """Select only a frozen R5 acquisition wave before collection starts."""

    if target_wave == "wave1":
        return
    if target_wave == "wave1b":
        manifest_factory = frozen_wave1b_tick_target_manifest
    elif target_wave == "wave2":
        manifest_factory = frozen_wave2_tick_target_manifest
    else:
        raise CTraderDemoLabProbeError("unsupported R5 target wave")
    setattr(tick_probe, "frozen_tick_target_manifest", manifest_factory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--target-wave", choices=("wave1", "wave1b", "wave2"), default="wave1"
    )
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
    _install_target_wave(args.target_wave)
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
