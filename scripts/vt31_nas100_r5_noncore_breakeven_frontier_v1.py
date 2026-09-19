"""Earlier breakeven frontier for VT31 NAS100 non-CORE first positions.

Consumed development evidence only.

CORE keeps its exact plan. SECONDARY/SCOUT keep the exact same authorization,
entry, structural stop, structural target and lifecycle. Only the predeclared
breakeven arming threshold is changed from source 3R to a lower fixed R level.

The underlying baseline simulator checks stop/target first, then arms BE only
after the bar closes, so a threshold touch can affect the stop no earlier than
the next bar. This avoids same-bar path assumptions and preserves causal order.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.noncore_breakeven_frontier.v1"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")
BE_LEVELS = (
    Decimal("0.75"),
    Decimal("1.00"),
    Decimal("1.25"),
    Decimal("1.50"),
    Decimal("2.00"),
)


def _with_be_boundary(setup: object, be_r: Decimal) -> object:
    entry = setup.entry_price
    risk = setup.initial_risk
    side = setup.side.value
    boundary = (
        entry + risk * be_r
        if side == "long"
        else entry - risk * be_r
    )
    return replace(setup, three_r_price=boundary)


def replay(path: Path, *, partition: str) -> dict[str, object]:
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("breakeven frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants: dict[str, object] = {}
    original_simulate = specialist.baseline._simulate

    for be_r in BE_LEVELS:
        def be_simulate(
            day_bars: tuple[object, ...],
            setup: object,
            *,
            _be_r: Decimal = be_r,
        ) -> dict[str, object]:
            adjusted = _with_be_boundary(setup, _be_r)
            outcome = original_simulate(day_bars, adjusted)
            if outcome.get("status") == "terminal":
                outcome["management_family"] = (
                    f"NONCORE_BE_{format(_be_r, 'f')}R_NEXT_BAR"
                )
                outcome["be_arm_threshold_r"] = format(_be_r, "f")
            return outcome

        specialist.baseline._simulate = be_simulate
        try:
            first_rows, first_diag = corrective._first_rows(
                by_day,
                context_by_day,
                evidence=evidence,
                alt_partial_r=None,
                secondary_route_policy="ORIGINAL",
            )
        finally:
            specialist.baseline._simulate = original_simulate

        rearm_rows, rearm_diag = corrective._rearm_rows(
            by_day,
            context_by_day,
            first_rows,
            evidence=evidence,
            rearm_partial_r=None,
        )
        combined = sorted(
            [*first_rows, *rearm_rows],
            key=lambda row: cast(str, row["signal_at"]),
        )
        rows = engine._scale_capital_rows(
            combined,
            scalar=GLOBAL_SCALAR,
        )
        metrics = engine._capital_metrics(rows)
        name = f"ALT_BE_{format(be_r, 'f').replace('.', '')}"
        mc = engine._monte_carlo(
            rows,
            variant=f"NONCORE_BE:{name}:{partition}",
        )
        tier_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            tier_counts[str(row.get("tier"))] += 1

        variants[name] = {
            "trade_count": len(rows),
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "tier_counts": dict(sorted(tier_counts.items())),
            "metrics": metrics,
            "monte_carlo": mc,
            "be_arm_threshold_r": format(be_r, "f"),
            "first_diagnostics": first_diag,
            "rearm_diagnostics": rearm_diag,
            "objectives": {
                "density_300_350": 300 <= len(rows) <= 350,
                "pf_ge_1_50": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("1.50")
                ),
                "dd_le_6": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("6")
                ),
                "mc_positive_ge_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_le_15": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    specialist.baseline._simulate = original_simulate

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "variants": variants,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "core_plan_changed": False,
            "noncore_authorization_changed": False,
            "entry_changed": False,
            "structural_stop_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "be_activates_no_earlier_than_next_bar": True,
            "same_bar_threshold_stop_order_assumed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_target_trade_count_at_runtime": False,
            "global_risk_scalar": "0.60",
            "policy_promoted": False,
            "opens_new_holdout": False,
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
