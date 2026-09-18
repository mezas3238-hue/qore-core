from qore.infrastructure.trader_lab import turtle_soup_xauusd_r4_topology_router_lab as lab


def test_variants_are_pre_registered() -> None:
    assert set(lab.VARIANTS) == {
        "R4A_RAID",
        "R4B_RAID_RECLAIM",
        "R4C_RAID_RECLAIM_RISK",
    }


def test_governance_identity() -> None:
    assert lab.IDENTITY == "TURTLE_SOUP_XAUUSD_R4_TOPOLOGY_ROUTER_LAB_V1"
    assert "NOT_FRESH_HOLDOUT" in lab.EVIDENCE_STATUS
