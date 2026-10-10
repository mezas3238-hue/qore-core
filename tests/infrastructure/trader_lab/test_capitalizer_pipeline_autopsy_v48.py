from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_pipeline_autopsy_v48 import (
    FRACTAL_S2A_AUTOPSY,
    FTM_S2C_AUTOPSY,
    S1R_INDEPENDENT_M1_EVIDENCE,
    stage_survival_table,
)


def test_fractal_s2a_population_matches_authoritative_v47_counts() -> None:
    assert FRACTAL_S2A_AUTOPSY.root_population == 2551
    assert FRACTAL_S2A_AUTOPSY.final_population == 91
    assert FRACTAL_S2A_AUTOPSY.cumulative_survival == Decimal(91) / Decimal(2551)
    assert FRACTAL_S2A_AUTOPSY.most_destructive_stage.stage_id == "INDEPENDENT_M1_BOUND"


def test_ftm_s2c_population_matches_authoritative_v47_counts() -> None:
    assert FTM_S2C_AUTOPSY.root_population == 46840
    assert FTM_S2C_AUTOPSY.final_population == 98
    assert FTM_S2C_AUTOPSY.cumulative_survival == Decimal(98) / Decimal(46840)
    assert FTM_S2C_AUTOPSY.most_destructive_stage.stage_id == "ICT_CONTINUATION_MSS_FVG"


def test_ftm_has_multiple_severe_multiplicative_bottlenecks() -> None:
    survival = {
        stage.stage_id: stage.incremental_survival
        for stage in FTM_S2C_AUTOPSY.stages
    }
    assert survival["ICT_CONTINUATION_MSS_FVG"] < Decimal("0.20")
    assert survival["INDEPENDENT_M1_BOUND"] < Decimal("0.40")
    assert survival["DETERMINISTIC_TARGET_BOUND"] < Decimal("0.32")


def test_s1r_demonstrates_recovery_when_m1_is_decoupled() -> None:
    evidence = S1R_INDEPENDENT_M1_EVIDENCE
    assert evidence.current_pipeline_count == 3
    assert evidence.alternative_construction_count == 15
    assert evidence.alternative_construction_count > evidence.current_pipeline_count


def test_stage_table_reports_incremental_and_cumulative_survival() -> None:
    rows = stage_survival_table(FRACTAL_S2A_AUTOPSY)
    assert rows[0][0] == "HTF_ALIGNED"
    assert rows[-1][0] == "V46_ADMITTED"
    assert rows[-1][4] == Decimal(91) / Decimal(2551)
