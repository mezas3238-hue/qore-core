"""Tests for the CIBO Cognitive World Model substrate (CA-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    TraderSubject,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_world_model import (
    MarketContextKind,
    MarketContextReference,
    MarketTraderContext,
    MarketTraderSuitability,
    MarketTraderSuitabilityDisposition,
    WorldModelContradiction,
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSnapshot,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_market_trader_suitability,
    build_world_model_snapshot,
    project_world_state,
)
from qore.kernel.result import Failure, Success

_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-0000000000a1")
_AS_OF = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
_SUITABILITY_ID = UUID("00000000-0000-0000-0000-0000000000b1")


def _fp(label: str) -> CiboCognitiveFingerprint:
    return fingerprint_material(label)


def _reference(
    *,
    domain: WorldModelDomain = WorldModelDomain.MARKET,
    source: str = "source-a",
    version: str = "1",
    as_of: datetime = _AS_OF,
    status: WorldModelReferenceStatus = WorldModelReferenceStatus.CURRENT,
    label: str | None = "provider-neutral market evidence",
) -> WorldModelReference:
    return WorldModelReference(
        domain=domain,
        source_id=WorldModelSourceId(source),
        source_version=WorldModelSourceVersion(version),
        as_of=as_of,
        status=status,
        evidence_fingerprint=_fp(f"{source}:{version}"),
        evidence_label=label,
    )


def test_snapshot_builds_and_projects() -> None:
    ref = _reference()
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[ref],
        staleness_threshold=timedelta(days=1),
    )
    assert snapshot.fingerprint.value == snapshot.fingerprint.value
    assert snapshot.references_for(WorldModelDomain.MARKET) == (ref,)
    assert project_world_state(snapshot, WorldModelDomain.MARKET) == Success((ref,))


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=datetime(2024, 6, 1, 12, 0, 0),
            references=[_reference()],
        )
    with pytest.raises(CiboCognitiveValidationError):
        _reference(as_of=datetime(2024, 6, 1, 12, 0, 0))


def test_secret_bearing_evidence_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _reference(label="api_key=sk-abcdef1234567890")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[
                _reference(label="-----BEGIN PRIVATE KEY-----"),
            ],
        )


def test_contradictory_sources_cannot_collapse() -> None:
    first = _reference(source="source-a")
    second = _reference(source="source-b")
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[first, second],
    )
    result = snapshot.resolved_reference(WorldModelDomain.MARKET)
    assert isinstance(result, Failure)

    contradiction = WorldModelContradiction(
        left=first, right=second, reason="sources disagree on regime"
    )
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[first, second],
        contradictions=[contradiction],
    )
    assert isinstance(snapshot.resolved_reference(WorldModelDomain.MARKET), Failure)


def test_single_source_resolves_without_contradiction() -> None:
    ref = _reference()
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
    )
    result = snapshot.resolved_reference(WorldModelDomain.MARKET)
    assert isinstance(result, Success)
    assert result.value == ref


def test_stale_source_cannot_masquerade_as_current() -> None:
    old = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[_reference(as_of=old, status=WorldModelReferenceStatus.CURRENT)],
            staleness_threshold=timedelta(days=1),
        )


def test_stale_source_is_explicitly_allowed() -> None:
    old = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[_reference(as_of=old, status=WorldModelReferenceStatus.STALE)],
        staleness_threshold=timedelta(days=1),
    )
    assert snapshot.stale_references()
    assert isinstance(snapshot.resolved_reference(WorldModelDomain.MARKET), Success)


def test_future_reference_rejected() -> None:
    future = datetime(2024, 6, 2, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[_reference(as_of=future)],
        )


def test_missing_reference_requires_no_evidence_fingerprint() -> None:
    ref = WorldModelReference(
        domain=WorldModelDomain.RESEARCH,
        source_id=WorldModelSourceId("research-a"),
        source_version=WorldModelSourceVersion("2"),
        as_of=_AS_OF,
        status=WorldModelReferenceStatus.MISSING,
        evidence_fingerprint=None,
        evidence_label=None,
    )
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
    )
    assert WorldModelDomain.RESEARCH in snapshot.missing_domains()
    assert snapshot.references_for(WorldModelDomain.RESEARCH) == ()


def test_reflective_corruption_fails_recursive_revalidation() -> None:
    ref = _reference()
    object.__setattr__(ref, "evidence_label", "password=hunter2secret")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
        )


def test_nested_reflective_corruption_fails() -> None:
    ref = _reference()
    object.__setattr__(ref.source_id, "value", "bad value with space")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
        )


def test_bool_cannot_launder_as_identity_or_version() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceId(True)  # type: ignore[arg-type]
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceVersion(False)  # type: ignore[arg-type]


def test_subclass_laundering_rejected() -> None:
    class EvilStr(str):
        pass

    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceId(EvilStr("source-a"))


def test_snapshot_ordering_is_permutation_invariant() -> None:
    refs = [_reference(source="a"), _reference(source="b"), _reference(source="c")]
    snapshot_one = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=refs
    )
    snapshot_two = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=list(reversed(refs))
    )
    assert snapshot_one.references == snapshot_two.references
    assert snapshot_one.fingerprint == snapshot_two.fingerprint


def test_contradiction_requires_same_domain() -> None:
    first = _reference(domain=WorldModelDomain.MARKET)
    second = _reference(domain=WorldModelDomain.PORTFOLIO)
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelContradiction(left=first, right=second, reason="cross-domain")


def test_snapshot_is_frozen() -> None:
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[_reference()]
    )
    assert isinstance(snapshot, WorldModelSnapshot)
    with pytest.raises(AttributeError):
        snapshot.as_of = _AS_OF  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IA-F-MARKET-TRADER-001: typed Market x Regime x Instrument x exact-Trader
# suitability family (CA-04).
# ---------------------------------------------------------------------------


def _trader(trader_id: str = "trader.vt-1", version: str = "v1") -> TraderSubject:
    return TraderSubject(
        trader_id=trader_id,
        trader_version=version,
        fingerprint=fingerprint_material((trader_id, version)),
    )


def _ctx_ref(
    kind: MarketContextKind,
    reference: str,
    *,
    status: WorldModelReferenceStatus = WorldModelReferenceStatus.CURRENT,
    as_of: datetime = _AS_OF,
) -> MarketContextReference:
    return MarketContextReference(
        kind=kind,
        reference=reference,
        as_of=as_of,
        status=status,
        evidence_fingerprint=(
            None
            if status is WorldModelReferenceStatus.MISSING
            else fingerprint_material((kind.value, reference))
        ),
        evidence_label=f"{kind.value} evidence",
    )


def _context(
    *,
    market: str = "market.fx",
    instrument: str = "instrument.eurusd",
    regime: str = "regime.trending",
) -> MarketTraderContext:
    return MarketTraderContext(
        market=_ctx_ref(MarketContextKind.MARKET, market),
        instrument=_ctx_ref(MarketContextKind.INSTRUMENT, instrument),
        regime=_ctx_ref(MarketContextKind.REGIME, regime),
    )


def _favorable(
    *,
    trader: TraderSubject | None = None,
    context: MarketTraderContext | None = None,
    **kwargs: object,
) -> MarketTraderSuitability:
    params: dict[str, Any] = {
        "suitability_id": _SUITABILITY_ID,
        "trader": trader if trader is not None else _trader(),
        "context": context if context is not None else _context(),
        "disposition": MarketTraderSuitabilityDisposition.FAVORABLE,
        "limitations": ("not-perfect-certainty",),
        "evidence_lineage": (fingerprint_material("evidence-1"),),
    }
    params.update(kwargs)
    return build_market_trader_suitability(**params)


def test_market_trader_suitability_favorable_builds_and_revalidates() -> None:
    suitability = _favorable()
    assert suitability.disposition is MarketTraderSuitabilityDisposition.FAVORABLE
    suitability.revalidate()


def test_cross_trader_fingerprint_laundering_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        TraderSubject(
            trader_id="trader.vt-2",
            trader_version="v1",
            fingerprint=fingerprint_material(("trader.vt-1", "v1")),
        )


def test_same_trader_version_laundering_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        TraderSubject(
            trader_id="trader.vt-1",
            trader_version="v2",
            fingerprint=fingerprint_material(("trader.vt-1", "v1")),
        )


def test_instrument_axis_mismatch_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        MarketTraderContext(
            market=_ctx_ref(MarketContextKind.MARKET, "market.fx"),
            instrument=_ctx_ref(MarketContextKind.REGIME, "regime.trending"),
            regime=_ctx_ref(MarketContextKind.REGIME, "regime.trending"),
        )


def test_regime_axis_mismatch_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        MarketTraderContext(
            market=_ctx_ref(MarketContextKind.MARKET, "market.fx"),
            instrument=_ctx_ref(MarketContextKind.INSTRUMENT, "instrument.eurusd"),
            regime=_ctx_ref(MarketContextKind.INSTRUMENT, "instrument.eurusd"),
        )


def test_stale_market_evidence_cannot_assert_favorable() -> None:
    stale = _context(market="market.fx")
    object.__setattr__(
        stale.market,
        "status",
        WorldModelReferenceStatus.STALE,
    )
    with pytest.raises(CiboCognitiveValidationError):
        _favorable(context=stale)


def test_missing_evidence_cannot_be_treated_as_certainty() -> None:
    missing = MarketTraderContext(
        market=_ctx_ref(
            MarketContextKind.MARKET,
            "market.fx",
            status=WorldModelReferenceStatus.MISSING,
        ),
        instrument=_ctx_ref(MarketContextKind.INSTRUMENT, "instrument.eurusd"),
        regime=_ctx_ref(MarketContextKind.REGIME, "regime.trending"),
    )
    with pytest.raises(CiboCognitiveValidationError):
        _favorable(context=missing)


def test_contradictory_references_cannot_collapse_into_favorable() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _favorable(contradictions=("regime-conflict",))


def test_favorable_requires_explicit_limitations() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        build_market_trader_suitability(
            suitability_id=_SUITABILITY_ID,
            trader=_trader(),
            context=_context(),
            disposition=MarketTraderSuitabilityDisposition.FAVORABLE,
            limitations=(),
            evidence_lineage=(fingerprint_material("evidence-1"),),
        )


def test_suitability_exposes_no_authority_fields() -> None:
    suitability = _favorable()
    for forbidden in (
        "execution",
        "risk",
        "promotion",
        "demo",
        "production",
        "profitability",
        "order",
        "account",
        "credential",
        "quantity",
    ):
        assert not hasattr(suitability, forbidden)


def test_suitability_secret_material_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _ctx_ref(MarketContextKind.MARKET, "market.fx").__class__(
            kind=MarketContextKind.MARKET,
            reference="market.api_key=sk-abcdef1234567890",
            as_of=_AS_OF,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("x"),
        )


def test_suitability_subclass_laundering_rejected() -> None:
    class EvilStr(str):
        pass

    class EvilDatetime(datetime):
        pass

    class EvilTraderSubject(TraderSubject):
        def revalidate(self) -> None:
            pass

    with pytest.raises(CiboCognitiveValidationError):
        _ctx_ref(MarketContextKind.MARKET, EvilStr("market.fx"))
    with pytest.raises(CiboCognitiveValidationError):
        _favorable(
            trader=EvilTraderSubject(
                trader_id="trader.vt-1",
                trader_version="v1",
                fingerprint=fingerprint_material(("trader.vt-1", "v1")),
            )
        )
    with pytest.raises(CiboCognitiveValidationError):
        MarketContextReference(
            kind=MarketContextKind.MARKET,
            reference="market.fx",
            as_of=EvilDatetime(2024, 6, 1, tzinfo=UTC),
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("x"),
        )


def test_suitability_bool_int_laundering_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        MarketContextReference(
            kind=MarketContextKind.MARKET,
            reference="market.fx",
            as_of=_AS_OF,
            status=cast(WorldModelReferenceStatus, True),
            evidence_fingerprint=fingerprint_material("x"),
        )
    with pytest.raises(CiboCognitiveValidationError):
        _favorable(evidence_lineage=(True,))


def test_suitability_reflective_corruption_rejected() -> None:
    suitability = _favorable()
    object.__setattr__(suitability, "contradictions", ("injected-contradiction",))
    with pytest.raises(CiboCognitiveValidationError):
        suitability.revalidate()


def test_suitability_ordering_is_permutation_invariant() -> None:
    first = _favorable(
        limitations=("not-perfect-certainty", "bounded-evidence"),
        evidence_lineage=(
            fingerprint_material("a"),
            fingerprint_material("b"),
        ),
    )
    second = _favorable(
        limitations=("bounded-evidence", "not-perfect-certainty"),
        evidence_lineage=(
            fingerprint_material("b"),
            fingerprint_material("a"),
        ),
    )
    assert first.limitations == second.limitations
    assert first.evidence_lineage == second.evidence_lineage
    assert first.fingerprint == second.fingerprint


def _snapshot() -> WorldModelSnapshot:
    return build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[_reference()],
        staleness_threshold=timedelta(days=1),
    )


class TestSnapshotReadPathRevalidation:
    def test_references_for_revalidates_nested_reference(self) -> None:
        snapshot = _snapshot()
        object.__setattr__(snapshot.references[0].source_id, "value", "bad value with space")
        with pytest.raises(CiboCognitiveValidationError):
            snapshot.references_for(WorldModelDomain.MARKET)

    def test_resolved_reference_revalidates_nested_reference(self) -> None:
        snapshot = _snapshot()
        object.__setattr__(snapshot.references[0].source_id, "value", "bad value with space")
        with pytest.raises(CiboCognitiveValidationError):
            snapshot.resolved_reference(WorldModelDomain.MARKET)

    def test_snapshot_revalidate_rejects_corrupted_reference(self) -> None:
        snapshot = _snapshot()
        object.__setattr__(snapshot.references[0].source_id, "value", "bad value with space")
        with pytest.raises(CiboCognitiveValidationError):
            snapshot.revalidate()


def test_source_id_rejects_secret_material() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceId("sk-abcdefghijklmnop")


def test_source_version_rejects_secret_material() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceVersion("ghp_abcdefghijklmnopqrstuvwxyz1234")


class TestWorldModelContradictionTemporalSemantics:
    def test_dst_fold_instants_are_distinct_references(self) -> None:
        tz = ZoneInfo("America/New_York")
        f0 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=0)
        f1 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=1)
        left = _reference(as_of=f0)
        right = _reference(as_of=f1)
        contradiction = WorldModelContradiction(left=left, right=right, reason="fold disagreement")
        contradiction.revalidate()

    def test_same_reference_across_offsets_still_rejected(self) -> None:
        utc = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        est = datetime(2024, 6, 1, 7, 0, tzinfo=timezone(timedelta(hours=-5)))
        left = _reference(as_of=utc)
        right = _reference(as_of=est)
        with pytest.raises(CiboCognitiveValidationError):
            WorldModelContradiction(left=left, right=right, reason="not distinct")
