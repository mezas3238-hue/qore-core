"""Residual drawdown forensics after the third-slot diagnostic hypothesis.

The consumed 2Y laboratory showed that third-slot candidates arriving after two
earlier same-session selections with *no active earlier position* form a weak
31-trade cohort. Abstaining that entire diagnostic cohort changes the frozen 1R
portfolio from 8.671R DD to 6.590R DD, but it still misses the Owner hard ceiling
of 6R.

This module does not promote that cohort as a rule. It uses the hypothesis only
as a diagnostic lens, locates the exact residual peak-to-trough drawdown episode,
and reconstructs the causal pre-entry state of every trade inside that episode.

No new admission filter is selected here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_RESIDUAL_DRAWDOWN_FORENSICS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"


@dataclass(frozen=True, slots=True)
class DrawdownEpisode:
    max_drawdown_r: str
    peak_equity_r: str
    trough_equity_r: str
    peak_after_trade_index: int | None
    trough_trade_index: int | None
    segment_start_index: int | None
    segment_end_index: int | None
    segment_trade_count: int


@dataclass(frozen=True, slots=True)
class ResidualDrawdownTrade:
    sequence_index: int
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    provenance: str
    prior_same_session_selected: int
    baseline_active_positions: int
    shared_factor_state: str
    entry_mode: str
    liquidity_kind: str
    liquidity_source: str
    mss_to_entry_phase: str
    fvg_to_entry_phase: str
    ob_fvg_overlap: str


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("residual DD forensics requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    coverage = report.get("binding_coverage")
    if not isinstance(coverage, dict):
        raise ValueError("V2 binding coverage missing")
    if int(coverage.get("source_microstructure", -1)) != int(
        report.get("control_trades", -2)
    ):
        raise ValueError("residual DD forensics requires complete source binding")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("residual DD forensics rejects future evidence")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _max_drawdown_episode(rows: tuple[dict[str, Any], ...]) -> DrawdownEpisode:
    if not rows:
        return DrawdownEpisode(
            max_drawdown_r="0",
            peak_equity_r="0",
            trough_equity_r="0",
            peak_after_trade_index=None,
            trough_trade_index=None,
            segment_start_index=None,
            segment_end_index=None,
            segment_trade_count=0,
        )

    equity = Decimal("0")
    peak_equity = Decimal("0")
    peak_index: int | None = None
    best_dd = Decimal("0")
    best_peak_equity = Decimal("0")
    best_trough_equity = Decimal("0")
    best_peak_index: int | None = None
    best_trough_index: int | None = None

    for index, row in enumerate(rows):
        equity += Decimal(str(row["realized_gross_r"]))
        if equity > peak_equity:
            peak_equity = equity
            peak_index = index
        current_dd = peak_equity - equity
        if current_dd > best_dd:
            best_dd = current_dd
            best_peak_equity = peak_equity
            best_trough_equity = equity
            best_peak_index = peak_index
            best_trough_index = index

    if best_trough_index is None:
        return DrawdownEpisode(
            max_drawdown_r="0",
            peak_equity_r=str(best_peak_equity),
            trough_equity_r=str(best_trough_equity),
            peak_after_trade_index=best_peak_index,
            trough_trade_index=None,
            segment_start_index=None,
            segment_end_index=None,
            segment_trade_count=0,
        )

    start = 0 if best_peak_index is None else best_peak_index + 1
    return DrawdownEpisode(
        max_drawdown_r=str(best_dd),
        peak_equity_r=str(best_peak_equity),
        trough_equity_r=str(best_trough_equity),
        peak_after_trade_index=best_peak_index,
        trough_trade_index=best_trough_index,
        segment_start_index=start,
        segment_end_index=best_trough_index,
        segment_trade_count=best_trough_index - start + 1,
    )


def _token_map(binding: dict[str, Any]) -> dict[str, str]:
    return stoprisk._token_map(binding)


def _residual_row(
    *,
    index: int,
    trade: dict[str, Any],
    binding: dict[str, Any],
) -> ResidualDrawdownTrade:
    tokens = _token_map(binding)
    return ResidualDrawdownTrade(
        sequence_index=index,
        symbol=str(trade["symbol"]),
        session=str(trade["session"]),
        operating_date=str(trade["operating_date"]),
        side=str(trade["side"]),
        entry_at=str(trade["entry_at"]),
        exit_at=str(trade["exit_at"]),
        realized_gross_r=str(trade["realized_gross_r"]),
        exit_reason=str(trade["exit_reason"]),
        provenance=str(trade["provenance"]),
        prior_same_session_selected=int(binding["prior_same_session_selected"]),
        baseline_active_positions=int(binding["baseline_active_positions"]),
        shared_factor_state=stoprisk._shared_factor_state(binding),
        entry_mode=tokens.get("ENTRY_MODE", "UNKNOWN"),
        liquidity_kind=tokens.get("LIQUIDITY_KIND", "UNKNOWN"),
        liquidity_source=tokens.get("LIQUIDITY_SOURCE", "UNKNOWN"),
        mss_to_entry_phase=stoprisk._mss_phase(binding, tokens),
        fvg_to_entry_phase=stoprisk._fvg_phase(binding, tokens),
        ob_fvg_overlap=tokens.get("M1_OB_FVG_OVERLAP", "UNKNOWN"),
    )


def build_report(
    binding_root: Path,
    target_root: Path,
) -> tuple[dict[str, Any], tuple[ResidualDrawdownTrade, ...]]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if len(binding_by_key) != len(bindings):
        raise ValueError("residual DD binding identity not unique")
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("residual DD binding/control identities differ")

    diagnostic_blocked = tuple(
        row
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
        and int(binding_by_key[_join_key(row)]["baseline_active_positions"]) == 0
    )
    if len(diagnostic_blocked) != 31:
        raise ValueError(
            "residual DD diagnostic requires frozen 31-trade third-slot cohort"
        )
    blocked_keys = {_join_key(row) for row in diagnostic_blocked}
    filtered = tuple(row for row in control if _join_key(row) not in blocked_keys)

    control_episode = _max_drawdown_episode(control)
    filtered_episode = _max_drawdown_episode(filtered)
    start = filtered_episode.segment_start_index
    end = filtered_episode.segment_end_index
    segment = (
        ()
        if start is None or end is None
        else tuple(filtered[start : end + 1])
    )
    residual_rows = tuple(
        _residual_row(
            index=start_index,
            trade=trade,
            binding=binding_by_key[_join_key(trade)],
        )
        for start_index, trade in enumerate(segment, start=start or 0)
    )

    symbols = Counter(row.symbol for row in residual_rows)
    sessions = Counter(row.session for row in residual_rows)
    slots = Counter(str(row.prior_same_session_selected) for row in residual_rows)
    exit_reasons = Counter(row.exit_reason for row in residual_rows)
    negative = tuple(
        row for row in residual_rows if Decimal(row.realized_gross_r) < 0
    )

    report = {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_metrics": _metrics(control),
        "control_drawdown_episode": asdict(control_episode),
        "diagnostic_hypothesis": (
            "ABSTAIN_THIRD_SLOT_WHEN_TWO_PRIOR_SESSION_SELECTIONS_"
            "ARE_BOTH_CLOSED_AT_DECISION"
        ),
        "diagnostic_hypothesis_only": True,
        "diagnostic_blocked_trades": len(diagnostic_blocked),
        "diagnostic_blocked_metrics": _metrics(diagnostic_blocked),
        "filtered_metrics": _metrics(filtered),
        "filtered_drawdown_episode": asdict(filtered_episode),
        "residual_segment_summary": {
            "trades": len(residual_rows),
            "negative_trades": len(negative),
            "stops": sum(row.exit_reason == "STOP" for row in residual_rows),
            "symbols": dict(sorted(symbols.items())),
            "sessions": dict(sorted(sessions.items())),
            "prior_same_session_selected": dict(sorted(slots.items())),
            "exit_reasons": dict(sorted(exit_reasons.items())),
        },
        "current_outcome_used_to_define_diagnostic_hypothesis": False,
        "current_outcome_used_to_locate_drawdown_after_hypothesis": True,
        "residual_trade_features_known_by_entry": True,
        "residual_filter_selected": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "EXPLAIN_RESIDUAL_DRAWDOWN_BEFORE_ANY_NEW_COGNITIVE_PRESSURE_RULE",
    }
    return report, residual_rows


def write_report(
    report: dict[str, Any],
    rows: tuple[ResidualDrawdownTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-residual-drawdown-forensics-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-residual-drawdown-forensics-2y-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.binding_root, args.target_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
