"""Causal Target Decision Engine V1 frontier for VT31_NAS100.

Development-only economic falsification.

The engine classifies destination capacity using ONLY state known at trade
authorization/fill time, based on stable 4/4 findings from Entry Destination
Intelligence V1.

States:
- SHALLOW: at least one stable shallow-capacity condition is present.
- DEEP: compressed reference volatility and no SHALLOW condition.
- NEUTRAL: everything else.

Policy under test:
- SHALLOW and NEUTRAL retain the current full DOL1 structural target.
- DEEP may bank 75% at DOL1 and retain a 25% runner toward DOL2/DOL3.
- Runner protection uses only confirmed post-DOL1 M1 protective swings,
  effective from the next M1, never widening the stop.
- No future journey label participates in the runtime decision.
- Silver Bullet, entry, initial stop, admission and risk are unchanged.

This is a frontier, not a promotion.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_post_dol1_structural_runner_protection_v1 as runner
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.target_decision_engine_frontier.v1"
MARKET = "NAS100"

BANK_FRACTION = Decimal("0.75")
RUNNER_FRACTION = Decimal("0.25")
EXTRA_RUNNER_FRICTION_R = Decimal("0.01")

VARIANTS = {
    "BASE": None,
    "DEEP_DOL2_PS1": (Decimal("0.25"), 1, "STRICT"),
    "DEEP_DOL2_PS2": (Decimal("0.25"), 2, "STRICT"),
    "DEEP_DOL3_PS2": (Decimal("0.50"), 2, "STRICT"),
    "COMPRESSED_DOL2_PS2": (Decimal("0.25"), 2, "BROAD"),
    "COMPRESSED_DOL3_PS2": (Decimal("0.50"), 2, "BROAD"),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _is_shallow(row: dict[str, object]) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []

    if row.get("confirmation_latency_bucket") == "11m_plus":
        reasons.append("LATENCY_11M_PLUS")
    if row.get("last_structure_event_family") == "breaker":
        reasons.append("LAST_STRUCTURE_BREAKER")
    if row.get("risk_ref_bucket") == "low":
        reasons.append("RISK_REF_LOW")
    if (
        row.get("tier") == "SECONDARY"
        and row.get("entry_family") == "breaker"
    ):
        reasons.append("SECONDARY_BREAKER")
    if (
        row.get("reference_volatility_state") == "expanded"
        and row.get("current_path_bucket") == "high"
    ):
        reasons.append("EXPANDED_PATH_HIGH")
    if (
        row.get("premarket_state") == "bearish"
        and row.get("cash_open_state") == "bearish"
    ):
        reasons.append("PREMARKET_BEARISH_CASH_BEARISH")

    return bool(reasons), tuple(reasons)


def _destination_state(
    row: dict[str, object],
) -> tuple[str, tuple[str, ...]]:
    shallow, reasons = _is_shallow(row)
    if shallow:
        return "SHALLOW", reasons
    if row.get("reference_volatility_state") == "compressed":
        return "DEEP", ("REFERENCE_VOLATILITY_COMPRESSED",)
    return "NEUTRAL", ()


def _runner_selected(
    row: dict[str, object],
    *,
    scope: str,
) -> tuple[bool, str, tuple[str, ...]]:
    state, reasons = _destination_state(row)
    if scope == "STRICT":
        return state == "DEEP", state, reasons
    if scope == "BROAD":
        selected = row.get("reference_volatility_state") == "compressed"
        return selected, state, reasons
    raise ValueError(scope)


def _apply_variant(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
    extension_ref: Decimal,
    required_confirmations: int,
    scope: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    state_counts: Counter[str] = Counter()
    runner_state_counts: Counter[str] = Counter()
    shallow_reason_counts: Counter[str] = Counter()
    runner_status_counts: Counter[str] = Counter()
    runner_applied = 0
    protection_armed = 0
    censored = 0

    for row in rows:
        updated = dict(row)
        state, reasons = _destination_state(updated)
        state_counts[state] += 1
        for reason in reasons:
            shallow_reason_counts[reason] += 1

        updated["destination_state"] = state
        updated["destination_state_reasons"] = list(reasons)

        selected, _, _ = _runner_selected(updated, scope=scope)
        if (
            not selected
            or row.get("exit_reason") != "structural-target"
            or _d(row["capital_weighted_net_r"]) <= 0
        ):
            updated["target_decision"] = "FULL_DOL1"
            adjusted.append(updated)
            continue

        entry = runner._opt_d(row.get("entry"))
        initial_stop = runner._opt_d(row.get("initial_stop"))
        target = runner._opt_d(row.get("structural_target"))
        risk_ref = runner._opt_d(row.get("risk_ref"))
        requested_risk = runner._opt_d(row.get("requested_risk_r"))
        exit_at = row.get("exit_at")

        if (
            entry is None
            or initial_stop is None
            or target is None
            or risk_ref is None
            or risk_ref <= 0
            or requested_risk is None
            or exit_at is None
        ):
            updated["target_decision"] = "FULL_DOL1_CENSORED_GEOMETRY"
            censored += 1
            adjusted.append(updated)
            continue

        risk = abs(entry - initial_stop)
        if risk <= 0:
            updated["target_decision"] = "FULL_DOL1_CENSORED_RISK"
            censored += 1
            adjusted.append(updated)
            continue

        local_day = date.fromisoformat(str(row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            updated["target_decision"] = "FULL_DOL1_CENSORED_DAY"
            censored += 1
            adjusted.append(updated)
            continue

        ref_width = risk / risk_ref
        side = str(row["side"])
        direction = Decimal(1) if side == "long" else Decimal(-1)
        runner_target = target + direction * ref_width * extension_ref

        runner_r, status, diag = runner._runner_outcome(
            day_bars,
            target_exit_at=runner._dt(exit_at),
            side=side,
            entry=entry,
            initial_stop=initial_stop,
            runner_target=runner_target,
            risk=risk,
            required_confirmations=required_confirmations,
        )

        target_r = abs(target - entry) / risk
        gross = (
            BANK_FRACTION * target_r
            + RUNNER_FRACTION * runner_r
        )
        net = requested_risk * (
            gross
            - engine.FRICTION
            - EXTRA_RUNNER_FRICTION_R
        )

        updated["target_decision"] = (
            "BANK75_DOL1_RUN25_DOL2"
            if extension_ref == Decimal("0.25")
            else "BANK75_DOL1_RUN25_DOL3"
        )
        updated["runner_extension_ref"] = format(extension_ref, "f")
        updated["runner_required_protective_confirmations"] = (
            required_confirmations
        )
        updated["runner_terminal_r"] = format(runner_r, "f")
        updated["runner_terminal_status"] = status
        updated["runner_structural_protection_armed"] = bool(
            diag.get("structural_protection_armed")
        )
        updated["r_multiple"] = format(gross, "f")
        updated["capital_weighted_net_r"] = format(net, "f")
        updated["exit_reason"] = "target-decision-engine"

        runner_applied += 1
        runner_state_counts[state] += 1
        runner_status_counts[status] += 1
        if updated["runner_structural_protection_armed"]:
            protection_armed += 1

        adjusted.append(updated)

    return adjusted, {
        "destination_state_counts": dict(sorted(state_counts.items())),
        "runner_applied_trade_count": runner_applied,
        "runner_destination_state_counts": dict(
            sorted(runner_state_counts.items())
        ),
        "runner_status_counts": dict(sorted(runner_status_counts.items())),
        "structural_protection_armed_count": protection_armed,
        "shallow_reason_counts": dict(sorted(shallow_reason_counts.items())),
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
        raise ValueError("target decision engine requires NAS100")

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
                "destination_state_counts": {},
                "runner_applied_trade_count": 0,
                "runner_destination_state_counts": {},
                "runner_status_counts": {},
                "structural_protection_armed_count": 0,
                "shallow_reason_counts": {},
                "censored_geometry_count": 0,
            }
        else:
            extension_ref, confirmations, scope = spec
            adjusted, diag = _apply_variant(
                rows,
                by_day=by_day,
                extension_ref=extension_ref,
                required_confirmations=confirmations,
                scope=scope,
            )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"TARGET_DECISION_ENGINE:{name}:{partition}",
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
            "decision_diagnostics": diag,
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
            "destination_state_uses_entry_known_features_only": True,
            "future_journey_runtime_input": False,
            "full_dol1_default_preserved": True,
            "runner_only_on_predeclared_capacity_state": True,
            "protective_swing_confirmed_closed_m1": True,
            "protective_swing_effective_next_m1": True,
            "stop_can_only_improve_or_hold": True,
            "stop_widened": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "risk_policy_changed": False,
            "silver_bullet_changed": False,
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
