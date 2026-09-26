"""V18 incremental autonomous Shared defense on top of the frozen V16 frontier.

V16 remains the consumed economic frontier. V17 proved that a generic,
monotonic Shared loss-defense policy improves the raw baseline, but applying
that policy as a replacement for V16 sacrificed some PF/Total-R in consumed
windows.

V18 therefore tests a strictly incremental question:

    Can Shared preserve every frozen V16 intervention exactly, then add only
    recovery-vetoed CAP_HALF_RISK defense to positions V16 would otherwise
    leave untouched?

The inference rule is autonomous and generic. It contains no trader,
methodology, symbol, calendar or fold identity. The frozen external evidence is
only a scoring surface.

No sizing, capital weighting, signal suppression, stop widening, target
mutation, order authority or broker execution is allowed. Future path is used
only by the offline scorer to determine whether a previously-issued monotonic
loss boundary would subsequently have been reached.
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

import shared_autonomous_loss_defense_economic_shadow_v17 as v17
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
import vt08_index_shared_context_conditioned_economic_shadow_v16 as v16
import vt08_index_shared_terminal_failure_economic_shadow_v7 as v7

from qore.infrastructure.core_stack_v2.autonomous_loss_defense import (
    AutonomousDefenseAction,
)

IDENTITY = "QORE_SHARED_AUTONOMOUS_INCREMENTAL_DEFENSE_ECONOMIC_SHADOW_V18"
SCHEMA = "qore.shared.autonomous_incremental_defense_economic_shadow.v18"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V16_RUN = 36142389500
SOURCE_V17_RUN = 36145156033

ZERO = Decimal("0")
ONE = Decimal("1")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _moderate_defense_item(
    *,
    item: object,
    probability_rows: list[tuple[dict[str, Any], int]],
) -> tuple[object, dict[str, object] | None]:
    active_cap_r: Decimal | None = None
    signal_at: datetime | None = None
    signal_reasons: tuple[str, ...] = ()
    signal_probability_bps: int | None = None

    for row, probability_bps in probability_rows:
        directive = v17._directive(row, probability_bps)
        tightened_now = False
        if directive.action is AutonomousDefenseAction.CAP_HALF_RISK:
            requested_cap_r = -Decimal("0.50")
            if active_cap_r is None or requested_cap_r > active_cap_r:
                active_cap_r = requested_cap_r
                signal_at = directive.as_of.astimezone(UTC)
                signal_reasons = directive.reasons
                signal_probability_bps = probability_bps
                tightened_now = True

        if active_cap_r is None:
            continue

        current_r = _d(row["current_position_r"])
        if current_r > active_cap_r:
            continue

        shadow_exit_at = datetime.fromisoformat(str(row["as_of"]))
        if shadow_exit_at.tzinfo is None or shadow_exit_at.utcoffset() is None:
            raise ValueError("V18 shadow exit timestamp must be timezone-aware")
        shadow_exit_at = shadow_exit_at.astimezone(UTC)
        canonical_exit_at = item.exited_at.astimezone(UTC)
        if shadow_exit_at >= canonical_exit_at:
            continue

        shadow_r = current_r if tightened_now and current_r < active_cap_r else active_cap_r
        managed = replace(
            item,
            outcome=replace(
                item.outcome,
                exited_at=shadow_exit_at,
                r_multiple=shadow_r,
                exit_reason="SHARED_V18_INCREMENTAL_CAP_HALF_RISK",
            ),
        )
        canonical_r = _d(item.outcome.r_multiple)
        return managed, {
            "trade_id": item.trade_id,
            "market": item.symbol,
            "action": AutonomousDefenseAction.CAP_HALF_RISK.value,
            "signal_at": None if signal_at is None else signal_at.isoformat(),
            "shadow_exit_at": shadow_exit_at.isoformat(),
            "canonical_exit_at": canonical_exit_at.isoformat(),
            "cap_r": str(active_cap_r),
            "canonical_r": str(canonical_r),
            "shadow_r": str(shadow_r),
            "delta_r": str(shadow_r - canonical_r),
            "canonical_outcome": (
                "LOSS" if canonical_r < ZERO else "WIN" if canonical_r > ZERO else "FLAT"
            ),
            "probability_bps": signal_probability_bps,
            "reasons": list(signal_reasons),
        }

    return item, None


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
    if len(control) != int(ledger_window["sample"]):
        raise ValueError(f"V18 {window_id} frozen-ledger density drift")

    trades = list(ledger_window["rows"])
    by_id = {int(row["trade_id"]): row for row in trades}
    probability_by_trade = v17._probability_rows(
        model=model,
        ledger_window=ledger_window,
    )
    context_by_id = v16._context_crossings(
        model=model,
        window=ledger_window,
    )

    v16_items: list[object] = []
    v18_items: list[object] = []
    incremental_rows: list[dict[str, object]] = []

    for item in control:
        trade_id = int(item.trade_id)
        trade_row = by_id[trade_id]
        chosen, source = v16._chosen_row(
            trade_row=trade_row,
            context_row=context_by_id.get(trade_id),
        )
        if chosen is not None and source is not None:
            frozen_v16 = v16._apply_shadow_exit(
                item=item,
                row=chosen,
                reason=f"SHARED_V16_{source}",
            )
            v16_items.append(frozen_v16)
            v18_items.append(frozen_v16)
            continue

        v16_items.append(item)
        managed, changed = _moderate_defense_item(
            item=item,
            probability_rows=probability_by_trade.get(trade_id, []),
        )
        v18_items.append(managed)
        if changed is not None:
            incremental_rows.append(changed)

    v16_tuple = tuple(v16_items)
    v18_tuple = tuple(v18_items)

    baseline = v7.v6.v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    reconstructed_v16 = v7.v6.v3.v2.r108._bundle(
        v16_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    v18_shadow = v7.v6.v3.v2.r108._bundle(
        v18_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )

    official_v16 = v16._window(
        roots=roots,
        window_id=window_id,
        ledger_window=ledger_window,
        model=model,
    )["v16_shadow"]
    for section in ("primary", "secondary", "primary_conservative_mtm"):
        if reconstructed_v16[section] != official_v16[section]:
            raise ValueError(f"V18 {window_id} failed frozen V16 reconstruction")

    changed_losses = [
        row for row in incremental_rows if row["canonical_outcome"] == "LOSS"
    ]
    changed_winners = [
        row for row in incremental_rows if row["canonical_outcome"] == "WIN"
    ]
    saved_loss_r = sum((_d(row["delta_r"]) for row in changed_losses), ZERO)
    winner_delta_r = sum((_d(row["delta_r"]) for row in changed_winners), ZERO)
    retention = v17._retention(control=control, managed=v18_tuple)

    v16_pf = _d(reconstructed_v16["primary"]["profit_factor"] or 0)
    v18_pf = _d(v18_shadow["primary"]["profit_factor"] or 0)
    v16_dd = _d(reconstructed_v16["primary_conservative_mtm"]["max_drawdown_r"])
    v18_dd = _d(v18_shadow["primary_conservative_mtm"]["max_drawdown_r"])
    v16_total_r = _d(reconstructed_v16["primary"]["total_r"])
    v18_total_r = _d(v18_shadow["primary"]["total_r"])

    pass_window = (
        bool(incremental_rows)
        and v18_pf > v16_pf
        and v18_dd < v16_dd
        and v18_total_r >= v16_total_r
        and _d(retention["winner_count_retention"]) >= Decimal("0.98")
        and _d(retention["winner_r_retention"]) >= Decimal("0.90")
    )

    return {
        "window_id": window_id,
        "sample": len(control),
        "density_retained_shadow": "1",
        "frozen_v16_reconstruction_matches": True,
        "incremental_defense_exit_count": len(incremental_rows),
        "incremental_defense_loss_count": len(changed_losses),
        "incremental_defense_winner_count": len(changed_winners),
        "incremental_saved_loss_r": str(saved_loss_r),
        "incremental_winner_delta_r": str(winner_delta_r),
        "incremental_net_utility_r": str(saved_loss_r + winner_delta_r),
        "winner_retention": retention,
        "baseline": baseline,
        "v16_shadow": reconstructed_v16,
        "v18_shadow": v18_shadow,
        "economic_delta_vs_baseline": v16._bundle_delta(
            baseline=baseline,
            shadow=v18_shadow,
        ),
        "incremental_economic_delta_vs_v16": v16._bundle_delta(
            baseline=reconstructed_v16,
            shadow=v18_shadow,
        ),
        "pass_window": pass_window,
        "contract": {
            "shared_policy_is_autonomous": True,
            "shared_policy_is_trader_agnostic": True,
            "symbol_identity_in_inference_rule": False,
            "methodology_identity_in_inference_rule": False,
            "calendar_identity_in_inference_rule": False,
            "fold_identity_in_inference_rule": False,
            "v16_interventions_preserved_exactly": True,
            "incremental_defense_only_on_v16_untouched_positions": True,
            "same_opportunity_universe": True,
            "same_trade_count": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "stop_improvement_research_used": True,
            "stop_widening_used": False,
            "target_mutation_used": False,
            "target_extension_used": False,
            "future_outcome_input_used": False,
            "future_market_input_used_by_runtime_policy": False,
            "future_path_used_for_offline_scoring_only": True,
            "broker_execution_authority": False,
        },
        "incremental_changed_rows": incremental_rows,
        "provenance": provenance,
    }


def run(
    *,
    ledger_json: Path,
    roots: dict[str, Path],
) -> dict[str, object]:
    ledger = json.loads(ledger_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    model, _, _, _ = v15._fit_v9(ledger)
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
        "source_v16_run": SOURCE_V16_RUN,
        "source_v17_run": SOURCE_V17_RUN,
        "shared_autonomous_policy": True,
        "trader_specific_inference": False,
        "research_only": True,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "windows": windows,
        "consumed_frontier_pass": all(
            bool(window["pass_window"])
            for window in windows.values()
        ),
        "governance": {
            "phase": "PHASE_2_INCREMENTAL_AUTONOMOUS_DEFENSE_RESEARCH_ONLY",
            "runtime_actuation": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
            "sizing_used": False,
            "risk_weighting_used": False,
            "broker_execution_authority": False,
        },
    }


def _parse_market_roots(values: list[str]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for value in values:
        market, separator, path = value.partition("=")
        if not separator or not market or not path:
            raise ValueError("--market-root must use MARKET=/path form")
        roots[market] = Path(path)
    if not roots:
        raise ValueError("at least one market root is required")
    return roots


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-json", type=Path, required=True)
    parser.add_argument("--market-root", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        ledger_json=args.ledger_json,
        roots=_parse_market_roots(args.market_root),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "consumed_frontier_pass": payload["consumed_frontier_pass"],
                "windows": {
                    key: {
                        "pass_window": value["pass_window"],
                        "incremental_exit_count": value[
                            "incremental_defense_exit_count"
                        ],
                        "incremental_saved_loss_r": value[
                            "incremental_saved_loss_r"
                        ],
                        "incremental_winner_delta_r": value[
                            "incremental_winner_delta_r"
                        ],
                        "winner_retention": value["winner_retention"],
                        "vs_v16": value["incremental_economic_delta_vs_v16"],
                    }
                    for key, value in payload["windows"].items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
