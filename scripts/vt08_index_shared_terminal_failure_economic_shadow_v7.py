"""VT08 Index economic shadow for Shared terminal-failure confirmation.

V7 changes exactly one thing relative to the canonical equal-size VT08
falsification book: when Shared causally emits TERMINAL_CONFIRMED before the
canonical exit, the shadow book closes that trade at the already-observed M15
close R recorded by V6.

Everything else remains identical:
- same methodology-valid opportunities;
- same trade count and markets;
- same initial unit size;
- no sizing or risk weighting;
- no signal suppression;
- no stop widening or target reduction;
- no trailing or target extension;
- no trader-specific cognition inside Shared.

All evidence windows are already consumed. This run measures economics and can
falsify/support the phase-one mechanism, but it cannot certify LIVE behavior.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import vt08_index_shared_stop_target_discrimination_v6 as v6

SCHEMA = "qore.shared.vt08_index.terminal_failure_economic_shadow.v7"
IDENTITY = "QORE_SHARED_VT08_INDEX_TERMINAL_FAILURE_ECONOMIC_SHADOW_V7"
ZERO = Decimal("0")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _source_window_id(window_id: str) -> str:
    return {
        "five_year": "5Y",
        "recent_two_year": "2Y",
        "r66_consumed_failed_holdout": "R66",
    }[window_id]


def _canonical_control(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
    tuple[object, ...],
    dict[str, tuple[object, ...]],
    dict[str, tuple[datetime, ...]],
    object,
    object,
    dict[str, object],
]:
    source_window_id = _source_window_id(window_id)
    canonical, bars_raw, provenance = v6.v3.v2.r74._load_window(
        roots=roots,
        window_id=source_window_id,
    )
    start_date, end_date, expected = v6.v3.v2.r74._window_contract(source_window_id)
    bars_by_symbol = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    base, _ = v6.v3.v2.r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = v6.v3.v2.r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=v6.v3.v2.r102.POLICY_EXPLICIT_FULL,
    )
    control = v6.v3.v2._unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 Shared V7 {window_id} density drift")
    return (
        tuple(control),
        bars_by_symbol,
        opened_by_symbol,
        start_date,
        end_date,
        provenance,
    )


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    source_window_id = _source_window_id(window_id)
    shadow = v6._window(roots=roots, window_id=window_id)
    (
        control,
        bars_by_symbol,
        opened_by_symbol,
        start_date,
        end_date,
        provenance,
    ) = _canonical_control(roots=roots, window_id=window_id)

    shadow_by_id = {
        int(row["trade_id"]): row
        for row in shadow["rows"]
    }
    managed: list[object] = []
    changed_rows: list[dict[str, object]] = []

    for item in control:
        row = shadow_by_id[int(item.trade_id)]
        first_terminal = row["first_terminal_confirmed"]
        if first_terminal is None:
            managed.append(item)
            continue

        canonical_r = _d(item.outcome.r_multiple)
        shadow_r = _d(first_terminal["current_position_r"])
        shadow_exit_at = datetime.fromisoformat(str(first_terminal["as_of"]))
        if shadow_exit_at.tzinfo is None or shadow_exit_at.utcoffset() is None:
            raise ValueError("terminal shadow exit must be timezone-aware")
        shadow_exit_at = shadow_exit_at.astimezone(UTC)
        if shadow_exit_at >= item.exited_at.astimezone(UTC):
            raise ValueError("terminal shadow exit must precede canonical exit")

        shadow_outcome = replace(
            item.outcome,
            exited_at=shadow_exit_at,
            r_multiple=shadow_r,
            exit_reason="SHARED_TERMINAL_CONFIRMED_SHADOW",
        )
        managed_item = replace(item, outcome=shadow_outcome)
        managed.append(managed_item)
        changed_rows.append(
            {
                "trade_id": item.trade_id,
                "market": item.symbol,
                "canonical_exit_at": item.exited_at.astimezone(UTC).isoformat(),
                "shadow_exit_at": shadow_exit_at.isoformat(),
                "canonical_r": str(canonical_r),
                "shadow_r": str(shadow_r),
                "delta_r": str(shadow_r - canonical_r),
                "canonical_outcome": (
                    "LOSS" if canonical_r < ZERO else "WIN" if canonical_r > ZERO else "FLAT"
                ),
                "bars_before_canonical_exit": first_terminal[
                    "bars_before_canonical_exit"
                ],
            }
        )

    managed_tuple = tuple(managed)
    if len(managed_tuple) != len(control):
        raise ValueError("terminal shadow changed trade density")

    baseline = v6.v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    terminal_shadow = v6.v3.v2.r108._bundle(
        managed_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )

    changed_losses = [
        row for row in changed_rows if row["canonical_outcome"] == "LOSS"
    ]
    changed_winners = [
        row for row in changed_rows if row["canonical_outcome"] == "WIN"
    ]
    saved_loss_r = sum((_d(row["delta_r"]) for row in changed_losses), ZERO)
    winner_delta_r = sum((_d(row["delta_r"]) for row in changed_winners), ZERO)
    net_delta_r = saved_loss_r + winner_delta_r

    baseline_primary = baseline["primary"]
    shadow_primary = terminal_shadow["primary"]
    baseline_secondary = baseline["secondary"]
    shadow_secondary = terminal_shadow["secondary"]
    baseline_dd = _d(baseline["primary_conservative_mtm"]["max_drawdown_r"])
    shadow_dd = _d(
        terminal_shadow["primary_conservative_mtm"]["max_drawdown_r"]
    )

    return {
        "window_id": window_id,
        "sample": len(control),
        "canonical_expected": len(control),
        "density_retained_shadow": "1",
        "terminal_exit_count": len(changed_rows),
        "terminal_exit_loss_count": len(changed_losses),
        "terminal_exit_winner_count": len(changed_winners),
        "saved_loss_r": str(saved_loss_r),
        "winner_delta_r": str(winner_delta_r),
        "net_shadow_utility_r": str(net_delta_r),
        "baseline": baseline,
        "terminal_shadow": terminal_shadow,
        "economic_delta": {
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
        },
        "phase_1_contract": {
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
            "terminal_confirmation_only_exit_change": True,
            "future_outcome_input_used": False,
            "realized_outcome_used_for_scoring_only": True,
        },
        "changed_rows": changed_rows,
        "provenance": provenance,
    }


def run(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "source_pr": 604,
            "source_head": v6.v3.VT08_HEAD,
            "shared_is_only_cognitive_engine": True,
            "vt08_role": "METHODOLOGY_VALID_FALSIFICATION_SURFACE_ONLY",
            "vt08_cognition_used_by_shared": False,
            "vt31_cognition_used_by_shared": False,
            "phase": "PHASE_1_NATURAL_DD_ECONOMIC_SHADOW",
            "same_opportunity_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "trailing_used": False,
            "target_extension_used": False,
        },
        "five_year": _window(roots=roots, window_id="five_year"),
        "recent_two_year": _window(roots=roots, window_id="recent_two_year"),
        "r66_consumed_failed_holdout": _window(
            roots=roots,
            window_id="r66_consumed_failed_holdout",
        ),
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(v6.v3._jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "five_year": payload["five_year"]["economic_delta"],
                "recent_two_year": payload["recent_two_year"]["economic_delta"],
                "r66": payload["r66_consumed_failed_holdout"]["economic_delta"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
