"""Causal OOS lineage binder for GEN-C7 profit preservation.

The binder attaches durable pre-outcome GEN-C7 decisions to observed account
state at the exact preregistered evaluation horizon. It describes the realized
path only. It does not infer the counterfactual treatment effect and cannot
claim economic utility or certification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_store import (
    Genc7ShadowDecisionSeal,
    VersionedGenc7ShadowBook,
)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 OOS {name} must be timezone-aware"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 OOS {name} must be finite non-negative Decimal"
        )


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(
            f"GEN-C7 OOS {name} must be finite Decimal"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C7 OOS {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class Genc7OutcomeEvidence:
    """Observed account state at one preregistered post-decision horizon."""

    outcome_id: str
    decision_sha256: str
    account_provider_key: str
    account_ref: str
    window_end_at: datetime
    observed_at: datetime
    ending_realized_capital_usd: Decimal
    ending_realized_profit_usd: Decimal
    ending_protected_floor_usd: Decimal
    ending_base_capital_usd: Decimal
    ending_compound_capital_usd: Decimal
    source_settlement_sha256: str
    source_t20_release_sha256: str
    path_evidence_sha256: str
    path_complete: bool
    settlement_coverage_complete: bool
    release_coverage_complete: bool
    counterfactual_treatment_pnl_computed: bool = False
    treatment_effect_identified: bool = False
    economic_utility_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.outcome_id
            or not self.account_provider_key
            or not self.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS outcome/account identity is required"
            )
        for name in (
            "decision_sha256",
            "source_settlement_sha256",
            "source_t20_release_sha256",
            "path_evidence_sha256",
        ):
            _sha(getattr(self, name), name)
        _aware(self.window_end_at, "window_end_at")
        _aware(self.observed_at, "observed_at")
        if self.observed_at < self.window_end_at:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS observation cannot predate evaluation horizon"
            )
        for name in (
            "ending_realized_capital_usd",
            "ending_realized_profit_usd",
            "ending_protected_floor_usd",
            "ending_base_capital_usd",
            "ending_compound_capital_usd",
        ):
            _nonnegative(getattr(self, name), name)
        if self.ending_realized_capital_usd <= 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS ending realized capital must be positive"
            )
        for name in (
            "path_complete",
            "settlement_coverage_complete",
            "release_coverage_complete",
            "counterfactual_treatment_pnl_computed",
            "treatment_effect_identified",
            "economic_utility_claimed",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 OOS {name} must be bool"
                )
        if (
            self.counterfactual_treatment_pnl_computed
            or self.treatment_effect_identified
            or self.economic_utility_claimed
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS evidence cannot invent treatment effect/authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["window_end_at"] = self.window_end_at.isoformat()
        payload["observed_at"] = self.observed_at.isoformat()
        for key, value in tuple(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = str(value)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


class Genc7OosBindingStatus(StrEnum):
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Genc7BoundObservedPath:
    decision_id: str
    decision_sha256: str
    decision_at: datetime
    account_provider_key: str
    account_ref: str
    evaluation_horizon_minutes: int
    outcome_evidence_sha256: str
    window_end_at: datetime
    observed_at: datetime
    realized_capital_delta_usd: Decimal
    realized_profit_delta_usd: Decimal
    protected_floor_delta_usd: Decimal
    base_capital_delta_usd: Decimal
    compound_capital_delta_usd: Decimal
    treatment_effect_identified: bool = False
    counterfactual_treatment_pnl_computed: bool = False
    economic_utility_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            not self.decision_id
            or not self.account_provider_key
            or not self.account_ref
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS bound path identity is required"
            )
        _sha(self.decision_sha256, "decision_sha256")
        _sha(self.outcome_evidence_sha256, "outcome_evidence_sha256")
        _aware(self.decision_at, "decision_at")
        _aware(self.window_end_at, "window_end_at")
        _aware(self.observed_at, "observed_at")
        if (
            not isinstance(self.evaluation_horizon_minutes, int)
            or isinstance(self.evaluation_horizon_minutes, bool)
            or self.evaluation_horizon_minutes <= 0
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS evaluation horizon must be positive int"
            )
        expected_window_end = self.decision_at + timedelta(
            minutes=self.evaluation_horizon_minutes
        )
        if self.window_end_at != expected_window_end:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS bound path horizon binding drift"
            )
        if self.observed_at < self.window_end_at:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS bound observation cannot predate horizon"
            )
        for name in (
            "realized_capital_delta_usd",
            "realized_profit_delta_usd",
            "protected_floor_delta_usd",
            "base_capital_delta_usd",
            "compound_capital_delta_usd",
        ):
            _finite(getattr(self, name), name)
        if self.protected_floor_delta_usd < 0:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS observed protected floor cannot decrease"
            )
        for name in (
            "treatment_effect_identified",
            "counterfactual_treatment_pnl_computed",
            "economic_utility_claimed",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C7 OOS bound path cannot claim counterfactual utility"
                )


@dataclass(frozen=True, slots=True)
class Genc7OosBindingReport:
    status: Genc7OosBindingStatus
    decision_count: int
    outcome_count: int
    bound_count: int
    path_complete_count: int
    settlement_complete_count: int
    release_complete_count: int
    missing_decision_ids: tuple[str, ...]
    failures: tuple[str, ...]
    rows: tuple[Genc7BoundObservedPath, ...]
    treatment_effect_identified: bool = False
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc7OosBindingStatus:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS report status is invalid"
            )
        for name in (
            "decision_count",
            "outcome_count",
            "bound_count",
            "path_complete_count",
            "settlement_complete_count",
            "release_complete_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C7 OOS {name} must be non-negative int"
                )
        if len(self.missing_decision_ids) != len(set(self.missing_decision_ids)):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS missing decision ids must be unique"
            )
        if len(self.failures) != len(set(self.failures)):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS failures must be unique"
            )
        if (
            not isinstance(self.rows, tuple)
            or any(
                not isinstance(item, Genc7BoundObservedPath)
                for item in self.rows
            )
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS report rows must be canonical"
            )
        if self.bound_count != len(self.rows):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS bound count/row count drift"
            )
        if (
            self.path_complete_count > self.outcome_count
            or self.settlement_complete_count > self.outcome_count
            or self.release_complete_count > self.outcome_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS coverage counts exceed outcome count"
            )
        if (
            self.bound_count
            + len(self.missing_decision_ids)
            + len(self.failures)
            != self.decision_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS decision accounting drift"
            )
        expected_status = _binding_status(
            decision_count=self.decision_count,
            bound_count=self.bound_count,
            missing_count=len(self.missing_decision_ids),
            failure_count=len(self.failures),
        )
        if self.status is not expected_status:
            raise CiboCompoundCapitalError(
                "GEN-C7 OOS report status/accounting drift"
            )
        for name in (
            "treatment_effect_identified",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool or getattr(self, name):
                raise CiboCompoundCapitalError(
                    "GEN-C7 OOS report cannot claim economic readiness"
                )


def bind_genc7_to_observed_paths(
    *,
    book: VersionedGenc7ShadowBook,
    outcomes: tuple[Genc7OutcomeEvidence, ...],
) -> Genc7OosBindingReport:
    """Bind exact decision identities to exact preregistered outcome windows."""

    if not isinstance(book, VersionedGenc7ShadowBook):
        raise CiboCompoundCapitalError(
            "GEN-C7 OOS requires canonical durable decision book"
        )
    if not isinstance(outcomes, tuple) or any(
        not isinstance(item, Genc7OutcomeEvidence) for item in outcomes
    ):
        raise CiboCompoundCapitalError(
            "GEN-C7 OOS outcomes must be canonical tuple"
        )
    outcome_shas = tuple(item.decision_sha256 for item in outcomes)
    if len(outcome_shas) != len(set(outcome_shas)):
        raise CiboCompoundCapitalError(
            "GEN-C7 OOS decision outcome identity must be unique"
        )
    sealed_decision_shas = {
        seal.decision_sha256
        for record in book.records
        if (seal := book.seal_for_decision(record.decision_id)) is not None
    }
    unmatched_outcomes = tuple(
        item.outcome_id
        for item in outcomes
        if item.decision_sha256 not in sealed_decision_shas
    )
    if unmatched_outcomes:
        raise CiboCompoundCapitalError(
            "GEN-C7 OOS outcome population contains unsealed decisions"
        )
    by_decision_sha = {item.decision_sha256: item for item in outcomes}

    rows: list[Genc7BoundObservedPath] = []
    missing: list[str] = []
    failures: list[str] = []
    path_complete = 0
    settlement_complete = 0
    release_complete = 0

    for record in book.records:
        seal = book.seal_for_decision(record.decision_id)
        if seal is None:
            failures.append(f"MISSING_DECISION_SEAL:{record.decision_id}")
            continue
        outcome = by_decision_sha.get(seal.decision_sha256)
        if outcome is None:
            missing.append(seal.decision_id)
            continue
        expected_end = seal.decision_at + timedelta(
            minutes=seal.evaluation_horizon_minutes
        )
        if outcome.window_end_at != expected_end:
            failures.append(
                f"OUTCOME_HORIZON_BINDING_DRIFT:{seal.decision_id}"
            )
            continue
        if (
            outcome.account_provider_key != seal.account_provider_key
            or outcome.account_ref != seal.account_ref
        ):
            failures.append(
                f"OUTCOME_ACCOUNT_BINDING_DRIFT:{seal.decision_id}"
            )
            continue
        if (
            outcome.ending_protected_floor_usd
            < seal.initial_protected_floor_usd
        ):
            failures.append(
                f"PROTECTED_FLOOR_DECREASE:{seal.decision_id}"
            )
            continue
        if outcome.path_complete:
            path_complete += 1
        if outcome.settlement_coverage_complete:
            settlement_complete += 1
        if outcome.release_coverage_complete:
            release_complete += 1
        if not (
            outcome.path_complete
            and outcome.settlement_coverage_complete
            and outcome.release_coverage_complete
        ):
            failures.append(
                f"OUTCOME_COVERAGE_INCOMPLETE:{seal.decision_id}"
            )
            continue

        rows.append(_bound_row(seal=seal, outcome=outcome))

    status = _binding_status(
        decision_count=book.generation,
        bound_count=len(rows),
        missing_count=len(missing),
        failure_count=len(failures),
    )
    return Genc7OosBindingReport(
        status=status,
        decision_count=book.generation,
        outcome_count=len(outcomes),
        bound_count=len(rows),
        path_complete_count=path_complete,
        settlement_complete_count=settlement_complete,
        release_complete_count=release_complete,
        missing_decision_ids=tuple(missing),
        failures=tuple(failures),
        rows=tuple(rows),
        treatment_effect_identified=False,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _bound_row(
    *,
    seal: Genc7ShadowDecisionSeal,
    outcome: Genc7OutcomeEvidence,
) -> Genc7BoundObservedPath:
    return Genc7BoundObservedPath(
        decision_id=seal.decision_id,
        decision_sha256=seal.decision_sha256,
        decision_at=seal.decision_at,
        account_provider_key=seal.account_provider_key,
        account_ref=seal.account_ref,
        evaluation_horizon_minutes=seal.evaluation_horizon_minutes,
        outcome_evidence_sha256=outcome.fingerprint(),
        window_end_at=outcome.window_end_at,
        observed_at=outcome.observed_at,
        realized_capital_delta_usd=(
            outcome.ending_realized_capital_usd
            - seal.initial_realized_capital_usd
        ),
        realized_profit_delta_usd=(
            outcome.ending_realized_profit_usd
            - seal.initial_realized_profit_usd
        ),
        protected_floor_delta_usd=(
            outcome.ending_protected_floor_usd
            - seal.initial_protected_floor_usd
        ),
        base_capital_delta_usd=(
            outcome.ending_base_capital_usd
            - seal.initial_base_capital_usd
        ),
        compound_capital_delta_usd=(
            outcome.ending_compound_capital_usd
            - seal.initial_compound_capital_usd
        ),
        treatment_effect_identified=False,
        counterfactual_treatment_pnl_computed=False,
        economic_utility_claimed=False,
    )


def _binding_status(
    *,
    decision_count: int,
    bound_count: int,
    missing_count: int,
    failure_count: int,
) -> Genc7OosBindingStatus:
    if decision_count == 0:
        return Genc7OosBindingStatus.EMPTY
    if failure_count:
        return Genc7OosBindingStatus.INVALID
    if missing_count or bound_count < decision_count:
        return Genc7OosBindingStatus.PARTIAL
    return Genc7OosBindingStatus.COMPLETE
