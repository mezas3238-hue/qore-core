from qore.infrastructure.traders.crt_pure_identity import (
    CRT_PURE_IDENTITY,
    CrtPureMarket,
    CrtPureSourceTier,
    canonical_methodology_sources,
    corroboration_sources,
)


def test_crt_pure_scope_is_exactly_three_owner_approved_markets() -> None:
    assert CRT_PURE_IDENTITY.markets == (
        CrtPureMarket.AUDUSD,
        CrtPureMarket.USDJPY,
        CrtPureMarket.BTCUSD,
    )


def test_crt_amd_is_explicitly_excluded() -> None:
    assert "crt-4h-amd" in CRT_PURE_IDENTITY.excluded_methodology_ids
    assert CRT_PURE_IDENTITY.methodology_family == "CRT"
    assert CRT_PURE_IDENTITY.methodology_variant == "PURE"


def test_only_primary_sources_can_define_methodology() -> None:
    canonical = canonical_methodology_sources()
    assert [item.name for item in canonical] == [
        "RomeoTPT",
        "RomeoTPT author-distributed documents",
    ]
    assert all(item.can_define_methodology for item in canonical)
    assert all(
        item.tier in {CrtPureSourceTier.LEVEL_A, CrtPureSourceTier.LEVEL_A_PLUS}
        for item in canonical
    )


def test_level_b_sources_are_corroboration_only() -> None:
    corroboration = corroboration_sources()
    assert [item.name for item in corroboration] == [
        "SpeculatorFL",
        "TraderFlameseN",
        "TTrades",
    ]
    assert all(item.tier is CrtPureSourceTier.LEVEL_B for item in corroboration)
    assert all(not item.can_define_methodology for item in corroboration)


def test_identity_remains_pre_certification_until_source_closure() -> None:
    assert CRT_PURE_IDENTITY.source_adjudication_complete is False
    assert CRT_PURE_IDENTITY.strategy_identity_complete is False
    assert CRT_PURE_IDENTITY.certified is False
