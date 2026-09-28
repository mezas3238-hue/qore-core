"""Provider-native pre-entry BID/ASK microstructure state for V41.

Research-only information frontier. Features use only historical tick messages
strictly at or before entry. No outcomes, exits, MAE/MFE, symbol/date identity,
or previously falsified V11/V38/V40 representation blocks are admitted.
"""

from __future__ import annotations

import argparse
import json
import math
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

IDENTITY = "QORE_CAPITALIZER_PREENTRY_PROVIDER_QUOTE_MICROSTRUCTURE_V41"
WINDOW_SECONDS = 60
MAX_QUOTE_AGE_SECONDS = 30
MIN_REQUEST_INTERVAL_SECONDS = 0.25
PRICE_SCALE = Decimal(100_000)
QUOTE_TYPES = (("BID", 1), ("ASK", 2))
PERIOD_SPECS = (
    ("DEVELOPMENT_2024_2026", "development", 948),
    ("CONSUMED_VALIDATION_2022_2024", "validation", 1034),
    ("CONSUMED_RESERVED_2020_2022", "reserved", 1088),
)

FEATURE_NAMES = (
    "bid_log1p_update_count",
    "bid_latest_age_over_30s",
    "bid_directional_net_displacement_r",
    "bid_path_length_r",
    "bid_path_efficiency",
    "bid_increment_reversal_rate",
    "bid_max_intertick_gap_over_60s",
    "ask_log1p_update_count",
    "ask_latest_age_over_30s",
    "ask_directional_net_displacement_r",
    "ask_path_length_r",
    "ask_path_efficiency",
    "ask_increment_reversal_rate",
    "ask_max_intertick_gap_over_60s",
    "latest_spread_r",
    "update_count_imbalance",
    "latest_quote_age_difference_over_30s",
    "directional_spread_change_r",
)


@dataclass(frozen=True, slots=True)
class DecodedTick:
    observed_at: datetime
    price: Decimal


@dataclass(frozen=True, slots=True)
class ProviderQuoteMicrostructureState:
    symbol: str
    side: str
    entry_at: str
    structural_risk_price: str
    feature_names: tuple[str, ...]
    vector: tuple[str, ...]
    feature_count: int
    bid_tick_count: int
    ask_tick_count: int
    bid_latest_at: str
    ask_latest_at: str
    bid_has_more: bool
    ask_has_more: bool
    provider_native: bool = True
    feature_timestamp_le_entry: bool = True
    future_quote_used: bool = False
    interpolation_used: bool = False
    synthetic_quote_used: bool = False
    outcome_used: bool = False
    exit_used: bool = False
    mae_mfe_used: bool = False
    symbol_identity_in_vector: bool = False
    date_identity_in_vector: bool = False

    def __post_init__(self) -> None:
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("V41 feature-name contract drift")
        if len(self.vector) != len(FEATURE_NAMES):
            raise ValueError("V41 vector dimension drift")
        if self.feature_count != len(FEATURE_NAMES):
            raise ValueError("V41 feature_count mismatch")
        if self.bid_tick_count < 2 or self.ask_tick_count < 2:
            raise ValueError("V41 requires at least two BID and ASK ticks")
        if self.bid_has_more or self.ask_has_more:
            raise ValueError("V41 requires complete 60s tick responses")
        if (
            not self.provider_native
            or not self.feature_timestamp_le_entry
            or self.future_quote_used
            or self.interpolation_used
            or self.synthetic_quote_used
            or self.outcome_used
            or self.exit_used
            or self.mae_mfe_used
            or self.symbol_identity_in_vector
            or self.date_identity_in_vector
        ):
            raise ValueError("V41 causal/governance invariant violated")


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V41 timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _sign(value: Decimal) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _reversal_rate(increments: tuple[Decimal, ...]) -> Decimal:
    directions = tuple(_sign(value) for value in increments if value != 0)
    if len(directions) < 2:
        return Decimal("0")
    reversals = sum(
        left != right
        for left, right in zip(
            directions[:-1],
            directions[1:],
            strict=True,
        )
    )
    return Decimal(reversals) / Decimal(len(directions) - 1)


def decode_tick_stream(
    ticks: tuple[object, ...],
    *,
    target_at: datetime,
    digits: int,
    quote_name: str,
    has_more: bool,
) -> tuple[DecodedTick, ...]:
    """Decode cTrader newest-first compressed historical ticks.

    The first tick has absolute timestamp/relative price. Subsequent rows carry
    deltas from the previous tick for both timestamp and price.
    """

    if has_more:
        raise ValueError("V41 60s provider response is truncated")
    if len(ticks) < 2:
        raise ValueError(f"V41 {quote_name} requires at least two ticks")

    current_timestamp: int | None = None
    current_relative: int | None = None
    newest_first: list[DecodedTick] = []
    quant = Decimal(1).scaleb(-digits)
    window_start = target_at - timedelta(seconds=WINDOW_SECONDS)

    for index, raw in enumerate(ticks):
        timestamp = getattr(raw, "timestamp", None)
        relative = getattr(raw, "tick", None)
        if type(timestamp) is not int or type(relative) is not int:
            raise ValueError("V41 historical tick lacks integer fields")
        if index == 0:
            if timestamp <= 0 or relative <= 0:
                raise ValueError("V41 first historical tick must be absolute")
            current_timestamp = timestamp
            current_relative = relative
        else:
            if current_timestamp is None or current_relative is None:
                raise AssertionError("V41 internal decoder state missing")
            current_timestamp += timestamp
            current_relative += relative

        if current_timestamp <= 0 or current_relative <= 0:
            raise ValueError("V41 decoded tick became non-positive")
        observed_at = datetime.fromtimestamp(current_timestamp / 1000, tz=UTC)
        if observed_at > target_at:
            raise ValueError("V41 attempted to use future quote")
        if observed_at < window_start:
            raise ValueError("V41 decoded tick escaped requested 60s window")
        price = (Decimal(current_relative) / PRICE_SCALE).quantize(quant)
        newest_first.append(DecodedTick(observed_at=observed_at, price=price))

    for newer, older in zip(
        newest_first[:-1],
        newest_first[1:],
        strict=True,
    ):
        if older.observed_at > newer.observed_at:
            raise ValueError("V41 provider ticks are not newest-first")

    latest = newest_first[0]
    latest_age = target_at - latest.observed_at
    if latest_age.total_seconds() < 0:
        raise ValueError("V41 latest provider tick is future")
    if latest_age > timedelta(seconds=MAX_QUOTE_AGE_SECONDS):
        raise ValueError(
            f"V41 {quote_name} latest quote exceeds 30s age contract"
        )

    return tuple(reversed(newest_first))


def _stream_features(
    stream: tuple[DecodedTick, ...],
    *,
    target_at: datetime,
    directional_sign: Decimal,
    risk: Decimal,
) -> tuple[Decimal, ...]:
    prices = tuple(row.price for row in stream)
    increments = tuple(
        right - left
        for left, right in zip(prices[:-1], prices[1:], strict=True)
    )
    net = prices[-1] - prices[0]
    path_length = sum((abs(value) for value in increments), Decimal("0"))
    efficiency = (
        Decimal("0")
        if path_length == 0
        else abs(net) / path_length
    )
    gaps = tuple(
        (right.observed_at - left.observed_at).total_seconds()
        for left, right in zip(stream[:-1], stream[1:], strict=True)
    )
    if any(value < 0 for value in gaps):
        raise ValueError("V41 decoded stream is not chronological")
    latest_age = Decimal(
        str((target_at - stream[-1].observed_at).total_seconds())
    )
    return (
        Decimal(str(math.log1p(len(stream)))),
        latest_age / Decimal(MAX_QUOTE_AGE_SECONDS),
        directional_sign * net / risk,
        path_length / risk,
        efficiency,
        _reversal_rate(increments),
        Decimal(str(max(gaps, default=0.0))) / Decimal(WINDOW_SECONDS),
    )


def build_state(
    *,
    symbol: str,
    side: str,
    entry_at: datetime,
    structural_risk_price: Decimal,
    bid_ticks: tuple[object, ...],
    ask_ticks: tuple[object, ...],
    digits: int,
    bid_has_more: bool,
    ask_has_more: bool,
) -> ProviderQuoteMicrostructureState:
    if entry_at.tzinfo is None or entry_at.utcoffset() is None:
        raise ValueError("V41 entry timestamp must be timezone-aware")
    if structural_risk_price <= 0:
        raise ValueError("V41 structural risk must be positive")
    if side == "LONG":
        directional_sign = Decimal("1")
    elif side == "SHORT":
        directional_sign = Decimal("-1")
    else:
        raise ValueError("V41 side must be LONG/SHORT")

    bid = decode_tick_stream(
        bid_ticks,
        target_at=entry_at,
        digits=digits,
        quote_name="BID",
        has_more=bid_has_more,
    )
    ask = decode_tick_stream(
        ask_ticks,
        target_at=entry_at,
        digits=digits,
        quote_name="ASK",
        has_more=ask_has_more,
    )

    values = [
        *_stream_features(
            bid,
            target_at=entry_at,
            directional_sign=directional_sign,
            risk=structural_risk_price,
        ),
        *_stream_features(
            ask,
            target_at=entry_at,
            directional_sign=directional_sign,
            risk=structural_risk_price,
        ),
    ]
    latest_spread = ask[-1].price - bid[-1].price
    if latest_spread < 0:
        raise ValueError("V41 latest historical spread is crossed")
    count_imbalance = Decimal(len(bid) - len(ask)) / Decimal(
        len(bid) + len(ask)
    )
    bid_age = Decimal(
        str((entry_at - bid[-1].observed_at).total_seconds())
    )
    ask_age = Decimal(
        str((entry_at - ask[-1].observed_at).total_seconds())
    )
    oldest_endpoint_spread = ask[0].price - bid[0].price
    spread_change = latest_spread - oldest_endpoint_spread
    values.extend(
        (
            latest_spread / structural_risk_price,
            count_imbalance,
            (bid_age - ask_age) / Decimal(MAX_QUOTE_AGE_SECONDS),
            directional_sign * spread_change / structural_risk_price,
        )
    )
    if len(values) != len(FEATURE_NAMES):
        raise ValueError("V41 internal feature dimension drift")
    if any(not value.is_finite() for value in values):
        raise ValueError("V41 feature vector contains non-finite value")

    return ProviderQuoteMicrostructureState(
        symbol=symbol,
        side=side,
        entry_at=entry_at.astimezone(UTC).isoformat(),
        structural_risk_price=str(structural_risk_price),
        feature_names=FEATURE_NAMES,
        vector=tuple(str(value) for value in values),
        feature_count=len(FEATURE_NAMES),
        bid_tick_count=len(bid),
        ask_tick_count=len(ask),
        bid_latest_at=bid[-1].observed_at.isoformat(),
        ask_latest_at=ask[-1].observed_at.isoformat(),
        bid_has_more=bid_has_more,
        ask_has_more=ask_has_more,
    )


def from_json_dict(payload: dict[str, object]) -> ProviderQuoteMicrostructureState:
    normalized = dict(payload)
    for field in ("feature_names", "vector"):
        value = normalized.get(field)
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"V41 {field} JSON field must be a sequence")
        if any(not isinstance(item, str) for item in value):
            raise ValueError(f"V41 {field} JSON items must be strings")
        normalized[field] = tuple(value)
    return ProviderQuoteMicrostructureState(**normalized)  # type: ignore[arg-type]


def _request_ticks(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    target_at: datetime,
    quote_name: str,
    quote_type: int,
    request_id: str,
) -> tuple[tuple[object, ...], bool]:
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
            f"V41 {quote_name} request failed: {type(result.error).__name__}"
        )
    if getattr(result.value, "ctidTraderAccountId", None) != client.account_id:
        raise RuntimeError("V41 historical tick response account mismatch")
    ticks = tuple(cast(Iterable[object], getattr(result.value, "tickData", ())))
    has_more = getattr(result.value, "hasMore", None)
    if type(has_more) is not bool:
        raise RuntimeError("V41 historical tick response missing hasMore")
    return ticks, has_more


def _original_period(
    root: Path,
    *,
    expected: int,
) -> tuple[milestone.SimulatedTrade, ...]:
    ledgers = router._load_selected(root, expected=expected)
    rows = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    if len(rows) != expected:
        raise ValueError("V41 selected population count drift")
    return rows


def collect_symbol(
    *,
    symbol: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    output: Path,
) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    roots = {
        "development": development_root,
        "validation": validation_root,
        "reserved": reserved_root,
    }
    output.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    rows: list[ProviderQuoteMicrostructureState] = []
    period_counts: dict[str, int] = {}
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"cTrader DEMO authentication failed: {type(ready.error).__name__}"
            )
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)

        for period, slug, expected in PERIOD_SPECS:
            trades = tuple(
                sorted(
                    (
                        row
                        for row in _original_period(
                            roots[slug],
                            expected=expected,
                        )
                        if row.symbol == symbol
                    ),
                    key=lambda row: row.entry_at,
                )
            )
            if not trades:
                raise ValueError(f"V41 {period} has no {symbol} entrants")
            period_counts[period] = len(trades)

            for trade in trades:
                entry_at = _aware(trade.entry_at)
                risk = abs(
                    Decimal(trade.entry_price)
                    - Decimal(trade.original_stop_price)
                )
                responses: dict[str, tuple[tuple[object, ...], bool]] = {}
                for quote_name, quote_type in QUOTE_TYPES:
                    responses[quote_name] = _request_ticks(
                        client,
                        symbol_id=symbol_id,
                        target_at=entry_at,
                        quote_name=quote_name,
                        quote_type=quote_type,
                        request_id=(
                            f"capitalizer-v41:{period}:{symbol}:"
                            f"{trade.entry_at}:{quote_name}"
                        ),
                    )
                    time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
                bid_ticks, bid_has_more = responses["BID"]
                ask_ticks, ask_has_more = responses["ASK"]
                rows.append(
                    build_state(
                        symbol=symbol,
                        side=trade.side,
                        entry_at=entry_at,
                        structural_risk_price=risk,
                        bid_ticks=bid_ticks,
                        ask_ticks=ask_ticks,
                        digits=digits,
                        bid_has_more=bid_has_more,
                        ask_has_more=ask_has_more,
                    )
                )
    finally:
        client.close()

    expected_rows = sum(period_counts.values())
    if len(rows) != expected_rows:
        raise ValueError("V41 microstructure coverage drift")

    stem = f"capitalizer-v41-{symbol.lower()}-microstructure"
    with (output / f"{stem}.jsonl").open("w", encoding="utf-8") as handle:
        for state in rows:
            payload = asdict(state)
            period = next(
                period
                for period, slug, expected in PERIOD_SPECS
                if any(
                    trade.entry_at == state.entry_at
                    and trade.symbol == symbol
                    for trade in _original_period(
                        roots[slug],
                        expected=expected,
                    )
                )
            )
            handle.write(
                json.dumps(
                    {"period": period, "state": payload},
                    sort_keys=True,
                )
                + "\n"
            )

    report: dict[str, object] = {
        "identity": IDENTITY,
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "feature_dimension": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "period_counts": period_counts,
        "state_count": len(rows),
        "coverage": "1",
        "provider_native": True,
        "response_must_be_complete": True,
        "min_ticks_per_side": 2,
        "max_quote_age_seconds": MAX_QUOTE_AGE_SECONDS,
        "future_quote_used": False,
        "interpolation_used": False,
        "synthetic_quote_used": False,
        "outcome_used": False,
        "exit_used": False,
        "mae_mfe_used": False,
        "v11_features_used": False,
        "v38_geometry_features_used": False,
        "v40_m1_path_features_used": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "trader_certified": False,
    }
    (output / f"{stem}-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def load_states(
    root: Path,
    *,
    period: str,
) -> dict[tuple[str, str], ProviderQuoteMicrostructureState]:
    paths = sorted(root.rglob("capitalizer-v41-*-microstructure.jsonl"))
    if not paths:
        raise ValueError("V41 requires microstructure ledgers")
    result: dict[tuple[str, str], ProviderQuoteMicrostructureState] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict) or payload.get("period") != period:
                    continue
                raw = payload.get("state")
                if not isinstance(raw, dict):
                    raise ValueError("V41 row missing state object")
                state = from_json_dict(raw)
                key = (state.symbol, state.entry_at)
                if key in result:
                    raise ValueError("V41 duplicate entrant identity")
                result[key] = state
    if not result:
        raise ValueError(f"V41 has no states for {period}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=TARGET_SYMBOLS)
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = collect_symbol(
        symbol=args.symbol,
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        output=args.output,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
