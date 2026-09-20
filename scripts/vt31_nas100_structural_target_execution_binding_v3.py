"""Causal DOL1-close execution binding for certified VT31 NAS100.

Strategy identity remains VT31_NAS100_STRUCTURAL_TARGET_V1.

This V3 execution binding retains V2 physical precedence and resolves the last
live-execution timing ambiguity in the compressed-reference runner selector:

- CORE non-compressed: if certified +1.25R base partial is first or same M1 as
  EQ, preserve base lifecycle; if EQ is first, the EQ overlay may activate.
- EQ overlay: bank 50% at EQ exactly as certified.
- non-compressed at DOL1: bank the remaining 50% at DOL1 (runner impossible).
- compressed at DOL1: bank 25% at DOL1. The remaining 25% is decided only after
  the DOL1-touch M1 closes:
    * close accepts beyond DOL1 -> runner starts next M1 toward DOL2 with PS2;
    * close rejects -> residual 25% exits at the NEXT M1 OPEN.
  This forbids retroactive use of the DOL1 touch price after observing the bar
  close.

No parameter search. Entry, stop, risk, EQ fraction, DOL1, runner fraction,
DOL2 destination and PS2 are unchanged.
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
import vt31_nas100_path_causal_target_ladder_v2 as v2
import vt31_nas100_post_dol1_structural_runner_protection_v1 as runner
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_ladder_frontier_v1 as ladder

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.structural_target_execution_binding.v3"
STRATEGY_IDENTITY = "VT31_NAS100_STRUCTURAL_TARGET_V1"
VARIANT = "EQ50_COMPRESSED_ACCEPT_RUN25_CAUSAL_DOL1_CLOSE"
EQ_FRACTION = Decimal("0.50")
DOL1_BANK_FRACTION = Decimal("0.25")
RUNNER_FRACTION = Decimal("0.25")
RUNNER_EXTENSION_REF = Decimal("0.25")
EXTRA_EQ_FRICTION_R = Decimal("0.005")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")


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


def _accepts(bar: object, *, side: str, target: Decimal) -> bool:
    close = _d(getattr(bar, "close"))
    return close >= target if side == "long" else close <= target


def _open_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    opened = _d(getattr(bar, "open"))
    return (
        (opened - entry) / risk
        if side == "long"
        else (entry - opened) / risk
    )


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    precedence: Counter[str] = Counter()

    for row in rows:
        use_overlay, reason = v2._overlay_allowed(row, by_day=by_day)
        precedence[reason] += 1
        if not use_overlay:
            preserved = dict(row)
            preserved["execution_binding_v3_status"] = "BASE_PRESERVED"
            adjusted.append(preserved)
            continue

        updated = dict(row)
        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        dol1 = _opt_d(row.get("structural_target"))
        requested = _opt_d(row.get("requested_risk_r"))
        original_gross = _opt_d(row.get("r_multiple"))
        filled_raw = row.get("filled_at")
        terminal_raw = row.get("exit_at")
        if (
            entry is None
            or stop is None
            or dol1 is None
            or requested is None
            or original_gross is None
            or filled_raw is None
            or terminal_raw is None
        ):
            updated["execution_binding_v3_status"] = "CENSORED_GEOMETRY"
            status["CENSORED_GEOMETRY"] += 1
            adjusted.append(updated)
            continue

        risk = abs(entry - stop)
        if risk <= 0:
            updated["execution_binding_v3_status"] = "CENSORED_RISK"
            status["CENSORED_RISK"] += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            updated["execution_binding_v3_status"] = "CENSORED_DAY"
            status["CENSORED_DAY"] += 1
            adjusted.append(updated)
            continue

        reference = tuple(
            bar
            for bar in bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            updated["execution_binding_v3_status"] = "CENSORED_REFERENCE"
            status["CENSORED_REFERENCE"] += 1
            adjusted.append(updated)
            continue

        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        ref_width = ref_high - ref_low
        equilibrium = (ref_high + ref_low) / Decimal("2")
        side = str(row["side"])
        if ref_width <= 0 or not _forward(
            side=side,
            entry=entry,
            level=equilibrium,
        ):
            updated["execution_binding_v3_status"] = "EQ_NOT_FORWARD_BASE"
            status["EQ_NOT_FORWARD_BASE"] += 1
            adjusted.append(updated)
            continue

        filled_at = _dt(filled_raw)
        terminal_at = _dt(terminal_raw)
        fill_index = next(
            (
                index
                for index, bar in enumerate(bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None:
            updated["execution_binding_v3_status"] = "CENSORED_FILL"
            status["CENSORED_FILL"] += 1
            adjusted.append(updated)
            continue

        eq_index = ladder._first_touch_index(
            bars,
            start_index=fill_index,
            terminal_at=terminal_at,
            side=side,
            level=equilibrium,
        )
        if eq_index is None:
            updated["execution_binding_v3_status"] = "EQ_NOT_REACHED_BASE"
            status["EQ_NOT_REACHED_BASE"] += 1
            adjusted.append(updated)
            continue
        eq_closed = cast(datetime, getattr(bars[eq_index], "closed_at"))
        if eq_closed >= terminal_at:
            updated["execution_binding_v3_status"] = "EQ_AT_TERMINAL_BASE"
            status["EQ_AT_TERMINAL_BASE"] += 1
            adjusted.append(updated)
            continue

        eq_r = abs(equilibrium - entry) / risk
        dol1_index = ladder._first_touch_index(
            bars,
            start_index=eq_index + 1,
            terminal_at=terminal_at,
            side=side,
            level=dol1,
        )
        if dol1_index is None:
            gross = (
                EQ_FRACTION * eq_r
                + (Decimal("1") - EQ_FRACTION) * original_gross
            )
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(
                requested
                * (gross - engine.FRICTION - EXTRA_EQ_FRICTION_R),
                "f",
            )
            updated["execution_binding_v3_status"] = "EQ50_BASE_REMAINDER"
            updated["exit_reason"] = "eq50-base-remainder"
            status["EQ50_BASE_REMAINDER"] += 1
            adjusted.append(updated)
            continue

        dol1_bar = bars[dol1_index]
        dol1_closed = cast(datetime, getattr(dol1_bar, "closed_at"))
        dol1_r = abs(dol1 - entry) / risk
        compressed = row.get("reference_volatility_state") == "compressed"

        if not compressed:
            gross = EQ_FRACTION * eq_r + Decimal("0.50") * dol1_r
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(
                requested
                * (gross - engine.FRICTION - EXTRA_EQ_FRICTION_R),
                "f",
            )
            updated["execution_binding_v3_status"] = "EQ50_DOL1_FULL"
            updated["exit_reason"] = "eq50-dol1-full-remainder"
            status["EQ50_DOL1_FULL"] += 1
            adjusted.append(updated)
            continue

        if _accepts(dol1_bar, side=side, target=dol1):
            direction = Decimal(1) if side == "long" else Decimal(-1)
            runner_target = dol1 + direction * ref_width * RUNNER_EXTENSION_REF
            runner_r, runner_status, diag = runner._runner_outcome(
                bars,
                target_exit_at=dol1_closed,
                side=side,
                entry=entry,
                initial_stop=stop,
                runner_target=runner_target,
                risk=risk,
                required_confirmations=2,
            )
            gross = (
                EQ_FRACTION * eq_r
                + DOL1_BANK_FRACTION * dol1_r
                + RUNNER_FRACTION * runner_r
            )
            updated["r_multiple"] = format(gross, "f")
            updated["capital_weighted_net_r"] = format(
                requested
                * (
                    gross
                    - engine.FRICTION
                    - EXTRA_EQ_FRICTION_R
                    - EXTRA_RUNNER_FRICTION_R
                ),
                "f",
            )
            updated["execution_binding_v3_status"] = "EQ50_DOL125_RUN25"
            updated["runner_terminal_status"] = runner_status
            updated["runner_structural_protection_armed"] = bool(
                diag.get("structural_protection_armed")
            )
            updated["exit_reason"] = "causal-dol1-accept-runner"
            status[f"RUNNER_{runner_status}"] += 1
            adjusted.append(updated)
            continue

        next_index = dol1_index + 1
        if next_index >= len(bars) or _wall(
            getattr(bars[next_index], "opened_at")
        ) >= (16, 0, 0):
            residual_r = _d(getattr(dol1_bar, "close"))
            residual_r = (
                (residual_r - entry) / risk
                if side == "long"
                else (entry - residual_r) / risk
            )
            reject_mode = "DOL1_REJECT_CLOSE_NO_NEXT_M1"
        else:
            residual_r = _open_r(
                bars[next_index],
                side=side,
                entry=entry,
                risk=risk,
            )
            reject_mode = "DOL1_REJECT_EXIT_NEXT_M1_OPEN"

        gross = (
            EQ_FRACTION * eq_r
            + DOL1_BANK_FRACTION * dol1_r
            + RUNNER_FRACTION * residual_r
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(
            requested
            * (
                gross
                - engine.FRICTION
                - EXTRA_EQ_FRICTION_R
                - EXTRA_RUNNER_FRICTION_R
            ),
            "f",
        )
        updated["execution_binding_v3_status"] = reject_mode
        updated["exit_reason"] = "causal-dol1-reject-residual-exit"
        status[reject_mode] += 1
        adjusted.append(updated)

    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, {
        "status_counts": dict(sorted(status.items())),
        "precedence_counts": dict(sorted(precedence.items())),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    series, account, fingerprint, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(items, key=lambda item: getattr(item, "opened_at")))
        for day, items in raw.items()
    }
    adjusted, diag = _apply(rows, by_day=by_day)
    metrics = residual._metrics(adjusted)
    mc = engine._monte_carlo(
        adjusted,
        variant=f"EXECUTION_BINDING_V3:{partition}",
    )
    annual = (
        annuals._annual_blocks(adjusted, start=date(2022, 7, 18), years=2)
        if partition == "consumed_holdout"
        else []
    )
    gates = {
        "density_300_350": 300 <= len(adjusted) <= 350,
        "pf_ge_1_50": (
            metrics["profit_factor"] is not None
            and _d(metrics["profit_factor"]) >= Decimal("1.50")
        ),
        "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
        "mc_positive_ge_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_le_15": _d(mc["p95_max_drawdown_r"]) <= Decimal("15"),
    }
    if annual:
        gates["both_consumed_years_positive"] = all(
            bool(block["positive"]) for block in annual
        )
    return {
        "schema": SCHEMA,
        "strategy_identity": STRATEGY_IDENTITY,
        "partition": partition,
        "variant": VARIANT,
        "trade_count": len(adjusted),
        "metrics": metrics,
        "monte_carlo": mc,
        "annual_blocks": annual,
        "execution_diagnostics": diag,
        "gates": gates,
        "passes": all(gates.values()),
        "evidence": {
            **evidence,
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "source_stats": stats,
        "diagnostics": diagnostics,
        "governance": {
            "parameter_search": False,
            "strategy_identity_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "risk_changed": False,
            "eq_fraction_changed": False,
            "dol1_changed": False,
            "runner_fraction_changed": False,
            "runner_destination_changed": False,
            "runner_ps2_changed": False,
            "dol1_acceptance_decision_closed_m1_only": True,
            "rejected_runner_exit_effective_next_m1": True,
            "retroactive_exit_price_forbidden": True,
            "future_runtime_input": False,
            "candidate_certified": False,
            "live_authorized": False,
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
    print(json.dumps({
        "partition": payload["partition"],
        "trade_count": payload["trade_count"],
        "metrics": payload["metrics"],
        "monte_carlo": payload["monte_carlo"],
        "gates": payload["gates"],
        "execution_diagnostics": payload["execution_diagnostics"],
        "passes": payload["passes"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
