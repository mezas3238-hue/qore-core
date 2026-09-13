"""Paired challenge and two-year CIBO influence studies for VT-08 R3.16."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from statistics import median
from typing import Protocol, cast

from qore.infrastructure.trader_lab.vt08_cibo_data_r3_16 import (
    CHALLENGE_END,
    CHALLENGE_START,
    LONG_END,
    LONG_START,
    PORTFOLIOS,
    STOP_POLICIES,
    ReplayTrade,
    StopPolicy,
    signal_identity,
)
from qore.infrastructure.trader_lab.vt08_cibo_engine_r3_16 import (
    CAPITAL_GUARDS,
    FINAL_PATHS,
    FINAL_SEED,
    PHASE_DAYS,
    PRIMARY_PHASE1_TARGET,
    PRIMARY_PHASE2_TARGET,
    RISK_LEVELS,
    SEARCH_PATHS,
    SEARCH_SEED,
    SENSITIVITY_PHASE1_TARGET,
    SENSITIVITY_PHASE2_TARGET,
    CapitalGuard,
    RiskLevel,
    SequenceMetrics,
    day_map,
    moving_block_draws,
    quantile,
    run_sequence,
    weekdays,
)


class _NamedPolicy(Protocol):
    name: str


@dataclass(frozen=True, slots=True)
class ChallengeScore:
    portfolio: str
    stop_policy: str
    capital_guard: str
    risk_level: str
    phase1_pass_probability: float
    phase2_pass_given_phase1: float
    two_phase_pass_probability: float
    drawdown_p99: float
    median_total_completion_days: float | None
    mean_risk_lockouts_per_path: float

    def selection_key(self) -> tuple[float, float, float, float]:
        risk = next(item for item in RISK_LEVELS if item.name == self.risk_level)
        return (
            self.two_phase_pass_probability,
            self.phase1_pass_probability,
            -self.mean_risk_lockouts_per_path,
            -risk.a_risk,
        )


def _by_name(name: str, values: Sequence[_NamedPolicy]) -> _NamedPolicy:
    for value in values:
        if value.name == name:
            return value
    raise ValueError(f"policy not found: {name}")


def challenge_score(
    *,
    portfolio: str,
    stop_policy: StopPolicy,
    guard: CapitalGuard,
    risk: RiskLevel,
    mapped: Mapping[date, Mapping[int, Sequence[ReplayTrade]]],
    base_days: Sequence[date],
    draws: Sequence[Sequence[int]],
    phase1_target: float,
    phase2_target: float,
) -> ChallengeScore:
    phase1_passes = 0
    phase2_passes = 0
    total_days: list[float] = []
    drawdowns: list[float] = []
    lockouts = 0
    for draw in draws:
        first = [base_days[index] for index in draw[:PHASE_DAYS]]
        second = [base_days[index] for index in draw[PHASE_DAYS:]]
        phase1 = run_sequence(
            first,
            mapped,
            risk=risk,
            guard=guard,
            target=phase1_target,
            stop_on_target=True,
        )
        drawdown = phase1.maximum_drawdown
        lockouts += phase1.risk_lockouts
        if not phase1.success or phase1.completion_day is None:
            drawdowns.append(drawdown)
            continue
        phase1_passes += 1
        phase2 = run_sequence(
            second,
            mapped,
            risk=risk,
            guard=guard,
            target=phase2_target,
            stop_on_target=True,
        )
        drawdown = max(drawdown, phase2.maximum_drawdown)
        lockouts += phase2.risk_lockouts
        if phase2.success and phase2.completion_day is not None:
            phase2_passes += 1
            total_days.append(float(phase1.completion_day + phase2.completion_day))
        drawdowns.append(drawdown)
    count = len(draws)
    return ChallengeScore(
        portfolio=portfolio,
        stop_policy=stop_policy.name,
        capital_guard=guard.name,
        risk_level=risk.name,
        phase1_pass_probability=phase1_passes / count,
        phase2_pass_given_phase1=(
            0.0 if phase1_passes == 0 else phase2_passes / phase1_passes
        ),
        two_phase_pass_probability=phase2_passes / count,
        drawdown_p99=quantile(drawdowns, 0.99),
        median_total_completion_days=None if not total_days else median(total_days),
        mean_risk_lockouts_per_path=lockouts / count,
    )


def challenge_study(
    records_by_stop: Mapping[str, Sequence[ReplayTrade]],
) -> dict[str, object]:
    base_days = weekdays(CHALLENGE_START, CHALLENGE_END)
    search_draws = moving_block_draws(
        len(base_days), paths=SEARCH_PATHS, seed=SEARCH_SEED
    )
    final_draws = moving_block_draws(
        len(base_days), paths=FINAL_PATHS, seed=FINAL_SEED
    )
    rows: list[dict[str, object]] = []
    selected: dict[str, dict[str, object]] = {}
    for portfolio in PORTFOLIOS:
        baseline_identity = signal_identity(records_by_stop["off"], portfolio)
        scored: list[ChallengeScore] = []
        maps: dict[str, dict[date, dict[int, list[ReplayTrade]]]] = {}
        for stop_policy in STOP_POLICIES:
            records = records_by_stop[stop_policy.name]
            if signal_identity(records, portfolio) != baseline_identity:
                raise ValueError("CIBO mutated VT-08 generated entry identities")
            maps[stop_policy.name] = day_map(records, portfolio)
            for guard in CAPITAL_GUARDS:
                for risk in RISK_LEVELS:
                    score = challenge_score(
                        portfolio=portfolio,
                        stop_policy=stop_policy,
                        guard=guard,
                        risk=risk,
                        mapped=maps[stop_policy.name],
                        base_days=base_days,
                        draws=search_draws,
                        phase1_target=PRIMARY_PHASE1_TARGET,
                        phase2_target=PRIMARY_PHASE2_TARGET,
                    )
                    scored.append(score)
                    rows.append(asdict(score))
        best = max(scored, key=lambda item: item.selection_key())
        stop = cast(StopPolicy, _by_name(best.stop_policy, STOP_POLICIES))
        guard = cast(CapitalGuard, _by_name(best.capital_guard, CAPITAL_GUARDS))
        risk = cast(RiskLevel, _by_name(best.risk_level, RISK_LEVELS))
        primary = challenge_score(
            portfolio=portfolio,
            stop_policy=stop,
            guard=guard,
            risk=risk,
            mapped=maps[stop.name],
            base_days=base_days,
            draws=final_draws,
            phase1_target=PRIMARY_PHASE1_TARGET,
            phase2_target=PRIMARY_PHASE2_TARGET,
        )
        sensitivity = challenge_score(
            portfolio=portfolio,
            stop_policy=stop,
            guard=guard,
            risk=risk,
            mapped=maps[stop.name],
            base_days=base_days,
            draws=final_draws,
            phase1_target=SENSITIVITY_PHASE1_TARGET,
            phase2_target=SENSITIVITY_PHASE2_TARGET,
        )
        risk_only = challenge_score(
            portfolio=portfolio,
            stop_policy=STOP_POLICIES[0],
            guard=CAPITAL_GUARDS[0],
            risk=risk,
            mapped=maps["off"],
            base_days=base_days,
            draws=final_draws,
            phase1_target=PRIMARY_PHASE1_TARGET,
            phase2_target=PRIMARY_PHASE2_TARGET,
        )
        selected[portfolio] = {
            "generated_entry_count": len(baseline_identity),
            "selected_policy": {
                "stop_policy": asdict(stop),
                "capital_guard": asdict(guard),
                "risk_level": asdict(risk),
            },
            "primary_10_5": asdict(primary),
            "sensitivity_11_6": asdict(sensitivity),
            "same_risk_risk_only_reference": asdict(risk_only),
            "cibo_delta_two_phase_probability": (
                primary.two_phase_pass_probability - risk_only.two_phase_pass_probability
            ),
        }
    return {
        "window": [CHALLENGE_START.isoformat(), CHALLENGE_END.isoformat()],
        "evidence_status": "CONSUMED_RETAINED_R3_15_NOT_FRESH_AFTER_R3_15",
        "selected": selected,
        "search_surface": rows,
    }


def long_run_study(
    records_by_stop: Mapping[str, Sequence[ReplayTrade]],
) -> dict[str, object]:
    days = weekdays(LONG_START, LONG_END)
    rows: list[dict[str, object]] = []
    selected: dict[str, dict[str, object]] = {}
    for portfolio in PORTFOLIOS:
        baseline_identity = signal_identity(records_by_stop["off"], portfolio)
        candidates: list[tuple[float, float, str, str, str, SequenceMetrics]] = []
        maps: dict[str, dict[date, dict[int, list[ReplayTrade]]]] = {}
        for stop in STOP_POLICIES:
            records = records_by_stop[stop.name]
            if signal_identity(records, portfolio) != baseline_identity:
                raise ValueError("CIBO mutated VT-08 generated entry identities")
            maps[stop.name] = day_map(records, portfolio)
            for guard in CAPITAL_GUARDS:
                for risk in RISK_LEVELS:
                    metrics = run_sequence(
                        days,
                        maps[stop.name],
                        risk=risk,
                        guard=guard,
                        target=None,
                        stop_on_target=False,
                    )
                    rows.append(
                        {
                            "portfolio": portfolio,
                            "stop_policy": stop.name,
                            "capital_guard": guard.name,
                            "risk_level": risk.name,
                            **asdict(metrics),
                        }
                    )
                    candidates.append(
                        (
                            metrics.terminal_return,
                            -metrics.maximum_drawdown,
                            stop.name,
                            guard.name,
                            risk.name,
                            metrics,
                        )
                    )
        best = max(candidates, key=lambda item: (item[0], item[1], item[4]))
        stop = cast(StopPolicy, _by_name(best[2], STOP_POLICIES))
        guard = cast(CapitalGuard, _by_name(best[3], CAPITAL_GUARDS))
        risk = cast(RiskLevel, _by_name(best[4], RISK_LEVELS))
        metrics = best[5]
        risk_only = run_sequence(
            days,
            maps["off"],
            risk=risk,
            guard=CAPITAL_GUARDS[0],
            target=None,
            stop_on_target=False,
        )
        selected[portfolio] = {
            "generated_entry_count": len(baseline_identity),
            "selected_policy": {
                "stop_policy": asdict(stop),
                "capital_guard": asdict(guard),
                "risk_level": asdict(risk),
            },
            "selected_metrics": asdict(metrics),
            "same_risk_risk_only_reference": asdict(risk_only),
            "cibo_delta_return": metrics.terminal_return - risk_only.terminal_return,
            "cibo_delta_drawdown": metrics.maximum_drawdown - risk_only.maximum_drawdown,
        }
    return {
        "window": [LONG_START.isoformat(), LONG_END.isoformat()],
        "evidence_status": "CONSUMED_R3_8_RESEARCH_EVIDENCE",
        "selected": selected,
        "search_surface": rows,
    }
