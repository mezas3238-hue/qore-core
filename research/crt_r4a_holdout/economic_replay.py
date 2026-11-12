"""Seven-family quote-price economic research bridge (offline, fail-closed).

Each candidate MUST carry frozen, family-owned geometry and causal timestamps.
Historical structural event counts are not orders; this bridge cannot construct
missing OHLC, provider quotes or cost schedules. Results have quote-price
units only, no FX conversion, no real balance or portfolio-level capital.
NO broker API, NO LIVE, NO VPS, NO certification.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from itertools import groupby, islice

from research.crt_r4a_holdout.paper_quote_execution import (
    BidAskM5,
    CostAssumptions,
    PaperResult,
    SwapDebit,
    simulate_single,
)
from research.crt_r4a_holdout.runner import SYMBOLS
from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_paper_plan import (
    MarketGeometry,
    plan_research_order,
)

D0 = Decimal("0")
SOURCE_PINE = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
ALLOWED_COHORTS = frozenset((
    "ICMARKETS_DEMO_CONFIRMED",
    "ATLAS_DEMO_BROKER_UNVERIFIED",
    "SYNTHETIC_TEST_ONLY",
))
LOCKED = datetime.max.replace(tzinfo=UTC)
FAMILY_PRIORITY = {family: index for index, family in enumerate(Family)}


@dataclass(frozen=True)
class FrozenResearchSignal:
    """One external causal event with independently recorded owned prices."""

    symbol: str
    provider_cohort: str
    family: Family
    source_event_id: str
    direction: int
    mss_at: datetime
    ratified_at: datetime
    available_at: datetime
    geometry: MarketGeometry
    atr_h4: Decimal
    price_tick: Decimal
    source_pine_blob: str = SOURCE_PINE

    def __post_init__(self) -> None:
        if (
            self.symbol not in SYMBOLS
            or self.provider_cohort not in ALLOWED_COHORTS
            or not isinstance(self.family, Family)
            or not isinstance(self.source_event_id, str)
            or not self.source_event_id.strip()
            or self.direction not in (1, -1)
            or self.source_pine_blob != SOURCE_PINE
        ):
            raise ValueError("unregistered provider, family, source or event identity")
        if any(
            t.tzinfo is None
            for t in (self.mss_at, self.ratified_at, self.available_at)
        ) or self.available_at < max(self.mss_at, self.ratified_at):
            raise ValueError("noncausal signal timestamp")
        if (
            self.family is Family.TWO_C_MSS_C2
            and self.mss_at > self.ratified_at
        ) or (
            self.family is Family.TWO_C_MSS_C3
            and self.mss_at <= self.ratified_at
        ) or (
            self.family in (Family.TRUE_3C, Family.INSIDE_RETURN,
                            Family.MULTI4, Family.MULTIN)
            and self.mss_at > self.ratified_at
        ):
            raise ValueError("MSS timestamp violates own-family C2/C3/H4 timing")
        if (
            not self.atr_h4.is_finite() or self.atr_h4 <= 0
            or not self.price_tick.is_finite() or self.price_tick <= 0
        ):
            raise ValueError("signal needs immutable positive ATR and tick")


@dataclass(frozen=True)
class QuoteEvidence:
    """A matching source-specific quote sequence: never synthesize bid/ask."""

    symbol: str
    provider_cohort: str
    bars: tuple[BidAskM5, ...]
    cost_assumptions: CostAssumptions
    swaps: tuple[SwapDebit, ...] = ()
    quote_source_sha256: str | None = None
    costs_broker_verified: bool = False

    def __post_init__(self) -> None:
        if (
            self.symbol not in SYMBOLS
            or self.provider_cohort not in ALLOWED_COHORTS
            or not self.bars
            or not isinstance(self.cost_assumptions, CostAssumptions)
        ):
            raise ValueError("quote tape requires explicit symbol/provider/bars/costs")
        previous: datetime | None = None
        for bar in self.bars:
            if not isinstance(bar, BidAskM5):
                raise ValueError("requires bid/ask M5 tape, not mid-price OHLC")
            if previous is not None and bar.opened_at <= previous:
                raise ValueError("quote source must be chronologically ordered")
            previous = bar.opened_at
        if self.quote_source_sha256 is not None and (
            len(self.quote_source_sha256) != 64
            or any(x not in "0123456789abcdef" for x in self.quote_source_sha256)
        ):
            raise ValueError("unverified quote SHA256 format")
        if any(not isinstance(s, SwapDebit) for s in self.swaps):
            raise ValueError("invalid swap records")
        # A declared flag is not independent certification of costs.
        # Return status always states the certification evidence is missing.


@dataclass(frozen=True)
class ReplayObservation:
    family: Family
    source_event_id: str
    signal_at: datetime
    status: str
    result: PaperResult | None = None
    reason: str | None = None


@dataclass(frozen=True)
class FamilyEconomics:
    signals: int
    closed: int
    wins: int
    losses: int
    breakeven: int
    without_fill: int
    unsettled: int
    blocked: int
    gross_quote: Decimal | None
    net_quote: Decimal | None
    mean_net_r: Decimal | None
    profit_factor_net_quote: Decimal | None


def summarize(observations: tuple[ReplayObservation, ...]) -> FamilyEconomics:
    settled = [
        o.result for o in observations
        if o.result is not None and o.result.status in (
            "CLOSED_STOP", "CLOSED_TARGET"
        )
    ]
    # Do not infer PF/R from absence of closed trades or a positive-only sample.
    net = [r.net_quote for r in settled if r.net_quote is not None]
    rs = [r.net_r for r in settled if r.net_r is not None]
    gross = [r.gross_quote for r in settled if r.gross_quote is not None]
    positive = sum((x for x in net if x > 0), D0)
    negative = -sum((x for x in net if x < 0), D0)
    return FamilyEconomics(
        signals=len(observations),
        closed=len(settled),
        wins=sum(x > 0 for x in net),
        losses=sum(x < 0 for x in net),
        breakeven=sum(x == 0 for x in net),
        without_fill=sum(
            o.status in ("EXPIRED_NO_FILL", "NO_FILL_TAPE_END")
            for o in observations
        ),
        unsettled=sum(o.status == "OPEN_UNSETTLED" for o in observations),
        blocked=sum(
            o.status not in (
                "CLOSED_STOP", "CLOSED_TARGET", "EXPIRED_NO_FILL",
                "NO_FILL_TAPE_END", "OPEN_UNSETTLED"
            )
            for o in observations
        ),
        gross_quote=sum(gross, D0) if settled else None,
        net_quote=sum(net, D0) if settled else None,
        mean_net_r=sum(rs, D0) / len(rs) if rs else None,
        profit_factor_net_quote=positive / negative if negative > 0 else None,
    )


@dataclass(frozen=True)
class ResearchReplay:
    symbol: str
    provider_cohort: str
    observations: tuple[ReplayObservation, ...]
    by_family: dict[str, FamilyEconomics]
    all_families: FamilyEconomics
    status: str = "EXPERIMENTAL_QUOTE_PRICE_REPLAY_NOT_CERTIFIED"
    broker_orders_executed: int = 0
    pine_parity_certified: bool = False
    holdout_24m_certified: bool = False
    broker_costs_certified: bool = False
    account_currency_pnl_certified: bool = False


def replay_symbol(
    signals: tuple[FrozenResearchSignal, ...],
    quotes: QuoteEvidence,
    *,
    quantity: Decimal,
) -> ResearchReplay:
    """Replay one symbol with strictly conservative hypothetical order ownership.

    Order-policy frozen before economics: one active submitted order OR pending
    limit per symbol, until its expiry/closed exit. On opposing SAME-M5 signal
    directions, no arbitrary long/short choice is permitted: block every event.
    On same-side ties use registered Family enum order, then source identity.
    Any gap with unresolved order locks following signals until tape end.
    This is a QA policy hypothesis, NOT source Pine's execution specification.
    Cross-symbol FX/risk-budgeting remains a separate blocked gate.
    """
    if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
        raise ValueError("quantity must be positive finite Decimal")
    seen: set[tuple[Family, str]] = set()
    for event in signals:
        if event.symbol != quotes.symbol or event.provider_cohort != quotes.provider_cohort:
            raise ValueError("signal and quote feed identity mismatch")
        key = (event.family, event.source_event_id)
        if key in seen:
            raise ValueError("duplicated event identity: reject, not double count")
        seen.add(key)
    ordered = sorted(
        signals, key=lambda x: (
            x.available_at, FAMILY_PRIORITY[x.family], x.source_event_id
        )
    )
    # One index build replaces per-signal scanning over 100k+ old M5 bars.
    # Quote samples remain original (no re-bucketing or synthesized spreads).
    quote_opens = tuple(bar.opened_at for bar in quotes.bars)
    locked_until: datetime | None = None
    rows: list[ReplayObservation] = []
    for _, candidates in groupby(ordered, key=lambda e: e.available_at):
        same_time = tuple(candidates)
        # Block contradictory family recommendations on the same source M5.
        # Choosing one would introduce a hidden discretionary side preference.
        if len({event.direction for event in same_time}) > 1:
            rows.extend(
                ReplayObservation(
                    event.family, event.source_event_id, event.available_at,
                    "BLOCKED_OPPOSING_SAME_BAR",
                )
                for event in same_time
            )
            continue
        for event in same_time:
            if locked_until is not None and event.available_at < locked_until:
                rows.append(ReplayObservation(
                    event.family, event.source_event_id, event.available_at,
                    "BLOCKED_OVERLAPPING_EXPOSURE",
                ))
                continue
            try:
                plan = plan_research_order(
                    event.family,
                    direction=event.direction,
                    source_event_id=event.source_event_id,
                    geometry=event.geometry,
                    available_at=event.available_at,
                    mss_at=event.mss_at,
                    ratified_at=event.ratified_at,
                    atr_h4=event.atr_h4,
                    price_tick=event.price_tick,
                )
            except ValueError as exc:
                rows.append(ReplayObservation(
                    event.family, event.source_event_id, event.available_at,
                    "REJECTED_INVALID_STRATEGY_PLAN", reason=str(exc),
                ))
                continue
            first_eligible = bisect_left(quote_opens, event.available_at)
            result = simulate_single(
                plan, islice(quotes.bars, first_eligible, None),
                quantity=quantity,
                costs=quotes.cost_assumptions,
                swap_debits=quotes.swaps,
            )
            rows.append(ReplayObservation(
                event.family, event.source_event_id, event.available_at,
                result.status, result=result,
            ))
            if result.status == "BLOCKED_QUOTE_GAP":
                # Missing prices make order lifecycle unresolvable.
                locked_until = LOCKED
            elif result.entry_at is not None:
                locked_until = (
                    result.exit_at if result.exit_at is not None else LOCKED
                )
            else:
                # A submitted pending limit reserves the single-order slot
                # while waiting; no second family may quietly queue one.
                locked_until = plan.expiry_at
    observations = tuple(rows)
    by_family = {
        family.value: summarize(tuple(x for x in observations if x.family == family))
        for family in Family
    }
    return ResearchReplay(
        symbol=quotes.symbol,
        provider_cohort=quotes.provider_cohort,
        observations=observations,
        by_family=by_family,
        all_families=summarize(observations),
    )
