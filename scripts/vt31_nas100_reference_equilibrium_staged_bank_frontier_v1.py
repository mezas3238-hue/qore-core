"""Reference-equilibrium staged bank frontier for VT31_NAS100.

Development-only economic falsification.

The frozen 09:00-10:00 reference equilibrium is a structural milestone known
before the trade. Entry Destination / Reference Ladder research shows it is
reached materially more often than the opposite boundary, but no stable 4/4
state justifies replacing DOL1 with equilibrium as the full target.

This frontier therefore tests partial realization at equilibrium while leaving
the remaining position under the existing trade outcome / DOL1 lifecycle.

Policies:
- ALL_EQ_BANK25 / ALL_EQ_BANK50: bank when equilibrium is a forward level and
  was reached on a strictly earlier closed M1 than the original terminal bar.
- SHALLOW_EQ_BANK25 / SHALLOW_EQ_BANK50: same, but only for stable 4/4 SHALLOW
  interactions from Target Decision Engine V2.

Same-bar equilibrium/terminal events are not credited.
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
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_target_decision_engine_frontier_v2 as target_v2

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.reference_equilibrium_staged_bank_frontier.v1"
MARKET = "NAS100"
EXTRA_PARTIAL_FRICTION_R = Decimal("0.005")

VARIANTS = {
    "BASE": None,
    "ALL_EQ_BANK25": (Decimal("0.25"), "ALL"),
    "ALL_EQ_BANK50": (Decimal("0.50"), "ALL"),
    "SHALLOW_EQ_BANK25": (Decimal("0.25"), "SHALLOW"),
    "SHALLOW_EQ_BANK50": (Decimal("0.50"), "SHALLOW"),
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


def _eq_before_terminal(
    bars: tuple[object, ...],
    *,
    filled_at: datetime,
    terminal_at: datetime,
    side: str,
    equilibrium: Decimal,
) -> bool:
    for bar in bars:
        closed = cast(datetime, getattr(bar, "closed_at"))
        if closed < filled_at:
            continue
        if closed >= terminal_at:
            break
        if _wall(getattr(bar, "opened_at")) >= (16, 0, 0):
            break
        if _touches(bar, side=side, level=equilibrium):
            return True
    return False


def _apply(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    bank_fraction: Decimal,
    scope: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    applied = 0
    eligible = 0
    shallow_applied = 0
    terminal_classes: Counter[str] = Counter()
    censored = 0

    for row in rows:
        updated = dict(row)
        if scope == "SHALLOW" and not target_v2._shallow_interactions(updated):
            adjusted.append(updated)
            continue

        entry = _opt_d(row.get("entry"))
        stop = _opt_d(row.get("initial_stop"))
        requested_risk = _opt_d(row.get("requested_risk_r"))
        original_gross = _opt_d(row.get("r_multiple"))
        filled_at_raw = row.get("filled_at")
        exit_at_raw = row.get("exit_at")

        if (
            entry is None
            or stop is None
            or requested_risk is None
            or original_gross is None
            or filled_at_raw is None
            or exit_at_raw is None
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

        reference_high = max(_d(getattr(bar, "high")) for bar in reference)
        reference_low = min(_d(getattr(bar, "low")) for bar in reference)
        equilibrium = (reference_high + reference_low) / Decimal("2")
        side = str(row["side"])

        if not _forward(side=side, entry=entry, level=equilibrium):
            adjusted.append(updated)
            continue

        eligible += 1
        if not _eq_before_terminal(
            day_bars,
            filled_at=_dt(filled_at_raw),
            terminal_at=_dt(exit_at_raw),
            side=side,
            equilibrium=equilibrium,
        ):
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

        updated["equilibrium_bank_fraction"] = format(bank_fraction, "f")
        updated["equilibrium_price"] = format(equilibrium, "f")
        updated["equilibrium_r"] = format(eq_r, "f")
        updated["equilibrium_bank_strictly_before_terminal"] = True
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "equilibrium-bank-plus-original-remainder"

        applied += 1
        if target_v2._shallow_interactions(updated):
            shallow_applied += 1
        terminal_classes[str(row.get("exit_reason"))] += 1
        adjusted.append(updated)

    return adjusted, {
        "eligible_forward_equilibrium_count": eligible,
        "bank_applied_count": applied,
        "shallow_bank_applied_count": shallow_applied,
        "original_terminal_reason_counts": dict(sorted(terminal_classes.items())),
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
        raise ValueError("equilibrium staged bank requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: getattr(item, "opened_at")))
        for local_day, items in raw.items()
    }

    variants: dict[str, object] = {}
    for name, spec in VARIANTS.items():
        if spec is None:
            adjusted = [dict(row) for row in rows]
            diag = {
                "eligible_forward_equilibrium_count": 0,
                "bank_applied_count": 0,
                "shallow_bank_applied_count": 0,
                "original_terminal_reason_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            fraction, scope = spec
            adjusted, diag = _apply(
                rows,
                by_day=by_day,
                bank_fraction=fraction,
                scope=scope,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"EQ_STAGED_BANK:{name}:{partition}",
        )
        annual = (
            annuals._annual_blocks(adjusted, start=date(2022, 7, 18), years=2)
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
            "equilibrium_known_before_trade": True,
            "bank_requires_strictly_earlier_closed_m1": True,
            "same_bar_bank_terminal_not_credited": True,
            "dol1_target_not_replaced": True,
            "stop_widened": False,
            "future_reach_runtime_input": False,
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
    print(json.dumps({"partition": payload["partition"], "variants": payload["variants"]}, sort_keys=True))


if __name__ == "__main__":
    main()
