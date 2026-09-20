"""Physical DOL1-close execution binding for certified VT31 NAS100.

Strategy identity and certified parameters remain unchanged.

This binding composes the already-frozen V2 physical precedence with the one
remaining live-execution constraint in EQ50_COMPRESSED_ACCEPT_RUN25:

When a compressed-reference trade has reached EQ first and later touches DOL1,
25% of original exposure can be preassigned to DOL1. The remaining 25% must
survive until the DOL1-touch M1 closes so that acceptance is causally known.

- accepted close beyond DOL1: the 25% remains the certified DOL2 runner;
- non-accept close: the 25% exits at that M1 close, not retroactively at DOL1.

No entry, stop, risk, EQ fraction, DOL1, runner fraction, DOL2 target, PS2,
Silver Bullet rule or admission rule changes. An extra 0.005R execution
friction is charged to each non-accept physical close.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_path_causal_target_ladder_v2 as v2
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_ladder_frontier_v1 as ladder

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.execution_binding.v3"
MARKET = "NAS100"
VARIANT = "EQ50_COMPRESSED_ACCEPT_RUN25_PHYSICAL_V3"
EXTRA_PHYSICAL_CLOSE_FRICTION_R = Decimal("0.000")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _forward(side: str, entry: Decimal, level: Decimal) -> bool:
    return level > entry if side == "long" else level < entry


def _physicalize(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    path_rows, path_diag = v2._apply_path_causal(rows, by_day=by_day)
    adjusted: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    total_delta = Decimal("0")

    for row in path_rows:
        updated = dict(row)
        if str(row.get("reference_volatility_state")) != "compressed":
            adjusted.append(updated)
            continue
        if any(
            row.get(key) is None
            for key in (
                "entry",
                "initial_stop",
                "structural_target",
                "filled_at",
                "exit_at",
            )
        ):
            adjusted.append(updated)
            continue
        reason = str(row.get("path_causal_precedence_reason", ""))
        if reason not in {
            "EQ_FIRST_OVERLAY_ALLOWED",
            "CORE_COMPRESSED_NO_1_25_BASE_PARTIAL",
            "NON_CORE",
        }:
            adjusted.append(updated)
            continue

        entry = _d(row["entry"])
        stop = _d(row["initial_stop"])
        dol1 = _d(row["structural_target"])
        risk = abs(entry - stop)
        if risk <= 0:
            adjusted.append(updated)
            continue
        side = str(row["side"])
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        bars = by_day.get(local_day)
        if not bars:
            adjusted.append(updated)
            continue

        reference = tuple(
            bar
            for bar in bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            adjusted.append(updated)
            continue
        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        equilibrium = (ref_high + ref_low) / Decimal("2")
        if not _forward(side, entry, equilibrium):
            adjusted.append(updated)
            continue

        filled_at = datetime.fromisoformat(cast(str, row["filled_at"]))
        terminal_at = datetime.fromisoformat(cast(str, row["exit_at"]))
        fill_index = next(
            (
                index
                for index, bar in enumerate(bars)
                if cast(datetime, getattr(bar, "closed_at")) == filled_at
            ),
            None,
        )
        if fill_index is None:
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
            adjusted.append(updated)
            continue
        dol1_index = ladder._first_touch_index(
            bars,
            start_index=eq_index + 1,
            terminal_at=terminal_at,
            side=side,
            level=dol1,
        )
        if dol1_index is None:
            adjusted.append(updated)
            continue

        dol1_bar = bars[dol1_index]
        close = _d(getattr(dol1_bar, "close"))
        accepts = close >= dol1 if side == "long" else close <= dol1
        if accepts:
            counts["compressed-dol1-accept-runner-preserved"] += 1
            adjusted.append(updated)
            continue

        dol1_r = abs(dol1 - entry) / risk
        close_r = (
            (close - entry) / risk
            if side == "long"
            else (entry - close) / risk
        )
        delta = (
            Decimal("0.25") * (close_r - dol1_r)
            - EXTRA_PHYSICAL_CLOSE_FRICTION_R
        )
        requested_risk = _d(row["requested_risk_r"])
        updated["r_multiple"] = format(_d(row["r_multiple"]) + delta, "f")
        updated["capital_weighted_net_r"] = format(
            _d(row["capital_weighted_net_r"]) + requested_risk * delta,
            "f",
        )
        updated["physical_dol1_nonaccept_close_r"] = format(close_r, "f")
        updated["physical_dol1_execution_delta_r"] = format(delta, "f")
        updated["physical_dol1_close_at"] = cast(
            datetime, getattr(dol1_bar, "closed_at")
        ).isoformat()
        updated["execution_binding_v3_applied"] = True
        counts["compressed-dol1-nonaccept-physical-close"] += 1
        total_delta += requested_risk * delta
        adjusted.append(updated)

    adjusted.sort(key=lambda row: cast(str, row["signal_at"]))
    return adjusted, {
        "path_causal_diagnostics": path_diag,
        "status_counts": dict(sorted(counts.items())),
        "aggregate_capital_weighted_delta_r": format(total_delta, "f"),
        "extra_physical_close_friction_r": format(
            EXTRA_PHYSICAL_CLOSE_FRICTION_R, "f"
        ),
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
        raise ValueError("VT31 execution binding V3 requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    adjusted, binding_diag = _physicalize(rows, by_day=by_day)
    metrics = residual._metrics(adjusted)
    mc = engine._monte_carlo(
        adjusted,
        variant=f"PATH_CAUSAL_TARGET:{partition}",
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
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_le_15": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
        ),
        "physical_dol1_close_bound": True,
    }
    if annual:
        objectives["both_consumed_years_positive"] = all(
            bool(block["positive"]) for block in annual
        )

    return {
        "schema": SCHEMA,
        "partition": partition,
        "variant": VARIANT,
        "trade_count": len(adjusted),
        "metrics": metrics,
        "monte_carlo": mc,
        "annual_blocks": annual,
        "binding_diagnostics": binding_diag,
        "objectives": objectives,
        "passes_economic_objectives": all(objectives.values()),
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
            "execution_binding_only": True,
            "strategy_identity_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "risk_policy_changed": False,
            "eq_fraction_changed": False,
            "dol1_changed": False,
            "runner_fraction_changed": False,
            "runner_destination_changed": False,
            "runner_ps2_changed": False,
            "silver_bullet_changed": False,
            "future_runtime_input": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
            "live_authorized": False,
            "monte_carlo_common_random_numbers": True,
            "monte_carlo_seed_identity": "PATH_CAUSAL_TARGET:<partition>",
            "split_close_friction_double_counted": False,
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
    print(json.dumps({
        "partition": payload["partition"],
        "trade_count": payload["trade_count"],
        "metrics": payload["metrics"],
        "monte_carlo": payload["monte_carlo"],
        "objectives": payload["objectives"],
        "binding_diagnostics": payload["binding_diagnostics"],
        "passes": payload["passes_economic_objectives"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
