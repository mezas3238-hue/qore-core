"""Structural bank-and-run target frontier for VT31_NAS100.

Consumed development research only.

The current DOL1 structural target is retained as the bank point. A fixed
fraction is realized at DOL1 and a residual runner remains open toward a
deeper structural destination measured in reference-width units.

Runner rules are causal and predeclared:
- no trade-admission change;
- no entry change;
- original methodological initial stop is retained (never widened);
- runner target is DOL1 + extension in the favorable direction;
- runner begins from the next M1 after the DOL1 target bar;
- same-M1 runner-target/stop ambiguity is fail-closed as STOP FIRST;
- unresolved runner exits at the final M1 close before 16:00 NY;
- combined trade friction includes the existing 0.05R plus a conservative
  0.01R extra runner-leg friction.

No future extension label is used to choose a variant at runtime.
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
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.structural_bank_runner_frontier.v1"
MARKET = "NAS100"
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")

VARIANTS = {
    "BASE": None,
    "BANK75_RUN25_DOL2": (
        Decimal("0.75"),
        Decimal("0.25"),
        Decimal("0.25"),
    ),
    "BANK75_RUN25_DOL3": (
        Decimal("0.75"),
        Decimal("0.25"),
        Decimal("0.50"),
    ),
    "BANK75_RUN25_DOL4": (
        Decimal("0.75"),
        Decimal("0.25"),
        Decimal("1.00"),
    ),
    "BANK50_RUN50_DOL2": (
        Decimal("0.50"),
        Decimal("0.50"),
        Decimal("0.25"),
    ),
    "BANK50_RUN50_DOL3": (
        Decimal("0.50"),
        Decimal("0.50"),
        Decimal("0.50"),
    ),
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


def _touches(
    bar: object,
    *,
    side: str,
    level: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _touches_stop(
    bar: object,
    *,
    side: str,
    stop: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _close_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    close: Decimal,
) -> Decimal:
    if side == "long":
        return (close - entry) / risk
    return (entry - close) / risk


def _runner_outcome(
    day_bars: tuple[object, ...],
    *,
    exit_at: datetime,
    side: str,
    entry: Decimal,
    stop: Decimal,
    runner_target: Decimal,
    risk: Decimal,
) -> tuple[Decimal, str]:
    eligible = [
        bar
        for bar in day_bars
        if cast(datetime, getattr(bar, "opened_at")) >= exit_at
        and _wall(getattr(bar, "opened_at")) < (16, 0, 0)
    ]
    if not eligible:
        return Decimal(0), "CENSORED_NO_POST_TARGET_BARS"

    for bar in eligible:
        stop_hit = _touches_stop(bar, side=side, stop=stop)
        target_hit = _touches(
            bar,
            side=side,
            level=runner_target,
        )
        if stop_hit and target_hit:
            return Decimal("-1"), "SAME_BAR_STOP_FIRST"
        if stop_hit:
            return Decimal("-1"), "METHODOLOGICAL_STOP"
        if target_hit:
            target_r = abs(runner_target - entry) / risk
            return target_r, "RUNNER_TARGET"

    final_close = _d(getattr(eligible[-1], "close"))
    return (
        _close_r(
            side=side,
            entry=entry,
            risk=risk,
            close=final_close,
        ),
        "16:00_LIFECYCLE",
    )


def _apply_variant(
    rows: list[dict[str, object]],
    *,
    day_bars_by_date: dict[date, tuple[object, ...]],
    bank_fraction: Decimal,
    runner_fraction: Decimal,
    extension_ref: Decimal,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    applied = 0
    censored_geometry = 0

    for row in rows:
        updated = dict(row)
        if (
            row.get("exit_reason") != "structural-target"
            or _d(row["capital_weighted_net_r"]) <= 0
        ):
            adjusted.append(updated)
            continue

        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        target = _opt_d(row.get("structural_target"))
        risk_ref = _opt_d(row.get("risk_ref"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        exit_at_raw = row.get("exit_at")
        if (
            entry is None
            or stop is None
            or target is None
            or risk_ref is None
            or risk_ref <= 0
            or requested_risk is None
            or exit_at_raw is None
        ):
            censored_geometry += 1
            adjusted.append(updated)
            continue

        risk = abs(entry - stop)
        if risk <= 0:
            censored_geometry += 1
            adjusted.append(updated)
            continue

        ref_width = risk / risk_ref
        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = day_bars_by_date.get(local_day)
        if not day_bars:
            censored_geometry += 1
            adjusted.append(updated)
            continue

        side = str(row["side"])
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = target + direction * ref_width * extension_ref
        target_r = abs(target - entry) / risk

        runner_r, runner_status = _runner_outcome(
            day_bars,
            exit_at=_dt(exit_at_raw),
            side=side,
            entry=entry,
            stop=stop,
            runner_target=runner_target,
            risk=risk,
        )

        combined_gross_r = (
            bank_fraction * target_r
            + runner_fraction * runner_r
        )
        combined_net_r = requested_risk * (
            combined_gross_r
            - engine.FRICTION
            - EXTRA_RUNNER_FRICTION_R
        )

        updated["bank_fraction"] = format(bank_fraction, "f")
        updated["runner_fraction"] = format(runner_fraction, "f")
        updated["runner_extension_ref"] = format(extension_ref, "f")
        updated["runner_target"] = format(runner_target, "f")
        updated["runner_terminal_r"] = format(runner_r, "f")
        updated["runner_terminal_status"] = runner_status
        updated["runner_extra_friction_r"] = format(
            EXTRA_RUNNER_FRICTION_R,
            "f",
        )
        updated["r_multiple"] = format(combined_gross_r, "f")
        updated["capital_weighted_net_r"] = format(
            combined_net_r,
            "f",
        )
        updated["exit_reason"] = (
            "structural-bank-plus-runner"
        )

        status_counts[runner_status] += 1
        applied += 1
        adjusted.append(updated)

    return adjusted, {
        "runner_applied_trade_count": applied,
        "runner_status_counts": dict(sorted(status_counts.items())),
        "censored_geometry_count": censored_geometry,
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
        raise ValueError("structural bank-runner requires NAS100")

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
            runner_diag = {
                "runner_applied_trade_count": 0,
                "runner_status_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            bank_fraction, runner_fraction, extension_ref = spec
            adjusted, runner_diag = _apply_variant(
                rows,
                day_bars_by_date=by_day,
                bank_fraction=bank_fraction,
                runner_fraction=runner_fraction,
                extension_ref=extension_ref,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"STRUCTURAL_BANK_RUNNER:{name}:{partition}",
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
            "dd_le_6": (
                _d(metrics["max_drawdown_r"]) <= Decimal("6")
            ),
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
                bool(block["positive"])
                for block in annual
            )

        variants[name] = {
            "trade_count": len(adjusted),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "runner_diagnostics": runner_diag,
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
            "consumed_evidence_only": True,
            "development_frontier_only": True,
            "dol1_bank_point_retained": True,
            "original_methodological_stop_retained": True,
            "stop_widened": False,
            "same_bar_stop_first": True,
            "extra_runner_friction_modeled": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "silver_bullet_changed": False,
            "future_extension_runtime_input": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
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
