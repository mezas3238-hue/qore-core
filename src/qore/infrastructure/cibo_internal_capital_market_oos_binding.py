"""Causal evidence binder for GEN-C6 Internal Capital Market shadow.

The binder proves lineage only:

GEN-C6 scarcity decision
-> durable GEN-C4 marginal evidence
-> durable GEN-C5 eligibility seal
-> Phase20 source decision
-> Phase20 source policy
-> terminal reconciled source outcome
-> exact capital deployment/release timing when available

It does not compute hypothetical GEN-C6 compound PnL and does not multiply
historical R by hypothetical capital.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_internal_capital_market_store import (
    VersionedGenc6InternalCapitalMarketBook,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    Genc4MarginalEvidenceSeal,
    VersionedGenc4MarginalEvidenceBook,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    T20CapitalReleaseSeal,
    VersionedT20CapitalReleaseBook,
)


class Genc6OosBindingStatus(StrEnum):
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Genc6BoundCandidateOutcome:
    genc6_decision_id: str
    scarcity_event_id: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    candidate_id: str
    trader_id: str
    signal_fingerprint: str
    c4_evidence_sha256: str
    genc5_decision_sha256: str
    source_decision_sha256: str
    source_policy_sha256: str
    control_selected: bool
    treatment_selected: bool
    requested_marginal_capital_usd: Decimal
    proposed_stop_risk_usd: Decimal
    proposed_margin_usd: Decimal
    expected_capital_minutes: Decimal
    outcome_evidence_id: str
    outcome_observed_at: datetime
    realized_net_pnl_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    realized_structural_outcome_r: Decimal
    actual_capital_minutes: Decimal | None
    t20_release_evidence_sha256: str | None = None
    requested_capital_usd: Decimal | None = None
    risk_authorized_capital_usd: Decimal | None = None
    execution_realized_capital_usd: Decimal | None = None
    returned_capacity_usd: Decimal | None = None
    capital_deployed_at: datetime | None = None
    capital_released_at: datetime | None = None
    partial_release_count: int = 0
    settlement_bound: bool = True
    release_timing_bound: bool = False
    hypothetical_genc6_pnl_computed: bool = False
    economic_utility_claimed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "genc6_decision_id",
            "scarcity_event_id",
            "account_provider_key",
            "account_ref",
            "candidate_id",
            "trader_id",
            "signal_fingerprint",
            "outcome_evidence_id",
        ):
            if not getattr(self, name):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} is required"
                )
        for name in (
            "c4_evidence_sha256",
            "genc5_decision_sha256",
            "source_decision_sha256",
            "source_policy_sha256",
        ):
            _sha(getattr(self, name), name)
        _aware(self.decision_at, "decision_at")
        _aware(self.outcome_observed_at, "outcome_observed_at")
        if self.outcome_observed_at <= self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS outcome must follow decision"
            )
        for name in (
            "requested_marginal_capital_usd",
            "proposed_stop_risk_usd",
            "proposed_margin_usd",
            "expected_capital_minutes",
            "executed_initial_stop_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} must be finite positive"
                )
        for name in (
            "realized_net_pnl_usd",
            "realized_structural_outcome_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} must be finite Decimal"
                )
        if (
            self.realized_net_pnl_usd
            / self.executed_initial_stop_risk_usd
            != self.realized_structural_outcome_r
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS structural R identity drift"
            )
        if self.actual_capital_minutes is not None and (
            not isinstance(self.actual_capital_minutes, Decimal)
            or not self.actual_capital_minutes.is_finite()
            or self.actual_capital_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS actual capital minutes must be positive"
            )
        release_amounts = (
            self.requested_capital_usd,
            self.risk_authorized_capital_usd,
            self.execution_realized_capital_usd,
            self.returned_capacity_usd,
        )
        if any(item is not None for item in release_amounts):
            if any(item is None for item in release_amounts):
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS T20 capital amounts must be complete"
                )
            for item in release_amounts:
                assert item is not None
                if (
                    not isinstance(item, Decimal)
                    or not item.is_finite()
                    or item <= 0
                ):
                    raise CiboCompoundCapitalError(
                        "GEN-C6 OOS T20 capital amounts must be positive"
                    )
            assert self.requested_capital_usd is not None
            assert self.risk_authorized_capital_usd is not None
            assert self.execution_realized_capital_usd is not None
            assert self.returned_capacity_usd is not None
            if (
                self.execution_realized_capital_usd
                > self.risk_authorized_capital_usd
                or self.risk_authorized_capital_usd
                > self.requested_capital_usd
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS T20 request/Risk/Execution ordering drift"
                )
            if self.returned_capacity_usd != self.execution_realized_capital_usd:
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS T20 returned capacity reconciliation drift"
                )
        if (
            not isinstance(self.partial_release_count, int)
            or isinstance(self.partial_release_count, bool)
            or self.partial_release_count < 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS partial_release_count must be non-negative int"
            )
        for name in ("capital_deployed_at", "capital_released_at"):
            value = getattr(self, name)
            if value is not None:
                _aware(value, name)
        for name in (
            "control_selected",
            "treatment_selected",
            "settlement_bound",
            "release_timing_bound",
            "hypothetical_genc6_pnl_computed",
            "economic_utility_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} must be bool"
                )
        if not self.settlement_bound:
            raise CiboCompoundCapitalError(
                "GEN-C6 bound outcome row requires terminal settlement"
            )
        release_payload_present = (
            self.actual_capital_minutes is not None
            or self.t20_release_evidence_sha256 is not None
            or self.requested_capital_usd is not None
            or self.risk_authorized_capital_usd is not None
            or self.execution_realized_capital_usd is not None
            or self.returned_capacity_usd is not None
            or self.capital_deployed_at is not None
            or self.capital_released_at is not None
            or self.partial_release_count != 0
        )
        if self.release_timing_bound != release_payload_present:
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS release-timing flag drift"
            )
        if self.release_timing_bound:
            assert self.t20_release_evidence_sha256 is not None
            _sha(
                self.t20_release_evidence_sha256,
                "t20_release_evidence_sha256",
            )
            if (
                self.capital_deployed_at is None
                or self.capital_released_at is None
                or self.actual_capital_minutes is None
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS T20 release timing must be complete"
                )
            if self.capital_released_at <= self.capital_deployed_at:
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS T20 release must follow deployment"
                )
        if (
            self.hypothetical_genc6_pnl_computed
            or self.economic_utility_claimed
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS binder cannot claim hypothetical PnL/utility"
            )


@dataclass(frozen=True, slots=True)
class Genc6OosBindingReport:
    status: Genc6OosBindingStatus
    decision_count: int
    candidate_count: int
    c4_bound_count: int
    c5_bound_count: int
    source_decision_bound_count: int
    source_policy_bound_count: int
    settlement_bound_count: int
    release_timing_bound_count: int
    missing_outcome_keys: tuple[str, ...]
    missing_release_keys: tuple[str, ...]
    failures: tuple[str, ...]
    rows: tuple[Genc6BoundCandidateOutcome, ...]
    hypothetical_genc6_pnl_computed: bool = False
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc6OosBindingStatus:
            raise CiboCompoundCapitalError(
                "GEN-C6 OOS binding status is invalid"
            )
        for name in (
            "decision_count",
            "candidate_count",
            "c4_bound_count",
            "c5_bound_count",
            "source_decision_bound_count",
            "source_policy_bound_count",
            "settlement_bound_count",
            "release_timing_bound_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} must be non-negative int"
                )
        for values, label in (
            (self.missing_outcome_keys, "missing outcome keys"),
            (self.missing_release_keys, "missing release keys"),
            (self.failures, "failures"),
        ):
            if len(values) != len(set(values)):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {label} must be unique"
                )
        for name in (
            "hypothetical_genc6_pnl_computed",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 OOS {name} must be bool"
                )
            if getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C6 OOS binding cannot claim economic readiness"
                )


def bind_genc6_to_causal_outcomes(
    *,
    genc6_book: VersionedGenc6InternalCapitalMarketBook,
    c4_book: VersionedGenc4MarginalEvidenceBook,
    genc5_seals: tuple[Genc5ShadowDecisionSeal, ...],
    phase20_evidence_book: VersionedPhase20ForwardEvidenceBook,
    phase20_policy_book: VersionedPhase20ForwardPolicyBook,
    settlement_book: VersionedCmaSettlementBook,
    t20_release_book: VersionedT20CapitalReleaseBook | None = None,
) -> Genc6OosBindingReport:
    """Bind GEN-C6 candidates to durable causal source outcomes."""

    if not isinstance(
        genc6_book,
        VersionedGenc6InternalCapitalMarketBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical GEN-C6 book"
        )
    if not isinstance(c4_book, VersionedGenc4MarginalEvidenceBook):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical GEN-C4 book"
        )
    if any(
        not isinstance(item, Genc5ShadowDecisionSeal)
        for item in genc5_seals
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical GEN-C5 seals"
        )
    if len({item.decision_sha256 for item in genc5_seals}) != len(
        genc5_seals
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS GEN-C5 decision SHA must be unique"
        )
    if not isinstance(
        phase20_evidence_book,
        VersionedPhase20ForwardEvidenceBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical Phase20 evidence book"
        )
    if not isinstance(
        phase20_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical Phase20 policy book"
        )

    if not isinstance(settlement_book, VersionedCmaSettlementBook):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical CMA settlement book"
        )
    if (
        t20_release_book is not None
        and not isinstance(t20_release_book, VersionedT20CapitalReleaseBook)
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 OOS requires canonical T20 release book"
        )

    c5_by_sha = {
        item.decision_sha256: item for item in genc5_seals
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in phase20_evidence_book.outcomes
    }

    candidate_count = 0
    c4_bound = 0
    c5_bound = 0
    source_decision_bound = 0
    source_policy_bound = 0
    settlement_bound = 0
    release_bound = 0
    missing_outcomes: list[str] = []
    missing_release: list[str] = []
    failures: list[str] = []
    rows: list[Genc6BoundCandidateOutcome] = []

    for record in genc6_book.records:
        seal = genc6_book.seal_for_decision(record.decision_id)
        if seal is None:
            _add_failure(
                failures,
                f"MISSING_GENC6_SEAL:{record.decision_id}",
            )
            continue
        event = _json_object(seal.event_json, "event")
        decision = _json_object(seal.decision_json, "decision")
        candidates = event.get("candidates")
        if not isinstance(candidates, list):
            _add_failure(
                failures,
                f"INVALID_CANDIDATE_SET:{record.decision_id}",
            )
            continue

        for candidate in candidates:
            candidate_count += 1
            if not isinstance(candidate, dict):
                _add_failure(
                    failures,
                    f"INVALID_CANDIDATE_RECORD:{record.decision_id}",
                )
                continue
            candidate_id = str(candidate.get("candidate_id", ""))
            key = f"{record.decision_id}:{candidate_id}"
            c4_sha = str(candidate.get("marginal_evidence_sha256", ""))
            c5_sha = str(candidate.get("genc5_decision_sha256", ""))
            signal = str(candidate.get("signal_fingerprint", ""))

            c4 = c4_book.seal_for_sha(c4_sha)
            if c4 is None:
                _add_failure(failures, f"MISSING_GENC4_EVIDENCE:{key}")
                continue
            c4_bound += 1
            if c4.signal_fingerprint != signal:
                _add_failure(failures, f"GENC4_SIGNAL_BINDING_DRIFT:{key}")
                continue
            if (
                c4.provider_key != seal.account_provider_key
                or c4.account_ref != seal.account_ref
            ):
                _add_failure(failures, f"GENC4_ACCOUNT_BINDING_DRIFT:{key}")
                continue

            c5 = c5_by_sha.get(c5_sha)
            if c5 is None:
                _add_failure(failures, f"MISSING_GENC5_SEAL:{key}")
                continue
            if (
                c5.marginal_evidence_sha256 != c4.evidence_sha256
                or c5.account_provider_key != c4.provider_key
                or c5.account_ref != c4.account_ref
                or c5.decision_at != c4.decision_at
            ):
                _add_failure(failures, f"GENC5_GENC4_BINDING_DRIFT:{key}")
                continue
            c5_bound += 1

            source_decision = phase20_evidence_book.decision_for_sha(
                c4.source_opportunity_decision_sha256
            )
            if source_decision is None:
                _add_failure(failures, f"MISSING_SOURCE_DECISION:{key}")
                continue
            if signal not in source_decision.signal_fingerprints:
                _add_failure(failures, f"SOURCE_SIGNAL_BINDING_DRIFT:{key}")
                continue
            if source_decision.decision_at != c4.decision_at:
                _add_failure(failures, f"SOURCE_DECISION_TIME_DRIFT:{key}")
                continue
            if not _source_account_matches(
                source_decision.canonical_payload_json,
                provider_key=c4.provider_key,
                account_ref=c4.account_ref,
            ):
                _add_failure(failures, f"SOURCE_ACCOUNT_BINDING_DRIFT:{key}")
                continue
            source_decision_bound += 1

            source_policy = phase20_policy_book.decision_for_evidence(
                c4.source_opportunity_decision_sha256
            )
            if source_policy is None:
                _add_failure(failures, f"MISSING_SOURCE_POLICY:{key}")
                continue
            if (
                source_policy.policy_record_sha256
                != c4.source_baseline_policy_record_sha256
            ):
                _add_failure(failures, f"SOURCE_POLICY_BINDING_DRIFT:{key}")
                continue
            source_policy_bound += 1

            outcome = outcomes.get(
                (
                    c4.source_opportunity_decision_sha256,
                    signal,
                )
            )
            if outcome is None:
                missing_outcomes.append(key)
                continue
            if outcome.observed_at <= seal.decision_at:
                _add_failure(failures, f"OUTCOME_TEMPORAL_CONTAMINATION:{key}")
                continue
            settlement = settlement_book.state_for(
                signal_fingerprint=signal,
                position_id=outcome.position_id,
            )
            if settlement is None:
                _add_failure(failures, f"MISSING_TERMINAL_SETTLEMENT:{key}")
                continue
            if not settlement.position_closed:
                _add_failure(failures, f"SETTLEMENT_NOT_TERMINAL:{key}")
                continue
            settlement_deal_ids = tuple(
                item.deal_id for item in settlement.records
            )
            if settlement_deal_ids != outcome.settlement_deal_ids:
                _add_failure(failures, f"SETTLEMENT_DEAL_BINDING_DRIFT:{key}")
                continue
            if settlement.realized_net_pnl_usd != outcome.realized_net_pnl_usd:
                _add_failure(failures, f"SETTLEMENT_PNL_BINDING_DRIFT:{key}")
                continue
            settlement_bound += 1

            t20_release = (
                None
                if t20_release_book is None
                else t20_release_book.for_signal_position(
                    signal_fingerprint=signal,
                    position_id=outcome.position_id,
                )
            )
            if t20_release is None:
                missing_release.append(key)
            else:
                release = t20_release.evidence
                authorization = release.authorization
                if (
                    authorization.decision_evidence_sha256
                    != c4.source_opportunity_decision_sha256
                    or authorization.signal_fingerprint != signal
                    or authorization.position_id != outcome.position_id
                ):
                    _add_failure(
                        failures,
                        f"T20_AUTHORIZATION_BINDING_DRIFT:{key}",
                    )
                    continue
                if (
                    authorization.execution_evidence_id
                    != outcome.execution_risk_evidence_id
                    or authorization.execution_realized_stop_risk_usd
                    != outcome.executed_initial_stop_risk_usd
                ):
                    _add_failure(
                        failures,
                        f"T20_EXECUTION_BINDING_DRIFT:{key}",
                    )
                    continue
                if (
                    release.source_outcome_evidence_id != outcome.evidence_id
                    or release.settlement_deal_ids != settlement_deal_ids
                    or release.terminal_settlement_pnl_usd
                    != settlement.realized_net_pnl_usd
                ):
                    _add_failure(
                        failures,
                        f"T20_SETTLEMENT_BINDING_DRIFT:{key}",
                    )
                    continue
                if release.inferred_from_position_close_only:
                    _add_failure(
                        failures,
                        f"T20_RELEASE_INFERRED_FROM_CLOSE:{key}",
                    )
                    continue
                release_bound += 1

            rows.append(
                _row(
                    seal=seal,
                    decision=decision,
                    candidate=candidate,
                    c4=c4,
                    c5=c5,
                    outcome=outcome,
                    t20_release=t20_release,
                )
            )

    status = _status(
        decision_count=len(genc6_book.records),
        candidate_count=candidate_count,
        settlement_bound=settlement_bound,
        release_bound=release_bound,
        failures=tuple(failures),
    )
    return Genc6OosBindingReport(
        status=status,
        decision_count=len(genc6_book.records),
        candidate_count=candidate_count,
        c4_bound_count=c4_bound,
        c5_bound_count=c5_bound,
        source_decision_bound_count=source_decision_bound,
        source_policy_bound_count=source_policy_bound,
        settlement_bound_count=settlement_bound,
        release_timing_bound_count=release_bound,
        missing_outcome_keys=tuple(missing_outcomes),
        missing_release_keys=tuple(missing_release),
        failures=tuple(failures),
        rows=tuple(rows),
        hypothetical_genc6_pnl_computed=False,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _row(
    *,
    seal: object,
    decision: dict[str, object],
    candidate: dict[str, object],
    c4: Genc4MarginalEvidenceSeal,
    c5: Genc5ShadowDecisionSeal,
    outcome: Phase20ForwardOutcomeSeal,
    t20_release: T20CapitalReleaseSeal | None,
) -> Genc6BoundCandidateOutcome:
    decision_id = str(decision["decision_id"])
    candidate_id = str(candidate["candidate_id"])
    control_selected = (
        decision.get("control_candidate_id") == candidate_id
    )
    treatment_selected = (
        decision.get("treatment_candidate_id") == candidate_id
    )
    return Genc6BoundCandidateOutcome(
        genc6_decision_id=decision_id,
        scarcity_event_id=str(decision["scarcity_event_id"]),
        decision_at=seal.decision_at,
        account_provider_key=seal.account_provider_key,
        account_ref=seal.account_ref,
        candidate_id=candidate_id,
        trader_id=c4.trader_id,
        signal_fingerprint=c4.signal_fingerprint,
        c4_evidence_sha256=c4.evidence_sha256,
        genc5_decision_sha256=c5.decision_sha256,
        source_decision_sha256=(
            c4.source_opportunity_decision_sha256
        ),
        source_policy_sha256=(
            c4.source_baseline_policy_record_sha256
        ),
        control_selected=control_selected,
        treatment_selected=treatment_selected,
        requested_marginal_capital_usd=(
            c4.requested_incremental_capital_usd
        ),
        proposed_stop_risk_usd=c4.incremental_stop_risk_usd,
        proposed_margin_usd=c4.incremental_margin_usd,
        expected_capital_minutes=c4.expected_capital_minutes,
        outcome_evidence_id=outcome.evidence_id,
        outcome_observed_at=outcome.observed_at,
        realized_net_pnl_usd=outcome.realized_net_pnl_usd,
        executed_initial_stop_risk_usd=(
            outcome.executed_initial_stop_risk_usd
        ),
        realized_structural_outcome_r=(
            outcome.realized_structural_outcome_r
        ),
        actual_capital_minutes=(
            None
            if t20_release is None
            else t20_release.evidence.release_latency_minutes
        ),
        t20_release_evidence_sha256=(
            None
            if t20_release is None
            else t20_release.evidence_sha256
        ),
        requested_capital_usd=(
            None
            if t20_release is None
            else t20_release.evidence.authorization.requested_capital_usd
        ),
        risk_authorized_capital_usd=(
            None
            if t20_release is None
            else (
                t20_release.evidence.authorization
                .risk_authorized_capital_usd
            )
        ),
        execution_realized_capital_usd=(
            None
            if t20_release is None
            else (
                t20_release.evidence.authorization
                .execution_realized_capital_usd
            )
        ),
        returned_capacity_usd=(
            None
            if t20_release is None
            else t20_release.evidence.total_returned_capacity_usd
        ),
        capital_deployed_at=(
            None
            if t20_release is None
            else t20_release.evidence.authorization.capital_deployed_at
        ),
        capital_released_at=(
            None
            if t20_release is None
            else t20_release.evidence.terminal_release_at
        ),
        partial_release_count=(
            0
            if t20_release is None
            else sum(
                1
                for item in t20_release.evidence.releases
                if not item.terminal
            )
        ),
        settlement_bound=True,
        release_timing_bound=t20_release is not None,
        hypothetical_genc6_pnl_computed=False,
        economic_utility_claimed=False,
    )


def _source_account_matches(
    canonical_payload_json: str,
    *,
    provider_key: str,
    account_ref: str,
) -> bool:
    payload = _json_object(canonical_payload_json, "source decision")
    account = payload.get("account_identity")
    return (
        isinstance(account, dict)
        and account.get("provider_key") == provider_key
        and account.get("account_ref") == account_ref
    )


def _status(
    *,
    decision_count: int,
    candidate_count: int,
    settlement_bound: int,
    release_bound: int,
    failures: tuple[str, ...],
) -> Genc6OosBindingStatus:
    if failures:
        return Genc6OosBindingStatus.INVALID
    if decision_count == 0:
        return Genc6OosBindingStatus.EMPTY
    if (
        candidate_count > 0
        and settlement_bound == candidate_count
        and release_bound == candidate_count
    ):
        return Genc6OosBindingStatus.COMPLETE
    return Genc6OosBindingStatus.PARTIAL


def _json_object(value: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            f"GEN-C6 OOS {label} JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            f"GEN-C6 OOS {label} payload must be object"
        )
    return payload


def _add_failure(failures: list[str], value: str) -> None:
    if value not in failures:
        failures.append(value)


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 OOS {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 OOS {name} must be timezone-aware"
        )
