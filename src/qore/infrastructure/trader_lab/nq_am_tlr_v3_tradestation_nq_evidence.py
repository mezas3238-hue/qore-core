"""Read-only TradeStation M1 acquisition foundation for exact NQ futures evidence.

Research infrastructure only. The collector never calls brokerage/order endpoints.
Exact TradeStation contract symbols and roll boundaries must be supplied through a
provider-verified manifest; QORE does not guess them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

IDENTITY = "QORE_NQ_AM_TLR_V3_EXACT_NQ_EVIDENCE_V1"
PROVIDER = "tradestation-api-v3"
API_BASE = "https://api.tradestation.com/v3"
TOKEN_URL = "https://signin.tradestation.com/oauth/token"
CHUNK_DAYS = 20
HTTP_TIMEOUT_SECONDS = 45.0


class ExactNqEvidenceError(RuntimeError):
    """Raised when exact-NQ evidence cannot be acquired or validated safely."""


@dataclass(frozen=True, slots=True)
class ContractSlice:
    symbol: str
    opened_at: datetime
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class ContractManifest:
    provider: str
    root: str
    opened_at: datetime
    closed_at: datetime
    slices: tuple[ContractSlice, ...]


@dataclass(frozen=True, slots=True)
class NqM1Bar:
    provider_symbol: str
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    total_volume: int | None
    open_interest: int | None
    is_realtime: bool


def _aware_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExactNqEvidenceError(f"{field} is not a valid ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExactNqEvidenceError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ExactNqEvidenceError(f"{field} must be numeric")
    try:
        return Decimal(str(value))
    except InvalidOperation as error:
        raise ExactNqEvidenceError(f"{field} must be numeric") from error


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ExactNqEvidenceError("integer market-data field cannot be bool")
    try:
        return int(str(value))
    except ValueError as error:
        raise ExactNqEvidenceError("invalid integer market-data field") from error


def parse_contract_manifest(raw: str) -> ContractManifest:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ExactNqEvidenceError("contract manifest is invalid JSON") from error
    if not isinstance(payload, dict):
        raise ExactNqEvidenceError("contract manifest root must be an object")
    provider = payload.get("provider")
    root = payload.get("root")
    if provider != PROVIDER:
        raise ExactNqEvidenceError("contract manifest provider mismatch")
    if root != "NQ":
        raise ExactNqEvidenceError("contract manifest root must be NQ")
    opened_at = _aware_utc(str(payload.get("opened_at")), "opened_at")
    closed_at = _aware_utc(str(payload.get("closed_at")), "closed_at")
    if opened_at >= closed_at:
        raise ExactNqEvidenceError("manifest interval must be positive")
    raw_slices = payload.get("slices")
    if not isinstance(raw_slices, list) or not raw_slices:
        raise ExactNqEvidenceError("manifest requires at least one contract slice")

    slices: list[ContractSlice] = []
    for index, item in enumerate(raw_slices):
        if not isinstance(item, dict):
            raise ExactNqEvidenceError(f"slice {index} must be an object")
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ExactNqEvidenceError(f"slice {index} requires provider symbol")
        start = _aware_utc(str(item.get("opened_at")), f"slice {index} opened_at")
        end = _aware_utc(str(item.get("closed_at")), f"slice {index} closed_at")
        if start >= end:
            raise ExactNqEvidenceError(f"slice {index} interval must be positive")
        slices.append(ContractSlice(symbol.strip(), start, end))

    ordered = tuple(sorted(slices, key=lambda item: item.opened_at))
    if tuple(slices) != ordered:
        raise ExactNqEvidenceError("contract slices must already be chronological")
    if ordered[0].opened_at != opened_at or ordered[-1].closed_at != closed_at:
        raise ExactNqEvidenceError("contract slices must cover exact manifest bounds")
    for left, right in zip(ordered, ordered[1:], strict=False):
        if left.closed_at != right.opened_at:
            raise ExactNqEvidenceError("contract slices must be gap-free/non-overlapping")
    return ContractManifest(PROVIDER, "NQ", opened_at, closed_at, ordered)


def contract_manifest_sha256(manifest: ContractManifest) -> str:
    payload = {
        "provider": manifest.provider,
        "root": manifest.root,
        "opened_at": manifest.opened_at.isoformat(),
        "closed_at": manifest.closed_at.isoformat(),
        "slices": [
            {
                "symbol": item.symbol,
                "opened_at": item.opened_at.isoformat(),
                "closed_at": item.closed_at.isoformat(),
            }
            for item in manifest.slices
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def chunk_grid(
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[tuple[datetime, datetime], ...]:
    if opened_at.tzinfo is None or closed_at.tzinfo is None:
        raise ExactNqEvidenceError("chunk bounds must be timezone-aware")
    if opened_at >= closed_at:
        raise ExactNqEvidenceError("chunk interval must be positive")
    result: list[tuple[datetime, datetime]] = []
    cursor = opened_at
    while cursor < closed_at:
        end = min(cursor + timedelta(days=CHUNK_DAYS), closed_at)
        result.append((cursor, end))
        cursor = end
    return tuple(result)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def barchart_url(
    symbol: str,
    opened_at: datetime,
    closed_at: datetime,
    *,
    api_base: str = API_BASE,
) -> str:
    if not symbol.strip():
        raise ExactNqEvidenceError("provider symbol is required")
    params = urlencode(
        {
            "interval": "1",
            "unit": "Minute",
            "firstdate": _iso_z(opened_at),
            "lastdate": _iso_z(closed_at),
        }
    )
    return f"{api_base}/marketdata/barcharts/{quote(symbol, safe='')}?{params}"


def refresh_access_token(
    *,
    client_id: str,
    refresh_token: str,
    client_secret: str | None,
) -> str:
    if not client_id or not refresh_token:
        raise ExactNqEvidenceError("TradeStation client id and refresh token required")
    fields = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        fields["client_secret"] = client_secret
    request = Request(
        TOKEN_URL,
        data=urlencode(fields).encode(),
        headers={"content-type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            decoded = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ExactNqEvidenceError("TradeStation token refresh failed") from error
    if not isinstance(decoded, dict):
        raise ExactNqEvidenceError("TradeStation token response must be an object")
    token = decoded.get("access_token")
    if not isinstance(token, str) or not token:
        raise ExactNqEvidenceError("TradeStation token response missing access_token")
    return token


def _get_json(url: str, access_token: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            decoded = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ExactNqEvidenceError("TradeStation market-data request failed") from error
    if not isinstance(decoded, dict):
        raise ExactNqEvidenceError("TradeStation market-data response must be an object")
    return cast(dict[str, Any], decoded)


def parse_barchart_response(
    payload: dict[str, Any],
    *,
    symbol: str,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[NqM1Bar, ...]:
    raw_bars = payload.get("Bars")
    if not isinstance(raw_bars, list):
        error = payload.get("Error")
        message = payload.get("Message")
        raise ExactNqEvidenceError(
            f"TradeStation response missing Bars: {error!r} {message!r}"
        )
    result: list[NqM1Bar] = []
    for index, raw in enumerate(raw_bars):
        if not isinstance(raw, dict):
            raise ExactNqEvidenceError(f"bar {index} must be an object")
        timestamp = _aware_utc(str(raw.get("TimeStamp")), "TimeStamp")
        if not opened_at <= timestamp < closed_at:
            continue
        is_realtime = raw.get("IsRealtime")
        if is_realtime is not False:
            raise ExactNqEvidenceError("historical evidence contains real-time bar")
        bar = NqM1Bar(
            provider_symbol=symbol,
            opened_at=timestamp,
            open=_decimal(raw.get("Open"), "Open"),
            high=_decimal(raw.get("High"), "High"),
            low=_decimal(raw.get("Low"), "Low"),
            close=_decimal(raw.get("Close"), "Close"),
            total_volume=_optional_int(raw.get("TotalVolume")),
            open_interest=_optional_int(raw.get("OpenInterest")),
            is_realtime=False,
        )
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            raise ExactNqEvidenceError("historical bar has invalid OHLC geometry")
        result.append(bar)
    ordered = tuple(sorted(result, key=lambda item: item.opened_at))
    if tuple(result) != ordered:
        raise ExactNqEvidenceError("provider bars are not chronological")
    return ordered


def collect_exact_nq_m1(
    manifest: ContractManifest,
    *,
    access_token: str,
    api_base: str = API_BASE,
) -> tuple[NqM1Bar, ...]:
    retained: dict[datetime, NqM1Bar] = {}
    for contract in manifest.slices:
        for start, end in chunk_grid(contract.opened_at, contract.closed_at):
            payload = _get_json(
                barchart_url(contract.symbol, start, end, api_base=api_base),
                access_token,
            )
            for bar in parse_barchart_response(
                payload,
                symbol=contract.symbol,
                opened_at=start,
                closed_at=end,
            ):
                previous = retained.get(bar.opened_at)
                if previous is not None and previous != bar:
                    raise ExactNqEvidenceError(
                        "contradictory bars at contract splice/timestamp"
                    )
                retained[bar.opened_at] = bar
    bars = tuple(retained[key] for key in sorted(retained))
    if not bars:
        raise ExactNqEvidenceError("TradeStation returned no exact NQ M1 evidence")
    return bars


def evidence_payload(
    manifest: ContractManifest,
    bars: tuple[NqM1Bar, ...],
) -> dict[str, Any]:
    symbols = tuple(dict.fromkeys(item.provider_symbol for item in bars))
    return {
        "schema": "qore.nq_am_tlr_v3.tradestation_exact_nq_m1.v1",
        "identity": IDENTITY,
        "provider": PROVIDER,
        "source_instrument": "NQ_FUTURES",
        "source_instrument_equivalence_target": "NQ_FUTURES",
        "resolution": "M1",
        "manifest_sha256": contract_manifest_sha256(manifest),
        "requested_opened_at": manifest.opened_at.isoformat(),
        "requested_closed_at": manifest.closed_at.isoformat(),
        "provider_contract_symbols": list(symbols),
        "bar_count": len(bars),
        "first_observed_at": bars[0].opened_at.isoformat(),
        "last_observed_at": bars[-1].opened_at.isoformat(),
        "contract_slices": [
            {
                "symbol": item.symbol,
                "opened_at": item.opened_at.isoformat(),
                "closed_at": item.closed_at.isoformat(),
            }
            for item in manifest.slices
        ],
        "bars": [
            {
                **asdict(item),
                "opened_at": item.opened_at.isoformat(),
                "open": str(item.open),
                "high": str(item.high),
                "low": str(item.low),
                "close": str(item.close),
            }
            for item in bars
        ],
        "read_only": True,
        "brokerage_endpoint_used": False,
        "order_endpoint_used": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ExactNqEvidenceError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    manifest = parse_contract_manifest(args.manifest.read_text())
    token = refresh_access_token(
        client_id=_required_env("QORE_TRADESTATION_CLIENT_ID"),
        refresh_token=_required_env("QORE_TRADESTATION_REFRESH_TOKEN"),
        client_secret=os.environ.get("QORE_TRADESTATION_CLIENT_SECRET") or None,
    )
    bars = collect_exact_nq_m1(manifest, access_token=token)
    payload = evidence_payload(manifest, bars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "provider": PROVIDER,
                "bar_count": len(bars),
                "contracts": payload["provider_contract_symbols"],
                "manifest_sha256": payload["manifest_sha256"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
