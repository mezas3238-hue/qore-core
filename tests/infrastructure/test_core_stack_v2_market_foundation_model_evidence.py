from qore.infrastructure.core_stack_v2.market_foundation_model_evidence import (
    FoundationLearningObjective,
    FoundationModality,
    MarketFoundationEvidence,
)


def _evidence(*, global_bound: bool = False) -> MarketFoundationEvidence:
    return MarketFoundationEvidence(
        representation_fingerprint="e2fc2ca059d5852b4e9107c467392e5e64aeabbd6aca2d8013951b93402bc987",
        concept_count=6,
        probe_count=8,
        horizon_minutes=30,
        markets=("NAS100", "SP500", "US30"),
        market_families=("US_EQUITY_INDEX",),
        objectives_proven=tuple(
            sorted(
                (
                    FoundationLearningObjective.NEXT_STATE_PREDICTION,
                    FoundationLearningObjective.CROSS_MARKET_REPRESENTATION,
                ),
                key=lambda item: item.value,
            )
        ),
        modalities_proven=(FoundationModality.M1_OHLC_DERIVED_SEQUENCE,),
        fresh_holdout_incremental_bps=288,
        fresh_holdout_positive_targets=8,
        temporal_replication_incremental_bps=312,
        temporal_replication_positive_targets=8,
        global_multi_family_world_bound=global_bound,
    )


def test_sequence_representation_is_scientifically_proven() -> None:
    evidence = _evidence()
    assert evidence.sequence_representation_scientifically_proven is True


def test_single_family_evidence_cannot_claim_mc12_ceiling() -> None:
    evidence = _evidence()
    assert evidence.ceiling_complete is False


def test_global_binding_is_explicit_requirement_for_ceiling() -> None:
    evidence = _evidence(global_bound=True)
    assert evidence.ceiling_complete is True


def test_evidence_fingerprint_is_deterministic() -> None:
    assert _evidence().fingerprint() == _evidence().fingerprint()
