from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_ttrades_cisd_density_bridge_v48 import (
    TTRADES_CISD_1Y_EVIDENCE,
    V48_TTRADES_CISD_DENSITY_ADJUDICATION,
)


def test_authoritative_1y_population_is_bound_exactly() -> None:
    evidence = TTRADES_CISD_1Y_EVIDENCE
    assert evidence.workflow_run_id == 35629551926
    assert evidence.aggregate_artifact_id == 10654022630
    assert evidence.directional_raid_candidates == 853
    assert evidence.close_entries == 612
    assert evidence.retest_entries == 575
    assert evidence.close_max3_selected == 599
    assert evidence.retest_max3_selected == 569


def test_standalone_cisd_retains_most_directional_raid_candidates() -> None:
    evidence = TTRADES_CISD_1Y_EVIDENCE
    assert evidence.close_survival_vs_directional_raid == Decimal(612) / Decimal(853)
    assert evidence.retest_survival_vs_directional_raid == Decimal(575) / Decimal(853)
    assert evidence.close_survival_vs_directional_raid > Decimal("0.70")
    assert evidence.retest_survival_vs_directional_raid > Decimal("0.67")
    assert evidence.fvg_required is False
    assert evidence.ict_mss_required is False


def test_density_bridge_does_not_reuse_surrogate_economics_or_risk_policy() -> None:
    state = V48_TTRADES_CISD_DENSITY_ADJUDICATION
    assert state.m1_cisd_scarcity_supported_as_primary_v47_explanation is False
    assert state.cross_layer_composition_remains_primary_investigation is True
    assert state.historical_economics_reusable is False
    assert state.historical_target_policy_reusable is False
    assert state.historical_stop_policy_reusable is False
    assert state.fresh_holdout_authorized is False
