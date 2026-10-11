"""VT08 5M M15-C2 intracandle reversal, preregistered, research ONLY.

TTrades source supports wick -> CISD -> protected swing -> trade same H4 body.
Broker fill at next M15 open, PS-exact stop, 2R and filled-H4 expiry are
QORE MODEL ASSUMPTIONS, not original TTrades rules or executable orders.
NO future outcomes are used for admission, event identity, or daily selection.
Do not interpret this as a fully cognitive replay or a certification.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    _r_multiple,
    load_market_evidence,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _latest_complete_source_days,
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_5m_m15_intracycle_c2_reversal.research.v1"
BUNDLE: Final = "M15_C2_REVERSAL_INTRACYCLE_QORE_FILL_2R_V1"
PREREG: Final = (
    "docs/research/VT08_5M_A_P0_M15_INTRACYCLE_C2_REVERSAL_PREREG_2026-10-10.md"
)
SOURCE_HEAD: Final = "b2d33e1b4829d8b4afc76983decca8a99131403c"
SOURCE_RUN_ID: Final = 35934924907
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class IntracycleSignal:
    market: str
    anchor_at: datetime
    decision_at: datetime
    confirmed_at: datetime
    opposing_series_at: datetime
    anchor_hour_ny: int
    ny_date: date
    side: DemoTradingSetupSide
    entry: Decimal
    stop: Decimal
    target: Decimal
    expires_at: datetime
    cisd_level: Decimal
    evidence_fingerprint: str

    def __post_init__(self) -> None:
        if self.market not in EXPANSION_MARKETS:
            raise ValueError("signal market out of research scope")
        if self.anchor_hour_ny not in ANCHORS_NY:
            raise ValueError("signal anchor outside Owner scope")
        times = (
            self.anchor_at,
            self.decision_at,
            self.confirmed_at,
            self.opposing_series_at,
            self.expires_at,
        )
        if any(x.tzinfo is None or x.utcoffset() is None for x in times):
            raise ValueError("signal timestamps must have timezone")
        if not (
            self.anchor_at <= self.opposing_series_at
            < self.confirmed_at
            == self.decision_at
            < self.expires_at
            == self.anchor_at + timedelta(hours=4)
        ):
            raise ValueError("signal not causal inside same H4")
        local = self.anchor_at.astimezone(_NY)
        if (local.hour != self.anchor_hour_ny or local.minute or local.second):
            raise ValueError("signal must originate at NY Owner anchor")
        if local.date() != self.ny_date:
            raise ValueError("signal NY date mismatch")
        risk = (
            self.entry - self.stop
            if self.side is DemoTradingSetupSide.LONG
            else self.stop - self.entry
        )
        if risk <= 0 or self.entry <= 0 or self.stop <= 0:
            raise ValueError("signal invalid risk geometry")
        expected = (
            self.entry + 2 * risk
            if self.side is DemoTradingSetupSide.LONG
            else self.entry - 2 * risk
        )
        if self.target != expected or self.target <= 0:
            raise ValueError("signal target differs from research-only 2R")

    def source_event_id(self) -> str:
        """Stable series-origin fingerprint; not dependent on later PnL."""
        material = "|".join(
            (
                BUNDLE,
                self.market,
                self.anchor_at.astimezone(UTC).isoformat(),
                self.side.value,
                self.opposing_series_at.astimezone(UTC).isoformat(),
            )
        )
        return "vt08-source:" + hashlib.sha256(material.encode()).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "bundle": BUNDLE,
            "source_event_id": self.source_event_id(),
            "market": self.market,
            "ny_date": self.ny_date.isoformat(),
            "anchor_ny_hour": self.anchor_hour_ny,
            "ltf_profile": "M15_STANDARD",
            "source_family": "reversal-entry",
            "scenario": "C2_INTRACYCLE_AFTER_PS_CISD",
            "side": self.side.value,
            "anchor_at": self.anchor_at.isoformat(),
            "decision_at": self.decision_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat(),
            "opposing_series_at": self.opposing_series_at.isoformat(),
            "entry_price": str(self.entry),
            "stop_price": str(self.stop),
            "target_price": str(self.target),
            "cisd_level": str(self.cisd_level),
            "expires_at": self.expires_at.isoformat(),
            "evidence_fingerprint": self.evidence_fingerprint,
            "methodology_status": "SOURCE_SUPPORTED_QORE_FILL_EXPERIMENT",
            "entry_mechanics": "NEXT_M15_OHLC_OPEN_QORE_CONTAINMENT",
            "stop_mechanics": "PROTECTED_SWING_EXACT_QORE_CONTAINMENT",
            "target_mechanics": "FIXED_2R_QORE_CONTAINMENT",
            "position_lifecycle": "SAME_H4_CLOSE_QORE_CONTAINMENT",
            "broker_costs": "NOT_MODELED",
            "research_only": True,
            "live_authorized": False,
            "cognitive_replay": False,
        }


def cycle_signal(
    *,
    market: str,
    anchor: Vt08B01Bar,
    bars_by_open: dict[datetime, Vt08B01Bar],
    evidence_fingerprint: str,
) -> tuple[IntracycleSignal | None, str]:
    """Exactly one earliest causally valid PS signal from each source H4 cycle.

    Outcome prices after decision are never used to decide entry.
    """
    local = anchor.opened_at.astimezone(_NY)
    if (local.hour not in ANCHORS_NY or local.minute or local.second):
        return None, "OUTSIDE_OWNER_ANCHOR"
    reference = source_h4_from_m15(
        bars_by_open, opened_at_local=local - timedelta(hours=4)
    )
    if reference is None:
        return None, "NO_PREVIOUS_H4"
    source_days = _latest_complete_source_days(bars_by_open, before_local=local)
    if len(source_days) != 2:
        return None, "SOURCE_DAY_INCOMPLETE"
    current_day, previous_day = source_days
    side = resolve_bias(previous_day=previous_day, current_day=current_day)
    if side is None:
        return None, "BIAS_UNRESOLVED"
    end = anchor.opened_at + timedelta(hours=4)
    # Stream only the causal, contiguous M15 prefix. Do not require future
    # H4 bars to exist before identifying an earlier valid CISD confirmation.
    observed: list[Vt08B01Bar] = []
    cursor = anchor.opened_at
    while cursor < end:
        row = bars_by_open.get(cursor)
        if (
            row is None
            or row.closed_at != cursor + timedelta(minutes=15)
        ):
            break
        observed.append(row)
        cursor += timedelta(minutes=15)
    bars = tuple(observed)
    if len(bars) < 2:
        return None, "INSUFFICIENT_CAUSAL_M15_PREFIX"
    important_level = (
        reference.low
        if side is DemoTradingSetupSide.LONG
        else reference.high
    )
    swings = protected_swings_in_candle2(
        bars, side=side, important_level=important_level
    )
    if not swings:
        return None, "NO_INTRACYCLE_CISD_PS"
    # Earliest in calendar order, with immutable tie resolution by source origin;
    # no best-price, closest stop, future order outcome or eventual profitability.
    swing = sorted(
        swings,
        key=lambda x: (x.confirmed_at, x.opposing_series_opened_at),
    )[0]
    if swing.confirmed_at >= end:
        return None, "NO_M15_LEFT_AFTER_CONFIRMATION"
    next_bar = bars_by_open.get(swing.confirmed_at)
    if (
        next_bar is None
        or next_bar.opened_at != swing.confirmed_at
        or next_bar.closed_at != next_bar.opened_at + timedelta(minutes=15)
    ):
        return None, "NO_NEXT_M15_OPEN"
    entry = next_bar.open
    stop = swing.price
    risk = (
        entry - stop
        if side is DemoTradingSetupSide.LONG
        else stop - entry
    )
    if risk <= 0:
        return None, "INVALID_CAUSAL_RISK"
    target = (
        entry + 2 * risk
        if side is DemoTradingSetupSide.LONG
        else entry - 2 * risk
    )
    if target <= 0:
        return None, "NONPOSITIVE_TARGET"
    signal = IntracycleSignal(
        market=market,
        anchor_at=anchor.opened_at,
        decision_at=next_bar.opened_at,
        confirmed_at=swing.confirmed_at,
        opposing_series_at=swing.opposing_series_opened_at,
        anchor_hour_ny=local.hour,
        ny_date=local.date(),
        side=side,
        entry=entry,
        stop=stop,
        target=target,
        expires_at=end,
        cisd_level=swing.cisd_level,
        evidence_fingerprint=evidence_fingerprint,
    )
    return signal, "CAUSAL_NEXT_M15_OPEN_QORE_RESEARCH_FILL"


def replay_trade(
    signal: IntracycleSignal,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> ExpansionTrade | None:
    """Model exits after entry only; stop-first on ambiguous M15 candle."""
    retained = _window_bars(
        bars_by_open,
        opened_at=signal.decision_at,
        closed_at=signal.expires_at,
    )
    if retained is None or not retained:
        return None
    exit_price = retained[-1].close
    exit_time = retained[-1].closed_at
    reason = "h4_qore_containment"
    for bar in retained:
        stop_hit = bar.low <= signal.stop <= bar.high
        target_hit = bar.low <= signal.target <= bar.high
        if stop_hit:
            exit_price = signal.stop
            exit_time = bar.closed_at
            reason = "stop_first_ambiguous" if target_hit else "stop"
            break
        if target_hit:
            exit_price = signal.target
            exit_time = bar.closed_at
            reason = "target"
            break
    return ExpansionTrade(
        symbol=signal.market,
        signal_at=signal.decision_at,
        exited_at=exit_time,
        anchor_hour_ny=signal.anchor_hour_ny,
        side=signal.side,
        entry=signal.entry,
        stop=signal.stop,
        target=signal.target,
        exit_price=exit_price,
        exit_reason=reason,
        r_multiple=_r_multiple(
            side=signal.side,
            entry=signal.entry,
            stop=signal.stop,
            exit_price=exit_price,
        ),
    )


def evaluate(path: Path) -> dict[str, object]:
    fingerprint, market, checked_at, sha, m15 = load_market_evidence(path)
    if sha != SOURCE_HEAD or market not in EXPANSION_MARKETS:
        raise ValueError("not frozen consumed 1095D five-market evidence")
    bars_by_open = {bar.opened_at: bar for bar in m15}
    rejection: Counter[str] = Counter()
    cycles: list[dict[str, object]] = []
    eligible: list[IntracycleSignal] = []
    for bar in m15:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        signal, state = cycle_signal(
            market=market,
            anchor=bar,
            bars_by_open=bars_by_open,
            evidence_fingerprint=fingerprint,
        )
        rejection[state] += 1
        cycles.append({
            "anchor_at": bar.opened_at.isoformat(),
            "ny_date": local.date().isoformat(),
            "anchor_ny_hour": local.hour,
            "status": state,
            "source_event_id": signal.source_event_id() if signal else None,
        })
        if signal:
            eligible.append(signal)
    first_per_day: dict[date, IntracycleSignal] = {}
    daily_conflicts = 0
    for signal in sorted(
        eligible,
        key=lambda s: (s.decision_at, s.anchor_at, s.source_event_id()),
    ):
        if signal.ny_date in first_per_day:
            daily_conflicts += 1
        else:
            first_per_day[signal.ny_date] = signal
    selected = sorted(first_per_day.values(), key=lambda s: s.decision_at)
    complete: list[ExpansionTrade] = []
    incomplete = 0
    for signal in selected:
        trade = replay_trade(signal, bars_by_open)
        if trade is None:
            incomplete += 1
        else:
            complete.append(trade)

    ny_year_signals: dict[str, Counter[str]] = defaultdict(Counter)
    for row in eligible:
        ny_year_signals[str(row.ny_date.year)]["eligible"] += 1
    for row in selected:
        ny_year_signals[str(row.ny_date.year)]["daily_selected"] += 1
    for row in complete:
        year = str(row.signal_at.astimezone(_NY).year)
        ny_year_signals[year]["terminal"] += 1

    if len(cycles) != sum(rejection.values()):
        raise AssertionError("inconsistent source H4 cycle count")
    if len(eligible) != len(selected) + daily_conflicts:
        raise AssertionError("Owner day cardinality must reconcile")
    if len(complete) + incomplete != len(selected):
        raise AssertionError("terminal and incomplete count mismatch")

    return {
        "schema": SCHEMA,
        "preregistered_bundle": BUNDLE,
        "preregistered_document": PREREG,
        "software_sha": sha,
        "source_run_id": SOURCE_RUN_ID,
        "evidence_account_hash": fingerprint,
        "evidence_checked_at": checked_at.isoformat(),
        "market": market,
        "observed_owner_h4": len(cycles),
        "by_rejection_reason": dict(sorted(rejection.items())),
        "source_supported_qore_fill_events": len(eligible),
        "daily_conflict_exclusions": daily_conflicts,
        "unique_ny_days_selected": len(selected),
        "complete_simulated_trades": len(complete),
        "incomplete_exit_windows": incomplete,
        "by_year_ny_counts": {
            year: dict(counter)
            for year, counter in sorted(ny_year_signals.items())
        },
        "raw_equal_risk": metrics(tuple(complete)),
        "source_eligible_events": [row.payload() for row in eligible],
        "selected_source_ids": [row.source_event_id() for row in selected],
        "terminal_trade_rows": [row.payload() for row in complete],
        "owner_one_fill_per_market_ny_day": True,
        "cognitive_evaluation_consumed": False,
        "bid_ask_spread_measured": False,
        "commission_measured": False,
        "source_authority_status": "SOURCE_SUPPORTED_WITH_EXPLICIT_QORE_FILL_CONTAINMENTS",
        "sealed_7y_read": False,
        "research_only": True,
        "live_authorized": False,
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
