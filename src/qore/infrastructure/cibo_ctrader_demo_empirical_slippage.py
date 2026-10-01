"""Read-only empirical entry-slippage calibration from cTrader DEMO history.

The collector reads QORE-labelled historical entry deals and the causal
provider BID/ASK immediately preceding each execution. It never sends, amends
or cancels an order. The result is current-account empirical execution evidence;
it is not historical-2017 provider economics and it never reads CIBO holdout
outcomes.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure

_PRICE_SCALE = Decimal("100000")
_BUY = 1
_SELL = 2
_BID = 1
_ASK = 2
_FILLED = 2
_PARTIALLY_FILLED = 3
_REQUIRED_DISTINCT_ORDERS_PER_SYMBOL = 8
_MAX_DEALS_PER_SYMBOL = 32
_LOOKBACK_DAYS = 365
_TICK_LOOKBACK_MS = 60_000


@dataclass(frozen=True, slots=True)
class CTraderEmpiricalSlippageObservation:
    evidence_ref: str
    qore_symbol: str
    provider_symbol: str
    trade_side: str
    execution_at: datetime
    quote_at: datetime
    quote_price: Decimal
    fill_price: Decimal
    signed_slippage_price: Decimal
    signed_slippage_bps: Decimal
    adverse_slippage_bps: Decimal
    execution_latency_ms: int
    quote_age_ms: int
    commission_usd: Decimal | None
    order_ref: str

    def __post_init__(self) -> None:
        if not self.evidence_ref.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "empirical slippage evidence ref must be SHA-256"
            )
        if not self.qore_symbol or not self.provider_symbol:
            raise CiboCapitalManagementError(
                "empirical slippage symbol identity required"
            )
        if self.trade_side not in {"BUY", "SELL"}:
            raise CiboCapitalManagementError(
                "empirical slippage side must be BUY/SELL"
            )
        for name in ("execution_at", "quote_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"empirical slippage {name} must be timezone-aware"
                )
        if self.quote_at > self.execution_at:
            raise CiboCapitalManagementError(
                "empirical slippage quote cannot postdate execution"
            )
        for name in ("quote_price", "fill_price"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"empirical slippage {name} must be finite positive"
                )
        for name in (
            "signed_slippage_price",
            "signed_slippage_bps",
            "adverse_slippage_bps",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"empirical slippage {name} must be finite"
                )
        if self.adverse_slippage_bps != max(
            Decimal(0), self.signed_slippage_bps
        ):
            raise CiboCapitalManagementError(
                "empirical slippage adverse metric drift"
            )
        if self.execution_latency_ms < 0 or self.quote_age_ms < 0:
            raise CiboCapitalManagementError(
                "empirical slippage latency cannot be negative"
            )
        if self.commission_usd is not None and (
            not self.commission_usd.is_finite()
            or self.commission_usd < 0
        ):
            raise CiboCapitalManagementError(
                "empirical slippage commission must be non-negative"
            )
        if not self.order_ref.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "empirical slippage order ref must be SHA-256"
            )


@dataclass(frozen=True, slots=True)
class CTraderEmpiricalSlippageSummary:
    qore_symbol: str
    fill_observations: int
    distinct_orders: int
    mean_signed_slippage_bps: Decimal
    p50_adverse_slippage_bps: Decimal
    p95_adverse_slippage_bps: Decimal
    worst_adverse_slippage_bps: Decimal
    p95_execution_latency_ms: int
    p95_quote_age_ms: int
    commission_observation_count: int
    mean_commission_usd: Decimal | None


@dataclass(frozen=True, slots=True)
class CTraderEmpiricalSlippageCalibration:
    provider_key: str
    environment: str
    account_fingerprint_sha256: str
    observed_at: datetime
    lookback_days: int
    account_entry_deals_found: int
    account_entry_deals_by_symbol: tuple[tuple[str, int], ...]
    qore_deals_found: int
    qore_deals_by_symbol: tuple[tuple[str, int], ...]
    non_qore_entry_deals_by_symbol: tuple[tuple[str, int], ...]
    observations: tuple[CTraderEmpiricalSlippageObservation, ...]
    summaries: tuple[CTraderEmpiricalSlippageSummary, ...]
    required_symbols: tuple[str, ...]
    required_symbol_coverage_met: bool
    minimum_distinct_orders_met: bool
    empirical_slippage_calibrated: bool
    execution_model_ready: bool
    deal_history_truncated: bool
    broker_mutation_performed: bool
    holdout_outcomes_used: bool
    historical_2017_exact_claimed: bool
    target_aware: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "empirical slippage provider/environment drift"
            )
        if len(self.account_fingerprint_sha256) != 64:
            raise CiboCapitalManagementError(
                "empirical slippage account fingerprint invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "empirical slippage observed_at must be timezone-aware"
            )
        names = tuple(item.qore_symbol for item in self.summaries)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise CiboCapitalManagementError(
                "empirical slippage summaries must be sorted unique"
            )
        required = set(self.required_symbols)
        expected_coverage = required.issubset(names)
        if self.required_symbol_coverage_met != expected_coverage:
            raise CiboCapitalManagementError(
                "empirical slippage symbol coverage drift"
            )
        by_symbol = {item.qore_symbol: item for item in self.summaries}
        expected_minimum = expected_coverage and all(
            by_symbol[symbol].distinct_orders
            >= _REQUIRED_DISTINCT_ORDERS_PER_SYMBOL
            for symbol in required
        )
        if self.minimum_distinct_orders_met != expected_minimum:
            raise CiboCapitalManagementError(
                "empirical slippage distinct-order minimum drift"
            )
        expected_ready = (
            expected_coverage
            and expected_minimum
            and bool(self.observations)
            and not self.blockers
            and not self.broker_mutation_performed
            and not self.holdout_outcomes_used
            and not self.historical_2017_exact_claimed
            and not self.target_aware
        )
        if (
            self.empirical_slippage_calibrated != expected_ready
            or self.execution_model_ready != expected_ready
        ):
            raise CiboCapitalManagementError(
                "empirical slippage readiness drift"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "empirical slippage calibration has no productive authority"
            )


def collect_ctrader_demo_empirical_slippage(
    client: CTraderOpenApiMessageClientBoundary,
    *,
    observed_at: datetime | None = None,
) -> CTraderEmpiricalSlippageCalibration:
    observed = observed_at or datetime.now(UTC)
    binding = discover_free_account_binding(client, bound_at=observed)
    account_id = client.account_id
    from_at = observed - timedelta(days=_LOOKBACK_DAYS)
    deals_response = _request(
        client,
        "ProtoOADealListReq",
        {
            "ctidTraderAccountId": account_id,
            "fromTimestamp": int(from_at.timestamp() * 1000),
            "toTimestamp": int(observed.timestamp() * 1000),
            "maxRows": 5000,
        },
        "qore-cibo-empirical-slippage-deals",
    )
    deal_history_truncated = bool(getattr(deals_response, "hasMore", False))
    contracts = {item.symbol_id: item for item in binding.contracts}
    required_symbols = tuple(
        sorted(item.qore_symbol for item in binding.contracts)
    )
    raw_deals = tuple(getattr(deals_response, "deal", ()))
    account_entries = tuple(
        deal
        for deal in raw_deals
        if _account_entry_deal(deal, contracts)
    )
    account_counts = Counter(
        contracts[int(deal.symbolId)].qore_symbol
        for deal in account_entries
    )
    candidates: list[Any] = []
    for deal in account_entries:
        if not _qore_label(deal):
            continue
        candidates.append(deal)
    qore_counts = Counter(
        contracts[int(deal.symbolId)].qore_symbol
        for deal in candidates
    )
    non_qore_counts = Counter(account_counts)
    non_qore_counts.subtract(qore_counts)
    candidates.sort(
        key=lambda item: int(item.executionTimestamp),
        reverse=True,
    )

    sampled: list[Any] = []
    per_symbol: dict[str, int] = defaultdict(int)
    for deal in candidates:
        contract = contracts[int(deal.symbolId)]
        symbol = contract.qore_symbol
        if per_symbol[symbol] >= _MAX_DEALS_PER_SYMBOL:
            continue
        sampled.append(deal)
        per_symbol[symbol] += 1

    observations: list[CTraderEmpiricalSlippageObservation] = []
    quote_failures: dict[str, int] = defaultdict(int)
    for deal in sampled:
        contract = contracts[int(deal.symbolId)]
        try:
            observation = _deal_observation(
                client=client,
                account_id=account_id,
                contract=contract,
                deal=deal,
            )
        except CiboCapitalManagementError:
            quote_failures[contract.qore_symbol] += 1
            continue
        observations.append(observation)

    summaries = tuple(
        _summary(
            symbol=symbol,
            rows=tuple(
                item for item in observations if item.qore_symbol == symbol
            ),
        )
        for symbol in sorted({item.qore_symbol for item in observations})
    )
    summary_by_symbol = {item.qore_symbol: item for item in summaries}
    coverage = set(required_symbols).issubset(summary_by_symbol)
    minimum = coverage and all(
        summary_by_symbol[symbol].distinct_orders
        >= _REQUIRED_DISTINCT_ORDERS_PER_SYMBOL
        for symbol in required_symbols
    )

    blockers: list[str] = []
    if not coverage:
        blockers.append("EMPIRICAL_SLIPPAGE_REQUIRED_SYMBOL_COVERAGE_INCOMPLETE")
    if not minimum:
        blockers.append("EMPIRICAL_SLIPPAGE_MINIMUM_DISTINCT_ORDERS_NOT_MET")
    if not observations:
        blockers.append("EMPIRICAL_SLIPPAGE_NO_CAUSAL_QUOTE_OBSERVATIONS")
    if any(quote_failures.values()):
        blockers.append("EMPIRICAL_SLIPPAGE_CAUSAL_QUOTE_GAPS_PRESENT")
    blockers = list(dict.fromkeys(blockers))
    ready = coverage and minimum and bool(observations) and not blockers

    account_fingerprint = hashlib.sha256(
        f"ctrader-demo:{binding.account.account_ref}".encode()
    ).hexdigest()
    return CTraderEmpiricalSlippageCalibration(
        provider_key="ctrader-demo",
        environment="demo",
        account_fingerprint_sha256=account_fingerprint,
        observed_at=observed,
        lookback_days=_LOOKBACK_DAYS,
        account_entry_deals_found=len(account_entries),
        account_entry_deals_by_symbol=tuple(
            (symbol, account_counts.get(symbol, 0))
            for symbol in required_symbols
        ),
        qore_deals_found=len(candidates),
        qore_deals_by_symbol=tuple(
            (symbol, qore_counts.get(symbol, 0))
            for symbol in required_symbols
        ),
        non_qore_entry_deals_by_symbol=tuple(
            (symbol, non_qore_counts.get(symbol, 0))
            for symbol in required_symbols
        ),
        observations=tuple(observations),
        summaries=summaries,
        required_symbols=required_symbols,
        required_symbol_coverage_met=coverage,
        minimum_distinct_orders_met=minimum,
        empirical_slippage_calibrated=ready,
        execution_model_ready=ready,
        deal_history_truncated=deal_history_truncated,
        broker_mutation_performed=False,
        holdout_outcomes_used=False,
        historical_2017_exact_claimed=False,
        target_aware=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )


def decode_ctrader_tick_series(
    rows: tuple[object, ...],
) -> tuple[tuple[int, Decimal], ...]:
    """Decode newest-first cTrader delta timestamps into absolute timestamps."""

    if not rows:
        return ()
    decoded: list[tuple[int, Decimal]] = []
    previous_timestamp: int | None = None
    for index, row in enumerate(rows):
        raw_timestamp = getattr(row, "timestamp", None)
        raw_tick = getattr(row, "tick", None)
        if type(raw_timestamp) is not int or raw_timestamp < 0:
            raise CiboCapitalManagementError(
                "historical tick timestamp invalid"
            )
        if type(raw_tick) is not int or raw_tick <= 0:
            raise CiboCapitalManagementError("historical tick price invalid")
        if index == 0:
            absolute = raw_timestamp
        else:
            if previous_timestamp is None or raw_timestamp > previous_timestamp:
                raise CiboCapitalManagementError(
                    "historical tick delta timestamp invalid"
                )
            absolute = previous_timestamp - raw_timestamp
        decoded.append((absolute, Decimal(raw_tick) / _PRICE_SCALE))
        previous_timestamp = absolute
    return tuple(decoded)


def signed_slippage(
    *,
    side: str,
    quote_price: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    if quote_price <= 0 or fill_price <= 0:
        raise CiboCapitalManagementError(
            "slippage prices must be positive"
        )
    if side == "BUY":
        signed_price = fill_price - quote_price
    elif side == "SELL":
        signed_price = quote_price - fill_price
    else:
        raise CiboCapitalManagementError("slippage side must be BUY/SELL")
    signed_bps = signed_price / quote_price * Decimal("10000")
    return signed_price, signed_bps, max(Decimal(0), signed_bps)


def _account_entry_deal(
    deal: Any,
    contracts: Mapping[int, object],
) -> bool:
    symbol_id = deal.symbolId
    if type(symbol_id) is not int or symbol_id not in contracts:
        return False
    if deal.dealStatus not in {_FILLED, _PARTIALLY_FILLED}:
        return False
    execution_price = deal.executionPrice
    execution_at = deal.executionTimestamp
    create_at = deal.createTimestamp
    filled_volume = deal.filledVolume
    side = deal.tradeSide
    if (
        not isinstance(execution_price, float)
        or execution_price <= 0
        or type(execution_at) is not int
        or execution_at <= 0
        or type(create_at) is not int
        or create_at <= 0
        or type(filled_volume) is not int
        or filled_volume <= 0
        or side not in {_BUY, _SELL}
    ):
        return False
    if _field_present(deal, "closePositionDetail"):
        return False
    return True


def _qore_label(deal: Any) -> bool:
    label = deal.label
    return isinstance(label, str) and label.startswith("QORE:")


def _deal_observation(
    *,
    client: CTraderOpenApiMessageClientBoundary,
    account_id: int,
    contract: Any,
    deal: Any,
) -> CTraderEmpiricalSlippageObservation:
    execution_ms = int(deal.executionTimestamp)
    create_ms = int(deal.createTimestamp)
    side_code = int(deal.tradeSide)
    side = "BUY" if side_code == _BUY else "SELL"
    quote_type = _ASK if side_code == _BUY else _BID
    response = _request(
        client,
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": account_id,
            "symbolId": contract.symbol_id,
            "type": quote_type,
            "fromTimestamp": max(0, execution_ms - _TICK_LOOKBACK_MS),
            "toTimestamp": execution_ms,
        },
        f"qore-cibo-tick-{contract.symbol_id}-{execution_ms}-{quote_type}",
    )
    ticks = decode_ctrader_tick_series(
        tuple(getattr(response, "tickData", ()))
    )
    causal = tuple(item for item in ticks if item[0] <= execution_ms)
    if not causal:
        raise CiboCapitalManagementError(
            "no causal historical quote before execution"
        )
    quote_ms, quote_price = max(causal, key=lambda item: item[0])
    fill_price = Decimal(str(deal.executionPrice))
    signed_price, signed_bps, adverse_bps = signed_slippage(
        side=side,
        quote_price=quote_price,
        fill_price=fill_price,
    )
    deal_id = int(deal.dealId)
    order_id = int(deal.orderId)
    evidence_ref = _hash_ref(
        f"{deal_id}|{order_id}|{contract.symbol_id}|{execution_ms}|{fill_price}"
    )
    order_ref = _hash_ref(f"order|{order_id}")
    commission = _commission_usd(deal)
    return CTraderEmpiricalSlippageObservation(
        evidence_ref=evidence_ref,
        qore_symbol=contract.qore_symbol,
        provider_symbol=contract.symbol_name,
        trade_side=side,
        execution_at=datetime.fromtimestamp(execution_ms / 1000, tz=UTC),
        quote_at=datetime.fromtimestamp(quote_ms / 1000, tz=UTC),
        quote_price=quote_price,
        fill_price=fill_price,
        signed_slippage_price=signed_price,
        signed_slippage_bps=signed_bps,
        adverse_slippage_bps=adverse_bps,
        execution_latency_ms=max(0, execution_ms - create_ms),
        quote_age_ms=max(0, execution_ms - quote_ms),
        commission_usd=commission,
        order_ref=order_ref,
    )


def _summary(
    *,
    symbol: str,
    rows: tuple[CTraderEmpiricalSlippageObservation, ...],
) -> CTraderEmpiricalSlippageSummary:
    if not rows:
        raise CiboCapitalManagementError(
            "empirical slippage summary requires observations"
        )
    signed = tuple(item.signed_slippage_bps for item in rows)
    adverse = tuple(item.adverse_slippage_bps for item in rows)
    execution_latency = tuple(
        Decimal(item.execution_latency_ms) for item in rows
    )
    quote_age = tuple(Decimal(item.quote_age_ms) for item in rows)
    commissions = tuple(
        item.commission_usd
        for item in rows
        if item.commission_usd is not None
    )
    return CTraderEmpiricalSlippageSummary(
        qore_symbol=symbol,
        fill_observations=len(rows),
        distinct_orders=len({item.order_ref for item in rows}),
        mean_signed_slippage_bps=sum(signed, Decimal(0))
        / Decimal(len(signed)),
        p50_adverse_slippage_bps=_nearest_rank(adverse, 50),
        p95_adverse_slippage_bps=_nearest_rank(adverse, 95),
        worst_adverse_slippage_bps=max(adverse),
        p95_execution_latency_ms=int(
            _nearest_rank(execution_latency, 95)
        ),
        p95_quote_age_ms=int(_nearest_rank(quote_age, 95)),
        commission_observation_count=len(commissions),
        mean_commission_usd=(
            sum(commissions, Decimal(0)) / Decimal(len(commissions))
            if commissions
            else None
        ),
    )


def _nearest_rank(
    values: tuple[Decimal, ...],
    percentile: int,
) -> Decimal:
    if not values:
        raise CiboCapitalManagementError("percentile requires values")
    ordered = tuple(sorted(values))
    index = max(0, ceil(Decimal(percentile) / Decimal(100) * len(ordered)) - 1)
    return ordered[index]


def _commission_usd(deal: object) -> Decimal | None:
    if not _field_present(deal, "commission"):
        return None
    raw = getattr(deal, "commission", None)
    digits = getattr(deal, "moneyDigits", None)
    if type(raw) is not int or type(digits) is not int or digits < 0:
        return None
    return abs(Decimal(raw).scaleb(-digits))


def _field_present(message: object, name: str) -> bool:
    has_field = getattr(message, "HasField", None)
    if callable(has_field):
        try:
            return bool(has_field(name))
        except (ValueError, KeyError):
            pass
    list_fields = getattr(message, "ListFields", None)
    if callable(list_fields):
        try:
            return any(
                getattr(descriptor, "name", None) == name
                for descriptor, _ in list_fields()
            )
        except (TypeError, ValueError):
            return False
    return False


def _hash_ref(material: str) -> str:
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _request(
    client: CTraderOpenApiMessageClientBoundary,
    name: str,
    fields: dict[str, object],
    message_id: str,
) -> object:
    result = client.request(
        name,
        fields,
        client_msg_id=message_id,
        timeout_seconds=10.0,
    )
    if isinstance(result, Failure):
        raise CiboCapitalManagementError(str(result.error))
    return result.value
