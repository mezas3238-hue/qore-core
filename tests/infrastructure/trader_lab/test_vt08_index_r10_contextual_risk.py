from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as mod


def test_r10_preserves_density_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.TARGET_R == Decimal("2.5")


def test_r10_scheme_space_never_uses_zero_risk() -> None:
    schemes = mod._schemes()
    assert len(schemes) == 6
    for scheme in schemes:
        contexts = (
            mod.Context(True, False, False, False),
            mod.Context(False, False, False, False),
            mod.Context(False, True, True, True),
        )
        assert all(scheme.weight(context) > 0 for context in contexts)


def test_r10_context_is_pre_entry_only() -> None:
    assert set(mod.Context.__annotations__) == {
        "previous_source_day_body_opposed",
        "rearm",
        "c2_expansion",
        "short",
    }


def test_r10_target_goals() -> None:
    # Economic goal is evaluated in report construction.
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
