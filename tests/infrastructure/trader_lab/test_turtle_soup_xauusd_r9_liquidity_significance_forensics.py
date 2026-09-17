from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_liquidity_significance_forensics as r9l


def test_ratio_fails_closed() -> None:
    assert r9l._ratio(Decimal("1"), None) is None
    assert r9l._ratio(Decimal("1"), Decimal("0")) is None
    assert r9l._ratio(Decimal("1"), Decimal("4")) == Decimal("0.25")


def test_percentile_interpolates() -> None:
    values = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")]
    assert r9l._percentile(values, 1, 2) == Decimal("2.5")


def test_feature_contract_covers_liquidity_externality_and_htf_edges() -> None:
    required = {
        "c1_externality_rank_20",
        "c1_beyond_prior20_source_range_fraction",
        "c1_prior_h4_edge_distance_fraction",
        "c1_prior_d1_edge_distance_fraction",
        "c1_nearest_prior_h4_boundary_source_fraction",
        "c1_nearest_prior_d1_boundary_source_fraction",
        "c1_directional_wick_fraction",
    }
    assert required <= set(r9l.FEATURES)


def test_identity_is_research_only() -> None:
    assert "LIQUIDITY_SIGNIFICANCE_FORENSICS" in r9l.IDENTITY
    assert "NOT_FRESH_HOLDOUT" in r9l.EVIDENCE_STATUS
