"""V48 density lineage from already-consumed Capitalizer evidence.

This is a population-capacity comparison only. The historical populations use different
strategy contracts and therefore MUST NOT be compared for edge/PF/DD or used as proof
that V48 will inherit old economics.

It establishes one narrower fact:
native M1 and the Owner/QORE M1 MSS+FVG+OB triad were historically capable of producing
thousands of entries per complete year; V47's ~31.5 pre-union candidates/year therefore
cannot be attributed to M1 data scarcity or triad reachability alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

IDENTITY = "QORE_CAPITALIZER_V48_DENSITY_LINEAGE"


@dataclass(frozen=True, slots=True)
class V48HistoricalPopulation:
    population_id: str
    evidence_run_id: int
    evidence_artifact_id: int | None
    years: tuple[tuple[int, int], ...]
    total_population: int
    comparable_for_economics: bool = False
    fresh_holdout_used: bool = False

    def __post_init__(self) -> None:
        if not self.population_id or self.population_id != self.population_id.upper():
            raise ValueError("population_id must be non-empty uppercase")
        if self.evidence_run_id <= 0 or self.total_population < 0:
            raise ValueError("invalid population provenance/count")
        if sum(count for _year, count in self.years) != self.total_population:
            raise ValueError("annual density rows must sum to total population")
        if self.comparable_for_economics:
            raise ValueError("V48 density lineage does not authorize economic comparison")
        if self.fresh_holdout_used:
            raise ValueError("V48 density lineage cannot use sealed Fresh Holdout")


NATIVE_M1_TRIAD_POPULATION = V48HistoricalPopulation(
    population_id="NATIVE_M1_OWNER_QORE_TRIAD_REPLAY",
    evidence_run_id=35548099334,
    evidence_artifact_id=10619127272,
    years=(
        (2016, 628),
        (2017, 2078),
        (2018, 2167),
        (2019, 2087),
        (2020, 2188),
        (2021, 2183),
        (2022, 2170),
        (2023, 2169),
        (2024, 2242),
        (2025, 2258),
        (2026, 1526),
    ),
    total_population=21696,
)


@dataclass(frozen=True, slots=True)
class V48RejectedPopulation:
    population_id: str
    source_years: Decimal
    fractal_rows: int
    ftm_rows: int
    pre_union_rows: int
    final_union_authoritatively_executed: bool = False

    def __post_init__(self) -> None:
        if self.pre_union_rows != self.fractal_rows + self.ftm_rows:
            raise ValueError("V47 pre-union count must equal route sum")
        if self.final_union_authoritatively_executed:
            raise ValueError("V47 final S2D union was not authoritative before rejection")

    @property
    def pre_union_rows_per_year(self) -> Decimal:
        return Decimal(self.pre_union_rows) / self.source_years


V47_REJECTED_PRE_UNION = V48RejectedPopulation(
    population_id="V47_S2_REJECTED_PRE_UNION",
    source_years=Decimal("6"),
    fractal_rows=91,
    ftm_rows=98,
    pre_union_rows=189,
)


def complete_year_native_m1_counts() -> tuple[int, ...]:
    return tuple(
        count
        for year, count in NATIVE_M1_TRIAD_POPULATION.years
        if 2017 <= year <= 2025
    )


def mean_complete_year_native_m1_entries() -> Decimal:
    counts = complete_year_native_m1_counts()
    return Decimal(sum(counts)) / Decimal(len(counts))


def population_capacity_ratio_vs_v47_pre_union() -> Decimal:
    """Diagnostic ratio only; populations are not economic equivalents."""

    return (
        mean_complete_year_native_m1_entries()
        / V47_REJECTED_PRE_UNION.pre_union_rows_per_year
    )


@dataclass(frozen=True, slots=True)
class V48DensityLineage:
    identity: str = IDENTITY
    old_m1_population: V48HistoricalPopulation = NATIVE_M1_TRIAD_POPULATION
    rejected_v47_population: V48RejectedPopulation = V47_REJECTED_PRE_UNION
    m1_data_scarcity_supported_as_primary_v47_explanation: bool = False
    m1_triad_unreachability_supported_as_primary_v47_explanation: bool = False
    composition_layer_is_primary_investigation_target: bool = True
    economics_inherited_from_old_population: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 density lineage identity is frozen")
        if self.m1_data_scarcity_supported_as_primary_v47_explanation:
            raise ValueError("retained native-M1 evidence contradicts M1 data-scarcity explanation")
        if self.m1_triad_unreachability_supported_as_primary_v47_explanation:
            raise ValueError(
                "retained native-M1 evidence contradicts triad-unreachability explanation"
            )
        if not self.composition_layer_is_primary_investigation_target:
            raise ValueError("V48 density evidence points to composition as primary investigation")
        if self.economics_inherited_from_old_population or self.fresh_holdout_authorized:
            raise ValueError("density lineage grants no economic/Fresh authority")


V48_DENSITY_LINEAGE = V48DensityLineage()
