"""Causal outcome binding for the GEN-C5 sequential compounding shadow.

This module joins four already-durable evidence layers:

GEN-C5 shadow decision
-> GEN-C4 marginal-capital evidence
-> Phase20 forward decision + sealed baseline policy
-> Phase20 terminal reconciled outcome

It does not estimate compound PnL, scale historical PnL to a new size, claim
economic utility or grant runtime authority. Its only job is to prove that a
future OOS evaluator has an exact causal lineage before any counterfactual or
economic analysis is attempted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    Genc4MarginalEvidenceSeal,
    VersionedGenc4MarginalEvidenceBook,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    Genc5ShadowDecisionSeal,
    VersionedGenc5ShadowBook,
)


class Genc5OutcomeBindingStatus(StrEnum):
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Genc5BoundOutcomeRow:
    decision_id: str
    decision_sha256: str
    decision_at: datetime
    c4_evidence_sha256: str
    source_opportunity_decision_sha256: str
    source_baseline_policy_record_sha256: str
    trader_id: str
    signal_fingerprint: str
    treatment_differs_from_control: bool
    treatment_requested_risk_review_usd: Decimal
    proposed_incremental_stop_risk_usd: Decimal
    proposed_incremental_margin_usd: Decimal
    expected_capital_minutes: Decimal
    outcome_evidence_id: str
    outcome_observed_at: datetime
    realized_net_pnl_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    realized_structural_outcome_r: Decimal
    observed_capital_minutes: Decimal | None
    counterfactual_compound_pnl_computed: bool = False
    economic_utility_claimed: bool = False

    def __post_init__(self) -> None:
        if not self.decision_id or not self.trader_id:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS bound decision/Trader identity is required"
            )
        if not self.signal_fingerprint or not self.outcome_evidence_id:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS bound signal/outcome identity is required"
            )
        for name in (
            "decision_sha256",
            "c4_evidence_sha256",
            "source_opportunity_decision_sha256",
            "source_baseline_policy_record_sha256",
        ):
            _require_sha(getattr(self, name), name)
        _aware(self.decision_at, "decision_at")
        _aware(self.outcome_observed_at, "outcome_observed_at")
        if self.outcome_observed_at <= self.decision_at:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS outcome must follow shadow decision"
            )
        for name in (
            "treatment_requested_risk_review_usd",
            "proposed_incremental_stop_risk_usd",
            "proposed_incremental_margin_usd",
            "expected_capital_minutes",
            "executed_initial_stop_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 OOS {name} must be finite non-negative"
                )
        if self.proposed_incremental_stop_risk_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS proposed stop risk must be positive"
            )
        if self.expected_capital_minutes <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS expected duration must be positive"
            )
        if self.executed_initial_stop_risk_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS executed risk must be positive"
            )
        for name in (
            "realized_net_pnl_usd",
            "realized_structural_outcome_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"GEN-C5 OOS {name} must be finite Decimal"
                )
        if (
            self.realized_net_pnl_usd
            / self.executed_initial_stop_risk_usd
            != self.realized_structural_outcome_r
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS structural R identity drift"
            )
        if self.observed_capital_minutes is not None and (
            not isinstance(self.observed_capital_minutes, Decimal)
            or not self.observed_capital_minutes.is_finite()
            or self.observed_capital_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS observed duration must be finite positive"
            )
        for name in (
            "treatment_differs_from_control",
            "counterfactual_compound_pnl_computed",
            "economic_utility_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C5 OOS {name} must be bool"
                )
        if self.treatment_differs_from_control:
            if self.treatment_requested_risk_review_usd <= 0:
                raise CiboCompoundCapitalError(
                    "GEN-C5 OOS treatment difference requires positive request"
                )
        elif self.treatment_requested_risk_review_usd != 0:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS non-different treatment must request zero"
            )
        if (
            self.counterfactual_compound_pnl_computed
            or self.economic_utility_claimed
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS binding cannot claim counterfactual PnL/utility"
            )


@dataclass(frozen=True, slots=True)
class Genc5OutcomeBindingReport:
    status: Genc5OutcomeBindingStatus
    shadow_decision_count: int
    treatment_divergent_count: int
    c4_bound_count: int
    source_decision_bound_count: int
    source_policy_bound_count: int
    terminal_outcome_bound_count: int
    treatment_divergent_outcome_count: int
    missing_outcome_decision_ids: tuple[str, ...]
    failures: tuple[str, ...]
    rows: tuple[Genc5BoundOutcomeRow, ...]
    counterfactual_compound_pnl_computed: bool = False
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc5OutcomeBindingStatus:
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS binding status is invalid"
            )
        for name in (
            "shadow_decision_count",
            "treatment_divergent_count",
            "c4_bound_count",
            "source_decision_bound_count",
            "source_policy_bound_count",
            "terminal_outcome_bound_count",
            "treatment_divergent_outcome_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 OOS {name} must be non-negative int"
                )
        if len(self.missing_outcome_decision_ids) != len(
            set(self.missing_outcome_decision_ids)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS missing-outcome ids must be unique"
            )
        if len(self.failures) != len(set(self.failures)):
            raise CiboCompoundCapitalError(
                "GEN-C5 OOS failures must be unique"
            )
        for name in (
            "counterfactual_compound_pnl_computed",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C5 OOS {name} must be bool"
                )
            if getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C5 OOS binding cannot claim economic readiness"
                )


def bind_genc5_shadow_to_phase20_outcomes(
    *,
    c4_book: VersionedGenc4MarginalEvidenceBook,
    c5_book: VersionedGenc5ShadowBook,
    phase20_evidence_book: VersionedPhase20ForwardEvidenceBook,
    phase20_policy_book: VersionedPhase20ForwardPolicyBook,
) -> Genc5OutcomeBindingReport:
    """Bind durable GEN-C5 shadows to canonical Phase20 outcomes."""

    if not isinstance(c4_book, VersionedGenc4MarginalEvidenceBook):
        raise CiboCompoundCapitalError(
            "GEN-C5 OOS binding requires canonical GEN-C4 book"
        )
    if not isinstance(c5_book, VersionedGenc5ShadowBook):
        raise CiboCompoundCapitalError(
            "GEN-C5 OOS binding requires canonical GEN-C5 book"
        )
    if not isinstance(
        phase20_evidence_book,
        VersionedPhase20ForwardEvidenceBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C5 OOS binding requires canonical Phase20 evidence book"
        )
    if not isinstance(
        phase20_policy_book,
        VersionedPhase20ForwardPolicyBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C5 OOS binding requires canonical Phase20 policy book"
        )

    outcome_by_key = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in phase20_evidence_book.outcomes
    }

    failures: list[str] = []
    missing_outcomes: list[str] = []
    rows: list[Genc5BoundOutcomeRow] = []
    c4_bound = 0
    source_decision_bound = 0
    source_policy_bound = 0
    divergent = 0
    divergent_outcomes = 0

    for record in c5_book.records:
        c5 = c5_book.seal_for_decision(record.decision_id)
        if c5 is None:
            _add_failure(
                failures,
                f"MISSING_GENC5_SEAL:{record.decision_id}",
            )
            continue
        if c5.treatment_differs_from_control:
            divergent += 1

        c4 = c4_book.seal_for_sha(c5.marginal_evidence_sha256)
        if c4 is None:
            _add_failure(
                failures,
                f"MISSING_GENC4_EVIDENCE:{c5.decision_id}",
            )
            continue
        c4_bound += 1
        if not _c4_c5_binding_valid(c4=c4, c5=c5):
            _add_failure(
                failures,
                f"GENC4_GENC5_BINDING_DRIFT:{c5.decision_id}",
            )
            continue

        source_decision = phase20_evidence_book.decision_for_sha(
            c4.source_opportunity_decision_sha256
        )
        if source_decision is None:
            _add_failure(
                failures,
                f"MISSING_SOURCE_DECISION:{c5.decision_id}",
            )
            continue
        if c4.signal_fingerprint not in source_decision.signal_fingerprints:
            _add_failure(
                failures,
                f"SOURCE_SIGNAL_BINDING_DRIFT:{c5.decision_id}",
            )
            continue
        if not _source_account_matches(
            source_decision.canonical_payload_json,
            provider_key=c4.provider_key,
            account_ref=c4.account_ref,
        ):
            _add_failure(
                failures,
                f"SOURCE_ACCOUNT_BINDING_DRIFT:{c5.decision_id}",
            )
            continue
        source_decision_bound += 1

        source_policy = phase20_policy_book.decision_for_evidence(
            c4.source_opportunity_decision_sha256
        )
        if source_policy is None:
            _add_failure(
                failures,
                f"MISSING_SOURCE_POLICY:{c5.decision_id}",
            )
            continue
        if (
            source_policy.policy_record_sha256
            != c4.source_baseline_policy_record_sha256
        ):
            _add_failure(
                failures,
                f"SOURCE_POLICY_BINDING_DRIFT:{c5.decision_id}",
            )
            continue
        source_policy_bound += 1

        outcome = outcome_by_key.get(
            (
                c4.source_opportunity_decision_sha256,
                c4.signal_fingerprint,
            )
        )
        if outcome is None:
            missing_outcomes.append(c5.decision_id)
            continue
        if outcome.observed_at <= c5.decision_at:
            _add_failure(
                failures,
                f"OUTCOME_TEMPORAL_CONTAMINATION:{c5.decision_id}",
            )
            continue

        row = _bound_row(c4=c4, c5=c5, outcome=outcome)
        rows.append(row)
        if c5.treatment_differs_from_control:
            divergent_outcomes += 1

    status = _status(
        decision_count=len(c5_book.records),
        bound_outcomes=len(rows),
        failures=tuple(failures),
    )
    return Genc5OutcomeBindingReport(
        status=status,
        shadow_decision_count=len(c5_book.records),
        treatment_divergent_count=divergent,
        c4_bound_count=c4_bound,
        source_decision_bound_count=source_decision_bound,
        source_policy_bound_count=source_policy_bound,
        terminal_outcome_bound_count=len(rows),
        treatment_divergent_outcome_count=divergent_outcomes,
        missing_outcome_decision_ids=tuple(missing_outcomes),
        failures=tuple(failures),
        rows=tuple(rows),
        counterfactual_compound_pnl_computed=False,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _c4_c5_binding_valid(
    *,
    c4: Genc4MarginalEvidenceSeal,
    c5: Genc5ShadowDecisionSeal,
) -> bool:
    return (
        c4.evidence_sha256 == c5.marginal_evidence_sha256
        and c4.decision_at == c5.decision_at
        and c4.provider_key == c5.account_provider_key
        and c4.account_ref == c5.account_ref
    )


def _source_account_matches(
    canonical_payload_json: str,
    *,
    provider_key: str,
    account_ref: str,
) -> bool:
    try:
        payload = json.loads(canonical_payload_json)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    account = payload.get("account_identity")
    return (
        isinstance(account, dict)
        and account.get("provider_key") == provider_key
        and account.get("account_ref") == account_ref
    )


def _bound_row(
    *,
    c4: Genc4MarginalEvidenceSeal,
    c5: Genc5ShadowDecisionSeal,
    outcome: Phase20ForwardOutcomeSeal,
) -> Genc5BoundOutcomeRow:
    return Genc5BoundOutcomeRow(
        decision_id=c5.decision_id,
        decision_sha256=c5.decision_sha256,
        decision_at=c5.decision_at,
        c4_evidence_sha256=c4.evidence_sha256,
        source_opportunity_decision_sha256=(
            c4.source_opportunity_decision_sha256
        ),
        source_baseline_policy_record_sha256=(
            c4.source_baseline_policy_record_sha256
        ),
        trader_id=c4.trader_id,
        signal_fingerprint=c4.signal_fingerprint,
        treatment_differs_from_control=(
            c5.treatment_differs_from_control
        ),
        treatment_requested_risk_review_usd=(
            c5.treatment_requested_risk_review_usd
        ),
        proposed_incremental_stop_risk_usd=(
            c4.incremental_stop_risk_usd
        ),
        proposed_incremental_margin_usd=c4.incremental_margin_usd,
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
        observed_capital_minutes=outcome.capital_minutes,
        counterfactual_compound_pnl_computed=False,
        economic_utility_claimed=False,
    )


def _status(
    *,
    decision_count: int,
    bound_outcomes: int,
    failures: tuple[str, ...],
) -> Genc5OutcomeBindingStatus:
    if failures:
        return Genc5OutcomeBindingStatus.INVALID
    if decision_count == 0:
        return Genc5OutcomeBindingStatus.EMPTY
    if bound_outcomes == decision_count:
        return Genc5OutcomeBindingStatus.COMPLETE
    return Genc5OutcomeBindingStatus.PARTIAL


def _add_failure(failures: list[str], value: str) -> None:
    if value not in failures:
        failures.append(value)


def _require_sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 OOS {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 OOS {name} must be timezone-aware"
        )
