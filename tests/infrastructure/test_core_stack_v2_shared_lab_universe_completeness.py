from qore.infrastructure.core_stack_v2.shared_lab_universe_completeness import assess_universe_coverage


def test_partial_universe_fails_strict_coverage() -> None:
    receipt = assess_universe_coverage(
        ("FX:EURUSD", "METAL:XAUUSD", "CRYPTO:BTCUSD"),
        ("FX:EURUSD", "METAL:XAUUSD"),
    )
    assert not receipt.passed
    assert receipt.missing_instruments == ("CRYPTO:BTCUSD",)
    assert receipt.coverage_ratio == 2 / 3


def test_universe_threshold_is_parameterized() -> None:
    receipt = assess_universe_coverage(
        ("A", "B", "C", "D"),
        ("A", "B", "C"),
        min_coverage_ratio=0.75,
    )
    assert receipt.passed


def test_unexpected_instrument_fails_even_with_full_expected_coverage() -> None:
    receipt = assess_universe_coverage(("A", "B"), ("A", "B", "WRONG"))
    assert not receipt.passed
    assert receipt.unexpected_instruments == ("WRONG",)
