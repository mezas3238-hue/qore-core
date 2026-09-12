"""Fresh historical replay for the VT-31 R2.4 source-demonstrated subset."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
    _load,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import AUTHORIZED_MARKET
from qore.infrastructure.traders.vt31_silver_bullet_r2_4 import (
    Vt31R24AbstainReason,
    Vt31R24ExactSetup,
    evaluate_vt31_r2_4_exact,
    source_bundle_fingerprint,
)

_SCHEMA = "qore.trader_lab.vt31_r2_4_backtest.v1"
_NY = ZoneInfo("America/New_York")
_OWNER_POLICY = "human-owner-max-one-filled-trade-per-nas100-new-york-date-v1"
_BUNDLE_ID = "SB_AM_FVG_MIDNIGHT_CE_SHORT_R2_4_V1"


class Vt31R24BacktestError(Vt31SilverBulletV2BacktestError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt31R24Trade:
    signal_at: datetime
    filled_at: datetime
    resolved_at: datetime | None
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    three_r_price: Decimal
    breakeven_armed_at: datetime | None
    outcome: str
    exit_price: Decimal | None
    r_multiple: Decimal | None

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": _ts(self.signal_at),
            "filled_at": _ts(self.filled_at),
            "resolved_at": _ts(self.resolved_at) if self.resolved_at else None,
            "side": DemoTradingSetupSide.SHORT.value,
            "entry_price": format(self.entry_price, "f"),
            "stop_price": format(self.stop_price, "f"),
            "target_price": format(self.target_price, "f"),
            "three_r_price": format(self.three_r_price, "f"),
            "breakeven_armed_at": (
                _ts(self.breakeven_armed_at) if self.breakeven_armed_at else None
            ),
            "outcome": self.outcome,
            "exit_price": format(self.exit_price, "f") if self.exit_price is not None else None,
            "r_multiple": format(self.r_multiple, "f") if self.r_multiple is not None else None,
        }


@dataclass(frozen=True, slots=True)
class Vt31R24MarketDayLedger:
    local_date: date
    eligible_day: bool
    reference_complete: bool
    session_complete: bool
    midnight_open_available: bool
    raid_high: bool
    raid_low: bool
    both_sides_swept: bool
    candidate_count: int
    selected_setup: bool
    pending_order: bool
    filled: bool
    filled_at: datetime | None
    three_r_reached: bool
    breakeven_armed: bool
    terminal_outcome: str | None
    resolved_at: datetime | None
    abstain_reason: str | None
    containment_reason: str | None
    source_bundle_fingerprint: str
    evidence_fingerprint: str
    software_sha: str

    def __post_init__(self) -> None:
        if self.filled and not self.selected_setup:
            raise Vt31R24BacktestError("filled day requires selected setup")
        if self.breakeven_armed and not self.filled:
            raise Vt31R24BacktestError("breakeven cannot arm without fill")
        if self.candidate_count not in (0, 1):
            raise Vt31R24BacktestError("R2.4 exact subset permits at most one exact candidate/day")

    def payload(self) -> dict[str, object]:
        return {
            "local_date": self.local_date.isoformat(),
            "eligible_day": self.eligible_day,
            "reference_complete": self.reference_complete,
            "session_complete": self.session_complete,
            "midnight_open_available": self.midnight_open_available,
            "raid_high": self.raid_high,
            "raid_low": self.raid_low,
            "both_sides_swept": self.both_sides_swept,
            "candidate_count": self.candidate_count,
            "selected_setup": self.selected_setup,
            "pending_order": self.pending_order,
            "filled": self.filled,
            "filled_at": _ts(self.filled_at) if self.filled_at else None,
            "three_r_reached": self.three_r_reached,
            "breakeven_armed": self.breakeven_armed,
            "terminal_outcome": self.terminal_outcome,
            "resolved_at": _ts(self.resolved_at) if self.resolved_at else None,
            "abstain_reason": self.abstain_reason,
            "containment_reason": self.containment_reason,
            "source_bundle_fingerprint": self.source_bundle_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "software_sha": self.software_sha,
        }


@dataclass(frozen=True, slots=True)
class Vt31R24BacktestReport:
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    software_sha: str
    ledgers: tuple[Vt31R24MarketDayLedger, ...]
    trades: tuple[Vt31R24Trade, ...]

    def payload(self) -> dict[str, object]:
        terminal = tuple(item for item in self.trades if item.r_multiple is not None)
        r_values = tuple(cast(Decimal, item.r_multiple) for item in terminal)
        targets = sum(item.outcome == "target" for item in terminal)
        stops = sum(item.outcome == "stop" for item in terminal)
        breakevens = sum(item.outcome == "breakeven" for item in terminal)
        expectancy = (
            sum(r_values, Decimal(0)) / Decimal(len(r_values))
            if r_values
            else Decimal(0)
        )
        win_rate = Decimal(targets) / Decimal(len(terminal)) if terminal else Decimal(0)
        equity = Decimal(0)
        peak = Decimal(0)
        max_drawdown = Decimal(0)
        for value in r_values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        eligible = sum(item.eligible_day for item in self.ledgers)
        fills = sum(item.filled for item in self.ledgers)
        if fills > eligible:
            raise Vt31R24BacktestError("filled count exceeds eligible market-day ceiling")
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "trader_code": "vt-31",
            "trader_version": "r2.4-source-demonstrated-subset",
            "methodology": "ttrades-am-silver-bullet-nq-r2.4-source-demonstrated-subset",
            "symbol": AUTHORIZED_MARKET,
            "bundle_id": _BUNDLE_ID,
            "source_exact_historical_replay": True,
            "broker_source_complete": False,
            "broker_order_type": "unresolved",
            "live_stop_offset": "unresolved",
            "generic_breaker_entry": "unresolved-not-executed",
            "generic_order_block_entry": "unresolved-not-executed",
            "generic_fvg_entry": "unresolved-not-executed",
            "both_sides_swept": "qore-operational-containment-abstain",
            "intrabar_ambiguity_policy": "censor-not-guess-v1",
            "human_owner_daily_cardinality_policy": _OWNER_POLICY,
            "source_bundle_fingerprint": source_bundle_fingerprint(),
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": _ts(self.checked_at),
            "software_sha": self.software_sha,
            "eligible_market_days": eligible,
            "maximum_possible_fills": eligible,
            "selected_setup_count": sum(item.selected_setup for item in self.ledgers),
            "pending_order_count": sum(item.pending_order for item in self.ledgers),
            "filled_count": fills,
            "daily_cardinality_violations": 0,
            "terminal_sample_size": len(terminal),
            "target_count": targets,
            "stop_count": stops,
            "breakeven_count": breakevens,
            "censored_count": sum(item.r_multiple is None for item in self.trades),
            "win_rate": format(win_rate, "f"),
            "expectancy_r": format(expectancy, "f"),
            "max_drawdown_r": format(max_drawdown, "f"),
            "abstain_counts": dict(
                sorted(
                    Counter(
                        item.abstain_reason
                        for item in self.ledgers
                        if item.abstain_reason is not None
                    ).items()
                )
            ),
            "containment_counts": dict(
                sorted(
                    Counter(
                        item.containment_reason
                        for item in self.ledgers
                        if item.containment_reason is not None
                    ).items()
                )
            ),
            "ledgers": [item.payload() for item in self.ledgers],
            "trades": [item.payload() for item in self.trades],
        }


def _ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _ny_date(value: datetime) -> date:
    return value.astimezone(_NY).date()


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _touches(bar: OhlcSnapshot, price: Decimal) -> bool:
    return _d(bar.low) <= price <= _d(bar.high)


def _complete_contiguous(bars: tuple[OhlcSnapshot, ...], expected: int) -> bool:
    return len(bars) == expected and all(
        current.opened_at == previous.closed_at
        for previous, current in zip(bars, bars[1:], strict=False)
    )


def _terminal(
    setup: Vt31R24ExactSetup,
    fill: OhlcSnapshot,
    bar: OhlcSnapshot,
    *,
    outcome: str,
    exit_price: Decimal,
    r_multiple: Decimal,
    breakeven_at: datetime | None,
) -> Vt31R24Trade:
    return Vt31R24Trade(
        signal_at=setup.decision_at,
        filled_at=fill.closed_at,
        resolved_at=bar.closed_at,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        three_r_price=setup.three_r_price,
        breakeven_armed_at=breakeven_at,
        outcome=outcome,
        exit_price=exit_price,
        r_multiple=r_multiple,
    )


def _censored(
    setup: Vt31R24ExactSetup,
    fill: OhlcSnapshot,
    bar: OhlcSnapshot | None,
    *,
    outcome: str,
    breakeven_at: datetime | None = None,
) -> Vt31R24Trade:
    return Vt31R24Trade(
        signal_at=setup.decision_at,
        filled_at=fill.closed_at,
        resolved_at=bar.closed_at if bar else None,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        three_r_price=setup.three_r_price,
        breakeven_armed_at=breakeven_at,
        outcome=outcome,
        exit_price=None,
        r_multiple=None,
    )


def _model_trade(
    series: tuple[OhlcSnapshot, ...],
    *,
    fill_index: int,
    setup: Vt31R24ExactSetup,
) -> Vt31R24Trade:
    fill = series[fill_index]
    if (
        _touches(fill, setup.stop_price)
        or _touches(fill, setup.target_price)
        or _touches(fill, setup.three_r_price)
    ):
        return _censored(setup, fill, fill, outcome="fill-bar-path-ambiguous")
    breakeven_at: datetime | None = None
    for index in range(fill_index + 1, len(series)):
        bar = series[index]
        previous = series[index - 1]
        if bar.opened_at != previous.closed_at:
            return _censored(
                setup,
                fill,
                previous,
                outcome="data-gap-censored",
                breakeven_at=breakeven_at,
            )
        stop_touch = _touches(bar, setup.stop_price)
        target_touch = _touches(bar, setup.target_price)
        three_r_touch = _touches(bar, setup.three_r_price)
        if breakeven_at is None:
            if stop_touch and (target_touch or three_r_touch):
                return _censored(setup, fill, bar, outcome="intrabar-path-ambiguous")
            if stop_touch:
                return _terminal(
                    setup,
                    fill,
                    bar,
                    outcome="stop",
                    exit_price=setup.stop_price,
                    r_multiple=Decimal(-1),
                    breakeven_at=None,
                )
            if target_touch:
                reward = abs(setup.target_price - setup.entry_price) / setup.initial_risk
                return _terminal(
                    setup,
                    fill,
                    bar,
                    outcome="target",
                    exit_price=setup.target_price,
                    r_multiple=reward,
                    breakeven_at=None,
                )
            if three_r_touch:
                breakeven_at = bar.closed_at
            continue
        be_touch = _touches(bar, setup.entry_price)
        if be_touch and target_touch:
            return _censored(
                setup,
                fill,
                bar,
                outcome="post-be-intrabar-path-ambiguous",
                breakeven_at=breakeven_at,
            )
        if be_touch:
            return _terminal(
                setup,
                fill,
                bar,
                outcome="breakeven",
                exit_price=setup.entry_price,
                r_multiple=Decimal(0),
                breakeven_at=breakeven_at,
            )
        if target_touch:
            reward = abs(setup.target_price - setup.entry_price) / setup.initial_risk
            return _terminal(
                setup,
                fill,
                bar,
                outcome="target",
                exit_price=setup.target_price,
                r_multiple=reward,
                breakeven_at=breakeven_at,
            )
    return _censored(
        setup,
        fill,
        None,
        outcome="data-end-censored",
        breakeven_at=breakeven_at,
    )


def run_vt31_r2_4_backtest(path: Path) -> Vt31R24BacktestReport:
    series, account, evidence_fp, checked_at, software_sha = _load(path)
    instrument = Instrument(AUTHORIZED_MARKET)
    by_day: dict[date, list[tuple[int, OhlcSnapshot]]] = defaultdict(list)
    for index, bar in enumerate(series):
        by_day[_ny_date(bar.opened_at)].append((index, bar))
    ledgers: list[Vt31R24MarketDayLedger] = []
    trades: list[Vt31R24Trade] = []

    for local_day in sorted(by_day):
        indexed = by_day[local_day]
        midnight = tuple(
            bar for _, bar in indexed if _wall(bar.opened_at) == (0, 0, 0)
        )
        reference = tuple(
            bar
            for _, bar in indexed
            if (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
        )
        session_indexed = tuple(
            (index, bar)
            for index, bar in indexed
            if (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
        )
        session = tuple(bar for _, bar in session_indexed)
        reference_complete = _complete_contiguous(reference, 60)
        session_complete = _complete_contiguous(session, 60)
        midnight_available = len(midnight) == 1
        eligible = reference_complete and session_complete and midnight_available
        if not eligible:
            ledgers.append(
                Vt31R24MarketDayLedger(
                    local_date=local_day,
                    eligible_day=False,
                    reference_complete=reference_complete,
                    session_complete=session_complete,
                    midnight_open_available=midnight_available,
                    raid_high=False,
                    raid_low=False,
                    both_sides_swept=False,
                    candidate_count=0,
                    selected_setup=False,
                    pending_order=False,
                    filled=False,
                    filled_at=None,
                    three_r_reached=False,
                    breakeven_armed=False,
                    terminal_outcome=None,
                    resolved_at=None,
                    abstain_reason="required-source-evidence-incomplete",
                    containment_reason=None,
                    source_bundle_fingerprint=source_bundle_fingerprint(),
                    evidence_fingerprint=evidence_fp,
                    software_sha=software_sha,
                )
            )
            continue

        ref_high = max(_d(bar.high) for bar in reference)
        ref_low = min(_d(bar.low) for bar in reference)
        raid_high = any(_d(bar.high) > ref_high for bar in session)
        raid_low = any(_d(bar.low) < ref_low for bar in session)
        exact_setup: Vt31R24ExactSetup | None = None
        abstain: str | None = None
        containment: str | None = None
        signal_global_index: int | None = None
        prefix: list[OhlcSnapshot] = [midnight[0], *reference]
        last_evaluation = None
        for global_index, bar in session_indexed:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_4_exact(
                instrument=instrument,
                as_of=bar.closed_at,
                m1_candles=tuple(prefix),
                evidence_fingerprint=evidence_fp,
            )
            last_evaluation = evaluation
            if evaluation.source_evaluation.both_sides_swept:
                abstain = "both-sides-swept"
                containment = "abstain-both-sides-swept-r2.4"
                break
            if evaluation.setup is None:
                abstain = cast(Vt31R24AbstainReason, evaluation.abstain_reason).value
                continue
            exact_setup = evaluation.setup
            signal_global_index = global_index
            break

        if exact_setup is None or signal_global_index is None:
            ledgers.append(
                Vt31R24MarketDayLedger(
                    local_date=local_day,
                    eligible_day=True,
                    reference_complete=True,
                    session_complete=True,
                    midnight_open_available=True,
                    raid_high=raid_high,
                    raid_low=raid_low,
                    both_sides_swept=raid_high and raid_low,
                    candidate_count=0,
                    selected_setup=False,
                    pending_order=False,
                    filled=False,
                    filled_at=None,
                    three_r_reached=False,
                    breakeven_armed=False,
                    terminal_outcome=None,
                    resolved_at=None,
                    abstain_reason=abstain,
                    containment_reason=containment,
                    source_bundle_fingerprint=source_bundle_fingerprint(),
                    evidence_fingerprint=evidence_fp,
                    software_sha=software_sha,
                )
            )
            continue

        fill_index: int | None = None
        for index in range(signal_global_index + 1, len(series)):
            bar = series[index]
            if _ny_date(bar.opened_at) != local_day or _wall(bar.opened_at) >= (11, 0, 0):
                break
            previous = series[index - 1]
            if bar.opened_at != previous.closed_at:
                containment = "pending-data-gap"
                break
            if _d(bar.low) < exact_setup.source_setup.reference.low:
                containment = "abstain-both-sides-swept-before-fill-r2.4"
                break
            if _touches(bar, exact_setup.entry_price):
                fill_index = index
                break

        trade: Vt31R24Trade | None = None
        if fill_index is not None:
            trade = _model_trade(series, fill_index=fill_index, setup=exact_setup)
            trades.append(trade)
        elif containment is None:
            abstain = "pending-expired-at-11"

        ledgers.append(
            Vt31R24MarketDayLedger(
                local_date=local_day,
                eligible_day=True,
                reference_complete=True,
                session_complete=True,
                midnight_open_available=True,
                raid_high=raid_high,
                raid_low=raid_low,
                both_sides_swept=raid_high and raid_low,
                candidate_count=1,
                selected_setup=True,
                pending_order=True,
                filled=trade is not None,
                filled_at=trade.filled_at if trade else None,
                three_r_reached=bool(trade and trade.breakeven_armed_at),
                breakeven_armed=bool(trade and trade.breakeven_armed_at),
                terminal_outcome=trade.outcome if trade else None,
                resolved_at=trade.resolved_at if trade else None,
                abstain_reason=abstain,
                containment_reason=containment,
                source_bundle_fingerprint=source_bundle_fingerprint(),
                evidence_fingerprint=evidence_fp,
                software_sha=software_sha,
            )
        )

    if any(
        sum(1 for trade in trades if _ny_date(trade.filled_at) == ledger.local_date) > 1
        for ledger in ledgers
    ):
        raise Vt31R24BacktestError("Human Owner daily cardinality violated")
    return Vt31R24BacktestReport(
        account_fingerprint=account,
        evidence_fingerprint=evidence_fp,
        checked_at=checked_at,
        software_sha=software_sha,
        ledgers=tuple(ledgers),
        trades=tuple(trades),
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.vt31_silver_bullet_r2_4_backtest PATH"
        )
        return 2
    try:
        payload = run_vt31_r2_4_backtest(Path(args[0])).payload()
    except Vt31SilverBulletV2BacktestError as error:
        print(f"VT-31 R2.4 backtest failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
