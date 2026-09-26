"""V16 economic shadow for the frozen V15 context-conditioned frontier.

V15 found one generic Shared context that increased V7 terminal-loss recall on
consumed recent-2Y and R66 without adding validation winner marks:

    path_state=CONTESTED
    environment_state=FRAGILE
    V9 competing-risk probability >= 0.900

V16 freezes that exact policy and measures its economics. The shadow book exits
at the earliest causal Shared intervention between:
1. V7 TERMINAL_CONFIRMED; and
2. the frozen V15 context-conditioned crossing.

The control opportunity universe, trade count and initial unit size remain
identical. There is no sizing, risk weighting, signal suppression, stop/target
mutation, trailing, target extension, or runtime actuation. All evidence is
already consumed; this run cannot certify LIVE behavior.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import vt08_index_shared_competing_risk_calibration_v9 as v9
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
import vt08_index_shared_terminal_failure_economic_shadow_v7 as v7

IDENTITY = "QORE_SHARED_VT08_CONTEXT_CONDITIONED_ECONOMIC_SHADOW_V16"
SCHEMA = "qore.shared.vt08_context_conditioned_economic_shadow.v16"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V15_HEAD = "4ad057663740b450f97188ed25b896ce62da5a82"

POLICY_CELL = v15.Cell(
    fields=("path_state", "environment_state"),
    values=("CONTESTED", "FRAGILE"),
    probability_floor=Decimal("0.900"),
)
ZERO = Decimal("0")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _winner_or_loss(value: Decimal) -> str:
    if value < ZERO:
        return "LOSS"
    if value > ZERO:
        return "WIN"
    return "FLAT"


def _context_crossings(
    *,
    model: object,
    window: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    trades = list(window["rows"])
    x_rows, _, _, meta = v9._observation_dataset(trades)
    probabilities = model.predict_proba(x_rows)[:, 1]
    by_cell = v15._cell_crossings(
        cells=[POLICY_CELL],
        probabilities=probabilities,
        meta=meta,
    )[POLICY_CELL.key()]
    result: dict[int, dict[str, Any]] = {}
    for trade_index, crossing in by_cell.items():
        trade_id = int(trades[trade_index]["trade_id"])
        result[trade_id] = crossing.row
    return result


def _chosen_row(
    *,
    trade_row: dict[str, Any],
    context_row: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    terminal = trade_row["first_terminal_confirmed"]
    if terminal is None:
        return (
            (context_row, "V15_CONTEXT_CONDITIONED")
            if context_row is not None
            else (None, None)
        )
    if context_row is None:
        return terminal, "V7_TERMINAL_CONFIRMED"
    if int(context_row["bars_before_canonical_exit"]) > int(
        terminal["bars_before_canonical_exit"]
    ):
        return context_row, "V15_CONTEXT_CONDITIONED_EARLIER"
    return terminal, "V7_TERMINAL_CONFIRMED"


def _apply_shadow_exit(
    *,
    item: object,
    row: dict[str, Any],
    reason: str,
) -> object:
    shadow_r = _d(row["current_position_r"])
    shadow_exit_at = datetime.fromisoformat(str(row["as_of"]))
    if shadow_exit_at.tzinfo is None or shadow_exit_at.utcoffset() is None:
        raise ValueError("V16 shadow exit must be timezone-aware")
    shadow_exit_at = shadow_exit_at.astimezone(UTC)
    canonical_exit_at = item.exited_at.astimezone(UTC)
    if shadow_exit_at >= canonical_exit_at:
        raise ValueError("V16 shadow exit must precede canonical exit")
    return replace(
        item,
        outcome=replace(
            item.outcome,
            exited_at=shadow_exit_at,
            r_multiple=shadow_r,
            exit_reason=reason,
        ),
    )


def _bundle_delta(
    *,
    baseline: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, str]:
    baseline_primary = baseline["primary"]
    shadow_primary = shadow["primary"]
    baseline_secondary = baseline["secondary"]
    shadow_secondary = shadow["secondary"]
    baseline_dd = _d(baseline["primary_conservative_mtm"]["max_drawdown_r"])
    shadow_dd = _d(shadow["primary_conservative_mtm"]["max_drawdown_r"])
    return {
        "primary_profit_factor": str(
            _d(shadow_primary["profit_factor"] or 0)
            - _d(baseline_primary["profit_factor"] or 0)
        ),
        "primary_total_r": str(
            _d(shadow_primary["total_r"])
            - _d(baseline_primary["total_r"])
        ),
        "primary_conservative_mtm_dd_r": str(shadow_dd - baseline_dd),
        "primary_conservative_mtm_dd_improvement_r": str(
            baseline_dd - shadow_dd
        ),
        "secondary_profit_factor": str(
            _d(shadow_secondary["profit_factor"] or 0)
            - _d(baseline_secondary["profit_factor"] or 0)
        ),
        "secondary_total_r": str(
            _d(shadow_secondary["total_r"])
            - _d(baseline_secondary["total_r"])
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
    ledger_window: dict[str, Any],
    model: object,
) -> dict[str, object]:
    source_window_id = v7._source_window_id(window_id)
    (
        control,
        bars_by_symbol,
        opened_by_symbol,
        start_date,
        end_date,
        provenance,
    ) = v7._canonical_control(roots=roots, window_id=window_id)

    trades = list(ledger_window["rows"])
    by_id = {int(row["trade_id"]): row for row in trades}
    if len(control) != int(ledger_window["sample"]):
        raise ValueError(f"V16 {window_id} frozen-ledger density drift")

    context_by_id = _context_crossings(
        model=model,
        window=ledger_window,
    )

    v7_managed: list[object] = []
    v16_managed: list[object] = []
    v16_changed: list[dict[str, object]] = []

    for item in control:
        trade_id = int(item.trade_id)
        trade_row = by_id[trade_id]
        terminal = trade_row["first_terminal_confirmed"]

        if terminal is None:
            v7_managed.append(item)
        else:
            v7_managed.append(
                _apply_shadow_exit(
                    item=item,
                    row=terminal,
                    reason="SHARED_V7_TERMINAL_CONFIRMED_SHADOW",
                )
            )

        chosen, source = _chosen_row(
            trade_row=trade_row,
            context_row=context_by_id.get(trade_id),
        )
        if chosen is None or source is None:
            v16_managed.append(item)
            continue

        managed = _apply_shadow_exit(
            item=item,
            row=chosen,
            reason=f"SHARED_V16_{source}",
        )
        v16_managed.append(managed)

        canonical_r = _d(item.outcome.r_multiple)
        shadow_r = _d(chosen["current_position_r"])
        v16_changed.append(
            {
                "trade_id": item.trade_id,
                "market": item.symbol,
                "source": source,
                "canonical_exit_at": item.exited_at.astimezone(UTC).isoformat(),
                "shadow_exit_at": managed.outcome.exited_at.astimezone(UTC).isoformat(),
                "canonical_r": str(canonical_r),
                "shadow_r": str(shadow_r),
                "delta_r": str(shadow_r - canonical_r),
                "canonical_outcome": _winner_or_loss(canonical_r),
                "bars_before_canonical_exit": int(
                    chosen["bars_before_canonical_exit"]
                ),
            }
        )

    baseline = v7.v6.v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    v7_shadow = v7.v6.v3.v2.r108._bundle(
        tuple(v7_managed),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    v16_shadow = v7.v6.v3.v2.r108._bundle(
        tuple(v16_managed),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )

    changed_losses = [
        row for row in v16_changed if row["canonical_outcome"] == "LOSS"
    ]
    changed_winners = [
        row for row in v16_changed if row["canonical_outcome"] == "WIN"
    ]
    saved_loss_r = sum((_d(row["delta_r"]) for row in changed_losses), ZERO)
    winner_delta_r = sum((_d(row["delta_r"]) for row in changed_winners), ZERO)
    net_delta_r = saved_loss_r + winner_delta_r

    v15_sources = {
        "V15_CONTEXT_CONDITIONED",
        "V15_CONTEXT_CONDITIONED_EARLIER",
    }
    v15_changed = [
        row for row in v16_changed if row["source"] in v15_sources
    ]

    return {
        "window_id": window_id,
        "sample": len(control),
        "canonical_expected": int(ledger_window["sample"]),
        "density_retained_shadow": "1",
        "policy_cell": POLICY_CELL.key(),
        "combined_exit_count": len(v16_changed),
        "combined_exit_loss_count": len(changed_losses),
        "combined_exit_winner_count": len(changed_winners),
        "v15_context_selected_exit_count": len(v15_changed),
        "v15_context_only_exit_count": sum(
            row["source"] == "V15_CONTEXT_CONDITIONED"
            for row in v15_changed
        ),
        "v15_context_earlier_than_v7_count": sum(
            row["source"] == "V15_CONTEXT_CONDITIONED_EARLIER"
            for row in v15_changed
        ),
        "saved_loss_r": str(saved_loss_r),
        "winner_delta_r": str(winner_delta_r),
        "net_shadow_utility_r": str(net_delta_r),
        "baseline": baseline,
        "v7_shadow": v7_shadow,
        "v16_shadow": v16_shadow,
        "economic_delta_vs_baseline": _bundle_delta(
            baseline=baseline,
            shadow=v16_shadow,
        ),
        "incremental_economic_delta_vs_v7": _bundle_delta(
            baseline=v7_shadow,
            shadow=v16_shadow,
        ),
        "contract": {
            "shadow_only": True,
            "same_opportunity_universe": True,
            "same_trade_count": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "stop_mutation_used": False,
            "target_mutation_used": False,
            "trailing_used": False,
            "target_extension_used": False,
            "only_frozen_v7_or_v15_exit_change": True,
            "future_outcome_input_used": False,
            "realized_outcome_used_for_scoring_only": True,
        },
        "changed_rows": v16_changed,
        "provenance": provenance,
    }


def run(
    *,
    v6_json: Path,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen V6 identity")

    model, _, _, _ = v15._fit_v9(ledger)
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    windows = {
        key: _window(
            roots=roots,
            window_id=key,
            ledger_window=ledger[key],
            model=model,
        )
        for key in (
            "five_year",
            "recent_two_year",
            "r66_consumed_failed_holdout",
        )
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v15_run": SOURCE_V15_RUN,
        "source_v15_head": SOURCE_V15_HEAD,
        "frozen_policy_cell": POLICY_CELL.key(),
        "v15_validation_pass_required": True,
        "research_only": True,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "windows": windows,
        "governance": {
            "same_opportunity_universe": True,
            "same_trade_count": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "stop_mutation_used": False,
            "target_mutation_used": False,
            "trailing_used": False,
            "target_extension_used": False,
            "runtime_actuation": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = run(
        v6_json=args.v6_json,
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": result["identity"],
                "policy": result["frozen_policy_cell"],
                "windows": {
                    key: {
                        "counts": {
                            "combined": value["combined_exit_count"],
                            "v15": value["v15_context_selected_exit_count"],
                            "v15_only": value["v15_context_only_exit_count"],
                            "v15_earlier": value["v15_context_earlier_than_v7_count"],
                        },
                        "net_shadow_utility_r": value["net_shadow_utility_r"],
                        "vs_baseline": value["economic_delta_vs_baseline"],
                        "vs_v7": value["incremental_economic_delta_vs_v7"],
                    }
                    for key, value in result["windows"].items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
