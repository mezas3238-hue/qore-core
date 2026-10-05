"""VT31 NAS100 deep-giveback structural rescue frontier.

Consumed-evidence research only. The study leaves trade admission, entry,
initial stop and structural target unchanged. It evaluates one causal post-entry
mechanism: after meaningful favorable excursion has occurred, a confirmed M1
protective swing may improve the stop only when the journey has given most of
that progress back.

No sizing, leverage, compounding, capital weighting, absolute volume, terminal
PnL oracle, future journey label, or fresh holdout evidence is used.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

getcontext().prec = 34
NY = ZoneInfo("America/New_York")
MARKET = "NAS100"
FRICTION_R = Decimal("0.05")
MIN_MFE_R = Decimal("1.5")
MIN_CLOSE_GIVEBACK_R = Decimal("1.0")
MAX_PATH_EFFICIENCY = Decimal("0.10")
CURRENT_CLOSE_FRONTIER_R = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("0.75"),
    Decimal("1.00"),
)


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _minute_ny(value: str) -> int:
    local = _dt(value).astimezone(NY)
    return local.hour * 60 + local.minute


def _r_from_price(
    price: Decimal,
    *,
    entry: Decimal,
    risk: Decimal,
    side: str,
) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    if side == "short":
        return (entry - price) / risk
    raise ValueError(side)


def _touches_stop(
    bar: dict[str, object],
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(bar["low"]) <= level
    if side == "short":
        return _d(bar["high"]) >= level
    raise ValueError(side)


def _touches_target(
    bar: dict[str, object],
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(bar["high"]) >= level
    if side == "short":
        return _d(bar["low"]) <= level
    raise ValueError(side)


def _path_efficiency(
    bars: list[dict[str, object]],
    side: str,
) -> Decimal | None:
    if len(bars) < 2:
        return None
    closes = [_d(bar["close"]) for bar in bars]
    net = (
        closes[-1] - closes[0]
        if side == "long"
        else closes[0] - closes[-1]
    )
    gross = sum(
        (
            abs(right - left)
            for left, right in zip(closes, closes[1:], strict=False)
        ),
        Decimal(0),
    )
    return None if gross <= 0 else net / gross


def _features(
    path: list[dict[str, object]],
    index: int,
    *,
    entry: Decimal,
    risk: Decimal,
    side: str,
) -> dict[str, Decimal | None]:
    through = path[: index + 1]
    recent = through[-5:]
    close_rs = [
        _r_from_price(
            _d(bar["close"]),
            entry=entry,
            risk=risk,
            side=side,
        )
        for bar in through
    ]
    current_close_r = close_rs[-1]
    peak_close_r = max(close_rs)
    favorable_extremes = [
        _d(bar["high"]) if side == "long" else _d(bar["low"])
        for bar in through
    ]
    mfe_r = max(
        _r_from_price(
            price,
            entry=entry,
            risk=risk,
            side=side,
        )
        for price in favorable_extremes
    )
    return {
        "mfe_r": mfe_r,
        "current_close_r": current_close_r,
        "close_giveback_r": max(
            Decimal(0),
            peak_close_r - current_close_r,
        ),
        "path_efficiency": _path_efficiency(recent, side),
    }


def _qualifies(
    state: dict[str, Decimal | None],
    *,
    maximum_current_close_r: Decimal,
) -> bool:
    efficiency = state["path_efficiency"]
    return bool(
        state["mfe_r"] is not None
        and state["mfe_r"] >= MIN_MFE_R
        and state["close_giveback_r"] is not None
        and state["close_giveback_r"] >= MIN_CLOSE_GIVEBACK_R
        and state["current_close_r"] is not None
        and state["current_close_r"] <= maximum_current_close_r
        and efficiency is not None
        and efficiency <= MAX_PATH_EFFICIENCY
    )


def _reference_boundary(
    bars: list[dict[str, object]],
    side: str,
) -> tuple[Decimal, Decimal] | None:
    reference = [
        bar
        for bar in bars
        if 9 * 60 <= _minute_ny(str(bar["opened_at"])) < 10 * 60
    ]
    if len(reference) != 60:
        return None
    high = max(_d(bar["high"]) for bar in reference)
    low = min(_d(bar["low"]) for bar in reference)
    if side == "long":
        return high, high - low
    if side == "short":
        return low, high - low
    raise ValueError(side)


def _trade_path(
    bars: list[dict[str, object]],
    *,
    filled_at: datetime,
) -> list[dict[str, object]]:
    return [
        bar
        for bar in bars
        if _dt(str(bar["opened_at"])) >= filled_at
        and _minute_ny(str(bar["opened_at"])) < 16 * 60
    ]


def _baseline(
    path: list[dict[str, object]],
    *,
    side: str,
    entry: Decimal,
    stop: Decimal,
    risk: Decimal,
    boundary: Decimal,
) -> dict[str, object]:
    for index, bar in enumerate(path):
        stopped = _touches_stop(bar, side, stop)
        reached = _touches_target(bar, side, boundary)
        if stopped and reached:
            return {"status": "censored-same-bar-stop-dol1"}
        if reached:
            return {
                "status": "terminal",
                "r_multiple": format(abs(boundary - entry) / risk, "f"),
                "exit_reason": "DOL1",
                "exit_index": index,
            }
        if stopped:
            return {
                "status": "terminal",
                "r_multiple": "-1",
                "exit_reason": "INITIAL_STOP",
                "exit_index": index,
            }
    if not path:
        return {"status": "no-path"}
    return {
        "status": "terminal",
        "r_multiple": format(
            _r_from_price(
                _d(path[-1]["close"]),
                entry=entry,
                risk=risk,
                side=side,
            ),
            "f",
        ),
        "exit_reason": "LIFECYCLE",
        "exit_index": len(path) - 1,
    }


def _rescue(
    path: list[dict[str, object]],
    *,
    side: str,
    entry: Decimal,
    initial_stop: Decimal,
    risk: Decimal,
    boundary: Decimal,
    maximum_current_close_r: Decimal,
) -> dict[str, object]:
    current_stop = initial_stop
    pending: dict[int, list[Decimal]] = defaultdict(list)
    armed = 0
    qualifying_observations = 0
    rescue_committed = False

    for index, bar in enumerate(path):
        candidates = pending.pop(index, [])
        if candidates and not rescue_committed:
            proposed = (
                max(candidates)
                if side == "long"
                else min(candidates)
            )
            improves = (
                current_stop < proposed < boundary
                if side == "long"
                else boundary < proposed < current_stop
            )
            if improves:
                current_stop = proposed
                armed += 1
                rescue_committed = True

        stopped = _touches_stop(bar, side, current_stop)
        reached = _touches_target(bar, side, boundary)
        if stopped and reached:
            return {
                "status": "censored-same-bar-stop-dol1",
                "armed_count": armed,
                "qualifying_observations": qualifying_observations,
            }
        if reached:
            return {
                "status": "terminal",
                "r_multiple": format(abs(boundary - entry) / risk, "f"),
                "exit_reason": "DOL1",
                "exit_index": index,
                "armed_count": armed,
                "qualifying_observations": qualifying_observations,
            }
        if stopped:
            return {
                "status": "terminal",
                "r_multiple": format(
                    _r_from_price(
                        current_stop,
                        entry=entry,
                        risk=risk,
                        side=side,
                    ),
                    "f",
                ),
                "exit_reason": (
                    "DEEP_GIVEBACK_RESCUE_STOP"
                    if current_stop != initial_stop
                    else "INITIAL_STOP"
                ),
                "exit_index": index,
                "armed_count": armed,
                "qualifying_observations": qualifying_observations,
            }

        # A protective swing is known only after the right bar closes. The
        # candidate therefore becomes effective on the next M1 bar.
        if (
            not rescue_committed
            and not pending
            and 2 <= index < len(path) - 1
        ):
            left = path[index - 2]
            middle = path[index - 1]
            right = path[index]
            level: Decimal | None = None
            if side == "long":
                middle_low = _d(middle["low"])
                if (
                    middle_low < _d(left["low"])
                    and middle_low < _d(right["low"])
                ):
                    level = middle_low
            else:
                middle_high = _d(middle["high"])
                if (
                    middle_high > _d(left["high"])
                    and middle_high > _d(right["high"])
                ):
                    level = middle_high
            if level is not None:
                improves = (
                    current_stop < level < boundary
                    if side == "long"
                    else boundary < level < current_stop
                )
                if improves:
                    state = _features(
                        path,
                        index,
                        entry=entry,
                        risk=risk,
                        side=side,
                    )
                    if _qualifies(
                        state,
                        maximum_current_close_r=maximum_current_close_r,
                    ):
                        qualifying_observations += 1
                        pending[index + 1].append(level)

    if not path:
        return {"status": "no-path"}
    return {
        "status": "terminal",
        "r_multiple": format(
            _r_from_price(
                _d(path[-1]["close"]),
                entry=entry,
                risk=risk,
                side=side,
            ),
            "f",
        ),
        "exit_reason": "LIFECYCLE",
        "exit_index": len(path) - 1,
        "armed_count": armed,
        "qualifying_observations": qualifying_observations,
    }


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["r_multiple"]) - FRICTION_R for row in rows]
    if not values:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "mean_r": None,
            "total_r": "0",
            "profit_factor": None,
            "max_drawdown_r": "0",
            "payoff_ratio": None,
        }
    total = sum(values, Decimal(0))
    gross_profit = sum(
        (value for value in values if value > 0),
        Decimal(0),
    )
    gross_loss = -sum(
        (value for value in values if value < 0),
        Decimal(0),
    )
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    wins = [value for value in values if value > 0]
    losses = [-value for value in values if value < 0]
    payoff = None
    if wins and losses:
        payoff = (
            sum(wins, Decimal(0)) / Decimal(len(wins))
        ) / (
            sum(losses, Decimal(0)) / Decimal(len(losses))
        )
    return {
        "sample": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "mean_r": format(total / Decimal(len(values)), "f"),
        "total_r": format(total, "f"),
        "profit_factor": (
            None
            if gross_loss == 0
            else format(gross_profit / gross_loss, "f")
        ),
        "max_drawdown_r": format(max_dd, "f"),
        "payoff_ratio": (
            None if payoff is None else format(payoff, "f")
        ),
    }


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    base = {
        str(row["trade_id"]): _d(row["r_multiple"]) - FRICTION_R
        for row in baseline
    }
    cand = {
        str(row["trade_id"]): _d(row["r_multiple"]) - FRICTION_R
        for row in candidate
    }
    winners = {
        key: value for key, value in base.items()
        if value > 0
    }
    if not winners:
        return {
            "baseline_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
        }
    preserved = sum(
        key in cand and cand[key] > 0
        for key in winners
    )
    base_r = sum(winners.values(), Decimal(0))
    cand_r = sum(
        (
            max(cand.get(key, Decimal(0)), Decimal(0))
            for key in winners
        ),
        Decimal(0),
    )
    return {
        "baseline_winner_count": len(winners),
        "winner_count_preservation": format(
            Decimal(preserved) / Decimal(len(winners)),
            "f",
        ),
        "winner_r_preservation": format(
            cand_r / base_r,
            "f",
        ),
    }


def _halfyear(local_date: str) -> str:
    year, month = (
        int(value)
        for value in local_date.split("-")[:2]
    )
    return f"{year}H{1 if month <= 6 else 2}"


def _group_metrics(
    rows: list[dict[str, object]],
    key: str,
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = (
            _halfyear(str(row["local_date"]))
            if key == "halfyear"
            else str(row[key])
        )
        grouped[value].append(row)
    return {
        name: _metrics(items)
        for name, items in sorted(grouped.items())
    }


def replay(
    evidence_path: Path,
    replay_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    replay_payload = json.loads(
        replay_path.read_text(encoding="utf-8")
    )
    source_trades = [
        row
        for row in replay_payload["trades"]
        if row.get("market") == MARKET
    ]
    dates = {
        str(row["local_date"])
        for row in source_trades
    }
    evidence = json.loads(
        evidence_path.read_text(encoding="utf-8")
    )
    by_day: dict[str, list[dict[str, object]]] = defaultdict(list)
    for bar in evidence["periods"]["M1"]:
        local = _dt(str(bar["opened_at"])).astimezone(NY)
        local_date = local.date().isoformat()
        if local_date in dates and 9 <= local.hour <= 16:
            by_day[local_date].append(bar)

    variants: dict[str, list[dict[str, object]]] = {
        "BASELINE": [],
        **{
            (
                "DGR_CURRENT_CLOSE_MAX_"
                + format(threshold, "f").replace(".", "_")
            ): []
            for threshold in CURRENT_CLOSE_FRONTIER_R
        },
    }
    status: Counter[str] = Counter()
    variant_armed: Counter[str] = Counter()

    for trade in source_trades:
        local_date = str(trade["local_date"])
        bars = by_day.get(local_date, [])
        side = str(trade["side"])
        entry = _d(trade["entry"])
        initial_stop = _d(trade["initial_stop"])
        risk = abs(entry - initial_stop)
        if risk <= 0:
            status["invalid-risk"] += 1
            continue
        reference = _reference_boundary(bars, side)
        if reference is None:
            status["missing-reference"] += 1
            continue
        dol1, reference_width = reference
        path = _trade_path(
            bars,
            filled_at=_dt(str(trade["filled_at"])),
        )
        trade_id = (
            f"{partition}|{local_date}|"
            f"{trade['signal_at']}|{side}"
        )
        baseline = _baseline(
            path,
            side=side,
            entry=entry,
            stop=initial_stop,
            risk=risk,
            boundary=dol1,
        )
        if baseline["status"] != "terminal":
            status[f"baseline:{baseline['status']}"] += 1
            continue
        base_row = {
            **baseline,
            "trade_id": trade_id,
            "local_date": local_date,
            "side": side,
            "reference_width": format(reference_width, "f"),
            "initial_risk_points": format(risk, "f"),
        }
        variants["BASELINE"].append(base_row)

        for threshold in CURRENT_CLOSE_FRONTIER_R:
            name = (
                "DGR_CURRENT_CLOSE_MAX_"
                + format(threshold, "f").replace(".", "_")
            )
            candidate = _rescue(
                path,
                side=side,
                entry=entry,
                initial_stop=initial_stop,
                risk=risk,
                boundary=dol1,
                maximum_current_close_r=threshold,
            )
            if candidate["status"] != "terminal":
                status[f"{name}:{candidate['status']}"] += 1
                continue
            row = {
                **candidate,
                "trade_id": trade_id,
                "local_date": local_date,
                "side": side,
                "reference_width": format(reference_width, "f"),
                "initial_risk_points": format(risk, "f"),
            }
            variants[name].append(row)
            if int(candidate.get("armed_count", 0)) > 0:
                variant_armed[name] += 1

    baseline_rows = variants["BASELINE"]
    reports: dict[str, object] = {}
    for name, rows in variants.items():
        reports[name] = {
            "metrics": _metrics(rows),
            "side_metrics": _group_metrics(rows, "side"),
            "halfyear_metrics": _group_metrics(rows, "halfyear"),
            "winner_preservation": (
                None
                if name == "BASELINE"
                else _winner_preservation(
                    baseline_rows,
                    rows,
                )
            ),
            "armed_trade_count": variant_armed[name],
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"])
                        for row in rows
                    ).items()
                )
            ),
        }

    return {
        "schema": (
            "qore.vt31.nas100."
            "deep_giveback_rescue_frontier.v1"
        ),
        "partition": partition,
        "market": MARKET,
        "rule_family": {
            "minimum_observed_mfe_r": format(MIN_MFE_R, "f"),
            "minimum_peak_close_giveback_r": format(
                MIN_CLOSE_GIVEBACK_R,
                "f",
            ),
            "maximum_recent_path_efficiency": format(
                MAX_PATH_EFFICIENCY,
                "f",
            ),
            "current_close_frontier_r": [
                format(value, "f")
                for value in CURRENT_CLOSE_FRONTIER_R
            ],
            "protection_source": (
                "confirmed-m1-protective-swing"
            ),
            "protection_effective": "next-m1-bar-only",
            "initial_stop_widening": False,
            "maximum_rescue_moves_per_trade": 1,
            "structural_target": (
                "opposite-frozen-09-reference-boundary"
            ),
        },
        "source_binding": {
            "candidate_id": replay_payload.get("candidate_id"),
            "contract_fingerprint": replay_payload.get(
                "contract_fingerprint"
            ),
            "account_fingerprint": evidence.get(
                "account_fingerprint"
            ),
            "evidence_software_sha": evidence.get("software_sha"),
            "provider_symbol_name": evidence.get(
                "provider_symbol_name"
            ),
        },
        "source_nas100_trade_count": len(source_trades),
        "variant_reports": reports,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "single_structural_rescue_move_max": True,
            "structural_target_changed": False,
            "terminal_pnl_runtime_input": False,
            "future_journey_runtime_input": False,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "absolute_volume_used": False,
            "opens_new_holdout": False,
            "automatic_variant_promotion": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = replay(
        args.evidence,
        args.replay,
        partition=args.partition,
    )
    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "source_nas100_trade_count": payload[
                    "source_nas100_trade_count"
                ],
                "variant_reports": payload["variant_reports"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
