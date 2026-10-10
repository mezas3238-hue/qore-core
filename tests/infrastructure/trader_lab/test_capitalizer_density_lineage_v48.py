from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_density_lineage_v48 import (
    NATIVE_M1_TRIAD_POPULATION,
    V47_REJECTED_PRE_UNION,
    V48_DENSITY_LINEAGE,
    complete_year_native_m1_counts,
    mean_complete_year_native_m1_entries,
    population_capacity_ratio_vs_v47_pre_union,
)


def test_native_m1_triad_population_matches_retained_artifact() -> None:
    assert NATIVE_M1_TRIAD_POPULATION.evidence_run_id == 35548099334
    assert NATIVE_M1_TRIAD_POPULATION.evidence_artifact_id == 10619127272
    assert NATIVE_M1_TRIAD_POPULATION.total_population == 21696
    assert complete_year_native_m1_counts() == (
        2078,
        2167,
        2087,
        2188,
        2183,
        2170,
        2169,
        2242,
        2258,
    )
    assert mean_complete_year_native_m1_entries() == Decimal(19542) / Decimal(9)


def test_v47_count_is_pre_union_not_s2d_survivor_claim() -> None:
    assert V47_REJECTED_PRE_UNION.fractal_rows == 91
    assert V47_REJECTED_PRE_UNION.ftm_rows == 98
    assert V47_REJECTED_PRE_UNION.pre_union_rows == 189
    assert V47_REJECTED_PRE_UNION.final_union_authoritatively_executed is False
    assert V47_REJECTED_PRE_UNION.pre_union_rows_per_year == Decimal("31.5")


def test_population_capacity_gap_is_about_sixty_nine_fold() -> None:
    ratio = population_capacity_ratio_vs_v47_pre_union()
    assert Decimal("68") < ratio < Decimal("70")


def test_density_lineage_does_not_inherit_old_economics() -> None:
    state = V48_DENSITY_LINEAGE
    assert state.m1_data_scarcity_supported_as_primary_v47_explanation is False
    assert state.m1_triad_unreachability_supported_as_primary_v47_explanation is False
    assert state.composition_layer_is_primary_investigation_target is True
    assert state.economics_inherited_from_old_population is False
    assert state.fresh_holdout_authorized is False
