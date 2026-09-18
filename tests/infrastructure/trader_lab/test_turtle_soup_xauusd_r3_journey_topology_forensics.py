from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_journey_topology_forensics as topo


def test_family_classification() -> None:
    stable = {"raid_depth_range_bucket": "q2:<=0.10", "cisd_progress_bucket": "q4:>0.75"}
    failing = {"raid_depth_range_bucket": "q4:<=0.50", "cisd_progress_bucket": "q4:>0.75"}
    other = {"raid_depth_range_bucket": "q3:<=0.25", "cisd_progress_bucket": "q2:<=0.50"}
    assert topo._family(stable) == "RAID_5_10_STABLE"
    assert topo._family(failing) == "RAID_25_50_LATE_CISD_FAILING"
    assert topo._family(other) == "OTHER"


def test_candidate_route_mapping() -> None:
    assert topo._candidate_route({"candidate_type": "SOURCE_OPPOSITE_BOUNDARY", "source_timeframe": "H1"}) == "SOURCE_OPPOSITE"
    assert topo._candidate_route({"candidate_type": "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY", "source_timeframe": "H4"}) == "PRIOR_H4"
    assert topo._candidate_route({"candidate_type": "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY", "source_timeframe": "H1"}) == "SWING_H1"
