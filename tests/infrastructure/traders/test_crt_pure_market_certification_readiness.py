from __future__ import annotations

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_market_certification_readiness import (
    CrtPureMarketCertificationEvidence,
    CrtPureMarketCertificationStage,
    evaluate_market_certification_readiness,
)


def _evidence(**overrides: bool) -> CrtPureMarketCertificationEvidence:
    values = {
        "market_history_verified": True,
        "exact_candidate_frozen": True,
        "fresh_holdout_green": True,
        "chronological_replay_green": True,
        "annual_stability_green": True,
        "rolling_stability_green": True,
        "walk_forward_green": True,
        "stress_green": True,
        "slippage_green": True,
        "monte_carlo_green": True,
        "robustness_green": True,
    }
    values.update(overrides)
    return CrtPureMarketCertificationEvidence(
        market=CrtPureMarket.BTCUSD,
        **values,
    )


def test_per_market_certification_is_fail_closed() -> None:
    readiness = evaluate_market_certification_readiness(
        _evidence(slippage_green=False)
    )

    assert readiness.stage is CrtPureMarketCertificationStage.ROBUSTNESS_VALIDATION
    assert readiness.research_certified is False
    assert readiness.blockers == ("SLIPPAGE_NOT_GREEN",)


def test_per_market_research_certification_never_grants_deployment() -> None:
    readiness = evaluate_market_certification_readiness(_evidence())

    assert readiness.stage is CrtPureMarketCertificationStage.RESEARCH_CERTIFIED
    assert readiness.research_certified is True
    assert readiness.external_review_required is True
    assert readiness.demo_authorized is False
    assert readiness.live_authorized is False
    assert readiness.real_capital_authorized is False
    assert readiness.production_authorized is False
