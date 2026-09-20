"""Path-causal correction for VT31 NAS100 Structural Target V1.

The previously frozen EQ50_COMPRESSED_ACCEPT_RUN25 target overlay is retained
unchanged, except for one physical-execution precedence invariant:

For CORE trades whose base lifecycle is the non-compressed
PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER:
- if +1.25R is touched before equilibrium, preserve the base lifecycle;
- if +1.25R and equilibrium are first touched on the same M1, preserve the
  base lifecycle (fail closed to no retroactive rebanking);
- only if equilibrium is touched first may the existing EQ50 structural ladder
  become active.

This is not a parameter search. It prevents the overlay from retroactively
reallocating exposure already realized by the base lifecycle.
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
import vt31_nas100_capacity_selective_target_ladder_v1 as capacity
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.path_causal_target_ladder.v2"
MARKET = "NAS100"
VARIANT = "EQ50_COMPRESSED_ACCEPT_RUN25_PATH_CAUSAL"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _touch(bar: object, *, side: str, level: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= level
    return _d(getattr(bar, "low")) <= level


def _overlay_allowed(
    row: dict[str, object],
    *,
    by_day: dict[date, tuple[object, ...]],
) -> tuple[bool, str]:
    if str(row.get("tier")) != "CORE":
        return True, "NON_CORE"
    if str(row.get("reference_volatility_state")) == "compressed":
        return True, "CORE_COMPRESSED_NO_1_25_BASE_PARTIAL"

    entry = _opt_d(row.get("entry"))
    stop = _opt_d(row.get("initial_stop"))
    filled_raw = row.get("filled_at")
    terminal_raw = row.get("exit_at")
    if entry is None or stop is None or filled_raw is None or terminal_raw is None:
        return False, "CORE_NONCOMPRESSED_MISSING_BASE_GEOMETRY"

    risk = abs(entry - stop)
    if risk <= 0:
        return False, "CORE_NONCOMPRESSED_INVALID_RISK"

    local_day = date.fromisoformat(cast(str, row["local_date"]))
    bars = by_day.get(local_day)
    if not bars:
        return False, "CORE_NONCOMPRESSED_MISSING_DAY"

    reference = tuple(
        bar
        for bar in bars
        if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
    )
    if len(reference) != 60:
        return False, "CORE_NONCOMPRESSED_REFERENCE_INCOMPLETE"

    ref_high = max(_d(getattr(bar, "high")) for bar in reference)
    ref_low = min(_d(getattr(bar, "low")) for bar in reference)
    equilibrium = (ref_high + ref_low) / Decimal(2)
    side = str(row["side"])
    forward = equilibrium > entry if side == "long" else equilibrium < entry
    if not forward:
        return True, "EQ_NOT_FORWARD_BASE_OVERLAY_NOOP"

    partial = (
        entry + risk * Decimal("1.25")
        if side == "long"
        else entry - risk * Decimal("1.25")
    )
    filled = datetime.fromisoformat(cast(str, filled_raw))
    terminal = datetime.fromisoformat(cast(str, terminal_raw))
    eq_at: datetime | None = None
    partial_at: datetime | None = None

    for bar in bars:
        opened = cast(datetime, getattr(bar, "opened_at"))
        closed = cast(datetime, getattr(bar, "closed_at"))
        if closed < filled or closed >= terminal:
            continue
        if _wall(opened) >= (16, 0, 0):
            break
        if eq_at is None and _touch(bar, side=side, level=equilibrium):
            eq_at = closed
        if partial_at is None and _touch(bar, side=side, level=partial):
            partial_at = closed
        if eq_at is not None and partial_at is not None:
            break

    if eq_at is None:
        return True, "EQ_NOT_REACHED_BASE_OVERLAY_NOOP"
    if partial_at is None or eq_at < partial_at:
        return True, "EQ_FIRST_OVERLAY_ALLOWED"
    if partial_at < eq_at:
        return False, "BASE_1_25_FIRST_PRESERVE_BASE"
    return False, "SAME_M1_1_25_EQ_PRESERVE_BASE"


def _apply_path_causal(
    rows: list[dict[str, object]],
    *,
    by_day: dict[date, tuple[object, ...]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    allowed: list[dict[str, object]] = []
    preserved: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()

    for row in rows:
        use_overlay, reason = _overlay_allowed(row, by_day=by_day)
        reasons[reason] += 1
        tagged = dict(row)
        tagged["path_causal_overlay_allowed"] = use_overlay
        tagged["path_causal_precedence_reason"] = reason
        if use_overlay:
            allowed.append(tagged)
        else:
            preserved.append(tagged)

    adjusted_allowed, capacity_diag = capacity._apply(
        allowed,
        by_day=by_day,
        variant="EQ50_COMPRESSED_ACCEPT_RUN25",
    )
    combined = sorted(
        [*adjusted_allowed, *preserved],
        key=lambda row: cast(str, row["signal_at"]),
    )
    return combined, {
        "precedence_reason_counts": dict(sorted(reasons.items())),
        "preserved_base_count": len(preserved),
        "overlay_evaluated_count": len(allowed),
        "capacity_diagnostics": capacity_diag,
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
        raise ValueError("path-causal target ladder requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    adjusted, path_diag = _apply_path_causal(rows, by_day=by_day)
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
        "physical_path_precedence_enforced": True,
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
        "path_diagnostics": path_diag,
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
            "development_only": True,
            "parameter_search": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "risk_policy_changed": False,
            "eq_fraction_changed": False,
            "dol1_policy_changed": False,
            "runner_selector_changed": False,
            "runner_target_changed": False,
            "runner_ps2_changed": False,
            "base_1_25_partial_never_retroactively_reallocated": True,
            "same_m1_1_25_eq_preserves_base": True,
            "future_runtime_input": False,
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
                "trade_count": payload["trade_count"],
                "metrics": payload["metrics"],
                "monte_carlo": payload["monte_carlo"],
                "objectives": payload["objectives"],
                "path_diagnostics": payload["path_diagnostics"],
                "passes": payload["passes_economic_objectives"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
