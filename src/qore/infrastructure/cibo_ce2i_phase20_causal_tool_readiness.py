"""Forward causal-evidence readiness for unresolved CE2I tools.

This module never promotes a tool or inspects the sealed 2017H1 holdout. It
measures whether the already-frozen Phase20D forward stream contains enough
causal, pre-decision evidence to evaluate unresolved T08/T09/T12/T13/T14/T15/T18
without silently relabeling contract proofs as empirical calibration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19l_competition import (
    MINIMUM_ROBUST_COMPETITION_EPOCHS,
)
from qore.infrastructure.cibo_ce2i_phase20_causal_history_state import (
    build_phase20_causal_history_state,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_readiness import (
    Phase20QualificationReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_reserve_population import (
    Phase20T13ReservePopulationAudit,
)
from qore.infrastructure.cibo_ce2i_phase20_t14_path_readiness import (
    Phase20T14PathReadiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t15_option_realization import (
    Phase20T15OptionRealization,
)


class Phase20ToolEvidenceState(StrEnum):
    STREAM_BLOCKED = "STREAM_BLOCKED"
    COLLECTING_FORWARD = "COLLECTING_FORWARD"
    FORWARD_POPULATION_READY = "FORWARD_POPULATION_READY"
    REQUIRES_DIFFERENT_EVIDENCE = "REQUIRES_DIFFERENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class Phase20ToolEvidenceReadiness:
    tool_code: str
    state: Phase20ToolEvidenceState
    stream_bound: bool
    forward_population_ready: bool
    observed_epochs: int
    qualifying_epochs: int
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.tool_code not in {
            "T08",
            "T09",
            "T12",
            "T13",
            "T14",
            "T15",
            "T18",
        }:
            raise CiboCapitalManagementError(
                "Phase20 causal readiness tool is outside unresolved causal set"
            )
        if type(self.state) is not Phase20ToolEvidenceState:
            raise CiboCapitalManagementError(
                "Phase20 causal readiness state is invalid"
            )
        for name in ("stream_bound", "forward_population_ready"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 causal readiness {name} must be bool"
                )
        for name in ("observed_epochs", "qualifying_epochs"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 causal readiness {name} must be non-negative int"
                )
        if self.qualifying_epochs > self.observed_epochs:
            raise CiboCapitalManagementError(
                "Phase20 qualifying epochs cannot exceed observed epochs"
            )
        if self.forward_population_ready and (
            not self.stream_bound
            or self.state is not Phase20ToolEvidenceState.FORWARD_POPULATION_READY
        ):
            raise CiboCapitalManagementError(
                "Phase20 ready population requires bound stream/ready state"
            )
        if (
            self.state is Phase20ToolEvidenceState.FORWARD_POPULATION_READY
            and self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 ready tool population cannot retain blockers"
            )
        if (
            self.state is not Phase20ToolEvidenceState.FORWARD_POPULATION_READY
            and not self.blockers
        ):
            raise CiboCapitalManagementError(
                "Phase20 non-ready tool population must name blockers"
            )


@dataclass(frozen=True, slots=True)
class Phase20CausalToolReadinessReport:
    global_forward_ready: bool
    global_forward_blockers: tuple[str, ...]
    decision_epochs: int
    usable_forward_epochs: int
    candidate_epochs: int
    exact_competition_epochs: int
    scarce_competition_epochs: int
    valid_regime_epochs: int
    portfolio_netting_epochs: int
    known_option_epochs: int
    causal_history_epochs: int
    tools: tuple[Phase20ToolEvidenceReadiness, ...]

    def __post_init__(self) -> None:
        expected = ("T08", "T09", "T12", "T13", "T14", "T15", "T18")
        if tuple(item.tool_code for item in self.tools) != expected:
            raise CiboCapitalManagementError(
                "Phase20 causal readiness must cover unresolved tools in order"
            )
        if self.global_forward_ready != (not self.global_forward_blockers):
            raise CiboCapitalManagementError(
                "Phase20 global readiness/blocker mismatch"
            )
        for name in (
            "decision_epochs",
            "usable_forward_epochs",
            "candidate_epochs",
            "exact_competition_epochs",
            "scarce_competition_epochs",
            "valid_regime_epochs",
            "portfolio_netting_epochs",
            "known_option_epochs",
            "causal_history_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 causal readiness {name} must be non-negative int"
                )
        if self.usable_forward_epochs > self.decision_epochs:
            raise CiboCapitalManagementError(
                "Phase20 usable epochs cannot exceed decision epochs"
            )
        if self.exact_competition_epochs > self.candidate_epochs:
            raise CiboCapitalManagementError(
                "Phase20 exact competition cannot exceed candidate epochs"
            )
        if self.scarce_competition_epochs > self.exact_competition_epochs:
            raise CiboCapitalManagementError(
                "Phase20 scarce competition cannot exceed exact competition"
            )


def assess_phase20_causal_tool_readiness(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    qualification_readiness: Phase20QualificationReadiness,
    t08_oos_ablation: T08NettingOosAblationReport | None = None,
    t13_reserve_population: Phase20T13ReservePopulationAudit | None = None,
    t14_path_readiness: Phase20T14PathReadiness | None = None,
    t15_option_realization: Phase20T15OptionRealization | None = None,
) -> Phase20CausalToolReadinessReport:
    """Measure tool-specific causal evidence without granting calibration."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness requires canonical evidence book"
        )
    if not isinstance(qualification_readiness, Phase20QualificationReadiness):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness requires canonical qualification readiness"
        )
    if (
        t08_oos_ablation is not None
        and not isinstance(t08_oos_ablation, T08NettingOosAblationReport)
    ):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness T08 OOS ablation is invalid"
        )
    if (
        t13_reserve_population is not None
        and not isinstance(
            t13_reserve_population,
            Phase20T13ReservePopulationAudit,
        )
    ):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness T13 reserve population is invalid"
        )
    if (
        t14_path_readiness is not None
        and not isinstance(t14_path_readiness, Phase20T14PathReadiness)
    ):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness T14 path evidence is invalid"
        )
    if (
        t15_option_realization is not None
        and not isinstance(t15_option_realization, Phase20T15OptionRealization)
    ):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness T15 option evidence is invalid"
        )

    usable: list[tuple[Phase20ForwardDecisionSeal, dict[str, Any]]] = []
    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        if not _usable_forward_decision(decision):
            continue
        usable.append((decision, _decision_payload(decision)))

    candidate_epochs = 0
    exact_competition_epochs = 0
    scarce_competition_epochs = 0
    valid_regime_epochs = 0
    portfolio_netting_epochs = 0
    known_option_epochs = 0
    causal_history_epochs = 0

    for decision, payload in usable:
        candidates = _candidates(payload)
        if candidates:
            candidate_epochs += 1
        if len(candidates) >= 2:
            exact_competition_epochs += 1
            if _is_scarce_competition(payload, candidates):
                scarce_competition_epochs += 1
        if _valid_regime(payload):
            valid_regime_epochs += 1
        if candidates and _portfolio_netting_bound(payload):
            portfolio_netting_epochs += 1
        if _known_options_present(payload):
            known_option_epochs += 1
        if candidates:
            history = build_phase20_causal_history_state(
                evidence_book=evidence_book,
                decision=decision,
            )
            if (
                history.prior_settled_outcomes > 0
                and history.observed_candidate_arrivals_per_day is not None
            ):
                causal_history_epochs += 1

    total_usable = len(usable)
    global_ready = qualification_readiness.ready
    global_blockers = tuple(qualification_readiness.reasons)

    if t08_oos_ablation is None:
        t08_stream = (
            candidate_epochs > 0
            and portfolio_netting_epochs == candidate_epochs
        )
        t08_ready = t08_stream and global_ready
        t08_observed = candidate_epochs
        t08_qualifying = portfolio_netting_epochs
        t08_blockers: list[str] = []
        if candidate_epochs == 0:
            t08_blockers.append("NO_FORWARD_CANDIDATE_EPOCHS")
        elif portfolio_netting_epochs != candidate_epochs:
            t08_blockers.append(
                "PORTFOLIO_NETTING_EVIDENCE_COVERAGE_INCOMPLETE"
            )
        if not global_ready:
            t08_blockers.append("GLOBAL_PHASE20D_POPULATION_NOT_READY")
    else:
        t08_stream = (
            t08_oos_ablation.mapping_evidence_bound
            and t08_oos_ablation.correlation_evidence_bound
        )
        t08_ready = (
            t08_stream
            and global_ready
            and t08_oos_ablation.fresh_oos_utility_demonstrated
        )
        t08_observed = t08_oos_ablation.sample_size
        t08_qualifying = (
            t08_oos_ablation.sample_size
            if t08_oos_ablation.fresh_oos_utility_demonstrated
            else 0
        )
        t08_blockers = []
        if not t08_stream:
            t08_blockers.append(
                "T08_OOS_MAPPING_OR_CORRELATION_EVIDENCE_NOT_BOUND"
            )
        if not t08_oos_ablation.fresh_oos_utility_demonstrated:
            t08_blockers.append(
                "FRESH_OOS_NETTING_UTILITY_NOT_DEMONSTRATED"
            )
        if not global_ready:
            t08_blockers.append("GLOBAL_PHASE20D_POPULATION_NOT_READY")

    competition_stream = total_usable > 0
    competition_ready = (
        competition_stream
        and global_ready
        and scarce_competition_epochs >= MINIMUM_ROBUST_COMPETITION_EPOCHS
    )
    competition_blockers: list[str] = []
    if total_usable == 0:
        competition_blockers.append("NO_USABLE_FORWARD_DECISION_EPOCHS")
    if scarce_competition_epochs < MINIMUM_ROBUST_COMPETITION_EPOCHS:
        competition_blockers.append(
            "FRESH_FORWARD_EXACT_SCARCE_COMPETITION_EPOCHS_"
            f"{scarce_competition_epochs}_OF_"
            f"{MINIMUM_ROBUST_COMPETITION_EPOCHS}"
        )
    if not global_ready:
        competition_blockers.append("GLOBAL_PHASE20D_POPULATION_NOT_READY")

    t12_stream = total_usable > 0 and valid_regime_epochs == total_usable
    t12_ready = t12_stream and global_ready
    t12_blockers: list[str] = []
    if total_usable == 0:
        t12_blockers.append("NO_USABLE_FORWARD_DECISION_EPOCHS")
    elif valid_regime_epochs != total_usable:
        t12_blockers.append(
            "CAUSAL_REGIME_STATE_COVERAGE_INCOMPLETE"
        )
    if not global_ready:
        t12_blockers.append("GLOBAL_PHASE20D_POPULATION_NOT_READY")

    if t13_reserve_population is None:
        t13_stream = causal_history_epochs > 0
        t13_observed = candidate_epochs
        t13_qualifying = causal_history_epochs
        t13_blockers: list[str] = []
        if not t13_stream:
            t13_blockers.append("NO_RECONSTRUCTIBLE_CAUSAL_HISTORY_EPOCHS")
        t13_blockers.append(
            "FRESH_OOS_DRAWDOWN_RESERVE_UTILITY_ANALYSIS_REQUIRED"
        )
    else:
        t13_stream = t13_reserve_population.settled_history_epochs > 0
        t13_observed = t13_reserve_population.usable_decision_epochs
        t13_qualifying = (
            t13_reserve_population.pressure_and_scarcity_epochs
        )
        t13_blockers = list(t13_reserve_population.blockers)

    t15_stream = total_usable > 0 and all(
        "known_options" in payload for _decision, payload in usable
    )
    t15_blockers: list[str] = []
    if not t15_stream:
        t15_blockers.append("KNOWN_OPTION_STREAM_NOT_BOUND")
    if known_option_epochs == 0:
        t15_blockers.append("NO_FORWARD_KNOWN_OPTION_EPOCHS")
    t15_blockers.append("FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED")

    rows = (
        _row(
            "T08",
            stream_bound=t08_stream,
            ready=t08_ready,
            observed=t08_observed,
            qualifying=t08_qualifying,
            blockers=t08_blockers,
        ),
        _row(
            "T09",
            stream_bound=competition_stream,
            ready=competition_ready,
            observed=exact_competition_epochs,
            qualifying=scarce_competition_epochs,
            blockers=competition_blockers,
        ),
        _row(
            "T12",
            stream_bound=t12_stream,
            ready=t12_ready,
            observed=total_usable,
            qualifying=valid_regime_epochs,
            blockers=t12_blockers,
        ),
        Phase20ToolEvidenceReadiness(
            tool_code="T13",
            state=(
                Phase20ToolEvidenceState.COLLECTING_FORWARD
                if t13_stream
                else Phase20ToolEvidenceState.STREAM_BLOCKED
            ),
            stream_bound=t13_stream,
            forward_population_ready=False,
            observed_epochs=t13_observed,
            qualifying_epochs=t13_qualifying,
            blockers=tuple(t13_blockers),
        ),
        _t14_row(
            total_usable=total_usable,
            readiness=t14_path_readiness,
        ),
        _t15_row(
            total_usable=total_usable,
            fallback_stream=t15_stream,
            fallback_known_option_epochs=known_option_epochs,
            fallback_blockers=tuple(t15_blockers),
            realization=t15_option_realization,
        ),
        _row(
            "T18",
            stream_bound=competition_stream,
            ready=competition_ready,
            observed=exact_competition_epochs,
            qualifying=scarce_competition_epochs,
            blockers=competition_blockers,
        ),
    )
    return Phase20CausalToolReadinessReport(
        global_forward_ready=global_ready,
        global_forward_blockers=global_blockers,
        decision_epochs=len(evidence_book.decisions),
        usable_forward_epochs=total_usable,
        candidate_epochs=candidate_epochs,
        exact_competition_epochs=exact_competition_epochs,
        scarce_competition_epochs=scarce_competition_epochs,
        valid_regime_epochs=valid_regime_epochs,
        portfolio_netting_epochs=portfolio_netting_epochs,
        known_option_epochs=known_option_epochs,
        causal_history_epochs=causal_history_epochs,
        tools=rows,
    )


def _t15_row(
    *,
    total_usable: int,
    fallback_stream: bool,
    fallback_known_option_epochs: int,
    fallback_blockers: tuple[str, ...],
    realization: Phase20T15OptionRealization | None,
) -> Phase20ToolEvidenceReadiness:
    if realization is None:
        return Phase20ToolEvidenceReadiness(
            tool_code="T15",
            state=(
                Phase20ToolEvidenceState.COLLECTING_FORWARD
                if fallback_stream
                else Phase20ToolEvidenceState.STREAM_BLOCKED
            ),
            stream_bound=fallback_stream,
            forward_population_ready=False,
            observed_epochs=total_usable,
            qualifying_epochs=fallback_known_option_epochs,
            blockers=fallback_blockers,
        )
    blockers = tuple(
        dict.fromkeys(
            realization.blockers
            + ("FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED",)
        )
    )
    return Phase20ToolEvidenceReadiness(
        tool_code="T15",
        state=(
            Phase20ToolEvidenceState.COLLECTING_FORWARD
            if realization.stream_bound
            else Phase20ToolEvidenceState.STREAM_BLOCKED
        ),
        stream_bound=realization.stream_bound,
        forward_population_ready=False,
        observed_epochs=realization.matured_option_instances,
        qualifying_epochs=realization.materialized_candidate_instances,
        blockers=blockers,
    )


def _t14_row(
    *,
    total_usable: int,
    readiness: Phase20T14PathReadiness | None,
) -> Phase20ToolEvidenceReadiness:
    if readiness is None:
        return Phase20ToolEvidenceReadiness(
            tool_code="T14",
            state=Phase20ToolEvidenceState.REQUIRES_DIFFERENT_EVIDENCE,
            stream_bound=False,
            forward_population_ready=False,
            observed_epochs=total_usable,
            qualifying_epochs=0,
            blockers=(
                "POST_ENTRY_POSITION_PATH_EVENT_STREAM_REQUIRED",
                "DECISION_EPOCH_BOOK_CANNOT_PROVE_DYNAMIC_DERISK_UTILITY",
            ),
        )

    blockers = list(readiness.blockers)
    blockers.append("FRESH_OOS_DYNAMIC_DERISK_UTILITY_ANALYSIS_REQUIRED")
    return Phase20ToolEvidenceReadiness(
        tool_code="T14",
        state=(
            Phase20ToolEvidenceState.COLLECTING_FORWARD
            if readiness.stream_bound
            else Phase20ToolEvidenceState.REQUIRES_DIFFERENT_EVIDENCE
        ),
        stream_bound=readiness.stream_bound,
        forward_population_ready=False,
        observed_epochs=readiness.path_positions,
        qualifying_epochs=readiness.qualifying_intervention_positions,
        blockers=tuple(blockers),
    )


def _row(
    code: str,
    *,
    stream_bound: bool,
    ready: bool,
    observed: int,
    qualifying: int,
    blockers: list[str],
) -> Phase20ToolEvidenceReadiness:
    if ready:
        return Phase20ToolEvidenceReadiness(
            tool_code=code,
            state=Phase20ToolEvidenceState.FORWARD_POPULATION_READY,
            stream_bound=True,
            forward_population_ready=True,
            observed_epochs=observed,
            qualifying_epochs=qualifying,
            blockers=(),
        )
    return Phase20ToolEvidenceReadiness(
        tool_code=code,
        state=(
            Phase20ToolEvidenceState.COLLECTING_FORWARD
            if stream_bound
            else Phase20ToolEvidenceState.STREAM_BLOCKED
        ),
        stream_bound=stream_bound,
        forward_population_ready=False,
        observed_epochs=observed,
        qualifying_epochs=qualifying,
        blockers=tuple(blockers),
    )


def _usable_forward_decision(decision: Phase20ForwardDecisionSeal) -> bool:
    if decision.sealed_at is None:
        return False
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return False
    if decision.decision_at < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at:
        return False
    payload = _decision_payload(decision)
    return payload.get("evidence_kind") == "FORWARD_OBSERVED"


def _decision_payload(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, Any]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 causal readiness decision payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness decision payload must be object"
        )
    return payload


def _candidates(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness candidates must be list"
        )
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise CiboCapitalManagementError(
                "Phase20 causal readiness candidate evidence must be object"
            )
        candidate = item.get("candidate")
        if not isinstance(candidate, dict):
            raise CiboCapitalManagementError(
                "Phase20 causal readiness candidate payload must be object"
            )
        result.append(candidate)
    return tuple(result)


def _is_scarce_competition(
    payload: dict[str, Any],
    candidates: tuple[dict[str, Any], ...],
) -> bool:
    risk_headroom = _decimal(payload.get("hard_risk_headroom_usd"))
    margin_headroom = _decimal(payload.get("margin_headroom_usd"))
    total_risk = sum(
        (_decimal(item.get("stop_risk_usd")) for item in candidates),
        Decimal(0),
    )
    total_margin = sum(
        (_decimal(item.get("margin_usd")) for item in candidates),
        Decimal(0),
    )
    if total_risk > risk_headroom or total_margin > margin_headroom:
        return True

    limits_raw = payload.get("concentration_limit_by_group")
    if not isinstance(limits_raw, list):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness concentration limits must be list"
        )
    limits: dict[str, Decimal] = {}
    for item in limits_raw:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
        ):
            raise CiboCapitalManagementError(
                "Phase20 causal readiness concentration limit row is invalid"
            )
        limits[item[0]] = _decimal(item[1])

    used: dict[str, Decimal] = {}
    for candidate in candidates:
        group = candidate.get("concentration_group")
        if not isinstance(group, str) or not group:
            raise CiboCapitalManagementError(
                "Phase20 causal readiness candidate concentration group invalid"
            )
        used[group] = used.get(group, Decimal(0)) + _decimal(
            candidate.get("concentration_risk_usd")
        )
    return any(
        group in limits and amount > limits[group]
        for group, amount in used.items()
    )


def _valid_regime(payload: dict[str, Any]) -> bool:
    regime = payload.get("regime_state")
    if not isinstance(regime, dict):
        return False
    return (
        regime.get("evidence_stale") is False
        and regime.get("provider_condition") != "UNAVAILABLE"
    )


def _portfolio_netting_bound(payload: dict[str, Any]) -> bool:
    advanced = payload.get("advanced_evidence")
    if not isinstance(advanced, dict):
        return False
    netting = advanced.get("portfolio_netting")
    if not isinstance(netting, dict):
        return False
    exposures = netting.get("exposures")
    return (
        netting.get("factor_map_verified") is True
        and netting.get("correlation_stable") is True
        and isinstance(exposures, list)
        and bool(exposures)
    )


def _known_options_present(payload: dict[str, Any]) -> bool:
    known = payload.get("known_options")
    if not isinstance(known, list):
        raise CiboCapitalManagementError(
            "Phase20 causal readiness known_options must be list"
        )
    return bool(known)


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            "Phase20 causal readiness monetary field is invalid"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            "Phase20 causal readiness monetary field must be finite non-negative"
        )
    return result
