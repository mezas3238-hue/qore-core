from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r115_last_extreme_source_qualification as r115,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r82_protected_swing_source_qualification as r82,
)


def test_r115_expected_standard_surface_is_frozen() -> None:
    assert r115.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }


def test_r115_r114_source_is_pinned() -> None:
    assert r115.SOURCE_R114_RUN_ID == 35665635210
    assert r115.SOURCE_R114_ARTIFACT_ID == 10669476302
    assert r115.SOURCE_R114_ARTIFACT_DIGEST == (
        "sha256:134027f3bc4c246c9316cc38df1de5bab6e01ac71a04eacb8516ad88280eaec7"
    )


def test_r115_qualification_family_contract_is_exact_r82() -> None:
    assert set(r82.FAMILIES) == {
        r82.FAMILY_LIQUIDITY,
        r82.FAMILY_FVG,
        r82.FAMILY_BOTH,
        r82.FAMILY_UNQUALIFIED,
    }
