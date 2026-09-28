"""Provider-bound historical BID/ASK spread evidence for consumed Scalper eras.

The evidence contract is frozen by PR #623 comment 5876110489:
- consumed Validation + Reserved only;
- latest provider-native BID and ASK at or before each entrant ENTRY/EXIT;
- each side requested over [T-60s, T];
- quote age <= 30s;
- no interpolation, synthetic quote, outcome use or Fresh Holdout access.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_10y_m1_clone_v1 import (
    TARGET_SYMBOLS,
    _credentials,
    _selected_symbol,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_PROVIDER_BOUND_HISTORICAL_SPREAD_EVIDENCE_V1"
WINDOW_SECONDS = 60
MAX_QUOTE_AGE_SECONDS = 30
MIN_REQUEST_INTERVAL_SECONDS = 0.25
PRICE_SCALE = Decimal(100_000)
QUOTE_TYPES = (("BID", 1), ("ASK", 2))
PERIOD_SPECS = (
    ("CONSUMED_VALIDATION_2022_2024", "validation", 1034),
    ("CONSUMED_RESERVED_2020_2022", "reserved", 1088),
)


@dataclass(frozen=True, slots=True)
class HistoricalQuote:
    quote_type: str
    observed_at: str
    age_ms: int
    price: str
    source_tick_count: int
    response_has_more: bool
    provider_native: bool = True
    future_quote_used: bool = False
    interpolation_used: bool = False
    synthetic_quote_used: bool = False

    def __post_init__(self) -> None:
        if self.quote_type not in {"BID", "ASK"}:
            raise ValueError("historical quote type must be BID/ASK")
        if self.age_ms < 0 or self.age_ms > MAX_QUOTE_AGE_SECONDS * 1000:
            raise ValueError("historical quote age outside frozen contract")
        if Decimal(self.price) <= 0:
            raise ValueError("historical quote price must be positive")
        if (
            not self.provider_native
            or self.future_quote_used
            or self.interpolation_used
            or self.synthetic_quote_used
        ):
            raise ValueError("provider-bound quote governance violation")


@dataclass(frozen=True, slots=True)
class SpreadEvidenceRow:
    period: str
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    side: str
    entrant_entry_at: str
    event: str
    event_at: str
    structural_risk_price: str
    bid: HistoricalQuote
    ask: HistoricalQuote
    spread_price: str
    spread_over_structural_risk: str
    entrant_identity_only: bool = True
    realized_outcome_read: bool = False
    exit_reason_read: bool = False
    fresh_holdout_touched: bool = False

    def __post_init__(self) -> None:
        if self.event not in {"ENTRY", "EXIT"}:
            raise ValueError("spread evidence event must be ENTRY/EXIT")
        if self.side not in {"LONG", "SHORT"}:
            raise ValueError("spread evidence side must be LONG/SHORT")
        risk = Decimal(self.structural_risk_price)
        spread = Decimal(self.spread_price)
        if risk <= 0:
            raise ValueError("structural risk must be positive")
        if spread < 0:
            raise ValueError("historical spread cannot be negative")
        if Decimal(self.ask.price) < Decimal(self.bid.price):
            raise ValueError("historical ASK cannot be below BID")
        if Decimal(self.spread_over_structural_risk) != spread / risk:
            raise ValueError("spread/risk contract drift")
        if (
            not self.entrant_identity_only
            or self.realized_outcome_read
            or self.exit_reason_read
            or self.fresh_holdout_touched
        ):
            raise ValueError("spread evidence governance violation")


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("spread evidence timestamps must be timezone-aware")
    return parsed.astimezone(UTC)


def _absolute_first_tick(
    ticks: tuple[object, ...],
    *,
    quote_type: str,
    target_at: datetime,
    digits: int,
    has_more: bool,
) -> HistoricalQuote:
    """Decode the newest cTrader tick.

    ProtoOAGetTickDataRes is newest-first. The first tick contains absolute
    timestamp and absolute relative price; later entries are deltas, so no
    later row is needed to select the latest quote <= T.
    """

    if not ticks:
        raise ValueError(f"{quote_type} historical tick window is empty")
    first = ticks[0]
    timestamp = getattr(first, "timestamp", None)
    relative = getattr(first, "tick", None)
    if type(timestamp) is not int or type(relative) is not int:
        raise ValueError("historical tick first row lacks integer fields")
    if timestamp <= 0 or relative <= 0:
        raise ValueError("historical first tick must be absolute positive values")

    observed_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    if observed_at > target_at:
        raise ValueError("historical response used a future quote")
    age_ms = int((target_at - observed_at).total_seconds() * 1000)
    if age_ms > MAX_QUOTE_AGE_SECONDS * 1000:
        raise ValueError(
            f"{quote_type} latest historical quote exceeds max age: {age_ms}ms"
        )
    quant = Decimal(1).scaleb(-digits)
    price = (Decimal(relative) / PRICE_SCALE).quantize(quant)
    return HistoricalQuote(
        quote_type=quote_type,
        observed_at=observed_at.isoformat(),
        age_ms=age_ms,
        price=str(price),
        source_tick_count=len(ticks),
        response_has_more=has_more,
    )


def _request_latest_quote(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    digits: int,
    target_at: datetime,
    quote_name: str,
    quote_type: int,
    request_id: str,
) -> HistoricalQuote:
    start = target_at - timedelta(seconds=WINDOW_SECONDS)
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": int(start.timestamp() * 1000),
            "toTimestamp": int(target_at.timestamp() * 1000),
        },
        client_msg_id=request_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(
            f"historical {quote_name} request failed: "
            f"{type(result.error).__name__}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise RuntimeError("historical tick response account mismatch")
    ticks = tuple(cast(Iterable[object], getattr(result.value, "tickData", ())))
    has_more = getattr(result.value, "hasMore", None)
    if type(has_more) is not bool:
        raise RuntimeError("historical tick response missing hasMore")
    return _absolute_first_tick(
        ticks,
        quote_type=quote_name,
        target_at=target_at,
        digits=digits,
        has_more=has_more,
    )


def _original_period(
    root: Path,
    *,
    expected: int,
) -> tuple[milestone.SimulatedTrade, ...]:
    ledgers = router._load_selected(root, expected=expected)
    rows = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    if len(rows) != expected:
        raise ValueError("spread evidence selected-population count drift")
    return rows


def _symbol_trades(
    root: Path,
    *,
    expected: int,
    symbol: str,
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            (row for row in _original_period(root, expected=expected) if row.symbol == symbol),
            key=lambda row: row.entry_at,
        )
    )


def evidence_symbol(
    symbol: str,
    validation_root: Path,
    reserved_root: Path,
    output: Path,
) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    output.mkdir(parents=True, exist_ok=True)

    roots = {"validation": validation_root, "reserved": reserved_root}
    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    rows: list[SpreadEvidenceRow] = []
    request_count = 0
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"cTrader DEMO authentication failed: {type(ready.error).__name__}"
            )
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)

        for period, slug, expected in PERIOD_SPECS:
            trades = _symbol_trades(
                roots[slug],
                expected=expected,
                symbol=symbol,
            )
            if not trades:
                raise ValueError(f"spread evidence {period} has no {symbol} entrants")

            for trade in trades:
                entry = _aware(trade.entry_at)
                exit_at = _aware(trade.exit_at)
                risk = abs(
                    Decimal(trade.entry_price)
                    - Decimal(trade.original_stop_price)
                )
                if risk <= 0:
                    raise ValueError("entrant structural risk is not positive")

                for event, target_at in (("ENTRY", entry), ("EXIT", exit_at)):
                    quotes: dict[str, HistoricalQuote] = {}
                    for quote_name, quote_type in QUOTE_TYPES:
                        quotes[quote_name] = _request_latest_quote(
                            client,
                            symbol_id=symbol_id,
                            digits=digits,
                            target_at=target_at,
                            quote_name=quote_name,
                            quote_type=quote_type,
                            request_id=(
                                f"capitalizer-spread:{period}:{symbol}:"
                                f"{trade.entry_at}:{event}:{quote_name}"
                            ),
                        )
                        request_count += 1
                        time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
                    bid = quotes["BID"]
                    ask = quotes["ASK"]
                    spread = Decimal(ask.price) - Decimal(bid.price)
                    rows.append(
                        SpreadEvidenceRow(
                            period=period,
                            canonical_symbol=symbol,
                            provider_symbol=provider_symbol,
                            provider_symbol_id=symbol_id,
                            digits=digits,
                            side=trade.side,
                            entrant_entry_at=trade.entry_at,
                            event=event,
                            event_at=target_at.isoformat(),
                            structural_risk_price=str(risk),
                            bid=bid,
                            ask=ask,
                            spread_price=str(spread),
                            spread_over_structural_risk=str(spread / risk),
                        )
                    )
    finally:
        client.close()

    expected_events = sum(
        len(
            _symbol_trades(
                roots[slug],
                expected=expected,
                symbol=symbol,
            )
        )
        * 2
        for _period, slug, expected in PERIOD_SPECS
    )
    if len(rows) != expected_events:
        raise ValueError("spread evidence event coverage drift")

    stem = f"capitalizer-provider-bound-spread-{symbol.lower()}-v1"
    with (output / f"{stem}.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, object] = {
        "identity": IDENTITY,
        "canonical_symbol": symbol,
        "provider_symbol": rows[0].provider_symbol,
        "provider_symbol_id": rows[0].provider_symbol_id,
        "digits": rows[0].digits,
        "consumed_periods": [item[0] for item in PERIOD_SPECS],
        "entrant_count": expected_events // 2,
        "event_count": len(rows),
        "request_count": request_count,
        "entry_coverage": "1",
        "exit_coverage": "1",
        "bid_coverage": "1",
        "ask_coverage": "1",
        "max_quote_age_seconds": MAX_QUOTE_AGE_SECONDS,
        "request_window_seconds": WINDOW_SECONDS,
        "provider_native": True,
        "future_quote_used": False,
        "interpolation_used": False,
        "synthetic_quote_used": False,
        "realized_outcome_read": False,
        "exit_reason_read": False,
        "fresh_holdout_touched": False,
        "commission_evidence_included": False,
        "fill_price_evidence_included": False,
        "slippage_evidence_included": False,
        "latency_evidence_included": False,
        "cost_certification_satisfied": False,
    }
    (output / f"{stem}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_matrix(root: Path) -> dict[str, object]:
    paths = sorted(root.rglob("capitalizer-provider-bound-spread-*-v1-report.json"))
    if len(paths) != len(TARGET_SYMBOLS):
        raise ValueError(
            f"spread matrix requires {len(TARGET_SYMBOLS)} reports, got {len(paths)}"
        )
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    symbols = {str(row["canonical_symbol"]) for row in reports}
    if symbols != set(TARGET_SYMBOLS):
        raise ValueError("spread evidence symbol universe mismatch")

    result: dict[str, object] = {
        "identity": "QORE_CAPITALIZER_PROVIDER_BOUND_HISTORICAL_SPREAD_MATRIX_V1",
        "market_count": len(reports),
        "markets_full_entry_exit_bid_ask_coverage": sum(
            row["entry_coverage"] == "1"
            and row["exit_coverage"] == "1"
            and row["bid_coverage"] == "1"
            and row["ask_coverage"] == "1"
            for row in reports
        ),
        "all_markets_full_coverage": all(
            row["entry_coverage"] == "1"
            and row["exit_coverage"] == "1"
            and row["bid_coverage"] == "1"
            and row["ask_coverage"] == "1"
            for row in reports
        ),
        "provider_native": True,
        "future_quote_used": False,
        "interpolation_used": False,
        "synthetic_quote_used": False,
        "realized_outcome_read": False,
        "fresh_holdout_touched": False,
        "commission_evidence_included": False,
        "fill_price_evidence_included": False,
        "slippage_evidence_included": False,
        "latency_evidence_included": False,
        "cost_certification_satisfied": False,
        "next_phase": (
            "ADD_COMMISSION_FILL_SLIPPAGE_LATENCY_EVIDENCE_THEN_COMPUTE_POST_COST"
            if all(row["entry_coverage"] == "1" and row["exit_coverage"] == "1" for row in reports)
            else "PROVIDER_BOUND_SPREAD_COVERAGE_INCOMPLETE"
        ),
        "markets": sorted(reports, key=lambda row: str(row["canonical_symbol"])),
    }
    output = root / "matrix-output"
    output.mkdir(exist_ok=True)
    (output / "capitalizer-provider-bound-historical-spread-matrix-v1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("symbol", choices=TARGET_SYMBOLS)
    market.add_argument("validation_root", type=Path)
    market.add_argument("reserved_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("root", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report = evidence_symbol(
            args.symbol,
            args.validation_root,
            args.reserved_root,
            args.output,
        )
    else:
        report = build_matrix(args.root)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
