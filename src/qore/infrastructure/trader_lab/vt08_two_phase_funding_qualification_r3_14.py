"""VT-08 R3.14 two-phase funding qualification Monte Carlo.

Research-only child of R3.13. The Trader, source contract, methodology and
portfolio identities remain frozen. R3.14 models temporary Challenge Mode:
Phase 1 +10%, reset evaluation state, Phase 2 +5%, both within 60 total trading
days, followed by an immediate transition to the conservative R3.12 funded
Risk policy. The protected [2020-07-01, 2022-07-01) holdout is never read.
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
from qore.infrastructure.trader_lab.vt08_challenge_speed_monte_carlo_r3_13 import (
    CHALLENGE_POLICIES,
    _policy,
)
from qore.infrastructure.trader_lab.vt08_official_adaptive_monte_carlo_r3_12 import (
    COST_GRID_BPS,
    PRIMARY_COST_BPS,
    PRIMARY_POLICY,
    PROFILES,
    AdaptivePreparedDay,
    AdaptiveRiskPolicy,
    PathMetrics,
    _adaptive_days,
    _canonical_digest,
    _distribution,
    _evidence_fingerprints,
    _file_digests,
    _policy_material,
    _profile_material,
    _scope_membership,
    simulate_adaptive_path,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    INPUT_ARTIFACTS,
    PORTFOLIOS,
    paired_block_indices,
)
from qore.infrastructure.trader_lab.vt08_prop_firm_profiles_r3_12 import (
    FTMO_2STEP_2026_09_12,
    PropFirmProfile,
)

SCHEMA = "qore.vt08.r3.14.two-phase-funding-qualification.v1"
PATHS = 10_000
SENSITIVITY_PATHS = 2_500
SEED = 2026091302
TOTAL_HORIZON_DAYS = 60
BLOCK_DAYS = 5
PHASE1_TARGET_INDEX = 2
PHASE2_TARGET_INDEX = 0
PHASE1_TARGET = Decimal("0.10")
PHASE2_TARGET = Decimal("0.05")
MAX_SAFE_BREACH_PROBABILITY = 0.01
MAX_SAFE_DRAWDOWN_P99 = 0.06
PROTECTED_HOLDOUT_START = date(2020, 7, 1)
PROTECTED_HOLDOUT_END = date(2022, 7, 1)
PRIMARY_SEARCH_PROFILE = FTMO_2STEP_2026_09_12


class TwoPhaseQualificationError(ValueError):
    """Raised when R3.14 governance or experiment invariants fail."""


_POLICIES_BY_NAME = {policy.name: policy for policy in CHALLENGE_POLICIES}

PHASE1_POLICIES = (
    _POLICIES_BY_NAME["challenge-150bps-v1"],
    _POLICIES_BY_NAME["challenge-200bps-v1"],
    _policy(
        "challenge-225bps-r314",
        a_base="225",
        g_base="170",
        a_floor="55",
        g_floor="45",
        a_ceiling="280",
        g_ceiling="215",
        heat="500",
        a_heat="365",
        g_heat="280",
        correlation="300",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="112.5",
    ),
    _policy(
        "challenge-250bps-r314",
        a_base="250",
        g_base="190",
        a_floor="60",
        g_floor="50",
        a_ceiling="310",
        g_ceiling="240",
        heat="550",
        a_heat="400",
        g_heat="310",
        correlation="330",
        daily_guard="300",
        dd_guard="600",
        upshift="5",
        downshift="125",
    ),
)

PHASE2_POLICIES = (
    _POLICIES_BY_NAME["challenge-075bps-v1"],
    _POLICIES_BY_NAME["challenge-100bps-v1"],
    _POLICIES_BY_NAME["challenge-125bps-v1"],
    _POLICIES_BY_NAME["challenge-150bps-v1"],
)


@dataclass(frozen=True, slots=True)
class PhaseOutcome:
    metrics: PathMetrics
    passed: bool
    completion_day: int | None
    available_days: int


@dataclass(frozen=True, slots=True)
class RiskPairScore:
    phase1_policy_name: str
    phase2_policy_name: str
    probability_phase1_pass_within_60d: float
    probability_phase2_pass_given_phase1: float
    probability_two_phase_complete_within_30d: float
    probability_two_phase_complete_within_45d: float
    probability_two_phase_complete_within_60d: float
    phase1_breach_probability: float
    phase2_breach_probability_given_phase1: float
    combined_breach_probability: float
    challenge_drawdown_p95: float
    challenge_drawdown_p99: float
    ruin_probability: float
    median_phase1_completion_days: float | None
    median_phase2_completion_days: float | None
    median_total_completion_days: float | None
    p95_total_completion_days: float | None
    expected_attempts_per_two_phase_completion: float | None
    safe_candidate: bool

    def selection_key(
        self,
        phase1_policy: AdaptiveRiskPolicy,
        phase2_policy: AdaptiveRiskPolicy,
    ) -> tuple[float, float, float, float, float]:
        median_days = (
            float(TOTAL_HORIZON_DAYS + 1)
            if self.median_total_completion_days is None
            else self.median_total_completion_days
        )
        combined_base = float(phase1_policy.a_base_bps + phase2_policy.a_base_bps)
        return (
            self.probability_two_phase_complete_within_60d,
            -self.combined_breach_probability,
            -self.challenge_drawdown_p99,
            -median_days,
            -combined_base,
        )


def phase_completion_day(
    *,
    target_day: int | None,
    first_breach_day: int | None,
    minimum_trading_days: int,
    available_days: int,
) -> int | None:
    """Return the phase completion day, enforcing provider minimum days fail-closed."""
    if target_day is None:
        return None
    completion = max(target_day, minimum_trading_days)
    if completion > available_days:
        return None
    if first_breach_day is not None and first_breach_day <= completion:
        return None
    return completion


def _run_phase(
    days: Sequence[AdaptivePreparedDay],
    indices: Sequence[int],
    *,
    policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
    target_index: int,
) -> PhaseOutcome:
    if not indices:
        raise TwoPhaseQualificationError("phase cannot run with zero available trading days")
    full = simulate_adaptive_path(
        days,
        indices,
        portfolio="B_COMBINED_PORTFOLIO",
        policy=policy,
        profile=profile,
    )
    completion = phase_completion_day(
        target_day=full.target_days[target_index],
        first_breach_day=full.first_breach_day,
        minimum_trading_days=profile.minimum_trading_days_per_phase,
        available_days=len(indices),
    )
    if completion is None:
        return PhaseOutcome(full, False, None, len(indices))
    if completion == len(indices):
        return PhaseOutcome(full, True, completion, len(indices))
    stopped = simulate_adaptive_path(
        days,
        indices[:completion],
        portfolio="B_COMBINED_PORTFOLIO",
        policy=policy,
        profile=profile,
    )
    stopped_completion = phase_completion_day(
        target_day=stopped.target_days[target_index],
        first_breach_day=stopped.first_breach_day,
        minimum_trading_days=profile.minimum_trading_days_per_phase,
        available_days=completion,
    )
    if stopped_completion != completion:
        raise TwoPhaseQualificationError("phase prefix replay changed completion semantics")
    return PhaseOutcome(stopped, True, completion, len(indices))


def _phase1_cache(
    days: Sequence[AdaptivePreparedDay],
    draws: Sequence[Sequence[int]],
    *,
    policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
) -> list[PhaseOutcome]:
    return [
        _run_phase(
            days,
            indices,
            policy=policy,
            profile=profile,
            target_index=PHASE1_TARGET_INDEX,
        )
        for indices in draws
    ]


def _pair_score(
    days: Sequence[AdaptivePreparedDay],
    draws: Sequence[Sequence[int]],
    *,
    phase1_policy: AdaptiveRiskPolicy,
    phase2_policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
    cached_phase1: Sequence[PhaseOutcome] | None = None,
) -> tuple[RiskPairScore, dict[str, object]]:
    if not draws:
        raise TwoPhaseQualificationError("draw set cannot be empty")
    if phase2_policy.a_base_bps > phase1_policy.a_base_bps:
        raise TwoPhaseQualificationError("Phase 2 base Risk cannot exceed Phase 1 base Risk")
    phase1 = (
        list(cached_phase1)
        if cached_phase1 is not None
        else _phase1_cache(days, draws, policy=phase1_policy, profile=profile)
    )
    if len(phase1) != len(draws):
        raise TwoPhaseQualificationError("Phase 1 cache cardinality mismatch")

    phase1_pass_days: list[float] = []
    phase2_pass_days: list[float] = []
    total_pass_days: list[float] = []
    challenge_drawdowns: list[float] = []
    phase1_drawdowns: list[float] = []
    phase2_drawdowns: list[float] = []
    phase1_passes = 0
    phase2_passes = 0
    phase1_breaches = 0
    phase2_breaches = 0
    combined_breaches = 0
    ruins = 0
    pass_by_30 = 0
    pass_by_45 = 0
    pass_by_60 = 0
    phase1_allow = 0
    phase1_reduce = 0
    phase1_reject = 0
    phase2_allow = 0
    phase2_reduce = 0
    phase2_reject = 0

    for indices, p1 in zip(draws, phase1, strict=True):
        phase1_drawdowns.append(p1.metrics.max_drawdown)
        phase1_allow += p1.metrics.allow
        phase1_reduce += p1.metrics.reduce
        phase1_reject += p1.metrics.reject
        path_dd = p1.metrics.max_drawdown
        path_breach = p1.metrics.any_prop_firm_breach
        path_ruin = p1.metrics.ruin
        if p1.metrics.any_prop_firm_breach:
            phase1_breaches += 1

        if not p1.passed or p1.completion_day is None:
            challenge_drawdowns.append(path_dd)
            combined_breaches += int(path_breach)
            ruins += int(path_ruin)
            continue

        phase1_passes += 1
        phase1_pass_days.append(float(p1.completion_day))
        remaining = indices[p1.completion_day :]
        if not remaining:
            challenge_drawdowns.append(path_dd)
            combined_breaches += int(path_breach)
            ruins += int(path_ruin)
            continue

        p2 = _run_phase(
            days,
            remaining,
            policy=phase2_policy,
            profile=profile,
            target_index=PHASE2_TARGET_INDEX,
        )
        phase2_drawdowns.append(p2.metrics.max_drawdown)
        phase2_allow += p2.metrics.allow
        phase2_reduce += p2.metrics.reduce
        phase2_reject += p2.metrics.reject
        path_dd = max(path_dd, p2.metrics.max_drawdown)
        path_breach = path_breach or p2.metrics.any_prop_firm_breach
        path_ruin = path_ruin or p2.metrics.ruin
        if p2.metrics.any_prop_firm_breach:
            phase2_breaches += 1

        if p2.passed and p2.completion_day is not None:
            phase2_passes += 1
            phase2_pass_days.append(float(p2.completion_day))
            total = p1.completion_day + p2.completion_day
            total_pass_days.append(float(total))
            pass_by_30 += int(total <= 30)
            pass_by_45 += int(total <= 45)
            pass_by_60 += int(total <= 60)

        challenge_drawdowns.append(path_dd)
        combined_breaches += int(path_breach)
        ruins += int(path_ruin)

    n = len(draws)
    p1_probability = phase1_passes / n
    p2_conditional = 0.0 if phase1_passes == 0 else phase2_passes / phase1_passes
    p_two = pass_by_60 / n
    dd = _distribution(challenge_drawdowns)
    phase1_dd = _distribution(phase1_drawdowns)
    phase2_dd = None if not phase2_drawdowns else _distribution(phase2_drawdowns)
    combined_breach_probability = combined_breaches / n
    ruin_probability = ruins / n
    safe = (
        combined_breach_probability <= MAX_SAFE_BREACH_PROBABILITY
        and dd["p99"] <= MAX_SAFE_DRAWDOWN_P99
        and ruin_probability == 0.0
        and phase1_policy.upshift_step_bps < phase1_policy.downshift_step_bps
        and phase2_policy.upshift_step_bps < phase2_policy.downshift_step_bps
        and phase2_policy.a_base_bps <= phase1_policy.a_base_bps
    )
    score = RiskPairScore(
        phase1_policy_name=phase1_policy.name,
        phase2_policy_name=phase2_policy.name,
        probability_phase1_pass_within_60d=p1_probability,
        probability_phase2_pass_given_phase1=p2_conditional,
        probability_two_phase_complete_within_30d=pass_by_30 / n,
        probability_two_phase_complete_within_45d=pass_by_45 / n,
        probability_two_phase_complete_within_60d=p_two,
        phase1_breach_probability=phase1_breaches / n,
        phase2_breach_probability_given_phase1=(
            0.0 if phase1_passes == 0 else phase2_breaches / phase1_passes
        ),
        combined_breach_probability=combined_breach_probability,
        challenge_drawdown_p95=dd["p95"],
        challenge_drawdown_p99=dd["p99"],
        ruin_probability=ruin_probability,
        median_phase1_completion_days=(
            None if not phase1_pass_days else median(phase1_pass_days)
        ),
        median_phase2_completion_days=(
            None if not phase2_pass_days else median(phase2_pass_days)
        ),
        median_total_completion_days=(
            None if not total_pass_days else median(total_pass_days)
        ),
        p95_total_completion_days=(
            None if not total_pass_days else _distribution(total_pass_days)["p95"]
        ),
        expected_attempts_per_two_phase_completion=(None if p_two == 0 else 1.0 / p_two),
        safe_candidate=safe,
    )
    diagnostics: dict[str, object] = {
        "phase1_drawdown": phase1_dd,
        "phase2_drawdown_conditional_on_phase1": phase2_dd,
        "challenge_drawdown": dd,
        "phase1_decisions": {
            "ALLOW": phase1_allow,
            "REDUCE": phase1_reduce,
            "REJECT": phase1_reject,
        },
        "phase2_decisions": {
            "ALLOW": phase2_allow,
            "REDUCE": phase2_reduce,
            "REJECT": phase2_reject,
        },
        "phase1_passes": phase1_passes,
        "phase2_passes": phase2_passes,
        "two_phase_passes": pass_by_60,
        "phase1_breaches": phase1_breaches,
        "phase2_breaches": phase2_breaches,
        "combined_breaches": combined_breaches,
        "ruins": ruins,
    }
    return score, diagnostics


def select_risk_pair(
    scored: Sequence[
        tuple[AdaptiveRiskPolicy, AdaptiveRiskPolicy, RiskPairScore]
    ],
) -> tuple[AdaptiveRiskPolicy | None, AdaptiveRiskPolicy | None, RiskPairScore | None]:
    safe = [item for item in scored if item[2].safe_candidate]
    if not safe:
        return None, None, None
    phase1, phase2, score = max(
        safe,
        key=lambda item: item[2].selection_key(item[0], item[1]),
    )
    return phase1, phase2, score


def _selection_status(score: RiskPairScore | None) -> str:
    if score is None:
        return "NO_SAFE_TWO_PHASE_SOLUTION"
    probability = score.probability_two_phase_complete_within_60d
    if probability >= 0.25:
        return "MATERIAL_60D_TWO_PHASE_CANDIDATE"
    if probability >= 0.10:
        return "LOW_CONFIDENCE_60D_TWO_PHASE_CANDIDATE"
    return "SAFE_BUT_LOW_60D_COMPLETION"


def _pair_material(
    phase1_policy: AdaptiveRiskPolicy,
    phase2_policy: AdaptiveRiskPolicy,
) -> dict[str, object]:
    return {
        "phase1": _policy_material(phase1_policy),
        "phase2": _policy_material(phase2_policy),
    }


def _pair_fingerprint(
    phase1_policy: AdaptiveRiskPolicy,
    phase2_policy: AdaptiveRiskPolicy,
) -> str:
    return _canonical_digest(_pair_material(phase1_policy, phase2_policy))


def _evaluate_selected_provider(
    days: Sequence[AdaptivePreparedDay],
    draws: Sequence[Sequence[int]],
    *,
    phase1_policy: AdaptiveRiskPolicy,
    phase2_policy: AdaptiveRiskPolicy,
    profile: PropFirmProfile,
) -> dict[str, object]:
    p1_cache = _phase1_cache(days, draws, policy=phase1_policy, profile=profile)
    score, diagnostics = _pair_score(
        days,
        draws,
        phase1_policy=phase1_policy,
        phase2_policy=phase2_policy,
        profile=profile,
        cached_phase1=p1_cache,
    )
    return {
        "profile": _profile_material(profile),
        "fixed_qualification_targets": {
            "phase1": format(PHASE1_TARGET, "f"),
            "phase2": format(PHASE2_TARGET, "f"),
            "total_horizon_trading_days": TOTAL_HORIZON_DAYS,
            "minimum_trading_days_per_phase": profile.minimum_trading_days_per_phase,
        },
        "score": asdict(score),
        "diagnostics": diagnostics,
    }


def build_report(
    baseline_root: Path,
    fresh_root: Path,
    *,
    git_sha: str,
    generated_at: str,
    paths: int = PATHS,
) -> dict[str, object]:
    if re.fullmatch(r"[0-9a-f]{40}", git_sha) is None:
        raise TwoPhaseQualificationError("git SHA must be exact")
    trades, constraints, bars = load_consumed_evidence(baseline_root, fresh_root)
    if len(trades) != 809:
        raise TwoPhaseQualificationError(f"expected 809 consumed trades, found {len(trades)}")
    if min(trade.signal_at for trade in trades) < CONSUMED_EVIDENCE_FLOOR:
        raise TwoPhaseQualificationError("protected holdout evidence encountered")
    samples = {
        name: sum(_scope_membership(trade, name) for trade in trades)
        for name in PORTFOLIOS
    }
    expected = {
        "A_CORE": 117,
        "GBPJPY_RETURN_ENHANCER": 112,
        "B_COMBINED_PORTFOLIO": 229,
    }
    if samples != expected:
        raise TwoPhaseQualificationError(f"frozen portfolio cardinality changed: {samples}")

    primary_days = _adaptive_days(
        trades,
        constraints,
        bars,
        cost_bps=PRIMARY_COST_BPS,
    )
    draws = paired_block_indices(
        len(primary_days),
        paths=paths,
        horizon_days=TOTAL_HORIZON_DAYS,
        block_days=BLOCK_DAYS,
        seed=SEED,
    )

    search_rows: list[dict[str, object]] = []
    scored: list[tuple[AdaptiveRiskPolicy, AdaptiveRiskPolicy, RiskPairScore]] = []
    phase1_caches = {
        policy.name: _phase1_cache(
            primary_days,
            draws,
            policy=policy,
            profile=PRIMARY_SEARCH_PROFILE,
        )
        for policy in PHASE1_POLICIES
    }
    for phase1_policy in PHASE1_POLICIES:
        for phase2_policy in PHASE2_POLICIES:
            score, diagnostics = _pair_score(
                primary_days,
                draws,
                phase1_policy=phase1_policy,
                phase2_policy=phase2_policy,
                profile=PRIMARY_SEARCH_PROFILE,
                cached_phase1=phase1_caches[phase1_policy.name],
            )
            scored.append((phase1_policy, phase2_policy, score))
            search_rows.append(
                {
                    "phase1_policy": _policy_material(phase1_policy),
                    "phase2_policy": _policy_material(phase2_policy),
                    "pair_fingerprint": _pair_fingerprint(
                        phase1_policy,
                        phase2_policy,
                    ),
                    "score": asdict(score),
                    "diagnostics": diagnostics,
                }
            )

    selected_phase1, selected_phase2, selected_score = select_risk_pair(scored)
    status = _selection_status(selected_score)
    provider_results: dict[str, object] = {}
    cost_sensitivity: dict[str, object] = {}
    selected_pair: dict[str, object] | None = None
    selected_fingerprint: str | None = None

    if selected_phase1 is not None and selected_phase2 is not None:
        selected_pair = _pair_material(selected_phase1, selected_phase2)
        selected_fingerprint = _pair_fingerprint(selected_phase1, selected_phase2)
        for profile in PROFILES:
            provider_results[profile.profile_id] = _evaluate_selected_provider(
                primary_days,
                draws,
                phase1_policy=selected_phase1,
                phase2_policy=selected_phase2,
                profile=profile,
            )

        sensitivity_draws = draws[: min(SENSITIVITY_PATHS, len(draws))]
        for cost in COST_GRID_BPS:
            cost_days = _adaptive_days(trades, constraints, bars, cost_bps=cost)
            p1_cache = _phase1_cache(
                cost_days,
                sensitivity_draws,
                policy=selected_phase1,
                profile=PRIMARY_SEARCH_PROFILE,
            )
            score, diagnostics = _pair_score(
                cost_days,
                sensitivity_draws,
                phase1_policy=selected_phase1,
                phase2_policy=selected_phase2,
                profile=PRIMARY_SEARCH_PROFILE,
                cached_phase1=p1_cache,
            )
            cost_sensitivity[format(cost, "f")] = {
                "score": asdict(score),
                "diagnostics": diagnostics,
            }

    file_digests = _file_digests((baseline_root, fresh_root))
    fingerprints = _evidence_fingerprints((baseline_root, fresh_root))
    profiles = {profile.profile_id: _profile_material(profile) for profile in PROFILES}
    funded_policy = _policy_material(PRIMARY_POLICY)
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "repository": "mezas3238-hue/qore-core",
        "pull_request": 530,
        "branch": "agent/vt08-r3-14-two-phase-funding-001",
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
            str(run): [
                {"id": artifact, "digest": digest}
                for artifact, digest in artifacts
            ]
            for run, artifacts in INPUT_ARTIFACTS.items()
        },
        "input_file_sha256": file_digests,
        "input_data_digest": _canonical_digest(file_digests),
        "methodology_fingerprints": fingerprints["methodology"],
        "source_contract_fingerprints": fingerprints["source_contract"],
        "portfolio_samples": samples,
        "objective": {
            "account_size_usd": "100000",
            "phase1_target_return": format(PHASE1_TARGET, "f"),
            "phase2_target_return": format(PHASE2_TARGET, "f"),
            "total_deadline_trading_days": TOTAL_HORIZON_DAYS,
            "primary_metric": (
                "P(Phase1 +10% -> Phase2 +5% before breach "
                "and within 60 total trading days)"
            ),
            "safe_breach_probability_ceiling": MAX_SAFE_BREACH_PROBABILITY,
            "safe_drawdown_p99_ceiling": MAX_SAFE_DRAWDOWN_P99,
        },
        "experiment": {
            "python_version": platform.python_version(),
            "seed": SEED,
            "paths_per_risk_pair": paths,
            "total_horizon_trading_days": TOTAL_HORIZON_DAYS,
            "block_length_trading_days": BLOCK_DAYS,
            "resampling": "paired moving-block bootstrap over consumed business days",
            "within_block_chronology_preserved": True,
            "simultaneous_events_preserved": True,
            "phase_boundary_account_state_reset": True,
            "phase_boundary_risk_memory_reset": True,
            "primary_transaction_cost_bps_per_completed_trade": format(
                PRIMARY_COST_BPS,
                "f",
            ),
            "cost_grid_bps": [format(value, "f") for value in COST_GRID_BPS],
            "phase1_candidates": len(PHASE1_POLICIES),
            "phase2_candidates": len(PHASE2_POLICIES),
            "risk_pair_candidates": len(PHASE1_POLICIES) * len(PHASE2_POLICIES),
            "multiplicity_retained": True,
            "actual_ctrader_cost_demonstrated": False,
        },
        "provider_profiles": profiles,
        "primary_search_profile": PRIMARY_SEARCH_PROFILE.profile_id,
        "search_surface": search_rows,
        "selection_status": status,
        "selected_pair": selected_pair,
        "selected_pair_fingerprint": selected_fingerprint,
        "selected_score": None if selected_score is None else asdict(selected_score),
        "provider_results": provider_results,
        "selected_cost_sensitivity_FTMO": cost_sensitivity,
        "funded_mode_transition": {
            "trigger": "successful Phase 2 completion",
            "challenge_risk_state_discarded": True,
            "funded_risk_state_fresh": True,
            "policy": funded_policy,
            "policy_fingerprint": _canonical_digest(funded_policy),
            "role": "CAPITAL_PRESERVATION_AFTER_QUALIFICATION",
        },
        "r3_13_role": "SINGLE_PHASE_CHALLENGE_SPEED_BASELINE",
        "r3_14_role": "TWO_PHASE_TEMPORARY_CHALLENGE_QUALIFICATION_RESEARCH",
    }


def write_artifacts(report: dict[str, object], output_dir: Path, git_sha: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "two-phase-funding-qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "risk-pair-search-surface.json").write_text(
        json.dumps(report["search_surface"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    selected = {
        "selection_status": report["selection_status"],
        "selected_pair": report["selected_pair"],
        "selected_pair_fingerprint": report["selected_pair_fingerprint"],
        "selected_score": report["selected_score"],
        "objective": report["objective"],
    }
    (output_dir / "selected-two-phase-policy.json").write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "provider-results.json").write_text(
        json.dumps(report["provider_results"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "cost-sensitivity.json").write_text(
        json.dumps(
            report["selected_cost_sensitivity_FTMO"],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "funded-mode-transition.json").write_text(
        json.dumps(report["funded_mode_transition"], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    fingerprint = report["selected_pair_fingerprint"]
    (output_dir / "risk-policy-fingerprint.txt").write_text(
        ("NONE" if fingerprint is None else str(fingerprint)) + "\n",
        encoding="utf-8",
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
