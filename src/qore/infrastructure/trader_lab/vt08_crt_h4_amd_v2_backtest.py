"""Source-bound economic replay for the executable VT-08 V2 subset.

The raw-OHLC executable subset is deliberately narrow: completed Candle-2 range
reversal, Candle-3 M15 FVG reach, CISD/protected swing, exact confirmation-close
limit, protected-swing stop, and the source-conditioned 2R target. Candle-2 cases
without causal directional context remain candidates rather than fake trades.

The source may show a wider repeating H4 cycle, but the operating scope is fixed:
Forex 01:00/05:00/09:00 New York and futures 02:00/06:00/10:00 New York.
Source-cycle anchors outside that scope are not research candidates for QORE.

SETUP and fill are distinct. A limit can fill only after its signal. Same-bar
stop/target ambiguity resolves stop-first as explicit operational containment.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    FOREX_H4_ANCHOR_HOURS,
    FUTURES_H4_ANCHOR_HOURS,
    METHODOLOGY_ID,
    METHODOLOGY_VERSION,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2TimingFamily,
    _protected_swing,
    methodology_fingerprint,
    timing_family_for_market,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_economic_replay.v4"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt08_crt_h4_amd_v2_evidence.v3"
_NY = ZoneInfo("America/New_York")

# Human Owner operating scope. These are New York H4 opening anchors, never
# automatic trades. Wider source-cycle anchors are intentionally excluded.
_FOREX_H4_ANCHOR_HOURS = FOREX_H4_ANCHOR_HOURS
_FUTURES_H4_ANCHOR_HOURS = FUTURES_H4_ANCHOR_HOURS


class Vt08CrtH4AmdV2BacktestError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def candle(self) -> Vt08CrtH4AmdV2Candle:
        return Vt08CrtH4AmdV2Candle(
            opened_at=self.opened_at,
            closed_at=self.closed_at,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
        )


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Candidate:
    scenario: Vt08CrtH4AmdV2Scenario
    anchor_opened_at: datetime
    h4_closes_at: datetime
    proposed_side: DemoTradingSetupSide
    signal_at: datetime
    entry_observation: Decimal
    protected_swing_extreme: Decimal
    cisd_level: Decimal
    source_bias_status: str
    source_wick_status: str
    prior_candle2_wick_status: str | None
    post_signal_h4_close_r: Decimal
    mfe_r: Decimal
    mae_r: Decimal
    automatic_setup: bool = False
    entry_price: Decimal | None = None
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    filled_at: datetime | None = None
    outcome: str | None = None
    result_r: Decimal | None = None
    same_bar_containment: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "scenario_candidate": self.scenario.value,
            "anchor_opened_at": _iso(self.anchor_opened_at),
            "h4_closes_at": _iso(self.h4_closes_at),
            "proposed_side": self.proposed_side.value,
            "signal_at": _iso(self.signal_at),
            "entry_observation": format(self.entry_observation, "f"),
            "protected_swing_extreme": format(self.protected_swing_extreme, "f"),
            "cisd_level": format(self.cisd_level, "f"),
            "source_bias_status": self.source_bias_status,
            "source_point_of_interest_status": (
                "causal-m15-fvg" if self.automatic_setup else "requires-source-poi-confirmation"
            ),
            "source_wick_status": (
                "source-formalized-c2-reference-boundary-sweep"
                if self.automatic_setup
                else self.source_wick_status
            ),
            "prior_candle2_wick_status": self.prior_candle2_wick_status,
            "automatic_setup": self.automatic_setup,
            "entry_price": None if self.entry_price is None else format(self.entry_price, "f"),
            "stop_price": None if self.stop_price is None else format(self.stop_price, "f"),
            "target_price": None if self.target_price is None else format(self.target_price, "f"),
            "filled_at": None if self.filled_at is None else _iso(self.filled_at),
            "outcome": self.outcome,
            "result_r": None if self.result_r is None else format(self.result_r, "f"),
            "same_bar_resolution": (
                "stop-first-operational-containment"
                if self.same_bar_containment
                else None
            ),
            "post_signal_h4_close_r_descriptive_only": format(
                self.post_signal_h4_close_r, "f"
            ),
            "mfe_r_descriptive_only": format(self.mfe_r, "f"),
            "mae_r_descriptive_only": format(self.mae_r, "f"),
            "post_signal_path_is_not_trade_result": True,
        }


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2SourceAudit:
    software_sha: str
    symbol: str
    provider_symbol_name: str
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    timing_family: Vt08CrtH4AmdV2TimingFamily
    eligible_anchor_windows: int
    missing_anchor_windows: int
    candidates: tuple[Vt08CrtH4AmdV2Candidate, ...]

    def payload(self) -> dict[str, object]:
        c2 = sum(
            item.scenario is Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2
            for item in self.candidates
        )
        c3 = sum(
            item.scenario is Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3
            for item in self.candidates
        )
        setups = tuple(item for item in self.candidates if item.automatic_setup)
        filled = tuple(item for item in setups if item.filled_at is not None)
        wins = sum(item.outcome == "target" for item in filled)
        losses = sum(item.outcome == "stop" for item in filled)
        censored = sum(item.outcome == "censored" for item in filled)
        total_r = sum((item.result_r or Decimal(0) for item in filled), Decimal(0))
        resolved = wins + losses
        peak = Decimal(0)
        equity = Decimal(0)
        max_drawdown = Decimal(0)
        loss_streak = 0
        max_loss_streak = 0
        for item in filled:
            equity += item.result_r or Decimal(0)
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
            if item.outcome == "stop":
                loss_streak += 1
                max_loss_streak = max(max_loss_streak, loss_streak)
            else:
                loss_streak = 0
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "source_fidelity_mode": True,
            "human_owner_operating_scope": True,
            "operating_timezone": "America/New_York",
            "forex_operating_h4_anchors": list(_FOREX_H4_ANCHOR_HOURS),
            "futures_operating_h4_anchors": list(_FUTURES_H4_ANCHOR_HOURS),
            "invalidates_prior_campaign": True,
            "prior_13468_campaign_valid_for_economics": False,
            "prior_16351_candidate_count_final_source_fidelity": False,
            "trader_code": "vt-08",
            "trader_version": "v2",
            "methodology": f"{METHODOLOGY_ID}-{METHODOLOGY_VERSION}",
            "methodology_id": METHODOLOGY_ID,
            "methodology_version": METHODOLOGY_VERSION,
            "methodology_fingerprint": methodology_fingerprint(),
            "symbol": self.symbol,
            "provider_symbol_name": self.provider_symbol_name,
            "software_sha": self.software_sha,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": _iso(self.checked_at),
            "timing_family": self.timing_family.value,
            "eligible_anchor_windows": self.eligible_anchor_windows,
            "missing_anchor_windows": self.missing_anchor_windows,
            "mechanical_candidate_count": len(self.candidates),
            "candle2_mechanical_candidate_count": c2,
            "candle3_mechanical_candidate_count": c3,
            "source_judgment_required_count": len(self.candidates) - len(setups),
            "automatic_setup_count": len(setups),
            "filled_count": len(filled),
            "unfilled_count": len(setups) - len(filled),
            "fill_rate": None if not setups else len(filled) / len(setups),
            "win_count": wins,
            "loss_count": losses,
            "censored_count": censored,
            "win_rate": None if not resolved else wins / resolved,
            "expectancy_r": None if not filled else format(total_r / len(filled), "f"),
            "total_r": format(total_r, "f"),
            "max_drawdown_r": format(max_drawdown, "f"),
            "max_consecutive_losses": max_loss_streak,
            "economic_backtest_authorized": True,
            "economic_profile": "c3-fvg-cisd-protected-swing-conditioned-2r",
            "candidate_semantics": (
                "mechanical prerequisites only inside Human Owner 3x3 New York "
                "operating windows; only the documented C3/FVG executable subset "
                "becomes SETUP; all other candidates remain non-economic"
            ),
            "candidates": [item.payload() for item in self.candidates],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be non-empty str")
    return value


def _timestamp(value: object, field: str) -> datetime:
    raw = _text(value, field)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, field: str) -> Decimal:
    raw = _text(value, field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be Decimal text") from error
    if not result.is_finite() or result <= 0:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be positive finite")
    return result


def _bar(raw: object) -> _Bar:
    row = _object(raw, "M15 bar")
    return _Bar(
        opened_at=_timestamp(row.get("opened_at"), "opened_at"),
        closed_at=_timestamp(row.get("closed_at"), "closed_at"),
        open=_decimal(row.get("open"), "open"),
        high=_decimal(row.get("high"), "high"),
        low=_decimal(row.get("low"), "low"),
        close=_decimal(row.get("close"), "close"),
    )


def _aggregate(bars: tuple[_Bar, ...]) -> Vt08CrtH4AmdV2Candle:
    if len(bars) != 16:
        raise Vt08CrtH4AmdV2BacktestError("source H4 requires exactly sixteen M15 bars")
    return Vt08CrtH4AmdV2Candle(
        opened_at=bars[0].opened_at,
        closed_at=bars[-1].closed_at,
        open=bars[0].open,
        high=max(item.high for item in bars),
        low=min(item.low for item in bars),
        close=bars[-1].close,
    )


def _exact_window(
    by_local_open: dict[datetime, _Bar],
    local_start: datetime,
) -> tuple[_Bar, ...] | None:
    result: list[_Bar] = []
    for offset in range(16):
        item = by_local_open.get(local_start + timedelta(minutes=15 * offset))
        if item is None:
            return None
        result.append(item)
    if any(
        current.opened_at != previous.closed_at
        for previous, current in zip(result, result[1:], strict=False)
    ):
        return None
    return tuple(result)


def _reversal_side(
    reference: Vt08CrtH4AmdV2Candle,
    signal: Vt08CrtH4AmdV2Candle,
) -> DemoTradingSetupSide | None:
    swept_high = signal.high > reference.high
    swept_low = signal.low < reference.low
    if swept_high == swept_low:
        return None
    if not reference.low < signal.close < reference.high:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def _causal_fvg_contains_confirmation(
    bars: tuple[_Bar, ...],
    *,
    confirmation_index: int,
    side: DemoTradingSetupSide,
) -> bool:
    """SF-02/SF-03: deterministic three-candle FVG visible by confirmation."""

    for index in range(2, confirmation_index):
        left = bars[index - 2]
        right = bars[index]
        if side is DemoTradingSetupSide.LONG:
            lower, upper = left.high, right.low
            exists = lower < upper
        else:
            lower, upper = right.high, left.low
            exists = lower < upper
        if exists and lower <= bars[confirmation_index].close <= upper:
            return True
    return False


def _replay_limit(
    path: tuple[_Bar, ...],
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[datetime | None, str | None, Decimal | None, bool]:
    """Fill after signal; conservatively resolve same-bar stop/target as stop."""

    filled_at: datetime | None = None
    for bar in path:
        if filled_at is None:
            if not bar.low <= entry <= bar.high:
                continue
            filled_at = bar.opened_at
        stop_hit = bar.low <= stop if side is DemoTradingSetupSide.LONG else bar.high >= stop
        target_hit = (
            bar.high >= target if side is DemoTradingSetupSide.LONG else bar.low <= target
        )
        if stop_hit and target_hit:
            return filled_at, "stop", Decimal(-1), True
        if stop_hit:
            return filled_at, "stop", Decimal(-1), False
        if target_hit:
            return filled_at, "target", Decimal(2), False
    if filled_at is None:
        return None, None, None, False
    return filled_at, "censored", Decimal(0), False


def _candidate_from_protected(
    *,
    scenario: Vt08CrtH4AmdV2Scenario,
    anchor: datetime,
    closes_at: datetime,
    current: tuple[_Bar, ...],
    side: DemoTradingSetupSide,
    required_run_level: Decimal | None,
    bias_status: str,
    prior_wick_status: str | None,
    executable_c3_profile: bool = False,
) -> Vt08CrtH4AmdV2Candidate | None:
    candles = tuple(item.candle() for item in current)
    protected = _protected_swing(
        candles,
        side=side,
        required_run_level=required_run_level,
    )
    if protected is None:
        return None
    confirmation, cisd_level, extreme = protected
    risk = (
        confirmation.close - extreme
        if side is DemoTradingSetupSide.LONG
        else extreme - confirmation.close
    )
    if risk <= 0:
        return None
    signal_index = next(
        (
            index
            for index, item in enumerate(current)
            if item.closed_at == confirmation.closed_at
        ),
        None,
    )
    if signal_index is None or signal_index + 1 >= len(current):
        return None
    path = current[signal_index + 1 :]
    if side is DemoTradingSetupSide.LONG:
        close_r = (path[-1].close - confirmation.close) / risk
        mfe = max((item.high - confirmation.close) / risk for item in path)
        mae = max((confirmation.close - item.low) / risk for item in path)
    else:
        close_r = (confirmation.close - path[-1].close) / risk
        mfe = max((confirmation.close - item.low) / risk for item in path)
        mae = max((item.high - confirmation.close) / risk for item in path)
    automatic = executable_c3_profile and _causal_fvg_contains_confirmation(
        current,
        confirmation_index=signal_index,
        side=side,
    )
    entry = confirmation.close if automatic else None
    stop = extreme if automatic else None
    target: Decimal | None = None
    filled_at: datetime | None = None
    outcome: str | None = None
    result_r: Decimal | None = None
    contained = False
    if entry is not None and stop is not None:
        target = entry + (risk * Decimal(2)) * (
            Decimal(1) if side is DemoTradingSetupSide.LONG else Decimal(-1)
        )
        filled_at, outcome, result_r, contained = _replay_limit(
            path,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
        )
    return Vt08CrtH4AmdV2Candidate(
        scenario=scenario,
        anchor_opened_at=anchor.astimezone(UTC),
        h4_closes_at=closes_at.astimezone(UTC),
        proposed_side=side,
        signal_at=confirmation.closed_at.astimezone(UTC),
        entry_observation=confirmation.close,
        protected_swing_extreme=extreme,
        cisd_level=cisd_level,
        source_bias_status=bias_status,
        source_wick_status="qualitative-unresolved-by-video",
        prior_candle2_wick_status=prior_wick_status,
        post_signal_h4_close_r=close_r,
        mfe_r=mfe,
        mae_r=mae,
        automatic_setup=automatic,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        filled_at=filled_at,
        outcome=outcome,
        result_r=result_r,
        same_bar_containment=contained,
    )


def _load(
    path: Path,
) -> tuple[str, str, str, str, datetime, tuple[_Bar, ...], str]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2BacktestError("cannot read VT-08 V2 evidence") from error
    payload = _object(decoded, "market evidence")
    if _text(payload.get("schema"), "schema") != _EVIDENCE_SCHEMA:
        raise Vt08CrtH4AmdV2BacktestError("unexpected VT-08 V2 evidence schema")
    if payload.get("environment") != "demo" or payload.get("read_only") is not True:
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must be read-only DEMO")
    if payload.get("account_is_live") is not False:
        raise Vt08CrtH4AmdV2BacktestError("LIVE evidence is prohibited")
    software_sha = _text(payload.get("software_sha"), "software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08CrtH4AmdV2BacktestError("software_sha must be exact Git SHA")
    account = _text(payload.get("account_fingerprint"), "account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise Vt08CrtH4AmdV2BacktestError("account fingerprint must be SHA-256")
    symbol = _text(payload.get("canonical_symbol"), "canonical_symbol")
    provider = _text(payload.get("provider_symbol_name"), "provider_symbol_name")
    checked_at = _timestamp(payload.get("checked_at"), "checked_at")
    periods = _object(payload.get("periods"), "periods")
    if set(periods) != {"M15"}:
        raise Vt08CrtH4AmdV2BacktestError("source-faithful V2 requires M15 evidence only")
    bars = tuple(_bar(item) for item in _array(periods.get("M15"), "M15"))
    if not bars or bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08CrtH4AmdV2BacktestError("M15 evidence must be chronological")
    identities = {(item.opened_at, item.closed_at) for item in bars}
    if len(identities) != len(bars):
        raise Vt08CrtH4AmdV2BacktestError("duplicate M15 evidence is prohibited")
    previous: _Bar | None = None
    for item in bars:
        if item.closed_at - item.opened_at != timedelta(minutes=15):
            raise Vt08CrtH4AmdV2BacktestError("wrong timeframe in M15 evidence")
        if item.closed_at > checked_at:
            raise Vt08CrtH4AmdV2BacktestError("future or open M15 evidence is prohibited")
        if previous is not None and item.opened_at < previous.closed_at:
            raise Vt08CrtH4AmdV2BacktestError("overlapping M15 evidence is prohibited")
        previous = item
    material = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return (
        software_sha,
        symbol,
        provider,
        account,
        checked_at,
        bars,
        sha256(material).hexdigest(),
    )


def run_vt08_v2_source_audit(path: Path) -> Vt08CrtH4AmdV2SourceAudit:
    software_sha, symbol, provider, account, checked_at, bars, evidence = _load(path)
    family = timing_family_for_market(symbol)
    if family is None:
        raise Vt08CrtH4AmdV2BacktestError("unsupported VT-08 owner-scope market")
    if family is Vt08CrtH4AmdV2TimingFamily.SOURCE_UNRESOLVED:
        return Vt08CrtH4AmdV2SourceAudit(
            software_sha,
            symbol,
            provider,
            account,
            evidence,
            checked_at,
            family,
            0,
            0,
            (),
        )
    anchor_hours = (
        _FUTURES_H4_ANCHOR_HOURS
        if family is Vt08CrtH4AmdV2TimingFamily.FUTURES
        else _FOREX_H4_ANCHOR_HOURS
    )
    by_local_open = {item.opened_at.astimezone(_NY): item for item in bars}
    local_dates = sorted({item.opened_at.astimezone(_NY).date() for item in bars})
    candidates: list[Vt08CrtH4AmdV2Candidate] = []
    eligible = 0
    missing = 0

    for local_day in local_dates:
        for hour in anchor_hours:
            anchor = datetime.combine(local_day, time(hour, 0), tzinfo=_NY)
            current = _exact_window(by_local_open, anchor)
            previous = _exact_window(by_local_open, anchor - timedelta(hours=4))
            previous2 = _exact_window(by_local_open, anchor - timedelta(hours=8))
            if current is None or previous is None:
                missing += 1
                continue
            eligible += 1
            reference = _aggregate(previous)

            long_c2 = _candidate_from_protected(
                scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
                anchor=anchor,
                closes_at=anchor + timedelta(hours=4),
                current=current,
                side=DemoTradingSetupSide.LONG,
                required_run_level=reference.low,
                bias_status="requires-source-context-confirmation",
                prior_wick_status=None,
            )
            short_c2 = _candidate_from_protected(
                scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
                anchor=anchor,
                closes_at=anchor + timedelta(hours=4),
                current=current,
                side=DemoTradingSetupSide.SHORT,
                required_run_level=reference.high,
                bias_status="requires-source-context-confirmation",
                prior_wick_status=None,
            )
            for item in (long_c2, short_c2):
                if item is not None:
                    candidates.append(item)

            if previous2 is None:
                continue
            pre_reference = _aggregate(previous2)
            candle2 = reference
            c3_side = _reversal_side(pre_reference, candle2)
            if c3_side is None:
                continue
            c3 = _candidate_from_protected(
                scenario=Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3,
                anchor=anchor,
                closes_at=anchor + timedelta(hours=4),
                current=current,
                side=c3_side,
                required_run_level=None,
                bias_status="completed-candle2-reversal-direction",
                prior_wick_status="large-required-but-qualitative-unresolved",
                executable_c3_profile=True,
            )
            if c3 is not None:
                candidates.append(c3)

    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.signal_at,
                item.scenario.value,
                item.proposed_side.value,
            ),
        )
    )
    return Vt08CrtH4AmdV2SourceAudit(
        software_sha=software_sha,
        symbol=symbol,
        provider_symbol_name=provider,
        account_fingerprint=account,
        evidence_fingerprint=evidence,
        checked_at=checked_at,
        timing_family=family,
        eligible_anchor_windows=eligible,
        missing_anchor_windows=missing,
        candidates=ordered,
    )


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: vt08_crt_h4_amd_v2_backtest <market-evidence.json>")
    print(run_vt08_v2_source_audit(Path(args[0])).to_json())


if __name__ == "__main__":
    main()
