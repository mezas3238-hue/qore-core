"""CIBO Phase-18 VT08 R3.15 legacy capital-policy reconstruction.

The certified R3.15 holdout retains exact B_COMBINED technical geometry but
does not persist per-trade R3.12 authorized Risk. This module reconstructs the
frozen pre-broker capital policy causally from the retained 124 trades.

No broker quantity, spread, commission, slippage, tick value or margin value is
invented. The economic unit is R25: USD risk equal to 25 bps of the frozen
$100k starting capital ($250). Provider/broker execution remains a later
calibration gate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

RISK_SOURCE_SHA = "6a09be314a5c8b6a17822ea141a41d521aaf8655"
RISK_ARTIFACT_ID = 10309794877
RISK_ARTIFACT_DIGEST = (
    "sha256:6b1ccbeac047b1d06d0b9eee7c24443d2ab03d7a9f33389dbc7ab34adba51d77"
)
HOLDOUT_SOURCE_SHA = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
HOLDOUT_ARTIFACT_ID = 10318827002
HOLDOUT_ARTIFACT_DIGEST = (
    "sha256:73aad16176f2f5335b47fff6510f8f3ce586e2d0a291dd6056c4d3c9e57f9ae4"
)
METHODOLOGY_FINGERPRINT = (
    "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
)
RISK_POLICY_FINGERPRINT = (
    "dfb3fc8217b9895356ed19f8d7e1ee47fae765d39a9bb2e72e14c4ac41fad1f5"
)
STARTING_EQUITY = Decimal("100000")
REFERENCE_RISK_BPS = Decimal("25")
REFERENCE_RISK_USD = STARTING_EQUITY * REFERENCE_RISK_BPS / Decimal(10_000)

A_BASE = Decimal("25")
GBPJPY_BASE = Decimal("20")
A_FLOOR = Decimal("10")
GBPJPY_FLOOR = Decimal("8")
A_CEILING = Decimal("30")
GBPJPY_CEILING = Decimal("25")
PORTFOLIO_HEAT = Decimal("90")
A_HEAT = Decimal("60")
GBPJPY_HEAT = Decimal("45")
CORRELATED_HEAT = Decimal("50")
INTERNAL_DAILY_GUARD = Decimal("200")
INTERNAL_DD_GUARD = Decimal("500")
PROVIDER_SAFETY_BUFFER = Decimal("10")
FULL_PROFIT_CUSHION = Decimal("0.10")
FULL_DD_BRAKE = Decimal("0.03")
HYSTERESIS = Decimal("0.25")
UPSHIFT = Decimal("0.50")
DOWNSHIFT = Decimal("5.00")

PROFILES = {
    "FUNDEDNEXT_STELLAR_2STEP_2026_09_12": {
        "timezone": "Europe/Athens",
        "daily_loss_fraction": Decimal("0.05"),
        "maximum_loss_fraction": Decimal("0.10"),
    },
    "FTMO_2STEP_2026_09_12": {
        "timezone": "Europe/Prague",
        "daily_loss_fraction": Decimal("0.05"),
        "maximum_loss_fraction": Decimal("0.10"),
    },
}
CANONICAL_PROFILE = "FUNDEDNEXT_STELLAR_2STEP_2026_09_12"


@dataclass(frozen=True, slots=True)
class LegacyTrade:
    signal_at: datetime
    exit_at: datetime
    symbol: str
    side: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    exit_reason: str
    raw_r: Decimal


@dataclass(slots=True)
class OpenRisk:
    exit_at: datetime
    symbol: str
    sleeve: str
    bounded_loss_usd: Decimal
    pnl_usd: Decimal


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def _sleeve(symbol: str, side: str) -> str:
    if side == "short" and symbol in {"AUDJPY", "GBPUSD"}:
        return "a"
    if symbol == "GBPJPY" and side in {"long", "short"}:
        return "gbpjpy"
    raise ValueError(f"trade outside frozen B_COMBINED: {symbol} {side}")


def _base(sleeve: str) -> Decimal:
    return A_BASE if sleeve == "a" else GBPJPY_BASE


def _floor(sleeve: str) -> Decimal:
    return A_FLOOR if sleeve == "a" else GBPJPY_FLOOR


def _ceiling(sleeve: str) -> Decimal:
    return A_CEILING if sleeve == "a" else GBPJPY_CEILING


def _sleeve_heat(sleeve: str) -> Decimal:
    return A_HEAT if sleeve == "a" else GBPJPY_HEAT


def _correlation_groups(symbol: str) -> tuple[str, ...]:
    groups: list[str] = []
    if "GBP" in symbol:
        groups.append("GBP")
    if "JPY" in symbol:
        groups.append("JPY")
    return tuple(groups)


def target_risk_bps(
    *,
    sleeve: str,
    equity: Decimal,
    peak_equity: Decimal,
) -> Decimal:
    if equity <= 0 or peak_equity <= 0:
        raise ValueError("equity inputs must be positive")
    base = _base(sleeve)
    floor = _floor(sleeve)
    ceiling = _ceiling(sleeve)
    cushion = max(Decimal(0), equity / STARTING_EQUITY - Decimal(1))
    cushion_progress = min(Decimal(1), cushion / FULL_PROFIT_CUSHION)
    up = (ceiling - base) * cushion_progress
    drawdown = max(Decimal(0), (peak_equity - equity) / peak_equity)
    brake_progress = min(Decimal(1), drawdown / FULL_DD_BRAKE)
    down = (base - floor) * brake_progress
    return min(ceiling, max(floor, base + up - down))


def apply_hysteresis(
    *,
    previous_bps: Decimal,
    target_bps_value: Decimal,
) -> Decimal:
    delta = target_bps_value - previous_bps
    if abs(delta) <= HYSTERESIS:
        return previous_bps
    if delta > 0:
        return min(target_bps_value, previous_bps + UPSHIFT)
    return max(target_bps_value, previous_bps - DOWNSHIFT)


def _raw_r(
    *,
    side: str,
    entry: Decimal,
    stop: Decimal,
    exit_price: Decimal,
) -> Decimal:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("technical risk must be positive")
    if side == "long":
        return (exit_price - entry) / risk
    if side == "short":
        return (entry - exit_price) / risk
    raise ValueError(f"unsupported side: {side}")


def _load_holdout(path: Path) -> tuple[dict[str, Any], list[LegacyTrade]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["schema"] != "qore.vt08.r3.15.final-independent-holdout.v1":
        raise ValueError("VT08 holdout schema drift")
    if payload["holdout_id"] != "VT08_R3_15_FINAL_INDEPENDENT_2020_2022":
        raise ValueError("VT08 holdout identity drift")
    if payload["software_sha"] != HOLDOUT_SOURCE_SHA:
        raise ValueError("VT08 holdout software SHA drift")
    if payload["methodology_fingerprint"] != METHODOLOGY_FINGERPRINT:
        raise ValueError("VT08 methodology fingerprint drift")
    if payload["portfolio"] != "B_COMBINED" or payload["sample_size"] != 124:
        raise ValueError("VT08 B_COMBINED population drift")

    rows: list[LegacyTrade] = []
    for source in payload["trades"]:
        signal_at = datetime.fromisoformat(str(source["signal_at"]))
        exit_at = datetime.fromisoformat(str(source["exited_at"]))
        if signal_at.tzinfo is None or exit_at.tzinfo is None:
            raise ValueError("VT08 timestamps must be timezone-aware")
        entry = _dec(source["entry"])
        stop = _dec(source["stop"])
        target = _dec(source["target"])
        exit_price = _dec(source["exit_price"])
        side = str(source["side"])
        risk = abs(entry - stop)
        target_r = (
            (target - entry) / risk
            if side == "long"
            else (entry - target) / risk
        )
        if target_r != Decimal(2):
            raise ValueError("VT08 frozen 2R target drift")
        rows.append(
            LegacyTrade(
                signal_at=signal_at,
                exit_at=exit_at,
                symbol=str(source["symbol"]),
                side=side,
                entry=entry,
                stop=stop,
                target=target,
                exit_price=exit_price,
                exit_reason=str(source["exit_reason"]),
                raw_r=_raw_r(
                    side=side,
                    entry=entry,
                    stop=stop,
                    exit_price=exit_price,
                ),
            )
        )
    rows.sort(key=lambda item: (item.signal_at, item.symbol, item.side))
    return payload, rows


def _verify_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["holdout_not_accessed"] is not True:
        raise ValueError("R3.12 holdout governance drift")
    if payload["risk_policy_fingerprint"] != RISK_POLICY_FINGERPRINT:
        raise ValueError("R3.12 risk policy fingerprint drift")
    policy = payload["primary_policy"]
    expected = {
        "name": "balanced-adaptive-v1",
        "a_base_bps": str(A_BASE),
        "gbpjpy_base_bps": str(GBPJPY_BASE),
        "a_floor_bps": str(A_FLOOR),
        "gbpjpy_floor_bps": str(GBPJPY_FLOOR),
        "a_ceiling_bps": str(A_CEILING),
        "gbpjpy_ceiling_bps": str(GBPJPY_CEILING),
        "portfolio_heat_bps": str(PORTFOLIO_HEAT),
        "a_sleeve_heat_bps": str(A_HEAT),
        "gbpjpy_sleeve_heat_bps": str(GBPJPY_HEAT),
        "correlated_heat_bps": str(CORRELATED_HEAT),
        "internal_daily_guard_bps": str(INTERNAL_DAILY_GUARD),
        "internal_peak_drawdown_guard_bps": str(INTERNAL_DD_GUARD),
        "provider_safety_buffer_bps": str(PROVIDER_SAFETY_BUFFER),
        "full_profit_cushion_fraction": str(FULL_PROFIT_CUSHION),
        "full_drawdown_brake_fraction": str(FULL_DD_BRAKE),
        "hysteresis_bps": str(HYSTERESIS),
        "upshift_step_bps": str(UPSHIFT),
        "downshift_step_bps": str(DOWNSHIFT),
    }
    for key, value in expected.items():
        if str(policy[key]) != value:
            raise ValueError(f"R3.12 policy drift: {key}")
    return payload


def _strategy_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [_dec(row["legacy_net_outcome_r25"]) for row in rows]
    positive = sum((v for v in values if v > 0), Decimal(0))
    negative = -sum((v for v in values if v < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(values),
        "profit_factor": None if negative == 0 else str(positive / negative),
        "total_r25": str(equity),
        "max_drawdown_r25_entry_order": str(dd),
        "max_losing_streak_entry_order": max_streak,
    }


def _simulate(
    trades: list[LegacyTrade],
    *,
    profile_id: str,
) -> dict[str, Any]:
    profile = PROFILES[profile_id]
    tz = ZoneInfo(str(profile["timezone"]))
    balance = STARTING_EQUITY
    peak = STARTING_EQUITY
    reset_balance = STARTING_EQUITY
    memory = {"a": A_BASE, "gbpjpy": GBPJPY_BASE}
    open_positions: list[OpenRisk] = []
    output: list[dict[str, Any]] = []
    realized_max_dd = Decimal(0)
    adverse_max_dd = Decimal(0)
    counts = {"ALLOW": 0, "REDUCE": 0, "REJECT": 0}

    first_local = trades[0].signal_at.astimezone(tz)
    current_day = first_local.date()
    next_reset = datetime.combine(
        current_day + timedelta(days=1),
        time.min,
        tzinfo=tz,
    ).astimezone(first_local.tzinfo)

    def close_due(cutoff: datetime) -> None:
        nonlocal balance, peak, realized_max_dd, open_positions
        due = sorted(
            (item for item in open_positions if item.exit_at <= cutoff),
            key=lambda item: item.exit_at,
        )
        for item in due:
            balance += item.pnl_usd
            peak = max(peak, balance)
            realized_max_dd = max(realized_max_dd, peak - balance)
        due_ids = {id(item) for item in due}
        open_positions = [
            item for item in open_positions if id(item) not in due_ids
        ]

    def advance(cutoff: datetime) -> None:
        nonlocal reset_balance, next_reset, current_day
        while next_reset <= cutoff:
            close_due(next_reset)
            reset_balance = balance
            current_day = next_reset.astimezone(tz).date()
            next_reset = datetime.combine(
                current_day + timedelta(days=1),
                time.min,
                tzinfo=tz,
            ).astimezone(next_reset.tzinfo)
        close_due(cutoff)

    for trade in trades:
        advance(trade.signal_at)
        sleeve = _sleeve(trade.symbol, trade.side)
        open_risk = sum(
            (item.bounded_loss_usd for item in open_positions),
            Decimal(0),
        )
        adverse_equity = balance - open_risk
        target = target_risk_bps(
            sleeve=sleeve,
            equity=adverse_equity,
            peak_equity=peak,
        )
        regime_bps = apply_hysteresis(
            previous_bps=memory[sleeve],
            target_bps_value=target,
        )
        memory[sleeve] = regime_bps

        safety = STARTING_EQUITY * PROVIDER_SAFETY_BUFFER / Decimal(10_000)
        daily_floor = (
            reset_balance
            - STARTING_EQUITY * _dec(profile["daily_loss_fraction"])
            + safety
        )
        maximum_floor = (
            STARTING_EQUITY
            * (Decimal(1) - _dec(profile["maximum_loss_fraction"]))
            + safety
        )
        internal_daily_floor = (
            reset_balance
            - STARTING_EQUITY * INTERNAL_DAILY_GUARD / Decimal(10_000)
        )
        internal_dd_floor = peak * (
            Decimal(1) - INTERNAL_DD_GUARD / Decimal(10_000)
        )
        sleeve_open = sum(
            item.bounded_loss_usd
            for item in open_positions
            if item.sleeve == sleeve
        )
        groups = set(_correlation_groups(trade.symbol))
        correlated_open = sum(
            item.bounded_loss_usd
            for item in open_positions
            if groups.intersection(_correlation_groups(item.symbol))
        )
        desired = balance * regime_bps / Decimal(10_000)
        limits = {
            "provider_daily": max(Decimal(0), adverse_equity - daily_floor),
            "provider_maximum": max(
                Decimal(0), adverse_equity - maximum_floor
            ),
            "internal_daily": max(
                Decimal(0), adverse_equity - internal_daily_floor
            ),
            "internal_drawdown": max(
                Decimal(0), adverse_equity - internal_dd_floor
            ),
            "portfolio_heat": max(
                Decimal(0),
                balance * PORTFOLIO_HEAT / Decimal(10_000) - open_risk,
            ),
            "sleeve_heat": max(
                Decimal(0),
                balance * _sleeve_heat(sleeve) / Decimal(10_000)
                - sleeve_open,
            ),
            "correlation_heat": max(
                Decimal(0),
                balance * CORRELATED_HEAT / Decimal(10_000)
                - correlated_open,
            ),
        }
        permitted = min([desired, *limits.values()])
        if permitted <= 0:
            counts["REJECT"] += 1
            raise ValueError(
                "VT08 legacy policy rejected a certified holdout opportunity; "
                "generic Phase-18 scorer cannot encode zero legacy risk"
            )
        reasons = tuple(
            sorted(
                name
                for name, value in limits.items()
                if value < desired
                and abs(value - permitted) <= Decimal("0.000001")
            )
        )
        reduced = permitted < desired
        counts["REDUCE" if reduced else "ALLOW"] += 1
        authorized_bps = permitted / balance * Decimal(10_000)
        pnl = permitted * trade.raw_r
        risk_scale_r25 = permitted / REFERENCE_RISK_USD
        net_r25 = pnl / REFERENCE_RISK_USD

        adverse_after = balance - (open_risk + permitted)
        adverse_max_dd = max(adverse_max_dd, peak - adverse_after)
        row = {
            "signal_at": trade.signal_at.isoformat(),
            "entry_at": trade.signal_at.isoformat(),
            "exit_at": trade.exit_at.isoformat(),
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": str(trade.entry),
            "structural_stop": str(trade.stop),
            "technical_target": str(trade.target),
            "exit_price": str(trade.exit_price),
            "exit_reason": trade.exit_reason,
            "raw_outcome_r": str(trade.raw_r),
            "legacy_regime_risk_bps": str(regime_bps),
            "legacy_authorized_risk_bps_pre_broker": str(authorized_bps),
            "legacy_risk_scale_r25": str(risk_scale_r25),
            "legacy_net_outcome_r25": str(net_r25),
            "legacy_bounded_loss_usd_pre_broker": str(permitted),
            "legacy_pnl_usd_zero_cost": str(pnl),
            "legacy_reduction_reasons": list(reasons),
            "profile_id": profile_id,
            "economics_status": "R_DENOMINATED_ONLY",
        }
        output.append(row)
        open_positions.append(
            OpenRisk(
                exit_at=trade.exit_at,
                symbol=trade.symbol,
                sleeve=sleeve,
                bounded_loss_usd=permitted,
                pnl_usd=pnl,
            )
        )

    if open_positions:
        advance(max(item.exit_at for item in open_positions))
    if open_positions:
        raise ValueError("VT08 policy replay left open positions")

    realized_total_r25 = (balance - STARTING_EQUITY) / REFERENCE_RISK_USD
    strategy = _strategy_metrics(output)
    if _dec(strategy["total_r25"]) != realized_total_r25:
        raise ValueError("VT08 capital accounting drift")

    return {
        "profile_id": profile_id,
        "rows": output,
        "risk_outcomes": counts,
        "ending_balance_usd": str(balance),
        "realized_total_r25": str(realized_total_r25),
        "realized_max_drawdown_r25": str(
            realized_max_dd / REFERENCE_RISK_USD
        ),
        "adverse_max_drawdown_r25": str(
            adverse_max_dd / REFERENCE_RISK_USD
        ),
        "entry_order_metrics": strategy,
    }


def replay(
    *,
    holdout_path: Path,
    risk_policy_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    holdout, trades = _load_holdout(holdout_path)
    _verify_policy(risk_policy_path)
    profiles = {
        profile_id: _simulate(trades, profile_id=profile_id)
        for profile_id in PROFILES
    }
    canonical = profiles[CANONICAL_PROFILE]
    risk_sequences_equal = (
        [
            row["legacy_authorized_risk_bps_pre_broker"]
            for row in profiles["FUNDEDNEXT_STELLAR_2STEP_2026_09_12"]["rows"]
        ]
        == [
            row["legacy_authorized_risk_bps_pre_broker"]
            for row in profiles["FTMO_2STEP_2026_09_12"]["rows"]
        ]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    trades_path = output_dir / "phase18-vt08-r315-fundednext-trades.jsonl"
    trades_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True) + "\n"
            for row in canonical["rows"]
        ),
        encoding="utf-8",
    )
    report: dict[str, Any] = {
        "schema": "qore.cibo.phase18.vt08_r315_policy_replay.v1",
        "identity": "CIBO_PHASE18_VT08_FOREX_R315_POLICY_REPLAY_V1",
        "status": (
            "CERTIFIED_GEOMETRY_AND_LEGACY_POLICY_RECONSTRUCTED_"
            "PROVIDER_EXECUTION_CALIBRATION_REQUIRED"
        ),
        "portfolio": "B_COMBINED",
        "rows": len(canonical["rows"]),
        "technical_geometry": {
            "methodology_fingerprint": METHODOLOGY_FINGERPRINT,
            "anchors_ny": [1, 5, 9],
            "entry": "CURRENT_NEW_H4_OPEN_EQUALS_SIGNAL_BOUNDARY",
            "stop": "PROTECTED_SWING",
            "target": "FIXED_2R",
            "lifecycle": "H4_BOUNDARY_CONTAINMENT",
            "holdout_reopened": False,
        },
        "legacy_capital_policy": {
            "policy": "balanced-adaptive-v1",
            "risk_policy_fingerprint": RISK_POLICY_FINGERPRINT,
            "risk_source_sha": RISK_SOURCE_SHA,
            "unit": "R25",
            "r25_usd_at_frozen_start": str(REFERENCE_RISK_USD),
            "broker_quantity_applied": False,
            "execution_cost_applied": False,
            "provider_profiles_replayed": list(PROFILES),
            "provider_risk_sequences_equal": risk_sequences_equal,
        },
        "canonical_profile": CANONICAL_PROFILE,
        "canonical_result": {
            key: value
            for key, value in canonical.items()
            if key != "rows"
        },
        "profile_diagnostics": {
            profile_id: {
                key: value
                for key, value in payload.items()
                if key != "rows"
            }
            for profile_id, payload in profiles.items()
        },
        "source_evidence": {
            "holdout_run_id": 34759027136,
            "holdout_artifact_id": HOLDOUT_ARTIFACT_ID,
            "holdout_artifact_digest": HOLDOUT_ARTIFACT_DIGEST,
            "holdout_source_sha": HOLDOUT_SOURCE_SHA,
            "risk_run_id": 34733491533,
            "risk_artifact_id": RISK_ARTIFACT_ID,
            "risk_artifact_digest": RISK_ARTIFACT_DIGEST,
            "risk_source_sha": RISK_SOURCE_SHA,
        },
        "provider_economics": {
            "status": "CALIBRATION_REQUIRED",
            "pre_broker_capital_policy_only": True,
            "usd_cibo_sizing_comparison_authorized": False,
        },
        "governance": {
            "consumed_holdout_only": True,
            "holdout_reopened": False,
            "methodology_changed": False,
            "research_only": True,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
        "certified_holdout_summary": {
            key: holdout[key]
            for key in (
                "sample_size",
                "wins",
                "losses",
                "flats",
                "profit_factor",
                "compounded_return",
                "maximum_drawdown",
                "max_losing_streak",
            )
        },
    }
    (output_dir / "phase18-vt08-r315-policy-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--risk-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(replay(
        holdout_path=args.holdout,
        risk_policy_path=args.risk_policy,
        output_dir=args.output,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
