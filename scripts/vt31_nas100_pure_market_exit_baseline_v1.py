"""VT31 NAS100 pure-market exit baseline V1.

Owner sovereign pure-edge certification research.

This replay holds admission, entry, initial structural invalidation, structural
destination and lifecycle constant. It compares:

- LEGACY_3R_BE: historical research baseline with 3R -> breakeven management.
- PURE_MARKET_EXIT: no R threshold is consulted during execution.

PURE_MARKET_EXIT can terminate only through:
- original structural invalidation;
- original structural target;
- 16:00 NY lifecycle.

R is computed only after the economic path is resolved, for evaluation metrics.
No sizing, leverage, compounding, capital weighting, absolute volume or
provider-volume rule is used.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_cognitive_structural_protection_frontier_v1 as metrics_lib
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.pure_market_exit_baseline.v1"
MARKET = "NAS100"
VARIANTS = ("LEGACY_3R_BE", "PURE_MARKET_EXIT")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _terminal_r(
    *,
    side: str,
    entry: Decimal,
    price: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    if side == "short":
        return (entry - price) / risk
    raise ValueError(side)


def _pure_market_simulate(
    day_bars: tuple[object, ...],
    setup: object,
) -> dict[str, object]:
    """Resolve by structure/target/lifecycle only; R never changes execution."""

    side = str(getattr(getattr(setup, "side"), "value"))
    entry = _d(getattr(setup, "entry_price"))
    stop = _d(getattr(setup, "stop_price"))
    target = _d(getattr(setup, "target_price"))
    risk_points = abs(entry - stop)
    if risk_points <= 0:
        return {"status": "censored-invalid-geometry"}

    fill_index = v2b._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    first_low = _d(getattr(first, "low"))
    first_high = _d(getattr(first, "high"))
    stop_hit = first_low <= stop if side == "long" else first_high >= stop
    target_hit = first_high >= target if side == "long" else first_low <= target
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    exit_at: datetime | None = None
    exit_reason: str | None = None
    exit_price: Decimal | None = None

    # Excursion telemetry is evaluation-only. It never affects control flow.
    max_favorable_points = Decimal(0)
    max_adverse_points = Decimal(0)

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        if side == "long":
            max_favorable_points = max(max_favorable_points, high - entry)
            max_adverse_points = max(max_adverse_points, entry - low)
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            max_favorable_points = max(max_favorable_points, entry - low)
            max_adverse_points = max(max_adverse_points, high - entry)
            hit_stop = high >= stop
            hit_target = low <= target

        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            exit_price = stop
            exit_reason = "structural-invalidation"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            exit_price = target
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

    if exit_price is None:
        eligible = [
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        ]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible[-1]
        exit_price = _d(getattr(final, "close"))
        exit_reason = "16:00-lifecycle"
        exit_at = cast(datetime, getattr(final, "closed_at"))

    r_multiple = _terminal_r(
        side=side,
        entry=entry,
        price=exit_price,
        risk=risk_points,
    )
    mfe_r = max_favorable_points / risk_points
    mae_r = max_adverse_points / risk_points
    return {
        "status": "terminal",
        "local_date": _day(getattr(setup, "decision_at")).isoformat(),
        "side": side,
        "signal_at": cast(datetime, getattr(setup, "decision_at"))
        .astimezone(UTC)
        .isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": str(getattr(getattr(setup, "selected_family"), "value")),
        "entry": format(entry, "f"),
        "initial_stop": format(stop, "f"),
        "structural_target": format(target, "f"),
        "exit_price": format(exit_price, "f"),
        "exit_reason": exit_reason,
        "r_multiple": format(r_multiple, "f"),
        "mfe_r_evaluation_only": format(mfe_r, "f"),
        "mae_r_evaluation_only": format(mae_r, "f"),
        "runtime_r_thresholds_consulted": False,
        "runtime_stop_moves": 0,
    }


def _halfyear(local_date: str) -> str:
    year, month = (int(value) for value in local_date.split("-")[:2])
    return f"{year}H{1 if month <= 6 else 2}"


def _group_metrics(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = (
            _halfyear(str(row["local_date"]))
            if key == "halfyear"
            else str(row[key])
        )
        grouped[value].append(row)
    return {
        name: metrics_lib._normalized_metrics(items)
        for name, items in sorted(grouped.items())
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("pure-market baseline requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    policy = oco.Vt31R22ExecutionPolicy()
    rows: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    status: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
        if selected is None:
            continue

        legacy = specialist.baseline._simulate(day_bars, selected)
        pure = _pure_market_simulate(day_bars, selected)
        trade_id = "|".join(
            (
                local_day.isoformat(),
                selected.decision_at.astimezone(UTC).isoformat(),
                selected.side.value,
                selected.selected_family.value,
            )
        )

        for variant, outcome in (
            ("LEGACY_3R_BE", legacy),
            ("PURE_MARKET_EXIT", pure),
        ):
            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            row = dict(outcome)
            row["trade_id"] = trade_id
            row["partition"] = partition
            rows[variant].append(row)

    baseline = rows["LEGACY_3R_BE"]
    reports: dict[str, object] = {}
    for variant, trades in rows.items():
        reports[variant] = {
            "terminal_count": len(trades),
            "normalized_metrics": metrics_lib._normalized_metrics(trades),
            "monte_carlo": specialist._monte_carlo(trades),
            "side_metrics": _group_metrics(trades, key="side"),
            "halfyear_metrics": _group_metrics(trades, key="halfyear"),
            "entry_family_metrics": _group_metrics(
                trades,
                key="entry_family",
            ),
            "winner_preservation_vs_legacy": (
                None
                if variant == "LEGACY_3R_BE"
                else metrics_lib._winner_preservation(
                    baseline,
                    trades,
                )
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in trades
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variant_reports": reports,
        "status_counts": dict(sorted(status.items())),
        "runtime_governance": {
            "r_used_for_admission": False,
            "r_used_for_entry": False,
            "r_used_for_invalidation": False,
            "r_used_for_stop_movement": False,
            "r_used_for_breakeven": False,
            "r_used_for_target": False,
            "r_used_for_exit": False,
            "r_used_for_trailing": False,
            "r_used_for_partials": False,
            "r_used_for_volume": False,
            "sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "volume_agnostic": True,
            "r_role": "post_trade_evaluation_only",
        },
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "pure_market_exit_uses_runtime_r_thresholds": False,
            "pure_market_exit_stop_moves": 0,
            "r_computed_for_evaluation_only": True,
            "normalized_equal_r_economics": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "provider_volume_rule_used": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
                "variant_reports": payload["variant_reports"],
                "runtime_governance": payload["runtime_governance"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
