"""Read-only native-M15 execution-path evidence for Turtle Soup candidate R1."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _collect_period_window,
    _connect_and_resolve_symbol,
    _required_env,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiMessageClientBoundary,
    SpotwareCTraderOpenApiClient,
)

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.m15_execution_evidence.v1"
_NATIVE_M15_PERIOD = 7
_M15_SECONDS = 900
_MIN_LOOKBACK_DAYS = 730
_MAX_LOOKBACK_DAYS = 1095
_REQUIRED_COVERAGE_DAYS = 730
_CHUNK_DAYS = 14
_RECENT_BOUNDARY_TOLERANCE_DAYS = 10


@dataclass(frozen=True, slots=True)
class TurtleSoupR1M15Evidence:
    account_fingerprint: str
    symbol_name: str
    symbol_digits: int
    checked_at: datetime
    requested_opened_at: datetime
    bars: tuple[CTraderDemoLabClosedTrendbar, ...]
    software_sha: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", self.account_fingerprint) is None:
            raise CTraderDemoLabProbeError("account fingerprint must be SHA-256")
        if re.fullmatch(r"[A-Z0-9][A-Z0-9]{1,31}", self.symbol_name) is None:
            raise CTraderDemoLabProbeError("symbol name must use canonical uppercase syntax")
        if type(self.symbol_digits) is not int or self.symbol_digits < 0:
            raise CTraderDemoLabProbeError("symbol_digits must be non-negative int")
        if re.fullmatch(r"[0-9a-f]{40}", self.software_sha) is None:
            raise CTraderDemoLabProbeError("software_sha must be exact Git SHA")
        if type(self.bars) is not tuple or not self.bars:
            raise CTraderDemoLabProbeError("Turtle Soup M15 evidence requires bars")
        if any(item.period != "M15" for item in self.bars):
            raise CTraderDemoLabProbeError("Turtle Soup execution evidence must be M15")
        if tuple(sorted(self.bars, key=lambda item: item.opened_at)) != self.bars:
            raise CTraderDemoLabProbeError("Turtle Soup M15 bars must be chronological")
        if len({item.opened_at for item in self.bars}) != len(self.bars):
            raise CTraderDemoLabProbeError("Turtle Soup M15 bars must be unique")
        first = self.bars[0].opened_at
        last = self.bars[-1].closed_at
        if last - first < timedelta(days=_REQUIRED_COVERAGE_DAYS):
            raise CTraderDemoLabProbeError(
                "Turtle Soup M15 evidence requires at least 730 calendar days of span"
            )
        if last < self.checked_at - timedelta(days=_RECENT_BOUNDARY_TOLERANCE_DAYS):
            raise CTraderDemoLabProbeError("Turtle Soup M15 evidence is stale")
        if any(item.closed_at > self.checked_at for item in self.bars):
            raise CTraderDemoLabProbeError("Turtle Soup M15 evidence must be fully closed")

    def evidence_digest(self) -> str:
        encoded = json.dumps(
            [item.payload() for item in self.bars],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def payload(self) -> dict[str, object]:
        first = self.bars[0].opened_at
        last = self.bars[-1].closed_at
        return {
            "schema": _SCHEMA,
            "environment": "development-market-data",
            "read_only": True,
            "research_only": True,
            "fresh_oos_consumed": False,
            "research_identity": "turtle-soup-candidate-r1",
            "symbol": self.symbol_name,
            "symbol_digits": self.symbol_digits,
            "period": "M15",
            "native_period_value": _NATIVE_M15_PERIOD,
            "account_fingerprint": self.account_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "requested_opened_at": self.requested_opened_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "required_coverage_days": _REQUIRED_COVERAGE_DAYS,
            "bar_count": len(self.bars),
            "first_opened_at": first.astimezone(UTC).isoformat(timespec="microseconds"),
            "last_closed_at": last.astimezone(UTC).isoformat(timespec="microseconds"),
            "span_seconds": int((last - first).total_seconds()),
            "software_sha": self.software_sha,
            "evidence_digest_sha256": self.evidence_digest(),
            "bars": [item.payload() for item in self.bars],
        }


def collect_turtle_soup_r1_m15_evidence(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    symbol_name: str,
    requested_opened_at: datetime,
    checked_at: datetime,
    software_sha: str,
    timeout_seconds: float = 15.0,
) -> TurtleSoupR1M15Evidence:
    if requested_opened_at.tzinfo is None or requested_opened_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("requested_opened_at must be timezone-aware")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise CTraderDemoLabProbeError("checked_at must be timezone-aware")
    opened = requested_opened_at.astimezone(UTC)
    checked = checked_at.astimezone(UTC)
    if opened >= checked:
        raise CTraderDemoLabProbeError("requested_opened_at must predate checked_at")
    account_id, account_fingerprint, symbol = _connect_and_resolve_symbol(
        client,
        symbol_name=symbol_name,
        timeout_seconds=timeout_seconds,
    )
    retained: dict[datetime, CTraderDemoLabClosedTrendbar] = {}
    cursor = opened
    window_index = 0
    while cursor < checked:
        window_end = min(cursor + timedelta(days=_CHUNK_DAYS), checked)
        window = _collect_period_window(
            client,
            account_id=account_id,
            symbol=symbol,
            period_name="M15",
            native_period=_NATIVE_M15_PERIOD,
            seconds=_M15_SECONDS,
            opened_at=cursor,
            checked_at=window_end,
            window_index=window_index,
            timeout_seconds=timeout_seconds,
        )
        for bar in window:
            existing = retained.get(bar.opened_at)
            if existing is not None and existing != bar:
                raise CTraderDemoLabProbeError(
                    "cTrader Turtle Soup M15 windows contradict on same bar"
                )
            retained[bar.opened_at] = bar
        cursor = window_end
        window_index += 1
    return TurtleSoupR1M15Evidence(
        account_fingerprint=account_fingerprint,
        symbol_name=symbol.symbol_name,
        symbol_digits=symbol.digits,
        checked_at=checked,
        requested_opened_at=opened,
        bars=tuple(retained[key] for key in sorted(retained)),
        software_sha=software_sha,
    )


def main() -> None:
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
    symbol_name = _required_env("QORE_TURTLE_SOUP_SYMBOL", "QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    lookback_days = int(os.environ.get("QORE_TURTLE_SOUP_LOOKBACK_DAYS", "1095"))
    if not _MIN_LOOKBACK_DAYS <= lookback_days <= _MAX_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError(
            "Turtle Soup lookback days must be between 730 and 1095"
        )
    checked_at = datetime.now(UTC)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_turtle_soup_r1_m15_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=checked_at - timedelta(days=lookback_days),
            checked_at=checked_at,
            software_sha=software_sha,
        )
        print(
            json.dumps(
                evidence.payload(),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
