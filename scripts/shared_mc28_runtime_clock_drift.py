"""Real read-only cTrader DEMO runtime clock-drift diagnostic."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from collections.abc import Callable
from typing import Any

from qore.infrastructure.core_stack_v2.runtime_clock_drift_diagnostic import (
    IDENTITY,
    MAX_ABSOLUTE_CLOCK_OFFSET_MS,
    MAX_WALL_MONOTONIC_DIVERGENCE_MS,
    MINIMUM_REAL_SAMPLES,
    TRANSPORT_JITTER_MARGIN_MS,
    CTraderClockReadOnlyMessageClient,
    RuntimeClockReferenceSample,
    assess_runtime_clock,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiPermissionScope,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

PREFERRED_PROVIDER_SYMBOLS = ("EURUSD", "GBPUSD", "XAUUSD")
REFERENCE_RTT_SAMPLE_COUNT = 3
EVENT_WAIT_TIMEOUT_SECONDS = 12.0
MAX_EVENT_ATTEMPTS = 25


class RuntimeClockDiagnosticError(RuntimeError):
    pass


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise RuntimeClockDiagnosticError(
        f"missing required environment input: {name}"
    )


def _elapsed_ms(started: float, ended: float) -> int:
    return max(0, round((ended - started) * 1000))


def _wall_elapsed_ms(started: datetime, ended: datetime) -> int:
    return max(
        0,
        round(
            (
                ended.astimezone(UTC)
                - started.astimezone(UTC)
            ).total_seconds()
            * 1000
        ),
    )


def _symbol_rows(value: object) -> list[tuple[int, str]]:
    native_symbols = getattr(value, "symbol", None)
    if native_symbols is None:
        raise RuntimeClockDiagnosticError(
            "cTrader symbol catalogue missing"
        )
    rows = []
    for item in native_symbols:
        if getattr(item, "enabled", None) is not True:
            continue
        symbol_id = getattr(item, "symbolId", None)
        symbol_name = getattr(item, "symbolName", None)
        if type(symbol_id) is not int or not isinstance(symbol_name, str):
            raise RuntimeClockDiagnosticError(
                "cTrader symbol identity invalid"
            )
        rows.append((symbol_id, symbol_name))
    return rows


def _provider_timestamp(value: object) -> int | None:
    timestamp = getattr(value, "timestamp", None)
    if type(timestamp) is not int or timestamp <= 0:
        return None
    return timestamp


def _timestamped_spot_predicate(
    symbol_id: int,
) -> Callable[[object], bool]:
    def predicate(item: object) -> bool:
        return (
            getattr(item, "symbolId", None) == symbol_id
            and _provider_timestamp(item) is not None
        )

    return predicate


def _newer_spot_predicate(
    symbol_id: int,
    after_timestamp: int,
) -> Callable[[object], bool]:
    def predicate(item: object) -> bool:
        timestamp = _provider_timestamp(item)
        return (
            getattr(item, "symbolId", None) == symbol_id
            and timestamp is not None
            and timestamp > after_timestamp
        )

    return predicate


def run(*, output_path: Path) -> dict[str, Any]:
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
    native = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        required_permission_scope=CTraderOpenApiPermissionScope.TRADE,
    )
    client = CTraderClockReadOnlyMessageClient(native)

    samples: list[RuntimeClockReferenceSample] = []
    rtt_samples_ms: list[int] = []
    provider_symbol = ""
    provider_symbol_id = 0
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeClockDiagnosticError(
                "cTrader DEMO read-only authentication failed"
            )

        rows: list[tuple[int, str]] = []
        for index in range(REFERENCE_RTT_SAMPLE_COUNT):
            wall_before = datetime.now(UTC)
            mono_before = monotonic()
            listed = client.request(
                "ProtoOASymbolsListReq",
                {
                    "ctidTraderAccountId": client.account_id,
                    "includeArchivedSymbols": False,
                },
                client_msg_id=f"shared-a-clock-rtt-{index}",
                timeout_seconds=10.0,
            )
            mono_after = monotonic()
            wall_after = datetime.now(UTC)
            if isinstance(listed, Failure):
                raise RuntimeClockDiagnosticError(
                    "cTrader DEMO clock reference request failed"
                )
            rtt_samples_ms.append(
                _elapsed_ms(mono_before, mono_after)
            )
            if abs(
                _wall_elapsed_ms(wall_before, wall_after)
                - rtt_samples_ms[-1]
            ) > MAX_WALL_MONOTONIC_DIVERGENCE_MS:
                raise RuntimeClockDiagnosticError(
                    "local wall clock moved inconsistently during RTT probe"
                )
            if not rows:
                rows = _symbol_rows(listed.value)

        by_name = {name: symbol_id for symbol_id, name in rows}
        for candidate in PREFERRED_PROVIDER_SYMBOLS:
            if candidate in by_name:
                provider_symbol = candidate
                provider_symbol_id = by_name[candidate]
                break
        if not provider_symbol:
            raise RuntimeClockDiagnosticError(
                "no frozen preferred liquid provider symbol is enabled"
            )

        subscribe_before = monotonic()
        subscribed = client.request(
            "ProtoOASubscribeSpotsReq",
            {
                "ctidTraderAccountId": client.account_id,
                "subscribeToSpotTimestamp": True,
                "symbolId": [provider_symbol_id],
            },
            client_msg_id="shared-a-runtime-clock-spots",
            timeout_seconds=10.0,
        )
        subscribe_after = monotonic()
        if isinstance(subscribed, Failure):
            raise RuntimeClockDiagnosticError(
                "cTrader DEMO spot timestamp subscription failed"
            )
        rtt_samples_ms.append(
            _elapsed_ms(subscribe_before, subscribe_after)
        )
        transport_upper_bound_ms = (
            max(rtt_samples_ms)
            + TRANSPORT_JITTER_MARGIN_MS
        )

        bootstrap = client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=EVENT_WAIT_TIMEOUT_SECONDS,
            predicate=_timestamped_spot_predicate(
                provider_symbol_id
            ),
        )
        if isinstance(bootstrap, Failure):
            raise RuntimeClockDiagnosticError(
                "cTrader DEMO spot timestamp bootstrap unavailable"
            )
        last_timestamp = _provider_timestamp(bootstrap.value)
        if last_timestamp is None:
            raise RuntimeClockDiagnosticError(
                "cTrader bootstrap event omitted timestamp"
            )

        attempts = 0
        while (
            len(samples) < MINIMUM_REAL_SAMPLES
            and attempts < MAX_EVENT_ATTEMPTS
        ):
            attempts += 1
            wall_before = datetime.now(UTC)
            mono_before = monotonic()
            event = client.wait_for_event(
                "ProtoOASpotEvent",
                timeout_seconds=EVENT_WAIT_TIMEOUT_SECONDS,
                predicate=_newer_spot_predicate(
                    provider_symbol_id,
                    last_timestamp,
                ),
            )
            mono_after = monotonic()
            wall_after = datetime.now(UTC)
            if isinstance(event, Failure):
                break
            timestamp = _provider_timestamp(event.value)
            if timestamp is None or timestamp <= last_timestamp:
                continue
            last_timestamp = timestamp
            samples.append(
                RuntimeClockReferenceSample(
                    sample_id=f"{len(samples):03d}",
                    provider_event_at=datetime.fromtimestamp(
                        timestamp / 1000,
                        tz=UTC,
                    ),
                    local_received_at=wall_after,
                    transport_upper_bound_ms=transport_upper_bound_ms,
                    local_wall_elapsed_ms=_wall_elapsed_ms(
                        wall_before,
                        wall_after,
                    ),
                    local_monotonic_elapsed_ms=_elapsed_ms(
                        mono_before,
                        mono_after,
                    ),
                )
            )
    finally:
        client.close()

    assessment = assess_runtime_clock(tuple(samples))
    payload: dict[str, Any] = {
        "identity": IDENTITY,
        "status": assessment.status.value,
        "provider_environment": "CTRADER_DEMO",
        "provider_symbol": provider_symbol,
        "provider_symbol_id": provider_symbol_id,
        "sample_count": assessment.sample_count,
        "minimum_real_samples": MINIMUM_REAL_SAMPLES,
        "maximum_absolute_clock_offset_ms": (
            MAX_ABSOLUTE_CLOCK_OFFSET_MS
        ),
        "maximum_wall_monotonic_divergence_ms": (
            MAX_WALL_MONOTONIC_DIVERGENCE_MS
        ),
        "transport_jitter_margin_ms": TRANSPORT_JITTER_MARGIN_MS,
        "reference_rtt_samples_ms": rtt_samples_ms,
        "transport_upper_bound_ms": (
            None
            if not rtt_samples_ms
            else max(rtt_samples_ms) + TRANSPORT_JITTER_MARGIN_MS
        ),
        "offset_lower_bound_ms": assessment.offset_lower_bound_ms,
        "offset_upper_bound_ms": assessment.offset_upper_bound_ms,
        "max_wall_monotonic_divergence_observed_ms": (
            assessment.max_wall_monotonic_divergence_ms
        ),
        "reason_codes": list(assessment.reason_codes),
        "samples": [
            {
                "sample_id": item.sample_id,
                "provider_event_at": item.provider_event_at.isoformat(),
                "local_received_at": item.local_received_at.isoformat(),
                "transport_upper_bound_ms": (
                    item.transport_upper_bound_ms
                ),
                "provider_minus_local_receive_ms": (
                    item.provider_minus_local_receive_ms
                ),
                "offset_lower_bound_ms": item.offset_lower_bound_ms,
                "offset_upper_bound_ms": item.offset_upper_bound_ms,
                "wall_monotonic_divergence_ms": (
                    item.wall_monotonic_divergence_ms
                ),
            }
            for item in samples
        ],
        "first_technical_spot_event_discarded": True,
        "subscribe_to_spot_timestamp": True,
        "read_only_message_firewall": True,
        "broker_mutation": False,
        "restart_authority": False,
        "order_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "protected_holdout_opened": False,
        "productive_authority": False,
        "clock_drift_completed_and_proven": assessment.diagnostic_pass,
        "mc28_completed_and_proven": False,
        "remaining_mc28_diagnostics": (
            ["EXECUTION_QUALITY_DETERIORATION"]
            if assessment.diagnostic_pass
            else [
                "CLOCK_DRIFT",
                "EXECUTION_QUALITY_DETERIORATION",
            ]
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(output_path=args.output)
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "status": payload["status"],
                "sample_count": payload["sample_count"],
                "offset_lower_bound_ms": (
                    payload["offset_lower_bound_ms"]
                ),
                "offset_upper_bound_ms": (
                    payload["offset_upper_bound_ms"]
                ),
                "remaining_mc28_diagnostics": (
                    payload["remaining_mc28_diagnostics"]
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
