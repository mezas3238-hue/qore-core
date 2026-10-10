from qore.infrastructure.trader_lab.capitalizer_v50_hierarchical_memory import (
    separate_memory_representation,
)


def test_identity_and_derived_tokens_cannot_be_causal_evidence() -> None:
    result = separate_memory_representation(
        symbol="EURUSD",
        session="LONDON",
        tokens=(
            "SYMBOL=EURUSD",
            "SESSION=LONDON",
            "H1_FRESHNESS=FRESH",
            "M15_M1_FRESHNESS=IMMEDIATE",
            "STOP_NOISE=BALANCED",
            "STRUCTURAL_DISPOSITION=PASS_TO_COMPETITION",
            "TRIGGER=FVG_RETRACE_CISD",
        ),
    )
    assert "SYMBOL=EURUSD" in result.context_tokens
    assert "SESSION=LONDON" in result.context_tokens
    assert "STRUCTURAL_DISPOSITION=PASS_TO_COMPETITION" in result.derived_tokens
    assert "H1_FRESHNESS=FRESH" in result.evidence_tokens
    assert "TRIGGER=FVG_RETRACE_CISD" in result.evidence_tokens
    assert all(not token.startswith("SYMBOL=") for token in result.evidence_tokens)
    assert all(not token.startswith("SESSION=") for token in result.evidence_tokens)
    assert all(
        not token.startswith("STRUCTURAL_DISPOSITION=")
        for token in result.evidence_tokens
    )


def test_representation_is_deterministic_and_outcome_blind() -> None:
    result = separate_memory_representation(
        symbol="XAUUSD",
        session="NEW_YORK",
        tokens=(
            "TRIGGER=LIQUIDITY_SWEEP_CISD",
            "H1_FRESHNESS=AGING",
            "TRIGGER=LIQUIDITY_SWEEP_CISD",
            "SESSION=NEW_YORK",
            "SYMBOL=XAUUSD",
        ),
    )
    assert result.evidence_tokens == (
        "H1_FRESHNESS=AGING",
        "TRIGGER=LIQUIDITY_SWEEP_CISD",
    )
    assert result.outcome_visible is False
    assert result.admission_decision_made is False
    assert result.rule_promotion_allowed is False
