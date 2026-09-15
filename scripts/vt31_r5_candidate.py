"""Frozen VT-31 R5 Silver Bullet quality candidate replay.

This module is research/validation infrastructure. It does not authorize orders,
account access, position sizing, live trading, or production use.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _quartiles,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    Vt31R26Variant,
    _evaluate,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    _detect_raid,
    _session_bars,
    _structure,
    build_reference_range,
)

CANDIDATE_ID = "VT31_R5_SILVER_BULLET_QUALITY_001"
MARKETS = ("NAS100", "SP500", "US30")
NY = ZoneInfo("America/New_York")
FRICTION = Decimal("0.05")
BASE_VARIANT = Vt31R26Variant("near-stop")
MAX_SIGNAL_MINUTE = 15
MAX_RISK_TO_REFERENCE = Decimal("0.25")
MIN_CONFIRMATION_BODY_FRACTION = Decimal("0.50")
TARGET_R = Decimal(2)


def contract_payload() -> dict[str, object]:
    """Return the immutable R5 candidate contract."""
    return {
        "candidate_id": CANDIDATE_ID,
        "source_market": "NAS100",
        "owner_authorized_transfer_markets": ["SP500", "US30"],
        "identical_configuration_across_markets": True,
        "methodology_sources": [
            "youtube:o0v4KQxZbpU",
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
            "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/",
            "https://ttrades.com/protected-swings-and-cisd-how-to-trail-your-stop-loss/",
        ],
        "reference": "09:00-10:00-America/New_York",
        "setup_window": "10:00-11:00-America/New_York",
        "raid": "strict-first-side;both-sides-abstain",
        "confirmation": "R2.6-structural-close-v1",
        "entry_families": ["breaker", "fair-value-gap", "order-block"],
        "entry_selector": "nearest-still-valid-retracement-to-confirmation-close",
        "entry_zone_location": "near-stop",
        "pending_expiry": "11:00-America/New_York",
        "initial_stop": "raid-extreme-no-buffer",
        "target": "fixed-2R",
        "management": "M1-protected-swing-trail",
        "lifecycle": "16:00-America/New_York",
        "same_bar_policy": "censor-unknown-path",
        "gap_policy": "censor-trade",
        "qore_empirical_quality_containment": {
            "first_executable_setup_at_or_before": "10:15-America/New_York",
            "initial_risk_over_09_range_at_most": "0.25",
            "confirmation_direction_aligned": True,
            "confirmation_body_fraction_at_least": "0.50",
        },
        "friction_r_per_trade": "0.05",
        "minimum_aggregate_sample": 150,
        "minimum_sample_each_market": 30,
        "profit_factor_gate": ">=1.10",
        "max_drawdown_gate_r": "<=20",
        "quartile_gate": ">=3-of-4-positive",
        "market_gate": "every-market-stressed-mean-positive",
        "side_gate": "long-and-short-stressed-mean-positive",
        "temporal_gate": ">=2-of-3-eligible-blocks-positive",
        "monte_carlo": {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": ">=0.70",
            "p95_max_drawdown_r": "<=20",
        },
        "fresh_partition_end_exclusive": "2022-07-17T00:00:00+00:00",
        "fresh_requested_lookback_days": 760,
        "fresh_minimum_calendar_span_days": 730,
        "fresh_acquisition": "one-shot-after-freeze-and-exact-head-full-qore-green",
        "retuning_after_fresh": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def contract_fingerprint() -> str:
    payload = json.dumps(
        contract_payload(), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _touch(bar: object, price: Decimal) -> bool:
    low = _d(cast(float, getattr(bar, "low")))
    high = _d(cast(float, getattr(bar, "high")))
    return low <= price <= high


def _opposing(bar: object, side: str) -> bool:
    opened = _d(cast(float, getattr(bar, "open")))
    closed = _d(cast(float, getattr(bar, "close")))
    return closed < opened if side == "long" else closed > opened


def _new_protected_stop(
    candles: tuple[object, ...],
    index: int,
    side: str,
    current_stop: Decimal,
    current_close: Decimal,
) -> Decimal:
    if index < 2:
        return current_stop
    start = index - 1
    if not _opposing(candles[start], side):
        return current_stop
    while start > 0 and _opposing(candles[start - 1], side):
        start -= 1
    if start == 0:
        return current_stop
    series = candles[start:index]
    swept = (
        min(_d(cast(float, getattr(item, "low"))) for item in series)
        < _d(cast(float, getattr(candles[start - 1], "low")))
        if side == "long"
        else max(_d(cast(float, getattr(item, "high"))) for item in series)
        > _d(cast(float, getattr(candles[start - 1], "high")))
    )
    crossed = (
        _d(cast(float, getattr(candles[index], "close")))
        > _d(cast(float, getattr(series[0], "open")))
        if side == "long"
        else _d(cast(float, getattr(candles[index], "close")))
        < _d(cast(float, getattr(series[0], "open")))
    )
    if not swept or not crossed:
        return current_stop
    proposed = (
        min(_d(cast(float, getattr(item, "low"))) for item in series)
        if side == "long"
        else max(_d(cast(float, getattr(item, "high"))) for item in series)
    )
    if side == "long" and current_stop < proposed < current_close:
        return proposed
    if side == "short" and current_close < proposed < current_stop:
        return proposed
    return current_stop


def _quality(prefix: tuple[object, ...], setup: object, reference_width: Decimal) -> bool:
    instrument = getattr(prefix[0], "instrument")
    signal_at = getattr(setup, "signal_at")
    reference = build_reference_range(
        instrument=instrument,
        as_of=signal_at,
        bars=cast(object, prefix),
    )
    if reference is None:
        return False
    session = _session_bars(signal_at, cast(object, prefix))
    raid = _detect_raid(session, reference)
    if raid is None or (raid.high_taken and raid.low_taken):
        return False
    structure = _structure(session, raid)
    if structure is None:
        return False
    confirmation_index, _, _, _ = structure
    confirmation = session[confirmation_index]
    side = getattr(setup, "side").value
    opened = _d(confirmation.open)
    closed = _d(confirmation.close)
    high = _d(confirmation.high)
    low = _d(confirmation.low)
    span = high - low
    if span <= 0:
        return False
    aligned = closed > opened if side == "long" else closed < opened
    body_fraction = abs(closed - opened) / span
    risk = getattr(setup, "risk")
    local = signal_at.astimezone(NY)
    signal_minute = local.hour * 60 + local.minute - 10 * 60
    return (
        aligned
        and body_fraction >= MIN_CONFIRMATION_BODY_FRACTION
        and signal_minute <= MAX_SIGNAL_MINUTE
        and risk / reference_width <= MAX_RISK_TO_REFERENCE
    )


def _simulate(day_bars: tuple[object, ...], signal_index: int, setup: object) -> dict[str, object] | None:
    side = getattr(setup, "side").value
    entry = cast(Decimal, getattr(setup, "entry"))
    initial_stop = cast(Decimal, getattr(setup, "stop"))
    risk = abs(entry - initial_stop)
    if risk <= 0:
        return None
    target = entry + TARGET_R * risk if side == "long" else entry - TARGET_R * risk
    fill_index: int | None = None
    for index in range(signal_index + 1, len(day_bars)):
        bar = day_bars[index]
        if _wall(getattr(bar, "opened_at")) >= (11, 0, 0):
            break
        if index > signal_index + 1 and getattr(bar, "opened_at") != getattr(
            day_bars[index - 1], "closed_at"
        ):
            return None
        if _touch(bar, entry):
            fill_index = index
            break
    if fill_index is None:
        return None
    first = day_bars[fill_index]
    current_stop = initial_stop
    first_stop = (
        _d(cast(float, getattr(first, "low"))) <= current_stop
        if side == "long"
        else _d(cast(float, getattr(first, "high"))) >= current_stop
    )
    first_target = (
        _d(cast(float, getattr(first, "high"))) >= target
        if side == "long"
        else _d(cast(float, getattr(first, "low"))) <= target
    )
    if first_stop or first_target:
        return None
    terminal: Decimal | None = None
    exit_reason: str | None = None
    exit_at = None
    previous = first
    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        local = getattr(bar, "opened_at").astimezone(NY)
        if local.hour * 60 + local.minute >= 16 * 60:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return None
        previous = bar
        hit_stop = (
            _d(cast(float, getattr(bar, "low"))) <= current_stop
            if side == "long"
            else _d(cast(float, getattr(bar, "high"))) >= current_stop
        )
        hit_target = (
            _d(cast(float, getattr(bar, "high"))) >= target
            if side == "long"
            else _d(cast(float, getattr(bar, "low"))) <= target
        )
        if hit_stop and hit_target:
            return None
        if hit_stop:
            terminal = (
                (current_stop - entry) / risk
                if side == "long"
                else (entry - current_stop) / risk
            )
            exit_reason = "protected-stop"
            exit_at = getattr(bar, "closed_at")
            break
        if hit_target:
            terminal = TARGET_R
            exit_reason = "fixed-2r-target"
            exit_at = getattr(bar, "closed_at")
            break
        current_stop = _new_protected_stop(
            day_bars,
            index,
            side,
            current_stop,
            _d(cast(float, getattr(bar, "close"))),
        )
    if terminal is None:
        eligible = [
            item
            for item in day_bars
            if getattr(item, "opened_at").astimezone(NY).hour * 60
            + getattr(item, "opened_at").astimezone(NY).minute
            < 16 * 60
        ]
        if not eligible:
            return None
        final = eligible[-1]
        final_close = _d(cast(float, getattr(final, "close")))
        terminal = (
            (final_close - entry) / risk
            if side == "long"
            else (entry - final_close) / risk
        )
        exit_reason = "16:00-lifecycle"
        exit_at = getattr(final, "closed_at")
    signal_at = getattr(setup, "signal_at")
    filled_at = getattr(day_bars[fill_index], "closed_at")
    if filled_at < signal_at:
        raise ValueError("fill before decision is prohibited")
    return {
        "local_date": _day(signal_at).isoformat(),
        "side": side,
        "signal_at": signal_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": exit_at.astimezone(UTC).isoformat(),
        "entry": format(entry, "f"),
        "initial_stop": format(initial_stop, "f"),
        "target": format(target, "f"),
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
    }


def _monte_carlo(trades: list[dict[str, object]]) -> tuple[dict[str, object], dict[str, bool]]:
    values = [Decimal(cast(str, item["r_multiple"])) for item in trades]
    n = len(values)
    if n == 0:
        mc = {
            "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p05_terminal_r": "0",
            "p50_terminal_r": "0",
            "p95_max_drawdown_r": "0",
        }
        return mc, {
            "positive_terminal_probability_at_least_0_70": False,
            "p95_max_drawdown_at_most_20r": True,
        }
    domain = b"qore:vt31-r5:sha256-domain-separated-moving-block-bootstrap-v1"
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(values[(start + offset) % n] for offset in range(5))
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        dd = Decimal(0)
        for value in sampled[:n]:
            equity += value - FRICTION
            peak = max(peak, equity)
            dd = max(dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(dd)
    terminals.sort()
    drawdowns.sort()

    def quantile(values_: list[Decimal], numerator: int, denominator: int) -> Decimal:
        return values_[(len(values_) - 1) * numerator // denominator]

    probability = Decimal(sum(value > 0 for value in terminals)) / Decimal(10000)
    p95_dd = quantile(drawdowns, 95, 100)
    mc = {
        "algorithm": "sha256-domain-separated-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(probability, "f"),
        "p05_terminal_r": format(quantile(terminals, 5, 100), "f"),
        "p50_terminal_r": format(quantile(terminals, 50, 100), "f"),
        "p95_max_drawdown_r": format(p95_dd, "f"),
    }
    gates = {
        "positive_terminal_probability_at_least_0_70": probability >= Decimal("0.70"),
        "p95_max_drawdown_at_most_20r": p95_dd <= Decimal(20),
    }
    return mc, gates


def replay(evidence_paths: dict[str, Path]) -> dict[str, object]:
    """Replay the exact frozen R5 candidate over all three evidence files."""
    if set(evidence_paths) != set(MARKETS):
        raise ValueError("all and only NAS100, SP500, US30 evidence is required")
    trades: list[dict[str, object]] = []
    evidence_meta: list[dict[str, object]] = []
    for market in MARKETS:
        series, account, evidence, checked, evidence_sha, provider = load_market_evidence(
            evidence_paths[market]
        )
        evidence_meta.append(
            {
                "market": market,
                "account_fingerprint": account,
                "evidence_fingerprint": evidence,
                "checked_at": checked.astimezone(UTC).isoformat(),
                "evidence_software_sha": evidence_sha,
                "provider_symbol_name": provider,
                "bar_count": len(series),
                "first_opened_at": series[0].opened_at.astimezone(UTC).isoformat(),
                "last_closed_at": series[-1].closed_at.astimezone(UTC).isoformat(),
            }
        )
        by_day: dict[object, list[object]] = defaultdict(list)
        for bar in series:
            by_day[_day(bar.opened_at)].append(bar)
        for local_day in sorted(by_day):
            day_bars = tuple(by_day[local_day])
            reference = tuple(
                item
                for item in day_bars
                if (9, 0, 0) <= _wall(getattr(item, "opened_at")) < (10, 0, 0)
            )
            session = tuple(
                (index, item)
                for index, item in enumerate(day_bars)
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            if len(reference) != 60 or len(session) != 60:
                continue
            ref_high = max(_d(cast(float, getattr(item, "high"))) for item in reference)
            ref_low = min(_d(cast(float, getattr(item, "low"))) for item in reference)
            ref_width = ref_high - ref_low
            if ref_width <= 0:
                continue
            prefix = list(reference)
            selected = None
            selected_index: int | None = None
            for global_index, bar in session:
                prefix.append(bar)
                candidate, _ = _evaluate(
                    instrument=getattr(bar, "instrument"),
                    as_of=getattr(bar, "closed_at"),
                    bars=cast(object, tuple(prefix)),
                    variant=BASE_VARIANT,
                )
                if candidate is None:
                    continue
                if not _quality(tuple(prefix), candidate, ref_width):
                    break
                selected = candidate
                selected_index = global_index
                break
            if selected is None or selected_index is None:
                continue
            trade = _simulate(day_bars, selected_index, selected)
            if trade is None:
                continue
            trade["market"] = market
            trades.append(trade)
    trades.sort(key=lambda item: (cast(str, item["signal_at"]), cast(str, item["market"])))
    aggregate = _metrics(trades)
    stress = _metrics(trades, friction=FRICTION)
    market_stress = {
        market: _metrics(
            [item for item in trades if item["market"] == market], friction=FRICTION
        )
        for market in MARKETS
    }
    side_stress = {
        side: _metrics(
            [item for item in trades if item["side"] == side], friction=FRICTION
        )
        for side in ("long", "short")
    }
    quartiles = _quartiles(trades)
    temporal: dict[str, dict[str, object]] = {}
    for market in MARKETS:
        own = [item for item in trades if item["market"] == market]
        for year in sorted({cast(str, item["local_date"])[:4] for item in own}):
            temporal[f"{market}:{year}"] = _metrics(
                [
                    item
                    for item in own
                    if cast(str, item["local_date"]).startswith(year)
                ],
                friction=FRICTION,
            )
    eligible = [item for item in temporal.values() if cast(int, item["sample"]) >= 10]
    gates = {
        "aggregate_sample_at_least_150": cast(int, aggregate["sample"]) >= 150,
        "each_market_sample_at_least_30": all(
            cast(int, item["sample"]) >= 30 for item in market_stress.values()
        ),
        "aggregate_stressed_mean_positive": Decimal(cast(str, stress["mean_r"])) > 0,
        "aggregate_stressed_pf_at_least_1_10": stress["profit_factor"] is not None
        and Decimal(cast(str, stress["profit_factor"])) >= Decimal("1.10"),
        "aggregate_stressed_dd_at_most_20r": Decimal(
            cast(str, stress["max_drawdown_r"])
        )
        <= Decimal(20),
        "every_market_stressed_mean_positive": all(
            Decimal(cast(str, item["mean_r"])) > 0
            for item in market_stress.values()
        ),
        "both_sides_stressed_mean_positive": all(
            cast(int, item["sample"]) > 0 and Decimal(cast(str, item["mean_r"])) > 0
            for item in side_stress.values()
        ),
        "three_of_four_quartiles_positive": sum(
            Decimal(cast(str, item["mean_r"])) > 0 for item in quartiles
        )
        >= 3,
        "two_thirds_eligible_temporal_blocks_positive": bool(eligible)
        and sum(Decimal(cast(str, item["mean_r"])) > 0 for item in eligible) * 3
        >= len(eligible) * 2,
    }
    mc, mc_gates = _monte_carlo(trades)
    causal = {
        "incremental_predecision_evaluation": True,
        "no_fill_before_decision": all(
            cast(str, item["filled_at"]) >= cast(str, item["signal_at"]) for item in trades
        ),
        "deterministic_ordering": trades
        == sorted(
            trades,
            key=lambda item: (
                cast(str, item["signal_at"]),
                cast(str, item["market"]),
            ),
        ),
    }
    return {
        "schema": "qore.trader_lab.vt31_r5_candidate.v1",
        "candidate_id": CANDIDATE_ID,
        "contract": contract_payload(),
        "contract_fingerprint": contract_fingerprint(),
        "evidence": evidence_meta,
        "aggregate": aggregate,
        "stress_0_05r": stress,
        "market_stress": market_stress,
        "side_stress": side_stress,
        "quartiles": quartiles,
        "temporal_blocks": temporal,
        "gates": gates,
        "monte_carlo": mc,
        "monte_carlo_gates": mc_gates,
        "causal_checks": causal,
        "passes_economic_gates": all(gates.values()),
        "passes_monte_carlo_gates": all(mc_gates.values()),
        "passes_causal_checks": all(causal.values()),
        "trades": trades,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        print("usage: vt31_r5_candidate.py NAS100_JSON SP500_JSON US30_JSON")
        return 2
    paths = {market: Path(path) for market, path in zip(MARKETS, args, strict=True)}
    result = replay(paths)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
