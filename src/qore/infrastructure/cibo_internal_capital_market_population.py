"""Descriptive fresh-scarcity population accounting for GEN-C6.

No performance judgment is made here. The population layer reports what causal
evidence actually exists for Internal Capital Market research and remains
explicitly non-economic until a separate economic gate is preregistered.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
)
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_MARKET_ID,
    GENC6_POLICY_FROZEN_AT,
    GENC6_POLICY_ID,
    genc6_policy_sha256,
)
from qore.infrastructure.cibo_internal_capital_market_oos_binding import (
    Genc6OosBindingReport,
    Genc6OosBindingStatus,
)
from qore.infrastructure.cibo_internal_capital_market_store import (
    VersionedGenc6InternalCapitalMarketBook,
)


class Genc6PopulationStatus(StrEnum):
    EMPTY = "EMPTY"
    COLLECTING = "COLLECTING"
    COVERAGE_COMPLETE = "COVERAGE_COMPLETE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class Genc6FreshScarcityPopulation:
    status: Genc6PopulationStatus
    market_id: str
    policy_id: str
    policy_sha256: str
    policy_frozen_at: datetime
    decision_epoch_count: int
    true_scarcity_epoch_count: int
    non_scarcity_epoch_count: int
    candidate_count: int
    treatment_control_divergence_count: int
    treatment_reserve_count: int
    treatment_allocation_count: int
    account_keys: tuple[str, ...]
    trader_ids: tuple[str, ...]
    decision_calendar_days: int
    first_decision_at: datetime | None
    last_decision_at: datetime | None
    calendar_span_days: int
    total_available_capital_usd: Decimal
    total_requested_capital_usd: Decimal
    total_capital_shortfall_usd: Decimal
    mean_competition_intensity: Decimal
    mean_true_scarcity_intensity: Decimal
    mean_mutually_fundable_candidates: Decimal
    candidate_c4_coverage: Decimal
    candidate_c5_coverage: Decimal
    source_decision_coverage: Decimal
    source_policy_coverage: Decimal
    settlement_coverage: Decimal
    release_timing_coverage: Decimal
    blocker_counts: tuple[tuple[str, int], ...]
    binding_status: Genc6OosBindingStatus
    missing_outcome_keys: tuple[str, ...]
    missing_release_keys: tuple[str, ...]
    failures: tuple[str, ...]
    descriptive_only: bool = True
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc6PopulationStatus:
            raise CiboCompoundCapitalError(
                "GEN-C6 population status is invalid"
            )
        if self.market_id != GENC6_MARKET_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 population market identity drift"
            )
        if self.policy_id != GENC6_POLICY_ID:
            raise CiboCompoundCapitalError(
                "GEN-C6 population policy identity drift"
            )
        if self.policy_sha256 != genc6_policy_sha256():
            raise CiboCompoundCapitalError(
                "GEN-C6 population policy digest drift"
            )
        if self.policy_frozen_at != GENC6_POLICY_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "GEN-C6 population policy freeze drift"
            )
        for name in (
            "decision_epoch_count",
            "true_scarcity_epoch_count",
            "non_scarcity_epoch_count",
            "candidate_count",
            "treatment_control_divergence_count",
            "treatment_reserve_count",
            "treatment_allocation_count",
            "decision_calendar_days",
            "calendar_span_days",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 population {name} must be non-negative int"
                )
        if (
            self.true_scarcity_epoch_count
            + self.non_scarcity_epoch_count
            != self.decision_epoch_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 population scarcity partition drift"
            )
        if (
            self.treatment_reserve_count
            + self.treatment_allocation_count
            != self.decision_epoch_count
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 population treatment action partition drift"
            )
        for name in (
            "total_available_capital_usd",
            "total_requested_capital_usd",
            "total_capital_shortfall_usd",
            "mean_competition_intensity",
            "mean_true_scarcity_intensity",
            "mean_mutually_fundable_candidates",
            "candidate_c4_coverage",
            "candidate_c5_coverage",
            "source_decision_coverage",
            "source_policy_coverage",
            "settlement_coverage",
            "release_timing_coverage",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 population {name} must be finite non-negative"
                )
        for name in (
            "mean_competition_intensity",
            "mean_true_scarcity_intensity",
            "candidate_c4_coverage",
            "candidate_c5_coverage",
            "source_decision_coverage",
            "source_policy_coverage",
            "settlement_coverage",
            "release_timing_coverage",
        ):
            if getattr(self, name) > 1:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 population {name} must be in [0,1]"
                )
        if (self.first_decision_at is None) != (
            self.last_decision_at is None
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 population decision range is incomplete"
            )
        if self.first_decision_at is not None:
            _aware(self.first_decision_at, "first_decision_at")
            assert self.last_decision_at is not None
            _aware(self.last_decision_at, "last_decision_at")
            if self.first_decision_at < self.policy_frozen_at:
                raise CiboCompoundCapitalError(
                    "GEN-C6 population contains pre-freeze decisions"
                )
            if self.last_decision_at < self.first_decision_at:
                raise CiboCompoundCapitalError(
                    "GEN-C6 population decision range reversed"
                )
        for values, label in (
            (self.account_keys, "accounts"),
            (self.trader_ids, "Traders"),
            (self.missing_outcome_keys, "missing outcomes"),
            (self.missing_release_keys, "missing releases"),
            (self.failures, "failures"),
        ):
            if len(values) != len(set(values)):
                raise CiboCompoundCapitalError(
                    f"GEN-C6 population {label} must be unique"
                )
        blocker_keys = tuple(item[0] for item in self.blocker_counts)
        if len(blocker_keys) != len(set(blocker_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C6 population blocker keys must be unique"
            )
        if any(
            not key
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count <= 0
            for key, count in self.blocker_counts
        ):
            raise CiboCompoundCapitalError(
                "GEN-C6 population blocker counts invalid"
            )
        if type(self.binding_status) is not Genc6OosBindingStatus:
            raise CiboCompoundCapitalError(
                "GEN-C6 population binding status invalid"
            )
        for name in (
            "descriptive_only",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C6 population {name} must be bool"
                )
        if not self.descriptive_only:
            raise CiboCompoundCapitalError(
                "GEN-C6 population must remain descriptive"
            )
        if self.economic_utility_ready or self.certification_ready:
            raise CiboCompoundCapitalError(
                "GEN-C6 population cannot claim economic/certification readiness"
            )


def describe_genc6_fresh_scarcity_population(
    *,
    genc6_book: VersionedGenc6InternalCapitalMarketBook,
    binding: Genc6OosBindingReport,
) -> Genc6FreshScarcityPopulation:
    if not isinstance(
        genc6_book,
        VersionedGenc6InternalCapitalMarketBook,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C6 population requires canonical market book"
        )
    if not isinstance(binding, Genc6OosBindingReport):
        raise CiboCompoundCapitalError(
            "GEN-C6 population requires canonical OOS binding report"
        )
    if binding.decision_count != len(genc6_book.records):
        raise CiboCompoundCapitalError(
            "GEN-C6 population/book binding decision count drift"
        )

    true_scarcity = 0
    divergence = 0
    reserve_count = 0
    allocation_count = 0
    candidate_count = 0
    accounts: set[str] = set()
    traders: set[str] = set()
    days: set[date] = set()
    times: list[datetime] = []
    blockers: Counter[str] = Counter()
    total_available = Decimal(0)
    total_requested = Decimal(0)
    total_shortfall = Decimal(0)
    intensities: list[Decimal] = []
    scarcity_intensities: list[Decimal] = []
    mutually_fundable: list[int] = []

    for record in genc6_book.records:
        seal = genc6_book.seal_for_decision(record.decision_id)
        if seal is None:
            raise CiboCompoundCapitalError(
                "GEN-C6 population missing durable decision seal"
            )
        event = _json_object(seal.event_json, "event")
        decision = _json_object(seal.decision_json, "decision")
        candidates = event.get("candidates")
        if not isinstance(candidates, list):
            raise CiboCompoundCapitalError(
                "GEN-C6 population event candidate set invalid"
            )
        candidate_count += len(candidates)
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise CiboCompoundCapitalError(
                    "GEN-C6 population candidate record invalid"
                )
            trader_id = candidate.get("trader_id")
            if isinstance(trader_id, str) and trader_id:
                traders.add(trader_id)

        account = event.get("account")
        if not isinstance(account, dict):
            raise CiboCompoundCapitalError(
                "GEN-C6 population account record invalid"
            )
        provider = str(account.get("provider_key", ""))
        account_ref = str(account.get("account_ref", ""))
        if not provider or not account_ref:
            raise CiboCompoundCapitalError(
                "GEN-C6 population account identity missing"
            )
        accounts.add(f"{provider}:{account_ref}")

        decision_at = datetime.fromisoformat(str(event["decision_at"]))
        _aware(decision_at, "decision_at")
        times.append(decision_at)
        days.add(decision_at.date())

        is_scarcity = _bool(event.get("true_scarcity"), "true_scarcity")
        if is_scarcity:
            true_scarcity += 1

        is_divergent = _bool(
            decision.get("treatment_differs_from_control"),
            "treatment_differs_from_control",
        )
        if is_divergent:
            divergence += 1

        treatment_action = decision.get("treatment_action")
        if treatment_action == "RESERVE_NO_DEPLOYMENT":
            reserve_count += 1
        elif treatment_action == "ALLOCATE_MARGINAL_UNIT":
            allocation_count += 1
        else:
            raise CiboCompoundCapitalError(
                "GEN-C6 population treatment action invalid"
            )

        decision_blockers = decision.get("blocker_codes")
        if not isinstance(decision_blockers, list):
            raise CiboCompoundCapitalError(
                "GEN-C6 population blocker list invalid"
            )
        blockers.update(str(item) for item in decision_blockers)

        available = Decimal(str(event["available_capital_usd"]))
        requested = Decimal(str(event["total_requested_capital_usd"]))
        shortfall = Decimal(str(event["capital_shortfall_usd"]))
        intensity = Decimal(str(event["competition_intensity"]))
        mutual = int(event["mutually_fundable_candidate_count"])
        total_available += available
        total_requested += requested
        total_shortfall += shortfall
        intensities.append(intensity)
        mutually_fundable.append(mutual)
        if is_scarcity:
            scarcity_intensities.append(intensity)

    if binding.candidate_count != candidate_count:
        raise CiboCompoundCapitalError(
            "GEN-C6 population/binder candidate count drift"
        )

    first = min(times) if times else None
    last = max(times) if times else None
    span = (
        0
        if first is None or last is None
        else (last.date() - first.date()).days + 1
    )

    if binding.status is Genc6OosBindingStatus.INVALID:
        status = Genc6PopulationStatus.INVALID
    elif not genc6_book.records:
        status = Genc6PopulationStatus.EMPTY
    elif binding.status is Genc6OosBindingStatus.COMPLETE:
        status = Genc6PopulationStatus.COVERAGE_COMPLETE
    else:
        status = Genc6PopulationStatus.COLLECTING

    return Genc6FreshScarcityPopulation(
        status=status,
        market_id=GENC6_MARKET_ID,
        policy_id=GENC6_POLICY_ID,
        policy_sha256=genc6_policy_sha256(),
        policy_frozen_at=GENC6_POLICY_FROZEN_AT,
        decision_epoch_count=len(genc6_book.records),
        true_scarcity_epoch_count=true_scarcity,
        non_scarcity_epoch_count=(
            len(genc6_book.records) - true_scarcity
        ),
        candidate_count=candidate_count,
        treatment_control_divergence_count=divergence,
        treatment_reserve_count=reserve_count,
        treatment_allocation_count=allocation_count,
        account_keys=tuple(sorted(accounts)),
        trader_ids=tuple(sorted(traders)),
        decision_calendar_days=len(days),
        first_decision_at=first,
        last_decision_at=last,
        calendar_span_days=span,
        total_available_capital_usd=total_available,
        total_requested_capital_usd=total_requested,
        total_capital_shortfall_usd=total_shortfall,
        mean_competition_intensity=_mean_decimal(intensities),
        mean_true_scarcity_intensity=_mean_decimal(
            scarcity_intensities
        ),
        mean_mutually_fundable_candidates=_mean_int(mutually_fundable),
        candidate_c4_coverage=_ratio(
            binding.c4_bound_count,
            candidate_count,
        ),
        candidate_c5_coverage=_ratio(
            binding.c5_bound_count,
            candidate_count,
        ),
        source_decision_coverage=_ratio(
            binding.source_decision_bound_count,
            candidate_count,
        ),
        source_policy_coverage=_ratio(
            binding.source_policy_bound_count,
            candidate_count,
        ),
        settlement_coverage=_ratio(
            binding.settlement_bound_count,
            candidate_count,
        ),
        release_timing_coverage=_ratio(
            binding.release_timing_bound_count,
            candidate_count,
        ),
        blocker_counts=tuple(sorted(blockers.items())),
        binding_status=binding.status,
        missing_outcome_keys=binding.missing_outcome_keys,
        missing_release_keys=binding.missing_release_keys,
        failures=binding.failures,
        descriptive_only=True,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal(0)
    return Decimal(numerator) / Decimal(denominator)


def _mean_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values, Decimal(0)) / Decimal(len(values))


def _mean_int(values: list[int]) -> Decimal:
    if not values:
        return Decimal(0)
    return Decimal(sum(values)) / Decimal(len(values))


def _json_object(value: str, label: str) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCompoundCapitalError(
            f"GEN-C6 population {label} JSON invalid"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            f"GEN-C6 population {label} payload must be object"
        )
    return payload


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise CiboCompoundCapitalError(
            f"GEN-C6 population {name} must be bool"
        )
    return value


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"GEN-C6 population {name} must be timezone-aware"
        )
