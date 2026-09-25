"""V17 autonomous Shared loss-defense economic shadow.

This research stage is Shared-first and trader-agnostic. The inference policy
contains no trader, methodology, symbol, calendar or fold identity. A frozen
external consumed trade surface is used only to score the economic consequence
of Shared directives after the fact.

V17 moves from classification to research-only monotonic defense:
- terminal-confirmed or the frozen high-confidence contested/fragile context
  caps maximum loss at 0.25R;
- high competing-risk probability with adverse/failure path state caps maximum
  loss at 0.50R;
- active/restored recovery and healthy/recovering winner paths veto the
  moderate defense;
- a loss boundary can only tighten, never widen.

No sizing, capital weighting, order authorization or broker execution is owned
by Shared. Future path is used only by the offline scorer to determine whether a
causally issued stop-equivalent boundary would later have been reached.
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
import vt08_index_shared_context_conditioned_economic_shadow_v16 as v16
import vt08_index_shared_terminal_failure_economic_shadow_v7 as v7

from qore.infrastructure.core_stack_v2.autonomous_loss_defense import (
    AutonomousDefenseAction,
    AutonomousLossDefenseEvidence,
    assess_autonomous_loss_defense,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import PositionPathState
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
)
from qore.infrastructure.core_stack_v2.terminal_failure_confirmation import (
    TerminalFailureState,
)

IDENTITY = "QORE_SHARED_AUTONOMOUS_LOSS_DEFENSE_ECONOMIC_SHADOW_V17"
SCHEMA = "qore.shared.autonomous_loss_defense_economic_shadow.v17"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V16_RUN = 36142389500

ZERO = Decimal("0")
ONE = Decimal("1")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _winner_or_loss(value: Decimal) -> str:
    if value < ZERO:
        return "LOSS"
    if value > ZERO:
        return "WIN"
    return "FLAT"


def _probability_rows(
    *,
    model: object,
    ledger_window: dict[str, Any],
) -> dict[int, list[tuple[dict[str, Any], int]]]:
    trades = list(ledger_window["rows"])
    x_rows, _, _, meta = v9._observation_dataset(trades)
    probabilities = model.predict_proba(x_rows)[:, 1]

    result: dict[int, list[tuple[dict[str, Any], int]]] = {}
    for probability, (trade_index, row) in zip(probabilities, meta, strict=True):
        trade_id = int(trades[trade_index]["trade_id"])
        probability_bps = max(
            0,
            min(10_000, int(round(float(probability) * 10_000))),
        )
        result.setdefault(trade_id, []).append((row, probability_bps))
    return result


def _directive(
    row: dict[str, Any],
    probability_bps: int,
) -> object:
    as_of = datetime.fromisoformat(str(row["as_of"]))
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("V17 evidence timestamp must be timezone-aware")
    return assess_autonomous_loss_defense(
        AutonomousLossDefenseEvidence(
            as_of=as_of.astimezone(UTC),
            data_integrity_bps=10_000,
            competing_risk_probability_bps=probability_bps,
            path_state=PositionPathState(str(row["path_state"])),
            environment_state=MarketEnvironmentState(str(row["environment_state"])),
            recovery_state=RecoveryChallengeState(
                str(row["recovery_challenge_state"])
            ),
            terminal_failure_state=TerminalFailureState(
                str(row["terminal_failure_state"])
            ),
        )
    )


def _managed_item(
    *,
    item: object,
    probability_rows: list[tuple[dict[str, Any], int]],
) -> tuple[object, dict[str, object] | None]:
    active_cap_r: Decimal | None = None
    active_action: AutonomousDefenseAction | None = None
    active_reasons: tuple[str, ...] = ()
    active_signal_at: datetime | None = None

    for row, probability_bps in probability_rows:
        directive = _directive(row, probability_bps)
        current_r = _d(row["current_position_r"])
        tightened_now = False

        if directive.maximum_loss_r is not None:
            requested_cap_r = -directive.maximum_loss_r
            if active_cap_r is None or requested_cap_r > active_cap_r:
                active_cap_r = requested_cap_r
                active_action = directive.action
                active_reasons = directive.reasons
                active_signal_at = directive.as_of.astimezone(UTC)
                tightened_now = True

        if active_cap_r is None or current_r > active_cap_r:
            continue

        shadow_exit_at = datetime.fromisoformat(str(row["as_of"]))
        if shadow_exit_at.tzinfo is None or shadow_exit_at.utcoffset() is None:
            raise ValueError("V17 shadow exit timestamp must be timezone-aware")
        shadow_exit_at = shadow_exit_at.astimezone(UTC)
        canonical_exit_at = item.exited_at.astimezone(UTC)
        if shadow_exit_at >= canonical_exit_at:
            continue

        shadow_r = (
            current_r
            if tightened_now and current_r < active_cap_r
            else active_cap_r
        )
        managed = replace(
            item,
            outcome=replace(
                item.outcome,
                exited_at=shadow_exit_at,
                r_multiple=shadow_r,
                exit_reason=f"SHARED_V17_{active_action.value}",
            ),
        )
        canonical_r = _d(item.outcome.r_multiple)
        return managed, {
            "trade_id": item.trade_id,
            "market": item.symbol,
            "action": active_action.value,
            "reasons": list(active_reasons),
            "signal_at": (
                None if active_signal_at is None else active_signal_at.isoformat()
            ),
            "shadow_exit_at": shadow_exit_at.isoformat(),
            "canonical_exit_at": canonical_exit_at.isoformat(),
            "cap_r": str(active_cap_r),
            "canonical_r": str(canonical_r),
            "shadow_r": str(shadow_r),
            "delta_r": str(shadow_r - canonical_r),
            "canonical_outcome": _winner_or_loss(canonical_r),
            "probability_bps": probability_bps,
        }

    return item, None


def _retention(
    *,
    control: tuple[object, ...],
    managed: tuple[object, ...],
) -> dict[str, str | int]:
    canonical_winners = [
        _d(item.outcome.r_multiple)
        for item in control
        if _d(item.outcome.r_multiple) > ZERO
    ]
    managed_by_id = {
        int(item.trade_id): _d(item.outcome.r_multiple)
        for item in managed
    }
    retained_winners = sum(
        managed_by_id[int(item.trade_id)] > ZERO
        for item in control
        if _d(item.outcome.r_multiple) > ZERO
    )
    canonical_winner_r = sum(canonical_winners, ZERO)
    managed_winner_r = sum(
        max(ZERO, managed_by_id[int(item.trade_id)])
        for item in control
        if _d(item.outcome.r_multiple) > ZERO
    )
    winner_count = len(canonical_winners)
    return {
        "canonical_winner_count": winner_count,
        "retained_winner_count": retained_winners,
        "winner_count_retention": str(
            ONE if winner_count == 0 else Decimal(retained_winners) / Decimal(winner_count)
        ),
        "canonical_winner_r": str(canonical_winner_r),
        "managed_winner_r": str(managed_winner_r),
        "winner_r_retention": str(
            ONE
            if canonical_winner_r == ZERO
            else managed_winner_r / canonical_winner_r
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
    if len(control) != int(ledger_window["sample"]):
        raise ValueError(f"V17 {window_id} frozen-ledger density drift")

    probability_by_trade = _probability_rows(
        model=model,
        ledger_window=ledger_window,
    )
    managed_items: list[object] = []
    changed_rows: list[dict[str, object]] = []

    for item in control:
        managed, changed = _managed_item(
            item=item,
            probability_rows=probability_by_trade.get(int(item.trade_id), []),
        )
        managed_items.append(managed)
        if changed is not None:
            changed_rows.append(changed)

    managed_tuple = tuple(managed_items)
    baseline = v7.v6.v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    v17_shadow = v7.v6.v3.v2.r108._bundle(
        managed_tuple,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    v16_result = v16._window(
        roots=roots,
        window_id=window_id,
        ledger_window=ledger_window,
        model=model,
    )
    v16_shadow = v16_result["v16_shadow"]

    changed_losses = [
        row for row in changed_rows if row["canonical_outcome"] == "LOSS"
    ]
    changed_winners = [
        row for row in changed_rows if row["canonical_outcome"] == "WIN"
    ]
    saved_loss_r = sum((_d(row["delta_r"]) for row in changed_losses), ZERO)
    winner_delta_r = sum((_d(row["delta_r"]) for row in changed_winners), ZERO)
    retention = _retention(control=control, managed=managed_tuple)

    baseline_primary_pf = _d(baseline["primary"]["profit_factor"] or 0)
    shadow_primary_pf = _d(v17_shadow["primary"]["profit_factor"] or 0)
    baseline_dd = _d(baseline["primary_conservative_mtm"]["max_drawdown_r"])
    shadow_dd = _d(v17_shadow["primary_conservative_mtm"]["max_drawdown_r"])
    baseline_total_r = _d(baseline["primary"]["total_r"])
    shadow_total_r = _d(v17_shadow["primary"]["total_r"])

    pass_window = (
        shadow_primary_pf > baseline_primary_pf
        and shadow_dd < baseline_dd
        and shadow_total_r >= baseline_total_r
        and _d(retention["winner_count_retention"]) >= Decimal("0.98")
        and _d(retention["winner_r_retention"]) >= Decimal("0.90")
    )

    return {
        "window_id": window_id,
        "sample": len(control),
        "density_retained_shadow": "1",
        "defense_exit_count": len(changed_rows),
        "defense_exit_loss_count": len(changed_losses),
        "defense_exit_winner_count": len(changed_winners),
        "saved_loss_r": str(saved_loss_r),
        "winner_delta_r": str(winner_delta_r),
        "net_shadow_utility_r": str(saved_loss_r + winner_delta_r),
        "winner_retention": retention,
        "baseline": baseline,
        "v16_shadow": v16_shadow,
        "v17_shadow": v17_shadow,
        "economic_delta_vs_baseline": v16._bundle_delta(
            baseline=baseline,
            shadow=v17_shadow,
        ),
        "economic_delta_vs_v16": v16._bundle_delta(
            baseline=v16_shadow,
            shadow=v17_shadow,
        ),
        "pass_window": pass_window,
        "contract": {
            "shared_policy_is_trader_agnostic": True,
            "symbol_identity_in_inference_rule": False,
            "calendar_identity_in_inference_rule": False,
            "fold_identity_in_inference_rule": False,
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
        "changed_rows": changed_rows,
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
        "shared_autonomous_policy": True,
        "trader_specific_inference": False,
        "research_only": True,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "windows": windows,
        "consumed_economic_pass": all(
            bool(window["pass_window"])
            for window in windows.values()
        ),
        "governance": {
            "phase": "PHASE_2_AUTONOMOUS_DEFENSE_RESEARCH_ONLY",
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
                "consumed_economic_pass": payload["consumed_economic_pass"],
                "windows": {
                    key: {
                        "pass_window": value["pass_window"],
                        "defense_exit_count": value["defense_exit_count"],
                        "saved_loss_r": value["saved_loss_r"],
                        "winner_delta_r": value["winner_delta_r"],
                        "winner_retention": value["winner_retention"],
                        "vs_baseline": value["economic_delta_vs_baseline"],
                        "vs_v16": value["economic_delta_vs_v16"],
                    }
                    for key, value in payload["windows"].items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
