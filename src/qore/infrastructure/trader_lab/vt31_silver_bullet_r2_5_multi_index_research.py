"""VT-31 R2.5 multi-index transfer research on the frozen AM configuration.

TTrades remains the methodology source and NQ/NAS100 remains the source market.
SP500 and US30 are Human Owner-authorized transfer research only.  The runner
applies identical New-York time, range, raid, structure, entry-zone, stop,
target, expiry, gap and same-bar semantics to every market.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
    _array,
    _canonical_evidence_fingerprint,
    _object,
    _snapshot,
    _strict_bool,
    _strict_int,
    _text,
    _timestamp,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    SOURCE_SHA256,
    SOURCE_VIDEO,
    Vt31R22EntryEvidence,
    Vt31R22EntryFamily,
    _detect_raid,
    _entry_evidence,
    _session_bars,
    _structure,
    _validate_evidence,
    build_reference_range,
)

SCHEMA = "qore.trader_lab.vt31_r2_5_multi_index_research.v1"
EVIDENCE_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
MARKETS = frozenset({"NAS100", "SP500", "US30"})
SOURCE_MARKET = "NAS100"
NY = ZoneInfo("America/New_York")
HYPOTHESIS_COUNT = 9


class Vt31R25ResearchError(Vt31SilverBulletV2BacktestError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt31R25Variant:
    family: Vt31R22EntryFamily
    location: str

    @property
    def variant_id(self) -> str:
        return f"{self.family.value}:{self.location}"

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.trader.vt31.r2.5.variant.v1",
            "source": SOURCE_VIDEO,
            "source_sha256": SOURCE_SHA256,
            "source_market": SOURCE_MARKET,
            "owner_transfer_markets": sorted(MARKETS),
            "reference": "09:00-10:00-America/New_York",
            "window": "10:00-11:00-America/New_York",
            "raid": "strict-first-side;both-sides-abstain",
            "confirmation": "structural-close-v1",
            "family": self.family.value,
            "zone_location": self.location,
            "stop": "raid-extreme-no-buffer",
            "target": "opposite-reference-boundary",
            "management": "3R-arms-breakeven",
            "pending_expiry": "11:00-America/New_York",
            "gap_policy": "censor",
            "same_bar_policy": "censor-unknown-path",
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


VARIANTS = tuple(
    Vt31R25Variant(family, location)
    for family in Vt31R22EntryFamily
    for location in ("near-stop", "midpoint", "near-target")
)


@dataclass(frozen=True, slots=True)
class _Setup:
    side: DemoTradingSetupSide
    signal_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    variant: Vt31R25Variant

    @property
    def risk(self) -> Decimal:
        return abs(self.stop - self.entry)

    @property
    def three_r(self) -> Decimal:
        if self.side is DemoTradingSetupSide.LONG:
            return self.entry + self.risk * Decimal(3)
        return self.entry - self.risk * Decimal(3)


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(NY)
    return local.hour, local.minute, local.second


def _day(value: datetime) -> date:
    return value.astimezone(NY).date()


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _touch(bar: OhlcSnapshot, price: Decimal) -> bool:
    return _d(bar.low) <= price <= _d(bar.high)


def load_market_evidence(
    path: Path,
) -> tuple[tuple[OhlcSnapshot, ...], str, str, datetime, str, str]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31R25ResearchError("cannot read VT-31 R2.5 evidence") from error
    payload = _object(decoded, field_name="VT-31 R2.5 evidence")
    if _text(payload.get("schema"), field_name="schema") != EVIDENCE_SCHEMA:
        raise Vt31R25ResearchError("unexpected VT-31 evidence schema")
    if _text(payload.get("environment"), field_name="environment") != "demo":
        raise Vt31R25ResearchError("evidence must be DEMO")
    if not _strict_bool(payload.get("read_only"), field_name="read_only"):
        raise Vt31R25ResearchError("evidence must be read-only")
    if _strict_bool(payload.get("account_is_live"), field_name="account_is_live"):
        raise Vt31R25ResearchError("LIVE evidence is prohibited")
    if not _strict_bool(
        payload.get("trading_permission_verified"),
        field_name="trading_permission_verified",
    ):
        raise Vt31R25ResearchError("DEMO permission must be verified")
    if _strict_int(
        payload.get("required_coverage_days"), field_name="required_coverage_days"
    ) < 730:
        raise Vt31R25ResearchError("evidence must require at least 730 days")
    if _text(
        payload.get("source_authorized_market"), field_name="source_authorized_market"
    ) != SOURCE_MARKET:
        raise Vt31R25ResearchError("TTrades source market must remain NAS100")
    symbol_payload = _object(payload.get("symbol"), field_name="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), field_name="symbol_name")
    if symbol not in MARKETS:
        raise Vt31R25ResearchError("unsupported Owner-authorized transfer market")
    owner_market = payload.get("owner_authorized_research_market", symbol)
    if owner_market != symbol:
        raise Vt31R25ResearchError("Owner-authorized market identity mismatch")
    provider = _text(
        payload.get("provider_symbol_name"), field_name="provider_symbol_name"
    )
    account = _text(
        payload.get("account_fingerprint"), field_name="account_fingerprint"
    )
    software_sha = _text(payload.get("software_sha"), field_name="software_sha")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise Vt31R25ResearchError("account fingerprint must be SHA-256")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt31R25ResearchError("software_sha must be exact Git SHA")
    checked_at = _timestamp(payload.get("checked_at"), field_name="checked_at")
    periods = _object(payload.get("periods"), field_name="periods")
    if set(periods) != {"M1"}:
        raise Vt31R25ResearchError("evidence must contain only M1")
    instrument = Instrument(symbol)
    snapshots = tuple(
        _snapshot(item, instrument=instrument)
        for item in _array(periods.get("M1"), field_name="period M1")
    )
    if not snapshots:
        raise Vt31R25ResearchError("M1 evidence is empty")
    if snapshots != tuple(sorted(snapshots, key=lambda item: item.opened_at)):
        raise Vt31R25ResearchError("M1 evidence is not chronological")
    identities = tuple((item.opened_at, item.closed_at) for item in snapshots)
    if len(set(identities)) != len(identities):
        raise Vt31R25ResearchError("M1 evidence contains duplicates")
    if snapshots[-1].closed_at - snapshots[0].opened_at < timedelta(days=730):
        raise Vt31R25ResearchError("M1 evidence span is below 730 days")
    if any(item.closed_at > checked_at for item in snapshots):
        raise Vt31R25ResearchError("future evidence is prohibited")
    coverage = _object(payload.get("coverage"), field_name="coverage")
    if _strict_int(coverage.get("bar_count"), field_name="coverage bar_count") != len(
        snapshots
    ):
        raise Vt31R25ResearchError("coverage count mismatch")
    return (
        snapshots,
        account,
        _canonical_evidence_fingerprint(payload),
        checked_at,
        software_sha,
        provider,
    )


def _entry(candidate: Vt31R22EntryEvidence, side: DemoTradingSetupSide, location: str) -> Decimal:
    if location == "midpoint":
        return (candidate.zone_lower + candidate.zone_upper) / Decimal(2)
    if location == "near-stop":
        return (
            candidate.zone_upper
            if side is DemoTradingSetupSide.SHORT
            else candidate.zone_lower
        )
    if location == "near-target":
        return (
            candidate.zone_lower
            if side is DemoTradingSetupSide.SHORT
            else candidate.zone_upper
        )
    raise Vt31R25ResearchError("unsupported zone location")


def _evaluate(
    *,
    instrument: Instrument,
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
    variant: Vt31R25Variant,
) -> tuple[_Setup | None, str]:
    _validate_evidence(instrument, as_of, bars)
    reference = build_reference_range(instrument=instrument, as_of=as_of, bars=bars)
    if reference is None:
        return None, "reference-incomplete"
    session = _session_bars(as_of, bars)
    raid = _detect_raid(session, reference)
    if raid is None:
        return None, "no-raid"
    if raid.high_taken and raid.low_taken:
        return None, "both-sides-swept"
    structure = _structure(session, raid)
    if structure is None:
        return None, "no-structure-confirmation"
    confirmation_index, extreme_index, extreme, _ = structure
    candidates = tuple(
        item
        for item in _entry_evidence(session, raid, confirmation_index, extreme_index)
        if item.family is variant.family
    )
    if not candidates:
        return None, "no-selected-entry-family"
    candidate = candidates[0]
    entry = _entry(candidate, raid.side, variant.location)
    target = reference.low if raid.side is DemoTradingSetupSide.SHORT else reference.high
    valid = (
        target < entry < extreme
        if raid.side is DemoTradingSetupSide.SHORT
        else extreme < entry < target
    )
    if not valid:
        return None, "invalid-geometry"
    return _Setup(raid.side, as_of.astimezone(UTC), entry, extreme, target, variant), "setup"


def _simulate(
    series: tuple[OhlcSnapshot, ...], signal_index: int, setup: _Setup
) -> tuple[dict[str, object] | None, str]:
    fill_index: int | None = None
    for index in range(signal_index + 1, len(series)):
        bar = series[index]
        if _day(bar.opened_at) != _day(setup.signal_at) or _wall(bar.opened_at) >= (
            11,
            0,
            0,
        ):
            return None, "pending-expired"
        if bar.opened_at != series[index - 1].closed_at:
            return None, "pending-gap"
        if _touch(bar, setup.entry):
            fill_index = index
            break
    if fill_index is None:
        return None, "pending-expired"
    breakeven_at: datetime | None = None
    outcome = "data-end-censored"
    result: Decimal | None = None
    resolved_at: datetime | None = None
    for index in range(fill_index, len(series)):
        bar = series[index]
        if index > fill_index and bar.opened_at != series[index - 1].closed_at:
            outcome = "data-gap-censored"
            resolved_at = series[index - 1].closed_at
            break
        stop = _touch(bar, setup.stop)
        target = _touch(bar, setup.target)
        three_r = _touch(bar, setup.three_r)
        if index == fill_index and (stop or target or three_r):
            outcome = "fill-bar-path-ambiguous"
            resolved_at = bar.closed_at
            break
        if breakeven_at is None:
            if stop and (target or three_r):
                outcome = "pre-be-path-ambiguous"
                resolved_at = bar.closed_at
                break
            if stop:
                outcome, result, resolved_at = "stop", Decimal(-1), bar.closed_at
                break
            if target:
                outcome = "target"
                result = abs(setup.target - setup.entry) / setup.risk
                resolved_at = bar.closed_at
                break
            if three_r:
                breakeven_at = bar.closed_at
            continue
        at_be = _touch(bar, setup.entry)
        if at_be and target:
            outcome = "post-be-path-ambiguous"
            resolved_at = bar.closed_at
            break
        if at_be:
            outcome, result, resolved_at = "breakeven", Decimal(0), bar.closed_at
            break
        if target:
            outcome = "target"
            result = abs(setup.target - setup.entry) / setup.risk
            resolved_at = bar.closed_at
            break
    return {
        "signal_at": setup.signal_at.isoformat(timespec="microseconds"),
        "filled_at": series[fill_index].closed_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "resolved_at": (
            resolved_at.astimezone(UTC).isoformat(timespec="microseconds")
            if resolved_at
            else None
        ),
        "local_date": _day(setup.signal_at).isoformat(),
        "side": setup.side.value,
        "entry": format(setup.entry, "f"),
        "stop": format(setup.stop, "f"),
        "target": format(setup.target, "f"),
        "planned_r": format(abs(setup.target - setup.entry) / setup.risk, "f"),
        "outcome": outcome,
        "r_multiple": format(result, "f") if result is not None else None,
        "breakeven_armed_at": (
            breakeven_at.astimezone(UTC).isoformat(timespec="microseconds")
            if breakeven_at
            else None
        ),
    }, "filled"


def _metrics(
    trades: list[dict[str, object]], *, friction: Decimal = Decimal(0)
) -> dict[str, object]:
    terminal = [item for item in trades if item["r_multiple"] is not None]
    values = [Decimal(cast(str, item["r_multiple"])) - friction for item in terminal]
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    losing = 0
    maximum_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        losing = losing + 1 if value < 0 else 0
        maximum_losing = max(maximum_losing, losing)
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": format(sum(values, Decimal(0)) / len(values), "f") if values else "0",
        "profit_factor": format(gains / losses, "f") if losses else None,
        "max_drawdown_r": format(drawdown, "f"),
        "max_losing_streak": maximum_losing,
    }


def _quartiles(trades: list[dict[str, object]]) -> list[dict[str, object]]:
    terminal = [item for item in trades if item["r_multiple"] is not None]
    result: list[dict[str, object]] = []
    for index in range(4):
        start = len(terminal) * index // 4
        end = len(terminal) * (index + 1) // 4
        result.append(_metrics(terminal[start:end]))
    return result


def run_research(path: Path) -> dict[str, object]:
    series, account, evidence, checked, software_sha, provider = load_market_evidence(path)
    instrument = series[0].instrument
    indexed_by_day: dict[date, list[tuple[int, OhlcSnapshot]]] = defaultdict(list)
    for index, bar in enumerate(series):
        indexed_by_day[_day(bar.opened_at)].append((index, bar))
    reports: dict[str, object] = {}
    for variant in VARIANTS:
        trades: list[dict[str, object]] = []
        abstains: Counter[str] = Counter()
        setups = 0
        for local_day in sorted(indexed_by_day):
            indexed = indexed_by_day[local_day]
            reference = tuple(
                bar for _, bar in indexed if (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
            )
            session = tuple(
                (index, bar)
                for index, bar in indexed
                if (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
            )
            if len(reference) != 60 or len(session) != 60:
                abstains["required-session-evidence-incomplete"] += 1
                continue
            prefix: list[OhlcSnapshot] = list(reference)
            selected: _Setup | None = None
            signal_index: int | None = None
            reason = "no-setup"
            for global_index, bar in session:
                prefix.append(bar)
                selected, reason = _evaluate(
                    instrument=instrument,
                    as_of=bar.closed_at,
                    bars=tuple(prefix),
                    variant=variant,
                )
                if selected is not None:
                    signal_index = global_index
                    break
                if reason == "both-sides-swept":
                    break
            if selected is None or signal_index is None:
                abstains[reason] += 1
                continue
            setups += 1
            trade, status = _simulate(series, signal_index, selected)
            if trade is None:
                abstains[status] += 1
            else:
                trades.append(trade)
        by_side = {
            side: _metrics([item for item in trades if item["side"] == side])
            for side in ("long", "short")
        }
        by_year = {
            year: _metrics(
                [item for item in trades if cast(str, item["local_date"]).startswith(year)]
            )
            for year in sorted({cast(str, item["local_date"])[:4] for item in trades})
        }
        reports[variant.variant_id] = {
            "fingerprint": variant.fingerprint(),
            "source_rule": False,
            "setup_count": setups,
            "fill_count": len(trades),
            "metrics": _metrics(trades),
            "stress_0_05r": _metrics(trades, friction=Decimal("0.05")),
            "stress_0_10r": _metrics(trades, friction=Decimal("0.10")),
            "by_side": by_side,
            "by_year": by_year,
            "quartiles": _quartiles(trades),
            "abstain_counts": dict(sorted(abstains.items())),
            "trades": trades,
        }
    return {
        "schema": SCHEMA,
        "research_only": True,
        "source": SOURCE_VIDEO,
        "source_sha256": SOURCE_SHA256,
        "source_market": SOURCE_MARKET,
        "owner_authorized_transfer_markets": sorted(MARKETS),
        "identical_configuration_across_markets": True,
        "hypothesis_count": HYPOTHESIS_COUNT,
        "market": instrument.symbol,
        "provider_symbol_name": provider,
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": account,
        "evidence_fingerprint": evidence,
        "checked_at": checked.astimezone(UTC).isoformat(timespec="microseconds"),
        "software_sha": software_sha,
        "candidate_frozen": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "variants": reports,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "vt31_silver_bullet_r2_5_multi_index_research PATH"
        )
        return 2
    try:
        report = run_research(Path(args[0]))
    except Vt31SilverBulletV2BacktestError as error:
        print(f"VT-31 R2.5 research failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
