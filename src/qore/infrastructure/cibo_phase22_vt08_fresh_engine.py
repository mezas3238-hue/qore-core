"""Frozen VT08 Phase22 fresh engine over the V2 six-month source corpus.

The engine reuses the exact R3.8 methodology modules already proven byte-
identical to the frozen VT08 source commit. Its only new data transformation is
deterministic M5 -> M15 aggregation. It has no sizing, Risk or broker authority.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    AUTHORIZED_FOREX_MARKETS,
    OWNER_FOREX_ENTRY_ANCHORS,
    Vt08B01Bar,
    Vt08B01Candidate,
    evaluate_b01_at_entry_indexed,
    methodology_fingerprint,
)

FROZEN_VT08_SOURCE_GIT_SHA = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
FROZEN_PORTFOLIO = frozenset(
    {
        ("AUDJPY", "short"),
        ("GBPUSD", "short"),
        ("GBPJPY", "long"),
        ("GBPJPY", "short"),
    }
)
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class FrozenVt08ModeledTrade:
    signal_at: datetime
    exited_at: datetime
    side: DemoTradingSetupSide
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    exit_reason: str
    return_rate: Decimal


@dataclass(frozen=True, slots=True)
class Phase22M5ToM15Receipt:
    symbol: str
    source_m5_bars: int
    emitted_m15_bars: int
    incomplete_m15_bins: int
    first_m15_opened_at: str | None
    last_m15_opened_at: str | None
    transform_id: str = "M5_TO_M15_EXACT_THREE_BAR_UTC_V1"

    def payload(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


@dataclass(frozen=True, slots=True)
class Phase22VolumeFreeOpportunity:
    trader_id: str
    symbol: str
    signal_fingerprint: str
    signal_at: str
    entry_at: str
    exit_at: str
    side: str
    entry: str
    stop: str
    target: str
    exit_price: str
    exit_reason: str
    realized_r: str
    methodology_sha256: str
    causal_provenance: tuple[str, ...]
    volume: None = None

    def __post_init__(self) -> None:
        if self.trader_id != "VT08_FOREX":
            raise ValueError("VT08 Phase22 opportunity Trader drift")
        if self.symbol not in AUTHORIZED_FOREX_MARKETS:
            raise ValueError("VT08 Phase22 opportunity market drift")
        if self.side not in {"long", "short"}:
            raise ValueError("VT08 Phase22 opportunity side drift")
        if self.volume is not None:
            raise ValueError("VT08 Phase22 opportunity must be volume-free")
        if not self.signal_fingerprint.startswith("sha256:"):
            raise ValueError("VT08 signal fingerprint must be SHA-256")
        if not self.methodology_sha256.startswith("sha256:"):
            raise ValueError("VT08 methodology digest must be SHA-256")


@dataclass(frozen=True, slots=True)
class Phase22Vt08SymbolResult:
    symbol: str
    resampling: Phase22M5ToM15Receipt
    candidate_count: int
    multiple_candidate_days: int
    incomplete_exit_windows: int
    abstain_reasons: tuple[tuple[str, int], ...]
    opportunities: tuple[Phase22VolumeFreeOpportunity, ...]


def _bucket_start(value: datetime) -> datetime:
    utc = value.astimezone(UTC)
    return utc.replace(
        minute=(utc.minute // 15) * 15,
        second=0,
        microsecond=0,
    )


def resample_m5_to_m15(
    evidence: Evidence,
) -> tuple[tuple[Vt08B01Bar, ...], Phase22M5ToM15Receipt]:
    """Aggregate only exact contiguous 00/05/10 M5 triplets; never interpolate."""
    if evidence.symbol not in AUTHORIZED_FOREX_MARKETS:
        raise ValueError("VT08 Phase22 resampling requires authorized Forex")
    grouped: dict[datetime, list[Bar]] = defaultdict(list)
    for bar in evidence.bars:
        opened = bar.opened_at.astimezone(UTC)
        if (
            opened.second != 0
            or opened.microsecond != 0
            or opened.minute % 5 != 0
        ):
            raise ValueError("VT08 V2 M5 timestamp alignment drift")
        grouped[_bucket_start(opened)].append(bar)

    result: list[Vt08B01Bar] = []
    incomplete = 0
    for bucket in sorted(grouped):
        rows = sorted(grouped[bucket], key=lambda item: item.opened_at)
        expected = (
            bucket,
            bucket + timedelta(minutes=5),
            bucket + timedelta(minutes=10),
        )
        observed = tuple(item.opened_at.astimezone(UTC) for item in rows)
        if observed != expected:
            incomplete += 1
            continue
        result.append(
            Vt08B01Bar(
                opened_at=bucket,
                closed_at=bucket + timedelta(minutes=15),
                open=rows[0].open,
                high=max(item.high for item in rows),
                low=min(item.low for item in rows),
                close=rows[-1].close,
            )
        )
    frozen = tuple(result)
    receipt = Phase22M5ToM15Receipt(
        symbol=evidence.symbol,
        source_m5_bars=len(evidence.bars),
        emitted_m15_bars=len(frozen),
        incomplete_m15_bins=incomplete,
        first_m15_opened_at=(
            None if not frozen else frozen[0].opened_at.isoformat()
        ),
        last_m15_opened_at=(
            None if not frozen else frozen[-1].opened_at.isoformat()
        ),
    )
    return frozen, receipt



def _touches(bar: Vt08B01Bar, price: Decimal) -> bool:
    return bar.low <= price <= bar.high


def _model_trade_frozen(
    candidate: Vt08B01Candidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> FrozenVt08ModeledTrade | None:
    """Exact copy of the frozen R3.8 execution model, without loader policy."""
    start = candidate.decision_at.astimezone(UTC)
    local = start.astimezone(_NY)
    end = (local + timedelta(hours=4)).astimezone(UTC)
    if end - start != timedelta(hours=4):
        return None
    retained: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)
    if cursor != end or not retained:
        return None

    setup = candidate.setup
    exit_price = retained[-1].close
    exited_at = retained[-1].closed_at
    reason = "h4_containment_exit"
    for bar in retained:
        if _touches(bar, setup.invalidation_price):
            exit_price = setup.invalidation_price
            exited_at = bar.closed_at
            reason = "stop"
            break
        if _touches(bar, setup.take_profit_price):
            exit_price = setup.take_profit_price
            exited_at = bar.closed_at
            reason = "target"
            break

    if candidate.side is DemoTradingSetupSide.LONG:
        return_rate = (exit_price - setup.entry_price) / setup.entry_price
    else:
        return_rate = (setup.entry_price - exit_price) / setup.entry_price
    return FrozenVt08ModeledTrade(
        signal_at=start,
        exited_at=exited_at,
        side=candidate.side,
        entry=setup.entry_price,
        stop=setup.invalidation_price,
        target=setup.take_profit_price,
        exit_price=exit_price,
        exit_reason=reason,
        return_rate=return_rate,
    )

def _realized_r(trade: FrozenVt08ModeledTrade) -> Decimal:
    if trade.side is DemoTradingSetupSide.LONG:
        risk = trade.entry - trade.stop
        delta = trade.exit_price - trade.entry
    else:
        risk = trade.stop - trade.entry
        delta = trade.entry - trade.exit_price
    if risk <= 0:
        raise ValueError("VT08 Phase22 trade risk must be positive")
    return delta / risk


def _fingerprint(
    *,
    symbol: str,
    trade: FrozenVt08ModeledTrade,
) -> str:
    payload = {
        "trader_id": "VT08_FOREX",
        "symbol": symbol,
        "signal_at": trade.signal_at.astimezone(UTC).isoformat(),
        "side": trade.side.value,
        "entry": format(trade.entry, "f"),
        "stop": format(trade.stop, "f"),
        "target": format(trade.target, "f"),
        "methodology_sha256": methodology_fingerprint(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def _opportunity(
    symbol: str,
    trade: FrozenVt08ModeledTrade,
    transform_sha256: str,
) -> Phase22VolumeFreeOpportunity:
    return Phase22VolumeFreeOpportunity(
        trader_id="VT08_FOREX",
        symbol=symbol,
        signal_fingerprint=_fingerprint(symbol=symbol, trade=trade),
        signal_at=trade.signal_at.astimezone(UTC).isoformat(),
        entry_at=trade.signal_at.astimezone(UTC).isoformat(),
        exit_at=trade.exited_at.astimezone(UTC).isoformat(),
        side=trade.side.value,
        entry=format(trade.entry, "f"),
        stop=format(trade.stop, "f"),
        target=format(trade.target, "f"),
        exit_price=format(trade.exit_price, "f"),
        exit_reason=trade.exit_reason,
        realized_r=format(_realized_r(trade), "f"),
        methodology_sha256=f"sha256:{methodology_fingerprint()}",
        causal_provenance=(
            f"git:{FROZEN_VT08_SOURCE_GIT_SHA}",
            transform_sha256,
        ),
    )


def evaluate_vt08_phase22_symbol(
    *,
    raw_root: Path,
) -> Phase22Vt08SymbolResult:
    """Evaluate one V2 symbol without the historical >=730-day loader guard."""
    evidence, _provenance = journey.load_raw_m5(raw_root)
    bars, resampling = resample_m5_to_m15(evidence)
    by_open = {item.opened_at: item for item in bars}
    abstains: Counter[str] = Counter()
    candidates_by_day: dict[date, list[Vt08B01Candidate]] = defaultdict(list)

    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in OWNER_FOREX_ENTRY_ANCHORS:
            continue
        evaluation = evaluate_b01_at_entry_indexed(
            symbol=evidence.symbol,
            bars_by_open=by_open,
            decision_at=bar.opened_at,
        )
        if evaluation.candidate is None:
            assert evaluation.abstain_reason is not None
            abstains[evaluation.abstain_reason.value] += 1
            continue
        candidates_by_day[local.date()].append(evaluation.candidate)

    multiple = 0
    incomplete = 0
    trades: list[FrozenVt08ModeledTrade] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            multiple += 1
            continue
        modeled = _model_trade_frozen(candidates[0], bars_by_open=by_open)
        if modeled is None:
            incomplete += 1
            continue
        trades.append(modeled)

    transform_sha = resampling.fingerprint()
    opportunities = tuple(
        _opportunity(evidence.symbol, trade, transform_sha)
        for trade in trades
        if (evidence.symbol, trade.side.value) in FROZEN_PORTFOLIO
    )
    return Phase22Vt08SymbolResult(
        symbol=evidence.symbol,
        resampling=resampling,
        candidate_count=sum(len(items) for items in candidates_by_day.values()),
        multiple_candidate_days=multiple,
        incomplete_exit_windows=incomplete,
        abstain_reasons=tuple(sorted(abstains.items())),
        opportunities=opportunities,
    )


def validate_full_vt08_surface(
    results: tuple[Phase22Vt08SymbolResult, ...],
) -> None:
    symbols = tuple(item.symbol for item in results)
    if symbols != AUTHORIZED_FOREX_MARKETS:
        raise ValueError("VT08 Phase22 requires exact ordered seven-market surface")
    fingerprints = tuple(
        opportunity.signal_fingerprint
        for result in results
        for opportunity in result.opportunities
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("VT08 Phase22 duplicate signal fingerprint")
