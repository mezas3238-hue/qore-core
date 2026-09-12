"""Fresh >=730-day replay for VT-31 R2.2 with a daily cardinality ledger.

Source semantics and QORE execution formalization are emitted separately. The
backtest never labels the zone-midpoint/CE policy as a TTrades rule.
"""

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
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    AUTHORIZED_MARKET,
    SOURCE_SHA256,
    Vt31R22AbstainReason,
    Vt31R22EntryFamily,
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
    source_fingerprint,
)

_SCHEMA = "qore.trader_lab.vt31_r2_2_backtest.v1"
_NY = ZoneInfo("America/New_York")
_OWNER_POLICY = "human-owner-max-one-filled-trade-per-nas100-new-york-date-v1"


class Vt31R22BacktestError(Vt31SilverBulletV2BacktestError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt31R22Trade:
    signal_at: datetime
    filled_at: datetime
    resolved_at: datetime | None
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    three_r_price: Decimal
    selected_family: Vt31R22EntryFamily
    candidate_families: tuple[Vt31R22EntryFamily, ...]
    breakeven_armed_at: datetime | None
    outcome: str
    exit_price: Decimal | None
    r_multiple: Decimal | None

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": self.signal_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "filled_at": self.filled_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "resolved_at": (
                self.resolved_at.astimezone(UTC).isoformat(timespec="microseconds")
                if self.resolved_at is not None
                else None
            ),
            "side": self.side.value,
            "entry_price": format(self.entry_price, "f"),
            "stop_price": format(self.stop_price, "f"),
            "target_price": format(self.target_price, "f"),
            "three_r_price": format(self.three_r_price, "f"),
            "selected_family": self.selected_family.value,
            "candidate_families": [item.value for item in self.candidate_families],
            "breakeven_armed_at": (
                self.breakeven_armed_at.astimezone(UTC).isoformat(timespec="microseconds")
                if self.breakeven_armed_at is not None
                else None
            ),
            "outcome": self.outcome,
            "exit_price": format(self.exit_price, "f") if self.exit_price is not None else None,
            "r_multiple": format(self.r_multiple, "f") if self.r_multiple is not None else None,
        }


@dataclass(frozen=True, slots=True)
class Vt31MarketDayLedger:
    local_date: date
    eligible_day: bool
    reference_complete: bool
    session_complete: bool
    reference_high: Decimal | None
    reference_low: Decimal | None
    raid_high: bool
    raid_low: bool
    both_sides_swept: bool
    raid_at: datetime | None
    confirmation_at: datetime | None
    candidate_count: int
    candidate_families: tuple[str, ...]
    candidate_zones: tuple[tuple[str, str, str], ...]
    selected_setup: bool
    selection_policy: str
    pending_order: bool
    filled: bool
    filled_at: datetime | None
    three_r_reached: bool
    breakeven_armed: bool
    terminal_outcome: str | None
    resolved_at: datetime | None
    abstain_reason: str | None
    containment_reason: str | None
    source_fingerprint: str
    config_fingerprint: str
    evidence_fingerprint: str
    software_sha: str

    def __post_init__(self) -> None:
        if self.filled and not self.selected_setup:
            raise Vt31R22BacktestError("filled day must have one selected setup")
        if self.breakeven_armed and not self.filled:
            raise Vt31R22BacktestError("breakeven cannot arm without fill")
        if self.candidate_count != len(self.candidate_families):
            raise Vt31R22BacktestError("candidate count/family ledger mismatch")
        if self.candidate_count != len(self.candidate_zones):
            raise Vt31R22BacktestError("candidate count/zone ledger mismatch")

    def payload(self) -> dict[str, object]:
        def ts(value: datetime | None) -> str | None:
            return (
                value.astimezone(UTC).isoformat(timespec="microseconds")
                if value
                else None
            )

        return {
            "local_date": self.local_date.isoformat(),
            "eligible_day": self.eligible_day,
            "reference_complete": self.reference_complete,
            "session_complete": self.session_complete,
            "reference_high": format(self.reference_high, "f") if self.reference_high else None,
            "reference_low": format(self.reference_low, "f") if self.reference_low else None,
            "raid_high": self.raid_high,
            "raid_low": self.raid_low,
            "both_sides_swept": self.both_sides_swept,
            "raid_at": ts(self.raid_at),
            "confirmation_at": ts(self.confirmation_at),
            "candidate_count": self.candidate_count,
            "candidate_families": list(self.candidate_families),
            "candidate_zones": [
                {"family": family, "lower": lower, "upper": upper}
                for family, lower, upper in self.candidate_zones
            ],
            "selected_setup": self.selected_setup,
            "selection_policy": self.selection_policy,
            "pending_order": self.pending_order,
            "filled": self.filled,
            "filled_at": ts(self.filled_at),
            "three_r_reached": self.three_r_reached,
            "breakeven_armed": self.breakeven_armed,
            "terminal_outcome": self.terminal_outcome,
            "resolved_at": ts(self.resolved_at),
            "abstain_reason": self.abstain_reason,
            "containment_reason": self.containment_reason,
            "source_fingerprint": self.source_fingerprint,
            "config_fingerprint": self.config_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "software_sha": self.software_sha,
        }


@dataclass(frozen=True, slots=True)
class Vt31R22BacktestReport:
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    software_sha: str
    execution_policy: Vt31R22ExecutionPolicy
    ledgers: tuple[Vt31MarketDayLedger, ...]
    trades: tuple[Vt31R22Trade, ...]

    def payload(self) -> dict[str, object]:
        terminal = tuple(item for item in self.trades if item.r_multiple is not None)
        values = tuple(cast(Decimal, item.r_multiple) for item in terminal)
        targets = sum(item.outcome == "target" for item in terminal)
        stops = sum(item.outcome == "stop" for item in terminal)
        breakevens = sum(item.outcome == "breakeven" for item in terminal)
        expectancy = (
            sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)
        )
        win_rate = Decimal(targets) / Decimal(len(terminal)) if terminal else Decimal(0)
        equity = Decimal(0)
        peak = Decimal(0)
        max_drawdown = Decimal(0)
        for value in values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        eligible = sum(item.eligible_day for item in self.ledgers)
        filled = sum(item.filled for item in self.ledgers)
        if filled > eligible:
            raise Vt31R22BacktestError("filled count exceeds eligible market-day ceiling")
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "trader_code": "vt-31",
            "trader_version": "r2.2-source-rebuild",
            "methodology": "ttrades-am-silver-bullet-nq-r2.2",
            "symbol": AUTHORIZED_MARKET,
            "source_file_sha256": SOURCE_SHA256,
            "source_fingerprint": source_fingerprint(),
            "execution_policy": {
                "policy_id": self.execution_policy.policy_id,
                "source_rule": self.execution_policy.source_rule,
                "fingerprint": self.execution_policy.fingerprint(),
                "breaker_price_policy": self.execution_policy.breaker_price_policy,
                "order_block_price_policy": self.execution_policy.order_block_price_policy,
                "fvg_price_policy": self.execution_policy.fvg_price_policy,
                "family_selection_policy": self.execution_policy.family_selection_policy,
                "stop_policy": self.execution_policy.stop_policy,
                "same_bar_policy": self.execution_policy.same_bar_policy,
            },
            "human_owner_daily_cardinality_policy": _OWNER_POLICY,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "software_sha": self.software_sha,
            "eligible_market_days": eligible,
            "maximum_possible_fills": eligible,
            "selected_setup_count": sum(item.selected_setup for item in self.ledgers),
            "pending_order_count": sum(item.pending_order for item in self.ledgers),
            "filled_count": filled,
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
                        if item.abstain_reason
                    ).items()
                )
            ),
            "containment_counts": dict(
                sorted(
                    Counter(
                        item.containment_reason
                        for item in self.ledgers
                        if item.containment_reason
                    ).items()
                )
            ),
            "entry_family_counts": dict(
                sorted(Counter(item.selected_family.value for item in self.trades).items())
            ),
            "ledgers": [item.payload() for item in self.ledgers],
            "trades": [item.payload() for item in self.trades],
        }


def _ny_date(value: datetime) -> date:
    return value.astimezone(_NY).date()


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _touches(bar: OhlcSnapshot, price: Decimal) -> bool:
    return Decimal(str(bar.low)) <= price <= Decimal(str(bar.high))


def _complete_contiguous(bars: tuple[OhlcSnapshot, ...], expected: int) -> bool:
    return len(bars) == expected and all(
        current.opened_at == previous.closed_at
        for previous, current in zip(bars, bars[1:])
    )


def _terminal(
    setup: Vt31R22ExecutableSetup,
    fill: OhlcSnapshot,
    bar: OhlcSnapshot,
    breakeven_at: datetime | None,
    outcome: str,
    exit_price: Decimal,
    r_multiple: Decimal,
) -> Vt31R22Trade:
    return Vt31R22Trade(
        setup.decision_at,
        fill.closed_at,
        bar.closed_at,
        setup.side,
        setup.entry_price,
        setup.stop_price,
        setup.target_price,
        setup.three_r_price,
        setup.selected_family,
        setup.candidate_families,
        breakeven_at,
        outcome,
        exit_price,
        r_multiple,
    )


def _model_filled_trade(
    series: tuple[OhlcSnapshot, ...],
    *,
    fill_index: int,
    setup: Vt31R22ExecutableSetup,
) -> Vt31R22Trade:
    fill = series[fill_index]
    breakeven_at: datetime | None = None
    for index in range(fill_index, len(series)):
        bar = series[index]
        if index > fill_index and bar.opened_at != series[index - 1].closed_at:
            return Vt31R22Trade(
                setup.decision_at,
                fill.closed_at,
                series[index - 1].closed_at,
                setup.side,
                setup.entry_price,
                setup.stop_price,
                setup.target_price,
                setup.three_r_price,
                setup.selected_family,
                setup.candidate_families,
                breakeven_at,
                "gap_censored",
                None,
                None,
            )
        if index == fill_index:
            if _touches(bar, setup.stop_price):
                return _terminal(
                    setup,
                    fill,
                    bar,
                    breakeven_at,
                    "stop",
                    setup.stop_price,
                    Decimal(-1),
                )
            continue
        if breakeven_at is None:
            if _touches(bar, setup.stop_price):
                return _terminal(
                    setup, fill, bar, None, "stop", setup.stop_price, Decimal(-1)
                )
            if _touches(bar, setup.target_price):
                reward = abs(setup.target_price - setup.entry_price) / setup.initial_risk
                return _terminal(
                    setup, fill, bar, None, "target", setup.target_price, reward
                )
            if _touches(bar, setup.three_r_price):
                breakeven_at = bar.closed_at
            continue
        if _touches(bar, setup.entry_price):
            return _terminal(
                setup,
                fill,
                bar,
                breakeven_at,
                "breakeven",
                setup.entry_price,
                Decimal(0),
            )
        if _touches(bar, setup.target_price):
            reward = abs(setup.target_price - setup.entry_price) / setup.initial_risk
            return _terminal(
                setup, fill, bar, breakeven_at, "target", setup.target_price, reward
            )
    return Vt31R22Trade(
        setup.decision_at,
        fill.closed_at,
        None,
        setup.side,
        setup.entry_price,
        setup.stop_price,
        setup.target_price,
        setup.three_r_price,
        setup.selected_family,
        setup.candidate_families,
        breakeven_at,
        "data_end_censored",
        None,
        None,
    )


def _ledger(
    *,
    local_day: date,
    eligible: bool,
    reference: tuple[OhlcSnapshot, ...],
    session: tuple[OhlcSnapshot, ...],
    source_eval: object | None,
    setup: Vt31R22ExecutableSetup | None,
    pending: bool,
    trade: Vt31R22Trade | None,
    abstain: str | None,
    containment: str | None,
    evidence_fingerprint: str,
    policy: Vt31R22ExecutionPolicy,
    software_sha: str,
) -> Vt31MarketDayLedger:
    source_setup = getattr(source_eval, "setup", None)
    structure = source_setup.structure if source_setup is not None else None
    candidates = source_setup.candidates if source_setup is not None else ()
    high = max((Decimal(str(item.high)) for item in reference), default=None)
    low = min((Decimal(str(item.low)) for item in reference), default=None)
    ref_high = high if len(reference) == 60 else None
    ref_low = low if len(reference) == 60 else None
    raid_high = bool(
        ref_high is not None
        and any(Decimal(str(item.high)) > ref_high for item in session)
    )
    raid_low = bool(
        ref_low is not None
        and any(Decimal(str(item.low)) < ref_low for item in session)
    )
    return Vt31MarketDayLedger(
        local_date=local_day,
        eligible_day=eligible,
        reference_complete=_complete_contiguous(reference, 60),
        session_complete=_complete_contiguous(session, 60),
        reference_high=ref_high,
        reference_low=ref_low,
        raid_high=raid_high,
        raid_low=raid_low,
        both_sides_swept=raid_high and raid_low,
        raid_at=structure.raid_at if structure else None,
        confirmation_at=structure.confirmation_at if structure else None,
        candidate_count=len(candidates),
        candidate_families=tuple(item.family.value for item in candidates),
        candidate_zones=tuple(
            (
                item.family.value,
                format(item.zone_lower, "f"),
                format(item.zone_upper, "f"),
            )
            for item in candidates
        ),
        selected_setup=setup is not None,
        selection_policy=policy.family_selection_policy,
        pending_order=pending,
        filled=trade is not None,
        filled_at=trade.filled_at if trade else None,
        three_r_reached=bool(trade and trade.breakeven_armed_at),
        breakeven_armed=bool(trade and trade.breakeven_armed_at),
        terminal_outcome=trade.outcome if trade else None,
        resolved_at=trade.resolved_at if trade else None,
        abstain_reason=abstain,
        containment_reason=containment,
        source_fingerprint=source_fingerprint(),
        config_fingerprint=policy.fingerprint(),
        evidence_fingerprint=evidence_fingerprint,
        software_sha=software_sha,
    )


def run_vt31_r2_2_backtest(
    path: Path,
    policy: Vt31R22ExecutionPolicy | None = None,
) -> Vt31R22BacktestReport:
    series, account, evidence_fp, checked_at, software_sha = _load(path)
    selected_policy = policy or Vt31R22ExecutionPolicy()
    instrument = Instrument(AUTHORIZED_MARKET)
    by_day: dict[date, list[tuple[int, OhlcSnapshot]]] = defaultdict(list)
    for index, bar in enumerate(series):
        by_day[_ny_date(bar.opened_at)].append((index, bar))
    ledgers: list[Vt31MarketDayLedger] = []
    trades: list[Vt31R22Trade] = []

    for local_day in sorted(by_day):
        indexed = by_day[local_day]
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
        eligible = _complete_contiguous(reference, 60) and _complete_contiguous(
            session, 60
        )
        if not eligible:
            ledgers.append(
                _ledger(
                    local_day=local_day,
                    eligible=False,
                    reference=reference,
                    session=session,
                    source_eval=None,
                    setup=None,
                    pending=False,
                    trade=None,
                    abstain="reference-or-session-incomplete",
                    containment=None,
                    evidence_fingerprint=evidence_fp,
                    policy=selected_policy,
                    software_sha=software_sha,
                )
            )
            continue

        source_eval = None
        executable: Vt31R22ExecutableSetup | None = None
        abstain: str | None = None
        containment: str | None = None
        signal_global_index: int | None = None
        prefix: list[OhlcSnapshot] = list(reference)
        for global_index, bar in session_indexed:
            prefix.append(bar)
            source_eval = evaluate_vt31_r2_2_source(
                instrument=instrument,
                as_of=bar.closed_at,
                m1_candles=tuple(prefix),
                evidence_fingerprint=evidence_fp,
            )
            if source_eval.setup is None:
                abstain = cast(
                    Vt31R22AbstainReason, source_eval.abstain_reason
                ).value
                if source_eval.both_sides_swept:
                    containment = "abstain-both-sides-swept-r2.2"
                    break
                continue
            executable, execution_abstain = make_executable_setup(
                source_eval.setup,
                selected_policy,
            )
            if executable is None:
                abstain = cast(Vt31R22AbstainReason, execution_abstain).value
                if execution_abstain is Vt31R22AbstainReason.AMBIGUOUS_ENTRY_FAMILY:
                    containment = "no-source-family-priority"
                    break
                continue
            signal_global_index = global_index
            break

        if executable is None or signal_global_index is None:
            ledgers.append(
                _ledger(
                    local_day=local_day,
                    eligible=True,
                    reference=reference,
                    session=session,
                    source_eval=source_eval,
                    setup=None,
                    pending=False,
                    trade=None,
                    abstain=abstain,
                    containment=containment,
                    evidence_fingerprint=evidence_fp,
                    policy=selected_policy,
                    software_sha=software_sha,
                )
            )
            continue

        pending = True
        trade: Vt31R22Trade | None = None
        fill_index: int | None = None
        for index in range(signal_global_index + 1, len(series)):
            bar = series[index]
            if _ny_date(bar.opened_at) != local_day or _wall(bar.opened_at) >= (11, 0, 0):
                break
            previous = series[index - 1]
            if bar.opened_at != previous.closed_at:
                containment = "pending-data-gap"
                break
            ref = executable.source_setup.reference
            if (
                Decimal(str(bar.high)) > ref.high
                and Decimal(str(bar.low)) < ref.low
            ):
                containment = "abstain-both-sides-swept-before-fill"
                break
            if (
                executable.side is DemoTradingSetupSide.SHORT
                and Decimal(str(bar.low)) < ref.low
            ):
                containment = "abstain-both-sides-swept-before-fill"
                break
            if (
                executable.side is DemoTradingSetupSide.LONG
                and Decimal(str(bar.high)) > ref.high
            ):
                containment = "abstain-both-sides-swept-before-fill"
                break
            if _touches(bar, executable.entry_price):
                fill_index = index
                break
        if fill_index is not None:
            trade = _model_filled_trade(
                series,
                fill_index=fill_index,
                setup=executable,
            )
            trades.append(trade)
        elif containment is None:
            abstain = "pending-expired-at-11"

        ledgers.append(
            _ledger(
                local_day=local_day,
                eligible=True,
                reference=reference,
                session=session,
                source_eval=source_eval,
                setup=executable,
                pending=pending,
                trade=trade,
                abstain=abstain,
                containment=containment,
                evidence_fingerprint=evidence_fp,
                policy=selected_policy,
                software_sha=software_sha,
            )
        )

    if len({(item.local_date, AUTHORIZED_MARKET) for item in ledgers}) != len(ledgers):
        raise Vt31R22BacktestError("daily ledger keys must be unique")
    if any(
        sum(1 for trade in trades if _ny_date(trade.filled_at) == ledger.local_date) > 1
        for ledger in ledgers
    ):
        raise Vt31R22BacktestError("Human Owner daily cardinality violated")
    return Vt31R22BacktestReport(
        account_fingerprint=account,
        evidence_fingerprint=evidence_fp,
        checked_at=checked_at,
        software_sha=software_sha,
        execution_policy=selected_policy,
        ledgers=tuple(ledgers),
        trades=tuple(trades),
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python -m "
            "qore.infrastructure.trader_lab.vt31_silver_bullet_r2_2_backtest PATH"
        )
        return 2
    try:
        payload = run_vt31_r2_2_backtest(Path(args[0])).payload()
    except Vt31SilverBulletV2BacktestError as error:
        print(f"VT-31 R2.2 backtest failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
