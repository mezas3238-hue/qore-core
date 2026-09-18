from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r33_candidate_freeze as freeze,
)


def test_r33_freeze_identity_and_source_are_immutable() -> None:
    assert freeze.IDENTITY == (
        "TURTLE_SOUP_XAUUSD_R33_FIVE_FAMILY_RISK_GOVERNOR_CANDIDATE_001"
    )
    assert freeze.SOURCE_RUN_ID == 35308249603
    assert freeze.SOURCE_ARTIFACT_ID == 10531704421
    assert freeze.SOURCE_GIT_SHA == "8dbe6385c7f15945e3f5001c76b70d0e5fc52b63"


def test_r33_freeze_economics_are_exact() -> None:
    assert freeze.EXPECTED_TRADES == 367
    assert freeze.EXPECTED_PF == "2.002523896485190572988396913"
    assert freeze.EXPECTED_DD == "5.69899493419710124390262490"
    assert freeze.SELECTED_GOVERNOR == "DD_2_4_SCALE_075_025"
