"""Consumed-development replay for the frozen TURTLE_SOUP_XAUUSD_R1 candidate.

This runner does not alter candidate mechanics. It reuses the exact frozen R1
implementation over the already-consumed CIBO XAUUSD corpus (2016-09-17 through
2026-09-17). Results are temporal-development evidence only, never a fresh
holdout or automatic promotion/certification signal.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1

IDENTITY = "TURTLE_SOUP_XAUUSD_R1_CONSUMED_10Y_REPLAY_V1"
SOURCE_RUN_ID = 35166210458
SOURCE_GIT_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_ARTIFACT_ID = 10476557530
SOURCE_ARTIFACT_DIGEST = (
    "sha256:dcb905b11380e3d4e1a4dc621e269bb75d2886806dd662e260d21d1d15362e08"
)
EVAL_OPEN = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
SESSION_BOUNDARY_TOLERANCE = timedelta(days=10)


def _stat(values: Sequence[Decimal]) -> dict[str, Any]:
    return r1._stat(values)


def _group(trades: Sequence[r1.Trade], key_fn: Any) -> dict[str, Any]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        groups[str(key_fn(trade))].append(trade.primary_net_r)
    return {key: _stat(values) for key, values in sorted(groups.items())}


def _trade_payload(trade: r1.Trade) -> dict[str, Any]:
    return r1._json_trade(trade)


def run_consumed_replay(source_root: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r1.SYMBOL:
        raise ValueError(f"expected {r1.SYMBOL}, got {evidence.symbol}")
    if not evidence.bars:
        raise ValueError("empty XAUUSD consumed corpus")
    first_bar = evidence.bars[0].opened_at
    last_bar_close = evidence.bars[-1].closed_at
    if first_bar > EVAL_OPEN + SESSION_BOUNDARY_TOLERANCE:
        raise ValueError("consumed corpus starts too far after frozen replay open")
    if last_bar_close < EVAL_CLOSE - SESSION_BOUNDARY_TOLERANCE:
        raise ValueError("consumed corpus ends too far before frozen replay close")

    original_open = r1.EVAL_OPEN
    original_close = r1.EVAL_CLOSE
    try:
        # Window substitution only. Candidate mechanics remain the exact R1 code.
        r1.EVAL_OPEN = EVAL_OPEN
        r1.EVAL_CLOSE = EVAL_CLOSE
        trades, funnel = r1.replay(evidence)
    finally:
        r1.EVAL_OPEN = original_open
        r1.EVAL_CLOSE = original_close

    ordered = sorted(trades, key=lambda item: item.entry_at)
    gross = [item.gross_r for item in ordered]
    primary = [item.primary_net_r for item in ordered]
    stress = [item.stress_net_r for item in ordered]
    midpoint = len(ordered) // 2

    by_year = _group(ordered, lambda item: item.entry_at.year)
    by_quarter = _group(
        ordered,
        lambda item: f"{item.entry_at.year}-Q{((item.entry_at.month - 1) // 3) + 1}",
    )
    by_side = _group(ordered, lambda item: item.side.value)
    by_timeframe = _group(ordered, lambda item: item.timeframe)
    by_session = _group(ordered, lambda item: item.session_bucket)
    by_prior_body = _group(ordered, lambda item: item.prior_body_alignment)

    positive_years = sum(Decimal(str(row["total_r"])) > 0 for row in by_year.values())
    negative_years = sum(Decimal(str(row["total_r"])) < 0 for row in by_year.values())
    positive_quarters = sum(
        Decimal(str(row["total_r"])) > 0 for row in by_quarter.values()
    )
    negative_quarters = sum(
        Decimal(str(row["total_r"])) < 0 for row in by_quarter.values()
    )

    payload: dict[str, Any] = {
        "schema": "qore.turtle_soup_xauusd_r1.consumed_10y_replay.v1",
        "identity": IDENTITY,
        "candidate_identity": r1.IDENTITY,
        "symbol": r1.SYMBOL,
        "evidence_status": "CONSUMED_DEVELOPMENT_REPLAY_NOT_FRESH_HOLDOUT",
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "first_observed_m5": first_bar.isoformat(),
        "last_observed_m5_close": last_bar_close.isoformat(),
        "retained_m5_bars": provenance["retained_bars"],
        "candidate_contract_unchanged": True,
        "candidate_contract": {
            "source_timeframes": ["H1", "H4"],
            "sides": ["long", "short"],
            "reference": "PRIOR_CANDLE_BOUNDARY",
            "closure": "EXACT_C2_REVERSAL",
            "confirmation": "CAUSAL_CISD_WITHIN_C2",
            "entry": "NEXT_SOURCE_OPEN",
            "stop": "PROTECTED_SWING_EXACT_NO_OFFSET",
            "target": "UNTOUCHED_C1_OPPOSITE_BOUNDARY",
            "maximum_lifetime_hours": 24,
            "single_position": True,
            "same_m5_bar_tie": "STOP_FIRST",
            "session_filter": None,
            "prior_body_filter": None,
            "fvg_filter": None,
            "equal_liquidity_filter": None,
            "minimum_projected_r": None,
            "c3_contract": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
        },
        "trades": len(ordered),
        "gross_wins": sum(value > 0 for value in gross),
        "gross_losses": sum(value < 0 for value in gross),
        "gross_flats": sum(value == 0 for value in gross),
        "gross": _stat(gross),
        "primary_005r_friction": _stat(primary),
        "stress_010r_friction": _stat(stress),
        "first_half_primary": _stat([item.primary_net_r for item in ordered[:midpoint]]),
        "second_half_primary": _stat([item.primary_net_r for item in ordered[midpoint:]]),
        "by_year_primary": by_year,
        "by_quarter_primary": by_quarter,
        "by_side_primary": by_side,
        "by_timeframe_primary": by_timeframe,
        "by_session_primary_diagnostic_only": by_session,
        "by_prior_body_alignment_primary_diagnostic_only": by_prior_body,
        "temporal_counts": {
            "positive_years": positive_years,
            "negative_years": negative_years,
            "positive_quarters": positive_quarters,
            "negative_quarters": negative_quarters,
        },
        "funnel": dict(sorted(funnel.items())),
        "interpretation_constraints": {
            "fresh_holdout": False,
            "automatic_rule_promotion_allowed": False,
            "automatic_certification_allowed": False,
            "may_retrospectively_filter_on_diagnostics": False,
        },
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "canonical_trader_code": "CODE_UNASSIGNED",
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "trades.json").write_text(
        json.dumps([_trade_payload(item) for item in ordered], indent=2, sort_keys=True)
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module SOURCE_ROOT OUTPUT_DIR")
    result = run_consumed_replay(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
