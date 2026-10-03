#!/usr/bin/env python3
"""Augment the Architect-2 T02 causal dataset with VT31 native M1 context.

The M1 context is reconstructed only from retained NAS100 M1 bars whose
closed_at is <= the Phase22 market decision timestamp. Outcomes are attached
only as Y_OUTCOME labels after the predecision feature vector is frozen.
"""

from __future__ import annotations

import argparse
import bisect
import json
from datetime import timedelta
from decimal import Decimal, getcontext
from pathlib import Path
from zoneinfo import ZoneInfo

PRICE_SCALE = Decimal("100000")
NY = ZoneInfo("America/New_York")
DATASET_SCHEMA = "qore.cibo.t02-causal-dataset-arch2.v1"

getcontext().prec = 50


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal) -> str:
    return format(value, "f")


def parse_dt(value: str):
    from datetime import datetime

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def t02_decision(trace: dict[str, object]) -> dict[str, object] | None:
    ce2i = trace.get("ce2i")
    if not isinstance(ce2i, dict):
        return None
    raw = ce2i.get("opportunity_advanced_decisions")
    if not isinstance(raw, list):
        return None
    matches = [
        item
        for item in raw
        if isinstance(item, dict) and item.get("tool_code") == "T02"
    ]
    if len(matches) > 1:
        raise RuntimeError("multiple T02 decisions for one opportunity")
    return matches[0] if matches else None


def load_vt31_native(path: Path) -> dict[str, dict[str, object]]:
    payload = json.loads(path.read_text())
    if payload.get("trader_id") != "VT31_NAS100":
        raise RuntimeError("VT31 native artifact identity drift")
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list) or len(opportunities) != 67:
        raise RuntimeError("VT31 native artifact must contain 67 opportunities")
    out: dict[str, dict[str, object]] = {}
    for row in opportunities:
        if not isinstance(row, dict):
            raise RuntimeError("VT31 native opportunity must be object")
        fingerprint = str(row.get("signal_fingerprint") or "")
        if not fingerprint or fingerprint in out:
            raise RuntimeError("VT31 native signal fingerprint invalid/duplicate")
        out[fingerprint] = row
    return out


def load_m1(path: Path) -> tuple[list[dict[str, object]], list[object]]:
    rows: list[dict[str, object]] = []
    closed: list[object] = []
    previous = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if raw.get("canonical_symbol") != "NAS100":
            raise RuntimeError("M1 ledger contains non-NAS100 row")
        opened = parse_dt(str(raw["opened_at"]))
        closed_at = opened + timedelta(minutes=1)
        if previous is not None and opened <= previous:
            raise RuntimeError("M1 ledger chronology drift")
        previous = opened
        row = {
            "opened_at": opened,
            "closed_at": closed_at,
            "open": dec(raw["open_relative"]),
            "high": dec(raw["high_relative"]),
            "low": dec(raw["low_relative"]),
            "close": dec(raw["close_relative"]),
            "volume": None if raw.get("volume") is None else dec(raw["volume"]),
        }
        rows.append(row)
        closed.append(closed_at)
    if len(rows) != 158005:
        raise RuntimeError(f"expected 158005 retained M1 bars, got {len(rows)}")
    return rows, closed


def alignment(side: str, open_: Decimal, close: Decimal) -> str:
    delta = close - open_
    if delta == 0:
        return "flat"
    bullish = delta > 0
    same = (side == "long" and bullish) or (side == "short" and not bullish)
    return "same" if same else "opposed"


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator > 0 else Decimal(0)


def window(rows: list[dict[str, object]], end: int, count: int):
    return rows[max(0, end - count) : end]


def same_ny_date(row: dict[str, object], decision) -> bool:
    return row["opened_at"].astimezone(NY).date() == decision.astimezone(NY).date()


def m1_features(
    rows: list[dict[str, object]],
    closed: list[object],
    *,
    decision,
    side: str,
    entry_price: Decimal,
    stop_price: Decimal,
) -> dict[str, str]:
    end = bisect.bisect_right(closed, decision)
    history = rows[:end]
    if len(history) < 60:
        raise RuntimeError("insufficient closed M1 history before VT31 decision")

    last = history[-1]
    w5 = window(history, len(history), 5)
    w15 = window(history, len(history), 15)
    w60 = window(history, len(history), 60)

    last_range = dec(last["high"]) - dec(last["low"])
    last_body = dec(last["close"]) - dec(last["open"])
    avg60_range = sum(
        (dec(row["high"]) - dec(row["low"]) for row in w60),
        Decimal(0),
    ) / Decimal(len(w60))
    range5 = max(dec(row["high"]) for row in w5) - min(
        dec(row["low"]) for row in w5
    )
    range15 = max(dec(row["high"]) for row in w15) - min(
        dec(row["low"]) for row in w15
    )
    range60 = max(dec(row["high"]) for row in w60) - min(
        dec(row["low"]) for row in w60
    )
    close_now = dec(last["close"])
    ret5 = close_now - dec(w5[0]["open"])
    ret15 = close_now - dec(w15[0]["open"])
    position60 = safe_ratio(
        close_now - min(dec(row["low"]) for row in w60),
        range60,
    )

    local = decision.astimezone(NY)
    day = [
        row
        for row in history
        if same_ny_date(row, decision)
    ]
    reference = [
        row
        for row in day
        if (9, 0) <= (
            row["opened_at"].astimezone(NY).hour,
            row["opened_at"].astimezone(NY).minute,
        ) < (10, 0)
    ]
    if len(reference) != 60:
        raise RuntimeError("VT31 decision missing exact 60-bar 09:00-10:00 M1 reference")
    ref_high = max(dec(row["high"]) for row in reference)
    ref_low = min(dec(row["low"]) for row in reference)
    after_1000 = [
        row
        for row in day
        if (10, 0) <= (
            row["opened_at"].astimezone(NY).hour,
            row["opened_at"].astimezone(NY).minute,
        )
        and row["closed_at"] <= decision
    ]
    high_raid = any(dec(row["high"]) > ref_high for row in after_1000)
    low_raid = any(dec(row["low"]) < ref_low for row in after_1000)
    raid_state = (
        "both"
        if high_raid and low_raid
        else "high"
        if high_raid
        else "low"
        if low_raid
        else "none"
    )

    stop_distance_relative = abs(stop_price - entry_price) * PRICE_SCALE
    if stop_distance_relative <= 0:
        raise RuntimeError("VT31 stop distance must be positive")

    minutes_from_1000 = Decimal(
        (local.hour * 60 + local.minute) - 10 * 60
    )
    return {
        "reg_m1_last_body_alignment": alignment(
            side, dec(last["open"]), close_now
        ),
        "reg_m1_raid_state": raid_state,
        "m1_last_body_efficiency": fmt(
            safe_ratio(abs(last_body), last_range)
        ),
        "m1_last_range_to_60_avg": fmt(
            safe_ratio(last_range, avg60_range)
        ),
        "m1_range_5_to_60_avg": fmt(
            safe_ratio(range5, avg60_range)
        ),
        "m1_range_15_to_60_avg": fmt(
            safe_ratio(range15, avg60_range)
        ),
        "m1_return_5_in_60_avg_range": fmt(
            safe_ratio(ret5, avg60_range)
        ),
        "m1_return_15_in_60_avg_range": fmt(
            safe_ratio(ret15, avg60_range)
        ),
        "m1_position_in_60_range": fmt(position60),
        "m1_reference_range_width_in_stop_units": fmt(
            safe_ratio(ref_high - ref_low, stop_distance_relative)
        ),
        "m1_entry_to_reference_high_in_stop_units": fmt(
            safe_ratio(ref_high - entry_price * PRICE_SCALE, stop_distance_relative)
        ),
        "m1_entry_to_reference_low_in_stop_units": fmt(
            safe_ratio(entry_price * PRICE_SCALE - ref_low, stop_distance_relative)
        ),
        "m1_minutes_from_ny_1000": fmt(minutes_from_1000),
        "m1_closed_bar_count_predecision": str(end),
    }


def economics(trace: dict[str, object], realized_r: Decimal) -> dict[str, Decimal]:
    op = trace["trader_opportunity"]
    if not isinstance(op, dict):
        raise RuntimeError("trader opportunity missing")
    state = trace["market_predecision_state"]
    if not isinstance(state, dict):
        raise RuntimeError("market predecision state missing")
    provider = state["provider_observation"]
    if not isinstance(provider, dict):
        raise RuntimeError("provider observation missing")
    step = dec(op["volume_step"])
    extra_risk = step * dec(op["stop_loss_per_volume"])
    extra_margin = step * dec(op["margin_per_volume"])
    spread_per_volume = (
        (dec(provider["ask"]) - dec(provider["bid"]))
        / dec(provider["tick_size"])
        * dec(provider["tick_value"])
    )
    spread_cost = step * spread_per_volume
    commission_cost = step * dec(provider["commission_per_volume_usd"])
    slippage_cost = step * dec(provider["slippage_reserve_per_volume_usd"])
    provider_cost = spread_cost + commission_cost + slippage_cost
    gross = realized_r * extra_risk
    return {
        "extra_risk": extra_risk,
        "extra_margin": extra_margin,
        "spread_cost": spread_cost,
        "commission_cost": commission_cost,
        "slippage_cost": slippage_cost,
        "provider_cost": provider_cost,
        "gross": gross,
        "incremental": gross - provider_cost,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-causal-dataset", type=Path, required=True)
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--vt31-native", type=Path, required=True)
    parser.add_argument("--m1-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base_lines = [
        json.loads(line)
        for line in args.base_causal_dataset.read_text().splitlines()
        if line.strip()
    ]
    trace = json.loads(args.decision_trace.read_text())
    native = load_vt31_native(args.vt31_native)
    m1_rows, m1_closed = load_m1(args.m1_ledger)

    existing = {
        str(row["X_PREDECISION"]["signal_fingerprint"]) for row in base_lines
    }
    additions = []
    phase_rows = [
        row
        for row in trace["opportunities"]
        if row.get("trader_id") == "VT31_NAS100"
    ]
    if len(phase_rows) != 67:
        raise RuntimeError("Phase22 trace must contain 67 VT31 opportunities")

    for item in phase_rows:
        fingerprint = str(item["signal_fingerprint"])
        raw = native.get(fingerprint)
        if raw is None:
            raise RuntimeError(f"VT31 native match missing: {fingerprint}")
        if fingerprint in existing:
            raise RuntimeError("VT31 row already exists in base causal dataset")

        decision_at = parse_dt(str(item["market_decision_at"]))
        op = item["trader_opportunity"]
        side = str(op["side"])
        entry_price = dec(op["intended_entry"])
        stop_price = dec(op["stop_loss"])
        m1 = m1_features(
            m1_rows,
            m1_closed,
            decision=decision_at,
            side=side,
            entry_price=entry_price,
            stop_price=stop_price,
        )
        realized_r = dec(raw["realized_r"])
        econ = economics(item, realized_r)
        provider = item["market_predecision_state"]["provider_observation"]
        exp = item["expectation"]
        decision = t02_decision(item)
        selected = bool(
            (item.get("allocation") or {}).get("selected_by_cibo_policy")
        )
        applied = bool(
            decision and decision.get("disposition") == "APPLIED"
        )
        context = {
            "family": "SILVER_BULLET_M1",
            "target_route": "OPPOSITE_0900_1000_RANGE_BOUNDARY",
            "ctx_timeframe": "M1",
            "ctx_session": "NEW_YORK_AM",
            **m1,
        }
        x = {
            "signal_fingerprint": fingerprint,
            "trader_id_measurement_only": "VT31_NAS100",
            "symbol_measurement_only": "NAS100",
            "decision_timestamp": str(item["market_decision_at"]),
            "entry_timestamp": str(raw["entry_at"]),
            "side": side,
            "context": context,
            "expected_net_value_usd": fmt(dec(exp["expected_net_value_usd"])),
            "expected_capital_minutes": fmt(dec(exp["expected_capital_minutes"])),
            "pre_ce2i_stop_risk_usd": fmt(
                dec(item["cma"]["pre_ce2i_stop_risk_usd"])
            ),
            "pre_ce2i_margin_usd": fmt(dec(item["cma"]["pre_ce2i_margin_usd"])),
            "hard_risk_headroom_usd": fmt(
                dec(item["market_predecision_state"]["hard_risk_headroom_usd"])
            ),
            "margin_headroom_usd": fmt(
                dec(item["market_predecision_state"]["margin_headroom_usd"])
            ),
            "extra_step_stop_risk_usd": fmt(econ["extra_risk"]),
            "extra_step_margin_usd": fmt(econ["extra_margin"]),
            "provider_spread_cost_usd": fmt(econ["spread_cost"]),
            "provider_commission_cost_usd": fmt(econ["commission_cost"]),
            "provider_slippage_reserve_usd": fmt(econ["slippage_cost"]),
            "provider_total_cost_usd": fmt(econ["provider_cost"]),
            "provider_cost_to_extra_risk": fmt(
                econ["provider_cost"] / econ["extra_risk"]
                if econ["extra_risk"] > 0
                else Decimal("999")
            ),
            "core_selected_before_t02": selected,
            "current_t02_applied": applied,
            "current_t02_disposition": (
                None if decision is None else decision.get("disposition")
            ),
            "current_t02_reason": (
                None if decision is None else decision.get("reason")
            ),
            "provider_key": str(provider["provider_key"]),
            "provider_symbol": str(provider["provider_symbol"]),
        }
        y = {
            "raw_net_r": fmt(realized_r),
            "exit_reason": str(raw["exit_reason"]),
            "exit_timestamp": str(raw["exit_at"]),
            "one_step_gross_incremental_usd": fmt(econ["gross"]),
            "one_step_incremental_pnl_usd": fmt(econ["incremental"]),
        }
        additions.append(
            {
                "schema": DATASET_SCHEMA,
                "X_PREDECISION": x,
                "Y_OUTCOME": y,
            }
        )

    combined = sorted(
        [*base_lines, *additions],
        key=lambda row: row["X_PREDECISION"]["decision_timestamp"],
    )
    if len(combined) != 553:
        raise RuntimeError(f"expected 553 six-lineage causal rows, got {len(combined)}")
    selected_count = sum(
        bool(row["X_PREDECISION"]["core_selected_before_t02"]) for row in combined
    )
    if selected_count != 145:
        raise RuntimeError(
            f"expected 145 six-lineage Core-selected rows, got {selected_count}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in combined)
    )
    print(
        json.dumps(
            {
                "base_rows": len(base_lines),
                "vt31_m1_rows_added": len(additions),
                "combined_rows": len(combined),
                "core_selected_rows": selected_count,
                "m1_feature_keys": sorted(
                    key
                    for key in additions[0]["X_PREDECISION"]["context"]
                    if key.startswith("m1_") or key.startswith("reg_m1_")
                ),
                "outcome_used_for_m1_feature_construction": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
