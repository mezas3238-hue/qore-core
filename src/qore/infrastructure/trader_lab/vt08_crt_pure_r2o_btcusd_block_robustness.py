"""R2-O deterministic circular-block robustness for BTCUSD survivors.

This lab reuses QORE's deterministic circular-block resampling stream from
research_block_bootstrap instead of introducing a second RNG/resampling
implementation.

The source sequences are the exact chronological R-multiples produced by the
R2-M survivor candidates over 2022-2026. Candidate definitions remain unchanged
and separate.

Frozen block family:
- block length 2;
- block length 4;
- block length 8.

Each policy uses 5,000 deterministic resamples and a fixed seed. The lab reports
terminal-R and max-drawdown empirical distributions. It does not impose a new
certification threshold or rank candidates.

Research only. No runtime/capital authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapPolicy,
    _draw_start,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2j_market_context_validation import (
    CandidateId,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _candidate_trades,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2O_BTCUSD_BLOCK_ROBUSTNESS_001"
SCHEMA = "qore.vt08.crt_pure.r2o_btcusd_block_robustness.v1"
MARKET = CrtPureMarket.BTCUSD

CANDIDATES: tuple[CandidateId, ...] = (
    CandidateId.BTC_BEARISH,
    CandidateId.BTC_BODY_GE_050,
    CandidateId.BTC_REF2_PLUS,
)

RESAMPLE_COUNT = 5_000
BASE_SEED = 20_260_923
BLOCK_LENGTHS: tuple[int, ...] = (2, 4, 8)


def _policy(block_length: int) -> ResearchBlockBootstrapPolicy:
    return ResearchBlockBootstrapPolicy(
        block_length=block_length,
        resample_count=RESAMPLE_COUNT,
        seed=BASE_SEED + block_length,
    )


def _resample(
    values: tuple[float, ...],
    policy: ResearchBlockBootstrapPolicy,
    replicate: int,
) -> tuple[float, ...]:
    if not values:
        raise ValueError("block robustness requires non-empty R sequence")
    sample_size = len(values)
    if policy.block_length > sample_size:
        raise ValueError("block length cannot exceed R sequence")
    blocks = (sample_size + policy.block_length - 1) // policy.block_length
    result: list[float] = []
    for draw in range(blocks):
        start = _draw_start(
            seed=policy.seed,
            replicate=replicate,
            draw=draw,
            sample_size=sample_size,
        )
        for offset in range(policy.block_length):
            result.append(values[(start + offset) % sample_size])
            if len(result) == sample_size:
                return tuple(result)
    return tuple(result)


def _max_drawdown(values: tuple[float, ...]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _nearest_rank(values: tuple[float, ...], quantile: float) -> float:
    if not values:
        raise ValueError("quantile requires non-empty values")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    if quantile == 0.0:
        return ordered[0]
    rank = max(
        1,
        min(len(ordered), int((quantile * len(ordered)) + 0.999999999)),
    )
    return ordered[rank - 1]


def _distribution(
    rows: tuple[Model1LabTrade, ...],
    policy: ResearchBlockBootstrapPolicy,
) -> dict[str, Any]:
    values = tuple(float(row.r_multiple) for row in rows)
    terminal: list[float] = []
    drawdowns: list[float] = []
    for replicate in range(policy.resample_count):
        sample = _resample(values, policy, replicate)
        terminal.append(sum(sample))
        drawdowns.append(_max_drawdown(sample))

    terminal_tuple = tuple(terminal)
    dd_tuple = tuple(drawdowns)
    positive = sum(value > 0 for value in terminal_tuple)
    return {
        "block_length": policy.block_length,
        "resample_count": policy.resample_count,
        "seed": policy.seed,
        "source_trade_count": len(values),
        "source_total_r": round(sum(values), 8),
        "source_max_drawdown_r": round(_max_drawdown(values), 8),
        "positive_terminal_fraction": round(positive / len(terminal_tuple), 8),
        "terminal_r": {
            "p05": round(_nearest_rank(terminal_tuple, 0.05), 8),
            "p50": round(_nearest_rank(terminal_tuple, 0.50), 8),
            "p95": round(_nearest_rank(terminal_tuple, 0.95), 8),
        },
        "max_drawdown_r": {
            "p50": round(_nearest_rank(dd_tuple, 0.50), 8),
            "p95": round(_nearest_rank(dd_tuple, 0.95), 8),
            "p99": round(_nearest_rank(dd_tuple, 0.99), 8),
        },
    }


def run_block_robustness() -> tuple[
    dict[CandidateId, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    all_candidates = _candidate_trades(MARKET)
    source = {candidate: all_candidates[candidate] for candidate in CANDIDATES}

    candidate_reports: dict[str, Any] = {}
    for candidate in CANDIDATES:
        rows = source[candidate]
        candidate_reports[candidate.value] = {
            f"BLOCK_{block_length}": _distribution(rows, _policy(block_length))
            for block_length in BLOCK_LENGTHS
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "candidate_family": [candidate.value for candidate in CANDIDATES],
        "candidate_definitions_reused_from_r2m": True,
        "resampling_engine": "QORE_RESEARCH_CIRCULAR_BLOCK_DRAW_STREAM",
        "block_lengths": list(BLOCK_LENGTHS),
        "resample_count": RESAMPLE_COUNT,
        "base_seed": BASE_SEED,
        "policies_frozen_before_results": True,
        "candidates": candidate_reports,
        "automatic_winner_ranking": False,
        "qualification_thresholds_imposed": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return source, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source, report = run_block_robustness()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "source_trades.jsonl").open("w", encoding="utf-8") as handle:
        for candidate in CANDIDATES:
            for trade in source[candidate]:
                row = asdict(trade)
                row["candidate_id"] = candidate.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2O_BTC_BLOCK_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
