"""Pre-registered one-mother-per-NY-day M30/M3 economic PROXY falsification.

STOP=QORE C protected swing, TARGET=C1 opposite extreme. Does not
reproduce authoritative TTrades EQ+breaker / valid HTF POI.  Native M3
OHLC only: conservative stop-first when M3 touches both levels, and
hypothetical cost sensitivity in R, NOT measured bid/ask/comissions.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    closed_source_window,
)
from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    evaluate as m30m3_source_geometry,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA = "qore.vt08.m30m3.one_mother_day.economic_proxy_falsification.v1"
COSTS_R = (Decimal("0"), Decimal("0.05"), Decimal("0.10"), Decimal("0.20"))


def first_mother_per_ny_day(
    observations: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Pre-entry selection; intentionally IGNORE retest future and outcomes."""
    found: dict[str, dict[str, object]] = {}
    for obs in observations:
        if obs["status"] != "M30_M3_SOURCE_GEOMETRY_ONLY":
            raise ValueError("only first source-complete MECHANICAL mother shapes")
        day, oid, start = (
            str(obs["market_ny_date"]),
            str(obs["origin_id"]),
            datetime.fromisoformat(str(obs["entry_positional_proposed_at"])),
        )
        if start.utcoffset() is None:
            raise ValueError("mother source date is not aware")
        old = found.get(day)
        if old is None or (start, oid) < (
            datetime.fromisoformat(str(old["entry_positional_proposed_at"])),
            str(old["origin_id"]),
        ):
            found[day] = obs
    return [found[x] for x in sorted(found)]


def _prices(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> Decimal:
    risk = entry-stop if side is DemoTradingSetupSide.LONG else stop-entry
    if risk <= 0:
        raise ValueError("stop must define strictly positive risk")
    gross_reward = (
        target-entry if side is DemoTradingSetupSide.LONG
        else entry-target
    )
    if gross_reward <= 0:
        raise ValueError("target must define strictly positive reward")
    return risk


def _events(
    *,
    side: DemoTradingSetupSide,
    bar: Vt08B01Bar,
    level: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[bool, bool, bool]:
    touch = bar.low <= level <= bar.high
    if side is DemoTradingSetupSide.LONG:
        return touch, bar.low <= stop, bar.high >= target
    return touch, bar.high >= stop, bar.low <= target


def _pnl_on_expiry(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    close: Decimal,
    risk: Decimal,
) -> Decimal:
    return (
        (close-entry)/risk if side is DemoTradingSetupSide.LONG
        else (entry-close)/risk
    )


def simulate_m30_window(
    *,
    side: DemoTradingSetupSide,
    entry_open: Decimal,
    limit: Decimal,
    stop: Decimal,
    target: Decimal,
    m3_window: tuple[Vt08B01Bar, ...],
) -> dict[str, object]:
    """Simulate mutually-exclusive paper COUNTERFACTUALS over same future bars.

    Terminal after ten exact consecutive native closed M3. Conservative
    STOP FIRST for ambiguous bar in either method; no bid/ask fills.
    """
    if len(m3_window) != 10:
        raise ValueError("need exactly 10 native M3 closed for one M30 window")
    if m3_window[0].open != entry_open:
        raise ValueError("positional entry must equal earliest C3 M3 open")
    cursor = m3_window[0].opened_at.astimezone(UTC)
    for bar in m3_window:
        if bar.opened_at.astimezone(UTC) != cursor:
            raise ValueError("future/missing M3 continuation")
        if bar.closed_at.astimezone(UTC) != cursor + timedelta(minutes=3):
            raise ValueError("invalid M3 candle duration")
        cursor = bar.closed_at.astimezone(UTC)

    risk = _prices(side=side, entry=entry_open, stop=stop, target=target)
    pos: dict[str, object] | None = None
    for bar in m3_window:
        _, hit_stop, hit_target = _events(
            side=side, bar=bar, level=entry_open, stop=stop, target=target,
        )
        if hit_stop:
            pos = {
                "status": "STOP_FIRST_BOTH_HIT" if hit_target else "STOP",
                "gross_r": "-1", "filled": True,
                "closed_at": bar.closed_at.isoformat(),
            }
            break
        if hit_target:
            reward = (target-entry_open if side is DemoTradingSetupSide.LONG
                      else entry_open-target)/risk
            pos = {"status": "TARGET", "gross_r": str(reward), "filled": True,
                   "closed_at": bar.closed_at.isoformat()}
            break
    if pos is None:
        pos = {
            "status": "EXPIRE_C3_CLOSE",
            "gross_r": str(_pnl_on_expiry(
                side=side, entry=entry_open, close=m3_window[-1].close,
                risk=risk,
            )),
            "filled": True, "closed_at": m3_window[-1].closed_at.isoformat(),
        }

    valid_limit = (
        stop < limit < entry_open < target
        if side is DemoTradingSetupSide.LONG
        else target < entry_open < limit < stop
    )
    if not valid_limit:
        ret: dict[str, object] = {
            "status": "NO_FAVORABLE_PREDECLARED_LIMIT",
            "gross_r": "0", "filled": False,
        }
    else:
        limit_risk = _prices(side=side, entry=limit, stop=stop, target=target)
        activated = False
        ret = {"status": "NO_FILL", "gross_r": "0", "filled": False}
        for bar in m3_window:
            touched, stopped, targeted = _events(
                side=side, bar=bar, level=limit, stop=stop, target=target,
            )
            if not activated and not touched:
                if stopped or targeted:
                    ret = {
                        "status": "NO_FILL_EXIT_BEFORE_LIMIT",
                        "gross_r": "0", "filled": False,
                    }
                    break
                continue
            first_fill_in_this_bar = not activated
            if first_fill_in_this_bar:
                activated = True
            if stopped or (first_fill_in_this_bar and touched and targeted):
                ret = {
                    "status": (
                        "AMBIGUOUS_TOUCH_STOP_FIRST"
                        if first_fill_in_this_bar and (stopped or targeted)
                        else "STOP"
                    ),
                    "gross_r": "-1", "filled": True,
                    "closed_at": bar.closed_at.isoformat(),
                }
                break
            if targeted:
                reward = (
                    target-limit if side is DemoTradingSetupSide.LONG
                    else limit-target
                )/limit_risk
                ret = {
                    "status": "TARGET", "gross_r": str(reward),
                    "filled": True, "closed_at": bar.closed_at.isoformat(),
                }
                break
        else:
            if activated:
                ret = {
                    "status": "EXPIRE_C3_CLOSE",
                    "gross_r": str(_pnl_on_expiry(
                        side=side, entry=limit,
                        close=m3_window[-1].close, risk=limit_risk,
                    )),
                    "filled": True,
                    "closed_at": m3_window[-1].closed_at.isoformat(),
                }
    return {"positional": pos, "cisd_limit": ret}


def _metrics(
    observations: list[dict[str, object]],
    *,
    cost: Decimal,
) -> dict[str, object]:
    signals = len(observations)
    filled = [o for o in observations if o["filled"]]
    gross = [Decimal(str(x["gross_r"])) for x in filled]
    net = [r-cost for r in gross]
    winners = sum(r > 0 for r in net)
    gains = sum((r for r in net if r > 0), Decimal(0))
    losses = -sum((r for r in net if r < 0), Decimal(0))
    pf = str(gains/losses) if losses else (
        "INF" if gains else None
    )
    equity = peak = drawdown = Decimal(0)
    for outcome in net:
        equity += outcome
        peak = max(peak, equity)
        drawdown = max(drawdown, peak-equity)
    return {
        "signals": signals,
        "filled_hypothetically": len(filled),
        "no_fill": signals-len(filled),
        "cost_assumption_per_fill_r": str(cost),
        "win_rate_on_fills": str(
            Decimal(winners)/len(filled) if filled else Decimal(0)
        ),
        "expectancy_net_r_per_filled": str(
            sum(net, Decimal(0))/len(filled) if filled else Decimal(0)
        ),
        "expectancy_net_r_per_signal_including_no_fills": str(
            sum(net, Decimal(0))/signals if signals else Decimal(0)
        ),
        "net_sum_r": str(sum(net, Decimal(0))),
        "profit_factor_net": pf,
        "max_peak_to_trough_dd_r": str(drawdown),
        "no_broker_cost_proof": True,
    }


def summarize_market(
    *,
    market: str,
    observations: list[dict[str, object]],
) -> dict[str, object]:
    mother = first_mother_per_ny_day(observations)
    per_year: dict[str, Counter[str]] = defaultdict(Counter)
    outcomes: list[dict[str, object]] = []
    for record in mother:
        day = str(record["market_ny_date"])
        per_year[day[:4]]["first_mothers"] += 1
        outputs = record["economic_proxy_results"]
        for mode in ("positional", "cisd_limit"):
            if outputs[mode]["filled"]:
                per_year[day[:4]][f"{mode}_hypothetical_fills"] += 1
        outcomes.append({
            "origin_id": record["origin_id"],
            "market_ny_date": day,
            "market": market,
            "entry_proposed_at": record["entry_positional_proposed_at"],
            "positional": outputs["positional"],
            "cisd_limit": outputs["cisd_limit"],
        })
    scenarios = {}
    for mode in ("positional", "cisd_limit"):
        data = [o[mode] for o in outcomes]
        scenarios[mode] = {str(c): _metrics(data, cost=c) for c in COSTS_R}
    return {
        "schema": SCHEMA,
        "market": market,
        "selection_policy": "EARLIEST_PRE-C3-OPEN_MOTHER_PER_NY_DAY_NO_FUTURE_RR_SELECTION",
        "mother_shapes_available": len(observations),
        "first_mothers_selected": len(mother),
        "results_per_year": {y: dict(v) for y,v in sorted(per_year.items())},
        "scenarios": scenarios,
        "first_mother_trade_receipts": outcomes,
        "author_TTrades_methodology_full": False,
        "source_PoI_and_EQ_breaker_validated": False,
        "broker_execution_physical": False,
        "cognition_full_used": False,
        "sealed_7y_accessed": False,
    }


def evaluate_market(base: Path, native_m3: Path) -> dict[str, object]:
    original = m30m3_source_geometry(base, native_m3)
    symbol = str(original["market"])
    native = _load_m3(native_m3, expected_symbol=symbol)
    m3_by_open = {b.opened_at:b for b in native}
    if len(m3_by_open) != len(native):
        raise ValueError("duplicate native M3 timestamps")
    parent = original["research_observations"]
    # Select *before* seeing any future C3 result. Do not use clean-touch
    # selection method: it biases to days that DID retrace.
    mothers = first_mother_per_ny_day(parent)
    prepared: list[dict[str, object]] = []
    for row in mothers:
        start = datetime.fromisoformat(
            str(row["entry_positional_proposed_at"])
        )
        window = closed_source_window(
            m3_by_open, begin=start, count=10, minutes=3,
        )
        if window is None:
            raise ValueError("original complete M3 C3 window disappeared")
        side = DemoTradingSetupSide(str(row["side"]))
        trial = simulate_m30_window(
            side=side, entry_open=Decimal(str(row["entry_positional_open"])),
            limit=Decimal(str(row["c2_m3_cisd_retest_level"])),
            stop=Decimal(str(row["c2_m3_ps_price"])),
            target=Decimal(str(row["opposite_c1_liquidity_target"])),
            m3_window=window,
        )
        prepared.append({
            **row,
            "economic_proxy_results": trial,
        })
    output = summarize_market(market=symbol, observations=prepared)
    if output["first_mothers_selected"] != len(mothers):
        raise AssertionError("mother signal denominator changed")
    return output


def aggregate_market_files(paths: list[Path]) -> dict[str, object]:
    all_events: list[dict[str, object]] = []
    markets: list[str] = []
    for p in paths:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if obj.get("schema") != SCHEMA:
            raise ValueError("economic proxy summary wrong schema")
        markets.append(str(obj["market"]))
        all_events.extend(obj["first_mother_trade_receipts"])
    if len(set(markets)) != len(markets):
        raise ValueError("market repeated in aggregated results")
    events = sorted(
        all_events,
        key=lambda x: (
            datetime.fromisoformat(x["entry_proposed_at"]).astimezone(UTC),
            x["market"],
            x["origin_id"],
        ),
    )
    return {
        "schema": SCHEMA,
        "markets": sorted(markets),
        "first_mother_market_day_signals": len(events),
        "scenarios": {
            mode: {
                str(cost): _metrics([r[mode] for r in events], cost=cost)
                for cost in COSTS_R
            }
            for mode in ("positional", "cisd_limit")
        },
        "time_order": "UTC_M30_OPEN_THEN_MARKET_AND_ORIGIN",
        "TTrades_author_complete": False,
        "stop_is_qore_PS_only_C_not_EQ_breaker": True,
        "POI_author_relevance_unverified": True,
        "bid_ask_and_real_commissions_unavailable": True,
        "PF_proxy_not_certification": True,
        "holdout_7y_accessed": False,
    }
