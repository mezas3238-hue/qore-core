"""VT-08 R3.13 challenge-speed adaptive Risk Monte Carlo.

Research-only child of R3.12.  The Trader and methodology remain frozen.  This
module searches a pre-registered adaptive Risk surface on consumed evidence only
for a USD 100k prop-firm challenge whose objective is +10% within 30 trading days.
The protected [2020-07-01, 2022-07-01) holdout is never read here.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from statistics import median

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BASELINE_RUN_ID,
    CONSUMED_EVIDENCE_FLOOR,
    FRESH_RUN_ID,
    load_consumed_evidence,
)
from qore.infrastructure.trader_lab.vt08_official_adaptive_monte_carlo_r3_12 import (
    COST_GRID_BPS,
    PRIMARY_COST_BPS,
    PRIMARY_POLICY,
    PROFILES,
    AdaptiveRiskPolicy,
    PathMetrics,
    _adaptive_days,
    _canonical_digest,
    _distribution,
    _evidence_fingerprints,
    _file_digests,
    _paired_marginal,
    _policy_material,
    _profile_material,
    _scope_membership,
    _summarize_paths,
    simulate_adaptive_path,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    INPUT_ARTIFACTS,
    PORTFOLIOS,
    paired_block_indices,
)
from qore.infrastructure.trader_lab.vt08_prop_firm_profiles_r3_12 import (
    FTMO_2STEP_2026_09_12,
)

SCHEMA = "qore.vt08.r3.13.challenge-speed-adaptive-risk.v1"
PATHS = 10_000
SENSITIVITY_PATHS = 2_500
SEED = 20260913
CHALLENGE_HORIZON_DAYS = 30
BLOCK_DAYS = 5
TARGET_INDEX_10PCT = 2
MAX_SAFE_BREACH_PROBABILITY = 0.01
MAX_SAFE_DRAWDOWN_P99 = 0.06
PROTECTED_HOLDOUT_START = date(2020, 7, 1)
PROTECTED_HOLDOUT_END = date(2022, 7, 1)


class ChallengeSpeedError(ValueError):
    """Raised when R3.13 governance or experiment invariants fail."""


def _policy(
    name: str,
    *,
    a_base: str,
    g_base: str,
    a_floor: str,
    g_floor: str,
    a_ceiling: str,
    g_ceiling: str,
    heat: str,
    a_heat: str,
    g_heat: str,
    correlation: str,
    daily_guard: str,
    dd_guard: str,
    upshift: str,
    downshift: str,
) -> AdaptiveRiskPolicy:
    return AdaptiveRiskPolicy(
        name=name,
        a_base_bps=Decimal(a_base),
        gbpjpy_base_bps=Decimal(g_base),
        a_floor_bps=Decimal(a_floor),
        gbpjpy_floor_bps=Decimal(g_floor),
        a_ceiling_bps=Decimal(a_ceiling),
        gbpjpy_ceiling_bps=Decimal(g_ceiling),
        portfolio_heat_bps=Decimal(heat),
        a_sleeve_heat_bps=Decimal(a_heat),
        gbpjpy_sleeve_heat_bps=Decimal(g_heat),
        correlated_heat_bps=Decimal(correlation),
        internal_daily_guard_bps=Decimal(daily_guard),
        internal_peak_drawdown_guard_bps=Decimal(dd_guard),
        provider_safety_buffer_bps=Decimal("10"),
        full_profit_cushion_fraction=Decimal("0.05"),
        full_drawdown_brake_fraction=Decimal("0.02"),
        hysteresis_bps=Decimal("0.50"),
        upshift_step_bps=Decimal(upshift),
        downshift_step_bps=Decimal(downshift),
    )


CHALLENGE_POLICIES = (
    AdaptiveRiskPolicy(
        **{
            **asdict(PRIMARY_POLICY),
            "name": "funded-baseline-r312",
        }
    ),
    _policy(
        "challenge-030bps-v1",
        a_base="30",
        g_base="25",
        a_floor="10",
        g_floor="8",
        a_ceiling="40",
        g_ceiling="35",
        heat="100",
        a_heat="70",
        g_heat="55",
        correlation="60",
        daily_guard="250",
        dd_guard="500",
        upshift="2",
        downshift="15",
    ),
    _policy(
        "challenge-050bps-v1",
        a_base="50",
        g_base="40",
        a_floor="15",
        g_floor="12",
        a_ceiling="65",
        g_ceiling="55",
        heat="150",
        a_heat="100",
        g_heat="80",
        correlation="90",
        daily_guard="300",
        dd_guard="550",
        upshift="3",
        downshift="25",
    ),
    _policy(
        "challenge-075bps-v1",
        a_base="75",
        g_base="60",
        a_floor="20",
        g_floor="15",
        a_ceiling="100",
        g_ceiling="80",
        heat="200",
        a_heat="140",
        g_heat="110",
        correlation="120",
        daily_guard="300",
        dd_guard="575",
        upshift="4",
        downshift="35",
    ),
    _policy(
        "challenge-100bps-v1",
        a_base="100",
        g_base="80",
        a_floor="25",
        g_floor="20",
        a_ceiling="130",
        g_ceiling="105",
        heat="250",
        a_heat="180",
        g_heat="140",
        correlation="150",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="50",
    ),
    _policy(
        "challenge-125bps-v1",
        a_base="125",
        g_base="100",
        a_floor="30",
        g_floor="25",
        a_ceiling="160",
        g_ceiling="130",
        heat="300",
        a_heat="220",
        g_heat="170",
        correlation="180",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="60",
    ),
    _policy(
        "challenge-150bps-v1",
        a_base="150",
        g_base="120",
        a_floor="35",
        g_floor="30",
        a_ceiling="190",
        g_ceiling="155",
        heat="350",
        a_heat="260",
        g_heat="200",
        correlation="210",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="75",
    ),
    _policy(
        "challenge-200bps-v1",
        a_base="200",
        g_base="150",
        a_floor="50",
        g_floor="40",
        a_ceiling="250",
        g_ceiling="190",
        heat="450",
        a_heat="330",
        g_heat="250",
        correlation="270",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="100",
    ),
)


@dataclass(frozen=True, slots=True)
class CandidateScore:
    policy_name: str
    probability_10pct_within_30d_before_breach: float
    probability_8pct_within_30d_before_breach: float
    probability_5pct_within_30d_before_breach: float
    any_breach_probability: float
    drawdown_p99: float
    ruin_probability: float
    median_terminal_return: float
    median_days_to_10pct_when_achieved: float | None
    safe_candidate: bool

    def selection_key(self, policy: AdaptiveRiskPolicy) -> tuple[float, float, float, float]:
        return (
            self.probability_10pct_within_30d_before_breach,
            -self.any_breach_probability,
            -self.drawdown_p99,
            -float(policy.a_base_bps),
        )


def _target_probability(results: Sequence[PathMetrics], target_index: int) -> float:
    successful = 0
    for item in results:
        day = item.target_days[target_index]
        if day is not None and day <= CHALLENGE_HORIZON_DAYS:
            if item.first_breach_day is None or day <= item.first_breach_day:
                successful += 1
    return successful / len(results)


def _candidate_score(policy: AdaptiveRiskPolicy, results: Sequence[PathMetrics]) -> CandidateScore:
    if not results:
        raise ChallengeSpeedError("candidate result set cannot be empty")
    breach = sum(item.any_prop_firm_breach for item in results) / len(results)
    ruin = sum(item.ruin for item in results) / len(results)
    drawdown_p99 = _distribution([item.max_drawdown for item in results])["p99"]
    successful_days = [
        float(item.target_days[TARGET_INDEX_10PCT])
        for item in results
        if item.target_days[TARGET_INDEX_10PCT] is not None
        and item.target_days[TARGET_INDEX_10PCT] <= CHALLENGE_HORIZON_DAYS
        and (
            item.first_breach_day is None
            or item.target_days[TARGET_INDEX_10PCT] <= item.first_breach_day
        )
    ]
    safe = (
        breach <= MAX_SAFE_BREACH_PROBABILITY
        and drawdown_p99 <= MAX_SAFE_DRAWDOWN_P99
        and ruin == 0.0
        and policy.upshift_step_bps < policy.downshift_step_bps
    )
    return CandidateScore(
        policy_name=policy.name,
        probability_10pct_within_30d_before_breach=_target_probability(results, 2),
        probability_8pct_within_30d_before_breach=_target_probability(results, 1),
        probability_5pct_within_30d_before_breach=_target_probability(results, 0),
        any_breach_probability=breach,
        drawdown_p99=drawdown_p99,
        ruin_probability=ruin,
        median_terminal_return=median(item.terminal_return for item in results),
        median_days_to_10pct_when_achieved=(
            None if not successful_days else median(successful_days)
        ),
        safe_candidate=safe,
    )


def select_policy(
    scored: Sequence[tuple[AdaptiveRiskPolicy, CandidateScore]],
) -> tuple[AdaptiveRiskPolicy | None, CandidateScore | None]:
    safe = [(policy, score) for policy, score in scored if score.safe_candidate]
    if not safe:
        return None, None
    return max(safe, key=lambda item: item[1].selection_key(item[0]))


def _score_material(score: CandidateScore) -> dict[str, object]:
    return asdict(score)


def _safe_status(score: CandidateScore | None) -> str:
    if score is None:
        return "NO_SAFE_30D_SOLUTION"
    probability = score.probability_10pct_within_30d_before_breach
    if probability >= 0.25:
        return "MATERIAL_30D_CHALLENGE_CANDIDATE"
    if probability >= 0.10:
        return "LOW_CONFIDENCE_30D_CHALLENGE_CANDIDATE"
    return "SAFE_BUT_NOT_30D_VIABLE"


def build_report(
    baseline_root: Path,
    fresh_root: Path,
    *,
    git_sha: str,
    generated_at: str,
    paths: int = PATHS,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise ChallengeSpeedError("git SHA must be exact")
    trades, constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    if len(trades) != 809:
        raise ChallengeSpeedError(f"expected 809 consumed trades, found {len(trades)}")
    if min(trade.signal_at for trade in trades) < CONSUMED_EVIDENCE_FLOOR:
        raise ChallengeSpeedError("protected holdout evidence encountered")
    samples = {
        name: sum(_scope_membership(trade, name) for trade in trades) for name in PORTFOLIOS
    }
    expected = {"A_CORE": 117, "GBPJPY_RETURN_ENHANCER": 112, "B_COMBINED_PORTFOLIO": 229}
    if samples != expected:
        raise ChallengeSpeedError(f"frozen portfolio cardinality changed: {samples}")

    primary_days = _adaptive_days(trades, constraints, bars, cost_bps=PRIMARY_COST_BPS)
    draws = paired_block_indices(
        len(primary_days),
        paths=paths,
        horizon_days=CHALLENGE_HORIZON_DAYS,
        block_days=BLOCK_DAYS,
        seed=SEED,
    )

    discovery_rows: list[dict[str, object]] = []
    scored: list[tuple[AdaptiveRiskPolicy, CandidateScore]] = []
    for policy in CHALLENGE_POLICIES:
        results = [
            simulate_adaptive_path(
                primary_days,
                indices,
                portfolio="B_COMBINED_PORTFOLIO",
                policy=policy,
                profile=FTMO_2STEP_2026_09_12,
            )
            for indices in draws
        ]
        score = _candidate_score(policy, results)
        scored.append((policy, score))
        discovery_rows.append(
            {
                "policy": _policy_material(policy),
                "policy_fingerprint": _canonical_digest(_policy_material(policy)),
                "score": _score_material(score),
                "B_COMBINED_PORTFOLIO": _summarize_paths(results, policy),
            }
        )

    selected_policy, selected_score = select_policy(scored)
    status = _safe_status(selected_score)
    provider_results: dict[str, object] = {}
    selected_cost_sensitivity: dict[str, object] = {}
    selected_policy_material: dict[str, object] | None = None
    selected_policy_fingerprint: str | None = None

    if selected_policy is not None:
        selected_policy_material = _policy_material(selected_policy)
        selected_policy_fingerprint = _canonical_digest(selected_policy_material)
        for profile in PROFILES:
            raw: dict[str, list[PathMetrics]] = {name: [] for name in PORTFOLIOS}
            for indices in draws:
                for portfolio in PORTFOLIOS:
                    raw[portfolio].append(
                        simulate_adaptive_path(
                            primary_days,
                            indices,
                            portfolio=portfolio,
                            policy=selected_policy,
                            profile=profile,
                        )
                    )
            summarized = {
                portfolio: {
                    "original_sample": samples[portfolio],
                    "challenge_0_50bp": _summarize_paths(results, selected_policy),
                }
                for portfolio, results in raw.items()
            }
            summarized["B_MINUS_A"] = _paired_marginal(
                raw["A_CORE"], raw["B_COMBINED_PORTFOLIO"]
            )
            provider_results[profile.profile_id] = {
                "profile": _profile_material(profile),
                "results": summarized,
            }

        sensitivity_draws = draws[: min(SENSITIVITY_PATHS, len(draws))]
        for cost in COST_GRID_BPS:
            cost_days = _adaptive_days(trades, constraints, bars, cost_bps=cost)
            by_portfolio: dict[str, object] = {}
            for portfolio in PORTFOLIOS:
                results = [
                    simulate_adaptive_path(
                        cost_days,
                        indices,
                        portfolio=portfolio,
                        policy=selected_policy,
                        profile=FTMO_2STEP_2026_09_12,
                    )
                    for indices in sensitivity_draws
                ]
                by_portfolio[portfolio] = _summarize_paths(results, selected_policy)
            selected_cost_sensitivity[format(cost, "f")] = by_portfolio

    file_digests = _file_digests((baseline_root, fresh_root))
    fingerprints = _evidence_fingerprints((baseline_root, fresh_root))
    profiles = {profile.profile_id: _profile_material(profile) for profile in PROFILES}
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "repository": "mezas3238-hue/qore-core",
        "pull_request": 529,
        "branch": "agent/vt08-r3-13-challenge-speed-risk-001",
        "git_sha": git_sha,
        "classification": "CONSUMED-DATA RESEARCH ONLY",
        "independent_validation": False,
        "demo_eligible": False,
        "live_authorized": False,
        "holdout_not_accessed": True,
        "protected_holdout": {
            "start": PROTECTED_HOLDOUT_START.isoformat(),
            "end_exclusive": PROTECTED_HOLDOUT_END.isoformat(),
            "accessed": False,
        },
        "consumed_run_ids": [FRESH_RUN_ID, BASELINE_RUN_ID],
        "input_artifacts": {
            str(run): [{"id": artifact, "digest": digest} for artifact, digest in artifacts]
            for run, artifacts in INPUT_ARTIFACTS.items()
        },
        "input_file_sha256": file_digests,
        "input_data_digest": _canonical_digest(file_digests),
        "methodology_fingerprints": fingerprints["methodology"],
        "source_contract_fingerprints": fingerprints["source_contract"],
        "portfolio_samples": samples,
        "objective": {
            "account_size_usd": "100000",
            "target_return": "0.10",
            "deadline_trading_days": CHALLENGE_HORIZON_DAYS,
            "primary_metric": "P(+10% before breach and on/before trading day 30)",
            "safe_breach_probability_ceiling": MAX_SAFE_BREACH_PROBABILITY,
            "safe_drawdown_p99_ceiling": MAX_SAFE_DRAWDOWN_P99,
        },
        "experiment": {
            "python_version": platform.python_version(),
            "seed": SEED,
            "paths": paths,
            "horizon_trading_days": CHALLENGE_HORIZON_DAYS,
            "block_length_trading_days": BLOCK_DAYS,
            "resampling": "paired moving-block bootstrap over consumed business days",
            "within_block_chronology_preserved": True,
            "simultaneous_events_preserved": True,
            "primary_transaction_cost_bps_per_completed_trade": format(PRIMARY_COST_BPS, "f"),
            "cost_grid_bps": [format(value, "f") for value in COST_GRID_BPS],
            "search_candidates": len(CHALLENGE_POLICIES),
            "multiplicity_retained": True,
            "actual_ctrader_cost_demonstrated": False,
        },
        "provider_profiles": profiles,
        "search_surface": discovery_rows,
        "selection_status": status,
        "selected_policy": selected_policy_material,
        "selected_policy_fingerprint": selected_policy_fingerprint,
        "selected_score": None if selected_score is None else _score_material(selected_score),
        "provider_results": provider_results,
        "selected_cost_sensitivity_FTMO": selected_cost_sensitivity,
        "r3_12_role": "FUNDED_MODE_CAPITAL_PRESERVATION_BASELINE",
        "r3_13_role": "CHALLENGE_MODE_RESEARCH_CANDIDATE_ONLY",
    }


def write_artifacts(report: dict[str, object], output_dir: Path, git_sha: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "challenge-speed-monte-carlo.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "risk-search-surface.json").write_text(
        json.dumps(report["search_surface"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    selected = {
        "selection_status": report["selection_status"],
        "selected_policy": report["selected_policy"],
        "selected_policy_fingerprint": report["selected_policy_fingerprint"],
        "selected_score": report["selected_score"],
        "objective": report["objective"],
    }
    (output_dir / "selected-challenge-policy.json").write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "challenge-cost-sensitivity.json").write_text(
        json.dumps(report["selected_cost_sensitivity_FTMO"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "provider-results.json").write_text(
        json.dumps(report["provider_results"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fingerprint = report["selected_policy_fingerprint"]
    (output_dir / "risk-policy-fingerprint.txt").write_text(
        ("NONE" if fingerprint is None else str(fingerprint)) + "\n", encoding="utf-8"
    )
    (output_dir / "git-sha.txt").write_text(git_sha + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.baseline_root,
        args.fresh_root,
        git_sha=args.git_sha,
        generated_at=args.generated_at,
    )
    write_artifacts(report, args.output_dir, args.git_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
