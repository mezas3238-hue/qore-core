from __future__ import annotations

from decimal import Decimal, localcontext

from qore.infrastructure.volatility_variance_semantics import VarianceStrike


def test_extreme_decimal_exponents_remain_compact_and_exact() -> None:
    cases = (
        (Decimal("1E+1000000"), "1e+1000000"),
        (Decimal("1E-1000000"), "1e-1000000"),
    )

    with localcontext() as context:
        context.prec = 2
        for value, expected in cases:
            projected = VarianceStrike(value).logical_values()[0]
            assert projected == expected
            assert len(projected) == 10
            assert Decimal(projected) == value


def test_compact_fallback_preserves_existing_human_scale_material() -> None:
    assert VarianceStrike(Decimal("0.0400")).logical_values() == ("0.04",)
    assert VarianceStrike(Decimal("10000.00")).logical_values() == ("10000",)
    assert VarianceStrike(Decimal("-0.000")).logical_values() == ("0",)
