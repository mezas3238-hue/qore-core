#!/usr/bin/env python3
"""Join frozen NY executed-control signals to historical ICT as-of evidence.

NO operation/filter/policy modifications. This tool checks what was causally
available by each of the 55 frozen signal timestamps, splits the 23-trade
drawdown episode, and labels PDH/PDL alignment *research hypothesis* only.
It never claims PDH/PDL is a universal ICT DOL, a completed MSS or actual fill.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA = "qore.vt31.ict_silver_bullet_3y_frozen_ny_alignment.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
NY = ZoneInfo("America/New_York")
FRICTION = Decimal("0.05")
EXPECTED_DD = Decimal("21.35859571830889503173217318")
EXPECTED_R = Decimal("25.49565121333850743720216933")
TOLERANCE = Decimal("0.000001")


def _dt(raw: object) -> datetime:
    x = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if x.tzinfo is None or x.utcoffset() is None:
        raise ValueError("naive source evidence")
    return x.astimezone(UTC)


def _d(raw: object) -> Decimal:
    return Decimal(str(raw))


def _s(value: Decimal) -> str:
    return format(value, "f")


def _group(trades: list[dict[str, Any]], by: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        groups[str(trade[by])].append(_d(trade["net_r"]))
    return {
        key: {
            "trades": len(values),
            "wins": sum(v > 0 for v in values),
            "losses": sum(v < 0 for v in values),
            "net_r": _s(sum(values, Decimal(0))),
            "negative_mass_r": _s(-sum(
                (v for v in values if v < 0), Decimal(0)
            )),
        }
        for key, values in sorted(groups.items())
    }


def build(
    *,
    replay: dict[str, Any],
    fvg_audit: dict[str, Any],
    pdh_census: dict[str, Any],
) -> dict[str, Any]:
    for item in (replay, fvg_audit, pdh_census):
        if item.get("base_id") != BASE_ID:
            raise ValueError("mixed 3Y bases")
    if replay.get("schema") != "qore.vt31.nas100.owner_3y_replay.v1":
        raise ValueError("wrong frozen replay")
    if fvg_audit.get("schema") != (
        "qore.vt31.ict_silver_bullet_ny_admitted_source_audit.v1"
    ):
        raise ValueError("wrong FVG comparison payload")
    if pdh_census.get("schema") != (
        "qore.vt31.ict_silver_bullet_3y_pdh_pdl_causal_capacity.v1"
    ):
        raise ValueError("wrong PDH/PDL research payload")
    if fvg_audit.get("frozen_control_trade_count") != 55:
        raise ValueError("frozen entry identity drift")
    g = replay["governance"]
    if g["fresh_independent_holdout_claimed"] is not False:
        raise ValueError("fresh holdout falsely opened")
    stack = replay["current_stack"]
    alias = stack["lab_control_alias"]
    rows = sorted(
        stack["variants"][alias]["candidate_rows"],
        key=lambda x: str(x["signal_at"]),
    )
    audit_by_signal = {
        _dt(x["signal_at"]): x for x in fvg_audit["annotated_frozen_trades"]
    }
    if len(rows) != 55 or len(audit_by_signal) != 55:
        raise AssertionError("55 frozen identities required")
    ny = pdh_census["models"]["VT31_NY_AM"]
    by_day = {
        x["ny_date"]: x for x in ny["research_hypotheses"]
    }
    if len(by_day) != len(ny["research_hypotheses"]):
        raise ValueError("more than one day hypothesis would create ambiguity")

    result_rows = []
    equity = Decimal(0)
    max_peak = Decimal(0)
    max_dd = Decimal(0)
    current_peak_index: int | None = None
    peak_index: int | None = None
    trough_index: int | None = None
    for index, row in enumerate(rows):
        signal = _dt(row["signal_at"])
        day = signal.astimezone(NY).date().isoformat()
        side = str(row["side"]).upper()
        if side not in {"SHORT", "LONG"}:
            raise ValueError("unknown frozen side")
        if signal not in audit_by_signal:
            raise ValueError(f"missing source-audit identity: {signal}")
        source = audit_by_signal[signal]
        if str(source["side"]).upper() != side:
            raise ValueError("source audit side identity drift")
        raw_fvg_earlier = (
            source["source_support"] == "RAW_FVG_CLOSED_BY_SIGNAL_UNLINKED"
        )
        if raw_fvg_earlier and _dt(
            source["latest_raw_fvg_closed_at"]
        ) > signal:
            raise AssertionError("future closed FVG identified as historical")
        candidate = by_day.get(day)
        qualified = False
        mismatch_reason: str
        if candidate is None:
            mismatch_reason = "NO_PDH_PDL_FVG_HYPOTHESIS_ON_NY_DAY"
        elif candidate["side"] != side:
            mismatch_reason = "FIRST_PDH_PDL_FVG_HYPOTHESIS_OPPOSITE_SIDE"
        elif _dt(candidate["source_fvg_closed_at_utc"]) > signal:
            mismatch_reason = "FIRST_PDH_PDL_FVG_HYPOTHESIS_AFTER_SIGNAL"
        elif not raw_fvg_earlier:
            mismatch_reason = "RAW_DIRECTIONAL_FVG_MISSING_BY_SIGNAL"
        else:
            draw_seen = _dt(candidate["draw_available_at_utc"])
            if draw_seen > signal:
                raise AssertionError("PDH/PDL from future NY trading day")
            if _d(candidate["projected_index_points_to_pdh_pdl"]) < 10:
                raise AssertionError("under-10-point source hypothesis")
            qualified = True
            mismatch_reason = "PRESIGNAL_PDH_PDL_10POINT_FVG_CONTEXT_UNLINKED"
        net = _d(row["r_multiple"]) - FRICTION
        equity += net
        if equity > max_peak:
            max_peak = equity
            current_peak_index = index
        dd = max_peak - equity
        if dd > max_dd:
            max_dd = dd
            peak_index = current_peak_index
            trough_index = index
        result_rows.append({
            "trade_index": index,
            "signal_at": signal.isoformat(),
            "ny_day": day,
            "entry_family": str(row.get("entry_family")),
            "side": side,
            "exit_reason": str(row.get("exit_reason")),
            "net_r": _s(net),  # outcome only after as-of alignment is frozen
            "raw_directional_fvg_present_by_signal": raw_fvg_earlier,
            "first_pdh_pdl_fvg_context_by_signal": qualified,
            "source_alignment_category": mismatch_reason,
            "pdh_pdl_hypothesis_fvg_closed_at_utc": (
                None if candidate is None else candidate[
                    "source_fvg_closed_at_utc"
                ]
            ),
            "selected_trade_source_identity_proven": False,
            "actual_fill_broker_parity_proven": False,
            "mss_displacement_causal_proven": False,
            "full_cognition_dol_producer_proven": False,
        })
    if abs(max_dd - EXPECTED_DD) > TOLERANCE:
        raise AssertionError(f"historical DD drift {max_dd}")
    total_r = sum((_d(x["net_r"]) for x in result_rows), Decimal(0))
    if abs(total_r - EXPECTED_R) > TOLERANCE:
        raise AssertionError(f"historical net R drift {total_r}")
    if peak_index != 17 or trough_index != 40:
        raise AssertionError("unexpected frozen DD peak/trough")
    worst = result_rows[peak_index + 1:trough_index + 1]
    if len(worst) != 23 or any(_d(x["net_r"]) >= 0 for x in worst):
        raise AssertionError("historic 23-loss episode drift")
    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "frozen_control_alias": alias,
        "trade_count": len(result_rows),
        "frozen_net_r": _s(total_r),
        "frozen_continuous_dd_r": _s(max_dd),
        "frozen_dd_episode": {
            "peak_index": peak_index,
            "trough_index": trough_index,
            "peak_signal": result_rows[peak_index]["signal_at"],
            "trough_signal": result_rows[trough_index]["signal_at"],
            "losses": len(worst),
            "classification_by_source_alignment": _group(
                worst, by="source_alignment_category"
            ),
            "classification_by_family": _group(worst, by="entry_family"),
            "classification_by_fvg_context": _group(
                worst, by="raw_directional_fvg_present_by_signal"
            ),
        },
        "all_frozen_trades_by_alignment": _group(
            result_rows, by="source_alignment_category"
        ),
        "all_frozen_trades_by_family": _group(
            result_rows, by="entry_family"
        ),
        "all_frozen_trades_by_fvg_context": _group(
            result_rows, by="raw_directional_fvg_present_by_signal"
        ),
        "research_only_asof_annotated_frozen_trades": result_rows,
        "governance": {
            "outcomes_used_to_select_source_hypothesis": False,
            "frozen_trades_not_filtered_or_resimulated": True,
            "pdh_pdl_is_not_complete_ict_liquidity_thesis": True,
            "first_fvg_is_not_selected_setup_provenance": True,
            "no_trader_policy_change": True,
            "no_sizing_or_leverage": True,
            "fresh_holdout_opened": False,
            "not_ict_fidelity_certified": True,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }
    return result


def self_test() -> None:
    # Only incomplete synthetic inputs: first boundary must reject drift.
    try:
        build(replay={"base_id": "WRONG"}, fvg_audit={}, pdh_census={})
    except ValueError:
        pass
    else:
        raise AssertionError("mixed source accepted")
    try:
        _dt("2026-03-01T10:00:00")
    except ValueError:
        pass
    else:
        raise AssertionError("unaware source accepted")
    assert _dt("2025-11-20T15:03:00+00:00").astimezone(
        NY
    ).hour == 10


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-replay", type=Path)
    parser.add_argument("--fvg-audit", type=Path)
    parser.add_argument("--pdh-pdl-audit", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "schema": SCHEMA}))
        return
    if any(x is None for x in (
        args.frozen_replay, args.fvg_audit, args.pdh_pdl_audit, args.output
    )):
        parser.error("required: --frozen-replay --fvg-audit --pdh-pdl-audit --output")
    report = build(
        replay=json.loads(args.frozen_replay.read_text()),
        fvg_audit=json.loads(args.fvg_audit.read_text()),
        pdh_census=json.loads(args.pdh_pdl_audit.read_text()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "trade_count": report["trade_count"],
        "frozen_dd_r": report["frozen_continuous_dd_r"],
        "all_55_by_ict_asof": report["all_frozen_trades_by_alignment"],
        "worst_23_by_ict_asof": report["frozen_dd_episode"][
            "classification_by_source_alignment"
        ],
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
