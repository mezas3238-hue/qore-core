"""Descriptive fresh-OOS population accounting for CIBO GEN-C5.

This layer measures what evidence has actually accumulated for the preregistered
GEN-C5 shadow controller. It does not set performance thresholds, estimate
counterfactual compound PnL, rank policies or claim certification readiness.

The report answers only descriptive questions such as:

- how many shadow decisions were sealed;
- how often treatment differed from control;
- how many exact C4/source-policy/outcome chains are complete;
- what accounts and Trader lineages are represented;
- what calendar span has been observed;
- which preregistered blocker codes occur.

Any future economic gate must be separately preregistered before inspecting the
outcomes it intends to evaluate.
"""

from __future__ import annotations

from collections import Counter
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
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_marginal_capital_utility_evidence_store import (
    VersionedGenc4MarginalEvidenceBook,
)
from qore.infrastructure.cibo_sequential_compounding_oos_binding import (
    Genc5OutcomeBindingStatus,
    bind_genc5_shadow_to_phase20_outcomes,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_policy import (
    GENC5_SHADOW_POLICY_FROZEN_AT,
    GENC5_SHADOW_POLICY_ID,
    genc5_shadow_policy_sha256,
)
from qore.infrastructure.cibo_sequential_compounding_shadow_store import (
    VersionedGenc5ShadowBook,
)


class Genc5PopulationStatus(StrEnum):
    EMPTY = "EMPTY"
    COLLECTING = "COLLECTING"
    COVERAGE_COMPLETE = "COVERAGE_COMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Genc5PopulationReport:
    status: Genc5PopulationStatus
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    shadow_decision_count: int
    treatment_divergent_count: int
    treatment_hold_count: int
    c4_bound_count: int
    terminal_outcome_bound_count: int
    treatment_divergent_outcome_count: int
    outcome_coverage: Decimal
    treatment_divergent_outcome_coverage: Decimal
    first_decision_at: datetime | None
    last_decision_at: datetime | None
    calendar_span_days: int
    decision_calendar_days: int
    account_keys: tuple[str, ...]
    trader_ids: tuple[str, ...]
    blocker_counts: tuple[tuple[str, int], ...]
    binding_status: Genc5OutcomeBindingStatus
    missing_outcome_decision_ids: tuple[str, ...]
    failures: tuple[str, ...]
    descriptive_only: bool = True
    counterfactual_compound_pnl_computed: bool = False
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc5PopulationStatus:
            raise CiboCompoundCapitalError(
                "GEN-C5 population status is invalid"
            )
        if self.policy_id != GENC5_SHADOW_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C5 population policy identity drift"
            )
        if self.policy_sha256 != genc5_shadow_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C5 population policy digest drift"
            )
        if self.policy_frozen_at != GENC5_SHADOW_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C5 population policy freeze drift"
            )
        for name in (
            "shadow_decision_count",
            "treatment_divergent_count",
            "treatment_hold_count",
            "c4_bound_count",
            "terminal_outcome_bound_count",
            "treatment_divergent_outcome_count",
            "calendar_span_days",
            "decision_calendar_days",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 population {name} must be non-negative int"
                )
        if (
            self.treatment_divergent_count
            + self.treatment_hold_count
            != self.shadow_decision_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population treatment partition drift"
            )
        if self.c4_bound_count > self.shadow_decision_count:
            raise CiboCompoundCapitalError(
                "GEN-C5 population C4 coverage exceeds decisions"
            )
        if self.terminal_outcome_bound_count > self.shadow_decision_count:
            raise CiboCompoundCapitalError(
                "GEN-C5 population outcome coverage exceeds decisions"
            )
        if (
            self.treatment_divergent_outcome_count
            > self.treatment_divergent_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population divergent outcome count exceeds treatment"
            )
        for name in (
            "outcome_coverage",
            "treatment_divergent_outcome_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 population {name} must be in [0,1]"
                )
        expected_outcome_coverage = _ratio(
            self.terminal_outcome_bound_count,
            self.shadow_decision_count,
        )
        expected_divergent_coverage = _ratio(
            self.treatment_divergent_outcome_count,
            self.treatment_divergent_count,
        )
        if self.outcome_coverage != expected_outcome_coverage:
            raise CiboCompoundCapitalError(
                "GEN-C5 population outcome coverage arithmetic drift"
            )
        if (
            self.treatment_divergent_outcome_coverage
            != expected_divergent_coverage
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population divergent coverage arithmetic drift"
            )
        if (self.first_decision_at is None) != (
            self.last_decision_at is None
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population decision time range is incomplete"
            )
        if self.first_decision_at is not None:
            _aware(self.first_decision_at, "first_decision_at")
            assert self.last_decision_at is not None
            _aware(self.last_decision_at, "last_decision_at")
            if self.first_decision_at < self.policy_frozen_at:
                raise CiboCompoundCapitalError(
                    "GEN-C5 population contains pre-freeze decision"
                )
            if self.last_decision_at < self.first_decision_at:
                raise CiboCompoundCapitalError(
                    "GEN-C5 population decision range is reversed"
                )
        for values, label in (
            (self.account_keys, "account keys"),
            (self.trader_ids, "Trader ids"),
            (self.missing_outcome_decision_ids, "missing outcome ids"),
            (self.failures, "failures"),
        ):
            if len(values) != len(set(values)):
                raise CiboCompoundCapitalError(
                    f"GEN-C5 population {label} must be unique"
                )
        blocker_keys = tuple(item[0] for item in self.blocker_counts)
        if len(blocker_keys) != len(set(blocker_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C5 population blocker keys must be unique"
            )
        if any(
            not key
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            for key, count in self.blocker_counts
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population blocker counts are invalid"
            )
        for name in (
            "descriptive_only",
            "counterfactual_compound_pnl_computed",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C5 population {name} must be bool"
                )
        if not self.descriptive_only:
            raise CiboCompoundCapitalError(
                "GEN-C5 population layer must remain descriptive"
            )
        if (
            self.counterfactual_compound_pnl_computed
            or self.economic_utility_ready
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C5 population cannot claim economic/certification readiness"
            )


def describe_genc5_fresh_oos_population(
    *,
    c4_book: VersionedGenc4MarginalEvidenceBook,
    c5_book: VersionedGenc5ShadowBook,
    phase20_evidence_book: VersionedPhase20ForwardEvidenceBook,
    phase20_policy_book: VersionedPhase20ForwardPolicyBook,
) -> Genc5PopulationReport:
    """Describe accumulated GEN-C5 evidence without evaluating performance."""

    binding = bind_genc5_shadow_to_phase20_outcomes(
        c4_book=c4_book,
        c5_book=c5_book,
        phase20_evidence_book=phase20_evidence_book,
        phase20_policy_book=phase20_policy_book,
    )

    seals = tuple(
        seal
        for row in c5_book.records
        if (seal := c5_book.seal_for_decision(row.decision_id)) is not None
    )
    decision_times = tuple(sorted(item.decision_at for item in seals))
    first_decision = decision_times[0] if decision_times else None
    last_decision = decision_times[-1] if decision_times else None
    calendar_span_days = (
        0
        if first_decision is None or last_decision is None
        else (last_decision.date() - first_decision.date()).days + 1
    )
    decision_calendar_days = len(
        {item.decision_at.date() for item in seals}
    )

    divergent = sum(
        1 for item in seals if item.treatment_differs_from_control
    )
    holds = len(seals) - divergent
    blockers = Counter(
        blocker
        for item in seals
        for blocker in item.blocker_codes
    )
    accounts = tuple(
        sorted(
            {
                f"{item.account_provider_key}:{item.account_ref}"
                for item in seals
            }
        )
    )

    c4_by_sha = {
        row.evidence_sha256: c4_book.seal_for_sha(row.evidence_sha256)
        for row in c4_book.records
    }
    trader_ids = tuple(
        sorted(
            {
                c4.trader_id
                for item in seals
                if (
                    (c4 := c4_by_sha.get(item.marginal_evidence_sha256))
                    is not None
                )
            }
        )
    )

    if binding.status is Genc5OutcomeBindingStatus.INVALID:
        status = Genc5PopulationStatus.INVALID
    elif not seals:
        status = Genc5PopulationStatus.EMPTY
    elif binding.status is Genc5OutcomeBindingStatus.COMPLETE:
        status = Genc5PopulationStatus.COVERAGE_COMPLETE
    else:
        status = Genc5PopulationStatus.COLLECTING

    return Genc5PopulationReport(
        status=status,
        policy_id=GENC5_SHADOW_POLICY_ID,
        policy_sha256=genc5_shadow_policy_sha256(),
        policy_frozen_at=GENC5_SHADOW_POLICY_FROZEN_AT,
        shadow_decision_count=len(seals),
        treatment_divergent_count=divergent,
        treatment_hold_count=holds,
        c4_bound_count=binding.c4_bound_count,
        terminal_outcome_bound_count=(
            binding.terminal_outcome_bound_count
        ),
        treatment_divergent_outcome_count=(
            binding.treatment_divergent_outcome_count
        ),
        outcome_coverage=_ratio(
            binding.terminal_outcome_bound_count,
            len(seals),
        ),
        treatment_divergent_outcome_coverage=_ratio(
            binding.treatment_divergent_outcome_count,
            divergent,
        ),
        first_decision_at=first_decision,
        last_decision_at=last_decision,
        calendar_span_days=calendar_span_days,
        decision_calendar_days=decision_calendar_days,
        account_keys=accounts,
        trader_ids=trader_ids,
        blocker_counts=tuple(sorted(blockers.items())),
        binding_status=binding.status,
        missing_outcome_decision_ids=(
            binding.missing_outcome_decision_ids
        ),
        failures=binding.failures,
        descriptive_only=True,
        counterfactual_compound_pnl_computed=False,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal(0)
    return Decimal(numerator) / Decimal(denominator)


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C5 population {name} must be timezone-aware"
        )
