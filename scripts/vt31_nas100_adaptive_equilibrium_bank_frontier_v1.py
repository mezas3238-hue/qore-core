"""Adaptive equilibrium bank frontier for VT31_NAS100.

Development-only economic falsification.

Uses only causal features available at the CLOSE of the first M1 touching the
frozen reference equilibrium. Decision becomes effective from the next M1.

Stable 4/4 continuation signals from Equilibrium Continuation Forensics V1:
- EQ bar closes beyond equilibrium;
- EQ bar closes beyond + last5 path efficiency >= 0.75;
- EQ bar closes beyond + giveback < 0.10R;
- EQ bar body fraction >= 0.75;
- cash-open state rotation.

Policies under test:
- ACCEPT_STRICT: strict acceptance pair (close beyond + path efficiency >=.75)
- ACCEPT_CORE: close beyond + low giveback
- ACCEPT_ANY: any stable continuation-enriched singleton

Bank logic:
- continuation state: bank 0% or 25% at EQ;
- non-continuation state: bank 50% at EQ;
- remainder preserves the original trade terminal outcome.

EQ bank is credited only when EQ is touched on a strictly earlier closed M1
than the original terminal bar. No same-bar credit.
No stop widening, no target replacement, no future label at runtime.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_equilibrium_continuation_forensics_v1 as eqf
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.adaptive_equilibrium_bank_frontier.v1"
MARKET = "NAS100"
EXTRA_PARTIAL_FRICTION_R = Decimal("0.005")

VARIANTS = {
    "BASE": None,
    "STRICT_CONT0_EXHAUST50": ("STRICT", Decimal("0"), Decimal("0.50")),
    "STRICT_CONT25_EXHAUST50": ("STRICT", Decimal("0.25"), Decimal("0.50")),
    "CORE_CONT0_EXHAUST50": ("CORE", Decimal("0"), Decimal("0.50")),
    "CORE_CONT25_EXHAUST50": ("CORE", Decimal("0.25"), Decimal("0.50")),
    "ANY_CONT25_EXHAUST50": ("ANY", Decimal("0.25"), Decimal("0.50")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _forward(*, side: str, entry: Decimal, level: Decimal) -> bool:
    return level > entry if side == "long" else level < entry


def _touches(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _continuation_signal(
    snapshot: dict[str, object],
    row: dict[str, object],
    *,
    mode: str,
) -> bool:
    close_beyond = bool(snapshot["eq_bar_close_beyond"])
    path_bucket = str(snapshot["eq_last5_path_efficiency_bucket"])
    giveback_bucket = str(snapshot["eq_close_giveback_bucket"])
    body_bucket = str(snapshot["eq_bar_body_bucket"])

    if mode == "STRICT":
        return close_beyond and path_bucket == "ge_0_75"
    if mode == "CORE":
        return close_beyond and giveback_bucket == "lt_0_10R"
    if mode == "ANY":
        return (
            close_beyond
            or body_bucket == "ge_0_75"
            or row.get("cash_open_state") == "rotation"
        )
    raise ValueError(mode)


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    signal_mode: str,
    continuation_bank: Decimal,
    exhaustion_bank: Decimal,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    signal_counts: Counter[str] = Counter()
    terminal_counts: Counter[str] = Counter()
    applied = 0
    cont_applied = 0
    exhaust_applied = 0
    censored = 0

    for row in rows:
        updated = dict(row)
        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        original_gross = _opt_d(row.get("r_multiple"))
        filled_at_raw = row.get("filled_at")
        terminal_at_raw = row.get("exit_at")

        if (
            entry is None
            or stop is None
            or requested_risk is None
            or original_gross is None
            or filled_at_raw is None
            or terminal_at_raw is None
        ):
            censored += 1
            adjusted.append(updated)
            continue

        risk = abs(entry - stop)
        if risk <= 0:
            censored += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            censored += 1
            adjusted.append(updated)
            continue

        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            censored += 1
            adjusted.append(updated)
            continue

        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        ref_width = ref_high - ref_low
        equilibrium = (ref_high + ref_low) / Decimal("2")
        side = str(row["side"])

        if (
            ref_width <= 0
            or not _forward(
                side=side,
                entry=entry,
                level=equilibrium,
            )
        ):
            adjusted.append(updated)
            continue

        filled_at = _dt(filled_at_raw)
        terminal_at = _dt(terminal_at_raw)
        fill_index = next(
            (
                index
                for index, bar in enumerate(day_bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None:
            censored += 1
            adjusted.append(updated)
            continue

        eq_index = next(
            (
                index
                for index in range(fill_index, len(day_bars))
                if cast(datetime, getattr(day_bars[index], "closed_at"))
                < terminal_at
                and _wall(getattr(day_bars[index], "opened_at")) < (16, 0, 0)
                and _touches(
                    day_bars[index],
                    side=side,
                    level=equilibrium,
                )
            ),
            None,
        )
        if eq_index is None:
            adjusted.append(updated)
            continue

        snapshot = eqf._eq_snapshot(
            day_bars[fill_index : eq_index + 1],
            eq_index=eq_index - fill_index,
            side=side,
            entry=entry,
            risk=risk,
            equilibrium=equilibrium,
            ref_width=ref_width,
        )
        continuation = _continuation_signal(
            snapshot,
            updated,
            mode=signal_mode,
        )
        bank_fraction = (
            continuation_bank if continuation else exhaustion_bank
        )
        signal_name = "CONTINUATION" if continuation else "EXHAUSTION"
        signal_counts[signal_name] += 1

        updated["eq_adaptive_signal"] = signal_name
        updated["eq_adaptive_signal_mode"] = signal_mode
        updated["eq_adaptive_snapshot"] = snapshot
        updated["eq_adaptive_bank_fraction"] = format(bank_fraction, "f")

        if bank_fraction <= 0:
            adjusted.append(updated)
            continue

        eq_r = abs(equilibrium - entry) / risk
        gross = (
            bank_fraction * eq_r
            + (Decimal("1") - bank_fraction) * original_gross
        )
        net = requested_risk * (
            gross
            - engine.FRICTION
            - EXTRA_PARTIAL_FRICTION_R
        )

        updated["equilibrium_price"] = format(equilibrium, "f")
        updated["equilibrium_r"] = format(eq_r, "f")
        updated["equilibrium_bank_strictly_before_terminal"] = True
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "adaptive-equilibrium-bank-plus-remainder"

        applied += 1
        if continuation:
            cont_applied += 1
        else:
            exhaust_applied += 1
        terminal_counts[str(row.get("exit_reason"))] += 1
        adjusted.append(updated)

    return adjusted, {
        "signal_counts": dict(sorted(signal_counts.items())),
        "bank_applied_count": applied,
        "continuation_bank_applied_count": cont_applied,
        "exhaustion_bank_applied_count": exhaust_applied,
        "original_terminal_reason_counts": dict(sorted(terminal_counts.items())),
        "censored_geometry_count": censored,
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, source_stats = alt._current_rows(path)
    (
        series,
        account,
        fingerprint,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("adaptive equilibrium bank requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    variants: dict[str, object] = {}
    for name, spec in VARIANTS.items():
        if spec is None:
            adjusted = [dict(row) for row in rows]
            diag = {
                "signal_counts": {},
                "bank_applied_count": 0,
                "continuation_bank_applied_count": 0,
                "exhaustion_bank_applied_count": 0,
                "original_terminal_reason_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            mode, continuation_bank, exhaustion_bank = spec
            adjusted, diag = _apply(
                rows,
                by_day=by_day,
                signal_mode=mode,
                continuation_bank=continuation_bank,
                exhaustion_bank=exhaustion_bank,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"ADAPTIVE_EQ_BANK:{name}:{partition}",
        )
        annual = (
            annuals._annual_blocks(
                adjusted,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )
        objectives = {
            "density_300_350": 300 <= len(adjusted) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and _d(metrics["profit_factor"]) >= Decimal("1.50")
            ),
            "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
            "mc_positive_ge_0_90": (
                _d(mc["positive_terminal_probability"])
                >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[name] = {
            "trade_count": len(adjusted),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "bank_diagnostics": diag,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "variants": variants,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "development_frontier_only": True,
            "eq_signal_uses_closed_m1_only": True,
            "decision_effective_next_m1": True,
            "future_continuation_runtime_input": False,
            "same_bar_bank_terminal_not_credited": True,
            "dol1_target_not_replaced": True,
            "stop_widened": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
