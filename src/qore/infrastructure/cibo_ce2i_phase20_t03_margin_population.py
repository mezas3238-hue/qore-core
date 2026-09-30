"""Fresh forward provider-margin population audit for CE2I T03.

T03 margin efficiency is measured from the exact opportunity/provider facts
sealed before each fresh forward decision. Economic USD notional is derived from
the already-audited monetary factor magnitude, while minimum executable margin
comes from the same provider snapshot.

This audit proves only forward/current provider observations. It does not claim
historical 2017 margin terms, certify an alternative expression universe, or
grant additional sizing/margin authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_magnitude import (
    assess_minimum_seed_factor_magnitude,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_forward_population import (
    iter_phase20_forward_candidate_facts,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    normalize_provider_economics,
)


@dataclass(frozen=True, slots=True)
class Phase20T03MarginPopulationAudit:
    candidate_instances: int
    margin_identified_instances: int
    blocked_candidate_instances: int
    represented_lineages: tuple[TraderLineage, ...]
    represented_symbols: tuple[str, ...]
    minimum_margin_usd: Decimal | None
    maximum_margin_usd: Decimal | None
    p50_exposure_per_margin: Decimal | None
    p95_exposure_per_margin: Decimal | None
    maximum_exposure_per_margin: Decimal | None
    minimum_required_lineages: int
    frozen_lineage_coverage_met: bool
    forward_margin_population_identified: bool
    historical_2017_margin_terms_proven: bool
    equivalent_expression_universe_certified: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "candidate_instances",
            "margin_identified_instances",
            "blocked_candidate_instances",
            "minimum_required_lineages",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T03 {name} must be non-negative int"
                )
        if (
            self.margin_identified_instances + self.blocked_candidate_instances
            != self.candidate_instances
        ):
            raise CiboCapitalManagementError(
                "Phase20 T03 candidate accounting drift"
            )
        if len(self.represented_lineages) != len(set(self.represented_lineages)):
            raise CiboCapitalManagementError(
                "Phase20 T03 lineages must be unique"
            )
        if len(self.represented_symbols) != len(set(self.represented_symbols)):
            raise CiboCapitalManagementError(
                "Phase20 T03 symbols must be unique"
            )
        for name in (
            "minimum_margin_usd",
            "maximum_margin_usd",
            "p50_exposure_per_margin",
            "p95_exposure_per_margin",
            "maximum_exposure_per_margin",
        ):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T03 {name} must be positive finite Decimal/null"
                )
        if (
            self.minimum_margin_usd is not None
            and self.maximum_margin_usd is not None
            and self.maximum_margin_usd < self.minimum_margin_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20 T03 margin bounds are inverted"
            )
        if (
            self.historical_2017_margin_terms_proven
            or self.equivalent_expression_universe_certified
        ):
            raise CiboCapitalManagementError(
                "Phase20 T03 forward audit cannot certify historical/provider alternatives"
            )


def assess_phase20_t03_margin_population(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T03MarginPopulationAudit:
    """Measure forward minimum-seed economic notional per margin dollar."""

    facts = iter_phase20_forward_candidate_facts(
        evidence_book=evidence_book,
    )
    ratios: list[Decimal] = []
    margins: list[Decimal] = []
    lineages: set[TraderLineage] = set()
    symbols: set[str] = set()
    blocked = 0

    for item in facts:
        magnitude = assess_minimum_seed_factor_magnitude(
            opportunity=item.opportunity,
            observation=item.provider_observation,
            decision_at=item.decision_at,
            provider_evidence_ref=item.provider_evidence_id,
        )
        normalized = normalize_provider_economics(
            opportunity=item.opportunity,
            observation=item.provider_observation,
        )
        usd_notionals = tuple(
            abs(exposure.signed_notional_usd)
            for exposure in magnitude.exposures
            if exposure.signed_notional_usd is not None
        )
        if (
            not magnitude.usd_magnitude_complete
            or not usd_notionals
            or normalized.minimum_margin_usd <= 0
        ):
            blocked += 1
            continue

        primary_notional = max(usd_notionals)
        if primary_notional <= 0:
            blocked += 1
            continue
        ratios.append(primary_notional / normalized.minimum_margin_usd)
        margins.append(normalized.minimum_margin_usd)
        lineages.add(item.opportunity.trader_id)
        symbols.add(item.opportunity.qore_symbol)

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    lineage_coverage = len(lineages) >= plan.minimum_global_lineages
    identified = bool(ratios) and blocked == 0 and lineage_coverage

    blockers: list[str] = []
    if not facts:
        blockers.append("NO_FORWARD_CANDIDATE_INSTANCES")
    if blocked > 0:
        blockers.append("FORWARD_MARGIN_ECONOMIC_COVERAGE_INCOMPLETE")
    if not lineage_coverage:
        blockers.append(
            "T03_FORWARD_LINEAGE_COVERAGE_NOT_MET:"
            f"{len(lineages)}/{plan.minimum_global_lineages}"
        )
    blockers.extend(
        (
            "HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN",
            "EQUIVALENT_EXPRESSION_UNIVERSE_NOT_CERTIFIED",
        )
    )

    return Phase20T03MarginPopulationAudit(
        candidate_instances=len(facts),
        margin_identified_instances=len(ratios),
        blocked_candidate_instances=blocked,
        represented_lineages=tuple(
            sorted(lineages, key=lambda item: item.value)
        ),
        represented_symbols=tuple(sorted(symbols)),
        minimum_margin_usd=min(margins) if margins else None,
        maximum_margin_usd=max(margins) if margins else None,
        p50_exposure_per_margin=_percentile(ratios, Decimal("0.50")),
        p95_exposure_per_margin=_percentile(ratios, Decimal("0.95")),
        maximum_exposure_per_margin=max(ratios) if ratios else None,
        minimum_required_lineages=plan.minimum_global_lineages,
        frozen_lineage_coverage_met=lineage_coverage,
        forward_margin_population_identified=identified,
        historical_2017_margin_terms_proven=False,
        equivalent_expression_universe_certified=False,
        blockers=tuple(blockers),
    )


def _percentile(
    values: list[Decimal],
    probability: Decimal,
) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = int(
        (probability * Decimal(len(ordered))).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    index = max(0, min(len(ordered) - 1, rank - 1))
    return ordered[index]
