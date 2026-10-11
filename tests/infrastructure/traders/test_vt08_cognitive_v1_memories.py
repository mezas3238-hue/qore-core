from qore.infrastructure.traders.vt08_cognitive_cibo_market_memory import (
    cibo_market_memory_fingerprint,
    cibo_market_memory_runtime_view,
    market_anchor_prior,
    validate_cibo_market_memory,
)
from qore.infrastructure.traders.vt08_cognitive_memory import (
    cognitive_memory_fingerprint,
    market_anchor_context,
    validate_cognitive_memory,
)
from qore.infrastructure.traders.vt08_cognitive_trader_experience_memory import (
    R315_CERTIFIED_PORTFOLIO_SIDES,
    experience_cell,
    trader_experience_fingerprint,
    trader_experience_runtime_view,
    validate_trader_experience,
)


def test_cibo_market_memory_covers_every_vt08_forex_market_and_anchor() -> None:
    validate_cibo_market_memory()
    for market in (
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
    ):
        for anchor in (1, 5, 9):
            cell = market_anchor_prior(market, anchor)
            assert int(cell["sample"]) >= 500
    assert len(cibo_market_memory_fingerprint()) == 64


def test_trader_experience_is_market_anchor_specific_and_non_authoritative() -> None:
    validate_trader_experience()
    assert R315_CERTIFIED_PORTFOLIO_SIDES == {
        "AUDJPY": ("short",),
        "GBPJPY": ("long", "short"),
        "GBPUSD": ("short",),
    }
    assert experience_cell("GBPUSD", 9)["sample"] == 18
    assert experience_cell("EURUSD", 5)["sample"] == 11
    assert len(trader_experience_fingerprint()) == 64


def test_context_binds_market_memory_and_trader_experience_without_gate() -> None:
    context = market_anchor_context("GBPJPY", 5)
    assert context["market"] == "GBPJPY"
    assert context["anchor_hour_ny"] == 5
    assert context["use"] == "CONTEXT_ONLY_NOT_DIRECT_EXECUTION_GATE"
    assert len(str(context["fingerprint"])) == 64


def test_cognitive_memory_bundle_validates() -> None:
    validate_cognitive_memory()
    assert len(cognitive_memory_fingerprint()) == 64


def test_invalid_market_or_anchor_fails_closed() -> None:
    try:
        market_anchor_context("XAUUSD", 5)
    except ValueError as error:
        assert "outside Forex authority" in str(error)
    else:
        raise AssertionError("XAUUSD must fail closed")

    try:
        market_anchor_context("GBPUSD", 13)
    except ValueError as error:
        assert "outside 01/05/09" in str(error)
    else:
        raise AssertionError("13 NY must fail closed")


def test_memory_runtime_views_cannot_mutate_governed_cached_state() -> None:
    prior_cibo = cibo_market_memory_fingerprint()
    prior_experience = trader_experience_fingerprint()
    market_view = cibo_market_memory_runtime_view()
    experience_view = trader_experience_runtime_view()
    market_governance = market_view["governance"]
    experience_governance = experience_view["governance"]
    assert isinstance(market_governance, dict)
    assert isinstance(experience_governance, dict)
    market_governance["may_issue_execute_or_abstain"] = True
    experience_governance["runtime_self_training_allowed"] = True

    # Modifications to *returned* runtime observations cannot poison the
    # frozen cached source before another cognitive event uses the memory.
    new_market = cibo_market_memory_runtime_view()["governance"]
    new_experience = trader_experience_runtime_view()["governance"]
    assert isinstance(new_market, dict)
    assert isinstance(new_experience, dict)
    assert new_market["may_issue_execute_or_abstain"] is False
    assert new_experience["runtime_self_training_allowed"] is False
    assert cibo_market_memory_fingerprint() == prior_cibo
    assert trader_experience_fingerprint() == prior_experience
    validate_cognitive_memory()
