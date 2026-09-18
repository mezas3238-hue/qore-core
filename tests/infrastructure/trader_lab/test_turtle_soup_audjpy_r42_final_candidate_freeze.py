from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r42_final_candidate_freeze as r42,
)


def test_r42_binds_exact_passing_r41() -> None:
    assert r42.SOURCE_RUN_ID == 35399430491
    assert r42.SOURCE_ARTIFACT_ID == 10569333275
    assert r42.EXPECTED_5Y_TRADES == 1039
    assert r42.EXPECTED_5Y_PF == "1.957251590510384151212372667"
    assert r42.EXPECTED_5Y_DD == "5.293573269867727808258117465"
    assert r42.EXPECTED_2Y_TRADES == 422
    assert r42.EXPECTED_2Y_PF == "2.316526174177060282046559780"
    assert r42.EXPECTED_2Y_DD == "3.13869363160529373642812201"
