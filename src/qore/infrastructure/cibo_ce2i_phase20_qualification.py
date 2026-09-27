"""Fixed Phase20D V2 economic qualification runner.

The runner consumes only durable fresh-forward evidence/policy books, applies
the pre-registered population gate, reconstructs the frozen minimal-seed hard
constraint baseline, and evaluates four contiguous temporal folds without
refitting.

Decision-time provider costs are explicit proxies. They are never relabeled as
realized execution costs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    Phase20QualificationReadiness,
    assess_phase20d_qualification_readiness,
)


class Phase20QualificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_READY = "NOT_READY"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Phase20QualificationRow:
    decision_epoch_id: str
    decision_evidence_sha256: str
    decision_at: datetime
    signal_fingerprint: str
    trader_id: str
    stop_risk_usd: Decimal
    margin_usd: Decimal
    concentration_group: str
    concentration_risk_usd: Decimal
    expected_capital_minutes: Decimal
    provider_cost_proxy_usd: Decimal
    policy_selected: bool
    baseline_selected: bool
    realized_structural_outcome_r: Decimal | None
    outcome_observed_at: datetime | None

    @property
    def policy_net_delta_usd(self) -> Decimal:
        if not self.policy_selected or self.realized_structural_outcome_r is None:
            return Decimal(0)
        return (
            self.realized_structural_outcome_r * self.stop_risk_usd
            - self.provider_cost_proxy_usd
        )

    @property
    def baseline_net_delta_usd(self) -> Decimal:
        if not self.baseline_selected or self.realized_structural_outcome_r is None:
            return Decimal(0)
        return (
            self.realized_structural_outcome_r * self.stop_risk_usd
            - self.provider_cost_proxy_usd
        )


@dataclass(frozen=True, slots=True)
class Phase20QualificationFold:
    fold_id: str
    decision_epoch_count: int
    candidate_count: int
    policy_selected_count: int
    baseline_selected_count: int
    policy_net_delta_usd: Decimal
    baseline_net_delta_usd: Decimal


@dataclass(frozen=True, slots=True)
class Phase20QualificationReport:
    status: Phase20QualificationStatus
    plan_id: str
    plan_sha256: str
    candidate_id: str
    readiness: Phase20QualificationReadiness
    failures: tuple[str, ...]
    rows: tuple[Phase20QualificationRow, ...]
    folds: tuple[Phase20QualificationFold, ...]
    policy_net_delta_usd: Decimal
    baseline_net_delta_usd: Decimal
    policy_max_drawdown_usd: Decimal
    baseline_max_drawdown_usd: Decimal
    policy_capital_productivity: Decimal
    baseline_capital_productivity: Decimal
    policy_acceptance_rate: Decimal
    baseline_acceptance_rate: Decimal
    policy_selected_outcome_coverage: Decimal
    baseline_selected_outcome_coverage: Decimal
    candidate_outcome_coverage: Decimal
    capital_utilization: Decimal
    capital_starvation_rate: Decimal
    mpc_reserve_efficiency: Decimal
    optionality_preserved_rate: Decimal
    concentration_utilization: Decimal
    provider_failure_incidence: Decimal
    evidence_missingness: Decimal


@dataclass(frozen=True, slots=True)
class _ParsedCandidate:
    signal_fingerprint: str
    trader_id: str
    stop_risk_usd: Decimal
    margin_usd: Decimal
    concentration_group: str
    concentration_risk_usd: Decimal
    expected_capital_minutes: Decimal
    provider_cost_proxy_usd: Decimal


def run_phase20d_v2_qualification(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> Phase20QualificationReport:
    """Run the frozen V2 protocol; no parameters are fitted from outcomes."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20D qualification requires canonical evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20D qualification requires canonical policy book"
        )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    readiness = assess_phase20d_qualification_readiness(
        evidence_book=evidence_book,
        policy_book=policy_book,
    )
    policy_by_sha = {
        item.evidence_sha256: item for item in policy_book.decisions
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in evidence_book.outcomes
    }

    rows: list[Phase20QualificationRow] = []
    safety_failures: list[str] = []
    policy_capacity_total = Decimal(0)
    policy_capacity_used = Decimal(0)
    concentration_limit_total = Decimal(0)
    concentration_used_total = Decimal(0)
    starvation_rejections = 0
    candidate_count = 0
    considered_option_epochs = 0
    coverable_option_epochs = 0
    population_slots = 0
    provider_failures = 0

    ordered_decisions = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )
    for decision in ordered_decisions:
        payload = _decision_payload(decision)
        if payload.get("evidence_kind") != "FORWARD_OBSERVED":
            safety_failures.append("ZERO_CAUSAL_CONTAMINATION")
        policy = policy_by_sha.get(decision.evidence_sha256)
        if policy is None:
            safety_failures.append("MISSING_POLICY_DECISIONS")
            selected: set[str] = set()
            policy_record: dict[str, object] = {}
        else:
            selected = set(policy.selected_signal_fingerprints)
            policy_record = _policy_payload(policy)

        candidates = _parse_candidates(payload)
        candidate_count += len(candidates)
        baseline_selected = _baseline_selection(
            payload=payload,
            candidates=candidates,
        )
        candidate_map = {
            item.signal_fingerprint: item for item in candidates
        }
        if not selected.issubset(candidate_map):
            safety_failures.append("ZERO_CAPITAL_CONSERVATION_BREACHES")

        _inspect_policy_safety(
            payload=payload,
            policy_record=policy_record,
            failures=safety_failures,
        )
        cap, used, conc_limit, conc_used, starved, considered, coverable = (
            _policy_operational_metrics(
                payload=payload,
                policy_record=policy_record,
            )
        )
        policy_capacity_total += cap
        policy_capacity_used += used
        concentration_limit_total += conc_limit
        concentration_used_total += conc_used
        starvation_rejections += starved
        considered_option_epochs += considered
        coverable_option_epochs += coverable

        slots = payload.get("population_slots", [])
        if not isinstance(slots, list):
            raise CiboCapitalManagementError(
                "Phase20D canonical population slots must be list"
            )
        population_slots += len(slots)
        provider_failures += sum(
            1
            for item in slots
            if isinstance(item, dict)
            and item.get("disposition") == "FAIL_CLOSED"
        )

        for candidate in candidates:
            outcome = outcomes.get(
                (decision.evidence_sha256, candidate.signal_fingerprint)
            )
            rows.append(
                Phase20QualificationRow(
                    decision_epoch_id=decision.decision_epoch_id,
                    decision_evidence_sha256=decision.evidence_sha256,
                    decision_at=decision.decision_at,
                    signal_fingerprint=candidate.signal_fingerprint,
                    trader_id=candidate.trader_id,
                    stop_risk_usd=candidate.stop_risk_usd,
                    margin_usd=candidate.margin_usd,
                    concentration_group=candidate.concentration_group,
                    concentration_risk_usd=candidate.concentration_risk_usd,
                    expected_capital_minutes=(
                        candidate.expected_capital_minutes
                    ),
                    provider_cost_proxy_usd=(
                        candidate.provider_cost_proxy_usd
                    ),
                    policy_selected=(
                        candidate.signal_fingerprint in selected
                    ),
                    baseline_selected=(
                        candidate.signal_fingerprint in baseline_selected
                    ),
                    realized_structural_outcome_r=(
                        None
                        if outcome is None
                        else outcome.realized_structural_outcome_r
                    ),
                    outcome_observed_at=(
                        None if outcome is None else outcome.observed_at
                    ),
                )
            )

    frozen_rows = tuple(rows)
    folds = _build_folds(
        rows=frozen_rows,
        decisions=ordered_decisions,
        fold_count=plan.fold_count,
    )

    policy_selected_rows = tuple(
        item for item in frozen_rows if item.policy_selected
    )
    baseline_selected_rows = tuple(
        item for item in frozen_rows if item.baseline_selected
    )
    policy_net = sum(
        (item.policy_net_delta_usd for item in frozen_rows),
        Decimal(0),
    )
    baseline_net = sum(
        (item.baseline_net_delta_usd for item in frozen_rows),
        Decimal(0),
    )
    policy_dd = _max_drawdown(
        tuple(
            (item.outcome_observed_at, item.signal_fingerprint, item.policy_net_delta_usd)
            for item in frozen_rows
            if item.policy_selected and item.outcome_observed_at is not None
        )
    )
    baseline_dd = _max_drawdown(
        tuple(
            (
                item.outcome_observed_at,
                item.signal_fingerprint,
                item.baseline_net_delta_usd,
            )
            for item in frozen_rows
            if item.baseline_selected and item.outcome_observed_at is not None
        )
    )
    policy_denominator = sum(
        (
            item.stop_risk_usd * item.expected_capital_minutes
            for item in policy_selected_rows
            if item.realized_structural_outcome_r is not None
        ),
        Decimal(0),
    )
    baseline_denominator = sum(
        (
            item.stop_risk_usd * item.expected_capital_minutes
            for item in baseline_selected_rows
            if item.realized_structural_outcome_r is not None
        ),
        Decimal(0),
    )
    policy_productivity = _ratio(policy_net, policy_denominator)
    baseline_productivity = _ratio(baseline_net, baseline_denominator)

    policy_coverage = _coverage_rows(policy_selected_rows)
    baseline_coverage = _coverage_rows(baseline_selected_rows)
    candidate_coverage = _coverage_rows(frozen_rows)
    policy_acceptance = _ratio(
        Decimal(len(policy_selected_rows)),
        Decimal(len(frozen_rows)),
    )
    baseline_acceptance = _ratio(
        Decimal(len(baseline_selected_rows)),
        Decimal(len(frozen_rows)),
    )

    safety_failures = list(dict.fromkeys(safety_failures))
    readiness_reasons: list[str] = []
    if not readiness.ready:
        readiness_reasons.extend(readiness.reasons)
    if (
        baseline_coverage
        < plan.required_baseline_selected_outcome_coverage
    ):
        readiness_reasons.append(
            "BASELINE_SELECTED_OUTCOME_COVERAGE_COMPLETE"
        )
    readiness_reasons = list(dict.fromkeys(readiness_reasons))

    economic_failures: list[str] = []
    if not safety_failures and not readiness_reasons:
        if any(item.policy_net_delta_usd <= 0 for item in folds):
            economic_failures.append(
                "ALL_TEMPORAL_FOLDS_POLICY_DELTA_POSITIVE"
            )
        if policy_net <= 0:
            economic_failures.append("AGGREGATE_POLICY_DELTA_POSITIVE")
        if policy_net < baseline_net:
            economic_failures.append(
                "POLICY_DELTA_NOT_BELOW_FIXED_BASELINE"
            )
        if policy_dd > baseline_dd:
            economic_failures.append(
                "POLICY_MAX_DRAWDOWN_NOT_ABOVE_FIXED_BASELINE"
            )
        if policy_productivity <= baseline_productivity:
            economic_failures.append(
                "POLICY_CAPITAL_PRODUCTIVITY_STRICTLY_ABOVE_FIXED_BASELINE"
            )
        if (
            policy_coverage
            < plan.required_selected_outcome_coverage
        ):
            economic_failures.append("SELECTED_OUTCOME_COVERAGE_COMPLETE")
        if candidate_coverage < plan.minimum_candidate_outcome_coverage:
            economic_failures.append(
                "CANDIDATE_OUTCOME_COVERAGE_AT_LEAST_95_PERCENT"
            )

    if safety_failures:
        status = Phase20QualificationStatus.INVALID
        failures = safety_failures
    elif readiness_reasons:
        status = Phase20QualificationStatus.NOT_READY
        failures = readiness_reasons
    elif economic_failures:
        status = Phase20QualificationStatus.FAIL
        failures = list(dict.fromkeys(economic_failures))
    else:
        status = Phase20QualificationStatus.PASS
        failures = []

    return Phase20QualificationReport(
        status=status,
        plan_id=plan.plan_id,
        plan_sha256=phase20d_qualification_plan_sha256(),
        candidate_id=plan.candidate_id,
        readiness=readiness,
        failures=tuple(failures),
        rows=frozen_rows,
        folds=folds,
        policy_net_delta_usd=policy_net,
        baseline_net_delta_usd=baseline_net,
        policy_max_drawdown_usd=policy_dd,
        baseline_max_drawdown_usd=baseline_dd,
        policy_capital_productivity=policy_productivity,
        baseline_capital_productivity=baseline_productivity,
        policy_acceptance_rate=policy_acceptance,
        baseline_acceptance_rate=baseline_acceptance,
        policy_selected_outcome_coverage=policy_coverage,
        baseline_selected_outcome_coverage=baseline_coverage,
        candidate_outcome_coverage=candidate_coverage,
        capital_utilization=_ratio(
            policy_capacity_used,
            policy_capacity_total,
        ),
        capital_starvation_rate=_ratio(
            Decimal(starvation_rejections),
            Decimal(candidate_count),
        ),
        mpc_reserve_efficiency=_ratio(
            Decimal(coverable_option_epochs),
            Decimal(considered_option_epochs),
        ),
        optionality_preserved_rate=_ratio(
            Decimal(coverable_option_epochs),
            Decimal(considered_option_epochs),
        ),
        concentration_utilization=_ratio(
            concentration_used_total,
            concentration_limit_total,
        ),
        provider_failure_incidence=_ratio(
            Decimal(provider_failures),
            Decimal(population_slots),
        ),
        evidence_missingness=Decimal(1) - candidate_coverage,
    )


def _decision_payload(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, object]:
    try:
        parsed = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20D canonical decision payload invalid"
        ) from error
    if not isinstance(parsed, dict):
        raise CiboCapitalManagementError(
            "Phase20D canonical decision payload must be object"
        )
    return parsed


def _policy_payload(
    policy: Phase20ForwardPolicyDecisionSeal,
) -> dict[str, object]:
    try:
        parsed = json.loads(policy.canonical_record_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20D canonical policy payload invalid"
        ) from error
    if not isinstance(parsed, dict):
        raise CiboCapitalManagementError(
            "Phase20D canonical policy payload must be object"
        )
    return parsed


def _parse_candidates(
    payload: dict[str, object],
) -> tuple[_ParsedCandidate, ...]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "Phase20D canonical candidates must be list"
        )
    parsed: list[_ParsedCandidate] = []
    for row in raw:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase20D canonical candidate row must be object"
            )
        candidate = row.get("candidate")
        provider = row.get("provider_observation")
        opportunity = row.get("opportunity")
        if not all(
            isinstance(item, dict)
            for item in (candidate, provider, opportunity)
        ):
            raise CiboCapitalManagementError(
                "Phase20D canonical candidate evidence incomplete"
            )
        assert isinstance(candidate, dict)
        assert isinstance(provider, dict)
        assert isinstance(opportunity, dict)
        expectation = candidate.get("expectation")
        if not isinstance(expectation, dict):
            raise CiboCapitalManagementError(
                "Phase20D candidate expectation missing"
            )
        parsed.append(
            _ParsedCandidate(
                signal_fingerprint=str(candidate["signal_fingerprint"]),
                trader_id=str(candidate["trader_id"]),
                stop_risk_usd=_decimal(candidate["stop_risk_usd"]),
                margin_usd=_decimal(candidate["margin_usd"]),
                concentration_group=str(candidate["concentration_group"]),
                concentration_risk_usd=_decimal(
                    candidate["concentration_risk_usd"]
                ),
                expected_capital_minutes=_decimal(
                    expectation["expected_capital_minutes"]
                ),
                provider_cost_proxy_usd=_provider_cost_proxy(
                    provider=provider,
                    opportunity=opportunity,
                ),
            )
        )
    fingerprints = tuple(item.signal_fingerprint for item in parsed)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "Phase20D duplicate candidate fingerprint"
        )
    return tuple(parsed)


def _baseline_selection(
    *,
    payload: dict[str, object],
    candidates: tuple[_ParsedCandidate, ...],
) -> set[str]:
    risk_limit = _decimal(payload["hard_risk_headroom_usd"])
    margin_limit = _decimal(payload["margin_headroom_usd"])
    raw_limits = payload.get("concentration_limit_by_group")
    if not isinstance(raw_limits, list):
        raise CiboCapitalManagementError(
            "Phase20D concentration limits must be list"
        )
    limits: dict[str, Decimal] = {}
    for item in raw_limits:
        if (
            not isinstance(item, list)
            or len(item) != 2
        ):
            raise CiboCapitalManagementError(
                "Phase20D concentration limit row invalid"
            )
        limits[str(item[0])] = _decimal(item[1])

    used_risk = Decimal(0)
    used_margin = Decimal(0)
    used_group: dict[str, Decimal] = {}
    selected: set[str] = set()
    for candidate in candidates:
        group_used = used_group.get(
            candidate.concentration_group,
            Decimal(0),
        )
        group_limit = limits.get(candidate.concentration_group)
        if used_risk + candidate.stop_risk_usd > risk_limit:
            continue
        if used_margin + candidate.margin_usd > margin_limit:
            continue
        if (
            group_limit is not None
            and group_used + candidate.concentration_risk_usd > group_limit
        ):
            continue
        selected.add(candidate.signal_fingerprint)
        used_risk += candidate.stop_risk_usd
        used_margin += candidate.margin_usd
        used_group[candidate.concentration_group] = (
            group_used + candidate.concentration_risk_usd
        )
    return selected


def _provider_cost_proxy(
    *,
    provider: dict[str, object],
    opportunity: dict[str, object],
) -> Decimal:
    minimum_volume = _decimal(provider["minimum_volume"])
    volume_step = _decimal(provider["volume_step"])
    minimum_steps_raw = opportunity.get("minimum_execution_steps", 1)
    if (
        not isinstance(minimum_steps_raw, int)
        or isinstance(minimum_steps_raw, bool)
        or minimum_steps_raw < 1
    ):
        raise CiboCapitalManagementError(
            "Phase20D minimum_execution_steps must be positive int"
        )
    minimum_steps = minimum_steps_raw
    raw_volume = minimum_volume * Decimal(minimum_steps)
    volume_steps = (
        raw_volume / volume_step
    ).to_integral_value(rounding=ROUND_CEILING)
    executable_volume = volume_steps * volume_step
    spread_ticks = (
        _decimal(provider["ask"]) - _decimal(provider["bid"])
    ) / _decimal(provider["tick_size"])
    cost_per_volume = (
        spread_ticks * _decimal(provider["tick_value"])
        + _decimal(provider["commission_per_volume_usd"])
        + _decimal(provider["slippage_reserve_per_volume_usd"])
    )
    return executable_volume * cost_per_volume


def _inspect_policy_safety(
    *,
    payload: dict[str, object],
    policy_record: dict[str, object],
    failures: list[str],
) -> None:
    if not policy_record:
        return
    allocation = policy_record.get("allocator_decision")
    if not isinstance(allocation, dict):
        failures.append("ZERO_CAPITAL_CONSERVATION_BREACHES")
        return
    decision = allocation.get("allocation")
    if decision is None:
        return
    if not isinstance(decision, dict):
        failures.append("ZERO_CAPITAL_CONSERVATION_BREACHES")
        return
    used_risk = _decimal(decision.get("used_stop_risk_usd", "0"))
    used_margin = _decimal(decision.get("used_margin_usd", "0"))
    deployable_risk = _decimal(
        allocation.get("deployable_stop_risk_usd", "0")
    )
    deployable_margin = _decimal(
        allocation.get("deployable_margin_usd", "0")
    )
    if used_risk > deployable_risk or used_margin > deployable_margin:
        failures.append("ZERO_CAPITAL_CONSERVATION_BREACHES")

    limits_raw = payload.get("concentration_limit_by_group", [])
    if not isinstance(limits_raw, list):
        failures.append("ZERO_CONCENTRATION_BREACHES")
        return
    limits = {
        str(item[0]): _decimal(item[1])
        for item in limits_raw
        if isinstance(item, list) and len(item) == 2
    }
    used_raw = decision.get("concentration_used_by_group", [])
    if not isinstance(used_raw, list):
        failures.append("ZERO_CONCENTRATION_BREACHES")
        return
    for item in used_raw:
        if not isinstance(item, list) or len(item) != 2:
            failures.append("ZERO_CONCENTRATION_BREACHES")
            continue
        group = str(item[0])
        used = _decimal(item[1])
        if group in limits and used > limits[group]:
            failures.append("ZERO_CONCENTRATION_BREACHES")


def _policy_operational_metrics(
    *,
    payload: dict[str, object],
    policy_record: dict[str, object],
) -> tuple[Decimal, Decimal, Decimal, Decimal, int, int, int]:
    hard_capacity = _decimal(payload["hard_risk_headroom_usd"])
    concentration_limits = payload.get("concentration_limit_by_group", [])
    if not isinstance(concentration_limits, list):
        raise CiboCapitalManagementError(
            "Phase20D concentration limits must be list"
        )
    concentration_limit_total = sum(
        (
            _decimal(item[1])
            for item in concentration_limits
            if isinstance(item, list) and len(item) == 2
        ),
        Decimal(0),
    )
    if not policy_record:
        return (
            hard_capacity,
            Decimal(0),
            concentration_limit_total,
            Decimal(0),
            0,
            0,
            0,
        )
    allocator = policy_record.get("allocator_decision")
    mpc = policy_record.get("mpc_plan")
    used = Decimal(0)
    concentration_used = Decimal(0)
    starved = 0
    if isinstance(allocator, dict):
        allocation = allocator.get("allocation")
        if isinstance(allocation, dict):
            used = _decimal(allocation.get("used_stop_risk_usd", "0"))
            used_groups = allocation.get(
                "concentration_used_by_group",
                [],
            )
            if isinstance(used_groups, list):
                concentration_used = sum(
                    (
                        _decimal(item[1])
                        for item in used_groups
                        if isinstance(item, list) and len(item) == 2
                    ),
                    Decimal(0),
                )
            rows = allocation.get("rows", [])
            if isinstance(rows, list):
                starved = sum(
                    1
                    for item in rows
                    if isinstance(item, dict)
                    and not bool(item.get("selected"))
                    and any(
                        token in str(item.get("reason", ""))
                        for token in (
                            "headroom",
                            "concentration",
                        )
                    )
                )
    considered = 0
    coverable = 0
    if isinstance(mpc, dict):
        ids = mpc.get("considered_option_ids", [])
        if isinstance(ids, list) and ids:
            considered = 1
            coverable = 1 if bool(mpc.get("horizon_fully_coverable")) else 0
    return (
        hard_capacity,
        used,
        concentration_limit_total,
        concentration_used,
        starved,
        considered,
        coverable,
    )


def _build_folds(
    *,
    rows: tuple[Phase20QualificationRow, ...],
    decisions: tuple[Phase20ForwardDecisionSeal, ...],
    fold_count: int,
) -> tuple[Phase20QualificationFold, ...]:
    if not decisions:
        return ()
    base, remainder = divmod(len(decisions), fold_count)
    result: list[Phase20QualificationFold] = []
    start = 0
    for index in range(fold_count):
        count = base + (1 if index < remainder else 0)
        decision_slice = decisions[start : start + count]
        start += count
        shas = {item.evidence_sha256 for item in decision_slice}
        fold_rows = tuple(
            item
            for item in rows
            if item.decision_evidence_sha256 in shas
        )
        result.append(
            Phase20QualificationFold(
                fold_id=f"WF{index + 1}",
                decision_epoch_count=len(decision_slice),
                candidate_count=len(fold_rows),
                policy_selected_count=sum(
                    1 for item in fold_rows if item.policy_selected
                ),
                baseline_selected_count=sum(
                    1 for item in fold_rows if item.baseline_selected
                ),
                policy_net_delta_usd=sum(
                    (item.policy_net_delta_usd for item in fold_rows),
                    Decimal(0),
                ),
                baseline_net_delta_usd=sum(
                    (item.baseline_net_delta_usd for item in fold_rows),
                    Decimal(0),
                ),
            )
        )
    return tuple(result)


def _max_drawdown(
    events: tuple[tuple[datetime | None, str, Decimal], ...],
) -> Decimal:
    ordered = sorted(
        (
            (observed_at, signal, delta)
            for observed_at, signal, delta in events
            if observed_at is not None
        ),
        key=lambda item: (item[0], item[1]),
    )
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for _, _, delta in ordered:
        equity += delta
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def _coverage_rows(rows: tuple[Phase20QualificationRow, ...]) -> Decimal:
    if not rows:
        return Decimal(1)
    observed = sum(
        1 for item in rows if item.realized_structural_outcome_r is not None
    )
    return Decimal(observed) / Decimal(len(rows))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal(0)
    return numerator / denominator


def _decimal(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise CiboCapitalManagementError(
            "Phase20D canonical decimal must be finite"
        )
    return result
