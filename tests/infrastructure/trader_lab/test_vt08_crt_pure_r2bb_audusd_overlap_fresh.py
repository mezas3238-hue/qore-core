from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bb_audusd_overlap_fresh import (
    END,
    EXCLUDED_DIMENSION,
    EXCLUDED_LABEL,
    IDENTITY,
    START,
    YEARS,
)


def test_r2bb_candidate_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BB_AUDUSD_OVERLAP_FRESH_2011_2016_001"
    assert EXCLUDED_DIMENSION == "confirmation_source_overlap"
    assert EXCLUDED_LABEL == "CONFOVERLAP_0_50_TO_0_75"


def test_r2bb_holdout_is_five_years() -> None:
    assert START.year == 2011
    assert END.year == 2016
    assert YEARS == 5
