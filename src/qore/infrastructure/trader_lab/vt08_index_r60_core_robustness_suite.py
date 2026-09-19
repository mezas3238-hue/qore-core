"""VT08 Index R60 — frozen R58 Core robustness suite.

R60 validates the immutable R59/R58 candidate with existing QORE Core research
machinery. It does not alter the candidate.

Reused Core components:
- ResearchBlockBootstrapPolicy and the canonical deterministic circular-block
  draw selector from research_block_bootstrap;
- ResearchResamplingEnvelopePolicy nearest-rank empirical quantile semantics;
- ResearchWalkForwardFold / ResearchEvaluationWindow temporal contracts;
- existing VT08 portfolio mark-to-market and stress accounting.

The bootstrap adapter adds terminal-R, drawdown and losing-streak summaries that
the generic mean-return envelope does not expose. The resampling indices remain
the canonical Core circular-block indices; no second RNG is introduced.

All 5Y and recent 2Y windows are consumed evidence. R60 is robustness evidence,
not fresh holdout evidence and not LIVE authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure import research_block_bootstrap as core_bootstrap
from qore.infrastructure import research_resampling_envelope as core_envelope
from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapPolicy,
)
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelopePolicy,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchWalkForwardFold,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as overlay,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r58_exact_r47_distributed_risk as r58,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)

SCHEMA = "qore.trader_lab.vt08_index_r60_core_robustness_suite.v1"
IDENTITY = "VT08_INDEX_R60_R58_CORE_ROBUSTNESS_SUITE_001"
CANDIDATE_ID = freeze.CANDIDATE_ID
CANDIDATE_RULE_FINGERPRINT = freeze.CANDIDATE_RULE_FINGERPRINT

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
HARD_STRESSES = (Decimal("0.15"), Decimal("0.20"))
HARD_STRESS_PF_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX_R = Decimal("6")

BOOTSTRAP_SEED = 20260919
BOOTSTRAP_PATHS = 10_000
BOOTSTRAP_BLOCK_LENGTH = 5
BOOTSTRAP_POSITIVE_TERMINAL_MIN = 0.90
BOOTSTRAP_P95_DD_MAX_R = 6.0
BOOTSTRAP_ENVELOPE = ResearchResamplingEnvelopePolicy(
    lower_quantile_bps=500,
    upper_quantile_bps=9500,
)
BOOTSTRAP_POLICY = ResearchBlockBootstrapPolicy(
    block_length=BOOTSTRAP_BLOCK_LENGTH,
    resample_count=BOOTSTRAP_PATHS,
    seed=BOOTSTRAP_SEED,
)

WFO_MIN_SAMPLE = 50
WFO_SECONDARY_PF_MIN = Decimal("1.00")
_NY = ZoneInfo("America/New_York")

SOURCE_FREEZE_RUN_ID = 35460187018
SOURCE_FREEZE_ARTIFACT_ID = 10589633213
SOURCE_FREEZE_ARTIFACT_DIGEST = (
    "sha256:bab6cb1dacf7d331aca68f97fa8227905ef35cc2492a6e9f4fee6ff6ae365e8d"
)
SOURCE_FREEZE_HEAD_SHA = "02c20f78ad8177ea8256f090bd9382775568bcab"


def _candidate(
    stream: Sequence[Any],
    *,
    bars_by_symbol: dict[str, Sequence[Any]],
) -> tuple[r15.AssignedTrade, ...]:
    base, _base_diagnostics = r58._exact_r47(
        stream,
        bars_by_symbol=bars_by_symbol,
    )
    candidate, diagnostics = overlay._apply_candidate(
        base,
        bars_by_symbol=bars_by_symbol,
    )
    if int(diagnostics["suppressed_trade_count"]) != 0:
        raise ValueError("R60 candidate unexpectedly suppressed signals")
    return candidate


def _verify_freeze(
    assigned: Sequence[r15.AssignedTrade],
    *,
    expected: dict[str, object],
    years: int,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, Sequence[Any]],
) -> None:
    metrics = r47._window_metrics(
        tuple(assigned),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        years=years,
    )
    if len(assigned) != int(str(expected["sample"])):
        raise ValueError("R60 frozen sample drift")
    secondary = metrics["secondary"]
    if Decimal(str(secondary["profit_factor"])) != Decimal(
        str(expected["secondary_pf"])
    ):
        raise ValueError("R60 frozen secondary PF drift")
    if Decimal(str(secondary["total_r"])) != Decimal(
        str(expected["secondary_total_r"])
    ):
        raise ValueError("R60 frozen secondary terminal drift")


def _stress_metrics(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, Sequence[Any]],
) -> dict[str, object]:
    realized = fx._metrics(
        r15._realized_values(tuple(assigned), stress=stress)
    )
    mtm = r15._portfolio_mark_to_market(
        tuple(assigned),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=stress,
        adverse=True,
    )
    return {
        "stress_r_per_trade": str(stress),
        "realized": realized,
        "conservative_mark_to_market": mtm,
    }


def _stress_ladder(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, Sequence[Any]],
) -> dict[str, object]:
    rows = {
        str(stress): _stress_metrics(
            assigned,
            stress=stress,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
        )
        for stress in (
            PRIMARY_STRESS,
            SECONDARY_STRESS,
            *HARD_STRESSES,
        )
    }
    hard_pass = True
    for stress in HARD_STRESSES:
        row = rows[str(stress)]
        realized = row["realized"]
        mtm = row["conservative_mark_to_market"]
        if not isinstance(realized, dict) or not isinstance(mtm, dict):
            hard_pass = False
            continue
        hard_pass = hard_pass and (
            Decimal(str(realized["total_r"])) > 0
            and Decimal(str(realized["profit_factor"] or "0"))
            >= HARD_STRESS_PF_MIN
            and Decimal(str(mtm["max_drawdown_r"]))
            <= PORTFOLIO_DD_MAX_R
        )
    return {
        "rows": rows,
        "hard_stress_pf_min": str(HARD_STRESS_PF_MIN),
        "hard_stress_dd_max_r": str(PORTFOLIO_DD_MAX_R),
        "hard_stress_pass": hard_pass,
    }


def _max_drawdown(values: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _max_losing_streak(values: Sequence[float]) -> int:
    current = 0
    maximum = 0
    for value in values:
        if value < 0.0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _nearest_float(values: Sequence[float], quantile_bps: int) -> float:
    if not values:
        raise ValueError("R60 quantile requires values")
    ordered = sorted(values)
    if quantile_bps == 0:
        return ordered[0]
    rank = (quantile_bps * len(ordered) + 9_999) // 10_000
    return ordered[rank - 1]


def _core_monte_carlo(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, object]:
    values = tuple(
        float(value)
        for value in r15._realized_values(
            tuple(assigned),
            stress=SECONDARY_STRESS,
        )
    )
    if len(values) < BOOTSTRAP_POLICY.block_length:
        raise ValueError("R60 bootstrap source shorter than block length")

    sample_size = len(values)
    blocks_per_path = (
        sample_size + BOOTSTRAP_POLICY.block_length - 1
    ) // BOOTSTRAP_POLICY.block_length
    terminals: list[float] = []
    drawdowns: list[float] = []
    losing_streaks: list[float] = []
    mean_decimals: list[Decimal] = []
    positive = 0

    for replicate in range(BOOTSTRAP_POLICY.resample_count):
        sample: list[float] = []
        for draw in range(blocks_per_path):
            start = core_bootstrap._draw_start(
                seed=BOOTSTRAP_POLICY.seed,
                replicate=replicate,
                draw=draw,
                sample_size=sample_size,
            )
            for offset in range(BOOTSTRAP_POLICY.block_length):
                sample.append(values[(start + offset) % sample_size])
                if len(sample) == sample_size:
                    break
            if len(sample) == sample_size:
                break

        terminal = sum(sample)
        mean_value = terminal / sample_size
        positive += int(terminal > 0.0)
        terminals.append(terminal)
        drawdowns.append(_max_drawdown(sample))
        losing_streaks.append(float(_max_losing_streak(sample)))
        mean_decimals.append(Decimal(str(mean_value)))

    ordered_means = tuple(sorted(mean_decimals))
    lower_mean = core_envelope._nearest_rank(
        ordered_means,
        BOOTSTRAP_ENVELOPE.lower_quantile_bps,
    )
    median_mean = core_envelope._nearest_rank(ordered_means, 5_000)
    upper_mean = core_envelope._nearest_rank(
        ordered_means,
        BOOTSTRAP_ENVELOPE.upper_quantile_bps,
    )
    positive_fraction = positive / BOOTSTRAP_POLICY.resample_count
    p95_dd = _nearest_float(drawdowns, 9_500)

    return {
        "engine": (
            "qore.infrastructure.research_block_bootstrap."
            "ResearchBlockBootstrapPolicy+_draw_start"
        ),
        "resampling": "canonical-deterministic-circular-block",
        "seed": BOOTSTRAP_POLICY.seed,
        "paths": BOOTSTRAP_POLICY.resample_count,
        "block_length": BOOTSTRAP_POLICY.block_length,
        "source_sample": sample_size,
        "mean_return_envelope": {
            "quantile_rule": BOOTSTRAP_ENVELOPE.rule.value,
            "lower_5pct": str(lower_mean),
            "median": str(median_mean),
            "upper_95pct": str(upper_mean),
            "lower_contains_positive_mean": lower_mean > 0,
        },
        "positive_terminal_fraction": positive_fraction,
        "terminal_r_p05": _nearest_float(terminals, 500),
        "terminal_r_p50": _nearest_float(terminals, 5_000),
        "terminal_r_p95": _nearest_float(terminals, 9_500),
        "max_drawdown_r_p50": _nearest_float(drawdowns, 5_000),
        "max_drawdown_r_p95": p95_dd,
        "max_drawdown_r_p99": _nearest_float(drawdowns, 9_900),
        "max_losing_streak_p50": int(
            _nearest_float(losing_streaks, 5_000)
        ),
        "max_losing_streak_p95": int(
            _nearest_float(losing_streaks, 9_500)
        ),
        "max_losing_streak_p99": int(
            _nearest_float(losing_streaks, 9_900)
        ),
        "qualification": {
            "positive_terminal_min": BOOTSTRAP_POSITIVE_TERMINAL_MIN,
            "p95_dd_max_r": BOOTSTRAP_P95_DD_MAX_R,
            "pass": (
                positive_fraction >= BOOTSTRAP_POSITIVE_TERMINAL_MIN
                and p95_dd <= BOOTSTRAP_P95_DD_MAX_R
            ),
        },
    }


def _dt(
    year: int,
    month: int,
    day: int,
) -> datetime:
    return datetime(year, month, day, tzinfo=_NY).astimezone(UTC)


def _five_year_folds() -> tuple[ResearchWalkForwardFold, ...]:
    return (
        ResearchWalkForwardFold(
            fold_number=1,
            in_sample=ResearchEvaluationWindow(
                _dt(2018, 9, 15),
                _dt(2020, 9, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2020, 9, 15),
                _dt(2021, 9, 15),
            ),
        ),
        ResearchWalkForwardFold(
            fold_number=2,
            in_sample=ResearchEvaluationWindow(
                _dt(2019, 9, 15),
                _dt(2021, 9, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2021, 9, 15),
                _dt(2022, 9, 15),
            ),
        ),
        ResearchWalkForwardFold(
            fold_number=3,
            in_sample=ResearchEvaluationWindow(
                _dt(2020, 9, 15),
                _dt(2022, 9, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2022, 9, 15),
                _dt(2023, 9, 15),
            ),
        ),
    )


def _two_year_folds() -> tuple[ResearchWalkForwardFold, ...]:
    return (
        ResearchWalkForwardFold(
            fold_number=1,
            in_sample=ResearchEvaluationWindow(
                _dt(2024, 9, 15),
                _dt(2025, 3, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2025, 3, 15),
                _dt(2025, 9, 15),
            ),
        ),
        ResearchWalkForwardFold(
            fold_number=2,
            in_sample=ResearchEvaluationWindow(
                _dt(2024, 9, 15),
                _dt(2025, 9, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2025, 9, 15),
                _dt(2026, 3, 15),
            ),
        ),
        ResearchWalkForwardFold(
            fold_number=3,
            in_sample=ResearchEvaluationWindow(
                _dt(2025, 3, 15),
                _dt(2026, 3, 15),
            ),
            out_of_sample=ResearchEvaluationWindow(
                _dt(2026, 3, 15),
                _dt(2026, 9, 15),
            ),
        ),
    )


def _fold_metrics(
    assigned: Sequence[r15.AssignedTrade],
    fold: ResearchWalkForwardFold,
) -> dict[str, object]:
    items = tuple(
        item
        for item in assigned
        if fold.out_of_sample.opened_at
        <= item.opportunity.signal.signal_at.astimezone(UTC)
        < fold.out_of_sample.closed_at
    )
    secondary = fx._metrics(
        r15._realized_values(items, stress=SECONDARY_STRESS)
    )
    hard = fx._metrics(
        r15._realized_values(items, stress=Decimal("0.20"))
    )
    fold_pass = (
        len(items) >= WFO_MIN_SAMPLE
        and Decimal(str(secondary["total_r"])) > 0
        and Decimal(str(secondary["profit_factor"] or "0"))
        >= WFO_SECONDARY_PF_MIN
    )
    return {
        "fold_number": fold.fold_number,
        "in_sample": list(fold.in_sample.logical_values()),
        "out_of_sample": list(fold.out_of_sample.logical_values()),
        "assignment_basis": "signal_at",
        "sample": len(items),
        "secondary_stress": secondary,
        "hard_stress_0.20": hard,
        "pass": fold_pass,
    }


def _wfo(
    assigned: Sequence[r15.AssignedTrade],
    folds: tuple[ResearchWalkForwardFold, ...],
) -> dict[str, object]:
    rows = [_fold_metrics(assigned, fold) for fold in folds]
    return {
        "core_contract": (
            "qore.infrastructure.research_temporal_evaluation."
            "ResearchWalkForwardFold"
        ),
        "candidate_retuned_between_folds": False,
        "selection_or_ranking_performed": False,
        "minimum_oos_sample": WFO_MIN_SAMPLE,
        "secondary_pf_minimum": str(WFO_SECONDARY_PF_MIN),
        "folds": rows,
        "all_oos_folds_pass": all(bool(row["pass"]) for row in rows),
    }


def _window(
    *,
    assigned: Sequence[r15.AssignedTrade],
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, Sequence[Any]],
    folds: tuple[ResearchWalkForwardFold, ...],
) -> dict[str, object]:
    concentration = overlay._concentration(tuple(assigned))
    stress = _stress_ladder(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    monte_carlo = _core_monte_carlo(assigned)
    wfo = _wfo(assigned, folds)
    return {
        "sample": len(assigned),
        "stress": stress,
        "monte_carlo": monte_carlo,
        "walk_forward": wfo,
        "concentration": concentration,
        "hard_gate_pass": (
            bool(stress["hard_stress_pass"])
            and bool(monte_carlo["qualification"]["pass"])
            and bool(wfo["all_oos_folds_pass"])
            and bool(concentration["leave_top_3_positive"])
        ),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R60 frozen R59/R58 dependency drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five = _candidate(five_stream, bars_by_symbol=five_bars)
    two = _candidate(two_stream, bars_by_symbol=two_bars)

    _verify_freeze(
        five,
        expected=freeze.FIVE_YEAR,
        years=5,
        bars_by_symbol=five_bars,
        opened_by_symbol=five_opened,
    )
    _verify_freeze(
        two,
        expected=freeze.RECENT_TWO_YEAR,
        years=2,
        bars_by_symbol=two_bars,
        opened_by_symbol=two_opened,
    )

    five_result = _window(
        assigned=five,
        bars_by_symbol=five_bars,
        opened_by_symbol=five_opened,
        folds=_five_year_folds(),
    )
    two_result = _window(
        assigned=two,
        bars_by_symbol=two_bars,
        opened_by_symbol=two_opened,
        folds=_two_year_folds(),
    )
    hard_gate_pass = (
        bool(five_result["hard_gate_pass"])
        and bool(two_result["hard_gate_pass"])
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": CANDIDATE_ID,
            "rule_fingerprint": CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "rules_changed": False,
            "risk_retuned": False,
        },
        "pre_registered_validation": {
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_paths": BOOTSTRAP_PATHS,
            "bootstrap_block_length": BOOTSTRAP_BLOCK_LENGTH,
            "bootstrap_positive_terminal_min": (
                BOOTSTRAP_POSITIVE_TERMINAL_MIN
            ),
            "bootstrap_p95_dd_max_r": BOOTSTRAP_P95_DD_MAX_R,
            "hard_stresses_r_per_trade": [
                str(value) for value in HARD_STRESSES
            ],
            "hard_stress_pf_min": str(HARD_STRESS_PF_MIN),
            "hard_stress_dd_max_r": str(PORTFOLIO_DD_MAX_R),
            "wfo_minimum_oos_sample": WFO_MIN_SAMPLE,
            "wfo_secondary_pf_minimum": str(WFO_SECONDARY_PF_MIN),
        },
        "five_year": five_result,
        "recent_two_year": two_result,
        "hard_gate_pass": hard_gate_pass,
        "decision": (
            "PASS_R60_CORE_ROBUSTNESS_CONTINUE_CERTIFICATION"
            if hard_gate_pass
            else "FAIL_R60_CORE_ROBUSTNESS_RETURN_TO_LAB"
        ),
        "source_evidence": {
            "r59_freeze": {
                "run_id": SOURCE_FREEZE_RUN_ID,
                "artifact_id": SOURCE_FREEZE_ARTIFACT_ID,
                "artifact_digest": SOURCE_FREEZE_ARTIFACT_DIGEST,
                "head_sha": SOURCE_FREEZE_HEAD_SHA,
            },
        },
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "robustness_only": True,
            "existing_core_monte_carlo_reused": True,
            "existing_core_walk_forward_contract_reused": True,
            "existing_core_stress_accounting_reused": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "candidate_retuned": False,
            "signals_suppressed": False,
            "calendar_or_year_runtime_feature": False,
            "certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "candidate": report["candidate"],
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "hard_gate_pass": report["hard_gate_pass"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
